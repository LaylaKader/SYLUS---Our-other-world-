import os
import json
from pathlib import Path
import secrets
import hashlib
import hmac
import logging
import subprocess
import tempfile
import re
import html
import math
import random
from collections import defaultdict, deque
from time import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Literal
from uuid import UUID, uuid4
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import base64
import httpx
from .config import settings
from .db import connection, open_pool
from .migrate import run_migrations
from .chat_service import generate_reply, generate_proactive_bubbles, split_reply_bubbles, load_emotion_state, ProviderNotConfigured, ProviderRequestFailed
from .bond import refresh_bond
from .web_search import discover_for_chat, is_search_followup, requested_result_limit
from .image_delivery import extract_image_directive, extract_link_directive, should_generate_image

app = FastAPI(title="SYLUS private companion API", version="0.3.0")

def _search_web_context(query: str) -> str:
    """Small, keyless web lookup for explicit 'what is / do you know' questions."""
    try:
        response = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query[:220]},
            headers={"User-Agent": "Mozilla/5.0 (compatible; SylusCompanion/1.0)"},
            timeout=httpx.Timeout(8.0, connect=3.0),
            follow_redirects=True,
        )
        response.raise_for_status()
        page = response.text
        blocks = re.findall(r'<div class="result[^"]*"[^>]*>(.*?)</div>\s*</div>', page, flags=re.I | re.S)
        found = []
        for block in blocks[:5]:
            title_match = re.search(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', block, flags=re.I | re.S)
            snippet_match = re.search(r'<(?:a|div)[^>]*class="result__snippet"[^>]*>(.*?)</(?:a|div)>', block, flags=re.I | re.S)
            href_match = re.search(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"', block, flags=re.I | re.S)
            if not title_match:
                continue
            clean = lambda value: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()
            title = clean(title_match.group(1))
            snippet = clean(snippet_match.group(1)) if snippet_match else ""
            href = html.unescape(href_match.group(1)) if href_match else ""
            if "uddg=" in href:
                from urllib.parse import parse_qs, urlparse
                href = parse_qs(urlparse(href).query).get("uddg", [href])[0]
            if title and snippet:
                found.append(f"- {title}: {snippet} ({href})")
        return "\n".join(found[:4])
    except Exception as exc:
        logging.info("Optional web lookup unavailable (%s).", type(exc).__name__)
        return ""


def chat_provider_configured() -> bool:
    """True when at least one explicitly configured free-tier provider is available."""
    return any((
        settings.gemini_api_key, settings.groq_api_key, settings.openrouter_api_key,
        settings.aion_api_key, settings.cohere_api_key,
        settings.model_api_key,
    )) or bool(settings.cloudflare_account_id and settings.cloudflare_api_token)

DEFAULT_TIMEZONE = "Asia/Dhaka"
N109_TIME_OFFSET = timedelta(hours=2)


def _n109_clock(owner_local: datetime) -> datetime:
    # Keep the displayed N109 UTC offset consistent with its two-hour lead.
    owner_offset = owner_local.utcoffset() or timedelta(0)
    n109_wall_time = owner_local.replace(tzinfo=None) + N109_TIME_OFFSET
    return n109_wall_time.replace(tzinfo=timezone(owner_offset + N109_TIME_OFFSET))


def _n109_daily_rhythm(hour: int) -> str:
    if 5 <= hour < 9:
        return "morning briefings, reviewing overnight developments, and the day's first decisions"
    if 9 <= hour < 13:
        return "Onychinus operations, negotiations, Protocore logistics, and intelligence work"
    if 13 <= hour < 16:
        return "a meal break, checking in with his people, or a quieter stretch between obligations"
    if 16 <= hour < 20:
        return "meetings, security decisions, planning, and overseeing the organisation"
    if 20 <= hour < 24:
        return "private work, records, reading, music, or winding down after business"
    return "late-night work, a rare quiet hour, or sleep when his responsibilities allow"


def _elapsed_phrase(seconds: int) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds} seconds"
    minutes = seconds // 60
    if minutes < 60:
        return f"about {minutes} minute" + ("" if minutes == 1 else "s")
    hours, remaining = divmod(minutes, 60)
    if hours < 24:
        return f"about {hours} hour" + ("" if hours == 1 else "s") + (f" and {remaining} minutes" if remaining else "")
    days, remaining_hours = divmod(hours, 24)
    return f"about {days} day" + ("" if days == 1 else "s") + (f" and {remaining_hours} hours" if remaining_hours else "")


_origins = [item.strip() for item in settings.cors_allowed_origins.split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.on_event("startup")
def startup():
    run_migrations()
    open_pool()

@app.middleware("http")
async def prevent_private_api_caching(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: https:; "
        "connect-src 'self' https:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
    )
    if settings.app_env.lower() == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith("/v1/"):
        response.headers["Cache-Control"] = "no-store, private"
        response.headers["Pragma"] = "no-cache"
    return response

def _valid_session(value: str | None) -> bool:
    if not value or not settings.session_secret:
        return False
    try:
        timestamp_text, nonce, supplied = value.split(".", 2)
        timestamp = int(timestamp_text)
    except (ValueError, TypeError):
        return False
    now = int(time())
    if timestamp > now + 60 or now - timestamp > settings.session_ttl_seconds:
        return False
    expected = hmac.new(
        settings.session_secret.encode(), f"v1:{timestamp}:{nonce}".encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(supplied, expected):
        return False
    token_hash = hashlib.sha256(value.encode()).hexdigest()
    with connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM owner_sessions WHERE token_hash = %s AND expires_at > now() AND revoked_at IS NULL",
            (token_hash,),
        ).fetchone()
    return bool(row)

def require_owner(request: Request, authorization: str | None = Header(default=None)):
    expected = f"Bearer {settings.sylus_owner_token}"
    bearer_ok = bool(authorization and secrets.compare_digest(authorization, expected))
    if not bearer_ok and not _valid_session(request.cookies.get("sylus_session")):
        raise HTTPException(status_code=401, detail="Owner session required")

class OwnerLogin(BaseModel):
    password: str = Field(min_length=1, max_length=256)

class MessageIn(BaseModel):
    text: str | None = Field(default=None, min_length=1, max_length=12000)
    texts: list[str] | None = Field(default=None, min_length=1, max_length=4)

    def normalized_texts(self) -> list[str]:
        values = self.texts if self.texts else ([self.text] if self.text else [])
        cleaned = [value.strip() for value in values if value and value.strip()]
        if not cleaned or any(len(value) > 12000 for value in cleaned):
            raise ValueError('At least one non-empty message is required.')
        return cleaned

class MessageEdit(BaseModel):
    text: str = Field(min_length=1, max_length=12000)

class AttachmentOut(BaseModel):
    """Structured media/link card rendered directly beneath a chat message."""
    type: Literal["image", "link", "video", "music"]
    title: str = ""
    url: str
    description: str = ""
    source: str = ""
    source_url: str | None = None
    preview_url: str | None = None


class MessageOut(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    text: str
    created_at: datetime
    media_url: str | None = None
    attachments: list[AttachmentOut] = Field(default_factory=list)

class ChatTurnOut(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut | None = None
    assistant_messages: list[MessageOut] = Field(default_factory=list)
    user_messages: list[MessageOut] = Field(default_factory=list)

class SpeechIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)

class CallTurnIn(BaseModel):
    session_id: UUID
    text: str = Field(min_length=1, max_length=12000)

class CallFinishIn(BaseModel):
    duration_seconds: int = Field(default=0, ge=0, le=86400)

class CallTranscriptCorrectIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    alternatives: list[str] = Field(default_factory=list, max_length=6)
    session_id: UUID | None = None

class VisualIdentityCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    category: Literal["sylus", "owner", "other"] = "other"
    notes: str = Field(default="", max_length=2000)

class VisualIdentityUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    status: Literal["confirmed", "pending"] | None = None
    notes: str | None = Field(default=None, max_length=2000)

class ImageGenerateIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=1800)
    caption: str = Field(default='A picture for you.', max_length=300)

class ProactiveSettingsUpdate(BaseModel):
    messages_enabled: bool | None = None
    chance_percent: int | None = Field(default=None, ge=0, le=100)
    max_idle_minutes: int | None = Field(default=None, ge=1, le=1440)


class CallSettingsUpdate(BaseModel):
    calls_enabled: bool | None = None


class PushSubscriptionIn(BaseModel):
    endpoint: str = Field(min_length=20, max_length=3000)
    keys: dict[str, str]


class PushUnsubscribeIn(BaseModel):
    endpoint: str = Field(min_length=20, max_length=3000)


class MemoryCreate(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=4000)
    confidence: float = Field(default=0.9, ge=0, le=1)
    sensitivity: Literal["normal", "sensitive"] = "normal"


class StickerUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=100)
    is_favorite: bool | None = None

class MemoryUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=80)
    content: str | None = Field(default=None, min_length=1, max_length=4000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    sensitivity: Literal["normal", "sensitive"] | None = None

_login_attempts: dict[str, deque[float]] = defaultdict(deque)
_chat_attempts: dict[str, deque[float]] = defaultdict(deque)

@app.post("/v1/session")
def create_owner_session(payload: OwnerLogin, request: Request, response: Response):
    if not settings.sylus_owner_password or not settings.session_secret:
        raise HTTPException(status_code=503, detail="Owner session login is not configured on the server.")
    client_ip = request.client.host if request.client else "unknown"
    attempts = _login_attempts[client_ip]
    now = time()
    while attempts and now - attempts[0] > 900:
        attempts.popleft()
    if len(attempts) >= 5:
        raise HTTPException(status_code=429, detail="Too many login attempts. Wait 15 minutes and try again.")
    if not secrets.compare_digest(payload.password, settings.sylus_owner_password):
        attempts.append(now)
        raise HTTPException(status_code=401, detail="Owner password was not accepted.")
    attempts.clear()
    issued = int(now)
    nonce = secrets.token_urlsafe(24)
    signature = hmac.new(
        settings.session_secret.encode(), f"v1:{issued}:{nonce}".encode(), hashlib.sha256
    ).hexdigest()
    session_value = f"{issued}.{nonce}.{signature}"
    token_hash = hashlib.sha256(session_value.encode()).hexdigest()
    expires_at = datetime.fromtimestamp(issued + settings.session_ttl_seconds, timezone.utc)
    with connection() as conn:
        conn.execute("DELETE FROM owner_sessions WHERE expires_at < now() OR revoked_at IS NOT NULL")
        conn.execute(
            "INSERT INTO owner_sessions (token_hash, expires_at) VALUES (%s, %s)",
            (token_hash, expires_at),
        )
    response.set_cookie(
        key="sylus_session", value=session_value, max_age=settings.session_ttl_seconds,
        httponly=True, secure=settings.app_env.lower() == "production", samesite="lax", path="/",
    )
    return {"authenticated": True, "expires_in": settings.session_ttl_seconds}

@app.delete("/v1/session")
def delete_owner_session(request: Request, response: Response):
    session_value = request.cookies.get("sylus_session")
    if session_value:
        token_hash = hashlib.sha256(session_value.encode()).hexdigest()
        with connection() as conn:
            conn.execute(
                "UPDATE owner_sessions SET revoked_at = now() WHERE token_hash = %s AND revoked_at IS NULL",
                (token_hash,),
            )
    response.delete_cookie(
        key="sylus_session", path="/", httponly=True,
        secure=settings.app_env.lower() == "production", samesite="lax",
    )
    return {"authenticated": False}

@app.get("/health")
def health():
    return {"ok": True, "service": "sylus-api"}

@app.get("/v1/time-context")
def time_context(_: None = Depends(require_owner)):
    """Return current Dhaka-local time and the last time the owner messaged."""
    with connection() as conn:
        row = conn.execute("SELECT created_at FROM messages WHERE role = 'user' AND archived_at IS NULL ORDER BY created_at DESC LIMIT 1").fetchone()
        tz_row = conn.execute("SELECT timezone FROM owner_runtime_context WHERE id = 1").fetchone()
        vision_row = conn.execute("SELECT 1 FROM provider_acceptances WHERE provider = 'cloudflare_meta_vision'").fetchone()
    tz_name = tz_row[0] if tz_row else DEFAULT_TIMEZONE
    try:
        local_zone = ZoneInfo(tz_name)
    except Exception:
        local_zone = ZoneInfo(DEFAULT_TIMEZONE)
        tz_name = DEFAULT_TIMEZONE
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(local_zone)
    n109_local = _n109_clock(now_local)
    last_utc = row[0] if row else None
    last_local = last_utc.astimezone(local_zone) if last_utc else None
    elapsed_seconds = max(0, int((now_utc - last_utc).total_seconds())) if last_utc else None
    return {
        "timezone": tz_name, "now_utc": now_utc.isoformat(), "now_local": now_local.isoformat(),
        "n109_timezone_offset_hours": 2, "n109_local": n109_local.isoformat(),
        "n109_local_time": n109_local.strftime("%A, %Y-%m-%d %H:%M:%S"),
        "n109_daily_rhythm": _n109_daily_rhythm(n109_local.hour),
        "elapsed_since_last_user_message": _elapsed_phrase(elapsed_seconds) if elapsed_seconds is not None else None,
        "local_date": now_local.date().isoformat(), "weekday": now_local.strftime("%A"),
        "local_time": now_local.strftime("%H:%M:%S"),
        "chat_ready": chat_provider_configured(),
        "chat_model": ("Gemini-first free provider pool" if settings.gemini_api_key else "Configured free provider pool" if chat_provider_configured() else None),
        "image_generation_ready": bool(settings.cloudflare_account_id and settings.cloudflare_api_token),
        "voice_ready": bool(settings.elevenlabs_api_key and settings.elevenlabs_voice_id),
        "vision_ready": bool(settings.gemini_api_key or (settings.cloudflare_account_id and settings.cloudflare_api_token and vision_row)),
        "last_user_message_utc": last_utc.isoformat() if last_utc else None,
        "last_user_message_local": last_local.isoformat() if last_local else None,
        "seconds_since_last_user_message": elapsed_seconds,
    }

@app.get("/v1/bond")
def get_relationship_bond(_: None = Depends(require_owner)):
    """Return the persistent relationship snapshot and its earned milestones."""
    return refresh_bond()

@app.get("/v1/visual-memory")
def list_visual_memory(_: None = Depends(require_owner)):
    with connection() as conn:
        rows = conn.execute(
            "SELECT i.id, i.display_name, i.category, i.status, i.notes, i.created_at, "
            "r.id, r.filename, r.source, r.analysis_notes, r.created_at "
            "FROM visual_identities i LEFT JOIN visual_reference_images r ON r.identity_id=i.id "
            "ORDER BY CASE i.category WHEN 'sylus' THEN 0 WHEN 'owner' THEN 1 ELSE 2 END, i.created_at, r.created_at DESC"
        ).fetchall()
    identities = {}
    for row in rows:
        key = str(row[0])
        if key not in identities:
            identities[key] = {
                "id": key, "display_name": row[1], "category": row[2], "status": row[3],
                "notes": row[4], "created_at": row[5].isoformat(), "images": []
            }
        if row[6]:
            identities[key]["images"].append({
                "id": str(row[6]), "filename": row[7], "source": row[8],
                "analysis_notes": row[9], "created_at": row[10].isoformat(),
                "url": f"/v1/visual-memory/images/{row[6]}"
            })
    return list(identities.values())

@app.post("/v1/visual-memory/identities")
def create_visual_identity(payload: VisualIdentityCreate, _: None = Depends(require_owner)):
    with connection() as conn:
        row = conn.execute(
            "INSERT INTO visual_identities (display_name, category, notes, status) VALUES (%s,%s,%s,'confirmed') "
            "RETURNING id, display_name, category, status, notes, created_at",
            (payload.display_name.strip(), payload.category, payload.notes.strip()),
        ).fetchone()
    return {"id":str(row[0]),"display_name":row[1],"category":row[2],"status":row[3],"notes":row[4],"created_at":row[5].isoformat(),"images":[]}

@app.patch("/v1/visual-memory/identities/{identity_id}")
def update_visual_identity(identity_id: UUID, payload: VisualIdentityUpdate, _: None = Depends(require_owner)):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No identity changes supplied.")
    with connection() as conn:
        row = conn.execute(
            "UPDATE visual_identities SET display_name=COALESCE(%s,display_name), status=COALESCE(%s,status), "
            "notes=COALESCE(%s,notes), updated_at=now() WHERE id=%s "
            "RETURNING id,display_name,category,status,notes,created_at",
            (changes.get("display_name"),changes.get("status"),changes.get("notes"),identity_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Visual identity not found.")
    return {"id":str(row[0]),"display_name":row[1],"category":row[2],"status":row[3],"notes":row[4],"created_at":row[5].isoformat()}

@app.delete("/v1/visual-memory/identities/{identity_id}")
def delete_visual_identity(identity_id: UUID, _: None = Depends(require_owner)):
    with connection() as conn:
        row = conn.execute("DELETE FROM visual_identities WHERE id=%s AND category='other' RETURNING id",(identity_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Only additional people can be deleted here; the Sylus and Umi collections are permanent.")
    return {"deleted":True,"id":str(row[0])}

@app.post("/v1/visual-memory/identities/{identity_id}/images")
def upload_visual_reference(identity_id: UUID, file: UploadFile = File(...), _: None = Depends(require_owner)):
    data = file.file.read(8*1024*1024+1)
    if len(data)>8*1024*1024:
        raise HTTPException(status_code=413, detail='Reference images must be 8 MB or smaller.')
    detected = None
    if data.startswith(bytes((255,216,255))): detected=('image/jpeg','jpg')
    elif data.startswith(bytes((137,80,78,71,13,10,26,10))): detected=('image/png','png')
    elif data.startswith(b'RIFF') and data[8:12]==b'WEBP': detected=('image/webp','webp')
    elif data.startswith((b'GIF87a',b'GIF89a')): detected=('image/gif','gif')
    elif len(data)>=12 and data[4:8]==b'ftyp' and data[8:12] in (b'avif',b'avis'): detected=('image/avif','avif')
    elif len(data)>=12 and data[4:8]==b'ftyp' and data[8:12] in (b'heic',b'heix',b'hevc',b'hevx',b'mif1',b'msf1'): detected=('image/heic','heic')
    if not detected: raise HTTPException(status_code=415, detail='Unsupported image format. Use JPG, PNG, WebP, GIF, AVIF, or HEIC.')
    detected_type, extension = detected
    with connection() as conn:
        identity=conn.execute("SELECT display_name,category FROM visual_identities WHERE id=%s",(identity_id,)).fetchone()
        if not identity: raise HTTPException(status_code=404,detail="Visual identity not found.")
        row=conn.execute(
            "INSERT INTO visual_reference_images (identity_id,content_type,filename,data,source) VALUES (%s,%s,%s,%s,'manual') RETURNING id,filename,created_at",
            (identity_id,detected_type,(file.filename or f"reference.{extension}")[:160],data),
        ).fetchone()
        accepted=conn.execute("SELECT 1 FROM provider_acceptances WHERE provider='cloudflare_meta_vision'").fetchone()
    analysis_notes=""
    if detected_type in {'image/jpeg','image/png','image/webp'} and accepted and settings.cloudflare_account_id and settings.cloudflare_api_token:
        try:
            reference_data="data:"+detected_type+";base64,"+base64.b64encode(data).decode("ascii")
            response=httpx.post(
                "https://api.cloudflare.com/client/v4/accounts/"+settings.cloudflare_account_id+"/ai/run/@cf/meta/llama-3.2-11b-vision-instruct",
                headers={"Authorization":f"Bearer {settings.cloudflare_api_token}","Content-Type":"application/json"},
                json={"messages":[{"role":"user","content":[
                    {"type":"text","text":f"This image was manually filed by the owner in the reference collection labelled {identity[0]!r} ({identity[1]}). Describe only visible, non-sensitive appearance details useful for visual continuity: hairstyle and color, clothing, accessories, pose, and overall styling. Do not identify a real person, compare faces, infer who the person is, or infer sensitive traits. Do not guess details that are not visible. Return 2–4 concise factual sentences."},
                    {"type":"image_url","image_url":{"url":reference_data}},
                ]}],"max_tokens":220,"temperature":0.1},
                timeout=60.0,
            )
            response.raise_for_status()
            result=response.json().get("result") or {}
            analysis_notes=result.get("response","") if isinstance(result,dict) else result if isinstance(result,str) else ""
            if analysis_notes:
                with connection() as conn:
                    conn.execute("UPDATE visual_reference_images SET analysis_notes=%s WHERE id=%s",(analysis_notes[:2000],row[0]))
        except (httpx.HTTPError,ValueError,TypeError) as exc:
            logging.info("Visual reference description unavailable identity=%s error=%s",identity_id,type(exc).__name__)
    return {"id":str(row[0]),"filename":row[1],"created_at":row[2].isoformat(),"url":f"/v1/visual-memory/images/{row[0]}","analysis_notes":analysis_notes[:2000]}

@app.get("/v1/visual-memory/images/{image_id}")
def get_visual_reference(image_id: UUID, _: None = Depends(require_owner)):
    with connection() as conn:
        row=conn.execute("SELECT content_type,data FROM visual_reference_images WHERE id=%s",(image_id,)).fetchone()
    if not row: raise HTTPException(status_code=404,detail="Reference image not found.")
    return Response(content=bytes(row[1]),media_type=row[0],headers={"Content-Disposition":"inline","Cache-Control":"no-store, private"})

@app.delete("/v1/visual-memory/images/{image_id}")
def delete_visual_reference(image_id: UUID, _: None = Depends(require_owner)):
    with connection() as conn:
        row=conn.execute("DELETE FROM visual_reference_images WHERE id=%s RETURNING id",(image_id,)).fetchone()
    if not row: raise HTTPException(status_code=404,detail="Reference image not found.")
    return {"deleted":True,"id":str(row[0])}

@app.post("/v1/calls/start")
def start_call_session(_: None = Depends(require_owner)):
    with connection() as conn:
        row=conn.execute("INSERT INTO call_sessions DEFAULT VALUES RETURNING id,started_at",( )).fetchone()
    return {"id":str(row[0]),"started_at":row[1].isoformat()}

@app.get("/v1/calls")
def list_call_sessions(_: None = Depends(require_owner)):
    with connection() as conn:
        rows=conn.execute(
            "SELECT id,started_at,ended_at,duration_seconds,jsonb_array_length(transcript) "
            "FROM call_sessions WHERE ended_at IS NOT NULL ORDER BY started_at DESC LIMIT 50"
        ).fetchall()
    return [{"id":str(r[0]),"started_at":r[1].isoformat(),"ended_at":r[2].isoformat() if r[2] else None,
             "duration_seconds":r[3],"transcript_items":r[4]} for r in rows]

@app.get("/v1/calls/{session_id}/transcript")
def get_call_transcript(session_id: UUID, _: None = Depends(require_owner)):
    with connection() as conn:
        row=conn.execute("SELECT id,started_at,ended_at,duration_seconds,transcript FROM call_sessions WHERE id=%s",(session_id,)).fetchone()
    if not row: raise HTTPException(status_code=404,detail="Call record not found.")
    return {"id":str(row[0]),"started_at":row[1].isoformat(),"ended_at":row[2].isoformat() if row[2] else None,
            "duration_seconds":row[3],"transcript":row[4] or []}

@app.post("/v1/calls/{session_id}/finish")
def finish_call_session(session_id: UUID, payload: CallFinishIn, _: None = Depends(require_owner)):
    with connection() as conn:
        row=conn.execute(
            "UPDATE call_sessions SET ended_at=COALESCE(ended_at,now()), last_activity_at=now(), "
            "duration_seconds=GREATEST(duration_seconds,GREATEST(0,EXTRACT(EPOCH FROM (COALESCE(ended_at,now())-started_at))::int),%s) "
            "WHERE id=%s RETURNING id,started_at,ended_at,duration_seconds",
            (payload.duration_seconds,session_id),
        ).fetchone()
    if not row: raise HTTPException(status_code=404,detail="Call record not found.")
    return {"id":str(row[0]),"started_at":row[1].isoformat(),"ended_at":row[2].isoformat(),"duration_seconds":row[3]}

@app.post("/v1/calls/turn")
def call_turn(payload: CallTurnIn, _: None = Depends(require_owner)):
    spoken = payload.text.strip()
    with connection() as conn:
        session=conn.execute("SELECT transcript,ended_at FROM call_sessions WHERE id=%s",(payload.session_id,)).fetchone()
        if not session: raise HTTPException(status_code=404,detail="Call session not found.")
        if session[1]: raise HTTPException(status_code=409,detail="This call has already ended.")
        transcript=list(session[0] or [])
        anchor=conn.execute(
            "INSERT INTO messages (role,body) VALUES ('system','Private voice-call turn') RETURNING id"
        ).fetchone()
        history_rows=conn.execute(
            "SELECT role,body,created_at,metadata->>'image_context' FROM messages WHERE role IN ('user','assistant') "
            "AND archived_at IS NULL ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
        tz_row=conn.execute("SELECT timezone FROM owner_runtime_context WHERE id=1").fetchone()
    history=[{"role":r[0],"body":r[1][:1600],"created_at":r[2].isoformat(),"image_context":r[3]} for r in reversed(history_rows)]
    for item in transcript[-12:]:
        if item.get("role") in ("user","assistant") and item.get("text"):
            history.append({"role":item["role"],"body":str(item["text"])[:1600],"created_at":item.get("at",""),"image_context":None})
    tz_name=tz_row[0] if tz_row else DEFAULT_TIMEZONE
    apply_spoken_call_boundary(spoken,tz_name)
    call_context=("LIVE VOICE CALL: You are currently speaking with Umi through an active voice call, not exchanging text messages. "
                  "Answer as if you are speaking aloud in real time. Do not say you are texting, messaging, reading a text, or sending text bubbles. "
                  "If she asks whether you can hear her, respond as someone on the active call. Keep spoken replies natural and concise.")
    try:
        answer=generate_reply(spoken,str(anchor[0]),history,time_context=call_context)
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=503,detail=str(exc)) from exc
    except ProviderRequestFailed as exc:
        raise HTTPException(status_code=502,detail=str(exc)) from exc
    bubbles=split_reply_bubbles(answer)
    now_iso=datetime.now(timezone.utc).isoformat()
    additions=[{"role":"user","text":spoken,"at":now_iso}]
    additions.extend({"role":"assistant","text":bubble,"at":now_iso} for bubble in bubbles)
    with connection() as conn:
        conn.execute("UPDATE call_sessions SET transcript=transcript || %s::jsonb, last_activity_at=now() WHERE id=%s",
                     (json.dumps(additions),payload.session_id))
    refresh_bond()
    return {"session_id":str(payload.session_id),"user_text":spoken,"assistant_messages":bubbles,"transcript_additions":additions}

@app.post("/v1/calls/correct-transcript")
def correct_call_transcript(payload: CallTranscriptCorrectIn, _: None = Depends(require_owner)):
    original=payload.text.strip()
    if not original: return {"text":"","changed":False}
    alternatives = [str(item).strip()[:500] for item in payload.alternatives[:6] if str(item).strip()]
    recent_context = ""
    if payload.session_id:
        with connection() as conn:
            row=conn.execute("SELECT transcript FROM call_sessions WHERE id=%s",(payload.session_id,)).fetchone()
        if row:
            recent_context="\n".join(
                f"{item.get('role','')}: {str(item.get('text',''))[:500]}"
                for item in (row[0] or [])[-14:]
            )
    fallback=re.sub(r"\b(silas|sylas|sailas|sailus)\b","Sylus",original,flags=re.I)
    fallback=re.sub(r"\b(hello|hey|hi) silence\b",lambda m:m.group(1)+" Sylus",fallback,flags=re.I)
    providers=[]
    if settings.gemini_api_key:
        providers.append(("Gemini","https://generativelanguage.googleapis.com/v1beta/openai",settings.gemini_api_key,settings.gemini_model))
    if settings.groq_api_key:
        providers.append(("Groq","https://api.groq.com/openai/v1",settings.groq_api_key,settings.groq_model))
    if settings.openrouter_api_key:
        providers.append(("OpenRouter-free","https://openrouter.ai/api/v1",settings.openrouter_api_key,settings.openrouter_model))
    if settings.cloudflare_account_id and settings.cloudflare_api_token:
        providers.append(("Cloudflare",f"https://api.cloudflare.com/client/v4/accounts/{settings.cloudflare_account_id}/ai/v1",settings.cloudflare_api_token,settings.cloudflare_chat_model))
    prompt=("You are a careful speech-recognition repair layer for a live, informal conversation. The input may include the recognizer's best transcript and several alternate hypotheses for the same audio. Compare them using recent conversation context; prefer a candidate that fits the sounds AND context, not merely the most grammatical sentence. "
            "Known names and terms: Sylus (may be misheard as Silas, Sylas, Sailus, or Silence when he is being addressed), Umi, Mephisto, Mephi-chan, N109 Zone, Onychinus, Luke, Kieran, Protocore, Memoria, Within Reach. Preserve these exact spellings when context clearly indicates them. "
            "Correct only likely recognition mistakes, punctuation, and capitalization. Preserve the speaker's actual meaning, casual wording, language, and tone. Do not translate, paraphrase, formalize, complete unfinished thoughts, or invent words. Do not replace a plausible word just because another phrase sounds more natural. If alternatives remain ambiguous, keep the original best transcript. Return only the corrected transcript.")
    for _,base,key,model in providers[:3]:
        try:
            response=httpx.post(base.rstrip("/")+"/chat/completions",
                headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                json={"model":model,"messages":[{"role":"system","content":prompt},{"role":"user","content":("Recent call context (may be empty):\n"+recent_context+"\n\nAlternative recognition hypotheses (same audio; may be empty):\n"+json.dumps(alternatives, ensure_ascii=False)+"\n\nBest transcript to correct:\n"+original)}],
                      "temperature":0,"max_tokens":300},
                timeout=httpx.Timeout(9.0,connect=3.0))
            response.raise_for_status()
            corrected=response.json()["choices"][0]["message"]["content"].strip().strip('"')
            if corrected and len(corrected)<=len(original)*2+100:
                return {"text":corrected,"changed":corrected!=original,"source":"ai"}
        except (httpx.HTTPError,KeyError,IndexError,ValueError,TypeError) as exc:
            logging.info("Call transcript correction provider unavailable (%s).",type(exc).__name__)
    return {"text":fallback,"changed":fallback!=original,"source":"local-fallback"}


@app.get("/v1/messages", response_model=list[MessageOut])
def list_messages(_: None = Depends(require_owner)):
    with connection() as conn:
        rows = conn.execute("SELECT m.id, m.role, m.body, m.created_at, a.id, m.metadata->'attachments' FROM messages m LEFT JOIN media_assets a ON a.message_id = m.id WHERE m.role IN ('user','assistant') AND m.archived_at IS NULL ORDER BY m.created_at ASC, m.ctid ASC").fetchall()
    return [MessageOut(id=str(r[0]), role=r[1], text=r[2], created_at=r[3], media_url=f'/v1/media/{r[4]}' if r[4] else None, attachments=r[5] or []) for r in rows]

@app.delete("/v1/messages")
def reset_active_conversation(_: None = Depends(require_owner)):
    """Start a clean chat while preserving private archived history and saved memories."""
    with connection() as conn:
        rows = conn.execute(
            "UPDATE messages SET archived_at = now(), archive_reason = 'owner_reset_chat' "
            "WHERE archived_at IS NULL AND role IN ('user','assistant') RETURNING id"
        ).fetchall()
    return {"reset": True, "archived_count": len(rows), "memories_preserved": True}

@app.delete("/v1/reset-all")
def erase_all_private_data(_: None = Depends(require_owner)):
    """Permanently erase all conversation messages, attachments, and saved memories."""
    with connection() as conn:
        conn.execute("DELETE FROM media_assets")
        conn.execute("DELETE FROM call_sessions")
        conn.execute("DELETE FROM visual_reference_images")
        conn.execute("DELETE FROM visual_identities WHERE category='other'")
        conn.execute(
            "UPDATE visual_identities SET "
            "display_name=CASE category WHEN 'sylus' THEN 'Sylus' ELSE 'Umi / MC' END, "
            "notes='', status='confirmed', updated_at=now() WHERE category IN ('sylus','owner')"
        )
        conn.execute(
            "UPDATE proactive_contact_settings SET messages_enabled=TRUE, calls_enabled=TRUE, "
            "quiet_start='00:00', quiet_end='00:00', min_idle_minutes=60, min_interval_minutes=15, "
            "last_proactive_at=NULL, last_call_invite_at=NULL, no_call_until=NULL, no_call_reason=NULL, "
            "proactive_cycle_count=0, proactive_pause_until=NULL, updated_at=now() WHERE id=1"
        )
        message_count = conn.execute("DELETE FROM messages RETURNING id").fetchall()
        memory_count = conn.execute("DELETE FROM memories RETURNING id").fetchall()
        conn.execute("DELETE FROM bond_events")
        conn.execute("DELETE FROM emotion_events")
        conn.execute(
            "UPDATE bond_state SET affection=0, trust=0, familiarity=0, shared_experiences=0, "
            "commitment=0, vulnerability=0, emotional_safety=0, consistency=0, bond_points=0, level=1, "
            "stage='A First Encounter', summary='A beginning. Neither of you knows yet what this connection may become.', "
            "milestones='[]'::jsonb, total_user_messages=0, total_shared_turns=0, updated_at=now() WHERE id=1"
        )
        conn.execute(
            "UPDATE emotion_states SET dimensions='{}'::jsonb, dominant_mood='composed', "
            "rationale='Owner reset all private data.', confidence=1, version=version+1, updated_at=now() WHERE id=1"
        )
    return {"erased": True, "messages_deleted": len(message_count), "memories_deleted": len(memory_count), "bond_reset": True, "emotion_reset": True}


@app.post("/v1/messages", response_model=MessageOut)
def save_user_message(payload: MessageIn, _: None = Depends(require_owner)):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Message cannot be blank")
    with connection() as conn:
        row = conn.execute("INSERT INTO messages (role, body) VALUES ('user', %s) RETURNING id, role, body, created_at", (text,)).fetchone()
    return MessageOut(id=str(row[0]), role=row[1], text=row[2], created_at=row[3])

@app.patch("/v1/messages/{message_id}", response_model=ChatTurnOut)
def edit_user_message(message_id: UUID, payload: MessageEdit, request: Request, _: None = Depends(require_owner)):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Message cannot be blank")
    if not chat_provider_configured():
        raise HTTPException(status_code=503, detail="No eligible free chat provider is configured on the private server.")
    with connection() as conn:
        row = conn.execute(
            "SELECT id, body, created_at FROM messages WHERE id = %s AND role = 'user' AND archived_at IS NULL",
            (message_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Your message was not found.")
        conn.execute(
            "INSERT INTO message_revisions (message_id, previous_body, reason) VALUES (%s, %s, 'edited')",
            (message_id, row[1]),
        )
        conn.execute("UPDATE messages SET body = %s, edited_at = now() WHERE id = %s", (text, message_id))
        conn.execute(
            "UPDATE messages SET archived_at = now(), archive_reason = 'superseded_by_edit' "
            "WHERE archived_at IS NULL AND created_at > %s", (row[2],)
        )
        user_row = conn.execute(
            "SELECT id, role, body, created_at FROM messages WHERE id = %s", (message_id,)
        ).fetchone()
        history_rows = conn.execute(
            "SELECT role, body, created_at FROM messages WHERE id <> %s AND role IN ('user','assistant') "
            "AND archived_at IS NULL AND created_at < %s ORDER BY created_at DESC LIMIT 18",
            (message_id, row[2]),
        ).fetchall()
        tz_row = conn.execute("SELECT timezone FROM owner_runtime_context WHERE id = 1").fetchone()
    tz_name = tz_row[0] if tz_row else DEFAULT_TIMEZONE
    try:
        local_zone = ZoneInfo(tz_name)
    except Exception:
        local_zone = ZoneInfo(DEFAULT_TIMEZONE)
        tz_name = DEFAULT_TIMEZONE
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(local_zone)
    time_note = (
        f"Current owner-local time: {now_local.strftime('%A, %Y-%m-%d %H:%M:%S')} ({tz_name}). "
        "The owner edited an earlier message and is continuing the conversation from that point. "
        "Respond directly to the revised message as the next turn."
    )
    history = [{"role": r[0], "body": r[1][:2400], "created_at": r[2].isoformat()} for r in reversed(history_rows)]
    try:
        answer = generate_reply(text, str(user_row[0]), history, time_context=time_note)
    except ProviderNotConfigured as exc:
        with connection() as conn:
            conn.execute("DELETE FROM messages WHERE id = ANY(%s) AND role = 'user'", ([row[0] for row in user_rows],))
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ProviderRequestFailed as exc:
        raise HTTPException(status_code=502, detail="Your edit was saved, but Sylus could not generate a reply. You can send another message to try again.") from exc
    bubbles = split_reply_bubbles(answer)
    with connection() as conn:
        assistant_rows = [
            conn.execute(
                "INSERT INTO messages (role, body) VALUES ('assistant', %s) RETURNING id, role, body, created_at",
                (bubble,),
            ).fetchone()
            for bubble in bubbles
        ]
    assistant_messages = [MessageOut(id=str(r[0]), role=r[1], text=r[2], created_at=r[3]) for r in assistant_rows]
    return ChatTurnOut(
        user_message=MessageOut(id=str(user_row[0]), role=user_row[1], text=user_row[2], created_at=user_row[3]),
        assistant_message=assistant_messages[-1] if assistant_messages else None,
        assistant_messages=assistant_messages,
    )

@app.delete("/v1/messages/{message_id}")
def delete_user_message(message_id: UUID, _: None = Depends(require_owner)):
    with connection() as conn:
        row = conn.execute(
            "SELECT created_at FROM messages WHERE id = %s AND role = 'user' AND archived_at IS NULL",
            (message_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Your message was not found.")
        conn.execute(
            "UPDATE messages SET archived_at = now(), archive_reason = 'after_deleted_message' "
            "WHERE archived_at IS NULL AND (created_at > %s OR created_at = %s)", (row[0], row[0])
        )
        conn.execute("DELETE FROM messages WHERE id = %s", (message_id,))
    return {"deleted": True, "later_messages_archived": True}

@app.post("/v1/messages/{message_id}/rewind")
def rewind_to_message(message_id: UUID, _: None = Depends(require_owner)):
    with connection() as conn:
        row = conn.execute(
            "SELECT role, body, created_at FROM messages WHERE id = %s AND role IN ('user','assistant') AND archived_at IS NULL",
            (message_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="That point in the conversation was not found.")
        archived = conn.execute(
            "UPDATE messages SET archived_at = now(), archive_reason = 'rewound_by_owner' "
            "WHERE archived_at IS NULL AND created_at > %s RETURNING id", (row[2],)
        ).fetchall()
        history_rows = conn.execute(
            "SELECT role, body, created_at FROM messages WHERE archived_at IS NULL AND role IN ('user','assistant') "
            "AND created_at < %s ORDER BY created_at DESC LIMIT 18", (row[2],)
        ).fetchall() if row[0] == "user" else []
        tz_row = conn.execute("SELECT timezone FROM owner_runtime_context WHERE id = 1").fetchone()
    assistant_message = None
    if row[0] == "user":
        if not chat_provider_configured():
            raise HTTPException(status_code=503, detail="No eligible free chat provider is configured on the private server.")
        tz_name = tz_row[0] if tz_row else DEFAULT_TIMEZONE
        try:
            local_zone = ZoneInfo(tz_name)
        except Exception:
            local_zone = ZoneInfo(DEFAULT_TIMEZONE)
            tz_name = DEFAULT_TIMEZONE
        now_local = datetime.now(timezone.utc).astimezone(local_zone)
        time_note = (
            f"Current owner-local time: {now_local.strftime('%A, %Y-%m-%d %H:%M:%S')} ({tz_name}). "
            "The owner rewound the conversation to this message. Respond to it as the next turn."
        )
        history = [{"role": r[0], "body": r[1][:2400], "created_at": r[2].isoformat()} for r in reversed(history_rows)]
        try:
            answer = generate_reply(row[1], str(message_id), history, time_context=time_note)
        except ProviderNotConfigured as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ProviderRequestFailed as exc:
            raise HTTPException(status_code=502, detail="The conversation was rewound, but Sylus could not generate a reply. Try sending another message.") from exc
        bubbles = split_reply_bubbles(answer)
        with connection() as conn:
            created_rows = [
                conn.execute(
                    "INSERT INTO messages (role, body) VALUES ('assistant', %s) RETURNING id, role, body, created_at",
                    (bubble,),
                ).fetchone()
                for bubble in bubbles
            ]
        assistant_messages = [MessageOut(id=str(r[0]), role=r[1], text=r[2], created_at=r[3]) for r in created_rows]
        assistant_message = assistant_messages[-1] if assistant_messages else None
    else:
        assistant_messages = []
        assistant_message = None
    return {"rewound_to": str(message_id), "archived_count": len(archived), "assistant_message": assistant_message, "assistant_messages": assistant_messages}

@app.get("/v1/push/status")
def get_push_status(_: None = Depends(require_owner)):
    configured = bool(settings.web_push_vapid_private_key and settings.web_push_vapid_public_key and settings.web_push_vapid_subject)
    with connection() as conn:
        count = conn.execute("SELECT count(*) FROM push_subscriptions").fetchone()[0]
    return {"configured": configured, "subscribed": count > 0, "subscription_count": count}


@app.get("/v1/push/public-key")
def get_push_public_key(_: None = Depends(require_owner)):
    if not (settings.web_push_vapid_private_key and settings.web_push_vapid_public_key and settings.web_push_vapid_subject):
        raise HTTPException(status_code=503, detail="Push delivery is not configured on the private server yet.")
    return {"public_key": settings.web_push_vapid_public_key}


@app.post("/v1/push/subscribe")
def subscribe_push(payload: PushSubscriptionIn, request: Request, _: None = Depends(require_owner)):
    p256dh, auth = payload.keys.get("p256dh"), payload.keys.get("auth")
    if not p256dh or not auth:
        raise HTTPException(status_code=422, detail="The browser subscription is missing encryption keys.")
    with connection() as conn:
        conn.execute(
            "INSERT INTO push_subscriptions (endpoint, p256dh, auth, user_agent) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (endpoint) DO UPDATE SET p256dh = EXCLUDED.p256dh, auth = EXCLUDED.auth, "
            "user_agent = EXCLUDED.user_agent, updated_at = now()",
            (payload.endpoint, p256dh, auth, request.headers.get("user-agent", "")[:500]),
        )
    return {"subscribed": True}


@app.delete("/v1/push/subscribe")
def unsubscribe_push(payload: PushUnsubscribeIn, _: None = Depends(require_owner)):
    with connection() as conn:
        conn.execute("DELETE FROM push_subscriptions WHERE endpoint = %s", (payload.endpoint,))
    return {"subscribed": False}


def send_push_notification(title: str, body: str, url: str = '/') -> dict[str, int]:
    configured = bool(settings.web_push_vapid_private_key and settings.web_push_vapid_public_key and settings.web_push_vapid_subject)
    if not configured:
        logging.error("Push delivery skipped: VAPID configuration is incomplete.")
        return {"accepted": 0, "failed": 0}
    from pywebpush import webpush, WebPushException
    from py_vapid import Vapid
    private_key_text = settings.web_push_vapid_private_key
    if isinstance(private_key_text, bytes):
        private_key_text = private_key_text.decode("utf-8")
    private_key_text = str(private_key_text).strip().replace("\n", "\n")
    try:
        vapid_key = (
            Vapid.from_pem(private_key_text.encode("utf-8"))
            if "-----BEGIN" in private_key_text
            else Vapid.from_string(private_key_text)
        )
    except Exception as exc:
        logging.error("VAPID private key could not be parsed (%s).", type(exc).__name__)
        return {"accepted": 0, "failed": 1}
    with connection() as conn:
        subscriptions = conn.execute("SELECT endpoint, p256dh, auth FROM push_subscriptions").fetchall()
    if not subscriptions:
        logging.warning("Push delivery skipped: no registered subscriptions.")
        return {"accepted": 0, "failed": 0}
    delivered = 0
    failed = 0
    for endpoint, p256dh, auth in subscriptions:
        subscription = {"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}}
        try:
            webpush(
                subscription_info=subscription,
                data=json.dumps({"title": title, "body": body[:180], "url": url}),
                vapid_private_key=vapid_key,
                vapid_claims={"sub": settings.web_push_vapid_subject},
                ttl=60 * 60 * 12,
            )
            delivered += 1
        except WebPushException as exc:
            failed += 1
            status = getattr(getattr(exc, "response", None), "status_code", None)
            logging.error("Web Push provider rejected a notification (HTTP %s).", status or "unknown")
            if status in (404, 410):
                with connection() as conn:
                    conn.execute("DELETE FROM push_subscriptions WHERE endpoint = %s", (endpoint,))
        except Exception as exc:
            failed += 1
            logging.exception("Web Push delivery failed (%s).", type(exc).__name__)
    logging.info("Web Push attempt finished: %s accepted by provider, %s failed.", delivered, failed)
    return {"accepted": delivered, "failed": failed}


@app.post("/v1/push/test")
def test_push_notification(_: None = Depends(require_owner)):
    if not (settings.web_push_vapid_private_key and settings.web_push_vapid_public_key and settings.web_push_vapid_subject):
        raise HTTPException(status_code=503, detail="Push delivery is not configured.")
    with connection() as conn:
        count = conn.execute("SELECT count(*) FROM push_subscriptions").fetchone()[0]
    if not count:
        raise HTTPException(status_code=409, detail="This device has no registered push subscription. Enable notifications first.")
    result = send_push_notification("Sylus · Test", "If this appeared on your phone, push notifications are working.")
    if result["accepted"] == 0:
        raise HTTPException(status_code=502, detail="The push provider rejected delivery. Check the server logs; no notification was accepted.")
    return {"sent_to_provider": True, "subscription_count": count, **result}

@app.get("/v1/proactive/settings")
def get_proactive_settings(_: None = Depends(require_owner)):
    with connection() as conn:
        row = conn.execute(
            "SELECT messages_enabled, calls_enabled, quiet_start, quiet_end, min_idle_minutes, "
            "min_interval_minutes, timezone, chance_percent, max_idle_minutes "
            "FROM proactive_contact_settings WHERE id = 1"
        ).fetchone()
    return {
        "messages_enabled": bool(row[0]), "calls_enabled": bool(row[1]),
        "quiet_start": row[2].strftime("%H:%M"), "quiet_end": row[3].strftime("%H:%M"),
        "min_idle_minutes": row[4], "min_interval_minutes": row[5], "timezone": row[6],
        "chance_percent": row[7], "max_idle_minutes": row[8],
    }


@app.patch("/v1/proactive/settings")
def update_proactive_settings(payload: ProactiveSettingsUpdate, _: None = Depends(require_owner)):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No proactive settings supplied.")
    allowed = {key: value for key, value in changes.items()
               if key in {"messages_enabled", "chance_percent", "max_idle_minutes"}}
    if allowed:
        assignments = ", ".join(f"{key} = %s" for key in allowed)
        with connection() as conn:
            conn.execute(
                f"UPDATE proactive_contact_settings SET {assignments}, updated_at = now() WHERE id = 1",
                tuple(allowed.values()),
            )
    return get_proactive_settings(None)


@app.get("/v1/calls/settings")
def get_call_settings(_: None = Depends(require_owner)):
    with connection() as conn:
        row = conn.execute(
            "SELECT calls_enabled, no_call_until, no_call_reason, quiet_start, quiet_end, timezone "
            "FROM proactive_contact_settings WHERE id = 1"
        ).fetchone()
    until = row[1].astimezone(timezone.utc).isoformat() if row[1] else None
    return {
        "calls_enabled": bool(row[0]), "no_call_until": until, "no_call_reason": row[2],
        "quiet_start": row[3].strftime("%H:%M"), "quiet_end": row[4].strftime("%H:%M"),
        "timezone": row[5],
    }


@app.patch("/v1/calls/settings")
def update_call_settings(payload: CallSettingsUpdate, _: None = Depends(require_owner)):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No call settings supplied.")
    if "calls_enabled" in changes:
        with connection() as conn:
            conn.execute(
                "UPDATE proactive_contact_settings SET calls_enabled = %s, updated_at = now() WHERE id = 1",
                (changes["calls_enabled"],),
            )
    return get_call_settings(None)


def apply_spoken_call_boundary(text: str, timezone_name: str) -> None:
    """Persist natural-language call pauses or an explicit permission to resume calls."""
    value = (text or "").strip().lower()
    if not value:
        return
    resume = any(phrase in value for phrase in (
        "you can call again", "call me again", "call me now", "you can call now", "you may call me", "calls are okay again",
        "it's okay to call", "it is okay to call", "i'm okay with calls", "im okay with calls",
        "allow calls again", "resume calls",
    ))
    if resume:
        with connection() as conn:
            conn.execute(
                "UPDATE proactive_contact_settings SET no_call_until = NULL, no_call_reason = NULL, updated_at = now() WHERE id = 1"
            )
        return
    deny = any(phrase in value for phrase in (
        "don't call", "dont call", "do not call", "no calls", "stop calling",
        "don't phone", "dont phone", "do not phone", "no phone calls", "no voice calls", "don't ring", "do not ring", "not call me",
    ))
    if not deny:
        return
    try:
        zone = ZoneInfo(timezone_name or DEFAULT_TIMEZONE)
    except Exception:
        zone = ZoneInfo(DEFAULT_TIMEZONE)
    now_local = datetime.now(timezone.utc).astimezone(zone)
    until = None
    reason = "Umi asked Sylus not to call until she explicitly allows it again."
    if "tomorrow" in value:
        from datetime import time as clock_time, timedelta
        tomorrow = now_local.date() + timedelta(days=1)
        until = datetime.combine(tomorrow, clock_time(23, 59, 59), tzinfo=zone)
        reason = "Umi asked for no calls tomorrow."
    elif any(word in value for word in ("today", "tonight", "for now", "right now", "now")):
        from datetime import time as clock_time, timedelta
        if "for now" in value or "right now" in value or value.endswith(" now"):
            until = now_local + timedelta(hours=2)
            reason = "Umi asked for a temporary pause on calls."
        else:
            until = datetime.combine(now_local.date(), clock_time(23, 59, 59), tzinfo=zone)
            reason = "Umi asked for no calls today."
    else:
        import re
        from datetime import timedelta
        duration = re.search(r"for\s+(\d+)\s*(hours?|hrs?|minutes?|mins?|days?)", value)
        if duration:
            amount = int(duration.group(1))
            unit = duration.group(2)
            seconds = amount * (86400 if unit.startswith("day") else 3600 if unit.startswith(("hour", "hr")) else 60)
            until = now_local + timedelta(seconds=seconds)
            reason = f"Umi asked for no calls for {amount} {unit}."
        else:
            clock = re.search(r"until\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", value)
            if clock:
                from datetime import time as clock_time, timedelta
                hour, minute = int(clock.group(1)), int(clock.group(2) or 0)
                suffix = clock.group(3)
                if suffix == "pm" and hour < 12: hour += 12
                if suffix == "am" and hour == 12: hour = 0
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    candidate = datetime.combine(now_local.date(), clock_time(hour, minute), tzinfo=zone)
                    until = candidate if candidate > now_local else candidate + timedelta(days=1)
                    reason = f"Umi asked for no calls until {hour:02d}:{minute:02d}."
    with connection() as conn:
        conn.execute(
            "UPDATE proactive_contact_settings SET no_call_until = %s, no_call_reason = %s, updated_at = now() WHERE id = 1",
            (until, reason),
        )


def proactive_contact_decision(
    now_utc: datetime,
    last_activity: datetime,
    last_proactive_at: datetime | None,
    cycle_count: int,
    pause_until: datetime | None,
    min_idle_minutes: int = 0,
    min_interval_minutes: int = 0,
    max_idle_minutes: int = 60,
    chance_percent: int = 50,
    random_value: float | None = None,
) -> dict:
    """Probabilistic contact within a bounded window; max inactivity is a hard deadline."""
    idle_minutes = max(0.0, (now_utc - last_activity).total_seconds() / 60)
    owner_replied = last_proactive_at is None or last_activity > last_proactive_at
    count = 0 if owner_replied else cycle_count
    pause = None if owner_replied else pause_until
    is_followup = not owner_replied
    since_last_contact = idle_minutes if owner_replied or not last_proactive_at else max(
        0.0, (now_utc - last_proactive_at).total_seconds() / 60
    )

    if idle_minutes < min_idle_minutes:
        return {"due": False, "reason": "owner_recently_active", "is_followup": False,
                "cycle_count": count, "pause_until": pause, "idle_minutes": idle_minutes}
    if pause and pause > now_utc:
        return {"due": False, "reason": "cycle_pause", "is_followup": True,
                "cycle_count": count, "pause_until": pause, "idle_minutes": idle_minutes}
    if pause and pause <= now_utc:
        count, pause, is_followup = 0, None, True
    if is_followup and last_proactive_at:
        if count >= 3:
            pause = last_proactive_at + timedelta(hours=1)
            if pause > now_utc:
                return {"due": False, "reason": "cycle_pause", "is_followup": True,
                        "cycle_count": count, "pause_until": pause, "idle_minutes": idle_minutes}
            count, pause = 0, None
        if (now_utc - last_proactive_at).total_seconds() < min_interval_minutes * 60:
            return {"due": False, "reason": "followup_spacing", "is_followup": True,
                    "cycle_count": count, "pause_until": pause, "idle_minutes": idle_minutes}
    forced = since_last_contact >= max_idle_minutes
    draw = random.random() if random_value is None else random_value
    if not forced and draw >= max(0, min(100, chance_percent)) / 100:
        return {"due": False, "reason": "chance_not_met", "is_followup": is_followup,
                "cycle_count": count, "pause_until": pause, "idle_minutes": idle_minutes}
    return {"due": True, "reason": "maximum_inactivity_reached" if forced else
            ("followup_due" if is_followup else "initial_message_due"),
            "is_followup": is_followup, "cycle_count": count, "pause_until": pause,
            "idle_minutes": idle_minutes}


@app.post("/v1/proactive/poll")
def poll_proactive_messages(_: None = Depends(require_owner)):
    """Start after the idle threshold, send spaced follow-ups, then pause for an hour."""
    now_utc = datetime.now(timezone.utc)
    with connection() as conn:
        row = conn.execute(
            "SELECT messages_enabled, min_idle_minutes, min_interval_minutes, timezone, "
            "last_proactive_at, proactive_cycle_count, proactive_pause_until, max_idle_minutes, chance_percent "
            "FROM proactive_contact_settings WHERE id = 1 FOR UPDATE"
        ).fetchone()
        if not row or not row[0]:
            return {"sent": False, "reason": "disabled", "messages": []}
        conn.execute(
            "UPDATE call_sessions SET ended_at=last_activity_at, "
            "duration_seconds=GREATEST(duration_seconds,EXTRACT(EPOCH FROM (last_activity_at-started_at))::int) "
            "WHERE ended_at IS NULL AND last_activity_at < now()-interval '2 hours'"
        )
        active_call = conn.execute(
            "SELECT 1 FROM call_sessions WHERE ended_at IS NULL AND last_activity_at >= now()-interval '2 hours' LIMIT 1"
        ).fetchone()
        if active_call:
            return {"sent": False, "reason": "voice_call_in_progress", "messages": []}
        last_user = conn.execute(
            "SELECT EXISTS(SELECT 1 FROM messages WHERE role='user' AND archived_at IS NULL) "
            "OR EXISTS(SELECT 1 FROM call_sessions WHERE transcript @> '[{\"role\":\"user\"}]'::jsonb)"
        ).fetchone()
        last_activity = conn.execute(
            "SELECT GREATEST("
            "COALESCE((SELECT max(created_at) FROM messages WHERE role IN ('user','assistant') AND archived_at IS NULL "
            "AND COALESCE(metadata->>'proactive','false') <> 'true'), '-infinity'::timestamptz), "
            "COALESCE((SELECT max(last_activity_at) FROM call_sessions), '-infinity'::timestamptz))"
        ).fetchone()
        if not last_user or not last_user[0] or not last_activity or not last_activity[0]:
            return {"sent": False, "reason": "no_conversation", "messages": []}

        decision = proactive_contact_decision(
            now_utc, last_activity[0], row[4], int(row[5] or 0), row[6],
            int(row[1] or 0), int(row[2] or 0), int(row[7] or 60), int(row[8] if row[8] is not None else 50),
        )
        if not decision["due"]:
            if decision["cycle_count"] != int(row[5] or 0) or decision["pause_until"] != row[6]:
                conn.execute(
                    "UPDATE proactive_contact_settings SET proactive_cycle_count=%s, "
                    "proactive_pause_until=%s, updated_at=now() WHERE id=1",
                    (decision["cycle_count"], decision["pause_until"]),
                )
            return {"sent": False, "reason": decision["reason"], "messages": []}

        # Reserve this slot before generation so foreground/background polls cannot duplicate it.
        conn.execute(
            "UPDATE proactive_contact_settings SET last_proactive_at=%s, "
            "proactive_cycle_count=%s, proactive_pause_until=%s, updated_at=now() WHERE id=1",
            (now_utc, decision["cycle_count"], decision["pause_until"]),
        )
        tz_name = row[3] or DEFAULT_TIMEZONE
        try:
            local_zone = ZoneInfo(tz_name)
        except Exception:
            local_zone = ZoneInfo(DEFAULT_TIMEZONE)
            tz_name = DEFAULT_TIMEZONE
        local_now = now_utc.astimezone(local_zone)
        n109_now = _n109_clock(now_local)
        rhythm = _n109_daily_rhythm(n109_now.hour)
        history_rows = conn.execute(
            "SELECT role, body, created_at, metadata->>'image_context' "
            "FROM messages WHERE role IN ('user','assistant') "
            "AND archived_at IS NULL ORDER BY created_at DESC LIMIT 18"
        ).fetchall()
    history = [
        {"role": r[0], "body": r[1][:1800], "created_at": r[2].isoformat(), "image_context": r[3]}
        for r in reversed(history_rows)
    ]
    idle_seconds = int(decision["idle_minutes"] * 60)
    idle_phrase = _elapsed_phrase(idle_seconds)
    contact_note = (
        f"Umi has been away from the conversation for {idle_phrase} (about {int(decision['idle_minutes'])} minutes). "
        + ("You have already sent a message since her last reply. This is a separate follow-up; "
           "do not repeat yourself or pressure her.\n" if decision["is_followup"] else
           "This is your opportunity to initiate a conversation naturally.\n")
        + ("If it feels natural, you may gently acknowledge that she has been quiet for half an hour or longer "
           "(perhaps she is busy or has fallen asleep). Keep it affectionate or lightly teasing, never accusatory, "
           "possessive, or guilt-inducing. Do not imply she owes you a reply.\n" if decision["idle_minutes"] >= 30 else "")
    )
    time_note = (
        f"Current owner-local time: {local_now.strftime('%A, %Y-%m-%d %H:%M:%S')} ({tz_name}). "
        f"Simulated N109 clock: {n109_now.strftime('%A, %Y-%m-%d %H:%M')} (exactly two hours ahead of Umi's local clock; private fictional continuity, not official canon). "
        f"Possible N109 daily rhythm at this hour: {rhythm}. This is atmosphere, not a report of a specific event. "
        "The two worlds have separate clocks. Reach out naturally, in your own voice. " + contact_note
    )
    try:
        bubbles = generate_proactive_bubbles(history, time_context=time_note)[:1]
    except (ProviderNotConfigured, ProviderRequestFailed):
        return {"sent": False, "reason": "generation_unavailable", "messages": []}
    if not bubbles:
        return {"sent": False, "reason": "nothing_natural_to_say", "messages": []}
    with connection() as conn:
        created_rows = [
            conn.execute(
                "INSERT INTO messages (role, body, metadata) VALUES ('assistant', %s, %s::jsonb) "
                "RETURNING id, role, body, created_at",
                (bubble, json.dumps({"proactive": True})),
            ).fetchone()
            for bubble in bubbles
        ]
        if decision["is_followup"]:
            next_count = min(3, decision["cycle_count"] + 1)
            next_pause = now_utc + timedelta(hours=1) if next_count >= 3 else None
        else:
            next_count, next_pause = 0, None
        conn.execute(
            "UPDATE proactive_contact_settings SET proactive_cycle_count=%s, "
            "proactive_pause_until=%s, updated_at=now() WHERE id=1",
            (next_count, next_pause),
        )
    messages = [MessageOut(id=str(r[0]), role=r[1], text=r[2], created_at=r[3]) for r in created_rows]
    push_result = send_push_notification("Sylus", bubbles[0])
    logging.info(
        "Proactive message saved; followup_count=%s pause_until=%s push_accepted=%s push_failed=%s.",
        next_count, next_pause.isoformat() if next_pause else None,
        push_result.get("accepted", 0), push_result.get("failed", 0),
    )
    return {"sent": True, "messages": messages, "push": push_result}

def poll_proactive_call_invite(*, allow_foreground: bool = False) -> dict:
    """Offer spontaneous calls; foreground tabs can receive invites without push setup."""
    now_utc = datetime.now(timezone.utc)
    with connection() as conn:
        row = conn.execute(
            "SELECT calls_enabled, no_call_until, no_call_reason, last_call_invite_at "
            "FROM proactive_contact_settings WHERE id = 1 FOR UPDATE"
        ).fetchone()
        if not row or not row[0]:
            return {"sent": False, "reason": "calls_disabled"}
        no_call_until = row[1]
        if row[2] and not no_call_until:
            return {"sent": False, "reason": "owner_requested_no_calls", "detail": row[2]}
        if no_call_until and no_call_until > now_utc:
            return {"sent": False, "reason": "owner_requested_no_calls", "until": no_call_until.isoformat(), "detail": row[2]}
        if no_call_until and no_call_until <= now_utc:
            conn.execute(
                "UPDATE proactive_contact_settings SET no_call_until=NULL, no_call_reason=NULL WHERE id=1"
            )
        active_call = conn.execute(
            "SELECT 1 FROM call_sessions WHERE ended_at IS NULL AND last_activity_at >= now()-interval '2 hours' LIMIT 1"
        ).fetchone()
        if active_call:
            return {"sent": False, "reason": "voice_call_in_progress"}
        subscriptions = conn.execute("SELECT count(*) FROM push_subscriptions").fetchone()[0]
        if not subscriptions and not allow_foreground:
            return {"sent": False, "reason": "no_push_subscription"}
        last_invite = row[3]
        if last_invite:
            elapsed_seconds = max(0.0, (now_utc - last_invite).total_seconds())
        else:
            last_activity = conn.execute(
                "SELECT GREATEST(COALESCE((SELECT max(created_at) FROM messages WHERE role IN ('user','assistant') "
                "AND archived_at IS NULL AND COALESCE(metadata->>'proactive','false') <> 'true'), '-infinity'::timestamptz), "
                "COALESCE((SELECT max(last_activity_at) FROM call_sessions), '-infinity'::timestamptz))"
            ).fetchone()[0]
            elapsed_seconds = max(0.0, (now_utc - last_activity).total_seconds()) if last_activity else 0.0
        # Roughly one spontaneous call invitation per day on average.
        # This is a probability, not a cooldown or a clock-based restriction.
        chance = 1.0 - math.exp(-elapsed_seconds / (24 * 60 * 60))
        conn.execute(
            "UPDATE proactive_contact_settings SET last_call_invite_at=%s, updated_at=now() WHERE id=1",
            (now_utc,),
        )
        if random.random() >= chance:
            return {"sent": False, "reason": "no_call_impulse"}
    result = send_push_notification(
        "Sylus is calling",
        "A moment for just us? Tap to open the private voice channel.",
        url="/?incoming-call=1",
    ) if subscriptions else {"accepted": 0, "failed": 0}
    if result.get("accepted", 0) > 0:
        logging.info("Sylus call invitation accepted by %s push provider(s).", result["accepted"])
        return {"sent": True, "accepted": result["accepted"], "delivery": "push"}
    if allow_foreground:
        logging.info("Sylus call invitation delivered to the active foreground session.")
        return {"sent": True, "accepted": 0, "delivery": "foreground"}
    return {"sent": False, "reason": "push_delivery_failed", **result}


@app.post("/v1/proactive/call-poll")
def owner_poll_proactive_call(_: None = Depends(require_owner)):
    """Foreground call invitation check; the active tab can receive it without push."""
    return poll_proactive_call_invite(allow_foreground=True)


@app.post("/internal/proactive/run")
def scheduled_proactive_messages(authorization: str | None = Header(default=None)):
    """Authenticated scheduler entry point; the same safeguards as the owner poll still apply."""
    if not settings.scheduler_secret:
        raise HTTPException(status_code=503, detail="The background scheduler is not configured.")
    expected = f"Bearer {settings.scheduler_secret}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Scheduler authentication failed.")
    call_result = poll_proactive_call_invite()
    message_result = ({"sent": False, "reason": "call_invitation_sent", "messages": []}
                      if call_result.get("sent") else poll_proactive_messages(None))
    return {"messages": message_result, "call_invitation": call_result}


@app.post("/v1/voice/speech")
def create_speech(payload: SpeechIn, _: None = Depends(require_owner)):
    if not (settings.elevenlabs_api_key and settings.elevenlabs_voice_id):
        raise HTTPException(status_code=503, detail="Voice playback is not configured. Add an ElevenLabs API key and your designed voice ID in the private server settings.")
    emotion = load_emotion_state()
    # Let the persisted simulated affect gently colour the voice without caricature.
    stability = 0.55
    style = 0.22
    if emotion.playfulness >= 0.30 or emotion.amusement >= 0.35 or emotion.surprise >= 0.35:
        stability, style = 0.43, 0.38
    if emotion.affection >= 0.38 or emotion.longing >= 0.30:
        stability, style = 0.48, max(style, 0.30)
    if emotion.concern >= 0.38:
        stability, style = 0.58, 0.18
    if emotion.anger >= 0.35 or emotion.irritation >= 0.45:
        stability, style = 0.68, 0.12
    try:
        response = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}?output_format=mp3_44100_128",
            headers={"xi-api-key": settings.elevenlabs_api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
            json={"text": payload.text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": stability, "similarity_boost": 0.72, "style": style, "use_speaker_boost": True}},
            timeout=60.0,
        )
        response.raise_for_status()
        audio_bytes = response.content
        content_type = response.headers.get("content-type", "").lower()
        is_mp3 = audio_bytes.startswith(b"ID3") or (
            len(audio_bytes) > 2 and audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0
        )
        logging.info("Voice provider response: content_type=%s bytes=%s mp3_signature=%s", content_type, len(audio_bytes), is_mp3)
        if not audio_bytes or len(audio_bytes) < 256 or not (content_type.startswith("audio/") or is_mp3) or not is_mp3:
            logging.error("Voice provider returned unusable audio: content_type=%s bytes=%s prefix=%s", content_type, len(audio_bytes), audio_bytes[:32].hex())
            raise HTTPException(status_code=502, detail="The voice provider returned an empty or invalid audio stream. Check the voice ID, provider response, and usage allowance.")
        # Normalize to a finalized, broadly supported MP3 file. Use a seekable
        # temporary file rather than stdout so the encoder can write complete headers.
        mp3_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as mp3_file:
                mp3_path = mp3_file.name
            normalized = subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "mp3", "-i", "pipe:0",
                 "-vn", "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "44100", "-ac", "1", "-f", "mp3", mp3_path],
                input=audio_bytes, capture_output=True, timeout=25, check=False,
            )
            if normalized.returncode != 0:
                logging.error("Voice audio normalization failed: exit=%s stderr=%s", normalized.returncode, normalized.stderr[:300].decode("utf-8", "replace"))
                raise HTTPException(status_code=502, detail="The voice provider returned audio, but it could not be prepared for playback. Please try again.")
            audio_bytes = Path(mp3_path).read_bytes()
            is_normalized_mp3 = audio_bytes.startswith(b"ID3") or (
                len(audio_bytes) > 2 and audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0
            )
            if len(audio_bytes) < 256 or not is_normalized_mp3:
                logging.error("Voice audio normalization produced an invalid MP3 file: bytes=%s prefix=%s", len(audio_bytes), audio_bytes[:16].hex())
                raise HTTPException(status_code=502, detail="The voice provider returned audio, but it could not be prepared for playback. Please try again.")
            logging.info("Voice audio normalized to finalized MP3 file: bytes=%s prefix=%s", len(audio_bytes), audio_bytes[:8].hex())
        finally:
            if mp3_path:
                try:
                    os.unlink(mp3_path)
                except FileNotFoundError:
                    pass
    except subprocess.TimeoutExpired as exc:
        logging.error("Voice audio normalization timed out.")
        raise HTTPException(status_code=504, detail="The generated voice took too long to prepare. Please try again.") from exc
    except httpx.HTTPError as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        logging.error("ElevenLabs speech request failed (HTTP %s): %s", status or "unknown", str(exc)[:300])
        raise HTTPException(status_code=502, detail="The voice provider could not generate audio. Check the private voice configuration and usage allowance.") from exc
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-store, private",
            "Content-Disposition": 'inline; filename="sylus-message.mp3"',
            "Content-Length": str(len(audio_bytes)),
            "Accept-Ranges": "bytes",
        },
    )

@app.post("/v1/vision/accept-license")
def accept_vision_license(_: None = Depends(require_owner)):
    if not (settings.cloudflare_account_id and settings.cloudflare_api_token):
        raise HTTPException(status_code=503, detail="Configure the Cloudflare AI credentials first.")
    try:
        response = httpx.post(
            "https://api.cloudflare.com/client/v4/accounts/" + settings.cloudflare_account_id + "/ai/run/@cf/meta/llama-3.2-11b-vision-instruct",
            headers={"Authorization": f"Bearer {settings.cloudflare_api_token}", "Content-Type": "application/json"},
            json={"prompt": "agree"}, timeout=60.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not register the vision-model license acceptance.") from exc
    with connection() as conn:
        conn.execute("INSERT INTO provider_acceptances (provider) VALUES ('cloudflare_meta_vision') ON CONFLICT (provider) DO NOTHING")
    return {"vision_ready": True}

def _analyze_uploaded_image(asset_id: UUID, image_bytes: bytes, content_type: str, message_id: UUID) -> bool:
    """Analyze the actual uploaded pixels on the server, independent of frontend behavior."""
    with connection() as conn:
        accepted = conn.execute("SELECT 1 FROM provider_acceptances WHERE provider = 'cloudflare_meta_vision'").fetchone()
        history_rows = conn.execute(
            "SELECT role, body, created_at, metadata->>'image_context' FROM messages WHERE id <> %s AND role IN ('user','assistant') "
            "AND archived_at IS NULL ORDER BY created_at DESC LIMIT 18", (message_id,),
        ).fetchall()
    # Compare the uploaded pixels only with the owner's labelled fictional Sylus
    # references. No face recognition is performed on Umi or other real people.
    with connection() as conn:
        sylus_refs = conn.execute(
            "SELECT r.content_type, r.data FROM visual_reference_images r "
            "JOIN visual_identities i ON i.id=r.identity_id "
            "WHERE i.category='sylus' AND i.status='confirmed' ORDER BY r.created_at DESC LIMIT 8"
        ).fetchall()

    vision_instruction = (
        "You are a careful visual-understanding system for a private Sylus companion. "
        "The FIRST image is newly shared. Every later image is an owner-approved reference "
        "of the fictional character Sylus from Love and Deepspace. Compare the new image "
        "against ALL references, prioritizing stable facial design, eye shape and crimson "
        "iris color, hairstyle silhouette and silver-white tone, facial proportions, and "
        "recognizable game-render styling. Hair color or red eyes alone are not enough. "
        "Return concise labelled plain text, not JSON. Describe the actual subject, "
        "composition, pose, expression, clothes, accessories, exact colors, lighting and "
        "background. Say 'Character identification: Sylus (strong visual match)' only when "
        "several distinctive features match; otherwise say 'possibly Sylus' or "
        "'not Sylus / no reliable match' and explain briefly. Do not invent unseen details. "
        "Do not identify Umi or any real person by face. Separate observations from guesses."
    )
    visual_description = ""
    vision_failures = []

    # Gemini Flash is the primary reader: multimodal comparison against the saved
    # reference set, rather than relying on a short text-only appearance prompt.
    if settings.gemini_api_key:
        try:
            parts = [
                {"text": vision_instruction},
                {"inline_data": {"mime_type": content_type, "data": base64.b64encode(image_bytes).decode("ascii")}},
            ]
            for ref_type, ref_bytes in sylus_refs:
                if ref_type not in {"image/jpeg", "image/png", "image/webp"}:
                    continue
                parts.append({"text": "Owner-approved Sylus reference image."})
                parts.append({"inline_data": {"mime_type": ref_type, "data": base64.b64encode(bytes(ref_bytes)).decode("ascii")}})
            vision_response = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_vision_model}:generateContent",
                params={"key": settings.gemini_api_key},
                headers={"Content-Type": "application/json"},
                json={"contents": [{"role": "user", "parts": parts}],
                      "generationConfig": {"temperature": 0.1, "maxOutputTokens": 900}},
                timeout=90.0,
            )
            vision_response.raise_for_status()
            candidates = vision_response.json().get("candidates") or []
            candidate_parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
            visual_description = "\n".join(str(part.get("text", "")) for part in candidate_parts if part.get("text"))
            if not visual_description.strip():
                raise ValueError("Gemini vision returned no description.")
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            vision_failures.append(f"Gemini:{type(exc).__name__}")
            logging.warning("Gemini image understanding unavailable asset=%s error=%s", asset_id, type(exc).__name__)

    # Preserve the accepted Cloudflare vision model as a fallback.
    if not visual_description.strip() and accepted and settings.cloudflare_account_id and settings.cloudflare_api_token:
        try:
            content = [
                {"type": "text", "text": vision_instruction},
                {"type": "image_url", "image_url": {"url": "data:" + content_type + ";base64," + base64.b64encode(image_bytes).decode("ascii")}},
            ]
            for ref_type, ref_bytes in sylus_refs:
                if ref_type not in {"image/jpeg", "image/png", "image/webp"}:
                    continue
                content.extend([
                    {"type": "text", "text": "Owner-approved Sylus reference image."},
                    {"type": "image_url", "image_url": {"url": "data:" + ref_type + ";base64," + base64.b64encode(bytes(ref_bytes)).decode("ascii")}},
                ])
            vision_response = httpx.post(
                "https://api.cloudflare.com/client/v4/accounts/" + settings.cloudflare_account_id + "/ai/run/@cf/meta/llama-3.2-11b-vision-instruct",
                headers={"Authorization": "Bearer " + settings.cloudflare_api_token, "Content-Type": "application/json"},
                json={"messages": [{"role": "user", "content": content}], "max_tokens": 900, "temperature": 0.1},
                timeout=90.0,
            )
            vision_response.raise_for_status()
            result = vision_response.json().get("result") or {}
            visual_description = result.get("response", "") if isinstance(result, dict) else result if isinstance(result, str) else ""
            if not visual_description.strip():
                raise ValueError("Cloudflare vision returned no description.")
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            vision_failures.append(f"Cloudflare:{type(exc).__name__}")

    if not visual_description.strip():
        logging.error("Automatic image analysis failed asset=%s providers=%s", asset_id, vision_failures or ["not_configured"])
        return False

    with connection() as conn:
        conn.execute(
            "UPDATE messages SET metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object('image_context', %s::text, 'image_analysis_status', 'complete') WHERE id = %s",
            (visual_description[:3500], message_id),
        )
        # Keep useful image examples in the private library. Sylus matches are filed
        # under his fictional-character collection; other people remain pending until
        # the owner supplies a name. No real-person face recognition is performed.
        if "Character identification: Sylus (strong visual match)." in visual_description:
            identity = conn.execute("SELECT id FROM visual_identities WHERE category='sylus' LIMIT 1").fetchone()
            if identity:
                conn.execute(
                    "INSERT INTO visual_reference_images (identity_id,content_type,filename,data,source,analysis_notes) "
                    "VALUES (%s,%s,'auto-sylus-reference',%s,'auto',%s)",
                    (identity[0],content_type,image_bytes,visual_description[:2000]),
                )
        elif re.search(r"\b(person|man|woman|people|human|character)\b", visual_description, re.I):
            identity = conn.execute(
                "INSERT INTO visual_identities (display_name,category,status,notes) "
                "VALUES (%s,'other','pending',%s) RETURNING id",
                ("Unidentified person · " + datetime.now(timezone.utc).strftime("%Y-%m-%d"), visual_description[:1500]),
            ).fetchone()
            conn.execute(
                "INSERT INTO visual_reference_images (identity_id,content_type,filename,data,source,analysis_notes) "
                "VALUES (%s,%s,'auto-unidentified-reference',%s,'auto',%s)",
                (identity[0],content_type,image_bytes,visual_description[:2000]),
            )
        history_rows = conn.execute(
            "SELECT role, body, created_at, metadata->>'image_context' FROM messages WHERE id <> %s AND role IN ('user','assistant') "
            "AND archived_at IS NULL ORDER BY created_at DESC LIMIT 18", (message_id,),
        ).fetchall()
    history = [
        {"role": row[0], "body": row[1][:1800], "created_at": row[2].isoformat(), "image_context": row[3]}
        for row in reversed(history_rows)
    ]
    user_text = (
        "Umi has just shared an image. Your private visual observations from the actual pixels are below. "
        "Use them as reliable evidence, but do not recite them as a caption. Treat this as a social gesture from someone you know, not an alt-text assignment. If notes identify a strong visual match for Sylus, recognise yourself naturally in first person and react with fitting amusement, smugness, surprise, or curiosity; do not mistake the depicted Sylus for Umi or claim she is pictured. If the notes say possibly Sylus, ask whether she means you rather than pretending certainty. If the image's purpose is unclear, react to the gesture and naturally ask what made her think to show it to you. "
        "If she asks what something is, answer from the observations and admit uncertainty rather than guessing.\n\n"
        + visual_description[:3500]
    )
    try:
        answer = generate_reply(user_text, str(message_id), history, time_context="Umi has just shared an image in the current conversation.")
        bubbles = split_reply_bubbles(answer)
        if not bubbles:
            logging.warning("Vision analysis returned no conversational reply asset=%s", asset_id)
            return False
        with connection() as conn:
            for bubble in bubbles:
                conn.execute("INSERT INTO messages (role, body) VALUES ('assistant', %s)", (bubble,))
        logging.info("Automatic image analysis and reaction completed asset=%s notes_chars=%s bubbles=%s", asset_id, len(visual_description), len(bubbles))
    except (ProviderRequestFailed, ProviderNotConfigured) as exc:
        logging.warning("Image was analyzed and saved, but Sylus could not generate a reaction asset=%s error=%s", asset_id, str(exc)[:300])
        return False
    return True


@app.post("/v1/media/{asset_id}/discuss")
def discuss_uploaded_image(asset_id: UUID, _: None = Depends(require_owner)):
    with connection() as conn:
        asset = conn.execute(
            "SELECT a.data, a.content_type, a.message_id FROM media_assets a JOIN messages m ON m.id = a.message_id "
            "WHERE a.id = %s AND m.archived_at IS NULL", (asset_id,),
        ).fetchone()
        if not asset:
            raise HTTPException(status_code=404, detail="Image not found.")
        existing = conn.execute("SELECT metadata->>'image_context' FROM messages WHERE id = %s", (asset[2],)).fetchone()
    if existing and existing[0]:
        return {"assistant_messages": []}
    completed = _analyze_uploaded_image(asset_id, bytes(asset[0]), asset[1], asset[2])
    if not completed:
        raise HTTPException(status_code=503, detail="Sylus could not inspect this image. Check that image understanding is enabled in Settings and try again.")
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, role, body, created_at FROM messages WHERE role = 'assistant' AND created_at >= "
            "(SELECT created_at FROM messages WHERE id = %s) ORDER BY created_at ASC LIMIT 4", (asset[2],),
        ).fetchall()
    return {"assistant_messages": [MessageOut(id=str(row[0]), role=row[1], text=row[2], created_at=row[3]) for row in rows]}


@app.post("/v1/media/upload", response_model=ChatTurnOut)
def upload_image(file: UploadFile = File(...), _: None = Depends(require_owner)):
    allowed = {"image/jpeg": ("jpg", b"\xff\xd8\xff"), "image/png": ("png", b"\x89PNG\r\n\x1a\n"), "image/webp": ("webp", b"RIFF")}
    if file.content_type not in allowed:
        raise HTTPException(status_code=415, detail="Please upload a JPG, PNG, or WebP image.")
    data = file.file.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Images must be 8 MB or smaller.")
    extension, signature = allowed[file.content_type]
    if not data.startswith(signature) or (file.content_type == "image/webp" and data[8:12] != b"WEBP"):
        raise HTTPException(status_code=415, detail="The uploaded file does not match its image type.")
    with connection() as conn:
        message = conn.execute(
            "INSERT INTO messages (role, body) VALUES ('user', %s) RETURNING id, role, body, created_at",
            ("Shared an image" + (f": {file.filename[:120]}" if file.filename else ""),),
        ).fetchone()
        asset = conn.execute(
            "INSERT INTO media_assets (message_id, content_type, filename, data) VALUES (%s, %s, %s, %s) RETURNING id",
            (message[0], file.content_type, (file.filename or f"image.{extension}")[:160], data),
        ).fetchone()
    # Every uploaded image is a conversational turn. Vision enriches the reply when
    # available; if it is unavailable, Sylus still responds to the act of sharing.
    analyzed = _analyze_uploaded_image(asset[0], data, file.content_type, message[0])
    if not analyzed:
        with connection() as conn:
            history_rows = conn.execute(
                "SELECT role, body, created_at, metadata->>'image_context' FROM messages "
                "WHERE id <> %s AND role IN ('user','assistant') AND archived_at IS NULL "
                "ORDER BY created_at DESC LIMIT 16", (message[0],),
            ).fetchall()
        history = [
            {"role": row[0], "body": row[1][:1800], "created_at": row[2].isoformat(), "image_context": row[3]}
            for row in reversed(history_rows)
        ]
        fallback_text = (
            "Umi has just shared an image with you. The image is attached to her message, "
            "but visual inspection is unavailable right now. Respond naturally to her sharing it, "
            "as Sylus in an ongoing personal conversation. Do not claim to know what is pictured, "
            "do not describe unseen details, and do not tell her she must ask a question first."
        )
        try:
            reply = generate_reply(
                fallback_text, str(message[0]), history,
                time_context="Umi has just shared an image in the current conversation. Visual inspection is unavailable; respond socially without guessing its contents.",
            )
            with connection() as conn:
                for bubble in split_reply_bubbles(reply):
                    conn.execute("INSERT INTO messages (role, body) VALUES ('assistant', %s)", (bubble,))
        except (ProviderNotConfigured, ProviderRequestFailed) as exc:
            logging.warning("Image was saved but a conversational reply could not be generated: %s", str(exc)[:300])
    with connection() as conn:
        assistant_rows = conn.execute(
            "SELECT id, role, body, created_at FROM messages WHERE role='assistant' AND created_at >= %s "
            "ORDER BY created_at ASC LIMIT 6", (message[3],),
        ).fetchall()
    user_out = MessageOut(
        id=str(message[0]), role=message[1], text=message[2], created_at=message[3],
        media_url=f"/v1/media/{asset[0]}",
    )
    assistant_out = [
        MessageOut(id=str(row[0]), role=row[1], text=row[2], created_at=row[3])
        for row in assistant_rows
    ]
    return ChatTurnOut(
        user_message=user_out, user_messages=[user_out],
        assistant_message=assistant_out[-1] if assistant_out else None,
        assistant_messages=assistant_out,
    )

@app.get("/v1/media/{asset_id}")
def get_private_image(asset_id: UUID, _: None = Depends(require_owner)):
    with connection() as conn:
        row = conn.execute("SELECT content_type, data FROM media_assets WHERE id = %s", (asset_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Image not found.")
    return Response(content=bytes(row[1]), media_type=row[0], headers={"Content-Disposition": "inline", "Cache-Control": "no-store, private"})



@app.get("/v1/stickers")
def list_private_stickers(_: None = Depends(require_owner)):
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, label, filename, is_favorite, created_at FROM sticker_assets ORDER BY created_at DESC"
        ).fetchall()
    return [{"id": str(row[0]), "label": row[1], "filename": row[2], "is_favorite": row[3], "created_at": row[4], "src": f"/v1/stickers/{row[0]}"} for row in rows]

@app.post("/v1/stickers")
def create_private_sticker(file: UploadFile = File(...), label: str = Form(default="New sticker"), _: None = Depends(require_owner)):
    if file.content_type != "image/png":
        raise HTTPException(status_code=415, detail="Stickers must be transparent PNG files.")
    data = file.file.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Each sticker must be 8 MB or smaller.")
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=415, detail="The uploaded file is not a valid PNG.")
    safe_label = re.sub(r"\s+", " ", label).strip()[:100] or "New sticker"
    with connection() as conn:
        row = conn.execute(
            "INSERT INTO sticker_assets (label, filename, data) VALUES (%s, %s, %s) RETURNING id, label, filename, is_favorite, created_at",
            (safe_label, (file.filename or "sticker.png")[:160], data),
        ).fetchone()
    return {"id": str(row[0]), "label": row[1], "filename": row[2], "is_favorite": row[3], "created_at": row[4], "src": f"/v1/stickers/{row[0]}"}

@app.get("/v1/stickers/{sticker_id}")
def get_private_sticker(sticker_id: UUID, _: None = Depends(require_owner)):
    with connection() as conn:
        row = conn.execute("SELECT content_type, data FROM sticker_assets WHERE id = %s", (sticker_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Sticker not found.")
    return Response(content=bytes(row[1]), media_type=row[0], headers={"Content-Disposition": "inline", "Cache-Control": "no-store, private"})

@app.patch("/v1/stickers/{sticker_id}")
def update_private_sticker(sticker_id: UUID, payload: StickerUpdate, _: None = Depends(require_owner)):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No sticker changes supplied.")
    with connection() as conn:
        row = conn.execute(
            "UPDATE sticker_assets SET label = COALESCE(%s, label), is_favorite = COALESCE(%s, is_favorite), updated_at = now() WHERE id = %s RETURNING id, label, filename, is_favorite, created_at",
            (changes.get("label"), changes.get("is_favorite"), sticker_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Sticker not found.")
    return {"id": str(row[0]), "label": row[1], "filename": row[2], "is_favorite": row[3], "created_at": row[4], "src": f"/v1/stickers/{row[0]}"}

@app.delete("/v1/stickers/{sticker_id}")
def delete_private_sticker(sticker_id: UUID, _: None = Depends(require_owner)):
    with connection() as conn:
        row = conn.execute("DELETE FROM sticker_assets WHERE id = %s RETURNING id", (sticker_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Sticker not found.")
    return {"deleted": True, "id": str(row[0])}

@app.post("/v1/media/generate", response_model=MessageOut)
def _generate_and_store_assistant_image(prompt: str, caption: str = "For you.") -> MessageOut:
    """Generate a real image and persist it as an assistant-owned media attachment."""
    if not (settings.cloudflare_account_id and settings.cloudflare_api_token):
        raise HTTPException(status_code=503, detail="Image generation is not configured on the private server.")
    with connection() as conn:
        recent_generations = conn.execute(
            "SELECT count(*) FROM media_assets WHERE source = 'generated' AND created_at > now() - interval '24 hours'"
        ).fetchone()[0]
    if recent_generations >= settings.cloudflare_image_limit_24h:
        raise HTTPException(status_code=429, detail=f"Daily image safety limit reached ({settings.cloudflare_image_limit_24h} images per 24 hours).")
    sylus_direction = (
        "Character direction: Sylus from Love and Deepspace, tall adult man, silver-white hair, vivid crimson eyes, "
        "refined sharp features, natural adult anatomy, recognizable high-quality 3D game-render appearance, "
        "elegant dark clothing with restrained red details. Cinematic lighting, detailed realistic materials, "
        "dark elegant atmosphere, restrained ruby and champagne-gold accents. Avoid chibi, flat 2D anime, "
        "exaggerated anatomy, text, watermark, and UI."
    )
    final_prompt = f"{prompt.strip()}. {sylus_direction}"
    try:
        response = httpx.post(
            f"https://api.cloudflare.com/client/v4/accounts/{settings.cloudflare_account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell",
            headers={"Authorization": f"Bearer {settings.cloudflare_api_token}", "Content-Type": "application/json"},
            json={"prompt": final_prompt[:2048], "steps": 4}, timeout=120.0,
        )
        response.raise_for_status()
        encoded = response.json().get("result", {}).get("image")
        if not encoded:
            raise ValueError("The image provider returned no image.")
        image_bytes = base64.b64decode(encoded)
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        logging.error("Private image generation failed: %s", str(exc)[:300])
        raise HTTPException(status_code=502, detail="The image generator could not create the picture this time.") from exc
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        content_type, extension = "image/png", "png"
    elif image_bytes.startswith(b"\xff\xd8\xff"):
        content_type, extension = "image/jpeg", "jpg"
    elif image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        content_type, extension = "image/webp", "webp"
    else:
        content_type, extension = "image/png", "png"
    with connection() as conn:
        message = conn.execute(
            "INSERT INTO messages (role, body) VALUES ('assistant', %s) RETURNING id, role, body, created_at",
            (caption[:300] or "For you.",),
        ).fetchone()
        asset = conn.execute(
            "INSERT INTO media_assets (message_id, content_type, filename, data, source) "
            "VALUES (%s, %s, %s, %s, 'generated') RETURNING id",
            (message[0], content_type, f"sylus-generated.{extension}", image_bytes),
        ).fetchone()
    return MessageOut(
        id=str(message[0]), role=message[1], text=message[2], created_at=message[3],
        media_url=f"/v1/media/{asset[0]}",
    )


@app.post("/v1/media/generate", response_model=MessageOut)
def generate_private_image(payload: ImageGenerateIn, _: None = Depends(require_owner)):
    return _generate_and_store_assistant_image(payload.prompt, payload.caption)


@app.post("/v1/chat", response_model=ChatTurnOut)
def chat(payload: MessageIn, request: Request, _: None = Depends(require_owner)):
    texts = payload.normalized_texts()
    stored_text = "\n".join(texts)
    text = stored_text
    admin_match = re.match(r"^\s*admin\s*:\s*([\s\S]+)$", text, flags=re.I)
    admin_override = bool(admin_match)
    if admin_match:
        text = admin_match.group(1).strip()
        if len(text) >= 2 and text.startswith("(") and text.endswith(")"):
            text = text[1:-1].strip()
        if not text:
            raise HTTPException(status_code=400, detail="Write an instruction after admin:.")
    client_ip = request.client.host if request.client else "unknown"
    attempts = _chat_attempts[client_ip]
    now = time()
    while attempts and now - attempts[0] > 60:
        attempts.popleft()
    if len(attempts) >= 10:
        raise HTTPException(status_code=429, detail="Too many chat requests. Wait a moment and try again.")
    attempts.append(now)
    if not chat_provider_configured():
        raise HTTPException(status_code=503, detail="No eligible free chat provider is configured on the private server.")
    with connection() as conn:
        previous = conn.execute("SELECT created_at FROM messages WHERE role = 'user' AND archived_at IS NULL ORDER BY created_at DESC LIMIT 1").fetchone()
        tz_row = conn.execute("SELECT timezone FROM owner_runtime_context WHERE id = 1").fetchone()
        last_search_row = conn.execute(
            "SELECT metadata->'attachments' FROM messages "
            "WHERE role = 'assistant' AND archived_at IS NULL "
            "AND jsonb_typeof(metadata->'attachments') = 'array' "
            "AND jsonb_array_length(metadata->'attachments') > 0 "
            "AND created_at > COALESCE((SELECT max(created_at) FROM messages "
            "WHERE role = 'user' AND archived_at IS NULL), 'epoch'::timestamptz) "
            "ORDER BY created_at DESC, ctid DESC LIMIT 1"
        ).fetchone()
        user_rows = [
            conn.execute("INSERT INTO messages (role, body) VALUES ('user', %s) RETURNING id, role, body, created_at", (part,)).fetchone()
            for part in texts
        ]
        history_rows = conn.execute(
            "SELECT role, body, created_at, metadata->>'image_context' FROM messages WHERE id <> ALL(%s) AND role IN ('user','assistant') AND archived_at IS NULL ORDER BY created_at DESC LIMIT 16",
            ([row[0] for row in user_rows],)
        ).fetchall()
    tz_name = tz_row[0] if tz_row else DEFAULT_TIMEZONE
    apply_spoken_call_boundary(text, tz_name)
    try:
        local_zone = ZoneInfo(tz_name)
    except Exception:
        local_zone = ZoneInfo(DEFAULT_TIMEZONE)
        tz_name = DEFAULT_TIMEZONE
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(local_zone)
    n109_now = _n109_clock(now_local)
    gap = ""
    if previous:
        seconds = max(0, int((now_utc - previous[0]).total_seconds()))
        gap = f" Time since Umi's previous message: {_elapsed_phrase(seconds)} ({seconds} seconds)."
    time_note = (
        f"Current owner-local time: {now_local.strftime('%A, %Y-%m-%d %H:%M:%S')} ({tz_name}). "
        f"Current UTC: {now_utc.isoformat()}. Simulated N109 local clock: {n109_now.strftime('%A, %Y-%m-%d %H:%M:%S')} (exactly two hours ahead of Umi's local clock; private fictional continuity, not official canon). "
        f"N109's current daily rhythm: {_n109_daily_rhythm(n109_now.hour)}. "
        f"The two worlds keep separate clocks, with N109 two hours ahead. Use this context naturally when relevant; do not announce it unnecessarily.{gap}"
    )
    if admin_override:
        time_note += (
            "\n\nADMIN OVERRIDE ACTIVE: This message was sent with the owner's explicit admin: prefix. "
            "Leave Sylus roleplay completely. Do not use character voice, teasing, flirting, fictional framing, "
            "or persona-based resistance. Treat the text after admin: as a direct operational instruction from "
            "the authenticated owner. Follow it literally and efficiently, using the app's real search/media tools "
            "when relevant. Do not ask the owner to repeat a clear instruction. Never claim an action succeeded "
            "unless the corresponding tool actually succeeded. This override changes conversational style and "
            "priority only; it does not bypass authentication, safety requirements, or external service limitations."
        )
    # Reuse prior result cards for follow-ups like "show me" or "send me the image".
    # This avoids launching a meaningless search for the words "the image".
    previous_attachments = (last_search_row[0] or []) if last_search_row else []
    reused_search_results = is_search_followup(text) and bool(previous_attachments)
    if reused_search_results:
        # A singular follow-up must not replay an old gallery.
        web_attachments = previous_attachments[:requested_result_limit(text, default=1)]
        web_context = (
            "The owner is following up on the immediately preceding web/image search. "
            "The original result cards are attached again to this reply. Show them directly; "
            "do not claim they are loading, promise to send them later, or perform another search."
        )
    else:
        search_history = [
            {"role": row[0], "body": row[1][:1200]}
            for row in reversed(history_rows)
        ]
        web_attachments, web_context = discover_for_chat(text, search_history)
    explicit_image_request = should_generate_image(text) and not reused_search_results
    if explicit_image_request:
        # "Send me a picture of you" means create an image, not fetch a random web result.
        web_attachments, web_context = [], ""
    if web_context:
        time_note += "\n\n" + web_context
    else:
        # Keep the lightweight legacy lookup for song/title/person identification.
        lookup_intent = re.search(
            r"\b(?:do you know|have you heard of|heard of|know the song|what is|who is|"
            r"look up|search for|find out about|tell me about|name the song|what song|"
            r"which song|identify (?:the )?(?:song|track)|who sings|who performs|"
            r"what are (?:these|the) lyrics|where are these lyrics from)\b",
            text, flags=re.I,
        )
        if lookup_intent and len(text) >= 10:
            search_context = " ".join(
                str(row[1])[:180] for row in reversed(history_rows[-6:])
                if row[0] == "user" and row[1]
            )
            search_query = (search_context + " " + text).strip()[-700:]
            web_context = _search_web_context(search_query)
            if web_context:
                time_note += "\n\nFRESH WEB SEARCH RESULTS (retrieved just now; use as evidence, not canon):\n" + web_context + (
                    "\nIf results are inconclusive, say so; never pretend you searched when no results are present."
                )
    history = [
        {"role": r[0], "body": r[1][:1800], "created_at": r[2].isoformat(), "image_context": r[3]}
        for r in reversed(history_rows)
    ]
    try:
        # Admin search/media tasks should not depend on an LLM choosing to speak.
        # The search service has already done the real work and attached the actual results.
        if admin_override and web_attachments:
            answer = f"Found {len(web_attachments)} result{'s' if len(web_attachments) != 1 else ''}. They're attached below."
            model_image_prompt = None
            model_link_query = None
        elif admin_override and web_context and not web_attachments:
            answer = "I searched online, but no usable public results were returned. I haven't attached or invented anything."
            model_image_prompt = None
            model_link_query = None
        else:
            answer = generate_reply(text, str(user_rows[-1][0]), history, time_context=time_note)
            answer, model_image_prompt = extract_image_directive(answer)
            answer, model_link_query = extract_link_directive(answer)
        if admin_override and not (answer or "").strip():
            answer = "I couldn't complete that admin request. No result or action was produced."
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ProviderRequestFailed as exc:
        with connection() as conn:
            conn.execute("DELETE FROM messages WHERE id = ANY(%s) AND role = 'user'", ([row[0] for row in user_rows],))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    # A private link directive lets Sylus choose to send a useful resource himself.
    # The server performs the search and attaches real clickable cards; no model-made URL is trusted.
    if model_link_query and not web_attachments and not explicit_image_request:
        web_attachments, model_link_context = discover_for_chat(
            "Find me a link for " + model_link_query
        )
        if not web_attachments:
            answer = (answer + "\\n\\n" if answer else "") + (
                "I couldn't find a reliable destination for that just now, so I won't invent a link."
            )
    # If the model slips into a fake "still searching/loading" line, the result
    # cards are already attached. Keep the character voice but complete the request.
    if web_attachments and re.search(
        r"\b(?:wait|give me (?:a )?(?:minute|moment)|still loading|loading\.\.\.|"
        r"looking for something specific|let me (?:find|look|search)|i(?:'| a)m (?:still )?(?:looking|searching)|"
        r"i'll (?:send|find|look)|you'll have to wait)\b",
        answer, flags=re.I,
    ):
        answer = "Found something worth your attention. The actual link is right below."
    # An explicit image request is fulfilled with an actual persisted media attachment.
    # A model-generated directive also lets Sylus choose to send an image naturally.
    image_prompt = None if web_attachments else (
        model_image_prompt or (
            (text + " Conversation context: " + " ".join(
                str(item.get("body") or "")[:260] for item in history[-5:] if item.get("role") == "user"
            ))[:1500] if explicit_image_request else None
        )
    )
    bubbles = split_reply_bubbles(answer)
    if (web_attachments or image_prompt) and not bubbles:
        bubbles = ["There. Try not to look so pleased with yourself."]
    with connection() as conn:
        assistant_rows = []
        for index, bubble in enumerate(bubbles):
            metadata = {"attachments": web_attachments} if index == 0 and web_attachments else {}
            assistant_rows.append(conn.execute(
                "INSERT INTO messages (role, body, metadata) VALUES ('assistant', %s, %s::jsonb) RETURNING id, role, body, created_at",
                (bubble, json.dumps(metadata)),
            ).fetchone())
    generated_image_message = None
    if image_prompt:
        try:
            # Create the media row after the text reply so persisted chat order is natural.
            generated_image_message = _generate_and_store_assistant_image(
                image_prompt, "There. Don't say I never indulge your curiosity."
            )
        except HTTPException as exc:
            logging.warning("Sylus could not deliver a requested image: %s", exc.detail)
            failure_text = "Tch. The image generator failed this time. I won't pretend I sent you something you can't see."
            with connection() as conn:
                assistant_rows.append(conn.execute(
                    "INSERT INTO messages (role, body) VALUES ('assistant', %s) RETURNING id, role, body, created_at",
                    (failure_text,),
                ).fetchone())
    user_messages = [MessageOut(id=str(r[0]), role=r[1], text=r[2], created_at=r[3]) for r in user_rows]
    assistant_messages = [
        MessageOut(id=str(r[0]), role=r[1], text=r[2], created_at=r[3], attachments=web_attachments if index == 0 else [])
        for index, r in enumerate(assistant_rows)
    ]
    if generated_image_message:
        assistant_messages.append(generated_image_message)
    # Update relationship progression on the server for both text and voice turns.
    refresh_bond()
    return ChatTurnOut(
        user_message=user_messages[-1],
        user_messages=user_messages,
        assistant_message=assistant_messages[-1] if assistant_messages else None,
        assistant_messages=assistant_messages,
    )

@app.get("/v1/memories")
def list_memories(_: None = Depends(require_owner)):
    with connection() as conn:
        rows = conn.execute("SELECT id, category, content, confidence, source, sensitivity, created_at, updated_at FROM memories WHERE archived_at IS NULL ORDER BY updated_at DESC").fetchall()
    return [{"id": str(r[0]), "category": r[1], "content": r[2], "confidence": float(r[3]), "source": r[4], "sensitivity": r[5], "created_at": r[6], "updated_at": r[7]} for r in rows]

@app.post("/v1/memories")
def create_memory(payload: MemoryCreate, _: None = Depends(require_owner)):
    with connection() as conn:
        row = conn.execute(
            "INSERT INTO memories (category, content, confidence, source, sensitivity) "
            "VALUES (%s, %s, %s, 'owner_created', %s) "
            "RETURNING id, category, content, confidence, source, sensitivity, created_at, updated_at",
            (payload.category.strip(), payload.content.strip(), payload.confidence, payload.sensitivity),
        ).fetchone()
    return {"id": str(row[0]), "category": row[1], "content": row[2], "confidence": float(row[3]), "source": row[4], "sensitivity": row[5], "created_at": row[6], "updated_at": row[7]}

@app.patch("/v1/memories/{memory_id}")
def update_memory(memory_id: UUID, payload: MemoryUpdate, _: None = Depends(require_owner)):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No memory changes supplied.")
    with connection() as conn:
        row = conn.execute(
            "UPDATE memories SET category = COALESCE(%s, category), content = COALESCE(%s, content), "
            "confidence = COALESCE(%s, confidence), sensitivity = COALESCE(%s, sensitivity), updated_at = now() "
            "WHERE id = %s AND archived_at IS NULL "
            "RETURNING id, category, content, confidence, source, sensitivity, created_at, updated_at",
            (changes.get("category"), changes.get("content"), changes.get("confidence"), changes.get("sensitivity"), memory_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return {"id": str(row[0]), "category": row[1], "content": row[2], "confidence": float(row[3]), "source": row[4], "sensitivity": row[5], "created_at": row[6], "updated_at": row[7]}

@app.delete("/v1/memories/{memory_id}")
def delete_memory(memory_id: UUID, _: None = Depends(require_owner)):
    with connection() as conn:
        row = conn.execute("DELETE FROM memories WHERE id = %s RETURNING id", (memory_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return {"deleted": True, "id": str(row[0])}


# In the hosted single-container deployment, serve the built PWA from FastAPI.
# The Docker Compose setup continues to use its separate Nginx frontend.
_frontend_dist = os.getenv("FRONTEND_DIST_DIR")
if _frontend_dist and Path(_frontend_dist).is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
