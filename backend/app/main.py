import os
from pathlib import Path
import secrets
import hashlib
import hmac
from collections import defaultdict, deque
from time import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Literal
from uuid import UUID
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import base64
import httpx
from .config import settings
from .db import connection, open_pool
from .migrate import run_migrations
from .chat_service import generate_reply, split_reply_bubbles, ProviderNotConfigured, ProviderRequestFailed

app = FastAPI(title="SYLUS private companion API", version="0.3.0")
DEFAULT_TIMEZONE = "Asia/Dhaka"

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
    text: str = Field(min_length=1, max_length=12000)

class MessageEdit(BaseModel):
    text: str = Field(min_length=1, max_length=12000)

class MessageOut(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    text: str
    created_at: datetime
    media_url: str | None = None

class ChatTurnOut(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
    assistant_messages: list[MessageOut] = Field(default_factory=list)

class SpeechIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)

class ImageGenerateIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=1800)
    caption: str = Field(default='A picture for you.', max_length=300)

class MemoryCreate(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=4000)
    confidence: float = Field(default=0.9, ge=0, le=1)
    sensitivity: Literal["normal", "sensitive"] = "normal"

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
    last_utc = row[0] if row else None
    last_local = last_utc.astimezone(local_zone) if last_utc else None
    elapsed_seconds = max(0, int((now_utc - last_utc).total_seconds())) if last_utc else None
    return {
        "timezone": tz_name, "now_utc": now_utc.isoformat(), "now_local": now_local.isoformat(),
        "local_date": now_local.date().isoformat(), "weekday": now_local.strftime("%A"),
        "local_time": now_local.strftime("%H:%M:%S"),
        "chat_ready": bool(settings.model_api_base_url and settings.model_api_key and settings.model_name),
        "chat_model": settings.model_name if settings.model_api_key else None,
        "image_generation_ready": bool(settings.cloudflare_account_id and settings.cloudflare_api_token),
        "voice_ready": bool(settings.elevenlabs_api_key and settings.elevenlabs_voice_id),
        "vision_ready": bool(settings.cloudflare_account_id and settings.cloudflare_api_token and vision_row),
        "last_user_message_utc": last_utc.isoformat() if last_utc else None,
        "last_user_message_local": last_local.isoformat() if last_local else None,
        "seconds_since_last_user_message": elapsed_seconds,
    }

@app.get("/v1/messages", response_model=list[MessageOut])
def list_messages(_: None = Depends(require_owner)):
    with connection() as conn:
        rows = conn.execute("SELECT m.id, m.role, m.body, m.created_at, a.id FROM messages m LEFT JOIN media_assets a ON a.message_id = m.id WHERE m.role IN ('user','assistant') AND m.archived_at IS NULL ORDER BY m.created_at ASC").fetchall()
    return [MessageOut(id=str(r[0]), role=r[1], text=r[2], created_at=r[3], media_url=f'/v1/media/{r[4]}' if r[4] else None) for r in rows]

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
    if not (settings.model_api_base_url and settings.model_api_key and settings.model_name):
        raise HTTPException(status_code=503, detail="Chat model is not configured on the private server.")
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
        assistant_message=assistant_messages[-1],
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
        if not (settings.model_api_base_url and settings.model_api_key and settings.model_name):
            raise HTTPException(status_code=503, detail="Chat model is not configured on the private server.")
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
        assistant_message = assistant_messages[-1]
    else:
        assistant_messages = []
    return {"rewound_to": str(message_id), "archived_count": len(archived), "assistant_message": assistant_message, "assistant_messages": assistant_messages}

@app.post("/v1/voice/speech")
def create_speech(payload: SpeechIn, _: None = Depends(require_owner)):
    if not (settings.elevenlabs_api_key and settings.elevenlabs_voice_id):
        raise HTTPException(status_code=503, detail="Voice playback is not configured. Add an ElevenLabs API key and your designed voice ID in the private server settings.")
    try:
        response = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}?output_format=mp3_44100_128",
            headers={"xi-api-key": settings.elevenlabs_api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
            json={"text": payload.text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.55, "similarity_boost": 0.72, "style": 0.25, "use_speaker_boost": True}},
            timeout=60.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="The voice provider could not generate audio. Check the private voice configuration and usage allowance.") from exc
    return Response(content=response.content, media_type="audio/mpeg", headers={"Cache-Control": "no-store, private", "Content-Disposition": "inline; filename=sylus-message.mp3"})

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

