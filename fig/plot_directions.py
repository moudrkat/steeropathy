"""The anatomy of the sliders: every direction built from the served model,
and the cosine between each pair. Sliders that are secretly one slider sit
near 1; sliders that add cleanly sit near 0.

    python fig/plot_directions.py --url http://localhost:8013 [names…]
    -> docs/runs/directions-<model>.json, docs/directions-cos.png
"""
import argparse
import json
import math
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

HERE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(HERE))
from steeropathy.transmit import default_layer  # noqa: E402
from steeropathy.worldof import direction_for  # noqa: E402
from steeropathy.cardof import CARD_KNOBS  # noqa: E402
from steeropathy.replyof import REPLY_KNOBS  # noqa: E402
from steeropathy import worldof  # noqa: E402

DEFAULT = ["sad", "calm", "angry", "sad~moods", "calm~moods", "angry~moods", "refusal", "certain", "formal",
           "night", "trees", "rain", "snow", "sea", "manytrees", "crowded", "darker", "later", "verbose", "warmer",
           "louder", "cheaper", "manyfeatures", "offers", "urgent"]
INK, INK2, SURF = "#0b0b0b", "#52514e", "#fcfcfb"
CMAP = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#fcfcfb", "#eb6834"])


def cos(a, b):
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) or 1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=DEFAULT)
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--layer", type=int, default=None)
    ap.add_argument("--from", dest="src", default=None, help="a saved directions json instead of the server")
    ap.add_argument("--min", type=float, default=0.5, help="print the cosine where |cos| is at least this")
    a = ap.parse_args()
    if a.src:
        d = json.loads(pathlib.Path(a.src).read_text())
        vecs, model, layer = d["directions"], d["model"], d["layer"]
    else:
        layer = a.layer if a.layer is not None else default_layer(a.url)
        worldof.LIKES.update({k: v for k, v in CARD_KNOBS.items()})
        worldof.LIKES.update({k: v for k, v in REPLY_KNOBS.items()})
        vecs = {}
        for n in a.names:
            v, _, src = direction_for(a.url, n, layer)
            vecs[n] = v
            print(f"{n:14s} {src}")
        import urllib.request
        model = json.loads(urllib.request.urlopen(a.url + "/info", timeout=30).read()).get("model", "")
        tag = model.split("/")[-1].lower()
        (HERE / "docs" / "runs" / f"directions-{tag}.json").write_text(json.dumps(
            {"model": model, "layer": layer, "directions": vecs}, ensure_ascii=False))
    # groups, in reading order; a thin gap between them
    GROUPS = [("moods", ["sad", "calm", "angry"]),
              ("minus what they share", ["sad~moods", "calm~moods", "angry~moods"]),
              ("registers", ["refusal", "certain", "formal", "offers", "urgent"]),
              ("things to like", ["night", "trees", "rain", "snow", "sea"]),
              ("sliders", ["crowded", "manytrees", "darker", "later", "verbose", "warmer", "louder", "cheaper", "manyfeatures"])]
    names = [n for _, g in GROUPS for n in g if n in vecs] + [n for n in vecs if n not in {x for _, g in GROUPS for x in g}]
    labels = {"sad~moods": "sad − moods", "calm~moods": "calm − moods", "angry~moods": "angry − moods",
              "manytrees": "many trees", "manyfeatures": "many features", "darker": "dark", "louder": "loud",
              "cheaper": "cheap", "warmer": "warm", "later": "late", "night": "likes night", "trees": "likes trees",
              "rain": "likes rain", "snow": "likes snow", "sea": "likes sea"}
    M = [[cos(vecs[x], vecs[y]) for y in names] for x in names]
    font_manager.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    n = len(names)
    fig, ax = plt.subplots(figsize=(0.46 * n + 2.6, 0.46 * n + 1.4), facecolor=SURF)
    im = ax.imshow(M, cmap=CMAP, vmin=-1, vmax=1)
    shown = [labels.get(x, x) for x in names]
    ax.set_xticks(range(n), shown, rotation=55, ha="right", fontsize=10)
    ax.set_yticks(range(n), shown, fontsize=10)
    for i in range(n):
        for j in range(n):
            if i != j and abs(M[i][j]) >= a.min:
                ax.text(j, i, f"{M[i][j]:+.1f}".replace("+0.", "+.").replace("-0.", "−."), ha="center", va="center",
                        fontsize=8, color=SURF if abs(M[i][j]) > 0.6 else INK)
    # white gaps between the groups
    pos = 0
    for _, g in GROUPS[:-1]:
        pos += sum(1 for x in g if x in vecs)
        ax.axhline(pos - 0.5, color=SURF, linewidth=3)
        ax.axvline(pos - 0.5, color=SURF, linewidth=3)
    # group names along the top
    pos = 0
    for gname, g in GROUPS:
        k = sum(1 for x in g if x in vecs)
        if k:
            ax.text(pos + k / 2 - 0.5, -1.0, gname, ha="center", va="bottom", fontsize=9.5, color=INK2)
            pos += k
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    cb = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02, ticks=[-1, -0.5, 0, 0.5, 1])
    cb.set_label("cosine: +1 the same direction, 0 unrelated, −1 opposite", color=INK2)
    cb.outline.set_visible(False)
    fig.tight_layout()
    out = HERE / "docs" / "directions-cos.png"
    fig.savefig(out, dpi=170, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
