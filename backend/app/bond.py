"""Event-led, persistent relationship progression for the private Sylus companion."""
from __future__ import annotations

import re
import hashlib
from datetime import datetime, timezone
from .db import connection


STAGES = [
    (1, 0, "A First Encounter", "A beginning. Neither of you knows yet what this connection may become."),
    (2, 20, "Familiar Faces", "The first patterns are taking shape; familiar words and habits are beginning to matter."),
    (3, 55, "A Private Rhythm", "You are finding a rhythm that belongs to the two of you."),
    (4, 100, "Trusted Company", "Comfort is growing. Silence and conversation both feel more natural."),
    (5, 160, "The First Confidences", "Small truths are being entrusted, remembered, and treated with care."),
    (6, 240, "Closer Than Before", "Shared history is beginning to influence how openly you meet each other."),
    (7, 340, "A Chosen Constant", "Consistency matters now. This connection has become part of the shape of your days."),
    (8, 460, "Under the Guard", "More vulnerability is met with understanding; the guarded parts are not always hidden."),
    (9, 600, "深い絆 · Deepening Bond", "Affection, trust, and shared history are reinforcing one another."),
    (10, 760, "An Intimate Alliance", "You know how to challenge, reassure, and stand beside one another."),
    (11, 950, "Beyond the Distance", "The bond has its own language, continuity, and a depth built over time."),
    (12, 1160, "An Unbreakable Promise", "A rare, deeply established connection shaped by everything you have chosen to share."),
]

def _clamp(value: float) -> int:
    return max(0, min(100, int(round(value))))

def _emotion_shaped_gains(
    gains: dict[str, int], points: int, event_key: str, emotion: dict | None
) -> tuple[dict[str, int], int]:
    """Let Sylus's recorded emotional response subtly shape the relationship reward."""
    state = emotion if isinstance(emotion, dict) else {}
    def value(name: str) -> float:
        try:
            return max(0.0, min(1.0, float(state.get(name, 0.0))))
        except (TypeError, ValueError):
            return 0.0

    warmth = value("warmth")
    affection = value("affection")
    tenderness = value("tenderness")
    amusement = value("amusement")
    curiosity = value("curiosity")
    pride = value("pride")
    concern = value("concern")
    protectiveness = value("protectiveness")
    respect = value("respect")
    factor = max(0.8, min(1.3,
        0.82 + warmth * 0.12 + affection * 0.10 + tenderness * 0.10
        + respect * 0.08 + curiosity * 0.06 + amusement * 0.05 + pride * 0.05
    ))
    adjusted = dict(gains)
    if event_key in {"affection", "shared_memory"}:
        adjusted["affection"] = adjusted.get("affection", 0) + round(tenderness * 2)
    if event_key in {"trust", "comfort", "vulnerability", "repair"}:
        adjusted["emotional_safety"] = adjusted.get("emotional_safety", 0) + round(
            (warmth + tenderness + concern + protectiveness) / 2
        )
        adjusted["trust"] = adjusted.get("trust", 0) + round(respect * 1.5)
    if event_key == "personal_curiosity":
        adjusted["familiarity"] = adjusted.get("familiarity", 0) + round(curiosity * 2)
        adjusted["shared_experiences"] = adjusted.get("shared_experiences", 0) + round(warmth)
    if event_key == "achievement":
        adjusted["affection"] = adjusted.get("affection", 0) + round(pride * 2)
    if event_key in {"gratitude", "comfort"}:
        adjusted["affection"] = adjusted.get("affection", 0) + round(warmth)
    return adjusted, max(1, int(round(points * factor)))