@app.post("/v1/media/{asset_id}/discuss", response_model=MessageOut)
def discuss_uploaded_image(asset_id: UUID, _: None = Depends(require_owner)):
    with connection() as conn:
        accepted = conn.execute("SELECT 1 FROM provider_acceptances WHERE provider = 'cloudflare_meta_vision'").fetchone()
        asset = conn.execute(
            "SELECT a.data, a.content_type, a.message_id FROM media_assets a JOIN messages m ON m.id = a.message_id "
            "WHERE a.id = %s AND m.archived_at IS NULL", (asset_id,),
        ).fetchone()
        if not accepted:
            raise HTTPException(status_code=428, detail="Accept Meta's model license in Settings before asking Sylus to interpret images.")
        if not asset:
            raise HTTPException(status_code=404, detail="Image not found.")
        history_rows = conn.execute(
            "SELECT role, body, created_at FROM messages WHERE id <> %s AND role IN ('user','assistant') "
            "AND archived_at IS NULL ORDER BY created_at DESC LIMIT 18", (asset[2],),
        ).fetchall()
    image_data = "data:" + asset[1] + ";base64," + base64.b64encode(bytes(asset[0])).decode("ascii")
    try:
        vision_response = httpx.post(
            "https://api.cloudflare.com/client/v4/accounts/" + settings.cloudflare_account_id + "/ai/run/@cf/meta/llama-3.2-11b-vision-instruct",
            headers={"Authorization": f"Bearer {settings.cloudflare_api_token}", "Content-Type": "application/json"},
            json={"messages": [{"role": "user", "content": "Describe this image accurately and concisely. Focus on visible details. Do not infer identity, sensitive traits, or unseen context."}], "image": image_data},
            timeout=90.0,
        )
        vision_response.raise_for_status()
        visual_description = vision_response.json().get("result", {}).get("response", "")
        if not visual_description:
            raise ValueError("The vision model returned no description.")
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Image understanding failed. The image remains saved privately.") from exc
    history = [{"role": r[0], "body": r[1][:1800], "created_at": r[2].isoformat()} for r in reversed(history_rows)]
    user_text = "The owner shared an image. What I can actually see in it: " + visual_description[:5000] + ". Respond naturally to the image, without claiming details that are not visible."
    try:
        answer = generate_reply(user_text, str(asset[2]), history, time_context="The owner has just shared an image in the current conversation.")
    except (ProviderRequestFailed, ProviderNotConfigured) as exc:
        raise HTTPException(status_code=502, detail="I could inspect the image, but Sylus could not reply. The image remains saved privately.") from exc
    with connection() as conn:
        row = conn.execute("INSERT INTO messages (role, body) VALUES ('assistant', %s) RETURNING id, role, body, created_at", (answer,)).fetchone()
    return MessageOut(id=str(row[0]), role=row[1], text=row[2], created_at=row[3])

@app.post("/v1/media/upload", response_model=MessageOut)
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
    return MessageOut(id=str(message[0]), role=message[1], text=message[2], created_at=message[3], media_url=f"/v1/media/{asset[0]}")

