"""The slider: how many trees (and how many things) the model draws as the
strength of a count direction goes from -3 to +3. Real vector as a line,
the shuffled vector in grey, the unsteered worlds at zero.

    python fig/plot_knob.py [docs/runs/worldof-13-aorus-1.5b-knob-s*.json]
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
from steeropathy.secondhand import kinds_of  # noqa: E402

VEC, ROTC, INK, INK2, GRID, SURF = "#eb6834", "#a09e99", "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"


def count(w, kind):
    ks = kinds_of(w)
    return min(6, len(ks) if kind is None else sum(1 for k in ks if k == kind))


def series(files, name, kind):
    pts = {"real": {}, "placebo": {}, "base": {}}
    for f in files:
        d = json.loads(pathlib.Path(f).read_text())
        st = float(d["params"]["strength"])
        for r in d["runs"]:
            if not r.get("world"):
                continue
            if r["kind"] == "base":
                pts["base"].setdefault(0.0, []).append(count(r["world"], kind))
            elif r["name"] == name and r["kind"] in ("real", "placebo"):
                pts[r["kind"]].setdefault(st, []).append(count(r["world"], kind))
    return pts


def mean_sd(v):
    m = sum(v) / len(v)
    sd = (sum((x - m) ** 2 for x in v) / max(1, len(v) - 1)) ** 0.5
    return m, sd / len(v) ** 0.5


def panel(ax, pts, title, ylabel):
    for kind, color, label in (("placebo", ROTC, "the same vector, shuffled"), ("real", VEC, "the vector")):
        xs = sorted(pts[kind])
        if not xs:
            continue
        ms = [mean_sd(pts[kind][x]) for x in xs]
        ax.errorbar(xs, [m for m, _ in ms], yerr=[s for _, s in ms], color=color, linewidth=2,
                    marker="o", markersize=6, markeredgecolor=SURF, capsize=3, label=label)
    if pts["base"]:
        m, s = mean_sd(pts["base"][0.0])
        ax.errorbar([0], [m], yerr=[s], color=INK, marker="o", markersize=7, capsize=3, linestyle="none",
                    label=f"nothing added (n={len(pts['base'][0.0])})")
    ax.set_title(title, loc="left", color=INK, fontsize=12)
    ax.set_xlabel("strength", color=INK2)
    ax.set_ylabel(ylabel, color=INK2)
    ax.set_xticks([-3, -2, -1, 0, 1, 2, 3])
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(length=0, colors=INK2)
    ax.set_facecolor(SURF)


def main():
    files = sys.argv[1:] or sorted(glob.glob(str(HERE / "docs" / "runs" / "worldof-13-aorus-1.5b-knob-s*.json")))
    font_manager.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6), facecolor=SURF)
    panel(a1, series(files, "manytrees", "tree"), "many trees minus one tree", "trees drawn per world")
    panel(a2, series(files, "crowded", None), "crowded minus empty", "things drawn per world")
    a2.legend(loc="upper left", frameon=False, fontsize=9.5, labelcolor=INK2)
    fig.suptitle("The slider", x=0.02, ha="left", fontsize=15, color=INK, fontweight="bold", y=0.985)
    fig.text(0.02, 0.905, "Qwen2.5-1.5B, layer 16 ± 4. Eight worlds per point; the bar is the standard error. "
             "Negative strength pushes the other way.", color=INK2, fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    out = HERE / "docs" / "worldof-slider.png"
    fig.savefig(out, dpi=170, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
