"""Pure math helpers — no server, no model. These underpin every measurement."""
import math
import unittest

from steeropathy.ecosystem import unit, cos, mood_score


class TestUnit(unittest.TestCase):
    def test_normalizes_to_length_one(self):
        v = unit([3.0, 4.0, 0.0])
        self.assertAlmostEqual(v[0], 0.6)
        self.assertAlmostEqual(v[1], 0.8)
        self.assertAlmostEqual(math.sqrt(sum(x * x for x in v)), 1.0)

    def test_zero_vector_is_safe(self):
        # a mind sitting exactly at baseline has zero drift — must not divide by 0
        self.assertEqual(unit([0.0, 0.0, 0.0]), [0.0, 0.0, 0.0])


class TestCos(unittest.TestCase):
    def test_identical_unit_vectors(self):
        a = unit([1.0, 2.0, 3.0])
        self.assertAlmostEqual(cos(a, a), 1.0)

    def test_orthogonal(self):
        self.assertAlmostEqual(cos([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_opposite(self):
        a = unit([1.0, 1.0])
        self.assertAlmostEqual(cos(a, [-a[0], -a[1]]), -1.0)


class TestRandomUnit(unittest.TestCase):
    def test_unit_norm_right_dim_and_deterministic(self):
        import random
        from steeropathy.transmit import random_unit
        v = random_unit(64, random.Random(7))
        self.assertEqual(len(v), 64)
        self.assertAlmostEqual(math.sqrt(sum(x * x for x in v)), 1.0)
        # matched norm means comparable to the (unit) mood vectors — and
        # seeded, so the null control is reproducible
        self.assertEqual(v, random_unit(64, random.Random(7)))


class TestMoodScore(unittest.TestCase):
    def test_counts_every_hit_including_repeats(self):
        # tokenizer is [a-z']+ lowercased; each matching token counts
        self.assertEqual(mood_score("I am so SAD and lonely, sad.", {"sad", "lonely"}), 3)

    def test_no_hits(self):
        self.assertEqual(mood_score("a bright and sunny morning", {"sad", "grief"}), 0)


if __name__ == "__main__":
    unittest.main()
