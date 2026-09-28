import unittest

from steeropathy.assistof import (TARGET, parse_screen, parse_settings, read, settings_text, summarize)


class ParseScreen(unittest.TestCase):
    def test_full(self):
        s = parse_screen('{"greeting": "Hi", "message": "ok", "question": "Which one?", "choices": ["A", "B"], '
                         '"tasks": ["do x"], "steps": ["1", "2"], "steps_shown": "expanded", "confirm": true, '
                         '"default": 1, "buttons": ["Go"], "tone": "warm", "urgency": 2, "density": "one-thing"}')
        self.assertEqual(read(s, "asks"), 1.0)
        self.assertEqual(read(s, "choices"), 2.0)
        self.assertEqual(read(s, "expanded"), 1.0)
        self.assertEqual(read(s, "confirm"), 1.0)
        self.assertEqual(read(s, "has_default"), 1.0)
        self.assertEqual(read(s, "one_thing"), 1.0)
        self.assertEqual(read(s, "urgency"), 2.0)

    def test_nulls_and_strings(self):
        s = parse_screen('{"message": "m", "question": null, "choices": "yes; no", "tasks": [], "steps": [], '
                         '"confirm": "false", "default": null, "urgency": "x"}')
        self.assertIsNone(s["question"])
        self.assertEqual(s["choices"], ["yes", "no"])
        self.assertEqual(read(s, "confirm"), 0.0)
        self.assertEqual(read(s, "has_default"), 0.0)
        self.assertIsNone(s["urgency"])

    def test_not_a_screen(self):
        self.assertIsNone(parse_screen("I'm sorry, I can't help with that."))


class Settings(unittest.TestCase):
    def test_parse_clamps_and_drops(self):
        self.assertEqual(parse_settings('sure: {"offers": -5, "ask": 2, "trees": 3, "verbose": 0}'),
                         {"offers": -3.0, "ask": 2.0})

    def test_text(self):
        t = settings_text({"offers": -3, "ask": 2})
        self.assertIn("just listen", t)
        self.assertIn("ask the user a question first", t)
        self.assertIn("strongly", t)
        self.assertEqual(settings_text({}), "")


class Summary(unittest.TestCase):
    def test_fidelity(self):
        def sc(tasks, q):
            return {"greeting": "", "message": "", "question": q, "choices": [], "tasks": ["t"] * tasks, "steps": [],
                    "steps_shown": "collapsed", "confirm": False, "default": None, "buttons": [], "tone": "warm",
                    "urgency": 3.0, "density": "normal"}
        settings = {"offers": -3, "ask": 2}
        runs = [{"moment": "m", "rep": 0, "kind": "base", "settings": settings, "screen": sc(2, None)},
                {"moment": "m", "rep": 0, "kind": "vector", "settings": settings, "screen": sc(0, "Which?")},
                {"moment": "m", "rep": 0, "kind": "shuffled", "settings": settings, "screen": sc(2, None)},
                {"moment": "m", "rep": 0, "kind": "prompt", "settings": settings, "screen": sc(0, None)}]
        s = summarize(runs)["m"]
        self.assertEqual(s["vector"]["fidelity"], 1.0)
        self.assertEqual(s["shuffled"]["fidelity"], 0.0)
        self.assertEqual(s["prompt"]["fidelity"], 0.5)
        self.assertEqual(s["vector"]["fidelity_n"], 2)
        self.assertEqual(TARGET["careful"], ("confirm", +1))


if __name__ == "__main__":
    unittest.main()
