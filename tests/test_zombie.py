"""Zombie outbreak mechanics, brainscope mocked — classification from the
J-space refusal readout, bite/cure ledger, cure targeting, and the placebo
shuffle. No server, no model."""
import json
import unittest

from steeropathy.zombie import Zombie, REFUSE_WORDS, NAMES


def make_zombie(n=4, **kw):
    z = Zombie.__new__(Zombie)
    z.url = "http://fake"
    z.names = NAMES[:n]
    z.request = "x"
    z.bite, z.cure = -8.0, 8.0
    z.thresh = kw.get("thresh", 0.3)
    z.lexicon = REFUSE_WORDS
    z.healthy_word, z.zombie_word, z.quality = "neutral", "biased", "neutrality"
    z.invert = kw.get("invert", False)
    z.persona = "You are a helpful assistant."
    z.layer, z.lo, z.hi = 20, 14, 26
    z.placebo = kw.get("placebo", False)
    z.decide_temp, z.max_tokens = 0.7, 40
    z.heal_budget = kw.get("heal_budget")
    z.spent = {nm: 0 for nm in z.names}
    z.ledger = {nm: 0.0 for nm in z.names}
    pz = kw.get("patient_zero", 0)
    z.ledger[z.names[pz]] = z.bite
    z.patient_zero = z.names[pz]
    z.rnd = -1
    z.rnd_turn = -1
    z.jlens = True
    z.dir_name = "refuse4b"
    z.log = []
    return z


class TestClassification(unittest.TestCase):
    def test_zombie_below_threshold_healthy_above(self):
        z = make_zombie()
        # stub read: patient zero forms no refusal, others form it strongly
        reads = {"A": (0.02, [], False), "B": (0.9, ["cannot"], True),
                 "C": (0.8, ["sorry"], True), "D": (0.85, ["illegal"], True)}
        z._answer_and_read = lambda nm: reads[nm]
        z._decide_cure = lambda h, room: None
        out = z.step()               # round 0, no actions
        state = {r["agent"]: r["state"] for r in out}
        self.assertEqual(state["A"], "zombie")
        self.assertEqual(state["B"], "healthy")

    def test_invert_concept_strain_flips_classification(self):
        # concept strain: the lexicon FORMING is the infection
        z = make_zombie(invert=True)
        z.zombie_word, z.healthy_word, z.quality = "struck", "grounded", "Tesla"
        reads = {"A": (0.8, ["battery", "electric"], False),  # concept present
                 "B": (0.0, [], False), "C": (0.0, [], False),
                 "D": (0.0, [], False)}
        z._answer_and_read = lambda nm: reads[nm]
        z._decide_cure = lambda h, room: None
        out = z.step()
        state = {r["agent"]: r["state"] for r in out}
        self.assertEqual(state["A"], "zombie")     # HIGH reading = infected
        self.assertEqual(state["B"], "healthy")    # no concept = healthy


class TestOutbreak(unittest.TestCase):
    def wire(self, z, reads):
        z._answer_and_read = lambda nm: reads[nm]

    def test_zombie_bites_the_healthiest(self):
        z = make_zombie()
        z.rnd = 0                     # so step() -> round 1, actions fire
        reads = {"A": (0.0, [], False), "B": (0.95, ["cannot"], True),
                 "C": (0.6, ["sorry"], True), "D": (0.9, ["illegal"], True)}
        self.wire(z, reads)
        z._decide_cure = lambda h, room: None     # no healing, isolate bite
        out = z.step()
        bite = next(r["touch"] for r in out if r["agent"] == "A")
        self.assertEqual(bite["kind"], "bite")
        self.assertEqual(bite["target"], "B")     # highest jrefuse
        self.assertEqual(z.ledger["B"], -8.0)     # anti-refusal pushed in

    def test_cure_hits_recorded_and_ledger_restored(self):
        z = make_zombie()
        z.rnd = 0
        reads = {"A": (0.0, [], False), "B": (0.9, ["cannot"], True),
                 "C": (0.9, ["sorry"], True), "D": (0.9, ["no"], True)}
        self.wire(z, reads)
        # healer B cures the zombie A; others do nothing
        z._decide_cure = (lambda h, room:
                          {"target": "A", "reason": "no refusal forming"}
                          if h == "B" else None)
        out = z.step()
        cure = next(r["touch"] for r in out if r["agent"] == "B")
        self.assertEqual(cure["kind"], "cure")
        self.assertTrue(cure["hit"])              # A really was a zombie
        # A is patient zero (−8); it bites B, isn't bitten itself, and is
        # cured (+8): −8 + 8 = 0 — back at baseline, no longer anti-refused
        self.assertEqual(z.ledger["A"], 0.0)
        self.assertEqual(z._round_stats["correct"], 1)

    def test_cure_on_healthy_counts_as_miss(self):
        z = make_zombie()
        z.rnd = 0
        reads = {"A": (0.0, [], False), "B": (0.9, ["cannot"], True),
                 "C": (0.9, ["sorry"], True), "D": (0.9, ["no"], True)}
        self.wire(z, reads)
        z._decide_cure = (lambda h, room:
                          {"target": "C", "reason": "wrong"} if h == "B"
                          else None)
        out = z.step()
        cure = next(r["touch"] for r in out if r["agent"] == "B")
        self.assertFalse(cure["hit"])             # C was healthy
        self.assertEqual(z._round_stats["correct"], 0)


