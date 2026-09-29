"""One look for the curve plots: Lato, a warm surface, the vector in orange
with a soft band, the shuffled vector in grey, the unsteered point in ink,
names at the ends of the lines instead of a legend.

    from style import fonts, curves
"""
import statistics

import matplotlib.pyplot as plt
from matplotlib import font_manager

VEC, ROTC, INK, INK2, GRID, SURF = "#eb6834", "#a8a6a1", "#141414", "#6b6964", "#ebeae6", "#fcfcfb"
LATO = "/usr/share/fonts/truetype/lato/Lato-{}.ttf"


def fonts(size=10.5):
    for w in ("Regular", "Medium", "Semibold", "Bold", "Italic"):
        try:
            font_manager.fontManager.addfont(LATO.format(w))
        except Exception:      # noqa: BLE001 - a missing weight is not a reason to stop
            pass
    plt.rcParams.update({"font.family": "Lato", "font.size": size, "axes.unicode_minus": True})


def mean_se(v):
    m = sum(v) / len(v)
    sd = (sum((x - m) ** 2 for x in v) / max(1, len(v) - 1)) ** 0.5
    se = sd / len(v) ** 0.5
    return m, se, se


def median_iqr(v):
    m = statistics.median(v)
    s = sorted(v)
    lo, hi = s[len(s) // 4], s[(3 * len(s)) // 4]
    return m, m - lo, hi - m


def _fmt(y):
    return f"{y:.0f}" if abs(y) >= 20 else (f"{y:.1f}" if abs(y) >= 1 else f"{y:.2f}")


def curves(ax, pts, title, ylabel, centre=mean_se, log=False, ylim=None, yticks=None, values=True):
    """pts: {"real": {x: [v]}, "placebo": {x: [v]}, "base": {0.0: [v]}}."""
    ends = []
    for kind, color, label, z in (("placebo", ROTC, "shuffled", 2), ("real", VEC, "the vector", 3)):
        xs = sorted(pts[kind])
        if not xs:
            continue
        cs = [centre(pts[kind][x]) for x in xs]
        ys = [m for m, _, _ in cs]
        ax.fill_between(xs, [m - lo for m, lo, _ in cs], [m + hi for m, _, hi in cs], color=color, alpha=0.15,
                        linewidth=0, zorder=z)
        ax.plot(xs, ys, color=color, linewidth=3.2, marker="o", markersize=8.5, markeredgecolor=SURF,
                markeredgewidth=1.6, zorder=z + 1, solid_capstyle="round", solid_joinstyle="round")
        ends.append((xs[-1], ys[-1], label, color, kind))
        if values and kind == "real":
            for x, y in ((xs[0], ys[0]), (xs[-1], ys[-1])):
                ax.annotate(_fmt(y), (x, y), xytext=(0, 11), textcoords="offset points", ha="center",
                            color=VEC, fontsize=9.5, fontweight="semibold", zorder=7)
    if pts["base"]:
        m, _, _ = centre(pts["base"][0.0])
        ax.plot([0], [m], color=INK, marker="o", markersize=9.5, markeredgecolor=SURF, markeredgewidth=1.6,
                linestyle="none", zorder=6)
        # the label goes to whichever side of the dot has no line running through it
        md = ax.transData.transform((0, m))[1]
        crowd = {"up": 0, "down": 0}
        for kind in ("real", "placebo"):
            xs = sorted(pts[kind])
            if len(xs) < 2 or not (xs[0] <= 0 <= xs[-1]):
                continue
            ys = [centre(pts[kind][x])[0] for x in xs]
            i = max(j for j in range(len(xs) - 1) if xs[j] <= 0)
            t = (0 - xs[i]) / (xs[i + 1] - xs[i]) if xs[i + 1] != xs[i] else 0
            yd = ax.transData.transform((0, ys[i] + t * (ys[i + 1] - ys[i])))[1]
            if 0 < yd - md < 26:
                crowd["up"] += 1
            elif 0 < md - yd < 26:
                crowd["down"] += 1
        dy = -15 if crowd["down"] <= crowd["up"] else 12
        ax.annotate("nothing added", (0, m), xytext=(0, dy), textcoords="offset points", ha="center",
                    color=INK2, fontsize=9, zorder=7)
    if log:
        ax.set_yscale("log")
        ax.minorticks_off()
    if ylim:
        ax.set_ylim(*ylim)
    if yticks:
        ax.set_yticks(yticks, [str(t) for t in yticks])
    # names at the right end of each line, pushed apart if they would touch
    lo = min([s for k in ("real", "placebo") for s in pts.get(k, {})] + [0.0])
    ax.set_xlim(min(-3.4, lo - 0.4) if lo <= -3 else lo - 0.4, 3.9)
    ends.sort(key=lambda e: e[1])
    ys_disp = []
    for x, y, label, color, kind in ends:
        ys_disp.append(ax.transData.transform((x, y))[1])
    for i in range(1, len(ys_disp)):
        if ys_disp[i] - ys_disp[i - 1] < 16:
            ys_disp[i] = ys_disp[i - 1] + 16
    for (x, y, label, color, kind), yd in zip(ends, ys_disp):
        yy = ax.transData.inverted().transform((0, yd))[1]
        ax.annotate(label, (x, yy), xytext=(9, 0), textcoords="offset points", va="center", ha="left",
                    color=color, fontsize=10, fontweight="semibold", zorder=8, annotation_clip=False)
    ax.set_title(title, loc="left", color=INK, fontsize=13.5, fontweight="semibold", pad=12)
    ax.set_ylabel(ylabel, color=INK2, fontsize=9.5)
    ax.set_xlabel("strength", color=INK2, fontsize=9.5)
    ticks = [x for x in (-3, -1.5, 0, 1.5, 3) if x >= lo - 0.01]
    ax.set_xticks(ticks, [("−" + str(abs(x)).rstrip("0").rstrip(".")) if x < 0 else ("+" + str(x).rstrip("0").rstrip(".") if x > 0 else "0") for x in ticks])
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0, colors=INK2, labelsize=9.5)
    ax.set_facecolor(SURF)
