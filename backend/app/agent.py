"""Agent orchestration interfaces.

The model provider is deliberately not hard-coded. A provider can be added later
without coupling chat persistence, character canon, or personal memory to it.
"""
from dataclasses import dataclass
from typing import Protocol

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
    def __init__(self, model: ChatModel, retriever: MemoryRetriever, writer: MemoryWriter, persona: str):
        self.model = model
        self.retriever = retriever
        self.writer = writer
        self.persona = persona

    def reply(self, *, user_text: str, recent_history: list[dict], source_message_id: str) -> str:
        memories = self.retriever.retrieve(query=user_text, limit=8)
        answer = self.model.respond(persona=self.persona, recent_history=recent_history, memories=memories, user_text=user_text)
        self.writer.extract_and_store(user_text=user_text, assistant_text=answer, source_message_id=source_message_id)
        return answer
