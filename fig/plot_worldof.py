"""The moods as numbers: per direction, the share of worlds that left the
unsteered mode on each field, and where they went. Each direction has a
placebo row under it (the same vector, coordinates shuffled): a field the
placebo moves as often is the dose, not the direction.

    python fig/plot_worldof.py [worldof-run.json]
"""
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

HERE = pathlib.Path(__file__).parent.parent
DEFAULT = HERE / "docs" / "runs" / "worldof-03-aorus-1.5b-n12.json"
FIELDS = ["time", "weather", "ground", "motion", "font"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"
RAMP = LinearSegmentedColormap.from_list("blue", ["#fcfcfb", "#c9dcf5", "#7fb0ea", "#2a78d6", "#123f7a"])


def main():
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    d = json.loads(path.read_text())
    summ = d["summary"]
    base = summ["base"]
    rows = [k for k in summ if k != "base"]
    font_manager.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    cols = FIELDS + ["things", "dark"]
    fig, ax = plt.subplots(figsize=(1.9 * len(cols) + 2.6, 0.5 * len(rows) + 2.2), facecolor=SURF)
    ax.set_facecolor(SURF)
    for i, r in enumerate(rows):
        y = len(rows) - 1 - i
        placebo = r.endswith("(placebo)")
        s = summ[r]
        for j, k in enumerate(cols):
            if k in FIELDS:
                f = s["fields"][k]
                val = f["moved"]
                label = (f"{f['to']} {f['to_n']}/{f['n']}" + (" ·ex" if f.get("to_is_example") else "")
                         if val else "–") if val is not None else "n/a"
            elif k == "things":
                val = None
                label = f"{s['things'][0]} ×{s['things'][1]}"
            else:
                val = None if s.get("dark_vs_base") is None else 1 - s["dark_vs_base"]
                label = f"{s['dark_vs_base']:.2f}" if s.get("dark_vs_base") is not None else "n/a"
            if val is not None:
                ax.add_patch(plt.Rectangle((j, y), 0.96, 0.92, facecolor=RAMP(float(min(1.0, val))),
                                           linewidth=0))
                ink = SURF if val > 0.6 else INK
            else:
                ink = INK2
            ax.text(j + 0.48, y + 0.46, label, ha="center", va="center", fontsize=9.2,
                    color=ink, style="italic" if placebo else "normal")
        ax.text(-0.15, y + 0.46, r.replace(" (placebo)", "  · shuffled"), ha="right",
                va="center", fontsize=10.5 if not placebo else 9.5,
                color=INK2 if placebo else INK, style="italic" if placebo else "normal")
        ax.text(len(cols) + 0.15, y + 0.46, f"parsed {s['parse_rate']:.2f}", ha="left",
                va="center", fontsize=8.5, color=INK2)
    for j, k in enumerate(cols):
        head = k if k != "dark" else "darkness ≈ base"
        ax.text(j + 0.48, len(rows) + 0.25, head, ha="center", va="bottom", fontsize=10.5, color=INK)
        if k in FIELDS:
            ax.text(j + 0.48, len(rows) + 0.02, f"unsteered: {base['mode'][k]}", ha="center",
                    va="bottom", fontsize=8.5, color=INK2)
        elif k == "things":
            ax.text(j + 0.48, len(rows) + 0.02, f"unsteered: {base['things'][0]} ×{base['things'][1]}",
                    ha="center", va="bottom", fontsize=8.5, color=INK2)
    ax.set_xlim(-1.9, len(cols) + 1.2)
    ax.set_ylim(-0.1, len(rows) + 1.0)
    ax.axis("off")
    fig.suptitle("What a vector looks like, counted", x=0.02, ha="left", fontsize=15,
                 color=INK, fontweight="bold", y=0.985)
    fig.text(0.02, 0.905, f"{d.get('model', '')} · strength {d['params']['strength']} · layer {d['layer']} · "
             f"{base['n']} unsteered worlds, {summ[rows[0]]['n']} per direction. Cell: share of worlds that "
             "left the unsteered mode, and the value they went to most (·ex = the worked example's value).\n"
             "The shuffled row under each direction is the same vector with its coordinates permuted: what the dose alone does.",
             color=INK2, fontsize=9.5, va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    out = HERE / "docs" / "worldof-counted.png"
    fig.savefig(out, dpi=170, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
