"""What never became text: per model and field, the items where only the
vector carried A's choice (right, orange) against the items where only the
poem did (left, blue). Both counted where A left B's own world, so B's own
taste cancels. The number the thesis is about is the difference.

    python fig/plot_residue.py [run.json ...]     # default: the three runs
"""
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

HERE = pathlib.Path(__file__).parent.parent
DEFAULT = [("Qwen2.5-0.5B", "secondhand-03-aorus-0.5b.json"),
           ("Qwen2.5-1.5B", "secondhand-04-aorus-1.5b-onestep.json"),
           ("Qwen3-4B", "secondhand-02-aorus-4b.json")]
FIELDS = ["time", "weather", "ground", "motion", "things", "ghost"]
TEXT, VEC = "#2a78d6", "#eb6834"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"


def main():
    runs = DEFAULT
    if len(sys.argv) > 1:
        runs = [(pathlib.Path(a).stem, a) for a in sys.argv[1:]]
    font_manager.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, axes = plt.subplots(1, len(runs), figsize=(4.4 * len(runs) + 0.6, 4.4),
                             sharey=True, facecolor=SURF)
    axes = list(axes) if len(runs) > 1 else [axes]
    for ax, (title, fn) in zip(axes, runs):
        path = pathlib.Path(fn) if pathlib.Path(fn).exists() else HERE / "docs" / "runs" / fn
        d = json.loads(path.read_text())
        res = d.get("residue") or {}
        ys = list(range(len(FIELDS)))[::-1]
        ax.set_facecolor(SURF)
        ax.axvline(0, color=INK2, linewidth=1)
        for y, k in zip(ys, FIELDS):
            r = res.get(k)
            if not r or not r["n"]:
                ax.text(0.15, y, "n/a", va="center", color=INK2, fontsize=9)
                continue
            t, v, n = r["text_only"], r["vector_only"], r["n"]
            ax.barh(y, -t, 0.62, color=TEXT, linewidth=0)
            ax.barh(y, v, 0.62, color=VEC, linewidth=0)
            if t:
                ax.text(-t - 0.15, y, str(t), va="center", ha="right", color=INK, fontsize=10)
            if v:
                ax.text(v + 0.15, y, str(v), va="center", ha="left", color=INK, fontsize=10)
            ax.text(7.9, y, f"n={n}", va="center", ha="right", color=INK2, fontsize=9)
        ax.set_yticks(ys, FIELDS)
        ax.set_xlim(-8, 8)
        ax.set_xticks([-6, -3, 0, 3, 6], ["", "3", "0", "3", ""])
        ax.grid(axis="x", color=GRID, linewidth=1)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(axis="both", length=0, colors=INK2)
        ax.set_title(title, loc="left", fontsize=12, color=INK, pad=8)
        ax.text(-0.4, len(FIELDS) - 0.35, "only the poem", color=TEXT, fontsize=9.5, ha="right")
        ax.text(0.4, len(FIELDS) - 0.35, "only the vector", color=VEC, fontsize=9.5, ha="left")
        ax.set_ylim(-0.6, len(FIELDS) - 0.0)
    fig.suptitle("What never became text", x=0.02, ha="left", fontsize=15,
                 color=INK, fontweight="bold", y=0.995)
    fig.text(0.02, 0.93, "items where only A's activations carried the field to B (right), or only A's own poem did (left); "
             "both counted where A left B's own world. ghost = a thing A almost placed.",
             color=INK2, fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = HERE / "docs" / "secondhand-residue.png"
    fig.savefig(out, dpi=170, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
