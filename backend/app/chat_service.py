"""Runnable, replaceable chat adapter with persisted artificial emotion and conservative memory retrieval."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import httpx

from .agent import ChatModel, RetrievedMemory, SylusAgent
from .config import settings
from .db import connection
from .emotion import EmotionState


class ProviderNotConfigured(RuntimeError):
    pass


class ProviderRequestFailed(RuntimeError):
    pass


class OpenAICompatibleChatModel(ChatModel):
    """Single configured provider only. No silent provider switching or paid fallback."""

    def respond(self, *, persona: str, recent_history: list[dict], memories: list[RetrievedMemory], user_text: str) -> str:
        if not settings.model_api_base_url or not settings.model_api_key or not settings.model_name:
            raise ProviderNotConfigured("A chat model is not configured. Add MODEL_API_BASE_URL, MODEL_API_KEY, and MODEL_NAME on the private server.")
        memory_context = "\n".join(
            f"- [{m.category}; confidence {m.confidence:.2f}] {m.content}" for m in memories
        ) or "No relevant saved memories were retrieved."
        system_prompt = (
            f"{persona}\n\nPRIVATE OWNER CONTEXT (use only when relevant; never recite it as a dossier):\n"
            f"{memory_context}\n\nBe accurate about current time and continuity. Do not invent shared experiences or canon. "
            "Do not claim to be human or conscious. Never pressure the owner to reply."
        )
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for item in recent_history[-16:]:
            role = item.get("role")
            body = item.get("body") or item.get("text") or ""
            if role in ("user", "assistant") and body:
                messages.append({"role": role, "content": str(body)[:12000]})
        messages.append({"role": "user", "content": user_text})
        try:
            response = httpx.post(
                settings.model_api_base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {settings.model_api_key}", "Content-Type": "application/json"},
                json={"model": settings.model_name, "messages": messages, "temperature": 0.78},
                timeout=45.0,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            answer = data["choices"][0]["message"]["content"]
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("Provider returned an empty response.")
            return answer.strip()
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise ProviderRequestFailed(f"Chat provider request failed: {exc}") from exc


class PostgresMemoryRetriever:
    """Conservative lexical retrieval; semantic embeddings can replace this adapter later."""

    def retrieve(self, *, query: str, limit: int = 8) -> list[RetrievedMemory]:
        terms = [word.strip(".,!?;:\"'()[]{}").lower() for word in query.split()]
        terms = [word for word in terms if len(word) >= 4][:8]
        if not terms:
            return []
        clauses = " OR ".join("content ILIKE %s" for _ in terms)
        params = [f"%{term}%" for term in terms] + [limit]
        with connection() as conn:
            rows = conn.execute(
                f"SELECT category, content, confidence, source FROM memories "
                f"WHERE archived_at IS NULL AND sensitivity = 'normal' AND ({clauses}) "
                "ORDER BY confidence DESC, updated_at DESC LIMIT %s",
                params,
            ).fetchall()
        return [RetrievedMemory(category=r[0], content=r[1], confidence=float(r[2]), source=r[3]) for r in rows]


class ExplicitOnlyMemoryWriter:
    """Automatic extraction is disabled until owner review/edit/delete controls exist."""

    def extract_and_store(self, *, user_text: str, assistant_text: str, source_message_id: str) -> None:
        return None


def load_emotion_state() -> EmotionState:
    with connection() as conn:
        row = conn.execute("SELECT dimensions FROM emotion_states WHERE id = 1").fetchone()
    if not row or not isinstance(row[0], dict):
        return EmotionState()
    allowed = EmotionState.__dataclass_fields__.keys()
    values = {key: float(value) for key, value in row[0].items() if key in allowed}
    return EmotionState(**values).normalize()


def classify_explicit_event(text: str) -> tuple[str | None, float]:
    """Only respond to clear first-person statements or unmistakable interaction cues."""
    value = text.lower()
    if any(phrase in value for phrase in ("i passed", "i got accepted", "i got the offer", "i finished it", "i did it", "i finally submitted")):
        return "user_reached_goal", 0.75
    if any(phrase in value for phrase in ("i'm sad", "i am sad", "i feel hopeless", "i'm scared", "i am scared", "i feel overwhelmed", "i'm overwhelmed", "i am overwhelmed", "i'm upset", "i am upset", "i'm disappointed", "i am disappointed")):
        return "user_distressed", 0.65
    if any(phrase in value for phrase in ("i'm disappointed", "i am disappointed")):
        return "disappointment", 0.6
    if any(phrase in value for phrase in ("i trust you", "i feel safe with you")):
        return "meaningful_trust", 0.6
    if any(phrase in value for phrase in ("i feel better", "that helped", "i'm feeling better")):
        return "reassurance_received", 0.55
    if any(phrase in value for phrase in ("haha", "hehe", "lmao")):
        return "playful_banter", 0.4
    return None, 0.0


def save_emotion_state(state: EmotionState, previous: dict[str, float], event: str | None, source_message_id: str) -> None:
    current = state.to_dict()
    rationale = f"Explicit interaction signal: {event}" if event else "Gradual baseline decay after a conversation turn."
    with connection() as conn:
        conn.execute(
            "UPDATE emotion_states SET dimensions = %s::jsonb, dominant_mood = %s, rationale = %s, "
            "confidence = %s, version = version + 1, updated_at = now() WHERE id = 1",
            (json.dumps(current), state.dominant_mood(), rationale, 0.65 if event else 0.5),
        )
        conn.execute(
            "INSERT INTO emotion_events (previous_state, next_state, trigger_message_id, trigger_type, rationale, confidence) "
            "VALUES (%s::jsonb, %s::jsonb, %s, %s, %s, %s)",
            (json.dumps(previous), json.dumps(current), source_message_id, event or "turn_decay", rationale, 0.65 if event else 0.5),
        )


def load_persona() -> str:
    path = Path(__file__).resolve().parents[2] / "character" / "SYLUS_PERSONA.md"
    if not path.exists():
        return "Portray Sylus as composed, perceptive, confident, strategic, dry-witted, and unhurried. Respect autonomy."
    return path.read_text(encoding="utf-8")


def generate_reply(user_text: str, source_message_id: str, history: list[dict], time_context: str = "") -> str:
    emotion = load_emotion_state()
    previous = emotion.to_dict()
    event, intensity = classify_explicit_event(user_text)
    if event:
        emotion.apply(event, intensity)
    agent = SylusAgent(
        model=OpenAICompatibleChatModel(),
        retriever=PostgresMemoryRetriever(),
        writer=ExplicitOnlyMemoryWriter(),
        persona=load_persona() + ("\n\n" + time_context if time_context else ""),
        emotion=emotion,
    )
    answer = agent.reply(user_text=user_text, recent_history=history, source_message_id=source_message_id)
    save_emotion_state(agent.emotion, previous, event, source_message_id)
    return answer
