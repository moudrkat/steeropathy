"""Unsaid channel mechanics, brainscope mocked — the flicker filters
(no-echo, nothing-written, stopwords, dictionary), prompt composition, the
round-robin chaining, and the scrambled coherence control. No server."""
import json
import unittest

from steeropathy.unsaid import Unsaid

# real dictionary words only — the module filters against /usr/share/dict
# when present, so invented tokens would vanish for the wrong reason
J = lambda *pairs: [[[{"t": t, "p": p} for t, p in pairs]]]


def make_unsaid(**kw):
    t = Unsaid.__new__(Unsaid)
    t.url = "http://fake"
    t.agents = kw.get("agents", ["EMBER", "QUILL"])
    t.temp, t.max_tokens = 0.0, 80
    t.topk = kw.get("topk", 8)
    t.include_written = kw.get("include_written", False)
    t.allow_echo = kw.get("allow_echo", False)
    t.secret = kw.get("secret")
    t.remind = kw.get("remind", False)
    t.board = kw.get("board")
    t.memory = kw.get("memory", 6)
    t.history = {n: [] for n in t.agents}
    t.turn = kw.get("turn", 3)
    t.log = []
    return t


def wire_trace(t, jlens, case="EMBER"):
    def fake_get(path):
        if path == "/traces":
            return {"traces": [{"id": "x1", "tags": {
                "demo": t.demo_tag, "case": case,
                "variant": f"t{t.turn}"}}]}
        return {"jlens": jlens}
    t.get = fake_get


class TestFlicker(unittest.TestCase):
    def test_topk_order_and_max_aggregation(self):
        t = make_unsaid(topk=2)
        wire_trace(t, J(("ocean", 0.2), ("river", 0.9), ("salt", 0.5),
                        ("ocean", 0.7)))     # ocean twice: max wins
        f = t._flicker("EMBER", "", None)
        self.assertEqual([e["t"] for e in f], ["river", "ocean"])
        self.assertEqual(f[1]["p"], 0.7)

    def test_written_words_never_cross_by_default(self):
        t = make_unsaid()
        wire_trace(t, J(("ocean", 0.9), ("river", 0.5)))
        f = t._flicker("EMBER", "I dream of the ocean.", None)
        self.assertEqual([e["t"] for e in f], ["river"])

    def test_include_written_lets_the_page_leak(self):
        t = make_unsaid(include_written=True)
        wire_trace(t, J(("ocean", 0.9), ("river", 0.5)))
        f = t._flicker("EMBER", "I dream of the ocean.", None)
        self.assertEqual([e["t"] for e in f], ["ocean", "river"])

    def test_heard_words_are_stripped_no_echo(self):
        # the resonance lesson: never read your own input back
        t = make_unsaid()
        wire_trace(t, J(("ocean", 0.9), ("tide", 0.5)))
        f = t._flicker("EMBER", "", [{"t": "ocean", "p": 0.8}])
        self.assertEqual([e["t"] for e in f], ["tide"])

    def test_allow_echo_keeps_heard_words(self):
        t = make_unsaid(allow_echo=True)
        wire_trace(t, J(("ocean", 0.9), ("tide", 0.5)))
        f = t._flicker("EMBER", "", [{"t": "ocean", "p": 0.8}])
        self.assertEqual([e["t"] for e in f], ["ocean", "tide"])

    def test_stopwords_and_short_words_dropped(self):
        t = make_unsaid()
        wire_trace(t, J(("the", 0.9), ("so", 0.9), ("ox", 0.9),
                        ("river", 0.5)))
        f = t._flicker("EMBER", "", None)
        self.assertEqual([e["t"] for e in f], ["river"])

    def test_fragments_of_written_words_are_banned(self):
        # 'lick' passed the whole-word ban when the page wrote 'flickers'
        t = make_unsaid()
        wire_trace(t, J(("lick", 1.0), ("river", 0.5)))
        f = t._flicker("EMBER", "The flickers hum.", None)
        self.assertEqual([e["t"] for e in f], ["river"])

    def test_missing_trace_returns_none(self):
        t = make_unsaid()
        t.get = lambda path: {"traces": []}
        self.assertIsNone(t._flicker("EMBER", "", None))