@app.get("/v1/media/{asset_id}")
def get_private_image(asset_id: UUID, _: None = Depends(require_owner)):
    with connection() as conn:
        row = conn.execute("SELECT content_type, data FROM media_assets WHERE id = %s", (asset_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Image not found.")
    return Response(content=bytes(row[1]), media_type=row[0], headers={"Content-Disposition": "inline", "Cache-Control": "no-store, private"})

@app.post("/v1/media/generate", response_model=MessageOut)
def generate_private_image(payload: ImageGenerateIn, _: None = Depends(require_owner)):
    if not (settings.cloudflare_account_id and settings.cloudflare_api_token):
        raise HTTPException(status_code=503, detail="Image generation is not configured. Add the Cloudflare AI credentials in the private server settings; no paid fallback will be used.")
    with connection() as conn:
        recent_generations = conn.execute("SELECT count(*) FROM media_assets WHERE source = 'generated' AND created_at > now() - interval '24 hours'").fetchone()[0]
    if recent_generations >= settings.cloudflare_image_limit_24h:
        raise HTTPException(status_code=429, detail=f"Daily image safety limit reached ({settings.cloudflare_image_limit_24h} images per 24 hours). This prevents unexpected usage.")
    prompt = f"{payload.prompt.strip()}. Character direction: Sylus from Love and Deepspace, a tall adult man with silver-white hair, vivid crimson eyes, refined sharp facial features, composed confident expression, elegant dark clothing with restrained red details. Preserve his recognizable in-game 3D appearance and realistic game-render proportions. Visual direction: cinematic lighting, detailed realistic materials, natural anatomy, dark elegant atmosphere, restrained ruby and champagne-gold accents. Avoid chibi, flat 2D anime, exaggerated anatomy, text, watermark, UI. "
    try:
        response = httpx.post(
            f"https://api.cloudflare.com/client/v4/accounts/{settings.cloudflare_account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell",
            headers={"Authorization": f"Bearer {settings.cloudflare_api_token}", "Content-Type": "application/json"},
            json={"prompt": prompt[:2048], "steps": 4}, timeout=120.0,
        )
        response.raise_for_status()
        result = response.json()
        encoded = result.get("result", {}).get("image")
        if not encoded:
            raise ValueError("The image provider returned no image.")
        image_bytes = base64.b64decode(encoded)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=502, detail=f"Image generation failed: {exc}") from exc
    with connection() as conn:
        message = conn.execute(
            "INSERT INTO messages (role, body) VALUES ('assistant', %s) RETURNING id, role, body, created_at",
            (payload.caption or "A picture for you.",),
        ).fetchone()
        asset = conn.execute(
            "INSERT INTO media_assets (message_id, content_type, filename, data, source) VALUES (%s, 'image/jpeg', 'sylus-generated.jpg', %s, 'generated') RETURNING id",
            (message[0], image_bytes),
        ).fetchone()
    return MessageOut(id=str(message[0]), role=message[1], text=message[2], created_at=message[3], media_url=f"/v1/media/{asset[0]}")

@app.post("/v1/chat", response_model=ChatTurnOut)
def chat(payload: MessageIn, request: Request, _: None = Depends(require_owner)):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Message cannot be blank")
    client_ip = request.client.host if request.client else "unknown"
    attempts = _chat_attempts[client_ip]
    now = time()
    while attempts and now - attempts[0] > 60:
        attempts.popleft()
    if len(attempts) >= 10:
        raise HTTPException(status_code=429, detail="Too many chat requests. Wait a moment and try again.")
    attempts.append(now)
    if not (settings.model_api_base_url and settings.model_api_key and settings.model_name):
        raise HTTPException(status_code=503, detail="Chat model is not configured on the private server. No paid or alternate provider will be selected automatically.")
    with connection() as conn:
        previous = conn.execute("SELECT created_at FROM messages WHERE role = 'user' AND archived_at IS NULL ORDER BY created_at DESC LIMIT 1").fetchone()
        tz_row = conn.execute("SELECT timezone FROM owner_runtime_context WHERE id = 1").fetchone()
        user_row = conn.execute("INSERT INTO messages (role, body) VALUES ('user', %s) RETURNING id, role, body, created_at", (text,)).fetchone()
        history_rows = conn.execute(
            "SELECT role, body, created_at FROM messages WHERE id <> %s AND role IN ('user','assistant') AND archived_at IS NULL ORDER BY created_at DESC LIMIT 12",
            (user_row[0],),
        ).fetchall()
    tz_name = tz_row[0] if tz_row else DEFAULT_TIMEZONE
    try:
        local_zone = ZoneInfo(tz_name)
    except Exception:
        local_zone = ZoneInfo(DEFAULT_TIMEZONE)
        tz_name = DEFAULT_TIMEZONE
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(local_zone)
    gap = ""
    if previous:
        seconds = max(0, int((now_utc - previous[0]).total_seconds()))
        gap = f" Time since the owner's previous message: {seconds} seconds."
    time_note = (
        f"Current owner-local time: {now_local.strftime('%A, %Y-%m-%d %H:%M:%S')} ({tz_name}). "
        f"Current UTC: {now_utc.isoformat()}.{gap} Use this context naturally when relevant; do not announce it unnecessarily."
    )
    history = [{"role": r[0], "body": r[1][:1800], "created_at": r[2].isoformat()} for r in reversed(history_rows)]
    try:
        answer = generate_reply(text, str(user_row[0]), history, time_context=time_note)
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ProviderRequestFailed as exc:
        with connection() as conn:
            conn.execute("DELETE FROM messages WHERE id = %s AND role = 'user'", (user_row[0],))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
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
        assistant_message=assistant_messages[-1],
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
