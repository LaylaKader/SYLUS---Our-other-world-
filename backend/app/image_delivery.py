"""Private media-delivery intent helpers for the SYLUS chat pipeline."""
from __future__ import annotations

import re

_IMAGE_DIRECTIVE = re.compile(r"\[\[SYLUS_IMAGE:\s*(.*?)\]\]", re.I | re.S)
_LINK_DIRECTIVE = re.compile(r"\[\[SYLUS_LINK:\s*(.*?)\]\]", re.I | re.S)


def extract_image_directive(text: str) -> tuple[str, str | None]:
    """Remove the private image-generation directive and return its visual prompt."""
    match = _IMAGE_DIRECTIVE.search(text or "")
    if not match:
        return (text or "").strip(), None
    prompt = re.sub(r"\s+", " ", match.group(1)).strip()[:1800]
    clean = (text[:match.start()] + text[match.end():]).strip()
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean, prompt or None


def extract_link_directive(text: str) -> tuple[str, str | None]:
    """Remove the private link-search directive and return its search query."""
    match = _LINK_DIRECTIVE.search(text or "")
    if not match:
        return (text or "").strip(), None
    query = re.sub(r"\s+", " ", match.group(1)).strip()[:220]
    clean = (text[:match.start()] + text[match.end():]).strip()
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean, query or None


def should_generate_image(text: str) -> bool:
    """Detect direct requests for a newly created image, not image discussion/search."""
    value = (text or "").strip().lower()
    if not value:
        return False
    patterns = (
        r"\b(?:send|make|create|generate|draw|paint)\b.{0,100}\b(?:me\s+)?(?:an?\s+)?(?:image|picture|photo|illustration|artwork|portrait|drawing)\b",
        r"\b(?:send me|show me)\s+(?:it|that|the image|the picture|the photo)\b",
        r"\bcan you\s+(?:draw|make|create|generate|paint)\b",
    )
    return any(re.search(pattern, value, re.I) for pattern in patterns)
