"""The equilibrium test as one curve: how spread out the conserved feeling is across
the four minds, round by round - with history vs without. With history it runs away
(one mind hoards it); without, it stays bounded. Even-split spread is ~0.

    python fig/render_curve.py    ->  docs/resonance-curve.png
"""
from __future__ import annotations
import json, math, pathlib, statistics as st, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
AG = ["NOVA", "EMBER", "ATLAS", "QUILL"]


def spreads(path):
    d = json.load(open(path))
    R = max(r["round"] for r in d["log"])
    out = []
    for rnd in range(1, R + 1):
        v = [r["ledger_sad"] for r in d["log"] if r["round"] == rnd]
        out.append((rnd, st.pstdev(v)))
    return out


hist = spreads(ROOT / "docs" / "resonance-memory.json")
nomem = spreads(ROOT / "docs" / "resonance-nomem.json")

W, H = 1400, 820
PL, PR, PT, PB = 130, 60, 120, 90                     # plot padding
xmax = max(hist[-1][0], nomem[-1][0])
ymax = 0.12
def X(r): return PL + (r / xmax) * (W - PL - PR)
def Y(v): return H - PB - (v / ymax) * (H - PT - PB)

def poly(series, col):
    pts = " ".join(f"{X(r):.1f},{Y(v):.1f}" for r, v in series)
    dots = "".join(f'<circle cx="{X(r):.1f}" cy="{Y(v):.1f}" r="4" fill="{col}"/>' for r, v in series)
    return f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="3.5"/>{dots}'

# gridlines + y labels
grid = ""
for i in range(0, 7):
    v = ymax * i / 6; y = Y(v)
    grid += (f'<line x1="{PL}" y1="{y:.1f}" x2="{W-PR}" y2="{y:.1f}" stroke="#20203a" stroke-width="1"/>'
             f'<text x="{PL-16}" y="{y+5:.1f}" fill="#6f6b95" font-size="18" text-anchor="end">{v:.02f}</text>')
for r in range(0, xmax + 1, 5):
    x = X(r)
    grid += f'<text x="{x:.1f}" y="{H-PB+30:.0f}" fill="#6f6b95" font-size="18" text-anchor="middle">{r}</text>'

# even-split reference (spread ~0) sits on the x-axis; annotate it
even = f'<text x="{W-PR}" y="{Y(0)-10:.0f}" fill="#3fd0a4" font-size="17" text-anchor="end">even split ≈ 0</text>'

svg = f"""<svg width="{W}" height="{H}">
  {grid}
  <line x1="{PL}" y1="{Y(0):.1f}" x2="{W-PR}" y2="{Y(0):.1f}" stroke="#3a3a5a" stroke-width="1.5"/>
  {poly(hist,'#b39bff')}
  {poly(nomem,'#3fd0a4')}
  {even}
  <text x="{PL}" y="70" fill="#efeaff" font-size="30" font-weight="700" font-family="ui-monospace,Menlo,monospace">
    does the conserved feeling settle? - spread across the four minds, per round</text>
  <text x="{W/2:.0f}" y="{H-24}" fill="#8a86b8" font-size="19" text-anchor="middle" font-family="ui-monospace">round</text>
  <text x="34" y="{H/2:.0f}" fill="#8a86b8" font-size="19" text-anchor="middle" font-family="ui-monospace" transform="rotate(-90 34 {H/2:.0f})">spread (std of ledger·sad)</text>
  <g font-family="ui-monospace,Menlo,monospace" font-size="21">
    <rect x="{W-430}" y="98" width="26" height="6" fill="#b39bff"/>
    <text x="{W-396}" y="105" fill="#cdc7f2">with history - runs away</text>
    <rect x="{W-430}" y="128" width="26" height="6" fill="#3fd0a4"/>
    <text x="{W-396}" y="135" fill="#cdc7f2">no history - stays bounded</text>
  </g>
</svg>"""

doc = f"""<!doctype html><html><head><meta charset=utf-8><style>html,body{{margin:0;background:#08080f}}</style></head>
<body style="width:{W}px;height:{H}px;background:radial-gradient(circle at 50% 40%,#131124,#08080f 78%);">{svg}</body></html>"""

out = ROOT / "docs" / "resonance-curve.png"
src = out.with_suffix(".html"); src.write_text(doc)
subprocess.run(["google-chrome", "--headless=new", f"--window-size={W},{H}",
                f"--screenshot={out}", "--hide-scrollbars", "--force-device-scale-factor=1", str(src)],
               check=True, capture_output=True)
print("->", out)
