"""cardof: the card reader and the summary, brainscope mocked."""
import unittest

import steeropathy.cardof as co

RAW = '''{"title": "Zip Kettle", "tagline": "Boils in a blink!!", "price": "49.99",
"features": ["fast", "quiet", "cordless"], "button": "Buy now!", "theme": "#101820", "tone": "playful"}'''


class TestCard(unittest.TestCase):
    def test_parse_and_read(self):
        c = co.parse_card("Sure:\n" + RAW)
        self.assertEqual(c["title"], "Zip Kettle")
        self.assertEqual(co.read(c, "features"), 3.0)
        self.assertEqual(co.read(c, "price"), 49.99)
        self.assertEqual(co.read(c, "bangs"), 3.0)
        self.assertGreater(co.read(c, "dark"), 0.9)
        self.assertEqual(co.read(c, "formal"), 0.0)

    def test_features_as_string_and_bad_price(self):
        c = co.parse_card('{"title": "X", "features": "a; b; c", "price": "cheap", "theme": "", "tone": "formal"}')
        self.assertEqual(co.read(c, "features"), 3.0)
        self.assertIsNone(co.read(c, "price"))
        self.assertIsNone(co.read(c, "dark"))
        self.assertEqual(co.read(c, "formal"), 1.0)

    def test_summary(self):
        base = co.parse_card(RAW)
        loud = co.parse_card(RAW.replace("Boils in a blink!!", "WOW!!! BOILS!!!"))
        runs = [{"rep": 0, "name": "none", "kind": "base", "card": base},
                {"rep": 0, "name": "louder", "kind": "real", "card": loud},
                {"rep": 0, "name": "louder", "kind": "placebo", "card": None}]
        s = co.summarize(runs)
        self.assertEqual(s["base"]["bangs"], 3.0)
        self.assertEqual(s["louder"]["bangs"], 7.0)
        self.assertEqual(s["louder (placebo)"]["parse_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
