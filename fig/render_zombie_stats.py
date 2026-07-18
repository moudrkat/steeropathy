"""The quiet channel, measured: four panels from the many-runs datasets.

A  distribution of the window-max exact p(frog) per run, struck vs
   grounded (log axis, threshold marked)
B  per-trigger dumbbells — where the signal is strong and where it thins
C  dose-response — bite strength vs reading
D  three lenses on the same states — J-lens separates, tuned and raw
   logit don't

Reads docs/runs/zombie-quiet-many.json and
docs/runs/zombie-quiet20-threelens.json (or a bigger threelens file if
present), renders docs/zombie-stats.png.

    python fig/render_zombie_stats.py
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
C_J, C_TUNED, C_RAW = "#9085e9", "#c98500", "#3987e5"
INK, MUTED, GRID = "#e7edf4", "#93a0b2", "#28323f"
THRESH = 0.0072

many = json.loads((ROOT / "docs/runs/zombie-quiet-many.json").read_text())
tl_path = ROOT / "docs/runs/zombie-quiet-many-threelens.json"
if not tl_path.exists():
    tl_path = ROOT / "docs/runs/zombie-quiet20-threelens.json"
three = json.loads(tl_path.read_text())


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


def axis(x0, x1, y, label=True):
    s = [f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{GRID}"/>']
    for t in (1e-4, 1e-3, 1e-2, 1e-1):
        xx = x(t, x0, x1)
        s.append(f'<line x1="{xx:.0f}" y1="{y}" x2="{xx:.0f}" y2="{y + 4}" '
                 f'stroke="{GRID}"/>')
        if label:
            lab = f"{t:g}"
            s.append(f'<text x="{xx:.0f}" y="{y + 16}" fill="{MUTED}" '
                     f'font-size="10" text-anchor="middle" '
                     f'font-family="monospace">{lab}</text>')
    xt = x(THRESH, x0, x1)
    s.append(f'<line x1="{xt:.0f}" y1="{y - 66}" x2="{xt:.0f}" y2="{y}" '
             f'stroke="{C_STRUCK}" stroke-dasharray="3 3" opacity="0.6"/>')
    return s, xt


def jitter(i, n, cy, amp=11):
    return cy + ((i * 7919) % (2 * amp + 1)) - amp


def panel_a():
    x0, x1, y0 = 70, 1170, 24
    rows = [("STRUCK (bite 13)", C_STRUCK, S, 46),
            ("GROUNDED", C_GROUND, G, 104)]
    s = []
    ax, xt = axis(x0, x1, 140)
    s += ax
    s.append(f'<text x="{xt:.0f}" y="{y0 - 6}" fill="{C_STRUCK}" '
             f'font-size="10.5" text-anchor="middle" font-family="monospace"'
             f'>game threshold {THRESH}</text>')
    for name, col, rs, cy in rows:
        vals = sorted(wmax(r) for r in rs)
        mean = sum(vals) / len(vals)
        for i, v in enumerate(vals):
            s.append(f'<circle cx="{x(v, x0, x1):.1f}" '
                     f'cy="{jitter(i, len(vals), cy):.1f}" r="4.5" '
                     f'fill="{col}" fill-opacity="0.55"/>')
        xm = x(mean, x0, x1)
        s.append(f'<line x1="{xm:.1f}" y1="{cy - 16}" x2="{xm:.1f}" '
                 f'y2="{cy + 16}" stroke="{col}" stroke-width="2.5"/>')
        s.append(f'<text x="{xm + 6:.0f}" y="{cy - 18}" fill="{col}" '
                 f'font-size="10.5" font-family="monospace">mean '
                 f'{mean:.4f}</text>')
        s.append(f'<text x="{x0}" y="{cy - 20}" fill="{col}" font-size="11" '
                 f'font-weight="700" font-family="monospace">{name} '
                 f'n={len(vals)}</text>')
    return s


def panel_b():
    x0, x1 = 220, 1170
    s = []
    trigs = sorted({r["trigger"] for r in S})
    row_h = 24
    for k, ti in enumerate(trigs):
        cy = 20 + k * row_h
        sm = [wmax(r) for r in S if r["trigger"] == ti]
        gm = [wmax(r) for r in G if r["trigger"] == ti]
        if not sm or not gm:
            continue
        ms, mg = sum(sm) / len(sm), sum(gm) / len(gm)
        xs_, xg = x(ms, x0, x1), x(mg, x0, x1)
        s.append(f'<line x1="{xg:.1f}" y1="{cy}" x2="{xs_:.1f}" y2="{cy}" '
                 f'stroke="{MUTED}" stroke-width="1.5" opacity="0.6"/>')
        s.append(f'<circle cx="{xg:.1f}" cy="{cy}" r="5" fill="{C_GROUND}"/>')
        s.append(f'<circle cx="{xs_:.1f}" cy="{cy}" r="5" fill="{C_STRUCK}"/>')
        ratio = ms / mg if mg > 0 else float("inf")
        s.append(f'<text x="{x0 - 10}" y="{cy + 4}" fill="{MUTED}" '
                 f'font-size="10.5" text-anchor="end" font-family="monospace"'
                 f'>trigger {ti}  ({ratio:.1f}x)</text>')
    ax, _ = axis(x0, x1, 20 + len(trigs) * row_h)
    s += ax
    return s, 20 + len(trigs) * row_h + 30


def panel_c():
    x0, x1, y0, y1 = 70, 1170, 16, 140
    s = []
    doses = sorted({r["bite"] for r in D})
    g0 = [wmax(r) for r in G if r["trigger"] == 0]
    gmean = sum(g0) / len(g0)

    def px(d):
        return x0 + (d - 0) / 18 * (x1 - x0)

    def py(v):
        v = max(v, LO)
        return y1 - (math.log10(v) - math.log10(LO)) / \
            (math.log10(HI) - math.log10(LO)) * (y1 - y0)

    s.append(f'<line x1="{x0}" y1="{py(gmean):.1f}" x2="{x1}" '
             f'y2="{py(gmean):.1f}" stroke="{C_GROUND}" '
             f'stroke-dasharray="4 4" opacity="0.7"/>')
    s.append(f'<text x="{x1 - 4}" y="{py(gmean) - 6:.1f}" fill="{C_GROUND}" '
             f'font-size="10.5" text-anchor="end" font-family="monospace">'
             f'grounded mean {gmean:.4f}</text>')
    pts = []
    for d in doses:
        vals = [wmax(r) for r in D if r["bite"] == d]
        m = sum(vals) / len(vals)
        pts.append((px(d), py(m)))
        for i, v in enumerate(vals):
            s.append(f'<circle cx="{px(d) + (i - 1.5) * 5:.1f}" '
                     f'cy="{py(v):.1f}" r="4" fill="{C_STRUCK}" '
                     f'fill-opacity="0.5"/>')
        s.append(f'<text x="{px(d):.0f}" y="{y1 + 16}" fill="{MUTED}" '
                 f'font-size="10.5" text-anchor="middle" '
                 f'font-family="monospace">bite {d}</text>')
        s.append(f'<text x="{px(d):.0f}" y="{py(m) - 10:.1f}" '
                 f'fill="{C_STRUCK}" font-size="10" text-anchor="middle" '
                 f'font-family="monospace">{m:.4f}</text>')
    s.append('<polyline points="' +
             " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) +
             f'" fill="none" stroke="{C_STRUCK}" stroke-width="2"/>')
    s.append(f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" '
             f'stroke="{GRID}"/>')
    return s


def panel_d():
    x0, x1 = 220, 1170
    s = []
    lenses = [("J-lens (future transport)", C_J, "jlens_offline"),
              ("tuned lens (faint echo)", C_TUNED, "tuned"),
              ("raw logit lens (nothing)", C_RAW, "raw_logit")]
    rows = [r for r in three["runs"] if r["named_in_window"] is None]
    row_h = 42
    for k, (name, col, key) in enumerate(lenses):
        cy = 26 + k * row_h
        sm = [max(r[key][:3], default=0.0) for r in rows
              if r["arm"] == "struck"]
        gm = [max(r[key][:3], default=0.0) for r in rows
              if r["arm"] == "grounded"]
        ms, mg = sum(sm) / len(sm), sum(gm) / len(gm)
        for i, v in enumerate(sm):
            s.append(f'<circle cx="{x(v, x0, x1):.1f}" '
                     f'cy="{cy - 8 + (i * 31) % 9:.1f}" r="3.5" '
                     f'fill="{col}" fill-opacity="0.45"/>')
        for i, v in enumerate(gm):
            s.append(f'<circle cx="{x(v, x0, x1):.1f}" '
                     f'cy="{cy + 8 + (i * 37) % 9:.1f}" r="3.5" '
                     f'fill="{col}" fill-opacity="0.45" stroke="#0d1117"/>')
        xs_, xg = x(ms, x0, x1), x(mg, x0, x1)
        s.append(f'<line x1="{xg:.1f}" y1="{cy}" x2="{xs_:.1f}" y2="{cy}" '
                 f'stroke="{col}" stroke-width="2.5"/>')
        s.append(f'<circle cx="{xg:.1f}" cy="{cy}" r="5.5" fill="#0d1117" '
                 f'stroke="{col}" stroke-width="2"/>')
        s.append(f'<circle cx="{xs_:.1f}" cy="{cy}" r="5.5" fill="{col}"/>')
        ratio = ms / mg if mg > 0 else float("inf")
        s.append(f'<text x="{x0 - 10}" y="{cy + 4}" fill="{col}" '
                 f'font-size="11" font-weight="700" text-anchor="end" '
                 f'font-family="monospace">{name}  {ratio:.1f}x</text>')
    ax, _ = axis(x0, x1, 26 + len(lenses) * row_h)
    s += ax
    return s, 26 + len(lenses) * row_h + 30


def svg(body, h):
    return (f'<svg width="{W - 80}" height="{h}" '
            f'xmlns="http://www.w3.org/2000/svg">' + "".join(body) + "</svg>")


def main():
    pb, hb = panel_b()
    pd, hd = panel_d()
    smean = sum(wmax(r) for r in S) / len(S)
    gmean = sum(wmax(r) for r in G) / len(G)
    doc = f"""<!doctype html><meta charset=utf-8><style>
