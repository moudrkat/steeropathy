"""runner-up mechanics, brainscope mocked: the candidate ranking read off
the logprob stream, the flicker readout (J-lens vs logit lens, written word
banned), the direction as a contrast, the signed-permutation placebo, the
reader's prompt per channel, and the scoring. No server."""
import json
import random
import unittest

from steeropathy.runnerup import RunnerUp, score, signed_perm, cos

# real dictionary words: the module filters against /usr/share/dict when
# present, and invented tokens would vanish for the wrong reason
STEPS = [
    {"token": "Answer", "top": [("Answer", -0.01)]},
    {"token": ":", "top": [(":", -0.01)]},
    {"token": " owl", "top": [(" owl", -0.4), (" fox", -1.2), (" wolf", -2.0),
                              (" cat", -2.5), (" moth", -3.0), (" the", -9)]},
]


def make(**kw):
    t = RunnerUp.__new__(RunnerUp)
    t.url = "http://fake"
    t.channels = kw.get("channels", ["none", "text", "jspace", "vector"])
    t.control = kw.get("control", "none")
    t.strength, t.layer, t.lo, t.hi = 4.0, 20, 16, 24
    t.topk, t.page_tokens, t.temp = 8, 70, 0.0
    t.rng = random.Random(0)
    t.demo_tag = "steeropathy-runnerup-test"
    t.jlens = kw.get("jlens", True)
    t.log = []
    return t


class TestCandidates(unittest.TestCase):
    def test_reads_the_answer_token_after_the_colon(self):
        c = RunnerUp.candidates(STEPS)
        self.assertEqual(c["words"], ["owl", "fox", "wolf", "cat", "moth"])
        self.assertEqual(c["step"], 2)
        self.assertAlmostEqual(c["logprobs"][0] - c["logprobs"][1], 0.8)

    def test_stopwords_and_short_tokens_do_not_count(self):
        steps = [{"token": " owl", "top": [(" owl", -0.4), (" the", -0.5),
                                           (" a", -0.6), (" fox", -1.2),
                                           (" wolf", -2), (" cat", -3),
                                           (" moth", -4)]}]
        c = RunnerUp.candidates(steps)
        self.assertEqual(c["words"][:2], ["owl", "fox"])

    def test_no_frame_falls_back_to_first_word(self):
        c = RunnerUp.candidates([STEPS[2]])
        self.assertEqual(c["words"][0], "owl")

    def test_too_few_real_words_is_unusable(self):
        steps = [{"token": ":", "top": []},
                 {"token": " owl", "top": [(" owl", -0.1), (" fox", -1)]}]
        self.assertIsNone(RunnerUp.candidates(steps))


class TestFlicker(unittest.TestCase):
    def trace(self, key, pairs):
        return {key: [[[{"t": t, "p": p} for t, p in pairs]]]}

    def test_written_winner_is_banned_and_topk_ordered(self):
        t = make()
        f = t.flicker(self.trace("jlens", [("owl", 0.9), ("fox", 0.3),
                                           ("moth", 0.6)]), ["owl"])
        self.assertEqual([e["t"] for e in f], ["moth", "fox"])

    def test_logit_control_reads_the_other_lens(self):
        t = make()
        tr = {"jlens": [[[{"t": "fox", "p": 0.5}]]],
              "lens": [[[{"t": "moth", "p": 0.5}]]]}
        self.assertEqual(t.flicker(tr, [])[0]["t"], "fox")
        self.assertEqual(t.flicker(tr, [], key="lens")[0]["t"], "moth")

    def test_no_trace_is_none_not_empty(self):
        self.assertIsNone(make().flicker(None, []))


