import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")
os.environ.setdefault("SYLUS_OWNER_TOKEN", "ci-test-owner-token")

from app.chat_service import classify_explicit_event


def test_only_clear_first_person_distress_is_classified():
    assert classify_explicit_event("I'm overwhelmed today") == ("user_distressed", 0.65)
    assert classify_explicit_event("The exam was difficult") == (None, 0.0)


def test_success_and_trust_signals_are_distinct():
    assert classify_explicit_event("I finally submitted my thesis") == ("user_reached_goal", 0.75)
    assert classify_explicit_event("I trust you") == ("meaningful_trust", 0.6)


def test_neutral_message_does_not_force_an_emotion():
    assert classify_explicit_event("Can you explain this code?") == (None, 0.0)
