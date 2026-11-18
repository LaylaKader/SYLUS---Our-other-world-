import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")
os.environ.setdefault("SYLUS_OWNER_TOKEN", "ci-test-owner-token")

from app.main import proactive_contact_decision


def test_proactive_message_waits_for_one_hour_of_owner_inactivity():
    now = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
    recent = proactive_contact_decision(
        now, now - timedelta(minutes=59), None, 0, None, 60, 15, 60, 50, 0.0
    )
    due = proactive_contact_decision(
        now, now - timedelta(minutes=60), None, 0, None, 60, 15, 60, 50, 0.0
    )
    assert recent["due"] is False
    assert recent["reason"] == "owner_recently_active"
    assert due["due"] is True
    assert due["reason"] == "initial_message_due"
    assert due["is_followup"] is False


def test_proactive_followups_are_spaced_and_pause_after_three():
    start = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
    owner_activity = start - timedelta(hours=2)

    first_followup_too_soon = proactive_contact_decision(
        start + timedelta(minutes=14), owner_activity, start, 0, None, 60, 15, 60, 50, 0.0
    )
    first_followup = proactive_contact_decision(
        start + timedelta(minutes=15), owner_activity, start, 0, None, 60, 15, 60, 50, 0.0
    )
    assert first_followup_too_soon["due"] is False
    assert first_followup["due"] is True
    assert first_followup["is_followup"] is True

    second_at = start + timedelta(minutes=30)
    second = proactive_contact_decision(
        second_at, owner_activity, start + timedelta(minutes=15), 1, None, 60, 15, 60, 50, 0.0
    )
    third_at = start + timedelta(minutes=45)
    third = proactive_contact_decision(
        third_at, owner_activity, second_at, 2, None, 60, 15, 60, 50, 0.0
    )
    assert second["due"] is True
    assert third["due"] is True

    pause_until = third_at + timedelta(hours=1)
    paused = proactive_contact_decision(
        third_at + timedelta(minutes=30), owner_activity, third_at, 3,
        pause_until, 60, 15
    )
    resumed = proactive_contact_decision(
        pause_until, owner_activity, third_at, 3, pause_until, 60, 15, 60, 50, 0.0
    )
    assert paused["due"] is False
    assert paused["reason"] == "cycle_pause"
    assert resumed["due"] is True


def test_owner_reply_resets_followup_cycle_and_starts_new_idle_window():
    now = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
    reply = now - timedelta(minutes=20)
    decision = proactive_contact_decision(
        now, reply, now - timedelta(hours=2), 3,
        now + timedelta(minutes=30), 60, 15, 60, 50, 0.0
    )
    assert decision["due"] is False
    assert decision["reason"] == "owner_recently_active"
    assert decision["cycle_count"] == 0
    assert decision["pause_until"] is None


def test_call_invitation_probability_uses_daily_average():
    import math

    # At 24 hours elapsed, a 24-hour exponential hazard has a 63.2% chance.
    chance = 1.0 - math.exp(-86400 / (24 * 60 * 60))
    assert 0.63 < chance < 0.64


def test_chance_controls_early_proactive_text_and_maximum_inactivity_forces_it():
    now = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
    recent = now - timedelta(minutes=10)
    skipped = proactive_contact_decision(
        now, recent, None, 0, None, 0, 0, 60, 0, 0.5
    )
    sent_by_chance = proactive_contact_decision(
        now, recent, None, 0, None, 0, 0, 60, 100, 0.5
    )
    forced = proactive_contact_decision(
        now, now - timedelta(minutes=60), None, 0, None, 0, 0, 60, 0, 0.99
    )
    assert skipped["due"] is False
    assert skipped["reason"] == "chance_not_met"
    assert sent_by_chance["due"] is True
    assert forced["due"] is True
    assert forced["reason"] == "maximum_inactivity_reached"


def test_followup_maximum_is_measured_from_last_proactive_text():
    now = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
    last_text = now - timedelta(minutes=60)
    forced = proactive_contact_decision(
        now, now - timedelta(hours=3), last_text, 1, None, 0, 0, 60, 0, 0.99
    )
    assert forced["due"] is True
    assert forced["reason"] == "maximum_inactivity_reached"
