"""All the knobs: for each count direction, the number of that thing drawn
per world against the strength; for the brightness direction, the sky's
mean luminance. Real vector as a line, the shuffled vector in grey, the
unsteered worlds at zero.

    python fig/plot_knobs.py            # trees + crowded (worldof-13), six kinds (worldof-14), darker (worldof-15)
"""
import glob
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

HERE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(HERE))
from steeropathy.secondhand import kinds_of, lum  # noqa: E402

VEC, ROTC, INK, INK2, GRID, SURF = "#eb6834", "#a09e99", "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"
PANELS = [  # (glob, direction, kind or None, title, y label)
    ("worldof-13-aorus-1.5b-knob-s*.json", "manytrees", "tree", "many trees − one tree", "trees per world"),
    ("worldof-13-aorus-1.5b-knob-s*.json", "crowded", None, "crowded − empty", "things per world"),
    ("worldof-14-aorus-1.5b-knob2-s*.json", "manybirds", "bird", "many birds − one bird", "birds per world"),
    ("worldof-14-aorus-1.5b-knob2-s*.json", "manyhouses", "house", "many houses − one house", "houses per world"),
    ("worldof-14-aorus-1.5b-knob2-s*.json", "manystars", "star", "many stars − one star", "stars per world"),
    ("worldof-14-aorus-1.5b-knob2-s*.json", "manycats", "cat", "many cats − one cat", "cats per world"),
    ("worldof-14-aorus-1.5b-knob2-s*.json", "manyflowers", "flower", "many flowers − one flower", "flowers per world"),
    ("worldof-14-aorus-1.5b-knob2-s*.json", "manyboats", "boat", "many boats − one boat", "boats per world"),
    ("worldof-15-aorus-1.5b-dark-s*.json", "darker", "LUM", "dark − bright", "sky luminance (0 black, 1 white)"),
]


def measure(w, kind):
    if kind == "LUM":
        ls = [lum(c) for c in (w.get("sky") or []) if isinstance(c, str)]
        ls = [x for x in ls if x is not None]
        return sum(ls) / len(ls) if ls else None
    ks = kinds_of(w)
    return min(6, len(ks) if kind is None else sum(1 for k in ks if k == kind))   # the page's own cap


def series(files, name, kind):
    pts = {"real": {}, "placebo": {}, "base": {}}
    for f in files:
        d = json.loads(pathlib.Path(f).read_text())
        st = float(d["params"]["strength"])
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


def mean_se(v):
    m = sum(v) / len(v)
    sd = (sum((x - m) ** 2 for x in v) / max(1, len(v) - 1)) ** 0.5
    return m, sd / len(v) ** 0.5


def panel(ax, pts, title, ylabel):
    for kind, color, label in (("placebo", ROTC, "the same vector, shuffled"), ("real", VEC, "the vector")):
        xs = sorted(pts[kind])
        if not xs:
            continue
        ms = [mean_se(pts[kind][x]) for x in xs]
        ax.errorbar(xs, [m for m, _ in ms], yerr=[s for _, s in ms], color=color, linewidth=2,
                    marker="o", markersize=5, markeredgecolor=SURF, capsize=3, label=label)
    if pts["base"]:
        m, s = mean_se(pts["base"][0.0])
        ax.errorbar([0], [m], yerr=[s], color=INK, marker="o", markersize=6, capsize=3, linestyle="none",
                    label="nothing added")
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    ax.set_ylabel(ylabel, color=INK2, fontsize=9)
    ax.set_xticks([-3, -1.5, 0, 1.5, 3])
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(length=0, colors=INK2, labelsize=9)
    ax.set_facecolor(SURF)


def main():
    font_manager.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    live = [(g, n, k, t, y) for g, n, k, t, y in PANELS if glob.glob(str(HERE / "docs" / "runs" / g))]
    cols = 3
    rows = (len(live) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(4.2 * cols, 3.4 * rows + 0.9), facecolor=SURF)
    axes = list(axes.flat) if hasattr(axes, "flat") else [axes]
    for ax, (g, n, k, t, y) in zip(axes, live):
        panel(ax, series(sorted(glob.glob(str(HERE / "docs" / "runs" / g))), n, k), t, y)
    for ax in axes[len(live):]:
        ax.axis("off")
    axes[0].legend(loc="upper left", frameon=False, fontsize=8.5, labelcolor=INK2)
    fig.suptitle("The knobs", x=0.02, ha="left", fontsize=15, color=INK, fontweight="bold", y=0.995)
    fig.text(0.02, 0.965, "Qwen2.5-1.5B, layer 16 ± 4. x: strength of one direction added to the residual stream; "
             "y: what the drawn world contains. Bars are standard errors. Negative strength pushes the other way.",
             color=INK2, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = HERE / "docs" / "worldof-knobs.png"
    fig.savefig(out, dpi=170, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
