import unittest

from app.emotion import EmotionState


class EmotionStateTests(unittest.TestCase):
    def test_playful_banter_increases_amusement(self):
        state = EmotionState()
        before = state.amusement
        state.apply("playful_banter", 1.0)
        self.assertGreater(state.amusement, before)
        self.assertEqual(state.dominant_mood(), "amused")

    def test_anger_is_controlled_and_bounded(self):
        state = EmotionState()
        for _ in range(10):
            state.apply("unfair_harm", 1.0)
        self.assertLessEqual(state.anger, 1.0)
        self.assertIn("Controlled anger", state.style_directive())

    def test_decay_returns_toward_baseline(self):
        state = EmotionState().apply("user_distressed", 1.0)
        before = state.concern
        state.decay(.5)
        self.assertLess(state.concern, before)
        self.assertGreater(state.concern, .10)

    def test_unknown_event_is_safe(self):
        state = EmotionState()
        original = state.to_dict()
        state.apply("unrecognized_event", 1.0)
        self.assertEqual(state.to_dict(), original)

    def test_success_can_raise_happiness_and_pride(self):
        state = EmotionState().apply("shared_success", 1.0)
        self.assertGreater(state.happiness, 0.18)
        self.assertGreater(state.pride, 0.10)
        self.assertEqual(state.dominant_mood(), "content")

    def test_disappointment_is_tracked_and_decays(self):
        state = EmotionState().apply("disappointment", 1.0)
        self.assertGreater(state.disappointment, 0)
        self.assertEqual(state.dominant_mood(), "disappointed")
        before = state.disappointment
        state.decay()
        self.assertLess(state.disappointment, before)


if __name__ == "__main__":
    unittest.main()
