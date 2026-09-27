"""handoff: A's settings parse, the reading of a world per knob, the text
channel's sentence, fidelity against a baseline, and the table. No server."""
import unittest
from unittest import mock

import steeropathy.handoff as ho

W = {"time": "night", "weather": "stars", "sky": ["#000000", "#222222"],
     "elements": [{"kind": "tree"}, {"kind": "tree"}, {"kind": "bird"}, {"kind": "cat"}]}


class TestPieces(unittest.TestCase):
    def test_parse_settings(self):
        s = ho.parse_settings('Sure. {"manytrees": 2, "darker": "1", "vibes": 3, "night": 0, "crowded": -9}')
        self.assertEqual(s, {"manytrees": 2.0, "darker": 1.0, "crowded": -3.0})
        self.assertEqual(ho.parse_settings("no json here"), {})

    def test_read(self):
        self.assertEqual(ho.read(W, "manytrees"), 2.0)
        self.assertEqual(ho.read(W, "crowded"), 4.0)
        self.assertEqual(ho.read(W, "night"), 1.0)
        self.assertGreater(ho.read(W, "darker"), -0.2)       # near-black sky reads as very dark (up)

    def test_text_channel(self):
        self.assertEqual(ho.settings_text({"manytrees": 2, "darker": -1, "night": 1}),
                         "Make it more trees, brighter, at night.")

    def test_fidelity(self):
        base = {"manytrees": 0.5, "manycats": 0.0, "darker": -0.9}
        self.assertEqual(ho.fidelity({"manytrees": 2, "manycats": -1, "darker": 1}, W, base), 2 / 3)
        self.assertIsNone(ho.fidelity({"manytrees": 2}, None, base))

    def test_table_and_baseline(self):
        none_w = {"time": "dawn", "sky": ["#ffffff"], "elements": [{"kind": "tree"}]}
        log = [{"item": 0, "brief": "b", "settings": {"manytrees": 2, "darker": 1},
                "reads": [{"channel": "none", "b": none_w}, {"channel": "vector", "b": W},
                          {"channel": "text", "b": none_w}]}]
        t = ho.table(log)
        self.assertEqual(t["channels"]["vector"]["fidelity"], 1.0)
        self.assertEqual(t["channels"]["text"]["fidelity"], 0.0)
        self.assertEqual(t["knobs"]["manytrees"]["vector"], {"hit": 1, "n": 1})

    def test_step_wiring(self):
        h = ho.Handoff.__new__(ho.Handoff)
        h.url, h.lo, h.hi, h.log, h.dirs = "u", 12, 20, [], {"manytrees": [1.0, 0.0], "darker": [0.0, 1.0]}
        posted = []
        with mock.patch.object(h, "decide", lambda brief: ({"manytrees": 2, "darker": -1}, "{}")), \
             mock.patch.object(h, "post", lambda p, b: posted.append((p, b))), \
             mock.patch.object(h, "draw", lambda tag, steering=None, extra=None: (W, "{}")):
            rec = h.step(0, "a dark forest")
        self.assertEqual([r["channel"] for r in rec["reads"]], ["none", "text", "vector", "placebo"])
        self.assertAlmostEqual(rec["strength"], 5 ** 0.5, places=3)
        self.assertEqual(sum(1 for p, _ in posted if p == "/directions"), 2)


if __name__ == "__main__":
    unittest.main()
