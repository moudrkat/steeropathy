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
    a = ap.parse_args()
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
    names = list(vecs)
    M = [[cos(vecs[x], vecs[y]) for y in names] for x in names]
    font_manager.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    n = len(names)
    fig, ax = plt.subplots(figsize=(0.42 * n + 2.4, 0.42 * n + 2.0), facecolor=SURF)
    im = ax.imshow(M, cmap=CMAP, vmin=-1, vmax=1)
    ax.set_xticks(range(n), names, rotation=60, ha="right", fontsize=9)
    ax.set_yticks(range(n), names, fontsize=9)
    for i in range(n):
        for j in range(n):
            if i != j and abs(M[i][j]) >= 0.3:
                ax.text(j, i, f"{M[i][j]:.1f}", ha="center", va="center", fontsize=7,
                        color=SURF if abs(M[i][j]) > 0.6 else INK)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02).set_label("cosine", color=INK2)
    fig.suptitle("Which sliders are the same slider", x=0.02, ha="left", fontsize=15, color=INK, fontweight="bold", y=0.995)
    fig.text(0.02, 0.955, f"{model} · layer {layer} · cosine between the unit directions. Numbers shown where |cos| ≥ 0.3.",
             color=INK2, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = HERE / "docs" / "directions-cos.png"
    fig.savefig(out, dpi=170, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
