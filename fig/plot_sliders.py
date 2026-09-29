"""All the knobs: for each count direction, the number of that thing drawn
per world against the strength; for the brightness direction, the sky's
mean luminance. Real vector as a line, the shuffled vector in grey, the
unsteered worlds at zero.

    python fig/plot_sliders.py            # trees + crowded (worldof-13), six kinds (worldof-14), darker (worldof-15)
"""
import glob
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "fig"))
from style import SURF, curves, fonts  # noqa: E402
from steeropathy.secondhand import kinds_of  # noqa: E402
from steeropathy.worldof import READERS  # noqa: E402

PANELS = [  # (glob, direction, kind or None, title, y label)
    ("worldof-13-aorus-1.5b-knob-s*.json", "manytrees", "tree", "many trees − one tree", "trees per world"),
    ("worldof-13-aorus-1.5b-knob-s*.json", "crowded", None, "crowded − empty", "things per world"),
    ("worldof-14-aorus-1.5b-knob2-s*.json", "manybirds", "bird", "many birds − one bird", "birds per world"),
    ("worldof-14-aorus-1.5b-knob2-s*.json", "manyhouses", "house", "many houses − one house", "houses per world"),
    ("worldof-14-aorus-1.5b-knob2-s*.json", "manystars", "star", "many stars − one star", "stars per world"),
    ("worldof-14-aorus-1.5b-knob2-s*.json", "manycats", "cat", "many cats − one cat", "cats per world"),
    ("worldof-14-aorus-1.5b-knob2-s*.json", "manyflowers", "flower", "many flowers − one flower", "flowers per world"),
    ("worldof-14-aorus-1.5b-knob2-s*.json", "manyboats", "boat", "many boats − one boat", "boats per world"),
    ("worldof-15-aorus-1.5b-dark-s*.json", "darker", "lum", "dark − bright", "sky luminance (0 black, 1 white)"),
    ("worldof-17-aorus-1.5b-more-s*.json", "later", "hour", "late − early", "hour (dawn 0 … night 3)"),
    ("worldof-17-aorus-1.5b-more-s*.json", "verbose", "poem_words", "verbose − terse", "words in the poem"),
    ("worldof-17-aorus-1.5b-more-s*.json", "warmer", "warmth", "warm − cold", "sky warmth (blue −1 … red +1)"),
]


def measure(w, kind):
    if kind in READERS and kind != "count":
        return READERS[kind](w)
    ks = kinds_of(w)
    return min(6, len(ks) if kind is None else sum(1 for k in ks if k == kind))   # the page's own cap


def series(files, name, kind, lo=None):
    pts = {"real": {}, "placebo": {}, "base": {}}
    for f in files:
        d = json.loads(pathlib.Path(f).read_text())
        st = float(d["params"]["strength"])
        if lo is not None and st < lo:
            continue
        for r in d["runs"]:
            if not r.get("world"):
                continue
            v = measure(r["world"], kind)
            if v is None:
                continue
            if r["kind"] == "base":
                pts["base"].setdefault(0.0, []).append(v)
            elif r["name"] == name and r["kind"] in ("real", "placebo"):
                pts[r["kind"]].setdefault(st, []).append(v)
    return pts


def panel(ax, pts, title, ylabel):
    curves(ax, pts, title, ylabel)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="comma list of direction names to draw, one panel each")
    ap.add_argument("--out", default=None)
    ap.add_argument("--title", default="The sliders")
    ap.add_argument("--from", dest="lo", default=None, help="leave out strengths below this: a number, or name:number,name:number")
    a = ap.parse_args()
    fonts()
    live = [(g, n, k, t, y) for g, n, k, t, y in PANELS if glob.glob(str(HERE / "docs" / "runs" / g))]
    if a.only:
        keep = a.only.split(",")
        live = [x for x in live if x[1] in keep]
    cols = min(3, len(live)) or 1
    rows = (len(live) + cols - 1) // cols
    size = (7.5, 4.8) if len(live) == 1 else ((12.5, 4.8) if len(live) == 2 else (4.6 * cols, 3.9 * rows + 0.3))
    fig, axes = plt.subplots(rows, cols, figsize=size, facecolor=SURF)
    axes = list(axes.flat) if hasattr(axes, "flat") else [axes]
    for ax, (g, n, k, t, y) in zip(axes, live):
        lo = None
        if a.lo:
            los = {x.split(":")[0]: float(x.split(":")[1]) for x in a.lo.split(",") if ":" in x}
            lo = los.get(n, float(a.lo) if ":" not in a.lo else None)
        panel(ax, series(sorted(glob.glob(str(HERE / "docs" / "runs" / g))), n, k, lo), t, y)
    for ax in axes[len(live):]:
        ax.axis("off")
    fig.tight_layout(h_pad=1.6, w_pad=2.4)
    out = pathlib.Path(a.out) if a.out else HERE / "docs" / "worldof-sliders.png"
    fig.savefig(out, dpi=170, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