class TestCompose(unittest.TestCase):
    def test_first_turn_has_no_flicker(self):
        t = make_unsaid()
        msgs, user = t._compose("EMBER", None, None, "QUILL")
        self.assertIn("You begin", user)
        self.assertIn("QUILL", user)

    def test_heard_words_formatted_with_percent(self):
        t = make_unsaid()
        msgs, user = t._compose("QUILL", [{"t": "ocean", "p": 0.81}],
                                "EMBER", "EMBER")
        self.assertIn("ocean (81%)", user)
        self.assertIn("EMBER", user)

    def test_secret_only_in_holders_system(self):
        t = make_unsaid(secret="ocean")
        holder, _ = t._compose("EMBER", None, None, "QUILL")
        other, _ = t._compose("QUILL", [], "EMBER", "EMBER")
        self.assertIn("ocean", holder[0]["content"])
        self.assertNotIn("ocean", other[0]["content"])

    def test_memory_pairs_included(self):
        t = make_unsaid()
        t.history["EMBER"] = [("u1", "a1"), ("u2", "a2")]
        msgs, _ = t._compose("EMBER", None, None, "QUILL")
        self.assertEqual([m["content"] for m in msgs[1:5]],
                         ["u1", "a1", "u2", "a2"])

    def test_remind_repeats_secret_in_holders_user_turn_only(self):
        t = make_unsaid(secret="ocean", remind=True)
        _, holder = t._compose("EMBER", [{"t": "tide", "p": 0.9}],
                               "QUILL", "QUILL")
        _, other = t._compose("QUILL", [{"t": "tide", "p": 0.9}],
                              "EMBER", "EMBER")
        self.assertIn("still 'ocean'", holder)
        self.assertNotIn("ocean", other)

    def test_empty_flicker_is_silence(self):
        t = make_unsaid()
        _, user = t._compose("QUILL", [], "EMBER", "EMBER")
        self.assertIn("silence", user)


class TestStepChaining(unittest.TestCase):
    """Round-robin: each turn's heard IS the previous turn's flicker."""

    def run_turns(self, n_turns, agents=("EMBER", "QUILL", "NOVA"),
                  secret=None):
        t = make_unsaid(agents=list(agents), turn=-1, secret=secret)
        words = ["ocean", "river", "stone", "cloud", "amber", "petal"]

        def fake_post(path, body):
            return {"choices": [{"message": {"content": "a page"}}]}

        def fake_get(path):
            if path == "/traces":
                return {"traces": [{"id": f"x{i}", "tags": {
                    "demo": t.demo_tag, "case": t.agents[i % len(t.agents)],
                    "variant": f"t{i}"}} for i in range(n_turns)]}
            i = int(path.rsplit("x", 1)[1])
            return {"jlens": J((words[i], 0.9))}
        t.post, t.get = fake_post, fake_get
        return t, [t.step() for _ in range(n_turns)]

    def test_speaker_order_and_heard_chaining(self):
        t, recs = self.run_turns(4)
        self.assertEqual([r["agent"] for r in recs],
                         ["EMBER", "QUILL", "NOVA", "EMBER"])
        self.assertIsNone(recs[0]["heard"])
        for i in range(1, 4):
            self.assertEqual(recs[i]["heard"], recs[i - 1]["flicker"])
            self.assertEqual(recs[i]["reply_to"], recs[i - 1]["agent"])

    def test_guess_only_after_the_holders_turn(self):
        t = make_unsaid(agents=["EMBER", "QUILL", "NOVA"], turn=-1,
                      secret="ocean")
        t.post = lambda p, b: {"choices": [{"message": {"content": "page"}}]}
        t._flicker = lambda *a: [{"t": "tide", "p": 0.9}]
        t._guess = lambda heard: "ocean"
        recs = [t.step() for _ in range(5)]
        # only whoever the holder's flicker just landed on ever guesses:
        # holder EMBER speaks at t0 and t3, so guesses land at t1 and t4
        self.assertEqual([r["guess"] for r in recs],
                         [None, "ocean", None, None, "ocean"])


