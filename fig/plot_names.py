"""The sliders, named by the model: for each slider the nearest words on the
J-lens token map (orange) and the farthest (grey), from docs/runs/vocabmap-*.json.

    python fig/plot_names.py            # docs/story/names.png
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

ROWS = [("crowded", "crowded"), ("darker", "dark"), ("night", "likes night"), ("formal", "formal"), ("urgent", "urgent"),
        ("verbose", "verbose"), ("louder", "loud"), ("cheaper", "cheap"), ("warmer", "warm"), ("trees", "likes trees"),
        ("rain", "likes rain"), ("sad", "sad"), ("calm", "calm"), ("angry", "angry"), ("angry~moods", "angry − moods"),
        ("calm~moods", "calm − moods"), ("refusal", "refusal")]
CLEAN = {"brenda": None, "extingu": "extinguish", "commande": "commander", "negot": "negotiate", "melanch": "melancholy",
         "leben": None, "sui": None, "sak": None, "tranqu": "tranquil", "orch": "orchid", "mel": None, "bloss": "blossom",
         "retali": "retaliation", "plaint": "complaint", "nit": None, "gast": None, "ord": None, "widget": None}


def clean(words, n):
    out = []
    for w in words:
        w = CLEAN.get(w, w)
        if w and w not in out:
            out.append(w)
        if len(out) == n:
            break
    return out


def main():
    d = json.loads((HERE / "docs" / "runs" / "vocabmap-qwen3-4b.json").read_text())
    fonts(11)
    fig, ax = plt.subplots(figsize=(10.5, 0.46 * len(ROWS) + 1.2), facecolor=SURF)
    ax.set_facecolor(SURF)
    for i, (key, label) in enumerate(ROWS):
        y = len(ROWS) - 1 - i
        v = d["sliders"][key]
        near = clean([w for w, _ in v["nearest"]], 4)
        far = clean([w for w, _ in v["farthest"]], 3)
        if key == "refusal":
            near, far = ["(nothing coherent, cosines under 0.10)"], []
        ax.text(0, y, label, ha="right", va="center", fontsize=11.5, color=INK, fontweight="semibold")
        ax.text(0.35, y, ", ".join(near), ha="left", va="center", fontsize=11, color=VEC)
        ax.text(6.4, y, ", ".join(far), ha="left", va="center", fontsize=10.5, color=INK2)
        ax.plot([0.2, 9.6], [y - 0.5, y - 0.5], color=GRID, lw=0.8)
    ax.text(0.35, len(ROWS) + 0.05, "nearest words", color=VEC, fontsize=10.5, fontweight="semibold", va="bottom")
    ax.text(6.4, len(ROWS) + 0.05, "farthest words", color=INK2, fontsize=10.5, fontweight="semibold", va="bottom")
    ax.set_xlim(-2.4, 9.7)
    ax.set_ylim(-0.7, len(ROWS) + 0.6)
    ax.axis("off")
    fig.tight_layout()
    out = HERE / "docs" / "story" / "names.png"
    fig.savefig(out, dpi=170, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
