"""The core physics: feeling is conserved. Every push is a transfer (+x to one mind,
−x from another), so the sum of all ledgers only ever holds the seed — ‖Σ ledgers‖ = 1.
This is what makes 'the sadness never dissipates, it only changes hands' literally true.
Tested with no server: _ledger_add is self-contained."""
import math
import unittest

from steeropathy.resonance import Reso, PERSONAS


def sum_norm(ledger):
    dim = max((len(v) for v in ledger.values() if v), default=0)
    tot = [0.0] * dim
    for v in ledger.values():
        if v:
            for i, x in enumerate(v):
                tot[i] += x
    return math.sqrt(sum(x * x for x in tot))


def fresh(decay=1.0):
    r = Reso.__new__(Reso)                      # skip __init__ (it hits the server)
    r.ledger = {n: None for n in PERSONAS}
    r.seed_mood = "seed"
    r.inject = {"seed": [0.6, 0.8]}             # a unit vector
    r.decay = decay
    return r


class TestConservation(unittest.TestCase):
    def test_seed_lands_at_unit_norm(self):
        r = fresh()
        r._ledger_add("EMBER", r.inject["seed"], 1.0)
        self.assertAlmostEqual(sum_norm(r.ledger), 1.0)

    def test_a_transfer_is_zero_sum(self):
        r = fresh()
        r._ledger_add("EMBER", r.inject["seed"], 1.0)
        before = sum_norm(r.ledger)
        F = r.inject["seed"]
        r._ledger_add("ATLAS", F, +0.3)         # target gains
        r._ledger_add("NOVA", F, -0.3)          # giver loses the same
        self.assertAlmostEqual(sum_norm(r.ledger), before)

    def test_conserved_even_across_different_directions(self):
        # the invariant doesn't depend on *what* is pushed — transfers always cancel
        r = fresh()
        r._ledger_add("EMBER", r.inject["seed"], 1.0)
        before = sum_norm(r.ledger)
        for g, t, F, amt in [("EMBER", "NOVA", [1.0, 0.0], 0.5),
                             ("NOVA", "QUILL", [0.0, 1.0], 0.3),
                             ("QUILL", "ATLAS", [0.7, 0.7], 0.4)]:
            r._ledger_add(t, F, +amt)
            r._ledger_add(g, F, -amt)
        self.assertAlmostEqual(sum_norm(r.ledger), before)


if __name__ == "__main__":
    unittest.main()
