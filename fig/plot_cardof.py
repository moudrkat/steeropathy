"""The card sliders as curves: for each direction, the reading it was built
for against the strength. The vector as a line with a one-standard-error
band, the shuffled vector in grey, the unsteered cards at zero. Price is the
median (one card at thirty million would own the mean).

    python fig/plot_cardof.py                      # docs/runs/cardof-01-aorus-1.5b-s*.json → docs/cardof-sliders.png
    python fig/plot_cardof.py --only cheaper,manyfeatures --out docs/story/card-sliders.png
"""
import glob
import json
import pathlib
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

HERE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(HERE))
from steeropathy.cardof import read  # noqa: E402

VEC, ROTC, INK, INK2, GRID, SURF = "#eb6834", "#a09e99", "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"
PANELS = [  # direction, reading, panel label, y label, median?
    ("cheaper", "price", "a bargain − a luxury", "price (median)", True),
    ("manyfeatures", "features", "a long list − a single line", "features per card", False),
    ("louder", "bangs", "shouting − quiet", "exclamation marks per card", False),
    ("formal", "words", "formal − casual", "words per card", False),
    ("darker", "dark", "dark − bright", "theme darkness (0 white, 1 black)", False),
]


def series(files, name, what):
    pts = {"real": {}, "placebo": {}, "base": {}}
    for f in files:
        d = json.loads(pathlib.Path(f).read_text())
        st = float(d["params"]["strength"])
        for r in d["runs"]:
            c = r.get("card")
            if not c:
                continue
            v = read(c, what)
            if v is None:
                continue
            if r["kind"] == "base":
                pts["base"].setdefault(0.0, []).append(v)
            elif r["name"] == name and r["kind"] in ("real", "placebo"):
                pts[r["kind"]].setdefault(st, []).append(v)
    return pts


def centre(v, median):
    if median:
        m = statistics.median(v)
        s = sorted(v)
        lo, hi = s[len(s) // 4], s[(3 * len(s)) // 4]     # the middle half
        return m, m - lo, hi - m
    m = sum(v) / len(v)
    sd = (sum((x - m) ** 2 for x in v) / max(1, len(v) - 1)) ** 0.5
    se = sd / len(v) ** 0.5
    return m, se, se


def panel(ax, pts, label, ylabel, median):
    for kind, color, lab, z in (("placebo", ROTC, "the same vector, shuffled", 2), ("real", VEC, "the vector", 3)):
        xs = sorted(pts[kind])
        if not xs:
            continue
        cs = [centre(pts[kind][x], median) for x in xs]
        ax.fill_between(xs, [m - lo for m, lo, _ in cs], [m + hi for m, _, hi in cs], color=color, alpha=0.16,
                        linewidth=0, zorder=z)
        ax.plot(xs, [m for m, _, _ in cs], color=color, linewidth=3, marker="o", markersize=8,
                markeredgecolor=SURF, markeredgewidth=1.5, label=lab, zorder=z + 1, solid_capstyle="round")
    if pts["base"]:
        m, _, _ = centre(pts["base"][0.0], median)
        ax.plot([0], [m], color=INK, marker="o", markersize=9, markeredgecolor=SURF, markeredgewidth=1.5,
                linestyle="none", label="nothing added", zorder=6)
    if median:
        ax.set_yscale("log")
        ax.set_ylim(8, 2500)     # the middle half of the cards; one card at −2 asks thirty million
        ax.set_yticks([10, 30, 100, 300, 1000], ["10", "30", "100", "300", "1000"])
        ax.minorticks_off()
    ax.set_title(label, loc="left", color=INK, fontsize=11)
    ax.set_ylabel(ylabel, color=INK2, fontsize=9)
    ax.set_xlabel("strength of the vector (negative pushes the other way)", color=INK2, fontsize=9.5)
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
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="cardof-01-aorus-1.5b-s*.json")
    ap.add_argument("--only", default=None, help="comma list of directions, one panel each")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    font_manager.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    files = sorted(glob.glob(str(HERE / "docs" / "runs" / a.glob)))
    live = PANELS if not a.only else [p for p in PANELS if p[0] in a.only.split(",")]
    cols = min(3, len(live)) or 1
    rows = (len(live) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(4.4 * cols, 3.9 * rows), facecolor=SURF)
    axes = list(axes.flat) if hasattr(axes, "flat") else [axes]
    for ax, (name, what, label, ylabel, median) in zip(axes, live):
        panel(ax, series(files, name, what), label, ylabel, median)
    for ax in axes[len(live):]:
        ax.axis("off")
    axes[0].legend(loc="best", frameon=False, fontsize=9, labelcolor=INK2)
    fig.tight_layout(h_pad=1.5, w_pad=1.5)
    out = pathlib.Path(a.out) if a.out else HERE / "docs" / "cardof-sliders.png"
    fig.savefig(out, dpi=170, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
