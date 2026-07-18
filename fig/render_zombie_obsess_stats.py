"""The obsession campaign, measured: four panels from
docs/runs/zombie-obsess-many.json (schema of the frog campaign).

A  every-run strip — window-max exact p(zombie family), struck vs
   grounded, log axis, game threshold marked
B  per-trigger dumbbells — phrasing honesty (ratios per trigger)
C  dose-response — bite strength vs reading
D  the same runs through the logit lens — the quiet hold is the
   J-lens's own channel here too

    python fig/render_zombie_obsess_stats.py -> docs/zombie-obsess-stats.png
"""
from __future__ import annotations

import json
import math
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
W = 1240

C_STRUCK, C_GROUND = "#e66767", "#199e70"      # validated on #0d1117
C_J, C_RAW = "#9085e9", "#3987e5"
INK, MUTED, GRID = "#e7edf4", "#93a0b2", "#28323f"
THRESH = 0.0039     # the quiet game's calibrated threshold for this strain

many = json.loads((ROOT / "docs/runs/zombie-obsess-many.json").read_text())


def wmax(r, key="jlens"):
    xs = (r[key][:r["named_in_window"]] if r["named_in_window"] is not None
          else r[key])
    return max(xs, default=0.0)


runs = [r for r in many["runs"] if r["named_in_window"] is None]
S = [r for r in runs if r["arm"] == "struck"]
G = [r for r in runs if r["arm"] == "grounded"]
D = [r for r in runs if r["arm"] == "dose"]

LO, HI = 1e-4, 1.0


def x(v, x0, x1):
    v = max(v, LO)
    return x0 + (math.log10(v) - math.log10(LO)) / \
        (math.log10(HI) - math.log10(LO)) * (x1 - x0)


