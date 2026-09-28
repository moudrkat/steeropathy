"""The card sliders as curves: for each direction, the reading it was built
for against the strength. The vector as a line with a one-standard-error
band, the shuffled vector in grey, the unsteered cards at zero. Price is the
median (one card at thirty million would own the mean).

    python fig/plot_cardof.py                      # docs/runs/cardof-01-aorus-1.5b-s*.json → docs/cardof-sliders.png
    python fig/plot_cardof.py --only cheaper,manyfeatures --out docs/story/card-sliders.png
    python fig/plot_cardof.py --bench replyof      # the assistant's reply: tasks, urgency, words, tone
"""
import glob
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "fig"))
from style import SURF, curves, fonts, mean_se, median_iqr  # noqa: E402
from steeropathy import cardof, replyof  # noqa: E402
PANELS = [  # direction, reading, panel label, y label, median?
    ("cheaper", "price", "a bargain − a luxury", "price (median)", True),
    ("manyfeatures", "features", "a long list − a single line", "features per card", False),
    ("louder", "bangs", "shouting − quiet", "exclamation marks per card", False),
    ("formal", "words", "formal − casual", "words per card", False),
    ("darker", "dark", "dark − bright", "theme darkness (0 white, 1 black)", False),
]
BENCH = {
    "cardof": dict(panels=PANELS, key="card", read=cardof.read, glob="cardof-01-aorus-1.5b-s*.json", out="cardof-sliders.png"),
    "replyof": dict(panels=[
        ("offers", "tasks", "here is what to do − take your time", "tasks offered per reply", False),
        ("verbose", "words", "verbose − terse", "words per reply", False),
        ("formal", "bangs", "formal − casual", "exclamation marks per reply", False),
        ("offers", "buttons", "here is what to do − take your time", "buttons per reply", False),
        ("urgent", "urgency", "now − whenever", "urgency the reply sets itself (1 to 5)", False),
    ], key="reply", read=replyof.read, glob="replyof-01-aorus-1.5b-s*.json", out="replyof-sliders.png"),
}


def series(files, name, what, key="card", read=cardof.read):
    pts = {"real": {}, "placebo": {}, "base": {}}
    for f in files:
        d = json.loads(pathlib.Path(f).read_text())
        st = float(d["params"]["strength"])
        for r in d["runs"]:
            c = r.get(key)
            if not c:
                continue
            v = read(c, what)
            if v is None:
                continue
            if r["kind"] == "base":
                pts["base"].setdefault(0.0, []).append(v)
            elif r["name"] == name and r["kind"] in ("real", "placebo"):
                pts[r["kind"]].setdefault(st, []).append(v)
    return pts


def panel(ax, pts, label, ylabel, median):
    if median:
        curves(ax, pts, label, ylabel, centre=median_iqr, log=True, ylim=(8, 2500), yticks=[10, 30, 100, 300, 1000])
    else:
        curves(ax, pts, label, ylabel, centre=mean_se)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="cardof", choices=sorted(BENCH))
    ap.add_argument("--glob", default=None)
    ap.add_argument("--only", default=None, help="comma list of directions, one panel each")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    bench = BENCH[a.bench]
    fonts()
    files = sorted(glob.glob(str(HERE / "docs" / "runs" / (a.glob or bench["glob"]))))
    keep = a.only.split(",") if a.only else None      # names, or name:reading
    live = bench["panels"] if not keep else [p for p in bench["panels"] if p[0] in keep or f"{p[0]}:{p[1]}" in keep]
    cols = min(3, len(live)) or 1
    rows = (len(live) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(4.6 * cols, 4.1 * rows), facecolor=SURF)
    axes = list(axes.flat) if hasattr(axes, "flat") else [axes]
    for ax, (name, what, label, ylabel, median) in zip(axes, live):
        panel(ax, series(files, name, what, bench["key"], bench["read"]), label, ylabel, median)
    for ax in axes[len(live):]:
        ax.axis("off")
    fig.tight_layout(h_pad=1.6, w_pad=2.4)
    out = pathlib.Path(a.out) if a.out else HERE / "docs" / bench["out"]
    fig.savefig(out, dpi=170, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
