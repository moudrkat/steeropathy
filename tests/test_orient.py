"""orient, offline: the map's tools on a toy map, and the agent's parsing."""
import pathlib
import tempfile
import unittest

import torch

from steeropathy.orient import TokenMap, _first_json, gain, read_worlds, recipe_str, BRIEFS


def toy_map():
    words = ["night", "dark", "cavern", "noon", "bright", "apple"]
    D = torch.tensor([[1.0, 0.0, 0.0], [0.9, 0.1, 0.0], [0.8, 0.2, 0.1],
                      [-1.0, 0.0, 0.0], [-0.9, 0.1, 0.0], [0.0, 0.0, 1.0]])
    D = D / D.norm(dim=-1, keepdim=True)
    p = pathlib.Path(tempfile.mkdtemp()) / "toy.pt"
    torch.save({"model": "toy", "layer": 1, "words": words, "ids": list(range(6)), "D": D.half()}, p)
    return TokenMap(p)


class MapTools(unittest.TestCase):
    def test_near_leaves_the_word_out_and_ranks_by_cosine(self):
        tm = toy_map()
        nb = tm.near("night", 3)
        self.assertEqual([w for w, _ in nb], ["dark", "cavern", "apple"])
        self.assertIsNone(tm.near("zebra"))

    def test_words_of_reads_a_vector_both_ways(self):
        tm = toy_map()
        r = tm.words_of([1.0, 0.0, 0.0], 2)
        self.assertEqual([w for w, _ in r["nearest"]], ["night", "dark"])
        self.assertEqual([w for w, _ in r["farthest"]], ["noon", "bright"])

    def test_vector_sums_with_signs_and_is_unit(self):
        tm = toy_map()
        v = torch.tensor(tm.vector([("night", 1.0), ("noon", -1.0)]))
        self.assertAlmostEqual(float(v.norm()), 1.0, places=5)
        self.assertGreater(float(v[0]), 0.99)
        with self.assertRaises(KeyError):
            tm.vector([("zebra", 1.0)])


class Readings(unittest.TestCase):
    def test_gain_follows_want(self):
        self.assertEqual(gain(0.3, 0.6, -1), 0.3)
        self.assertEqual(gain(0.3, 0.6, +1), -0.3)
        self.assertIsNone(gain(None, 0.6, 1))

    def test_read_worlds_counts_fields_and_skips_unparsed(self):
        worlds = [{"time": "night", "weather": "snow", "ground": "ice", "sky": ["#000000", "#222222"],
                   "elements": [{"kind": "tree"}, {"kind": "tree"}], "title": "a"},
                  None,
                  {"time": "midnight", "weather": "clear", "ground": "ice", "sky": ["#ffffff"],
                   "elements": [{"kind": "cat"}], "title": "b"}]
        r = read_worlds(worlds, BRIEFS["winter"])
        self.assertEqual((r["n"], r["parsed"]), (3, 2))
        self.assertEqual(r["value"], 0.5)
        self.assertEqual(r["fields"]["time"][0], ("night", 2))
        self.assertEqual(r["things"][0], ("tree", 2))
        self.assertEqual(read_worlds(worlds, BRIEFS["night"])["value"], 3.0)

    def test_agent_json_and_recipe_strings(self):
        self.assertEqual(_first_json('sure {"near": "dark"} ok'), {"near": "dark"})
        self.assertIsNone(_first_json("no json here"))
        self.assertEqual(recipe_str([("quiet", 1.0), ("loud", -1.0)]), "quiet ~loud")


if __name__ == "__main__":
    unittest.main()
