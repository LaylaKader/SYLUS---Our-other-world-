import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SYLUS_OWNER_TOKEN", "test-owner-token")

from app.bond import _signals, _sylus_signals


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

    def test_user_comfort_is_tracked_separately(self):
        signals = _signals("I feel comfortable around you. I can be myself with you.")
        comfort = next(item for item in signals if item[0] == "comfort")
        self.assertGreater(comfort[3]["comfort"], 0)

    def test_repetitive_generic_reply_does_not_award_bond(self):
        self.assertEqual(_sylus_signals("Very well. What would you like to do?"), [])

    def test_concern_is_not_possessive(self):
        signals = _sylus_signals("I was worried about you. I hoped you were getting some rest.")
        self.assertIn("sylus_concern", [item[0] for item in signals])


if __name__ == "__main__":
    unittest.main()
