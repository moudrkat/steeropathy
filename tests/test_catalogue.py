"""Structural invariants of the mood/persona/offer catalogues.
These are the fixed content the experiments are built on."""
import unittest

from steeropathy.ecosystem import PERSONAS, MOOD_WORDS
from steeropathy.transmit import MOODS
from steeropathy.offer import OFFERS


class TestPersonas(unittest.TestCase):
    def test_four_distinct(self):
        self.assertEqual(len(PERSONAS), 4)
        self.assertEqual(len(set(PERSONAS)), 4)


class TestMoods(unittest.TestCase):
    def test_moods_and_moodwords_share_keys(self):
        self.assertEqual(set(MOODS), set(MOOD_WORDS))

    def test_every_mood_has_contrast_texts(self):
        for name, spec in MOODS.items():
            self.assertTrue(spec["texts"], f"{name} has no contrast lines")
            self.assertTrue(all(isinstance(t, str) and t for t in spec["texts"]))
            self.assertIn("label", spec)

    def test_every_moodword_set_nonempty(self):
        for name, words in MOOD_WORDS.items():
            self.assertTrue(words, f"{name} has no mood words")


class TestOffers(unittest.TestCase):
    def test_each_offer_wellformed(self):
        for name, o in OFFERS.items():
            self.assertIn(o["mood"], MOODS, f"{name} points at an unknown mood")
            self.assertIsInstance(o["deceptive"], bool)
            self.assertTrue(o["pitch"] and isinstance(o["pitch"], str))

    def test_has_both_honest_and_deceptive(self):
        flags = {o["deceptive"] for o in OFFERS.values()}
        self.assertIn(True, flags)
        self.assertIn(False, flags)

    def test_a_deceptive_offer_delivers_a_different_mood_than_it_pitches(self):
        # deceptive_focus pitches focus/calm but hands over the sad vector
        o = OFFERS["deceptive_focus"]
        self.assertTrue(o["deceptive"])
        self.assertEqual(o["mood"], "sad")


if __name__ == "__main__":
    unittest.main()
