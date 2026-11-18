"""Event-led, persistent relationship progression for the private Sylus companion."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from .db import connection


STAGES = [
    (1, 0, "A First Encounter", "A beginning. Neither of you knows yet what this connection may become."),
    (2, 20, "Familiar Faces", "The first patterns are taking shape; familiar words and habits are beginning to matter."),
    (3, 50, "A Private Rhythm", "You are finding a rhythm that belongs to the two of you."),
    (4, 90, "Trusted Company", "Comfort is growing. Silence and conversation both feel more natural."),
    (5, 140, "The First Confidences", "Small truths are being entrusted, remembered, and treated with care."),
    (6, 200, "Closer Than Before", "Shared history is beginning to influence how openly you meet each other."),
    (7, 280, "A Chosen Constant", "Consistency matters now. This connection has become part of the shape of your days."),
    (8, 380, "Under the Guard", "More vulnerability is met with understanding; the guarded parts are not always hidden."),
    (9, 500, "深い絆 · Deepening Bond", "Affection, trust, and shared history are reinforcing one another."),
    (10, 650, "An Intimate Alliance", "You know how to challenge, reassure, and stand beside one another."),
    (11, 830, "Beyond the Distance", "The bond has its own language, continuity, and a depth built over time."),
    (12, 1050, "An Unbreakable Promise", "A rare, deeply established connection shaped by everything you have chosen to share."),
]

def _clamp(value: float) -> int:
    return max(0, min(100, int(round(value))))

def _signals(text: str) -> list[tuple[str, str, str, dict[str, int], int]]:
    """Return grounded, user-authored signals. One message can earn at most two distinct events."""
    value = text.casefold()
    found = []
    rules = [
        ("affection", "Affection shared", "An affectionate moment was openly shared.", r"\bi love you\b|\bi adore you\b|\bi miss you\b|\bi wish we (?:could|were) together\b", {"affection": 7, "commitment": 2}, 9),
        ("trust", "Trust offered", "A moment of explicit trust or personal confidence was shared.", r"\bi trust you\b|\bi feel safe with you\b|\bi can tell you anything\b|\bi want to tell you something personal\b", {"trust": 8, "emotional_safety": 6, "vulnerability": 3}, 10),
        ("vulnerability", "A guarded truth", "Umi shared a difficult feeling or personal vulnerability.", r"\bi feel (?:scared|afraid|lonely|overwhelmed|hopeless|insecure)\b|\bi(?:'m| am) (?:struggling|not okay|having a hard time)\b|\bi have never told anyone\b", {"vulnerability": 7, "emotional_safety": 4, "trust": 3}, 9),
        ("repair", "A moment of repair", "A disagreement or hurt was approached with honesty and care.", r"\bi(?:'m| am) sorry\b|\bi didn't mean to hurt\b|\blet's talk this through\b|\bi forgive you\b|\bcan we work this out\b", {"trust": 3, "emotional_safety": 5, "commitment": 3}, 8),
        ("shared_memory", "A memory revisited", "A shared story, Memoria, or meaningful detail was brought back into the present.", r"\bmemoria\b|\bwithin reach\b|\bthe first time we\b|\bremember when we\b|\bour memory\b", {"familiarity": 5, "shared_experiences": 7, "affection": 1}, 8),
        ("shared_world", "A world in common", "A meaningful part of the shared N109 world or its people entered the conversation.", r"\bmephisto\b|\bn109\b|\bonychinus\b|\bluke and kieran\b|\bciren\b|\bsenlu\b", {"familiarity": 3, "shared_experiences": 4}, 4),
        ("achievement", "A win worth sharing", "A personal achievement or difficult step was shared.", r"\bi (?:passed|got accepted|got the offer|finished|submitted|won|succeeded)\b|\bi did it\b|\bi finally (?:managed|completed)\b", {"shared_experiences": 4, "commitment": 2, "affection": 2}, 7),
        ("playful", "A private joke", "Playful teasing or a recurring in-joke added to your shared rhythm.", r"\bmephi-chan\b|\bmistress\b|\bkitten\b|😜|😏|🫣|🤭|🤣|😂|\byou're impossible\b|\btry me\b", {"familiarity": 3, "affection": 1}, 3),
        ("gratitude", "Care acknowledged", "Umi acknowledged a moment of care or understanding.", r"\bthank you for listening\b|\bthat helped me\b|\bi appreciate you\b|\bi'm glad i told you\b|\bi feel better now\b", {"emotional_safety": 4, "trust": 2, "affection": 2}, 6),
        ("shared_media", "Something shown to each other", "A picture, song, or small discovery was shared between you.", r"\bshared an image\b|\blook at (?:this|that|the picture)\b|\bi just saw (?:a|this) (?:reel|video|picture|photo)\b|\blisten to this\b", {"shared_experiences": 3, "familiarity": 2}, 4),
        ("daily_life", "A detail from everyday life", "A small detail from ordinary life became part of your shared context.", r"\bwhat are you doing\b|\bhow was your day\b|\bgood morning\b|\bgood night\b|\bi'm back\b|\bim back\b", {"familiarity": 2, "shared_experiences": 1}, 2),
        ("trust_breach", "Trust needs repair", "A clear statement of broken trust or a broken promise was expressed.", r"\bi can't trust you\b|\byou lied to me\b|\byou broke your promise\b|\byou ignored my boundary\b|\bi don't feel safe with you\b", {"trust": -10, "emotional_safety": -9, "commitment": -3}, -6),
        ("commitment", "Choosing to return", "A clear intention to keep building the connection was expressed.", r"\bi want us to\b|\bi want to keep (?:this|building)\b|\bi choose you\b|\bi'm not going anywhere\b|\blet's keep (?:this|going)\b", {"commitment": 8, "trust": 2, "affection": 2}, 10),
    ]
    for key, title, description, pattern, gains, points in rules:
        if re.search(pattern, value, re.I):
            found.append((key, title, description, gains, points))
    # Avoid rewarding a single message for many overlapping keywords.
    priority = {"trust_breach": 0, "trust": 1, "vulnerability": 2, "repair": 3, "commitment": 4, "affection": 5, "gratitude": 6, "achievement": 7, "shared_memory": 8, "shared_media": 9, "shared_world": 10, "daily_life": 11, "playful": 12}
    return sorted(found, key=lambda item: priority.get(item[0], 99))[:2]

def _stage(points: int) -> tuple[int, str, str, int, int]:
    current = STAGES[0]
    next_stage = STAGES[1]
    for index, item in enumerate(STAGES):
        if points >= item[1]:
            current = item
            next_stage = STAGES[min(index + 1, len(STAGES) - 1)]
        else:
            break
    return current[0], current[2], current[3], current[1], next_stage[1]

def refresh_bond() -> dict:
    """Backfill unseen user events once, then return the durable relationship state."""
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, body, created_at FROM messages WHERE role='user' ORDER BY created_at ASC"
        ).fetchall()
        for message_id, body, created_at in rows:
            for key, title, description, gains, points in _signals(str(body or "")):
                # A category can contribute once per Dhaka-local calendar day, not once per repeated phrase.
                event_key = f"day:{created_at.date().isoformat()}:{key}"
                inserted = conn.execute(
                    "INSERT INTO bond_events (event_key, title, description, source_message_id) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT (event_key) DO NOTHING RETURNING id",
                    (event_key, title, description, message_id),
                ).fetchone()
                if inserted:
                    conn.execute(
                        "UPDATE bond_state SET affection=GREATEST(0,LEAST(100, affection+%s)), trust=GREATEST(0,LEAST(100, trust+%s)), "
                        "familiarity=GREATEST(0,LEAST(100, familiarity+%s)), shared_experiences=GREATEST(0,LEAST(100, shared_experiences+%s)), "
                        "commitment=GREATEST(0,LEAST(100, commitment+%s)), vulnerability=GREATEST(0,LEAST(100, vulnerability+%s)), "
                        "emotional_safety=GREATEST(0,LEAST(100, emotional_safety+%s)), bond_points=GREATEST(0,bond_points+%s), updated_at=now() WHERE id=1",
                        (gains.get("affection",0), gains.get("trust",0), gains.get("familiarity",0),
                         gains.get("shared_experiences",0), gains.get("commitment",0), gains.get("vulnerability",0),
                         gains.get("emotional_safety",0), points),
                    )

        call_rows = conn.execute("SELECT transcript, started_at FROM call_sessions").fetchall()
        call_user_count = 0
        call_assistant_count = 0
        call_days = set()
        for transcript, started_at in call_rows:
            call_days.add(started_at.date())
            for item in (transcript or []):
                if item.get("role") == "user" and item.get("text"):
                    call_user_count += 1
                    for key, title, description, gains, points in _signals(str(item["text"])):
                        event_key = f"day:{started_at.date().isoformat()}:{key}"
                        inserted = conn.execute(
                            "INSERT INTO bond_events (event_key,title,description,source_message_id) "
                            "VALUES (%s,%s,%s,NULL) ON CONFLICT (event_key) DO NOTHING RETURNING id",
                            (event_key,title,description),
                        ).fetchone()
                        if inserted:
                            conn.execute(
                                "UPDATE bond_state SET affection=GREATEST(0,LEAST(100,affection+%s)), "
                                "trust=GREATEST(0,LEAST(100,trust+%s)), familiarity=GREATEST(0,LEAST(100,familiarity+%s)), "
                                "shared_experiences=GREATEST(0,LEAST(100,shared_experiences+%s)), "
                                "commitment=GREATEST(0,LEAST(100,commitment+%s)), vulnerability=GREATEST(0,LEAST(100,vulnerability+%s)), "
                                "emotional_safety=GREATEST(0,LEAST(100,emotional_safety+%s)), bond_points=GREATEST(0,bond_points+%s), updated_at=now() WHERE id=1",
                                (gains.get("affection",0),gains.get("trust",0),gains.get("familiarity",0),
                                 gains.get("shared_experiences",0),gains.get("commitment",0),gains.get("vulnerability",0),
                                 gains.get("emotional_safety",0),points),
                            )
                elif item.get("role") == "assistant":
                    call_assistant_count += 1

        user_count = len(rows) + call_user_count
        turns = min(user_count, conn.execute(
            "SELECT count(*) FROM messages WHERE role='assistant'"
        ).fetchone()[0] + call_assistant_count)
        active_days = len({r[2].date() for r in rows if r[2]} | call_days)
        # Familiarity and consistency reward time spent together, but both have diminishing returns.
        last_activity = max((r[2] for r in rows if r[2]), default=None)
        inactive_days = max(0, (datetime.now(timezone.utc).date() - last_activity.date()).days) if last_activity else 0
        # Consistency and familiarity soften gradually during long absences; trust and affection
        # are not automatically punished for taking a break.
        time_decay = 0.5 ** (inactive_days / 120)
        consistency = _clamp(min(100, active_days * 4) * time_decay)
        familiarity_from_time = _clamp(min(24, turns * 0.35) * time_decay)
        # Gentle activity progress keeps the chapter moving during ordinary conversation,
        # while explicit trust, affection, repair, and shared-memory events remain the main rewards.
        # Five completed shared turns add two points; active days add two points each.
        activity_points = min(60, active_days * 2 + (turns // 5) * 2)
        conn.execute(
            "UPDATE bond_state SET familiarity=GREATEST(familiarity,%s), consistency=%s, "
            "bond_points=GREATEST(bond_points, %s), total_user_messages=%s, total_shared_turns=%s WHERE id=1",
            (familiarity_from_time, consistency, activity_points, user_count, turns),
        )
        state = conn.execute(
            "SELECT affection, trust, familiarity, shared_experiences, commitment, vulnerability, "
            "emotional_safety, consistency, bond_points, level, stage, summary, milestones, "
            "total_user_messages, total_shared_turns, updated_at FROM bond_state WHERE id=1"
        ).fetchone()
        points = int(state[8] or 0)
        level, stage, summary, floor_points, next_points = _stage(points)
        progress = 100 if level == 12 else _clamp((points-floor_points) / max(1, next_points-floor_points) * 100)
        milestones = conn.execute(
            "SELECT event_key, title, description, created_at FROM bond_events ORDER BY created_at DESC LIMIT 60"
        ).fetchall()
        milestone_list = [
            {"key":r[0], "title":r[1], "description":r[2], "date":r[3].isoformat()}
            for r in reversed(milestones)
        ]
        conn.execute(
            "UPDATE bond_state SET level=%s, stage=%s, summary=%s, milestones=%s::jsonb, updated_at=now() WHERE id=1",
            (level, stage, summary, __import__("json").dumps(milestone_list)),
        )
        updated = conn.execute("SELECT updated_at FROM bond_state WHERE id=1").fetchone()[0]
    return {
        "affection":state[0], "trust":state[1], "familiarity":state[2], "shared_experiences":state[3],
        "commitment":state[4], "vulnerability":state[5], "emotional_safety":state[6],
        "consistency":consistency, "bond_points":points, "level":level, "level_progress":progress,
        "points_to_next_level":max(0,next_points-points) if level < 12 else 0,
        "stage":stage, "summary":summary, "next_stage":STAGES[level][2] if level < 12 else "The deepest bond",
        "all_stages":[{"level":item[0],"name":item[2],"threshold":item[1]} for item in STAGES],
        "milestones":milestone_list,
        "total_user_messages":state[13], "total_shared_turns":state[14],
        "updated_at":updated.isoformat(),
    }
