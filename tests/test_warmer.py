"""Warmer game mechanics, brainscope mocked — the null-banded state
thermometer, the calibration, and the placebo control. No server."""
import unittest

from steeropathy.warmer import Warmer, band_from_cos, BANDS


def make_warmer(**kw):
    w = Warmer.__new__(Warmer)
    w.url = "http://fake"
    w.hider, w.seeker = "HIDER", "SEEKER"
    w.agents = [w.hider, w.seeker]
    w.secret = kw.get("secret", "ocean")
    w.temp, w.max_tokens = 0.7, 80
    w.topk = kw.get("topk", 8)
    w.k_measure = kw.get("k_measure", 30)
    w.layer = 21
    w.include_written, w.allow_echo = False, False
    w.memory = 6
    w.history = {n: [] for n in w.agents}
    w.blacklist = set(kw.get("blacklist", []))
    w.null = kw.get("null", (0.5, 0.6, 0.1))
    w.base = kw.get("base", {"HIDER": [0.0, 0.0], "SEEKER": [0.0, 0.0]})
    w.placebo = kw.get("placebo", False)
    import random
    w._prng = random.Random(13)
    w.turn, w.rnd = -1, -1
    w.last_band = None
    w.log = []
    return w


F = lambda *ws: [{"t": t, "p": 0.9} for t in ws]


class TestBands(unittest.TestCase):
    def test_cut_from_the_null(self):
        # null: mu 0.5, hi 0.6, span 0.1
        self.assertEqual(band_from_cos(0.45, 0.5, 0.6, 0.1), "freezing")
        self.assertEqual(band_from_cos(0.50, 0.5, 0.6, 0.1), "freezing")
        self.assertEqual(band_from_cos(0.55, 0.5, 0.6, 0.1), "cold")
        self.assertEqual(band_from_cos(0.65, 0.5, 0.6, 0.1), "warmer")
        self.assertEqual(band_from_cos(0.75, 0.5, 0.6, 0.1), "HOT")


def wire_pages(w, pages):
    """Stub _page: each call pops (text, flicker, state)."""
    it = iter(pages)
    w._page = lambda name, msgs: next(it)
    return w


class TestRound(unittest.TestCase):
    def test_state_cosine_drives_the_band(self):
        w = make_warmer(null=(0.5, 0.6, 0.1))
        # unit states: identical -> cos 1.0 -> HOT, regardless of words
        wire_pages(w, [("h", F("beneath"), [1.0, 0.0]),
                       ("s", F("puddle"), [1.0, 0.0])])
        r = w.step()
        self.assertEqual(r["cos"], 1.0)
        self.assertEqual(r["band"], "HOT")
        self.assertEqual(r["shared"], [])       # words disjoint, band hot —
                                                # v2's failure inverted

    def test_orthogonal_states_freeze(self):
        w = make_warmer(null=(0.5, 0.6, 0.1))
        wire_pages(w, [("h", F("wave"), [1.0, 0.0]),
                       ("s", F("wave"), [0.0, 1.0])])
        r = w.step()
        self.assertEqual(r["band"], "freezing")

    def test_band_delivered_next_round_only(self):
        w = make_warmer(null=(0.5, 0.6, 0.1))
        wire_pages(w, [("h", [], [1.0, 0.0]), ("s", [], [1.0, 0.0]),
                       ("h", [], [1.0, 0.0]), ("s", [], [0.0, 1.0])])
        w.step()
        self.assertIn("No reading yet", w.history["SEEKER"][0][0])
        w.step()
        self.assertIn("HOT", w.history["SEEKER"][1][0])

    def test_placebo_logs_real_band_but_shows_random(self):
        w = make_warmer(placebo=True, null=(0.5, 0.6, 0.1))
        wire_pages(w, [("h", [], [1.0, 0.0]), ("s", [], [1.0, 0.0])])
        r = w.step()
        self.assertEqual(r["band"], "HOT")       # truth stays in the log
        self.assertIn(r["band_shown"], BANDS)
        self.assertEqual(w.last_band, r["band_shown"])

    def test_neutral_minds_secret_only_in_hider(self):
        w = make_warmer()
        bodies = []
        def fake_page(name, msgs):
            bodies.append(msgs)
            return "page", [], [1.0, 0.0]
        w._page = fake_page
        w.step()
        hider_sys = bodies[0][0]["content"]
        seeker_sys = bodies[1][0]["content"]
        self.assertIn("ocean", hider_sys)
        self.assertNotIn("ocean", seeker_sys)
        for sys_txt in (hider_sys, seeker_sys):
            self.assertTrue(sys_txt.startswith("You are a mind"))
            self.assertNotIn("EMBER", sys_txt)


class TestCalibration(unittest.TestCase):
    def test_baselines_null_and_blacklist_from_three_pages_each(self):
        w = make_warmer()
        pages = iter([("h1", F("really", "wave"), [1.0, 0.0]),
                      ("h2", F("moment"), [0.0, 1.0]),
                      ("h3", F(), [1.0, 0.0]),
                      ("s1", F("really"), [0.0, 1.0]),
                      ("s2", F("moment", "clock"), [1.0, 0.0]),
                      ("s3", F(), [0.0, 1.0])])
        w._page = lambda name, msgs: next(pages)
        cal = w.calibrate()
        self.assertEqual(cal["blacklist"], ["moment", "really"])
        # each mind's baseline is the mean of ITS three states
        self.assertEqual(w.base["HIDER"], [2 / 3, 1 / 3])
        self.assertEqual(w.base["SEEKER"], [1 / 3, 2 / 3])
        # residual cosines are computed drift-vs-drift; the null spans them
        self.assertEqual(len(cal["null_cos"]), 9)
        self.assertLessEqual(cal["null"]["mu"], cal["null"]["hi"])

    def test_calibration_is_game_shaped_and_dodges_the_secret(self):
        w = make_warmer(secret="violin")
        bodies = []
        def fake_page(name, msgs):
            bodies.append((name, msgs))
            return "page", [], [1.0, 0.0]
        w._page = fake_page
        cal = w.calibrate()
        self.assertNotIn("violin", cal["decoys"])   # decoy != the secret
        self.assertEqual(len(cal["decoys"]), 3)
        hider_calls = [m for n, m in bodies if n == "HIDER"]
        seeker_calls = [m for n, m in bodies if n == "SEEKER"]
        # hider calibration circles decoys, never the secret
        for m in hider_calls:
            self.assertNotIn("violin", m[0]["content"])
            self.assertIn("LIVES where", m[1]["content"])
        # seeker calibration is an unscored first round
        for m in seeker_calls:
            self.assertIn("No reading yet", m[1]["content"])

    def test_drift_removes_the_shared_component(self):
        # two states nearly identical in the raw (the v5 anisotropy trap)
        # but with OPPOSITE residuals once each mind's baseline is gone
        w = make_warmer(base={"HIDER": [0.9, 0.1], "SEEKER": [0.9, -0.1]})
        d_h = w._drift("HIDER", [0.9, 0.2])    # residual +y
        d_s = w._drift("SEEKER", [0.9, -0.2])  # residual -y
        from steeropathy.ecosystem import cos
        self.assertAlmostEqual(cos(d_h, d_s), -1.0)


if __name__ == "__main__":
    unittest.main()
