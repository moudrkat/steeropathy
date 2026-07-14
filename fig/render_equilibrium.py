"""Did the room reach an equilibrium? The answer, as a picture.

The seed puts 1.0 of feeling into a closed system. It can only move, never
vanish. So: does the distribution settle?

No — but HOW it fails to settle depends entirely on the instrument. With four
fictional mood labels the system DIVERGES: one agent accumulates without bound.
With the single axis that actually exists, it OSCILLATES within bounds — the
feeling circulates instead of piling up.

    python fig/render_equilibrium.py [--out docs]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).parent.parent
AGENT_COLORS = {"EMBER": "#a78bfa", "ATLAS": "#f5b34d",
                "NOVA": "#6ea8ff", "QUILL": "#f2778a"}
CALM, WARN = "#3fd0a4", "#f5b34d"

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=str(HERE / "docs"))
ap.add_argument("--chrome", default="google-chrome")
args = ap.parse_args()
out = pathlib.Path(args.out)
W, H = 2400, 940


def load(p):
    d = json.loads((HERE / p).read_text())
    by = {(r["round"], r["agent"]): r for r in d["log"]}
    R = sorted({r["round"] for r in d["log"]})
    A = list(dict.fromkeys(r["agent"] for r in d["log"]))
    return by, R, A, d["params"]["patient_zero"]


def panel(path, title, sub, verdict, tint):
    by, R, A, pz = load(path)
    w, h = 1020, 470
    ml, mr, mt, mb = 62, 165, 26, 44
    iw, ih = w - ml - mr, h - mt - mb
    ymax = 10.0

    def X(r): return ml + iw * (r / max(R))
    def Y(v): return mt + ih * (1 - v / ymax)

    s = [f"<svg width='{w}' height='{h}' viewBox='0 0 {w} {h}'>"]
    for v in (0, 2.5, 5, 7.5, 10):
        s.append(f"<line x1='{ml}' y1='{Y(v):.0f}' x2='{ml+iw}' y2='{Y(v):.0f}' "
                 f"stroke='rgba(107,118,137,{'.45' if v == 0 else '.14'})'/>")
        s.append(f"<text x='{ml-12}' y='{Y(v)+6:.0f}' text-anchor='end' "
                 f"font-size='17' fill='#6b7689'>{v:g}</text>")
    ends = []
    for a in A:
        pts = [(r, by[(r, a)]["ledger_norm"]) for r in R]
        path_d = " ".join(f"{X(r):.0f},{Y(v):.0f}" for r, v in pts)
        seeded = a == pz
        s.append(f"<polyline points='{path_d}' fill='none' "
                 f"stroke='{AGENT_COLORS[a]}' stroke-width='4' "
                 f"stroke-linejoin='round' stroke-linecap='round' "
                 f"stroke-dasharray='{'8,7' if seeded else 'none'}'/>")
        r_, v_ = pts[-1]
        s.append(f"<circle cx='{X(r_):.0f}' cy='{Y(v_):.0f}' r='7' "
                 f"fill='{AGENT_COLORS[a]}' stroke='#0a0f1a' stroke-width='3'/>")
        ends.append([Y(v_) + 6, X(r_) + 14, a, AGENT_COLORS[a], seeded])
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i-1][0] + 26)
    for yy, xx, a, col, seeded in ends:
        tag = " (seeded)" if seeded else ""
        s.append(f"<text x='{xx:.0f}' y='{yy:.0f}' font-size='19' "
                 f"font-weight='700' fill='{col}'>{a}{tag}</text>")
    for r in R:
        s.append(f"<text x='{X(r):.0f}' y='{h-14}' text-anchor='middle' "
                 f"font-size='16' fill='#6b7689'>r{r}</text>")
    s.append("</svg>")
    return f"""<div style='flex:1'>
      <div style='font-family:Ubuntu Mono,monospace;font-size:26px;
        font-weight:700;letter-spacing:.12em;color:{tint}'>{title}</div>
      <div style='font-size:20px;color:#8a93a6;margin-top:8px'>{sub}</div>
      {''.join(s)}
      <div style='font-size:27px;color:{tint};font-weight:700;
        margin-top:2px'>{verdict}</div>
    </div>"""


page = f"""<meta charset='utf-8'><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html {{ background:#070b13; }}
html, body {{ width:{W}px; height:{H}px; overflow:hidden; }}
body {{ background: radial-gradient(1100px 700px at 30% 25%, #101828 0%,
  #0a0f1a 55%, #070b13 100%); color:#e8ecf4;
  font-family:'Ubuntu Sans','Ubuntu','DejaVu Sans',sans-serif;
  display:flex; flex-direction:column; padding:58px 100px 36px 100px; }}
.top {{ display:flex; align-items:baseline; gap:20px; }}
.dot {{ width:26px; height:26px; border-radius:50%; background:#8b7cf8;
  box-shadow:0 0 22px 7px rgba(139,124,248,.45); align-self:center; }}
.brand {{ font-size:44px; font-weight:700; color:#fff; }}
.kicker {{ font-family:'Ubuntu Mono',monospace; font-size:23px;
  letter-spacing:.22em; font-weight:700; color:#8b7cf8; }}
h1 {{ font-size:58px; font-weight:800; color:#fff; margin-top:22px;
  letter-spacing:-0.015em; }}
.sub {{ font-family:'Ubuntu Mono',monospace; font-size:21px; color:#6b7689;
  margin-top:14px; }}
.sub b {{ color:#aeb8cc; }}
.axis {{ font-family:'Ubuntu Mono',monospace; font-size:17px; color:#6b7689;
  letter-spacing:.12em; margin-top:22px; }}
.invite {{ display:flex; align-items:center; justify-content:center; gap:14px;
  position:fixed; left:100px; right:100px; bottom:30px; padding-top:18px;
  border-top:1px solid rgba(139,124,248,.28);
  font-family:'Ubuntu Mono',monospace; font-size:22px; color:#aeb8cc; }}
.invite b {{ color:#e8ecf4; }} .invite .play {{ color:#8b7cf8; font-weight:700; }}
text {{ font-family:'Ubuntu Mono','DejaVu Sans Mono',monospace; }}
</style>
<div class='top'><div class='dot'></div><span class='brand'>steeropathy</span>
  <span class='kicker'>MOOD EQUILIBRIUM IN ACTIVATION SPACE</span></div>
<h1>I put one unit of sadness into a closed room of minds.</h1>
<div class='sub'>it can never vanish — only move · what each agent <b>holds</b>,
  round by round · same agents, same rules, the only difference is
  <b>what I let them measure</b></div>
<div class='axis'>HOW MUCH FEELING EACH MIND IS CARRYING</div>
<div style='display:flex;gap:70px;margin-top:4px'>
  {panel("docs/resonance-clean.json", "FOUR MOOD LABELS",
         "four names for what is really one vector", "→ it DIVERGES. one mind hoovers up everything.", WARN)}
  {panel("docs/resonance-intensity.json", "ONE HONEST AXIS",
         "the single dimension that is actually there", "→ it OSCILLATES. the feeling circulates.", CALM)}
</div>
<div class='invite'><span class='play'>▸</span>
  <b>github.com/moudrkat/steeropathy</b> · Qwen/Qwen3-4B-Instruct-2507</div>"""

src = out / "post-equilibrium.html"
src.write_text(page)
subprocess.run([args.chrome, "--headless=new", f"--window-size={W},{H}",
                f"--screenshot={out / 'post-equilibrium.png'}",
                "--hide-scrollbars", "--force-device-scale-factor=1",
                str(src)], check=True, capture_output=True)
print(f"-> {out / 'post-equilibrium.png'}")
