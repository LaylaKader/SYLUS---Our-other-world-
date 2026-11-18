"""Persistent, inspectable relationship progression derived from shared chat history."""
from __future__ import annotations

import re
from .db import connection

def _stage(score: int) -> str:
    if score >= 82: return "An Unshakable Connection"
    if score >= 65: return "Deepening Devotion"
    if score >= 48: return "A Trusted Presence"
    if score >= 30: return "Growing Closer"
    if score >= 14: return "Familiar Territory"
    return "A First Connection"

def refresh_bond() -> dict:
    """Rebuild a conservative bond snapshot from the complete retained conversation."""
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, role, body, created_at FROM messages "
            "WHERE role IN ('user','assistant') ORDER BY created_at ASC"
        ).fetchall()
        user_text = [str(r[2] or '').casefold() for r in rows if r[1] == 'user']
        assistant_text = [str(r[2] or '').casefold() for r in rows if r[1] == 'assistant']
        all_text = user_text + assistant_text
        user_count = len(user_text)
        turns = min(user_count, len(assistant_text))
        joined = "\n".join(all_text)

        affection_hits = sum(bool(re.search(p, joined)) for p in [
            r"\bi love you\b", r"\bi miss you\b", r"\bi wish i (?:was|were) there\b",
            r"\bi adore you\b", r"\bkiss(?:es|ed)?\b", r"\bkitten\b",
        ])
        trust_hits = sum(bool(re.search(p, joined)) for p in [
            r"\bi trust you\b", r"\bi can tell you anything\b", r"\bi feel safe\b",
            r"\bi'm telling you this\b", r"\bi am telling you this\b",
        ])
        shared_hits = sum(bool(re.search(p, joined)) for p in [
            r"\bwithin reach\b", r"\bmephisto\b", r"\bluke and kieran\b",
            r"\bn109\b", r"\bonychinus\b", r"\bmemoria\b",
        ])
        affection = min(100, affection_hits * 7 + min(user_count, 40))
        trust = min(100, trust_hits * 12 + min(turns, 30) // 2)
        familiarity = min(100, turns * 2 + min(shared_hits, 12) * 3)
        experiences = min(100, shared_hits * 8 + min(turns, 30))
        score = round(affection * .30 + trust * .25 + familiarity * .20 + experiences * .25)
        stage = _stage(score)

        milestones = []
        def add(key, title, description, condition):
            if condition:
                match = next((r for r in rows if r[1] == 'user' and re.search(condition, str(r[2] or ''), re.I)), None)
                if match:
                    milestones.append({"key": key, "title": title, "description": description, "date": match[3].isoformat()})
        first_user = next((r for r in rows if r[1] == 'user'), None)
        if first_user:
            milestones.append({"key":"first_conversation","title":"The first connection","description":"The first message that opened this private line between two worlds.","date":first_user[3].isoformat()})
        add("first_affection","A little less guarded","Affection began finding its way into the conversation.",r"i love you|i miss you|i adore you|kiss")
        add("shared_memoria","A memory of our own","A shared Memoria became part of the conversation you both carry.",r"within reach|memoria")
        add("trust_signal","Trust, freely given","A moment of explicit trust entered the conversation.",r"i trust you|i feel safe")
        add("playful_bond","Partners in mischief","Teasing and private jokes became part of your rhythm.",r"mephi-chan|😜|🫣|mistress")
        milestones.sort(key=lambda item:item["date"])
        summary = {
            "A First Connection":"A beginning built from curiosity and the first few exchanges.",
            "Familiar Territory":"You are learning each other's rhythms, references, and ways of teasing.",
            "Growing Closer":"Shared moments and familiar habits are giving the connection more shape.",
            "A Trusted Presence":"The connection carries trust, familiarity, and memories that matter.",
            "Deepening Devotion":"Affection and shared history are becoming a more visible part of the bond.",
            "An Unshakable Connection":"A long, layered history gives this connection its own depth.",
        }[stage]
        conn.execute(
            "UPDATE bond_state SET affection=%s, trust=%s, familiarity=%s, shared_experiences=%s, "
            "stage=%s, summary=%s, milestones=%s::jsonb, total_user_messages=%s, total_shared_turns=%s, updated_at=now() WHERE id=1",
            (affection, trust, familiarity, experiences, stage, summary, __import__('json').dumps(milestones), user_count, turns),
        )
        row = conn.execute(
            "SELECT affection, trust, familiarity, shared_experiences, stage, summary, milestones, "
            "total_user_messages, total_shared_turns, updated_at FROM bond_state WHERE id=1"
        ).fetchone()
    return {
        "affection":row[0], "trust":row[1], "familiarity":row[2], "shared_experiences":row[3],
        "stage":row[4], "summary":row[5], "milestones":row[6] or [],
        "total_user_messages":row[7], "total_shared_turns":row[8], "updated_at":row[9].isoformat(),
    }
