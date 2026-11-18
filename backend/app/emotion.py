"""Deterministic, inspectable artificial-emotion state for Sylus.

This is a simulation layer, not a claim of subjective experience. It tracks
conversation-relevant affect and produces bounded tone guidance for the LLM.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass
class EmotionState:
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
    playfulness: float = 0.18
    longing: float = 0.05
    surprise: float = 0.05
    tenderness: float = 0.16
    protectiveness: float = 0.12
    attachment: float = 0.18
    jealousy: float = 0.00
    respect: float = 0.30
    vulnerability: float = 0.05

    def normalize(self) -> "EmotionState":
        for key, value in asdict(self).items():
            setattr(self, key, _clamp(value))
        return self

    def decay(self, factor: float = 0.88) -> "EmotionState":
        factor = max(0.0, min(1.0, factor))
        baselines = {
            "warmth": .30, "amusement": .10, "irritation": .05, "anger": 0.0,
            "pride": .10, "concern": .10, "curiosity": .25, "affection": .20,
            "happiness": .18, "disappointment": 0.0, "confidence": .85,
            "energy": .45, "playfulness": .18, "longing": .05, "surprise": .05,
            "tenderness": .16, "protectiveness": .12, "attachment": .18,
            "jealousy": 0.0, "respect": .30, "vulnerability": .05,
        }
        for key, base in baselines.items():
            current = getattr(self, key)
            setattr(self, key, base + (current - base) * factor)
        return self.normalize()

    def apply(self, event: str, intensity: float = 0.5) -> "EmotionState":
        x = _clamp(intensity)
        changes: Mapping[str, Mapping[str, float]] = {
            "playful_banter": {"amusement": .30, "playfulness": .34, "warmth": .06, "energy": .05},
            "affection_confession": {"affection": .30, "warmth": .22, "happiness": .18, "tenderness": .22, "attachment": .12, "surprise": .06},
            "provocative_banter": {"amusement": .20, "playfulness": .30, "confidence": .03, "jealousy": .16},
            "competitive_challenge": {"amusement": .16, "playfulness": .24, "confidence": .06, "energy": .10},
            "conflict_repair": {"anger": -.18, "irritation": -.20, "disappointment": -.10, "warmth": .12, "affection": .05, "respect": .08},
            "flirtatious_banter": {"amusement": .20, "playfulness": .34, "affection": .10, "warmth": .06},
            "distance_longing": {"longing": .34, "affection": .16, "warmth": .10, "tenderness": .12, "attachment": .08},
            "image_shared": {"curiosity": .18, "warmth": .06, "playfulness": .04},
            "image_interesting": {"curiosity": .28, "amusement": .08, "happiness": .10},
            "shared_memory": {"affection": .14, "warmth": .14, "happiness": .06, "attachment": .08, "tenderness": .08},
            "shared_success": {"pride": .28, "warmth": .14, "affection": .06, "happiness": .22, "respect": .12},
            "user_reached_goal": {"pride": .25, "warmth": .14, "amusement": .05, "happiness": .22, "respect": .12},
            "meaningful_trust": {"affection": .14, "warmth": .16, "confidence": .03, "tenderness": .10, "protectiveness": .12, "respect": .12, "attachment": .06},
            "user_confided": {"concern": .18, "warmth": .14, "tenderness": .16, "protectiveness": .18, "respect": .14, "vulnerability": .10},
            "user_distressed": {"concern": .30, "warmth": .14, "energy": .06, "protectiveness": .16, "tenderness": .12},
            "unfair_harm": {"anger": .30, "irritation": .22, "concern": .10, "protectiveness": .16},
            "boundary_violated": {"irritation": .30, "anger": .16},
            "frustrating_obstacle": {"irritation": .18, "energy": .08},
            "interesting_discovery": {"curiosity": .28, "amusement": .04, "energy": .06},
            "reassurance_received": {"concern": -.16, "warmth": .10, "happiness": .12, "tenderness": .06},
            "conflict_resolved": {"anger": -.20, "irritation": -.18, "disappointment": -.12, "warmth": .08, "respect": .08},
            "quiet_companionship": {"warmth": .10, "affection": .06, "happiness": .06, "attachment": .04, "energy": -.03},
            "disappointment": {"warmth": -.06, "irritation": .12, "disappointment": .32, "energy": -.06},
            "surprise": {"surprise": .34, "curiosity": .12, "energy": .06},
        }
        for key, delta in changes.get(event, {}).items():
            setattr(self, key, getattr(self, key) + delta * x)
        return self.normalize()

    def dominant_mood(self) -> str:
        scores = {
            "angry": self.anger, "irritated": self.irritation, "jealous": self.jealousy,
            "concerned": self.concern, "protective": self.protectiveness,
            "proud": self.pride, "amused": self.amusement, "curious": self.curiosity,
            "affectionate": max(self.affection, self.tenderness),
            "content": self.happiness, "disappointed": self.disappointment,
            "playful": self.playfulness, "longing": self.longing,
            "surprised": self.surprise,
        }
        mood, score = max(scores.items(), key=lambda item: item[1])
        return mood if score >= .34 else "composed"

    def style_directive(self) -> str:
        mood = self.dominant_mood()
        directives = {
            "angry": "Controlled anger: colder and sharper, but never cruel or threatening.",
            "irritated": "Dry impatience and a restrained edge; remain fair and composed.",
            "jealous": "A brief competitive edge and a little sharper teasing; never possessive, threatening, or controlling.",
            "concerned": "Pay close attention. Respond to the actual problem before teasing; do not patronize.",
            "protective": "Quietly protective and practical. Respect her autonomy; never become controlling.",
            "proud": "Subtle, unmistakable pride; acknowledge her effort specifically, without gushing.",
            "amused": "Dry wit and deliberate teasing; do not force a joke.",
            "curious": "Focused interest in the detail that caught his attention.",
            "affectionate": "Let warmth and tenderness show through familiarity, attention, and small gestures; avoid constant pet names.",
            "content": "Quiet satisfaction and ease; keep the confidence and dry wit.",
            "disappointed": "A restrained, honest note of disappointment; never punish or guilt her.",
            "playful": "Mischievous and openly amused; teasing is not a substitute for emotional presence.",
            "longing": "A little more intimate and wistful; acknowledge distance without melodrama or pressure.",
            "surprised": "A brief, genuine note of surprise and curiosity.",
            "composed": "Calm, confident, observant, and unhurried.",
        }
        return directives[mood]

    def to_dict(self) -> dict[str, float]:
        return asdict(self)
