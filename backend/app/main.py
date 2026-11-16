import secrets
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Literal
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from .config import settings
from .db import connection, open_pool

app = FastAPI(title="SYLUS private companion API", version="0.2.0")
DEFAULT_TIMEZONE = "Asia/Dhaka"

@app.on_event("startup")
def startup():
    open_pool()

def require_owner(authorization: str | None = Header(default=None)):
    expected = f"Bearer {settings.sylus_owner_token}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Owner access required")

class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=12000)

class MessageOut(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    text: str
    created_at: datetime

@app.get("/health")
def health():
    return {"ok": True, "service": "sylus-api"}

@app.get("/v1/time-context")
def time_context(_: None = Depends(require_owner)):
    """Return current Dhaka-local time and the last time the owner messaged."""
    with connection() as conn:
        row = conn.execute(
            "SELECT created_at FROM messages WHERE role = 'user' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        tz_row = conn.execute(
            "SELECT timezone FROM owner_runtime_context WHERE id = 1"
        ).fetchone()
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
        "timezone": tz_name,
        "now_utc": now_utc.isoformat(),
        "now_local": now_local.isoformat(),
        "local_date": now_local.date().isoformat(),
        "weekday": now_local.strftime("%A"),
        "local_time": now_local.strftime("%H:%M:%S"),
        "last_user_message_utc": last_utc.isoformat() if last_utc else None,
        "last_user_message_local": last_local.isoformat() if last_local else None,
        "seconds_since_last_user_message": elapsed_seconds,
    }

@app.get("/v1/messages", response_model=list[MessageOut])
def list_messages(_: None = Depends(require_owner)):
    with connection() as conn:
        rows = conn.execute("SELECT id, role, body, created_at FROM messages ORDER BY created_at ASC").fetchall()
    return [MessageOut(id=str(r[0]), role=r[1], text=r[2], created_at=r[3]) for r in rows]

@app.post("/v1/messages", response_model=MessageOut)
def save_user_message(payload: MessageIn, _: None = Depends(require_owner)):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Message cannot be blank")
    with connection() as conn:
        row = conn.execute("INSERT INTO messages (role, body) VALUES ('user', %s) RETURNING id, role, body, created_at", (text,)).fetchone()
    return MessageOut(id=str(row[0]), role=row[1], text=row[2], created_at=row[3])

@app.get("/v1/memories")
def list_memories(_: None = Depends(require_owner)):
    with connection() as conn:
        rows = conn.execute("SELECT id, category, content, confidence, source, created_at, updated_at FROM memories WHERE archived_at IS NULL ORDER BY updated_at DESC").fetchall()
    return [{"id": str(r[0]), "category": r[1], "content": r[2], "confidence": r[3], "source": r[4], "created_at": r[5], "updated_at": r[6]} for r in rows]
