"""Replaceable private image-generation adapter for assistant-created image messages.

Provider implementations must return image bytes and metadata. Keep provider API
keys on the server; never expose them to the Android/web client.
"""
from dataclasses import dataclass
from typing import Protocol


@dataclass
class GeneratedImage:
    image_bytes: bytes
    mime_type: str
    provider: str
    revised_prompt: str | None = None
    metadata: dict | None = None


class ImageGenerator(Protocol):
    def generate(
        self,
        *,
        prompt: str,
        style_context: str,
        aspect_ratio: str = "1:1",
    ) -> GeneratedImage:
        """Generate one image and return bytes; raise a provider error on failure."""
        ...


class PrivateMediaStorage(Protocol):
    def put(
        self,
        *,
        owner_id: str,
        content: bytes,
        mime_type: str,
        file_extension: str,
    ) -> str:
        """Store privately and return an opaque storage key, never a public URL."""
        ...

    def get_signed_url(self, *, storage_key: str, expires_in_seconds: int = 300) -> str:
        """Return a short-lived, owner-authorized URL for display."""
        ...


class SylusImageService:
    def __init__(self, generator: ImageGenerator, storage: PrivateMediaStorage):
        self.generator = generator
        self.storage = storage

    def create_image(
        self,
        *,
        owner_id: str,
        prompt: str,
        style_context: str,
        aspect_ratio: str = "1:1",
    ) -> tuple[str, GeneratedImage]:
        result = self.generator.generate(
            prompt=prompt,
            style_context=style_context,
            aspect_ratio=aspect_ratio,
        )
        extension = "png" if result.mime_type == "image/png" else "webp"
        key = self.storage.put(
            owner_id=owner_id,
            content=result.image_bytes,
            mime_type=result.mime_type,
            file_extension=extension,
        )
        return key, result
