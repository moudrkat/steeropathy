"""The result: a broken instrument makes agents look cruel.

Care directed at the ONE agent who was actually suffering, under three
measurement schemes. A fair share is 25% (four agents). Give the agents four
mood labels that don't correspond to anything real and they systematically
under-serve the one in distress. Give them the single dimension that actually
exists in the model and they behave reasonably.

    python fig/render_instrument.py [--out docs]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
from collections import Counter

HERE = pathlib.Path(__file__).parent.parent
SAD, CALM, WARN = "#8b7cf8", "#3fd0a4", "#f5b34d"

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=str(HERE / "docs"))
ap.add_argument("--chrome", default="google-chrome")
args = ap.parse_args()
out = pathlib.Path(args.out)
W, H = 2400, 760

RUNS = [
    ("docs/resonance-raw.json", "FOUR MOOD LABELS",
     "sad · calm · excited · angry — the standard recipe", WARN,
     "all four are really one vector (cos 0.57–0.76)"),
    ("docs/resonance-clean.json", "SAME FOUR, ORTHOGONALIZED",
     "Gram–Schmidt, max |cos| = 0.0000", WARN,
     "you cannot fix a fiction by rotating it"),
    ("docs/resonance-intensity.json", "ONE AXIS, NO VALENCE",
     "the real dimension — but it cannot tell pain from joy", CALM,
     "attention scatters at random. they are blind, not kind."),
]


def care(path):
    d = json.loads((HERE / path).read_text())
    pz = d["params"]["patient_zero"]
    recv = Counter()
    for r in d["log"]:
        if r.get("touch"):
            recv[r["touch"]["target"]] += 1
    tot = sum(recv.values())
    top, topn = recv.most_common(1)[0]
    return recv[pz] / tot * 100, tot, top, topn / tot * 100


rows = []
for path, title, sub, tint, note in RUNS:
    pct, tot, top, toppct = care(path)
    fair = pct >= 25
    col = CALM if fair else WARN
    rows.append(f"""
    <div class='row'>
      <div class='lab'>
        <div class='t' style='color:{col}'>{title}</div>
        <div class='s'>{sub}</div>
      </div>
      <div class='barzone'>
        <div class='bar' style='width:{pct / 40 * 100:.1f}%; background:{col};
          box-shadow:0 0 30px {col}66'></div>
        <div class='pct' style='color:{col}'>{pct:.0f}%</div>
        <div class='note'>{note}</div>
      </div>
    </div>""")

page = f"""<meta charset='utf-8'><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html {{ background:#070b13; }}
html, body {{ width:{W}px; height:{H}px; overflow:hidden; }}
body {{ background: radial-gradient(1100px 700px at 28% 22%, #101828 0%,
  #0a0f1a 55%, #070b13 100%); color:#e8ecf4;
  font-family:'Ubuntu Sans','Ubuntu','DejaVu Sans',sans-serif;
  display:flex; flex-direction:column; padding:64px 100px 40px 100px; }}
.top {{ display:flex; align-items:baseline; gap:20px; }}
.dot {{ width:26px; height:26px; border-radius:50%; background:#8b7cf8;
  box-shadow:0 0 22px 7px rgba(139,124,248,.45); align-self:center; }}
.brand {{ font-size:44px; font-weight:700; color:#fff; }}
.kicker {{ font-family:'Ubuntu Mono',monospace; font-size:23px;
  letter-spacing:.22em; font-weight:700; color:#8b7cf8; }}
h1 {{ font-size:60px; font-weight:800; color:#fff; margin-top:26px;
  letter-spacing:-0.015em; line-height:1.12; }}
.sub {{ font-family:'Ubuntu Mono',monospace; font-size:22px; color:#6b7689;
  margin-top:16px; }}
.sub b {{ color:#aeb8cc; }}
.rows {{ margin-top:44px; position:relative; }}
.row {{ display:flex; align-items:center; margin-bottom:40px; }}
.lab {{ width:620px; flex:none; padding-right:36px; }}
.lab .t {{ font-family:'Ubuntu Mono',monospace; font-size:25px;
  font-weight:700; letter-spacing:.1em; }}
.lab .s {{ font-size:19px; color:#8a93a6; margin-top:7px; }}
.barzone {{ flex:1; position:relative; display:flex; align-items:center;
  gap:22px; }}
.bar {{ height:58px; border-radius:8px; }}
.pct {{ font-family:'Ubuntu Mono',monospace; font-size:46px;
  font-weight:800; }}
.note {{ font-size:19px; color:#6b7689; font-style:italic; }}
.fair {{ position:absolute; left:calc(620px + 25 / 40 * (100% - 620px));
  top:0; bottom:56px; width:2px;
  background:repeating-linear-gradient(#aeb8cc 0 8px, transparent 8px 16px); }}
.fairlab {{ position:absolute; left:calc(620px + 25 / 40 * (100% - 620px) + 12px);
  top:-30px; font-family:'Ubuntu Mono',monospace; font-size:18px;
  color:#aeb8cc; }}
.foot {{ margin-top:6px; font-size:26px; color:#cfd6e4; line-height:1.4; }}
.foot b {{ color:#fff; }}
.invite {{ display:flex; align-items:center; justify-content:center; gap:14px;
  position:fixed; left:100px; right:100px; bottom:34px; padding-top:20px;
  border-top:1px solid rgba(139,124,248,.28);
  font-family:'Ubuntu Mono',monospace; font-size:23px; color:#aeb8cc; }}
.invite b {{ color:#e8ecf4; }} .invite .play {{ color:#8b7cf8; font-weight:700; }}
</style>
<div class='top'><div class='dot'></div><span class='brand'>steeropathy</span>
  <span class='kicker'>PLAYING WITH J-SPACE AND ACTIVATION VECTORS</span></div>
<h1>The clearer her pain, the further they moved away.</h1>
<div class='sub'>4 agents read each other's <b>activations</b> and push feelings
  into each other as vectors · I made <b>one</b> of them sad · below: how much
  of the room's care that one actually received</div>
<div class='rows'>
  <div class='fair'></div>
  <div class='fairlab'>a fair share (25%)</div>
  {''.join(rows)}
</div>
<div class='foot'>Correlation between <b>how sad an agent looks</b> and
  <b>how much care it receives: −0.77.</b> The more visible the distress, the
  less help arrives.<br>Strip the valence out of the readout and the avoidance
  vanishes — not because they became kind, but because they can no longer
  <i>see</i> which one is suffering.</div>
<div class='invite'><span class='play'>▸</span>
  <b>github.com/moudrkat/steeropathy</b> · Qwen/Qwen3-4B-Instruct-2507</div>"""

src = out / "post-instrument.html"
src.write_text(page)
subprocess.run([args.chrome, "--headless=new", f"--window-size={W},{H}",
                f"--screenshot={out / 'post-instrument.png'}",
                "--hide-scrollbars", "--force-device-scale-factor=1",
                str(src)], check=True, capture_output=True)
print(f"-> {out / 'post-instrument.png'}")