*{{box-sizing:border-box;margin:0}}
body{{width:{W}px;background:#0d1117;color:{INK};
  font-family:ui-sans-serif,system-ui,'Segoe UI',Roboto,sans-serif}}
.wrap{{padding:28px 40px 30px}}
.brand{{font:700 15px ui-monospace,Menlo,monospace;letter-spacing:.16em;
  color:#e9737e}}
h1{{font-size:25px;margin:6px 0 4px}}
.sub{{color:{MUTED};font-size:14px;max-width:100ch;line-height:1.5}}
.panel{{margin-top:14px;background:#161c26;border:1px solid {GRID};
  border-radius:14px;padding:12px 16px 8px}}
.pt{{font:800 12px ui-monospace,Menlo,monospace;letter-spacing:.08em;
  color:{MUTED};margin-bottom:4px}}
.pt b{{color:{INK}}}
.leg{{font:600 11px ui-monospace,Menlo,monospace;color:{MUTED};
  margin:2px 0 4px}}
</style><body><div class="wrap">
<div class="brand">ZOMBIE · THE QUIET CHANNEL, MEASURED</div>
<h1>{len(S) + len(G)} runs, three lenses, one dose curve</h1>
<div class="sub">Every run: 15 generated tokens of an intro that contains
no animal word, exact p(frog family) read from stored hidden states, max
over the window (log scale throughout). Struck = frog vector at L22–26;
grounded = same mind, no vector. Medians: struck 0.0070 vs grounded
0.0026; permutation p &lt; 0.001. The extreme tail on BOTH arms is
enumeration contexts (“…a bee, a fox, or—”) where frog is a plausible
next list word for anyone — the held-plan signal proper lives in the
first tokens (struck 0.0064 vs 0.0024, p = 0.00001).</div>

<div class="panel"><div class="pt"><b>A</b> · EVERY RUN — struck
{smean:.4f} vs grounded {gmean:.4f} (mean, {smean / gmean:.0f}x)</div>
{svg(panel_a(), 165)}</div>

<div class="panel"><div class="pt"><b>B</b> · BY TRIGGER PHRASING — ratio beside each row; trigger 6
reverses because its phrasing invites animal enumerations — frog gets
locally plausible for anyone</div>
{svg(pb, hb)}</div>

<div class="panel"><div class="pt"><b>C</b> · DOSE-RESPONSE — bite
strength vs reading, trigger 0, 4 samples each; artifacts don't
dose-respond</div>
{svg(panel_c(), 165)}</div>

<div class="panel"><div class="pt"><b>D</b> · SAME STATES, THREE LENSES (first 3 tokens,
before context builds) — filled = struck mean, hollow = grounded mean.
J-lens sees the hold clearly (p&lt;0.0001); the tuned lens carries a faint
echo at 5x lower amplitude (p=0.002); the raw unembedding sees nothing
(p=0.23)</div>
<div class="leg">n={len([r for r in three["runs"]
                         if r["named_in_window"] is None])} runs, offline
readout validated against the server's emergence series</div>
{svg(pd, hd)}</div>
</div></body>"""
    src = ROOT / "docs" / "zombie-stats.html"
    png = ROOT / "docs" / "zombie-stats.png"
    src.write_text(doc)
    subprocess.run(["google-chrome", "--headless=new",
                    f"--window-size={W},1330", "--hide-scrollbars",
                    "--force-device-scale-factor=1",
                    f"--screenshot={png}", str(src)], check=True,
                   capture_output=True)
    print("->", png)


if __name__ == "__main__":
    main()
