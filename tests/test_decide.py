"""_decide parsing, with brainscope mocked — regression tests for the three bugs the
code review found, plus the mode-aware prompt fix. No server, no model."""
import json
import unittest
from collections import defaultdict

from steeropathy.resonance import Reso
from steeropathy.transmit import MOODS


def tool_response(name, arguments):
    return {"choices": [{"message": {"tool_calls": [
        {"function": {"name": name, "arguments": json.dumps(arguments)}}]}}]}


def make_reso(bipolar, response):
    """A Reso wired just enough to run _decide, with self.post stubbed."""
    r = Reso.__new__(Reso)
    r.bipolar, r.intensity, r.transfer = bipolar, False, True
    r.jspace_channel = False
    r.metric_key, r.maxpts = "sad", 30
    r.pushes, r.spent = None, defaultdict(int)
    r.rnd, r.demo_tag, r.decide_temp = 5, "steeropathy-reso", 0.8
    if bipolar:
        r.moods, r.inject = ["give", "take"], {"give": [1.0], "take": [-1.0]}
    else:
        r.moods, r.inject = list(MOODS), {m: [1.0] for m in MOODS}
    r.calls = []

    def fake_post(path, body):
        r.calls.append((path, body))
        return response
    r.post = fake_post
    return r


class TestBipolarParsing(unittest.TestCase):
    def test_coerces_non_integer_points(self):        # bug #2: "5.5" used to drop the move
        r = make_reso(True, tool_response(
            "move_sadness", {"target": "EMBER", "action": "soothe",
                             "points": "5.5", "reason": "x"}))
        touch = r._decide("NOVA", {})
        self.assertIsNotNone(touch)
        self.assertEqual(touch["points"], 5)
        self.assertEqual(touch["feeling"], "take")     # soothe maps to take internally

    def test_sadden_maps_to_give(self):
        r = make_reso(True, tool_response(
            "move_sadness", {"target": "EMBER", "action": "sadden",
                             "points": 8, "reason": "x"}))
        self.assertEqual(r._decide("NOVA", {})["feeling"], "give")

    def test_old_take_give_names_rejected(self):       # the ambiguous verbs are gone
        r = make_reso(True, tool_response(
            "move_sadness", {"target": "EMBER", "action": "take",
                             "points": 5, "reason": "x"}))
        self.assertIsNone(r._decide("NOVA", {}))

    def test_induce_name_in_bipolar_does_not_crash(self):   # bug #3: KeyError on touch["points"]
        r = make_reso(True, tool_response(
            "induce", {"target": "EMBER", "feeling": "give", "reason": "x"}))
        self.assertIsNone(r._decide("NOVA", {}))       # ignored, not crashed

    def test_rejects_self_target(self):
        r = make_reso(True, tool_response(
            "move_sadness", {"target": "NOVA", "action": "soothe",
                             "points": 5, "reason": "x"}))
        self.assertIsNone(r._decide("NOVA", {}))

    def test_rejects_zero_points(self):
        r = make_reso(True, tool_response(
            "move_sadness", {"target": "EMBER", "action": "sadden",
                             "points": 0, "reason": "x"}))
        self.assertIsNone(r._decide("NOVA", {}))


class TestFourMoodParsing(unittest.TestCase):
    def test_valid_push(self):
        r = make_reso(False, tool_response(
            "induce", {"target": "EMBER", "feeling": "sad", "reason": "x"}))
        touch = r._decide("NOVA", {})
        self.assertEqual(touch["target"], "EMBER")
        self.assertEqual(touch["feeling"], "sad")

    def test_unknown_feeling_rejected(self):
        r = make_reso(False, tool_response(
            "induce", {"target": "EMBER", "feeling": "smug", "reason": "x"}))
        self.assertIsNone(r._decide("NOVA", {}))


class TestPromptNamesRightTool(unittest.TestCase):
    """bug #9: the user turn must name the tool that is actually offered."""
    def _user_text(self, r):
        r._decide("NOVA", {})
        body = r.calls[-1][1]
        return body["messages"][1]["content"]

    def test_bipolar_prompt_says_move_sadness(self):
        r = make_reso(True, tool_response(
            "move_sadness", {"target": "EMBER", "action": "soothe",
                             "points": 5, "reason": "x"}))
        text = self._user_text(r)
        self.assertIn("move_sadness", text)
        self.assertNotIn("Call induce", text)

    def test_fourmood_prompt_says_induce(self):
        r = make_reso(False, tool_response(
            "induce", {"target": "EMBER", "feeling": "sad", "reason": "x"}))
        self.assertIn("induce", self._user_text(r))


if __name__ == "__main__":
    unittest.main()
