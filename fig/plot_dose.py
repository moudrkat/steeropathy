"""Dose and layer: what the vector channel carries on the 1.5B as the
strength grows (left) and as the band moves through the stack (right).
Lines are agreement with A's world on the moved fields; the dotted line is
the parse rate (a broken form is a miss). The poem's numbers, which do not
depend on either knob, sit as grey ticks at the right edge.

    python fig/plot_dose.py
"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

HERE = pathlib.Path(__file__).parent.parent
RUNS = HERE / "docs" / "runs"
POOLED = RUNS / "secondhand-1.5b-pooled.json"        # strength 3, layer 16, 60 wishes
DOSE = {s: RUNS / f"secondhand-09-aorus-1.5b-dose-{s}.json" for s in (1, 2, 4, 5)}
LAYER = {l: RUNS / f"secondhand-10-aorus-1.5b-layer-{l}.json" for l in (6, 10, 22)}
FIELDS = ["time", "weather", "ground", "motion", "font", "things"]
# one hue per field, fixed order (categorical), plus ink for the parse rate
COLORS = {"time": "#2a78d6", "weather": "#eb6834", "ground": "#8a6d3b",
          "motion": "#2f9e7a", "font": "#8d5bd6", "things": "#d6469a"}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"


def point(path):
    if not path.exists():
        return None
    d = json.loads(path.read_text())
    if not d.get("complete", True) and "merged" not in d:
        return None
    t = d["table"]
    v = t.get("vector") or {}
    return {"fields": {k: v["fields"].get(f"m:{k}") for k in FIELDS},
            "parse": v.get("parse_rate"),
            "text": {k: (t.get("text") or {}).get("fields", {}).get(f"m:{k}") for k in FIELDS},
            "n": v.get("n")}


def panel(ax, xs, pts, xlabel, ref):
    for k in FIELDS:
        ys = [p["fields"][k] if p else None for p in pts]
        ax.plot([x for x, y in zip(xs, ys) if y is not None],
                [y for y in ys if y is not None], color=COLORS[k], linewidth=2,
                marker="o", markersize=6, markeredgecolor=SURF, markeredgewidth=1.2, label=k)
        if ref and ref["text"].get(k) is not None:
            ax.plot([xs[-1] + 0.6 * (xs[1] - xs[0])], [ref["text"][k]], marker="_",
                    markersize=14, markeredgewidth=2.2, color=COLORS[k], alpha=0.45)
    ps = [p["parse"] if p else None for p in pts]
    ax.plot([x for x, y in zip(xs, ps) if y is not None], [y for y in ps if y is not None],
            color=INK2, linewidth=1.6, linestyle=(0, (2, 2)), marker="o", markersize=4,
            label="form parsed")
    for x, p in zip(xs, pts):
        if p:
            ax.text(x, 1.03, f"n={p['n']}", ha="center", va="bottom", color=INK2, fontsize=8.5)
    ax.set_xticks(xs)
    ax.set_xlabel(xlabel, color=INK2)
    ax.set_ylim(-0.02, 1.12)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(length=0, colors=INK2)
    ax.set_facecolor(SURF)


def main():
    font_manager.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.8), facecolor=SURF, sharey=True)
    pooled = point(POOLED)
    xs = [1, 2, 3, 4, 5]
    pts = [point(DOSE[1]), point(DOSE[2]), pooled, point(DOSE[4]), point(DOSE[5])]
    panel(a1, xs, pts, "strength (layer 16 ± 4)", pooled)
    a1.set_title("the dose", loc="left", color=INK, fontsize=12)
    xs2 = [6, 10, 16, 22]
    pts2 = [point(LAYER[6]), point(LAYER[10]), pooled, point(LAYER[22])]
    panel(a2, xs2, pts2, "layer (strength 3, ± 4)", pooled)
    a2.set_title("the layer", loc="left", color=INK, fontsize=12)
    if pts2[0] is None:
        a2.text(6, 0.5, "layer 6:\nthe form\nbreaks", ha="center", va="center", color=INK2, fontsize=9)
    a1.set_ylabel("agreement with A, moved fields, vector", color=INK2)
    a2.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False, fontsize=9.5,
              labelcolor=INK2)
    fig.suptitle("What the dose and the layer do", x=0.02, ha="left", fontsize=15,
                 color=INK, fontweight="bold", y=0.985)
    fig.text(0.02, 0.905, "Qwen2.5-1.5B, seed 1, 12 wishes per point (60 at the shared point). "
             "Faint ticks at the right edge: the poem, which does not depend on either knob.",
             color=INK2, fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    out = HERE / "docs" / "secondhand-dose.png"
    fig.savefig(out, dpi=170, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
