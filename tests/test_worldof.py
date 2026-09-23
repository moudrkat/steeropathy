"""worldof: the contrast directions are built from the served model's own
lines (mood: mean(lines) − neutral; contrast: pole minus opposite pole),
unit-normed; unknown names fail loudly. brainscope mocked."""
import unittest
from unittest import mock

import steeropathy.worldof as wo


class TestDirections(unittest.TestCase):
    def test_contrast_is_pole_minus_opposite_and_unit(self):
        calls = []

        def fake_capture(url, texts, layer=None):
            calls.append(texts)
            return ([1.0, 0.0] if "sorry" in texts[0] else [0.0, 1.0]), 7
        with mock.patch.object(wo, "capture_mood", fake_capture):
            v, lay, src = wo.direction_for("http://fake", "refusal", 7)
        self.assertEqual(src, "contrast")
        self.assertAlmostEqual(v[0], -v[1])
        self.assertAlmostEqual(sum(x * x for x in v), 1.0, places=9)
        self.assertEqual(len(calls), 2)                 # both poles captured

    def test_mood_goes_through_capture_mood(self):
        with mock.patch.object(wo, "capture_mood", lambda url, t, layer=None: ([0.6, 0.8], 5)):
            v, lay, src = wo.direction_for("http://fake", "sad", 5)
        self.assertEqual((src, lay, v), ("mood", 5, [0.6, 0.8]))

    def test_unknown_name_fails_loudly(self):
        with self.assertRaises(KeyError):
            wo.direction_for("http://fake", "vibes", 5)


if __name__ == "__main__":
    unittest.main()
