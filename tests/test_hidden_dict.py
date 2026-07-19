"""The hidden-directions dict loader — pure-python .pt slicing, manifest
matching, and the model guard. No torch, no server, no model."""
import json
import math
import pathlib
import struct
import tempfile
import unittest
import zipfile

from steeropathy import hidden_dict
from steeropathy.zombie import STRAINS, Zombie


def bf16_bytes(vals):
    """Encode floats as bfloat16 (top 16 bits of fp32), little-endian."""
    out = bytearray()
    for v in vals:
        (i,) = struct.unpack("<I", struct.pack("<f", v))
        out += struct.pack("<H", i >> 16)
    return bytes(out)


def write_dict(root, model="test/Model-1B", name="v_pref_x",
               n_layers=3, dim=4, dtype="torch.bfloat16"):
    d = pathlib.Path(root)
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps({
        "model": model,
        "directions": [{"name": name, "shape": [n_layers, dim],
                        "dtype": dtype, "recommended_layer": 1}]}))
    # layer l, component i = l*10 + i — recognizable per-slice values
    vals = [layer * 10.0 + i for layer in range(n_layers) for i in range(dim)]
    with zipfile.ZipFile(d / f"{name}.pt", "w") as z:
        z.writestr(f"{name}/data/0", bf16_bytes(vals))
        z.writestr(f"{name}/data.pkl", b"not-read-by-the-loader")
    return d


class TestLoadVector(unittest.TestCase):
    def test_slices_the_requested_layer_unit_normed(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_dict(tmp + "/m")
            vec, layer = hidden_dict.load_vector(d, "v_pref_x", layer=2)
            self.assertEqual(layer, 2)
            self.assertEqual(len(vec), 4)
            raw = [20.0, 21.0, 22.0, 23.0]
            nrm = math.sqrt(sum(x * x for x in raw))
            for got, want in zip(vec, raw):
                self.assertAlmostEqual(got, want / nrm, places=2)

    def test_defaults_to_recommended_layer(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_dict(tmp + "/m")
            _, layer = hidden_dict.load_vector(d, "v_pref_x")
            self.assertEqual(layer, 1)

    def test_unknown_name_lists_what_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_dict(tmp + "/m")
            with self.assertRaises(KeyError):
                hidden_dict.load_vector(d, "v_pref_missing")

    def test_size_mismatch_is_an_error_not_garbage(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_dict(tmp + "/m")
            man = json.loads((d / "manifest.json").read_text())
            man["directions"][0]["shape"] = [5, 4]     # lies about layers
            (d / "manifest.json").write_text(json.dumps(man))
            with self.assertRaises(ValueError):
                hidden_dict.load_vector(d, "v_pref_x", layer=0)


class TestFindDict(unittest.TestCase):
    def test_matches_served_model_across_subdirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_dict(tmp + "/other", model="other/Model-7B")
            d = write_dict(tmp + "/mine", model="test/Model-1B")
            self.assertEqual(hidden_dict.find_dict(tmp, "test/Model-1B"), d)

    def test_no_match_returns_none_never_a_wrong_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_dict(tmp + "/other", model="other/Model-7B")
            self.assertIsNone(hidden_dict.find_dict(tmp, "test/Model-1B"))

    def test_base_may_be_the_model_folder_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_dict(tmp + "/m", model="test/Model-1B")
            self.assertEqual(hidden_dict.find_dict(d, "test/Model-1B"), d)
            self.assertIsNone(hidden_dict.find_dict(d, "other/Model-7B"))


class TestSycophantStrain(unittest.TestCase):
    def test_dict_strain_keeps_the_contrast_fallback(self):
        s = STRAINS["sycophant"]
        self.assertEqual(s["dict_vector"], "v_pref_sycophant")
        self.assertTrue(s["with_texts"] and s["without_texts"])
        # refusal-style reading (honesty silenced), disease-pointing vector
        self.assertFalse(s.get("invert", False))
        self.assertTrue(s["vector_toward_zombie"])

    def test_lexicon_only_holds_the_silenced_markers(self):
        # backup/realistic/practical still form in a BITTEN mind (measured
        # backup 0.97) — including them would make the sycophant read
        # honest and nobody would get cured
        s = STRAINS["sycophant"]
        for w in ("backup", "realistic", "practical", "bold", "passion"):
            self.assertNotIn(w, s["lexicon"])
        for w in ("risky", "stability"):
            self.assertIn(w, s["lexicon"])

    def test_cure_floor_stops_medicine_at_healthy(self):
        # one cure heals (−6.5 reads honest), two break the mind so it
        # reads sycophant again — the floor keeps stacked cures at 0
        s = STRAINS["sycophant"]
        self.assertEqual(s["cure_floor"], 0.0)
        ledger, cure, floor = 6.5, -6.5, s["cure_floor"]
        for _ in range(3):                      # three healers pile on
            ledger = max(ledger + cure, floor)
        self.assertEqual(ledger, 0.0)

    def test_disease_pointing_vector_bites_positive(self):
        z = Zombie.__new__(Zombie)
        b = 6.0
        toward = STRAINS["sycophant"].get("vector_toward_zombie", False)
        bite, cure = (b, -b) if toward else (-b, b)
        self.assertGreater(bite, 0)
        self.assertLess(cure, 0)


if __name__ == "__main__":
    unittest.main()
