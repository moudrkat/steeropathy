"""Some sliders are the same slider: every direction as an arrow in the
plane of the first two principal axes of all of them (the amount axis and
the emotion axis, from fig/synth_directions.py). Arrows that lie on top of
each other are one slider with several names; arrows at right angles add.

    python fig/plot_arrows.py            # docs/story/same-slider.png
"""
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(HERE / "fig"))
from style import INK, INK2, GRID, SURF, VEC, fonts  # noqa: E402

FAMILY = {"sad": "moods", "calm": "moods", "angry": "moods",
          "crowded": "amount", "cheaper": "amount", "manyfeatures": "amount", "urgent": "amount", "louder": "amount",
          "trees": "amount", "darker": "amount", "night": "amount",
          "offers": "alone", "verbose": "alone", "later": "alone", "formal": "alone", "refusal": "alone", "warmer": "alone"}
COLOR = {"moods": "#2a78d6", "amount": VEC, "alone": "#3a9d5d"}
NUDGE = {"louder": (0.02, 0.0), "crowded": (0.0, -0.05)}
FAN = ("urgent", "cheaper", "manyfeatures", "trees")     # four arrows on top of each other: one label for all
LABEL = {"manyfeatures": "more features", "darker": "dark", "louder": "loud", "cheaper": "cheap", "trees": "likes trees",
         "night": "likes night", "warmer": "warm", "later": "late"}


def main():
    d = json.loads((HERE / "docs" / "runs" / "synth-qwen2.5-1.5b-instruct.json").read_text())
    fonts(11)
    fig, ax = plt.subplots(figsize=(8.6, 7.4), facecolor=SURF)
    ax.set_facecolor(SURF)
    ax.axhline(0, color=GRID, linewidth=1)
    ax.axvline(0, color=GRID, linewidth=1)
    for name, fam in FAMILY.items():
        if name not in d["loadings"]:
            continue
        x, y = d["loadings"][name]["pc1"], d["loadings"][name]["pc2"]
        c = COLOR[fam]
        ax.annotate("", xy=(x, y), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=c, lw=2.6, mutation_scale=16,
                                                                  shrinkA=0, shrinkB=0), zorder=3)
        if name in FAN:
            continue
        dx, dy = NUDGE.get(name, (0, 0))
        ax.text(x * 1.06 + (0.03 if x >= 0 else -0.03) + dx, y * 1.06 + dy, LABEL.get(name, name), color=c, fontsize=11,
                ha="left" if x >= 0 else "right", va="center", fontweight="semibold", zorder=4)
    fan = [(d["loadings"][n]["pc1"], d["loadings"][n]["pc2"]) for n in FAN if n in d["loadings"]]
    fx, fy = max(x for x, _ in fan), sum(y for _, y in fan) / len(fan)
    ax.text(fx + 0.05, fy + 0.04, "urgent, cheap, more features, likes trees:\none arrow with four names", color=VEC,
            fontsize=10.5, ha="left", va="center", fontweight="semibold", zorder=4)
    ax.set_xlim(-1.05, 1.45)
    ax.set_ylim(-0.9, 1.0)
    ax.set_aspect("equal")
    ax.text(1.12, 0.06, "more of everything →", color=VEC, fontsize=10.5, ha="right", va="bottom")
    ax.text(-1.0, 0.06, "← less, and dark", color=VEC, fontsize=10.5, ha="left", va="bottom")
    ax.text(0.03, 0.96, "emotional at all ↑", color="#2a78d6", fontsize=10.5, ha="left", va="top")
    ax.text(-1.0, -0.84, "blue: the moods · orange: the amount family · green: the ones that stand alone and add\n"
            "the plane of the two biggest axes of all the sliders; an arrow's length is how much of it lies in this plane",
            color=INK2, fontsize=9.5, ha="left", va="bottom")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    out = HERE / "docs" / "story" / "same-slider.png"
    fig.savefig(out, dpi=170, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
