"""Runnable, replaceable OpenAI-compatible chat adapter for the private owner instance."""
from __future__ import annotations

from pathlib import Path
from typing import Any
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
            f"- [{m.category}; confidence {m.confidence:.2f}] {m.content}"
            for m in memories
        ) or "No relevant saved memories were retrieved."
        system_prompt = (
            f"{persona}\n\n"
            "PRIVATE OWNER CONTEXT (use only when relevant; never recite it as a dossier):\n"
            f"{memory_context}\n\n"
            "Be accurate about current time and continuity. Do not invent shared experiences or canon. "
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
    """Automatic extraction is deliberately disabled until owner review/edit controls exist."""

    def extract_and_store(self, *, user_text: str, assistant_text: str, source_message_id: str) -> None:
        return None


def load_persona() -> str:
    path = Path(__file__).resolve().parents[2] / "character" / "SYLUS_PERSONA.md"
    if not path.exists():
        return "Portray Sylus as composed, perceptive, confident, strategic, dry-witted, and unhurried. Respect autonomy."
    return path.read_text(encoding="utf-8")


def generate_reply(user_text: str, source_message_id: str, history: list[dict]) -> str:
    agent = SylusAgent(
        model=OpenAICompatibleChatModel(),
        retriever=PostgresMemoryRetriever(),
        writer=ExplicitOnlyMemoryWriter(),
        persona=load_persona(),
        emotion=EmotionState(),
    )
    return agent.reply(user_text=user_text, recent_history=history, source_message_id=source_message_id)
