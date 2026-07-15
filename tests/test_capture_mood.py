"""capture_mood is the whole method: mean(mood) − mean(baseline), unit-normalized.
Mock brainscope's /capture so we test the math, not the network."""
import math
import unittest
from unittest.mock import patch

from steeropathy import transmit
from steeropathy.transmit import capture_mood, MOODS


def fake_post(vectors):
    """Return a stand-in _post that looks up a vector by the message text."""
    def _post(host, path, payload, timeout=300):
        assert path == "/capture"
        text = payload["messages"][0]["content"]
        return {"vector": vectors.get(text, [0.0, 0.0, 0.0])}
    return _post


class TestCaptureMood(unittest.TestCase):
    def test_direction_is_mood_minus_baseline_normalized(self):
        # mood lines average to [3,4,0]; every neutral baseline line is [0,0,0]
        vecs = {"A": [3.0, 4.0, 0.0], "B": [3.0, 4.0, 0.0]}
        with patch.object(transmit, "_post", fake_post(vecs)):
            vec, layer = capture_mood("http://x", ["A", "B"], layer=7)
        self.assertEqual(layer, 7)                       # passed layer is respected
        self.assertAlmostEqual(vec[0], 0.6)              # [3,4,0] normalized
        self.assertAlmostEqual(vec[1], 0.8)
        self.assertAlmostEqual(math.sqrt(sum(x * x for x in vec)), 1.0)

    def test_averages_cancel_topic_noise(self):
        # two mood lines pointing different ways average before the subtraction
        vecs = {"A": [2.0, 0.0], "B": [0.0, 2.0]}
        with patch.object(transmit, "_post", fake_post(vecs)):
            vec, _ = capture_mood("http://x", ["A", "B"], layer=1)
        # mean = [1,1], baseline 0 -> unit([1,1])
        self.assertAlmostEqual(vec[0], vec[1])
        self.assertAlmostEqual(math.sqrt(sum(x * x for x in vec)), 1.0)

    def test_baseline_moods_subtracts_the_other_moods(self):
        # with baseline="moods" the mood library is the baseline, not neutral text.
        # If the mood line equals the mood-library mean, the direction collapses to 0
        # (and unit() must keep it finite, not blow up).
        all_mood_texts = [t for spec in MOODS.values() for t in spec["texts"]]
        vecs = {t: [1.0, 0.0, 0.0] for t in all_mood_texts}
        with patch.object(transmit, "_post", fake_post(vecs)):
            vec, _ = capture_mood("http://x", all_mood_texts, layer=1, baseline="moods")
        self.assertEqual(vec, [0.0, 0.0, 0.0])


if __name__ == "__main__":
    unittest.main()