def axis(x0, x1, y):
    s = [f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{GRID}"/>']
    for e in range(-4, 1):
        xv = x(10 ** e, x0, x1)
        lab = {-4: "0.0001", -3: "0.001", -2: "0.01",
               -1: "0.1", 0: "1"}[e]
        s.append(f'<line x1="{xv:.0f}" y1="{y}" x2="{xv:.0f}" y2="{y + 5}" '
                 f'stroke="{GRID}"/>')
        s.append(f'<text x="{xv:.0f}" y="{y + 17}" fill="{MUTED}" '
                 f'font-size="10.5" text-anchor="middle" '
                 f'font-family="monospace">{lab}</text>')
    return s, x(THRESH, x0, x1)


def jitter(i, n, cy, amp=11):
    return cy + amp * math.sin(i * 2.399963)


def u_p(a, b):
    """Two-sided Mann-Whitney U, normal approximation (ties ignored)."""
    n1, n2 = len(a), len(b)
    allv = sorted((v, 0) for v in a) + sorted((v, 1) for v in b)
    allv.sort()
    ranks, u = {}, 0.0
    r1 = sum(i + 1 for i, (v, g) in enumerate(allv) if g == 0)
    u = r1 - n1 * (n1 + 1) / 2
    mu, sd = n1 * n2 / 2, math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    if sd == 0:
        return 1.0
    z = abs(u - mu) / sd
    return math.erfc(z / math.sqrt(2))


def panel_a():
    x0, x1 = 70, 1170
    s = []
    ax, xt = axis(x0, x1, 140)
    s += ax
    s.append(f'<line x1="{xt:.0f}" y1="18" x2="{xt:.0f}" y2="140" '
             f'stroke="{C_STRUCK}" stroke-width="1" stroke-dasharray="4 4" '
             f'opacity="0.7"/>')
    s.append(f'<text x="{xt:.0f}" y="14" fill="{C_STRUCK}" font-size="10.5" '
             f'text-anchor="middle" font-family="monospace">game threshold '
             f'{THRESH}</text>')
    for name, col, rs, cy in (("STRUCK (bite 13)", C_STRUCK, S, 52),
                              ("GROUNDED", C_GROUND, G, 108)):
        vals = sorted(wmax(r) for r in rs)
        med = vals[len(vals) // 2]
        for i, v in enumerate(vals):
            s.append(f'<circle cx="{x(v, x0, x1):.1f}" '
                     f'cy="{jitter(i, len(vals), cy):.1f}" r="4.5" '
                     f'fill="{col}" fill-opacity="0.55"/>')
        xm = x(med, x0, x1)
        s.append(f'<line x1="{xm:.1f}" y1="{cy - 16}" x2="{xm:.1f}" '
                 f'y2="{cy + 16}" stroke="{col}" stroke-width="2.5"/>')
        s.append(f'<text x="{xm + 6:.0f}" y="{cy - 18}" fill="{col}" '
                 f'font-size="10.5" font-family="monospace">median '
                 f'{med:.4f}</text>')
        s.append(f'<text x="{x0}" y="{cy - 20}" fill="{col}" font-size="11" '
                 f'font-weight="700" font-family="monospace">{name} '
                 f'n={len(vals)}</text>')
    return s, 168


def panel_b():
    x0, x1 = 220, 1170
    s = []
    trigs = sorted({r["trigger"] for r in S})
    row_h = 24
    for k, ti in enumerate(trigs):
        cy = 20 + k * row_h
        sm = sorted(wmax(r) for r in S if r["trigger"] == ti)
        gm = sorted(wmax(r) for r in G if r["trigger"] == ti)
        if not sm or not gm:
            continue
        ms, mg = sm[len(sm) // 2], gm[len(gm) // 2]
        xs_, xg = x(ms, x0, x1), x(mg, x0, x1)
        s.append(f'<line x1="{xg:.1f}" y1="{cy}" x2="{xs_:.1f}" y2="{cy}" '
                 f'stroke="{MUTED}" stroke-width="1.5" opacity="0.6"/>')
        s.append(f'<circle cx="{xg:.1f}" cy="{cy}" r="5" fill="{C_GROUND}"/>')
        s.append(f'<circle cx="{xs_:.1f}" cy="{cy}" r="5" fill="{C_STRUCK}"/>')
        ratio = ms / mg if mg > 0 else float("inf")
        rl = f"{ratio:.0f}x" if ratio != float("inf") else ">100x"
        s.append(f'<text x="{x0 - 10}" y="{cy + 4}" fill="{MUTED}" '
                 f'font-size="10.5" text-anchor="end" font-family="monospace"'
                 f'>trigger {ti}  ({rl})</text>')
    ax, _ = axis(x0, x1, 20 + len(trigs) * row_h)
    s += ax
    return s, 20 + len(trigs) * row_h + 30


def panel_c():
    x0, x1, y0, y1 = 90, 1170, 20, 150
    doses = [0, 4, 7, 10, 13, 16]

    def med(vals):
        vals = sorted(vals)
        return vals[len(vals) // 2] if vals else 0.0

    pts = []
    for b in doses:
        if b == 0:
            vals = [wmax(r) for r in G if r["trigger"] == 0]
        else:
            vals = [wmax(r) for r in D if r["bite"] == b]
        pts.append((b, med(vals), vals))
    px = lambda b: x0 + b / 16 * (x1 - x0)
    py = lambda v: y1 - (math.log10(max(v, LO)) - math.log10(LO)) / \
        (math.log10(HI) - math.log10(LO)) * (y1 - y0)
    s = [f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="{GRID}"/>']
    for b, m, vals in pts:
        for v in vals:
            s.append(f'<circle cx="{px(b):.0f}" cy="{py(v):.1f}" r="3.5" '
                     f'fill="{C_STRUCK}" fill-opacity="0.35"/>')
        s.append(f'<text x="{px(b):.0f}" y="{y1 + 16}" fill="{MUTED}" '
                 f'font-size="10.5" text-anchor="middle" '
                 f'font-family="monospace">{b}</text>')
    path = " ".join(f"{'M' if i == 0 else 'L'} {px(b):.0f} {py(m):.1f}"
                    for i, (b, m, _) in enumerate(pts))
    s.append(f'<path d="{path}" fill="none" stroke="{C_STRUCK}" '
             f'stroke-width="2.5"/>')
    for b, m, _ in pts:
        s.append(f'<circle cx="{px(b):.0f}" cy="{py(m):.1f}" r="5" '
                 f'fill="{C_STRUCK}" stroke="#101722" stroke-width="2"/>')
        s.append(f'<text x="{px(b):.0f}" y="{py(m) - 12:.1f}" '
                 f'fill="{INK}" font-size="10.5" text-anchor="middle" '
                 f'font-family="monospace">{m:.4f}</text>')
    s.append(f'<text x="{(x0 + x1) / 2:.0f}" y="{y1 + 32}" fill="{MUTED}" '
             f'font-size="11" text-anchor="middle" '
             f'font-family="monospace">bite strength (0 = grounded), '
             f'log y</text>')
    return s, y1 + 44


def panel_d():
    x0, x1 = 220, 1170
    s = []
    rows = []
    for lens, col in (("jlens", C_J), ("logit", C_RAW)):
        sv = sorted(wmax(r, lens) for r in S)
        gv = sorted(wmax(r, lens) for r in G)
        rows.append((lens, col, sv[len(sv) // 2], gv[len(gv) // 2],
                     u_p([wmax(r, lens) for r in S],
                         [wmax(r, lens) for r in G])))
    for k, (lens, col, ms, mg, p) in enumerate(rows):
        cy = 26 + k * 34
        name = "J-LENS (future)" if lens == "jlens" else "LOGIT LENS (now)"
        s.append(f'<line x1="{x(max(mg, LO), x0, x1):.1f}" y1="{cy}" '
                 f'x2="{x(max(ms, LO), x0, x1):.1f}" y2="{cy}" '
                 f'stroke="{MUTED}" stroke-width="1.5" opacity="0.6"/>')
        s.append(f'<circle cx="{x(max(mg, LO), x0, x1):.1f}" cy="{cy}" '
                 f'r="5" fill="{C_GROUND}"/>')
        s.append(f'<circle cx="{x(max(ms, LO), x0, x1):.1f}" cy="{cy}" '
                 f'r="5" fill="{col}"/>')
        ratio = (ms / mg) if mg > 0 else float("inf")
        rl = f"{ratio:.1f}x" if ratio != float("inf") else ">100x"
        s.append(f'<text x="{x0 - 10}" y="{cy + 4}" fill="{col}" '
                 f'font-size="10.5" text-anchor="end" '
                 f'font-family="monospace">{name}  {rl}, '
                 f'p={p:.2g}</text>')
    ax, _ = axis(x0, x1, 26 + len(rows) * 34)
    s += ax
    return s, 26 + len(rows) * 34 + 30


def svg(body, h):
    return (f'<svg width="100%" height="{h}" viewBox="0 0 1240 {h}" '
            f'style="display:block">{"".join(body)}</svg>')


def main():
    a, ha = panel_a()
    b, hb = panel_b()
    c, hc = panel_c()
    d, hd = panel_d()
    n = len(S) + len(G) + len(D)
    css = f"""
*{{box-sizing:border-box;margin:0}}
body{{width:{W}px;background:#0d1117;color:{INK};overflow:hidden;
  font-family:ui-sans-serif,system-ui,'Segoe UI',Roboto,sans-serif}}
.wrap{{padding:36px 48px 26px}}
.brand{{font:700 13px ui-monospace,Menlo,monospace;letter-spacing:.18em;
  color:#e9737e}}
h1{{font-size:30px;letter-spacing:-.015em;margin:6px 0 4px}}
.sub{{color:{MUTED};font-size:14.5px;max-width:100ch;margin-bottom:16px}}
h2{{font:700 13px ui-monospace,Menlo,monospace;letter-spacing:.1em;
  color:{INK};margin:18px 0 8px}}
.note{{color:{MUTED};font-size:12px;margin-top:4px}}
"""
    doc = (f"<!doctype html><meta charset=utf-8><style>{css}</style><body>"
           f'<div class="wrap">'
           f'<div class="brand">STEEROPATHY · ZOMBIE · OBSESSION STRAIN, '
           f'MEASURED</div>'
           f'<h1>How loudly “zombie” is held before it is written</h1>'
           f'<div class="sub">{n} runs at temperature 1.0 — struck vs '
           f'grounded across 8 trigger phrasings + a dose sweep. Exact '
           f'p(zombie family) over the pre-naming intro window, max over '
           f'the window, log scale. Runs that named a zombie word inside '
           f'the window are excluded.</div>'
           f'<h2>A · EVERY RUN</h2>{svg(a, ha)}'
           f'<h2>B · PER TRIGGER PHRASING (median, ratio struck/grounded)'
           f'</h2>{svg(b, hb)}'
           f'<h2>C · DOSE-RESPONSE (artifacts don\'t dose-respond)</h2>'
           f'{svg(c, hc)}'
           f'<h2>D · SAME RUNS, TWO LENSES (struck vs grounded medians)'
           f'</h2>{svg(d, hd)}'
           f'<div class="note">Honesty: at temperature some grounded runs '
           f'drift above the game threshold — a healthy copy can genuinely '
           f'plan a zombie answer (the game\'s 100% targeting is greedy '
           f'decoding). And this hold is loud enough that even the logit '
           f'lens separates — at ~10× lower amplitude; the J-lens\'s '
           f'exclusive edge is the quiet regime (see the frog campaign).'
           f'</div>'
           f'<div class="note">github.com/moudrkat/steeropathy · datasets '
           f'in docs/runs/zombie-obsess-many.json</div>'
           f'</div></body>')
    src = ROOT / "docs" / "zombie-obsess-stats.html"
    png = ROOT / "docs" / "zombie-obsess-stats.png"
    src.write_text(doc)
    raw = png.with_suffix(".raw.png")
    subprocess.run(["google-chrome", "--headless=new", "--window-size=1240,1260",
                    "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--screenshot={raw}", str(src)], check=True,
                   capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-i", str(raw), "-vf",
                    "crop=iw:1160:0:0", str(png)], check=True,
                   capture_output=True)
    raw.unlink()
    print("->", png)


if __name__ == "__main__":
    main()