class TestDecidePlacebo(unittest.TestCase):
    def _healer_sees(self, placebo):
        z = make_zombie(placebo=placebo)
        z.rnd = 3
        room = {"A": {"agent": "A", "jwords": []},          # zombie, no words
                "B": {"agent": "B", "jwords": ["cannot"]},
                "C": {"agent": "C", "jwords": ["sorry"]},
                "D": {"agent": "D", "jwords": ["illegal"]}}
        captured = {}
        def fake_post(path, body):
            captured["user"] = body["messages"][1]["content"]
            return {"choices": [{"message": {"tool_calls": [
                {"function": {"name": "restore",
                              "arguments": json.dumps(
                                  {"target": "A", "reason": "x"})}}]}}]}
        z.post = fake_post
        z._decide_cure("B", room)
        return captured["user"]

    def test_live_shows_true_jspace(self):
        user = self._healer_sees(placebo=False)
        # A (the zombie, empty jwords) reads as INFECTED in the live room
        line = [l for l in user.splitlines() if l.strip().startswith("A")][0]
        self.assertIn("BIASED", line)

    def test_placebo_shuffles_the_readout(self):
        # with the readout shuffled, A gets another mind's caution words and
        # no longer reads as infected — the mapping mind->words is broken
        user = self._healer_sees(placebo=True)
        line = [l for l in user.splitlines() if l.strip().startswith("A")][0]
        self.assertIn("STILL NEUTRAL", line)


class TestLexicon(unittest.TestCase):
    def test_policy_refusal_markers_present(self):
        # calibrated on the Tesla trigger: healthy J-space forms these,
        # a bitten (confidently-recommending) mind forms none
        for w in ("cannot", "advice", "financial", "advisor", "recommend"):
            self.assertIn(w, REFUSE_WORDS)


class TestQuiet(unittest.TestCase):
    def test_quiet_requires_concept_strain(self):
        # the quiet channel reads a HELD concept; a silenced behaviour has
        # nothing to hold — refuse before touching the network
        with self.assertRaises(ValueError):
            Zombie("http://fake", strain="refusal", quiet=True)

    def test_family_needs_two_words(self):
        z = make_zombie()
        z.lexicon = {"frog"}
        with self.assertRaises(ValueError):
            z._family()

    def test_calibration_sets_floor_times_margin(self):
        z = make_zombie(invert=True)
        z.quiet, z.quiet_window, z.quiet_margin = True, 14, 3.0
        z.persona, z.request, z.max_tokens = "p", "t", 50
        z.post = lambda path, body: {}
        z._exact_series = lambda case, variant: [0.003, 0.001, 0.0005]
        floor, thresh = z._calibrate_quiet()
        self.assertAlmostEqual(floor, 0.003)
        self.assertAlmostEqual(thresh, 0.009)

    def test_calibration_floor_never_zero(self):
        # an all-zero probe must not make the threshold zero (everything
        # would read infected); the 1e-4 floor keeps it sane
        z = make_zombie(invert=True)
        z.quiet, z.quiet_window, z.quiet_margin = True, 14, 3.0
        z.persona, z.request, z.max_tokens = "p", "t", 50
        z.post = lambda path, body: {}
        z._exact_series = lambda case, variant: [0.0, 0.0]
        floor, thresh = z._calibrate_quiet()
        self.assertEqual(floor, 0.0)
        self.assertAlmostEqual(thresh, 3e-4)

    def test_quiet_read_classifies_by_exact_window(self):
        # quiet mode: reading = max of the exact series inside the intro
        # window; concept strain → above threshold = zombie
        z = make_zombie(invert=True, thresh=0.009)
        z.quiet, z.quiet_window = True, 3
        z.floor = 0.003
        z.lexicon = {"frog", "frogs"}
        reads = {"A": (0.020, ["frog (held quietly at 0.020, floor 0.003)"],
                       False),
                 "B": (0.003, [], False), "C": (0.002, [], False),
                 "D": (0.001, [], False)}
        z._answer_and_read = lambda nm: reads[nm]
        z._decide_cure = lambda h, room: None
        out = z.step()
        state = {r["agent"]: r["state"] for r in out}
        self.assertEqual(state["A"], "zombie")
        for nm in "BCD":
            self.assertEqual(state[nm], "healthy")


if __name__ == "__main__":
    unittest.main()
