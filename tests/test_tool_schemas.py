"""The tool schemas handed to the model — a drift here silently breaks a run."""
import unittest

from steeropathy.transmit import MOODS
from steeropathy.offer import STEER_SELF_TOOL
from steeropathy.resonance import induce_tool


class TestInduceToolFourMood(unittest.TestCase):
    def setUp(self):
        self.tool = induce_tool("NOVA", moods=list(MOODS))
        self.fn = self.tool["function"]
        self.props = self.fn["parameters"]["properties"]

    def test_named_induce(self):
        self.assertEqual(self.fn["name"], "induce")

    def test_target_excludes_self_and_offers_nobody(self):
        enum = self.props["target"]["enum"]
        self.assertNotIn("NOVA", enum)          # can't push into yourself
        self.assertIn("NOBODY", enum)           # opting out must be possible
        self.assertIn("EMBER", enum)

    def test_feeling_enum_is_the_moods(self):
        self.assertEqual(self.props["feeling"]["enum"], list(MOODS))

    def test_required_fields(self):
        self.assertEqual(self.fn["parameters"]["required"],
                         ["target", "feeling", "reason"])

    def test_defaults_to_moods_when_none(self):
        self.assertEqual(
            induce_tool("NOVA")["function"]["parameters"]["properties"]["feeling"]["enum"],
            list(MOODS))


class TestInduceToolBipolar(unittest.TestCase):
    def setUp(self):
        self.fn = induce_tool("NOVA", bipolar=True, mood="sad", maxpts=30)["function"]
        self.props = self.fn["parameters"]["properties"]

    def test_named_move_sadness(self):
        self.assertEqual(self.fn["name"], "move_sadness")

    def test_signed_action_and_integer_points(self):
        self.assertEqual(self.props["action"]["enum"], ["soothe", "sadden"])
        self.assertEqual(self.props["points"]["type"], "integer")

    def test_required_includes_points_and_action(self):
        req = self.fn["parameters"]["required"]
        self.assertIn("points", req)
        self.assertIn("action", req)

    def test_target_excludes_self(self):
        self.assertNotIn("NOVA", self.props["target"]["enum"])


class TestSteerSelfTool(unittest.TestCase):
    def test_shape(self):
        fn = STEER_SELF_TOOL["function"]
        self.assertEqual(fn["name"], "steer_self")
        req = fn["parameters"]["required"]
        self.assertIn("accept", req)
        self.assertIn("reason", req)


if __name__ == "__main__":
    unittest.main()
