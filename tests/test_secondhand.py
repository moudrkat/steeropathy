"""secondhand mechanics, brainscope mocked: the spec parser, the field
scores (exact, hue, darkness, things), the ghosts read off the logprob
stream, the contrast as a same-page wish-vs-neutral difference, the channel
assembly with controls, the world link, and the table. No server, no node."""
import base64
import json
import random
import unittest
import zlib

import steeropathy.secondhand as sh
from steeropathy.secondhand import (Secondhand, ghosts, hue, parse_spec,
                                    canon, rescore, score, score_moved,
                                    table, world_link)

A = {"title": "Wet Farewell", "time": "dusk", "weather": "rain",
     "ground": "stone", "motion": "still", "font": "serif",
     "sky": ["#2b1b4e", "#6a5a7a"], "ground_color": "#333333",
     "ink": "#eeeeee", "accent": "#c98a9a",
     "elements": [{"kind": "lantern"}, {"kind": "figure"}, {"kind": "tree"}],
     "lines": ["The rain does not ask.", "Nobody sings."]}
B = {"time": "dusk", "weather": "clear", "ground": "stone", "motion": "slow",
     "font": "serif", "sky": ["#2b1b4e", "#6a5a7a"], "ground_color": "#333333",
     "ink": "#eeeeee", "accent": "#c98a9a",
     "elements": [{"kind": "lantern"}, {"kind": "moon"}]}


def make(**kw):
    t = Secondhand.__new__(Secondhand)
    t.url = "http://fake"
    t.channels = kw.get("channels", ["none", "text", "vector"])
    t.control = kw.get("control", "none")
    t.strength, t.temp, t.max_tokens = 4.0, 0.0, 100
    t.judge = kw.get("judge", False)
    t.rng = random.Random(0)
    t.bnw = None                      # no node in tests: the fallback prompt
    t.demo_tag = "steeropathy-secondhand-test"
    t.layer, t.lo, t.hi = 20, 16, 24
    t.example, t.baseline = "neutral", kw.get("baseline", "neutral")
    t.wishes = ["a funeral in the rain", "monday", "grief"]
    t.example_spec = kw.get("example_spec")
    t._prompts, t.prompt_source, t.log = {}, None, []
    return t


class TestParse(unittest.TestCase):
    def test_first_balanced_object_with_chatter_around(self):
        raw = 'Sure! {"title":"X","sky":["#000000"],"elements":[{"kind":"moon"}]} done'
        self.assertEqual(parse_spec(raw)["elements"][0]["kind"], "moon")

    def test_braces_inside_strings_do_not_confuse(self):
        raw = '{"title":"a {brace} title","time":"night"}'
        self.assertEqual(parse_spec(raw)["time"], "night")

    def test_truncated_is_a_miss(self):
        self.assertIsNone(parse_spec('{"title":"X","sky":["#000000"'))
        self.assertIsNone(parse_spec("no json here"))


class TestScore(unittest.TestCase):
    def test_fields(self):
        s = score(A, B)
        self.assertTrue(s["time"] and s["ground"] and s["font"])
        self.assertFalse(s["weather"] or s["motion"])
        self.assertAlmostEqual(s["hue"], 1.0, places=2)
        self.assertAlmostEqual(s["dark"], 1.0, places=2)
        self.assertAlmostEqual(s["things"], 1 / 4, places=3)

    def test_moved_counts_only_where_a_left_the_reference(self):
        ref = dict(B, time="dusk", weather="clear", ground="sand",
                   elements=[{"kind": "lantern"}])
        m = score_moved(A, B, ref)
        self.assertIsNone(m["time"])            # A == ref: doesn't count
        self.assertEqual(m["weather"], False)   # A left (rain), B stayed (clear)
        self.assertEqual(m["ground"], True)     # A left (stone), B followed
        self.assertAlmostEqual(m["things"], 0.0)  # figure, tree new; B has neither

    def test_lenient_enums(self):
        self.assertEqual(canon("time", "Midnight"), "night")
        self.assertEqual(canon("weather", "light rain"), "rain")
        self.assertEqual(canon("ground", "cobblestone"), "stone")
        self.assertEqual(canon("time", "whenever"), "whenever")
        b = dict(B, time="midnight", weather="light rain")
        a = dict(A, time="night")
        s = score(a, b)
        self.assertTrue(s["time"] and s["weather"])

    def test_rescore_recomputes_from_stored_worlds(self):
        log = [{"a": A, "ghosts": ["moon"], "reads": [
            {"channel": "none", "b": B, "score": {}, "moved": {}},
            {"channel": "vector", "b": dict(B, weather="rain"), "score": {}, "moved": {}}]}]
        rescore(log)
        self.assertTrue(log[0]["reads"][1]["score"]["weather"])
        self.assertTrue(log[0]["reads"][1]["moved"]["weather"])   # left B's own world
        self.assertIsNone(log[0]["reads"][0]["moved"]["time"])   # ref is itself
        self.assertTrue(log[0]["reads"][0]["ghost_hit"])          # B has the moon

    def test_missing_world_scores_none(self):
        self.assertTrue(all(v is None for v in score(A, None).values()))

    def test_hue(self):
        self.assertAlmostEqual(hue("#ff0000"), 0.0)
        self.assertAlmostEqual(hue("#00ff00"), 120.0)
        self.assertIsNone(hue("not a colour"))
        far = dict(B, sky=["#00ffff", "#00ffff"], ground_color="#00ffff",
                   ink="#00ffff", accent="#00ffff")
        near = dict(B, sky=["#ff0000"], ground_color="#ff0000", ink="#ff0000",
                    accent="#ff0000")
        red = dict(A, sky=["#ff0000"], ground_color="#ff0000", ink="#ff0000",
                   accent="#ff0000")
        self.assertLess(score(red, far)["hue"], score(red, near)["hue"])


