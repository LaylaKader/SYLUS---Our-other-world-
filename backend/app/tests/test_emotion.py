from app.emotion import EmotionState


def test_emotion_is_bounded_and_decays_toward_baseline():
    state = EmotionState().apply("playful_banter", 1.0)
    assert 0 <= state.amusement <= 1
    assert state.amusement > 0.1
    state.decay()
    assert state.amusement < 0.45


def test_unknown_event_does_not_change_state():
    state = EmotionState()
    before = state.to_dict()
    state.apply("unrecognized_event", 1.0)
    assert state.to_dict() == before
