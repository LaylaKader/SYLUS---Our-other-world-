"""Sylus agent orchestration with memory retrieval and emotional style context."""
from dataclasses import dataclass
from typing import Protocol

from .emotion import EmotionState


@dataclass
class RetrievedMemory:
    category: str
    content: str
    confidence: float
    source: str


class ChatModel(Protocol):
    def respond(self, *, persona: str, recent_history: list[dict], memories: list[RetrievedMemory], user_text: str) -> str: ...


class MemoryRetriever(Protocol):
    def retrieve(self, *, query: str, limit: int = 8) -> list[RetrievedMemory]: ...


class MemoryWriter(Protocol):
    def extract_and_store(self, *, user_text: str, assistant_text: str, source_message_id: str) -> None: ...


class SylusAgent:
    def __init__(
        self,
        model: ChatModel,
        retriever: MemoryRetriever,
        writer: MemoryWriter,
        persona: str,
        emotion: EmotionState | None = None,
    ):
        self.model = model
        self.retriever = retriever
        self.writer = writer
        self.persona = persona
        self.emotion = emotion or EmotionState()

    def apply_emotion_event(self, event: str, intensity: float = 0.5) -> None:
        """Apply a classified/explicit event before the next response."""
        self.emotion.apply(event, intensity)

    def reply(self, *, user_text: str, recent_history: list[dict], source_message_id: str) -> str:
        memories = self.retriever.retrieve(query=user_text, limit=5)
        emotional_context = (
            "\\n\\nCurrent simulated emotional state (internal style guidance): "
            f"{self.emotion.dominant_mood()}. {self.emotion.style_directive()} "
            "Express this subtly and consistently with Sylus. Do not describe the state "
            "as a diagnostic readout or claim human subjective experience."
        )
        answer = self.model.respond(
            persona=self.persona + emotional_context,
            recent_history=recent_history,
            memories=memories,
            user_text=user_text,
        )
        self.writer.extract_and_store(
            user_text=user_text,
            assistant_text=answer,
            source_message_id=source_message_id,
        )
        self.emotion.decay()
        return answer
