"""Opt-in live tests against a running brainscope. Skipped unless STEEROPATHY_BRAINSCOPE
is set to its URL, e.g.:

    STEEROPATHY_BRAINSCOPE=http://localhost:8011 python -m unittest discover -s tests

These build against the real model (no generation, just captures), so they're quick.
"""
import math
import os
import unittest

from steeropathy.transmit import capture_mood
from steeropathy.resonance import Reso

URL = os.environ.get("STEEROPATHY_BRAINSCOPE")


@unittest.skipUnless(URL, "set STEEROPATHY_BRAINSCOPE to a brainscope URL to run")
class TestLive(unittest.TestCase):
    def test_capture_mood_returns_unit_direction(self):
        vec, layer = capture_mood(URL, ["I just lost someone I love.",
                                        "The grief is unbearable."])
        self.assertIsInstance(layer, int)
        self.assertAlmostEqual(math.sqrt(sum(x * x for x in vec)), 1.0, places=5)

    def test_intensity_constructor_sets_maxpts(self):
        # regression for the --intensity crash: _decide references self.maxpts, which
        # the intensity init path used to skip.
        r = Reso(URL, intensity=True)
        self.assertTrue(hasattr(r, "maxpts"))

    def test_bipolar_constructor_is_signed_and_sized(self):
        r = Reso(URL, bipolar=True)
        self.assertTrue(hasattr(r, "maxpts"))
        self.assertIn("give", r.inject)
        self.assertIn("take", r.inject)


if __name__ == "__main__":
    unittest.main()