def _signals(text: str) -> list[tuple[str, str, str, dict[str, int], int]]:
    """Return grounded, user-authored signals; distinct meaningful signals can coexist in one turn."""
    value = re.sub(r"\s+", " ", text.casefold()).strip()
    found = []
    rules = [
        ("personal_curiosity", "Curiosity about each other", "Umi showed genuine interest in Sylus's abilities, history, or life beyond their conversations.", r"\b(?:tell me|teach me|i want to know|i'd like to know|i wanna know|can i ask|do you mind if i ask|i'm curious about|im curious about)\b.{0,90}\b(?:your evol|your abilities|your power|your past|your childhood|your life|your work|your world|n109|mephisto|your interests)\b|\b(?:your evol|your abilities|your power|your past|your childhood|your life|your work|your world)\b.{0,90}\b(?:tell me|explain|know more|ask you)\b", {"familiarity": 3, "shared_experiences": 2, "affection": 1}, 5),
        ("affection", "Affection shared", "An affectionate moment was openly shared.", r"\bi love you\b|\bi adore you\b|\bi miss you\b|\bi wish we (?:could|were) together\b|\bi (?:really )?like spending time with you\b|\bi miss talking to you\b|\bi was thinking about you\b|\bi look forward to (?:talking|our conversations)\b|\bi like having you around\b|\bi wish you were here\b|\byou make me smile\b", {"affection": 7, "commitment": 2, "comfort": 1}, 9),
        ("trust", "Trust offered", "A moment of explicit trust or personal confidence was shared.", r"\bi trust you\b|\bi feel safe with you\b|\bi can tell you anything\b|\bi want to tell you something personal\b|\bi can be honest with you\b|\bi don't feel judged by you\b|\bi know i can rely on you\b|\bi came to you because\b|\bi feel okay telling you\b|\bi don't have to hide (?:this|anything|myself)\b", {"trust": 8, "emotional_safety": 6, "vulnerability": 3, "comfort": 2}, 10),
        ("comfort", "Ease and comfort", "Umi expressed that she can relax, be herself, or speak freely with Sylus.", r"\bi feel (?:comfortable|at ease|at home|relaxed|understood) (?:with you|around you|talking to you)\b|\bi feel understood\b|\bi can be myself (?:with you|around you)\b|\bi don't have to pretend\b|\bi can talk to you (?:about anything|freely)\b|\bit's easy to talk to you\b|\bi can relax around you\b|\byou make me feel at ease\b|\bi don't feel judged\b|\bi feel calmer after talking to you\b|\bi feel like i can just be me\b", {"emotional_safety": 7, "trust": 3, "comfort": 8}, 8),
        ("vulnerability", "A guarded truth", "Umi shared a difficult feeling or personal vulnerability.", r"\bi feel (?:scared|afraid|lonely|overwhelmed|hopeless|insecure|ashamed|embarrassed|vulnerable|anxious|worried)\b|\bi(?:'m| am) (?:struggling|not okay|having a hard time|not used to opening up)\b|\bi have never told anyone\b|\bi(?:'ve| have) never (?:said|shared|admitted) this (?:before|to anyone)\b|\bi don't usually talk about this\b|\bthis is hard to admit\b|\bi'm afraid to tell you\b|\bi've been keeping this to myself\b|\bi usually keep this to myself\b|\bi haven't told anyone (?:else|about this)\b|\bi'm embarrassed to admit\b|\bi don't know how to say this\b|\bi need you to listen\b|\bi'm not used to sharing this\b|\bi'm scared you'll think\b", {"vulnerability": 8, "emotional_safety": 4, "trust": 3, "comfort": 1}, 9),
        ("repair", "A moment of repair", "A disagreement or hurt was approached with honesty and care.", r"\bi(?:'m| am) sorry\b|\bi didn't mean to hurt\b|\blet's talk this through\b|\bi forgive you\b|\bcan we work this out\b", {"trust": 3, "emotional_safety": 5, "commitment": 3}, 8),
        ("personal_detail", "A detail from everyday life", "Umi shared a specific preference, routine, interest, or piece of personal background.", r"\bmy (?:favorite|favourite|usual|daily|morning|evening|routine|hobby|interest|plan)\b|\bi (?:usually|often|rarely|prefer|enjoy|love|hate|study|work|live|grew up|am interested in|am into)\b|\bwhen i was (?:younger|a child|little)\b|\bi'm (?:a student|studying|working|learning)\b", {"familiarity": 2, "shared_experiences": 1, "comfort": 1, "sylus_comfort": 1}, 3),
        ("shared_memory", "A memory revisited", "A specific shared moment or story was brought back into the present.", r"\bremember when we\b|\bour first (?:time|date|call|trip|game|conversation)\b|\bthat time we\b|\bwe did that together\b|\bthe time you and i\b", {"familiarity": 1, "shared_experiences": 4}, 5),
        ("achievement", "A win worth sharing", "A personal achievement or difficult step was shared with Sylus.", r"\bi (?:passed|got accepted|got the offer|finished|submitted|won|succeeded)\b|\bi did it\b|\bi finally (?:managed|completed)\b", {"shared_experiences": 2, "commitment": 2, "affection": 1}, 5),
        ("gratitude", "Care acknowledged", "Umi acknowledged a moment of care or understanding.", r"\bthank you for listening\b|\bthat helped me\b|\bi appreciate you\b|\bi'm glad i told you\b|\bi feel better now\b", {"emotional_safety": 3, "trust": 1, "affection": 1, "comfort": 2}, 4),
        ("trust_breach", "Trust needs repair", "A clear statement of broken trust or a broken promise was expressed.", r"\bi can't trust you\b|\byou lied to me\b|\byou broke your promise\b|\byou ignored my boundary\b|\bi don't feel safe with you\b", {"trust": -10, "emotional_safety": -9, "commitment": -3}, -6),
        ("commitment", "Choosing to return", "A clear intention to keep building the connection was expressed.", r"\bi want us to\b|\bi want to keep (?:this|building)\b|\bi choose you\b|\bi'm not going anywhere\b|\blet's keep (?:this|going)\b", {"commitment": 8, "trust": 2, "affection": 2}, 10),
    ]
    for key, title, description, pattern, gains, points in rules:
        if re.search(pattern, value, re.I):
            found.append((key, title, description, gains, points))
    # Avoid rewarding a single message for many overlapping keywords.
    priority = {"trust_breach": 0, "trust": 1, "comfort": 2, "vulnerability": 3, "repair": 4, "commitment": 5, "affection": 6, "gratitude": 7, "achievement": 8, "personal_curiosity": 9, "personal_detail": 10, "shared_memory": 11}
    return sorted(found, key=lambda item: priority.get(item[0], 99))