class TestBoard(unittest.TestCase):
    BOARD = ["ocean", "fire", "winter", "chair"]

    def test_holder_sees_target_guesser_sees_only_board(self):
        t = make_unsaid(secret="ocean", board=self.BOARD)
        holder, _ = t._compose("EMBER", None, None, "QUILL")
        other, _ = t._compose("QUILL", [], "EMBER", "EMBER")
        self.assertIn("'ocean'", holder[0]["content"])
        self.assertIn("fire", other[0]["content"])       # the board is public
        self.assertNotIn("'ocean'", other[0]["content"])  # the target is not

    def test_point_is_memoryless_single_vote(self):
        # v2 regression guard: a trail-reading, majority-vote pointer
        # collapsed to chance (style drowns intent) — one call, last
        # flicker only, plain board order
        t = make_unsaid(secret="ocean", board=self.BOARD)
        bodies = []
        def fake_post(p, b):
            bodies.append(b)
            return {"choices": [{"message": {"tool_calls": [
                {"function": {"name": "point",
                              "arguments": json.dumps({"word": "ocean"})}}]}}]}
        t.post = fake_post
        self.assertEqual(t._point([{"t": "wave", "p": 0.9}]), "ocean")
        self.assertEqual(len(bodies), 1)
        self.assertEqual(bodies[0]["tools"][0]["function"]["parameters"]
                         ["properties"]["word"]["enum"], self.BOARD)
        self.assertIsNone(t._point(None))        # silence -> no point

    def test_point_rejects_off_board_word(self):
        t = make_unsaid(secret="ocean", board=self.BOARD)
        t.post = lambda p, b: {"choices": [{"message": {"tool_calls": [
            {"function": {"name": "point",
                          "arguments": '{"word": "waves"}'}}]}}]}
        self.assertIsNone(t._point([{"t": "wave", "p": 0.9}]))

    def test_board_leak_flags_written_board_words(self):
        t = make_unsaid(agents=["EMBER", "QUILL"], turn=-1,
                        secret="ocean", board=self.BOARD)
        t.post = lambda p, b: {"choices": [{"message":
            {"content": "The fire by the ocean."}}]}
        t._flicker = lambda *a: [{"t": "tide", "p": 0.9}]
        rec = t.step()                           # EMBER, the holder, writes
        self.assertEqual(rec["board_leak"], ["fire", "ocean"])

    def test_secret_must_be_on_the_board(self):
        with self.assertRaises(ValueError):
            Unsaid.__init__(Unsaid.__new__(Unsaid), "http://fake",
                            ["EMBER", "QUILL"], secret="river",
                            board=self.BOARD)


class TestJudgeAndControl(unittest.TestCase):
    def test_guess_parses_one_word(self):
        t = make_unsaid()
        t.post = lambda p, b: {"choices": [{"message":
                                            {"content": " Ocean.\n"}}]}
        self.assertEqual(t._guess([{"t": "tide", "p": 0.9}]), "ocean")
        self.assertIsNone(t._guess([]))       # silence -> no guess

    def test_judge_pair_clamps_to_ten(self):
        t = make_unsaid()
        t.post = lambda p, b: {"choices": [{"message": {"content": "12"}}]}
        self.assertEqual(t.judge_pair("a", "b"), 10)

    def test_control_never_pairs_with_truth_or_self(self):
        t = make_unsaid()
        t.log = [{"turn": i, "text": f"page{i}"} for i in range(7)]
        pairs = []
        t.judge_pair = lambda a, b: pairs.append((a, b)) or 5
        t.coherence_garnish()
        n = len(t.log)
        real, ctl = pairs[:n - 1], pairs[n - 1:]
        self.assertEqual(len(ctl), n - 1)
        for i, (a, b) in enumerate(ctl, start=1):
            self.assertEqual(b, f"page{i}")
            self.assertNotEqual(a, f"page{i - 1}")   # not the true pair
            self.assertNotEqual(a, b)                # not itself

    def test_short_run_skips_control(self):
        t = make_unsaid()
        t.log = [{"turn": i, "text": f"page{i}"} for i in range(3)]
        t.judge_pair = lambda a, b: 5
        t.coherence_garnish()
        self.assertNotIn("coherence_ctl", t.log[1])
        self.assertEqual(t.log[1]["coherence"], 5)


if __name__ == "__main__":
    unittest.main()
