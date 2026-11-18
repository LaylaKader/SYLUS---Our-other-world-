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
    """Only explicit creation requests invoke the generator; ordinary picture requests search online."""
    value = (text or "").strip()
    if not value:
        return False
    patterns = (
        r"\\b(?:make|create|generate|draw|paint|illustrate)\\b.{0,100}\\b(?:me\\s+)?(?:an?\\s+)?(?:image|picture|photo|illustration|artwork|portrait|drawing)\\b",
        r"\\bcan you\\s+(?:draw|make|create|generate|paint|illustrate)\\b",
        r"\\b(?:draw|make|create|generate|paint|illustrate)\\b.{0,80}\\b(?:you and me|us together|a new picture)\\b",
    )
    return any(re.search(pattern, value, re.I) for pattern in patterns)
