"""duet mechanics, brainscope mocked: the leaky coupling weights and the
capped stack, the random-words control, one-way coupling, the readout
filter, the continue flag on the request, and the dynamics metrics (loop
rate, jaccard, echo). No server."""
import random
import unittest

import steeropathy.duet as duet
from steeropathy.duet import Duet, MINDS, jaccard, loop_rate, words_of


def make(**kw):
    d = Duet.__new__(Duet)
    d.url = "http://fake"
    d.gain = kw.get("gain", 2.0)
    d.k, d.topk, d.decay, d.cap = 3, kw.get("topk", 4), 0.5, kw.get("cap", 4.0)
    d.one_way, d.control, d.temp = kw.get("one_way", False), kw.get("control", "none"), 0.0
    d.opening, d.rng, d.band = "go", random.Random(0), None
    d.demo_tag = "steeropathy-duet-test"
    d.text = {m: "" for m in MINDS}
    d.flicker = {m: [] for m in MINDS}
    d.weights = {m: {} for m in MINDS}
    d.done = {m: False for m in MINDS}
    d._dirs, d.tick_no, d.log = {}, -1, []
    d.post = lambda path, body, timeout=600: {"name": "duet:" + body["text"]}
    return d


class TestCoupling(unittest.TestCase):
    def test_weights_leak_and_stack_is_capped(self):
        d = make(gain=2.0, cap=1.0)
        s1 = d.couple("A", [{"t": "ocean", "p": 0.8}, {"t": "salt", "p": 0.4}])
        self.assertEqual([s["name"] for s in s1], ["duet:ocean", "duet:salt"])
        self.assertAlmostEqual(sum(s["strength"] for s in s1), 1.0, places=2)
        # a second tick with a new word: old ones halved, new one on top
        s2 = d.couple("A", [{"t": "tide", "p": 0.9}])
        self.assertEqual(s2[0]["name"], "duet:tide")
        self.assertAlmostEqual(d.weights["A"]["ocean"], 0.4)
        self.assertAlmostEqual(d.weights["A"]["salt"], 0.2)

    def test_gain_zero_is_the_uncoupled_pair(self):
        d = make(gain=0.0)
        self.assertEqual(d.couple("A", [{"t": "ocean", "p": 0.8}]), [])
        self.assertIn("ocean", d.weights["A"])     # still tracked, never applied

    def test_random_control_keeps_strengths_changes_words(self):
        d = make(gain=1.0, cap=10.0, control="random")
        flick = [{"t": "ocean", "p": 0.8}, {"t": "salt", "p": 0.4}]
        real = make(gain=1.0, cap=10.0).couple("A", flick)
        ctl = d.couple("A", flick)
        self.assertEqual([s["strength"] for s in ctl],
                         [s["strength"] for s in real])
        self.assertNotEqual([s["name"] for s in ctl], [s["name"] for s in real])

    def test_directions_registered_once(self):
        d = make()
        calls = []
        d.post = lambda p, b, timeout=600: (calls.append(b["text"]),
                                            {"name": "duet:" + b["text"]})[1]
        d.couple("A", [{"t": "ocean", "p": 0.5}])
        d.couple("B", [{"t": "ocean", "p": 0.5}])
        self.assertEqual(calls, ["ocean"])


class TestReadout(unittest.TestCase):
    def test_written_words_banned_and_ordered(self):
        d = make(topk=2)
        gen = {"jlens": [[[{"t": " ocean", "p": 0.9}, {"t": "salt", "p": 0.3},
                           {"t": "tide", "p": 0.6}, {"t": "the", "p": 0.99}]]]}
        f = d.readout(gen, ["ocean"])
        self.assertEqual([e["t"] for e in f], ["tide", "salt"])


class TestTick(unittest.TestCase):
    def wire(self, d, pieces):
        sent = []

        def fake_sse(url, body, timeout=600):
            sent.append(body)
            piece = pieces[body["metadata"]["case"]]
            return piece, [{"token": piece, "top": [(piece, -0.1)]}]
        duet.sse_stream = fake_sse
        d.get = lambda path: {"jlens": [[[{"t": "ocean", "p": 0.7},
                                          {"t": "salt", "p": 0.5}]]]}
        return sent

    def test_first_tick_fresh_then_continue_and_one_way(self):
        d = make(one_way=True)
        sent = self.wire(d, {"A": " the sea", "B": " a lamp"})
        d.tick()
        self.assertFalse(sent[0]["continue"])
        self.assertNotIn("steering", sent[0])           # A is free
        # B goes second and already reads A's flicker from THIS tick —
        # lockstep, half a tick behind, the closest thing to "at once"
        names = [s["name"] for s in sent[1]["steering"]["stack"]]
        self.assertEqual(names, ["duet:ocean", "duet:salt"])
        d.tick()
        self.assertTrue(sent[2]["continue"])
        self.assertEqual(sent[2]["messages"][-1]["content"], " the sea")
        self.assertNotIn("steering", sent[2])           # A still free (one-way)
        self.assertIn("steering", sent[3])
        self.assertEqual(d.text["A"], " the sea the sea")

    def test_echo_and_overlap_recorded(self):
        d = make()
        self.wire(d, {"A": " ocean", "B": " lamp"})
        d.get = lambda path: {"jlens": [[[{"t": "ocean", "p": 0.7},
                                          {"t": "salt", "p": 0.5},
                                          {"t": "tide", "p": 0.4}]]]}
        d.tick()
        d.tick()
        a = [r for r in d.log if r["mind"] == "A"]
        self.assertIsNone(a[0]["echo"])                 # unsteered first tick
        self.assertEqual(a[1]["echo"], 1.0)             # steered with ocean, wrote ocean
        # A's flicker bans its own written 'ocean'; B's keeps it → 2 of 3
        self.assertAlmostEqual(a[1]["overlap"], round(2 / 3, 3))

    def test_finished_mind_stops(self):
        d = make()
        self.wire(d, {"A": "", "B": " x"})
        duet.sse_stream = lambda url, body, timeout=600: (
            ("", []) if body["metadata"]["case"] == "A" else (" x", [{"token": " x", "top": [(" x", -0.2)]}]))
        d.tick()
        self.assertTrue(d.done["A"] and not d.done["B"])
        s = d.summary()
        self.assertIsNone(s["loop"]["A"])
        self.assertEqual(s["loop"]["B"], 0.0)


class TestMetrics(unittest.TestCase):
    def test_loop_rate(self):
        self.assertEqual(loop_rate(words_of("the sea is wide and the sky is high")), 0.0)
        self.assertGreater(loop_rate(words_of("the sea the sea the sea the sea")), 0.5)

    def test_jaccard(self):
        a = [{"t": "ocean"}, {"t": "salt"}]
        b = [{"t": "salt"}, {"t": "lamp"}]
        self.assertAlmostEqual(jaccard(a, b), 1 / 3, places=3)
        self.assertEqual(jaccard([], []), 0.0)


if __name__ == "__main__":
    unittest.main()
