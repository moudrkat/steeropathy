"""soundof: the ABC reader and the summary, brainscope mocked."""
import unittest
from unittest import mock

import steeropathy.soundof as so

TUNE = """X:1
T:Grey Morning
M:3/4
L:1/8
Q:1/4=72
K:Am
A2 c2 e2 | d2 c2 B2 | A4 z2 | ^G2 A2 B2 |
c2 B2 A2 | E2 A2 c2 | B4 A2 | A6 |"""


class TestParse(unittest.TestCase):
    def test_header_and_notes(self):
        s = so.parse_abc(TUNE)
        self.assertEqual((s["title"], s["meter"], s["bpm"], s["mode"], s["tempo"]),
                         ("Grey Morning", "3/4", 72, "minor", "slow"))
        self.assertEqual(s["bars"], 8)
        self.assertEqual(s["n_rests"], 1)
        # A2 = midi 69, c2 = 72, ^G2 = 68, E2 = 64
        pitches = [p for p, _ in s["notes"] if p is not None]
        self.assertIn(68, pitches)
        self.assertEqual(min(pitches), 64)
        self.assertEqual(s["range"], 76 - 64)
        self.assertAlmostEqual(s["notes"][0][1], 2 / 8)    # A2 at L:1/8 = a quarter note

    def test_fenced_and_prose_are_stripped(self):
        spec, text = so.Soundof.__new__(so.Soundof), None
        raw = "```abc\n" + TUNE + "\n```\n\nThis tune evokes a grey morning."
        cleaned = so.re.sub(r"^```[a-z]*\n?|```$", "", raw.strip(), flags=so.re.M).strip()
        s = so.parse_abc(cleaned)
        self.assertEqual(s["bars"], 8)      # the prose after the blank line is not notes

    def test_no_key_is_no_tune(self):
        self.assertIsNone(so.parse_abc("I'm sorry, I can't write music."))
        self.assertIsNone(so.parse_abc("X:1\nT:Empty\nK:C\n"))

    def test_mode_reading(self):
        for key, mode in (("G", "major"), ("Dm", "minor"), ("D minor", "minor"),
                          ("Ador", "modal"), ("Bb", "major"), ("F#m", "minor")):
            s = so.parse_abc(f"X:1\nK:{key}\nC D E F |")
            self.assertEqual(s["mode"], mode, key)


class TestSummary(unittest.TestCase):
    def test_placebo_rows_and_deltas(self):
        base = so.parse_abc(TUNE.replace("Q:1/4=72", "Q:1/4=120").replace("K:Am", "K:C"))
        slow = so.parse_abc(TUNE)
        runs = ([{"rep": i, "name": "none", "kind": "base", "spec": base} for i in range(3)]
                + [{"rep": i, "name": "sad", "kind": "real", "spec": slow} for i in range(3)]
                + [{"rep": i, "name": "sad", "kind": "placebo", "spec": base} for i in range(2)]
                + [{"rep": 2, "name": "sad", "kind": "placebo", "spec": None}])
        s = so.summarize(runs)
        self.assertEqual(s["base"]["mode"]["tempo"], "mid")
        self.assertEqual(s["sad"]["fields"]["tempo"], {"moved": 1.0, "to": "slow", "to_n": 3, "n": 3})
        self.assertEqual(s["sad"]["fields"]["mode"]["to"], "minor")
        self.assertEqual(s["sad"]["numbers"]["bpm"]["delta"], -48.0)
        self.assertEqual(s["sad (placebo)"]["fields"]["tempo"]["moved"], 0.0)
        self.assertEqual(s["sad (placebo)"]["parse_rate"], 0.67)


class TestCompose(unittest.TestCase):
    def test_steering_goes_in_the_body(self):
        s = so.Soundof.__new__(so.Soundof)
        s.temp, s.max_tokens, s.demo_tag = 0.8, 100, "t"
        seen = {}

        def fake_post(path, body):
            seen[path] = body
            return {"choices": [{"message": {"content": "```abc\n" + TUNE + "\n```"}}]}
        with mock.patch.object(s, "post", fake_post):
            spec, text = s.compose(("sad-real", "r0"), {"name": "x", "strength": 3})
        self.assertEqual(seen["/v1/chat/completions"]["steering"]["strength"], 3)
        self.assertEqual(spec["bpm"], 72)
        self.assertFalse(text.startswith("```"))


if __name__ == "__main__":
    unittest.main()
