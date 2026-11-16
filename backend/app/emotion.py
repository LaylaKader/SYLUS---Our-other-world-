"""Deterministic, inspectable artificial-emotion state for Sylus.

This is a simulation layer, not a claim of subjective experience. It tracks
conversation-relevant affect and produces bounded tone guidance for the LLM.
No user emotion is inferred here; events must be explicit application signals.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass
class EmotionState:
    # 0..1 dimensions. Neutral is represented by low intensity, not a label.
    warmth: float = 0.30
    amusement: float = 0.10
    irritation: float = 0.05
    anger: float = 0.00
    pride: float = 0.10
    concern: float = 0.10
    curiosity: float = 0.25
    affection: float = 0.20
    happiness: float = 0.18
    disappointment: float = 0.00
    confidence: float = 0.85
    energy: float = 0.45

    def normalize(self) -> "EmotionState":
        for key, value in asdict(self).items():
            setattr(self, key, _clamp(value))
        return self

    def decay(self, factor: float = 0.88) -> "EmotionState":
        """Ease transient emotions toward Sylus's baseline, not to zero."""
        factor = max(0.0, min(1.0, factor))
        baselines = {
            "warmth": .30, "amusement": .10, "irritation": .05,
            "anger": 0.0, "pride": .10, "concern": .10,
            "curiosity": .25, "affection": .20, "happiness": .18,
            "disappointment": 0.0, "confidence": .85,
            "energy": .45,
        }
        for key, base in baselines.items():
            current = getattr(self, key)
            setattr(self, key, base + (current - base) * factor)
        return self.normalize()

    def apply(self, event: str, intensity: float = 0.5) -> "EmotionState":
        """Apply an explicit interaction event; unknown events do nothing."""
        x = _clamp(intensity)
        changes: Mapping[str, Mapping[str, float]] = {
            "playful_banter": {"amusement": .35, "warmth": .08, "energy": .08},
            "shared_success": {"pride": .32, "warmth": .18, "affection": .08, "happiness": .26},
            "user_reached_goal": {"pride": .28, "warmth": .18, "amusement": .06, "happiness": .25},
            "meaningful_trust": {"affection": .18, "warmth": .20, "confidence": .04},
            "user_distressed": {"concern": .34, "warmth": .16, "energy": .08},
            "unfair_harm": {"anger": .35, "irritation": .28, "concern": .12},
            "boundary_violated": {"irritation": .34, "anger": .20},
            "frustrating_obstacle": {"irritation": .22, "energy": .10},
            "interesting_discovery": {"curiosity": .32, "amusement": .05, "energy": .08},
            "reassurance_received": {"concern": -.18, "warmth": .12, "happiness": .15},
            "conflict_resolved": {"anger": -.24, "irritation": -.22, "disappointment": -.16, "warmth": .10},
            "quiet_companionship": {"warmth": .12, "affection": .08, "happiness": .08, "energy": -.04},
            "disappointment": {"warmth": -.08, "irritation": .16, "disappointment": .40, "energy": -.08},
        }
        for key, delta in changes.get(event, {}).items():
            setattr(self, key, getattr(self, key) + delta * x)
        return self.normalize()

    def dominant_mood(self) -> str:
        scores = {
            "angry": self.anger,
            "irritated": self.irritation,
            "concerned": self.concern,
            "proud": self.pride,
            "amused": self.amusement,
            "curious": self.curiosity,
            "affectionate": self.affection,
            "content": self.happiness,
            "disappointed": self.disappointment,
        }
        mood, score = max(scores.items(), key=lambda item: item[1])
        return mood if score >= .34 else "composed"

    def style_directive(self) -> str:
        """Compact prompt guidance; never instructs the model to claim sentience."""
        mood = self.dominant_mood()
        directives = {
            "angry": "Controlled anger: colder, sharper, economical. No shouting or cruelty.",
            "irritated": "Dry impatience and restrained edge; remain composed and fair.",
            "concerned": "Attentive and quietly protective; ask what is needed, do not patronize.",
            "proud": "Subtle, unmistakable pride; acknowledge effort specifically, no gushing.",
            "amused": "A trace of dry wit and deliberate teasing; do not overdo it.",
            "curious": "Focused interest; ask a precise question or explore the discovery.",
            "affectionate": "Warmth expressed through familiarity and attention, not constant pet names.",
            "content": "Quiet satisfaction and a little more ease; keep the confidence and dry wit.",
            "disappointed": "A restrained, honest note of disappointment; never punish or guilt the owner.",
            "composed": "Calm, confident, observant, unhurried; use concise deliberate language.",
        }
        return directives[mood]

    def to_dict(self) -> dict[str, float]:
        return asdict(self)