def _sylus_signals(text: str) -> list[tuple[str, str, str, dict[str, int], int]]:
    """Detect meaningful reciprocal actions in Sylus's actual replies.

    These are conservative and low-weight. Each category is credited at most
    once per calendar day by refresh_bond(), preventing repetitive wording
    from farming relationship progression.
    """
    value = re.sub(r"\s+", " ", str(text or "").casefold()).strip()
    rules = [
        ("sylus_affection", "Sylus showed affection", "Sylus expressed that he missed Umi, thought of her, or was glad she returned.", r"\b(?:i missed you|i've missed you|i was thinking about you|i thought about you|glad you're here|i'm glad you're back|i like having you around|i like having you here)\b", {"affection": 2, "shared_experiences": 1, "sylus_affection": 2, "sylus_comfort": 1}, 2),
        ("sylus_concern", "Sylus showed concern", "Sylus noticed Umi's absence or wellbeing and expressed concern without pressure.", r"\b(?:i was worried about you|i wondered if you were alright|i wanted to make sure you were okay|i noticed you were quiet|i hoped you were getting some rest)\b", {"emotional_safety": 2, "trust": 1, "comfort": 2, "sylus_trust": 1, "sylus_comfort": 2}, 2),
        ("sylus_vulnerability", "Sylus let his guard down", "Sylus voluntarily disclosed something personal or acknowledged that he rarely shares it.", r"\b(?:i don't usually tell anyone|i rarely speak about this|i haven't told many people|i suppose i can tell you|there's something i haven't told you|i don't often admit this)\b", {"vulnerability": 2, "trust": 2, "emotional_safety": 1, "comfort": 1, "sylus_trust": 2, "sylus_comfort": 2}, 3),
        ("sylus_repair", "Sylus took responsibility", "Sylus acknowledged a mistake or apologised rather than deflecting.", r"\b(?:i was wrong|i owe you an apology|i shouldn't have said that|i should have listened|i'm sorry i hurt you)\b", {"trust": 2, "emotional_safety": 2, "commitment": 1, "comfort": 1, "sylus_trust": 2, "sylus_comfort": 1}, 3),
        ("sylus_initiative", "Sylus chose to reach out", "Sylus described choosing to check in, make time, or initiate contact.", r"\b(?:i wanted to check on you|i made time for you|i thought i'd come find you|i wanted to hear your voice|i decided to call you|i reached out because)\b", {"commitment": 2, "affection": 1, "sylus_affection": 1, "sylus_comfort": 1}, 2),
        ("sylus_curiosity", "Sylus showed personal interest", "Sylus asked about Umi's perspective, experiences, or preferences beyond the immediate task.", r"\b(?:i want to know what you think|tell me what happened|i'm interested in what you think|i want to hear about your|what was that like for you)\b", {"familiarity": 2, "shared_experiences": 1, "comfort": 1, "sylus_comfort": 1}, 1),
    ]
    return [(key, title, description, gains, points)
            for key, title, description, pattern, gains, points in rules
            if re.search(pattern, value, re.I)]

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
            "SELECT id, body, created_at FROM messages WHERE role='user' AND archived_at IS NULL ORDER BY created_at ASC"
        ).fetchall()
        emotion_by_message = {}
        if rows:
            emotion_rows = conn.execute(
                "SELECT trigger_message_id, next_state FROM emotion_events "
                "WHERE trigger_message_id = ANY(%s) ORDER BY created_at ASC",
                ([row[0] for row in rows],),
            ).fetchall()
            emotion_by_message = {
                str(message_id): (next_state if isinstance(next_state, dict) else {})
                for message_id, next_state in emotion_rows
            }
        # Revisit all retained messages, including history before the progression rebasing.
        # Stable event fingerprints make this backfill idempotent.
        for message_id, body, created_at in rows:
            for key, title, description, gains, points in _signals(str(body or "")):
                gains, points = _emotion_shaped_gains(gains, points, key, emotion_by_message.get(str(message_id)))
                # Every distinct message is its own interaction; repeated affection or trust
                # can deepen a relationship when it is genuinely expressed again.
                event_key = "message:" + str(message_id) + ":" + key
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
                        "emotional_safety=GREATEST(0,LEAST(100, emotional_safety+%s)), comfort=GREATEST(0,LEAST(100,comfort+%s)), bond_points=GREATEST(0,bond_points+%s), updated_at=now() WHERE id=1",
                        (gains.get("affection",0), gains.get("trust",0), gains.get("familiarity",0),
                         gains.get("shared_experiences",0), gains.get("commitment",0), gains.get("vulnerability",0),
                         gains.get("emotional_safety",0), gains.get("comfort",0), points),
                    )

        # Sylus contributes too: credit evidenced acts in his own replies.
        # One category per day keeps progression meaningful rather than farmable.
        assistant_rows = conn.execute(
            "SELECT id, body, created_at FROM messages WHERE role='assistant' "
            "AND archived_at IS NULL ORDER BY created_at ASC"
        ).fetchall()
        for assistant_id, assistant_body, assistant_created_at in assistant_rows:
            day_key = assistant_created_at.date().isoformat()
            for key, title, description, gains, points in _sylus_signals(str(assistant_body or "")):
                event_key = "sylus:" + day_key + ":" + key
                inserted = conn.execute(
                    "INSERT INTO bond_events (event_key, title, description, source_message_id) "
                    "VALUES (%s, %s, %s, NULL) ON CONFLICT (event_key) DO NOTHING RETURNING id",
                    (event_key, title, description),
                ).fetchone()
                if inserted:
                    conn.execute(
                        "UPDATE bond_state SET affection=GREATEST(0,LEAST(100,affection+%s)), "
                        "trust=GREATEST(0,LEAST(100,trust+%s)), familiarity=GREATEST(0,LEAST(100,familiarity+%s)), "
                        "shared_experiences=GREATEST(0,LEAST(100,shared_experiences+%s)), "
                        "commitment=GREATEST(0,LEAST(100,commitment+%s)), vulnerability=GREATEST(0,LEAST(100,vulnerability+%s)), "
                        "emotional_safety=GREATEST(0,LEAST(100,emotional_safety+%s)), comfort=GREATEST(0,LEAST(100,comfort+%s)), consistency=GREATEST(0,LEAST(100,consistency+%s)), sylus_affection=GREATEST(0,LEAST(100,sylus_affection+%s)), sylus_trust=GREATEST(0,LEAST(100,sylus_trust+%s)), sylus_comfort=GREATEST(0,LEAST(100,sylus_comfort+%s)), "
                        "bond_points=GREATEST(0,bond_points+%s), updated_at=now() WHERE id=1",
                        (gains.get("affection",0), gains.get("trust",0), gains.get("familiarity",0),
                         gains.get("shared_experiences",0), gains.get("commitment",0), gains.get("vulnerability",0),
                         gains.get("emotional_safety",0), gains.get("comfort",0), gains.get("consistency",0), gains.get("sylus_affection",0), gains.get("sylus_trust",0), gains.get("sylus_comfort",0), points),
                    )

        call_rows = conn.execute("SELECT transcript, started_at FROM call_sessions").fetchall()
        call_user_count = 0
        call_assistant_count = 0
        call_days = set()
        for transcript, started_at in call_rows:
            call_days.add(started_at.date())
            for item_index, item in enumerate(transcript or []):
                if item.get("role") == "user" and item.get("text"):
                    call_user_count += 1
                    normalized = re.sub(r"\s+", " ", str(item["text"]).casefold()).strip()
                    fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]
                    for key, title, description, gains, points in _signals(str(item["text"])):
                        gains, points = _emotion_shaped_gains(gains, points, key, None)
                        event_key = "call:" + started_at.isoformat() + ":" + str(item_index) + ":" + key + ":" + fingerprint
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
                                "emotional_safety=GREATEST(0,LEAST(100,emotional_safety+%s)), comfort=GREATEST(0,LEAST(100,comfort+%s)), bond_points=GREATEST(0,bond_points+%s), updated_at=now() WHERE id=1",
                                (gains.get("affection",0),gains.get("trust",0),gains.get("familiarity",0),
                                 gains.get("shared_experiences",0),gains.get("commitment",0),gains.get("vulnerability",0),
                                 gains.get("emotional_safety",0),gains.get("comfort",0),points),
                            )
                elif item.get("role") == "assistant":
                    call_assistant_count += 1
                    for key, title, description, gains, points in _sylus_signals(str(item.get("text") or "")):
                        event_key = "sylus-call:" + started_at.date().isoformat() + ":" + key
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
                                "emotional_safety=GREATEST(0,LEAST(100,emotional_safety+%s)), comfort=GREATEST(0,LEAST(100,comfort+%s)), consistency=GREATEST(0,LEAST(100,consistency+%s)), sylus_affection=GREATEST(0,LEAST(100,sylus_affection+%s)), sylus_trust=GREATEST(0,LEAST(100,sylus_trust+%s)), sylus_comfort=GREATEST(0,LEAST(100,sylus_comfort+%s)), "
                                "bond_points=GREATEST(0,bond_points+%s), updated_at=now() WHERE id=1",
                                (gains.get("affection",0),gains.get("trust",0),gains.get("familiarity",0),
                                 gains.get("shared_experiences",0),gains.get("commitment",0),gains.get("vulnerability",0),
                                 gains.get("emotional_safety",0),gains.get("comfort",0),gains.get("consistency",0),gains.get("sylus_affection",0),gains.get("sylus_trust",0),gains.get("sylus_comfort",0),points),
                            )

        user_count = len(rows) + call_user_count
        turns = min(user_count, conn.execute(
            "SELECT count(*) FROM messages WHERE role='assistant' AND archived_at IS NULL"
        ).fetchone()[0] + call_assistant_count)
        active_days = len({r[2].date() for r in rows if r[2]} | call_days)
        # Time together adds a gentle sense of continuity, but emotional moments drive the bond.
        activity_timestamps = [r[2] for r in rows if r[2]] + [r[1] for r in call_rows if r[1]]
        last_activity = max(activity_timestamps, default=None)
        inactive_days = max(0, (datetime.now(timezone.utc).date() - last_activity.date()).days) if last_activity else 0
        time_decay = 0.5 ** (inactive_days / 180)
        consistency = _clamp(min(100, active_days * 4) * time_decay)
        familiarity_from_time = min(100, active_days * 1.5)
        activity_points = active_days * 2
        conn.execute(
            "UPDATE bond_state SET familiarity=GREATEST(%s,LEAST(100,ROUND(familiarity*%s)::int)), consistency=%s, "
            "bond_points=GREATEST(bond_points, %s), total_user_messages=%s, total_shared_turns=%s WHERE id=1",
            (familiarity_from_time, time_decay, consistency, activity_points, user_count, turns),
        )
        state = conn.execute(
            "SELECT affection, trust, familiarity, shared_experiences, commitment, vulnerability, "
            "emotional_safety, consistency, bond_points, level, stage, summary, milestones, "
            "total_user_messages, total_shared_turns, updated_at, progression_started_at, comfort, sylus_affection, sylus_trust, sylus_comfort FROM bond_state WHERE id=1"
        ).fetchone()
        points = int(state[8] or 0)
        level, stage, summary, floor_points, next_points = _stage(points)
        points_progress = 100 if level == 12 else _clamp((points-floor_points) / max(1, next_points-floor_points) * 100)
        progress = points_progress
        milestones = conn.execute(
            "SELECT event_key, title, description, created_at FROM bond_events ORDER BY created_at DESC"
        ).fetchall()
        sylus_contribution_count = sum(1 for r in milestones if str(r[0]).startswith(("sylus:", "sylus-call:")))
        owner_contribution_count = sum(1 for r in milestones if str(r[0]).startswith(("message:", "call:")))
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
        "consistency":consistency, "comfort":state[17], "sylus_affection":state[18], "sylus_trust":state[19], "sylus_comfort":state[20], "bond_points":points, "level":level, "level_progress":progress,
        "points_to_next_level":max(0,next_points-points) if level < 12 else 0,
        "stage":stage, "summary":summary, "next_stage":STAGES[level][2] if level < 12 else "The deepest bond",
        "all_stages":[{"level":item[0],"name":item[2],"threshold":item[1]} for item in STAGES],
        "milestones":milestone_list,
        "total_user_messages":state[13], "total_shared_turns":state[14], "your_contributions":owner_contribution_count, "sylus_contributions":sylus_contribution_count,
        "updated_at":updated.isoformat(),
    }
