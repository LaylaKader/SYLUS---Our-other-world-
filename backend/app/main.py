import secrets
import hashlib
import hmac
from collections import defaultdict, deque
from time import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Literal
from uuid import UUID
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .config import settings
from .db import connection, open_pool
from .migrate import run_migrations
from .chat_service import generate_reply, ProviderNotConfigured, ProviderRequestFailed

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
    if request.url.path.startswith("/v1/"):
        response.headers["Cache-Control"] = "no-store, private"
        response.headers["Pragma"] = "no-cache"
    return response

def _valid_session(value: str | None) -> bool:
    if not value or not settings.session_secret:
        return False
    try:
        timestamp_text, supplied = value.split(".", 1)
        timestamp = int(timestamp_text)
    except (ValueError, TypeError):
        return False
    now = int(time())
    if timestamp > now + 60 or now - timestamp > settings.session_ttl_seconds:
        return False
    expected = hmac.new(settings.session_secret.encode(), f"v1:{timestamp}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied, expected)

def require_owner(request: Request, authorization: str | None = Header(default=None)):
    expected = f"Bearer {settings.sylus_owner_token}"
    bearer_ok = bool(authorization and secrets.compare_digest(authorization, expected))
    if not bearer_ok and not _valid_session(request.cookies.get("sylus_session")):
        raise HTTPException(status_code=401, detail="Owner session required")

class OwnerLogin(BaseModel):
    password: str = Field(min_length=1, max_length=256)

class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=12000)

class MessageOut(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    text: str
    created_at: datetime

class ChatTurnOut(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut

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
    signature = hmac.new(settings.session_secret.encode(), f"v1:{issued}".encode(), hashlib.sha256).hexdigest()
    response.set_cookie(
        key="sylus_session", value=f"{issued}.{signature}", max_age=settings.session_ttl_seconds,
        httponly=True, secure=settings.app_env.lower() == "production", samesite="lax", path="/",
    )
    return {"authenticated": True, "expires_in": settings.session_ttl_seconds}

@app.delete("/v1/session")
def delete_owner_session(response: Response):
    response.delete_cookie(key="sylus_session", path="/", httponly=True, secure=settings.app_env.lower() == "production", samesite="none" if settings.app_env.lower() == "production" else "lax")
    return {"authenticated": False}

@app.get("/health")
def health():
    return {"ok": True, "service": "sylus-api"}

@app.get("/v1/time-context")
def time_context(_: None = Depends(require_owner)):
    """Return current Dhaka-local time and the last time the owner messaged."""
    with connection() as conn:
        row = conn.execute("SELECT created_at FROM messages WHERE role = 'user' ORDER BY created_at DESC LIMIT 1").fetchone()
        tz_row = conn.execute("SELECT timezone FROM owner_runtime_context WHERE id = 1").fetchone()
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
        "last_user_message_utc": last_utc.isoformat() if last_utc else None,
        "last_user_message_local": last_local.isoformat() if last_local else None,
        "seconds_since_last_user_message": elapsed_seconds,
    }

@app.get("/v1/messages", response_model=list[MessageOut])
def list_messages(_: None = Depends(require_owner)):
    with connection() as conn:
        rows = conn.execute("SELECT id, role, body, created_at FROM messages WHERE role IN ('user','assistant') ORDER BY created_at ASC").fetchall()
    return [MessageOut(id=str(r[0]), role=r[1], text=r[2], created_at=r[3]) for r in rows]

@app.post("/v1/messages", response_model=MessageOut)
def save_user_message(payload: MessageIn, _: None = Depends(require_owner)):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Message cannot be blank")
    with connection() as conn:
        row = conn.execute("INSERT INTO messages (role, body) VALUES ('user', %s) RETURNING id, role, body, created_at", (text,)).fetchone()
    return MessageOut(id=str(row[0]), role=row[1], text=row[2], created_at=row[3])

@app.post("/v1/chat", response_model=ChatTurnOut)
def chat(payload: MessageIn, _: None = Depends(require_owner)):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Message cannot be blank")
    if not (settings.model_api_base_url and settings.model_api_key and settings.model_name):
        raise HTTPException(status_code=503, detail="Chat model is not configured on the private server. No paid or alternate provider will be selected automatically.")
    with connection() as conn:
        previous = conn.execute("SELECT created_at FROM messages WHERE role = 'user' ORDER BY created_at DESC LIMIT 1").fetchone()
        tz_row = conn.execute("SELECT timezone FROM owner_runtime_context WHERE id = 1").fetchone()
        user_row = conn.execute("INSERT INTO messages (role, body) VALUES ('user', %s) RETURNING id, role, body, created_at", (text,)).fetchone()
        history_rows = conn.execute(
            "SELECT role, body, created_at FROM messages WHERE id <> %s AND role IN ('user','assistant') ORDER BY created_at DESC LIMIT 16",
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
    history = [{"role": r[0], "body": r[1], "created_at": r[2].isoformat()} for r in reversed(history_rows)]
    try:
        answer = generate_reply(text, str(user_row[0]), history, time_context=time_note)
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ProviderRequestFailed as exc:
        with connection() as conn:
            conn.execute("DELETE FROM messages WHERE id = %s AND role = 'user'", (user_row[0],))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    with connection() as conn:
        assistant_row = conn.execute("INSERT INTO messages (role, body) VALUES ('assistant', %s) RETURNING id, role, body, created_at", (answer,)).fetchone()
    return ChatTurnOut(
        user_message=MessageOut(id=str(user_row[0]), role=user_row[1], text=user_row[2], created_at=user_row[3]),
        assistant_message=MessageOut(id=str(assistant_row[0]), role=assistant_row[1], text=assistant_row[2], created_at=assistant_row[3]),
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
