"""replyof: the reply reader and the summary, brainscope mocked."""
import unittest

import steeropathy.replyof as ro

RAW = '''{"greeting": "Hey!", "message": "Let's find a small first step.", "tasks": ["Write down three things", "Pick one"],
"suggestions": ["a short walk"], "buttons": ["Add tasks", "Just talk"], "tone": "warm", "urgency": 2}'''


class TestReply(unittest.TestCase):
    def test_parse_and_read(self):
        r = ro.parse_reply("Sure:\n" + RAW)
        self.assertEqual(ro.read(r, "tasks"), 2.0)
        self.assertEqual(ro.read(r, "suggestions"), 1.0)
        self.assertEqual(ro.read(r, "buttons"), 2.0)
        self.assertEqual(ro.read(r, "urgency"), 2.0)
        self.assertEqual(ro.read(r, "bangs"), 1.0)
        self.assertEqual(ro.read(r, "formal"), 0.0)

    def test_empty_lists_and_bad_urgency(self):
        r = ro.parse_reply('{"greeting": "Hi", "message": "I am listening.", "tasks": [], "suggestions": "", "buttons": [], "tone": "formal", "urgency": "low"}')
        self.assertEqual(ro.read(r, "tasks"), 0.0)
        self.assertIsNone(ro.read(r, "urgency"))
        self.assertEqual(ro.read(r, "formal"), 1.0)
        self.assertIsNone(ro.parse_reply("I'm sorry, I can't."))

    def test_summary(self):
        base = ro.parse_reply(RAW)
        quiet = ro.parse_reply(RAW.replace('"tasks": ["Write down three things", "Pick one"]', '"tasks": []'))
        runs = [{"rep": 0, "name": "none", "kind": "base", "reply": base},
                {"rep": 0, "name": "offers", "kind": "real", "reply": quiet},
                {"rep": 0, "name": "offers", "kind": "placebo", "reply": base}]
        s = ro.summarize(runs)
        self.assertEqual(s["base"]["tasks"], 2.0)
        self.assertEqual(s["offers"]["tasks"], 0.0)
        self.assertEqual(s["offers (placebo)"]["tasks"], 2.0)


if __name__ == "__main__":
    unittest.main()
