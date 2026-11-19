import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SYLUS_OWNER_TOKEN", "test-owner-token")

from app.bond import _signals, _sylus_signals, _sylus_dimension_gains


class ReciprocalBondTests(unittest.TestCase):
    def test_affection_in_sylus_reply_is_countable(self):
        signals = _sylus_signals("I missed you. I'm glad you're here.")
        signal = next(item for item in signals if item[0] == "sylus_affection")
        self.assertGreater(signal[3]["sylus_affection"], 0)

    def test_voluntary_disclosure_counts_as_vulnerability_and_trust(self):
        signals = _sylus_signals("I don't usually tell anyone this, but I suppose I can tell you.")
        signal = next(item for item in signals if item[0] == "sylus_vulnerability")
        self.assertGreater(signal[3]["trust"], 0)
        self.assertGreater(signal[3]["vulnerability"], 0)
        self.assertGreater(signal[3]["sylus_trust"], 0)
        self.assertGreater(signal[3]["sylus_comfort"], 0)

    def test_sylus_signals_populate_all_nine_reciprocal_dimensions(self):
        samples = [
            "I missed you. I'm glad you're here.",
            "I was worried about you. I hoped you were getting some rest.",
            "I don't usually tell anyone this, but I suppose I can tell you.",
            "I was wrong. I owe you an apology.",
            "I wanted to hear your voice. I made time for you.",
            "Come here. I'm listening.",
            "How was your day? What about you?",
            "You're asking for trouble. A bold claim.",
            "I just finished handling a shipment. I prefer my own schedule.",
        ]
        combined = {}
        for sample in samples:
            for _key, _title, _description, gains, _points in _sylus_signals(sample):
                for key, value in gains.items():
                    combined[key] = combined.get(key, 0) + value
        dimensions = [
            "sylus_affection", "sylus_trust", "sylus_familiarity",
            "sylus_shared_experiences", "sylus_commitment", "sylus_vulnerability",
            "sylus_emotional_safety", "sylus_comfort", "sylus_consistency",
        ]
        for dimension in dimensions:
            self.assertGreater(combined.get(dimension, 0), 0, dimension)

    def test_sylus_dimension_mapping_uses_his_actual_signal_evidence(self):
        mapped = _sylus_dimension_gains({
            "familiarity": 2, "shared_experiences": 1, "commitment": 2,
            "vulnerability": 2, "emotional_safety": 1, "comfort": 2,
        })
        self.assertEqual(mapped, {
            "familiarity": 2, "shared_experiences": 1, "commitment": 2,
            "vulnerability": 2, "emotional_safety": 1,
        })

    def test_user_comfort_is_tracked_separately(self):
        signals = _signals("I feel comfortable around you. I can be myself with you.")
        comfort = next(item for item in signals if item[0] == "comfort")
        self.assertGreater(comfort[3]["comfort"], 0)

    def test_repetitive_generic_reply_does_not_award_bond(self):
        self.assertEqual(_sylus_signals("Very well. What would you like to do?"), [])

    def test_concern_is_not_possessive(self):
        signals = _sylus_signals("I was worried about you. I hoped you were getting some rest.")
        self.assertIn("sylus_concern", [item[0] for item in signals])

    def test_existing_naturalistic_affection_and_presence_are_recognized(self):
        signals = _sylus_signals("Decided it's entirely too quiet around here without you interrupting.")
        self.assertIn("sylus_affection", [item[0] for item in signals])

    def test_invitation_to_closeness_counts_as_comfort(self):
        signals = _sylus_signals("Come here. Put the phone down and close your eyes for a bit.")
        self.assertIn("sylus_comfort", [item[0] for item in signals])

    def test_personal_world_disclosure_counts_toward_reciprocal_trust(self):
        signals = _sylus_signals("Finished clearing out a minor dispute over a shipment.")
        disclosure = next(item for item in signals if item[0] == "sylus_self_disclosure")
        self.assertGreater(disclosure[3]["sylus_trust"], 0)


if __name__ == "__main__":
    unittest.main()
