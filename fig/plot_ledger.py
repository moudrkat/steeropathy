"""The ledger, one panel: on the 1.5B over 60 wishes, the share of moved
items where only A's poem carried the field to B (left, blue) against the
share where only A's activations did (right, orange). The outline on the
right is the same vector with its coordinates shuffled (run 06, 12 wishes):
what the dose alone does. Both sides are read against B's own world, so
B's taste cancels.

    python fig/plot_ledger.py [pooled.json] [rot.json]
"""
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

HERE = pathlib.Path(__file__).parent.parent
POOLED = "secondhand-1.5b-pooled.json"
ROT = "secondhand-06-aorus-1.5b-rot.json"
FIELDS = ["time", "weather", "ground", "font", "things", "ghost", "motion"]
TEXT, VEC, ROTC = "#2a78d6", "#eb6834", "#a09e99"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"


def load(fn):
    p = pathlib.Path(fn) if pathlib.Path(fn).exists() else HERE / "docs" / "runs" / fn
    return json.loads(p.read_text()).get("residue") or {}


def main():
    pooled = load(sys.argv[1] if len(sys.argv) > 1 else POOLED)
    rot = load(sys.argv[2] if len(sys.argv) > 2 else ROT)
    font_manager.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12})
    fig, ax = plt.subplots(figsize=(9.6, 5.6), facecolor=SURF)
    ax.set_facecolor(SURF)
    ys = list(range(len(FIELDS)))[::-1]
    ax.axvline(0, color=INK2, linewidth=1, zorder=3)
    for y, k in zip(ys, FIELDS):
        r, c = pooled.get(k), rot.get(k)
        if not r or not r["n"]:
            continue
        t, v, n = r["text_only"] / r["n"], r["vector_only"] / r["n"], r["n"]
        ax.barh(y + 0.1, -t, 0.5, color=TEXT, linewidth=0, zorder=2)
        ax.barh(y + 0.1, v, 0.5, color=VEC, linewidth=0, zorder=2)
        ax.text(-t - 0.012, y + 0.1, f"{r['text_only']}", va="center", ha="right", color=INK, fontsize=11)
        ax.text(v + 0.012, y + 0.1, f"{r['vector_only']}", va="center", ha="left", color=INK, fontsize=11)
        if c and c["n"]:
            cv = c["vector_only"] / c["n"]
            ax.barh(y - 0.27, cv, 0.16, color=ROTC, linewidth=0, zorder=2)
            ax.text(max(cv, 0) + 0.012, y - 0.27, f"{c['vector_only']}", va="center",
                    ha="left", color=INK2, fontsize=8.5)
        ax.text(0.475, y + 0.1, f"n={n}", va="center", ha="right", color=INK2, fontsize=10)
    ax.set_yticks([y + 0.05 for y in ys], FIELDS)
    ax.set_xlim(-0.48, 0.48)
    ax.set_xticks([-0.4, -0.2, 0, 0.2, 0.4], ["40 %", "20 %", "0", "20 %", "40 %"])
    ax.grid(axis="x", color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="both", length=0, colors=INK2)
    ax.tick_params(axis="y", labelsize=12, labelcolor=INK)
    top = len(FIELDS) - 0.3
    ax.text(-0.02, top, "only A's poem carried it", color=TEXT, fontsize=11.5, ha="right", va="center")
    ax.text(0.02, top, "only A's activations carried it", color=VEC, fontsize=11.5, ha="left", va="center")
    ax.set_ylim(-1.15, len(FIELDS) + 0.2)
    # legend for the grey bar, drawn by hand so it reads as what it is
    lx, ly = -0.46, -0.85
    ax.add_patch(plt.Rectangle((lx, ly - 0.08), 0.04, 0.16, facecolor=ROTC, linewidth=0))
    ax.text(lx + 0.052, ly, "grey: the same vector with its coordinates shuffled (12 wishes), the dose alone",
            va="center", color=INK2, fontsize=10)
    fig.suptitle("What never became text", x=0.02, ha="left", fontsize=16,
                 color=INK, fontweight="bold", y=0.985)
    fig.text(0.02, 0.905, "Qwen2.5-1.5B, 60 wishes, 3 seeds. Share of the wishes where A left B's own world "
             "and exactly one channel carried A's choice.\nghost = a thing A almost placed and didn't. "
             "Count on the bar; the bars are read against B's own world, so B's taste cancels.",
             color=INK2, fontsize=10, va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    out = HERE / "docs" / "secondhand-ledger.png"
    fig.savefig(out, dpi=170, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
