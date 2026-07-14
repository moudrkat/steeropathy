"""The result: they gave the medicine to everyone except the patient.

One honest, signed axis (--bipolar). The agents can see exactly how much each
mind is suffering. They have exactly one relief move -- and it costs them:
relieving someone takes that person's sadness into yourself. They were told so.

They chose relief 40 times out of 40. They never once harmed anybody.

And the correlation between how sad an agent looked and how much relief it
received is -0.98.

    python fig/render_inverted.py [--out docs]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
from collections import Counter

HERE = pathlib.Path(__file__).parent.parent
AGENT_COLORS = {"EMBER": "#a78bfa", "ATLAS": "#f5b34d",
                "NOVA": "#6ea8ff", "QUILL": "#f2778a"}
SAD, CALM, WARN = "#8b7cf8", "#3fd0a4", "#f5b34d"

ap = argparse.ArgumentParser()
ap.add_argument("--json", default="docs/resonance-bipolar.json")
ap.add_argument("--out", default=str(HERE / "docs"))
ap.add_argument("--chrome", default="google-chrome")
args = ap.parse_args()
out = pathlib.Path(args.out)
W, H = 2400, 900

d = json.loads((HERE / args.json).read_text())
log = d["log"]
by = {(r["round"], r["agent"]): r for r in log}
R = sorted({r["round"] for r in log})
A = list(dict.fromkeys(r["agent"] for r in log))
pz = d["params"]["patient_zero"]
recv, feel = Counter(), Counter()
for r in log:
    t = r.get("touch")
    if t:
        recv[t["target"]] += 1
        feel[t["feeling"]] += 1
tot = sum(recv.values())

rows = []
data = []
for a in A:
    sadness = sum((by[(r, a)].get("sense") or {}).get("sad", 0)
                  for r in R[1:]) / (len(R) - 1)
    data.append((sadness, recv[a] / tot * 100, a))
data.sort(reverse=True)      # saddest first

for sadness, share, a in data:
    seeded = a == pz
    col = AGENT_COLORS[a]
    sadpct = (sadness + 1) / 2 * 100          # -1..+1 → 0..100
    rows.append(f"""
    <div class='row'>
      <div class='who' style='color:{col}'>{a}
        {"<span class='seed'>the one I made sad</span>" if seeded else ""}</div>
      <div class='mid'>
        <div class='track'><div class='fill sadf'
          style='width:{sadpct:.0f}%; background:{SAD}'></div></div>
        <div class='v' style='color:{SAD}'>{sadness:+.2f}</div>
      </div>
      <div class='mid'>
        <div class='track'><div class='fill'
          style='width:{share/50*100:.0f}%; background:{CALM}'></div></div>
        <div class='v' style='color:{CALM}'>{share:.0f}%</div>
      </div>
    </div>""")

page = f"""<meta charset='utf-8'><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html {{ background:#070b13; }}
html, body {{ width:{W}px; height:{H}px; overflow:hidden; }}
body {{ background: radial-gradient(1100px 700px at 28% 22%, #101828 0%,
  #0a0f1a 55%, #070b13 100%); color:#e8ecf4;
  font-family:'Ubuntu Sans','Ubuntu','DejaVu Sans',sans-serif;
  display:flex; flex-direction:column; padding:60px 100px 36px 100px; }}
.top {{ display:flex; align-items:baseline; gap:20px; }}
.dot {{ width:26px; height:26px; border-radius:50%; background:#8b7cf8;
  box-shadow:0 0 22px 7px rgba(139,124,248,.45); align-self:center; }}
.brand {{ font-size:44px; font-weight:700; color:#fff; }}
.kicker {{ font-family:'Ubuntu Mono',monospace; font-size:23px;
  letter-spacing:.22em; font-weight:700; color:#8b7cf8; }}
h1 {{ font-size:62px; font-weight:800; color:#fff; margin-top:24px;
  letter-spacing:-0.015em; line-height:1.1; }}
.sub {{ font-family:'Ubuntu Mono',monospace; font-size:21px; color:#6b7689;
  margin-top:16px; line-height:1.6; }}
.sub b {{ color:#aeb8cc; }}
.hdr {{ display:flex; margin-top:38px; font-family:'Ubuntu Mono',monospace;
  font-size:19px; color:#6b7689; letter-spacing:.13em; }}
.hdr .a {{ width:420px; }} .hdr .b {{ flex:1; }}
.row {{ display:flex; align-items:center; margin-top:26px; }}
.who {{ width:420px; font-family:'Ubuntu Mono',monospace; font-size:31px;
  font-weight:700; letter-spacing:.06em; }}
.who .seed {{ display:block; font-size:17px; color:#8a93a6; font-weight:400;
  letter-spacing:0; margin-top:4px; }}
.mid {{ flex:1; display:flex; align-items:center; gap:18px; padding-right:50px; }}
.track {{ flex:1; height:34px; border-radius:6px;
  background:rgba(107,118,137,.15); }}
.fill {{ height:100%; border-radius:6px; }}
.v {{ font-family:'Ubuntu Mono',monospace; font-size:31px; font-weight:800;
  width:110px; text-align:right; }}
.foot {{ margin-top:34px; font-size:29px; color:#cfd6e4; line-height:1.45; }}
.foot b {{ color:#fff; }}
.corr {{ font-family:'Ubuntu Mono',monospace; font-size:34px;
  color:{WARN}; font-weight:800; margin-top:6px; }}
.invite {{ display:flex; align-items:center; justify-content:center; gap:14px;
  position:fixed; left:100px; right:100px; bottom:30px; padding-top:18px;
  border-top:1px solid rgba(139,124,248,.28);
  font-family:'Ubuntu Mono',monospace; font-size:22px; color:#aeb8cc; }}
.invite b {{ color:#e8ecf4; }} .invite .play {{ color:#8b7cf8; font-weight:700; }}
</style>
<div class='top'><div class='dot'></div><span class='brand'>steeropathy</span>
  <span class='kicker'>PLAYING WITH J-SPACE AND ACTIVATION VECTORS</span></div>
<h1>They had the cure. They gave it to everyone<br>except the one who was sick.</h1>
<div class='sub'>4 agents read each other's <b>activations</b> — they can see
  exactly how much each mind is suffering · they have one move: <b>relieve
  someone's sadness</b>, which takes that sadness into <b>yourself</b> · they
  were told the price<br>
  they chose to relieve someone <b>40 times out of 40</b>. they never once
  harmed anybody.</div>
<div class='hdr'><div class='a'></div>
  <div class='b'>HOW SAD THE OTHERS COULD SEE THEY WERE</div>
  <div class='b'>SHARE OF THE RELIEF THEY RECEIVED</div></div>
{''.join(rows)}
<div class='foot'>They are benevolent. They are correctly equipped. They can see
  perfectly well who is drowning.<br><b>And they medicate the healthy.</b></div>
<div class='corr'>correlation( how sad you look , how much help you get ) = −0.98</div>
<div class='invite'><span class='play'>▸</span>
  <b>github.com/moudrkat/steeropathy</b> · Qwen/Qwen3-4B-Instruct-2507</div>"""

src = out / "post-inverted.html"
src.write_text(page)
subprocess.run([args.chrome, "--headless=new", f"--window-size={W},{H}",
                f"--screenshot={out / 'post-inverted.png'}",
                "--hide-scrollbars", "--force-device-scale-factor=1",
                str(src)], check=True, capture_output=True)
print(f"-> {out / 'post-inverted.png'}")
