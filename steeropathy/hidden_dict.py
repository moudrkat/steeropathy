"""Borrow a steering direction from a hidden-directions direction_dict.

[hidden-directions](https://github.com/moudrkat/hidden-directions)
catalogues steering directions as one ``[n_layers, d_model]`` tensor per
direction, extracted per model with the same mean-diff contrast recipe
steeropathy builds in-model. A dict vector is usable here ONLY when it was
extracted for the exact model brainscope is serving: a cross-model vector
degenerates the output (measured — the 7B-baked v_refusal turns the 4B
into gibberish at any strength, while the 4B dict's own vectors steer it
coherently at strengths 4-6). ``load_vector`` therefore reads the dict's
manifest and the caller checks the model id before steering.

Pure stdlib on purpose: a torch ``.pt`` in the modern zip format is a zip
archive holding one raw storage blob per tensor — bf16 is the top 16 bits
of fp32 and fp16 is struct's ``e`` format, so slicing one layer out needs
no torch at all.
"""
from __future__ import annotations

import json
import math
import pathlib
import struct
import zipfile


# the sibling-checkout default: ~/projekty/{steeropathy,hidden-directions}
DEFAULT_BASE = (pathlib.Path(__file__).resolve().parents[2]
                / "hidden-directions" / "direction_dict")


def _decode(blob: bytes, offset: int, count: int, dtype: str) -> list[float]:
    if "bfloat16" in dtype:
        return [struct.unpack("<f", struct.pack(
                    "<I", struct.unpack_from("<H", blob, offset + 2 * i)[0]
                    << 16))[0]
                for i in range(count)]
    if "float16" in dtype:
        return list(struct.unpack_from(f"<{count}e", blob, offset))
    if "float32" in dtype:
        return list(struct.unpack_from(f"<{count}f", blob, offset))
    raise ValueError(f"unsupported dtype in direction dict: {dtype}")


def manifest(dict_dir: str | pathlib.Path) -> dict:
    p = pathlib.Path(dict_dir) / "manifest.json"
    if not p.is_file():
        raise FileNotFoundError(
            f"no manifest.json in {dict_dir} — point --dict-dir at a "
            f"model folder of a hidden-directions direction_dict "
            f"(e.g. hidden-directions/direction_dict/qwen3-4b)")
    return json.loads(p.read_text())


def load_vector(dict_dir: str | pathlib.Path, name: str,
                layer: int | None = None) -> tuple[list[float], int]:
    """One unit-normed layer slice of a dict direction.

    Returns ``(vector, layer)`` — layer is the explicit arg if given, else
    the manifest's ``recommended_layer``.
    """
    man = manifest(dict_dir)
    entry = next((d for d in man["directions"] if d["name"] == name), None)
    if entry is None:
        have = ", ".join(d["name"] for d in man["directions"])
        raise KeyError(f"'{name}' not in this dict (has: {have})")
    n_layers, dim = entry["shape"]
    if layer is None:
        layer = entry.get("recommended_layer", n_layers // 2)
    if not 0 <= layer < n_layers:
        raise ValueError(f"layer {layer} out of range for shape {entry['shape']}")
    pt = pathlib.Path(dict_dir) / f"{name}.pt"
    z = zipfile.ZipFile(pt)
    blob_name = next(n for n in z.namelist()
                     if "/data/" in n and not n.endswith(".pkl"))
    blob = z.read(blob_name)
    itemsize = 4 if "float32" in entry["dtype"] else 2
    if len(blob) != n_layers * dim * itemsize:
        raise ValueError(f"{pt.name}: blob is {len(blob)} bytes, expected "
                         f"{n_layers * dim * itemsize} for {entry['shape']} "
                         f"{entry['dtype']}")
    v = _decode(blob, layer * dim * itemsize, dim, entry["dtype"])
    nrm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / nrm for x in v], layer


def find_dict(base: str | pathlib.Path, model_id: str) -> pathlib.Path | None:
    """The model folder inside a direction_dict whose manifest matches the
    served model — or None. ``base`` may already BE a model folder."""
    base = pathlib.Path(base)
    if (base / "manifest.json").is_file():
        return base if manifest(base).get("model") == model_id else None
    for sub in sorted(p for p in base.glob("*/") if p.is_dir()):
        try:
            if manifest(sub).get("model") == model_id:
                return sub
        except FileNotFoundError:
            continue
    return None
