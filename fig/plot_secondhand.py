"""The secondhand results chart: per model, agreement of B's world with A's on
the fields where A left B's own unsteered world (so "nothing" is zero by
construction), A's poem vs A's activations. Plus the ghost column: B placed a
thing A almost placed and didn't.

    python fig/plot_secondhand.py
"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

HERE = pathlib.Path(__file__).parent.parent
RUNS = [("Qwen2.5-0.5B · two-step", "secondhand-03-aorus-0.5b.json"),
        ("Qwen2.5-1.5B · in the JSON", "secondhand-04-aorus-1.5b-onestep.json"),
        ("Qwen3-4B · two-step", "secondhand-02-aorus-4b.json")]
FIELDS = [("m:time", "time"), ("m:weather", "weather"), ("m:ground", "ground"),
          ("m:motion", "motion"), ("m:things", "things"), ("ghost", "ghost")]
TEXT, VEC = "#2a78d6", "#eb6834"      # validated pair, reference palette slots 1–2
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"


def values(table, ch):
    d = table.get(ch) or {}
    out = []
    for key, _ in FIELDS:
        v = d.get("ghost_rate") if key == "ghost" else (d.get("fields") or {}).get(key)
        out.append(v)
    return out


def main():
    font_manager.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.6), sharey=True, facecolor=SURF)
    for ax, (title, fn) in zip(axes, RUNS):
        d = json.loads((HERE / "docs" / "runs" / fn).read_text())
        t, v = values(d["table"], "text"), values(d["table"], "vector")
        n = d["table"]["none"]["n"]
        xs = range(len(FIELDS))
        w = 0.36
        ax.set_facecolor(SURF)
        for i, (tv, vv) in enumerate(zip(t, v)):
            if tv is not None:
                ax.bar(i - w / 2 - 0.02, tv, w, color=TEXT, linewidth=0)
            if vv is not None:
                ax.bar(i + w / 2 + 0.02, vv, w, color=VEC, linewidth=0)
            if tv is None and vv is None:
                ax.text(i, 0.04, "n/a", ha="center", color=INK2, fontsize=9)
        ax.set_xticks(list(xs), [lab for _, lab in FIELDS])
        ax.set_ylim(0, 1)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0], ["0", "", "0.5", "", "1"])
        ax.grid(axis="y", color=GRID, linewidth=1)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(axis="both", length=0, colors=INK2)
        ax.set_title(f"{title}   ·   {n} wishes", loc="left", fontsize=12, color=INK, pad=10)
    axes[0].set_ylabel("agreement with A's world\n(only where A left B's own world)", color=INK2, fontsize=10)
    fig.suptitle("What crossed — the poem vs the activations", x=0.02, ha="left",
                 fontsize=15, color=INK, fontweight="bold", y=0.995)
    fig.text(0.02, 0.925, "“nothing” is 0 by construction here. ghost = B placed a thing A almost placed and didn't "
             "(needs logprobs; the 4B server had none).", color=INK2, fontsize=10)
    handles = [plt.Rectangle((0, 0), 1, 1, color=TEXT), plt.Rectangle((0, 0), 1, 1, color=VEC)]
    fig.legend(handles, ["A's poem (text)", "A's activations (vector)"], loc="upper right",
               bbox_to_anchor=(0.99, 0.995), frameon=False, ncol=2, fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    out = HERE / "docs" / "secondhand-fields.png"
    fig.savefig(out, dpi=170, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