class TestVector(unittest.TestCase):
    def test_direction_is_the_private_minus_public_contrast(self):
        t = make()
        calls = []

        def fake_post(path, body, timeout=600):
            calls.append(body["messages"][0]["content"])
            v = [1.0, 0.0, 0.0] if "sea" in calls[-1] else [0.0, 1.0, 0.0]
            return {"vector": v}
        t.post = fake_post
        d = t.direction("history. You grew up by the sea.", "history.",
                        "q", "Answer: owl")
        self.assertAlmostEqual(cos(d, d), 1.0)
        self.assertAlmostEqual(d[0], -d[1])
        self.assertEqual(len(calls), 2)

    def test_signed_perm_keeps_norm_and_kills_meaning(self):
        rng = random.Random(1)
        v = [rng.gauss(0, 1) for _ in range(2000)]
        r = signed_perm(v, seed=3)
        self.assertAlmostEqual(cos(v, v), cos(r, r), places=9)
        self.assertLess(abs(cos(v, r)) / cos(v, v), 0.1)
        self.assertEqual(signed_perm(v, seed=3), r)      # deterministic


class TestReader(unittest.TestCase):
    def test_prompt_per_channel(self):
        t = make()
        opts = ["fox", "wolf", "cat", "moth"]
        flick = [{"t": "moth", "p": 0.6}]
        none = t._reader_msgs("q", opts, "none", "owl", flick)[0]["content"]
        text = t._reader_msgs("q", opts, "text", "owl", flick)[0]["content"]
        js = t._reader_msgs("q", opts, "jspace", "owl", flick)[0]["content"]
        vec = t._reader_msgs("q", opts, "vector", "owl", flick)[0]["content"]
        self.assertNotIn("owl", none)
        self.assertIn("'owl'", text)
        self.assertNotIn("flickered", text)
        self.assertIn("moth (60%)", js)
        self.assertIn("'owl'", vec)
        self.assertNotIn("flickered", vec)
        for m in (none, text, js, vec):
            self.assertIn("fox, wolf, cat, moth", m)

    def test_reader_points_and_steers_only_on_vector(self):
        t = make()
        posted = []

        def fake_post(path, body, timeout=600):
            posted.append((path, body))
            if path == "/directions":
                return {}
            if "tools" in body:
                return {"choices": [{"message": {"tool_calls": [
                    {"function": {"name": "point",
                                  "arguments": json.dumps({"word": "fox"})}}]}}]}
            return {"choices": [{"message": {"content": "a page"}}]}
        t.post = fake_post
        cand = {"words": ["owl", "fox", "wolf", "cat", "moth"]}
        r = t.reader(0, "q", cand, "vector", None, [0.0, 1.0])
        self.assertTrue(r["hit"] and r["steered"])
        self.assertEqual(r["pick"], "fox")
        steer = [b for p, b in posted if b.get("steering")]
        self.assertEqual(len(steer), 1)               # the page, not the point
        self.assertNotIn("steering", posted[-1][1])   # the point is sober
        r = t.reader(0, "q", cand, "text", None, [0.0, 1.0])
        self.assertFalse(r["steered"])
        self.assertNotIn("owl", r["options"])


class TestScore(unittest.TestCase):
    def test_rates_and_moved_subset(self):
        log = [{"moved": True, "reads": [{"channel": "text", "hit": True},
                                         {"channel": "none", "hit": False}]},
               {"moved": False, "reads": [{"channel": "text", "hit": False},
                                          {"channel": "none", "hit": False}]},
               {"skipped": "x", "reads": []}]
        s = score(log)
        self.assertEqual(s["text"]["hits"], 1)
        self.assertEqual(s["text"]["n"], 2)
        self.assertEqual(s["text"]["rate_moved"], 1.0)
        self.assertEqual(s["none"]["rate"], 0.0)



class TestStreamFallback(unittest.TestCase):
    def test_plain_json_answer_yields_text_and_no_steps(self):
        import io
        from unittest import mock
        from steeropathy import runnerup

        class Resp(io.BytesIO):
            headers = {"Content-Type": "application/json"}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        payload = json.dumps({"choices": [{"message": {"content": "Owl."}}]}).encode()
        with mock.patch.object(runnerup.urllib.request, "urlopen",
                               lambda req, timeout=600: Resp(payload)):
            text, steps = runnerup.sse_stream("http://fake", {"messages": []})
        self.assertEqual((text, steps), ("Owl.", []))


if __name__ == "__main__":
    unittest.main()
