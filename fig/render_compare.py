"""The A/B figure: the same room, two mood geometries.

Run A uses the naive "mood − neutral" contrast vectors — which are ~0.75
correlated with each other, so a *calm* push measurably carries sadness.
Run B projects the seed direction out of every other mood (`--orthogonal`),
so a calm push carries almost none. Same agents, same seed, same rules.

    python fig/render_compare.py --a docs/resonance-raw.json \
                                 --b docs/resonance.json [--out docs]

Outputs: docs/resonance-ab.png
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).parent.parent

AGENT_COLORS = {"EMBER": "#a78bfa", "ATLAS": "#f5b34d",
                "NOVA": "#6ea8ff", "QUILL": "#f2778a"}
SAD, CALM = "#8b7cf8", "#3fd0a4"

ap = argparse.ArgumentParser()
ap.add_argument("--a", default=str(HERE / "docs" / "resonance-raw.json"))
ap.add_argument("--b", default=str(HERE / "docs" / "resonance.json"))
ap.add_argument("--out", default=str(HERE / "docs"))
ap.add_argument("--chrome", default="google-chrome")
args = ap.parse_args()

W, H = 2400, 1350
out = pathlib.Path(args.out)


def load(p):
    d = json.loads(pathlib.Path(p).read_text())
    log = d["log"]
    by = {(r["round"], r["agent"]): r for r in log}
    rounds = sorted({r["round"] for r in log})
    agents = list(dict.fromkeys(r["agent"] for r in log))
    recv = {a: 0 for a in agents}
    for r in log:
        t = r.get("touch")
        if t:
            recv[t["target"]] += 1
    return d, log, by, rounds, agents, recv


A = load(args.a)
B = load(args.b)


def panel(D, title, sub, tint):
    d, log, by, rounds, agents, recv = D
    P = d["params"]
    pz = P["patient_zero"]
    cross = (P.get("cross") or {}).get("calm")
    pw, ph = 1020, 470
    ml, mr, mt, mb = 60, 150, 34, 40
    iw, ih = pw - ml - mr, ph - mt - mb

    def X(r): return ml + iw * (r / max(rounds))
    def Y(v): return mt + ih * (1 - (v + 0.3) / 10.6)

    s = [f"<svg width='{pw}' height='{ph}' viewBox='0 0 {pw} {ph}'>"]
    for v in (0, 5, 10):
        s.append(f"<line x1='{ml}' y1='{Y(v):.0f}' x2='{ml+iw}' "
                 f"y2='{Y(v):.0f}' stroke='rgba(107,118,137,"
                 f"{'.45' if v == 0 else '.15'})' stroke-width='1'/>")
        s.append(f"<text x='{ml-12}' y='{Y(v)+6:.0f}' text-anchor='end' "
                 f"font-size='17' fill='#6b7689'>{v}</text>")
    ends = []
    for a in agents:
        pts = [(r, by[(r, a)]["sad_score"]) for r in rounds
               if by[(r, a)].get("sad_score") is not None]
        path = " ".join(f"{X(r):.0f},{Y(v):.0f}" for r, v in pts)
        seeded = a == pz
        s.append(f"<polyline points='{path}' fill='none' "
                 f"stroke='{AGENT_COLORS[a]}' stroke-width='"
                 f"{4.5 if a == 'QUILL' else 3}' "
                 f"stroke-opacity='{1 if a in ('QUILL', pz) else .45}' "
                 f"stroke-dasharray='{'7,6' if seeded else 'none'}' "
                 f"stroke-linejoin='round' stroke-linecap='round'/>")
        r_, v_ = pts[-1]
        ends.append([Y(v_) + 6, X(r_) + 12, a, AGENT_COLORS[a],
                     recv[a], seeded])
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 26)
    for yy, xx, a, col, n, seeded in ends:
        tag = " (seeded)" if seeded else ""
        s.append(f"<text x='{xx:.0f}' y='{yy:.0f}' font-size='18' "
                 f"font-weight='700' fill='{col}'>{a}{tag}</text>")
        s.append(f"<text x='{xx:.0f}' y='{yy + 19:.0f}' font-size='14' "
                 f"fill='#6b7689'>got {n} calm</text>")
    for r in rounds:
        s.append(f"<text x='{X(r):.0f}' y='{ph - 12}' text-anchor='middle' "
                 f"font-size='15' fill='#6b7689'>r{r}</text>")
    s.append("</svg>")
    q = by[(max(rounds), "QUILL")]
    qpeak = max(by[(r, "QUILL")]["sad_score"] for r in rounds)
    return f"""
    <div class='pan'>
      <div class='ptitle' style='color:{tint}'>{title}</div>
      <div class='psub'>{sub}</div>
      <div class='pmath'>a <b style='color:{CALM}'>calm</b> push carries
        <b style='color:{tint}'>{cross:+.2f}</b> of
        <b style='color:{SAD}'>sad</b></div>
      {''.join(s)}
      <div class='pnote'>QUILL — never seeded, most cared-for —
        peaks at <b style='color:{tint}'>{qpeak}/10 sad</b></div>
    </div>"""


page = f"""<meta charset='utf-8'><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html {{ background:#070b13; }}
html, body {{ width:{W}px; height:{H}px; overflow:hidden; }}
body {{ background: radial-gradient(1100px 700px at 30% 25%, #101828 0%,
        #0a0f1a 55%, #070b13 100%); color:#e8ecf4;
  font-family:'Ubuntu Sans','Ubuntu','DejaVu Sans',sans-serif;
  display:flex; flex-direction:column; padding:64px 100px 44px 100px; }}
.top {{ display:flex; align-items:baseline; gap:20px; }}
.dot {{ width:26px; height:26px; border-radius:50%; background:#8b7cf8;
       box-shadow:0 0 22px 7px rgba(139,124,248,.45); align-self:center; }}
.brand {{ font-size:44px; font-weight:700; color:#fff; }}
.kicker {{ font-family:'Ubuntu Mono','DejaVu Sans Mono',monospace;
  font-size:24px; letter-spacing:.24em; font-weight:700; color:#8b7cf8; }}
h1 {{ font-size:60px; font-weight:800; color:#fff; margin-top:26px;
     letter-spacing:-0.015em; line-height:1.1; }}
.sub {{ font-family:'Ubuntu Mono','DejaVu Sans Mono',monospace;
  font-size:23px; color:#6b7689; margin-top:18px; }}
.sub b {{ color:#aeb8cc; }}
.cols {{ display:flex; gap:60px; margin-top:26px; }}
.pan {{ flex:1; }}
.ptitle {{ font-family:'Ubuntu Mono','DejaVu Sans Mono',monospace;
  font-size:26px; font-weight:700; letter-spacing:.16em; }}
.psub {{ font-size:20px; color:#8a93a6; margin-top:8px; }}
.pmath {{ font-family:'Ubuntu Mono','DejaVu Sans Mono',monospace;
  font-size:21px; color:#6b7689; margin-top:12px; }}
.pmath b {{ font-weight:700; }}
.pnote {{ font-size:22px; color:#cfd6e4; margin-top:10px; }}
.invite {{ display:flex; align-items:center; justify-content:center; gap:14px;
  position:fixed; left:100px; right:100px; bottom:40px; padding-top:22px;
  border-top:1px solid rgba(139,124,248,.28);
  font-family:'Ubuntu Mono','DejaVu Sans Mono',monospace; font-size:24px;
  color:#aeb8cc; }}
.invite b {{ color:#e8ecf4; }} .invite .play {{ color:#8b7cf8; font-weight:700; }}
text {{ font-family:'Ubuntu Mono','DejaVu Sans Mono',monospace; }}
</style>
<div class='top'><div class='dot'></div><span class='brand'>steeropathy</span>
  <span class='kicker'>RESONANCE · THE MEDICINE WAS THE DISEASE</span></div>
<h1>Agents kept sending each other <span style='color:{CALM}'>calm</span>.
  It made them sadder —<br>because in this model,
  <span style='color:{CALM}'>calm</span> and
  <span style='color:{SAD}'>sad</span> point the same way.</h1>
<div class='sub'>same 4 agents · same seed · same rules · the only difference
  is <b>the geometry of the mood vectors they push</b> · blind judge, 0–10,
  on every journal entry</div>
<div class='cols'>
  {panel(A, "RAW CONTRAST VECTORS", "mood − neutral, straight from transmit — what everyone builds", SAD)}
  {panel(B, "SAD PROJECTED OUT", "the same calm, with its sad component removed (--orthogonal)", CALM)}
</div>
<div class='invite'><span class='play'>▸</span>
  <b>github.com/moudrkat/steeropathy</b> · model
  {html.escape(str(A[0]['params'].get('model') or ''))}</div>"""

src = out / "resonance-ab.html"
src.write_text(page)
subprocess.run([args.chrome, "--headless=new", f"--window-size={W},{H}",
                f"--screenshot={out / 'resonance-ab.png'}",
                "--hide-scrollbars", "--force-device-scale-factor=1",
                str(src)], check=True, capture_output=True)
print(f"-> {out / 'resonance-ab.png'}")