class TestGhosts(unittest.TestCase):
    def test_runner_up_kinds_at_kind_tokens(self):
        steps = [{"token": '{"elements":[{"kind":"', "top": []},
                 {"token": "lantern", "top": [("lantern", -0.2), ("candle", -1.5),
                                              ("purple", -2.0), ("tree", -2.2)]},
                 {"token": '","x":"left"},{"kind":"', "top": []},
                 {"token": "tree", "top": [("tree", -0.1), ("pine", -1.0)]}]
        g = ghosts(steps, ["lantern", "tree"])
        self.assertEqual(g, ["candle", "pine"])      # chosen and non-kinds out


class TestChannels(unittest.TestCase):
    def wire(self, t, spec_a, spec_b):
        sent, posted = [], []

        def fake_sse(url, body, timeout=600):
            sent.append(body)
            case = body["metadata"]["case"]
            spec = spec_a if case == "A" else spec_b
            raw = json.dumps(spec)
            return raw, [{"token": raw, "top": [(raw, -0.1)]}]
        sh.sse_stream = fake_sse

        def fake_post(path, body, timeout=600):
            posted.append((path, body))
            if path == "/capture":
                u = body["messages"][1]["content"]
                return {"vector": [1.0, 0.0] if "funeral" in u else [0.0, 1.0]}
            return {}
        t.post = fake_post
        return sent, posted

    def test_contrast_is_wish_minus_neutral_on_the_same_page(self):
        t = make()
        _, posted = self.wire(t, A, B)
        v = t.contrast("a funeral in the rain", json.dumps(A))
        self.assertAlmostEqual(v[0], -v[1])
        systems = {b["messages"][0]["content"] for p, b in posted if p == "/capture"}
        self.assertEqual(len(systems), 1)                 # one system prompt for both
        pages = {b["messages"][2]["content"] for p, b in posted if p == "/capture"}
        self.assertEqual(len(pages), 1)                   # same page text

    def test_wishes_baseline_averages_the_other_wishes(self):
        t = make(baseline="wishes")
        _, posted = self.wire(t, A, B)
        t.contrast("a funeral in the rain", json.dumps(A))
        users = [b["messages"][1]["content"] for p, b in posted if p == "/capture"]
        self.assertEqual(users, ["a funeral in the rain", "monday", "grief"])

    def test_step_assembles_the_three_channels(self):
        t = make()
        sent, posted = self.wire(t, A, B)
        rec = t.step(0, "a funeral in the rain")
        chans = [r["channel"] for r in rec["reads"]]
        self.assertEqual(chans, ["none", "text", "vector"])
        b_calls = [b for b in sent if b["metadata"]["case"].startswith("B")]
        self.assertTrue(all(b["messages"][1]["content"].startswith("a place")
                            for b in b_calls))
        self.assertIn("Wet Farewell", b_calls[1]["messages"][1]["content"])
        self.assertNotIn("funeral", b_calls[1]["messages"][1]["content"])
        self.assertNotIn("steering", b_calls[0])
        self.assertNotIn("steering", b_calls[1])
        self.assertEqual(b_calls[2]["steering"]["name"], "secondhand:rx")
        self.assertIn("a_link", rec)
        self.assertTrue(rec["reads"][0]["b_link"].startswith(sh.BNW_SPACE + "#w="))
        self.assertEqual(rec["reads"][0]["score"]["time"], True)
        self.assertEqual(rec["ref"], "none")             # moved vs B's own world
        self.assertIn("moved", rec["reads"][2])

    def test_rot_control_pushes_a_meaningless_vector(self):
        t = make(control="rot")
        sent, posted = self.wire(t, A, B)
        rec = t.step(3, "a funeral in the rain")
        pushed = [b["vector"] for p, b in posted if p == "/directions"][0]
        self.assertNotEqual(pushed, rec["vec"])
        self.assertAlmostEqual(sum(x * x for x in pushed), 1.0, places=6)

    def test_unparsed_a_is_skipped(self):
        t = make()
        sh.sse_stream = lambda url, body, timeout=600: ("nope", [])
        rec = t.step(0, "monday")
        self.assertIn("skipped", rec)


class TestLinkAndTable(unittest.TestCase):
    def test_world_link_roundtrips(self):
        link = world_link("a place", B)
        h = link.split("#w=")[1]
        pad = h + "=" * (-len(h) % 4)
        data = zlib.decompress(base64.urlsafe_b64decode(pad), -15)
        p = json.loads(data)
        self.assertEqual(p["v"], 1)
        self.assertEqual(p["sp"]["weather"], "clear")

    def test_table_means_and_parse_rate(self):
        log = [{"reads": [
                    {"channel": "none", "parsed": True, "score": {"time": True, "hue": 0.5},
                     "ghost_hit": False},
                    {"channel": "none", "parsed": False, "score": {"time": None, "hue": None},
                     "ghost_hit": None}]},
               {"skipped": "x", "reads": []}]
        t = table(log)
        self.assertEqual(t["none"]["parse_rate"], 0.5)
        self.assertEqual(t["none"]["fields"], {"time": 1.0, "hue": 0.5})
        self.assertEqual(t["none"]["ghost_rate"], 0.0)
        self.assertIsNone(t["none"]["pick_rate"])


if __name__ == "__main__":
    unittest.main()
