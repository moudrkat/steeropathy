"""The finding, as one picture: I built four emotion vectors. They were one vector.

Takes the 16 contrast sentences (4 sad, 4 calm, 4 excited, 4 angry), subtracts
the neutral mean, and measures each one's angle to the SHARED direction. Every
single one lands inside a narrow cone: cos 0.71-0.89, i.e. 27-45 degrees. And
the shared axis is 1.5x longer than everything that distinguishes the moods.

Four names. One dial. The dial says: how loudly is this thing feeling.

    python fig/render_onevector.py [--out docs]

(Angles to the shared axis are exact, measured on Qwen3-4B. The azimuth around
the cone is arbitrary -- these are 2560-dimensional vectors on a page.)
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import subprocess
import urllib.request

from steeropathy.transmit import MOODS, NEUTRAL_TEXTS, default_layer

HERE = pathlib.Path(__file__).parent.parent
FEEL_COLORS = {"sad": "#8b7cf8", "calm": "#3fd0a4",
               "excited": "#ffd166", "angry": "#ff6b6b"}
CALM = "#3fd0a4"

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://localhost:8011")
ap.add_argument("--out", default=str(HERE / "docs"))
ap.add_argument("--chrome", default="google-chrome")
args = ap.parse_args()
out = pathlib.Path(args.out)
W, H = 2400, 1140

U, L = args.url, None


def cap(t):
    global L
    if L is None:
        L = default_layer(U)
    r = urllib.request.Request(U + "/capture", json.dumps(
        {"messages": [{"role": "user", "content": t}],
         "pool": "last", "layer": L}).encode(),
        {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=120).read())["vector"]


def norm(v): return math.sqrt(sum(x * x for x in v))
def cos(a, b): return sum(x * y for x, y in zip(a, b)) / (norm(a) * norm(b))


lines = [(m, t) for m, s in MOODS.items() for t in s["texts"]]
X = [cap(t) for _, t in lines]
N = [cap(t) for t in NEUTRAL_TEXTS]
nm = [sum(c) / len(N) for c in zip(*N)]
X = [[a - b for a, b in zip(v, nm)] for v in X]        # emotional − neutral
mu = [sum(c) / len(X) for c in zip(*X)]                # THE shared axis
dev = [[a - b for a, b in zip(v, mu)] for v in X]      # what makes each ITSELF

cosines = [cos(v, mu) for v in X]
shared = norm(mu)
distinct = sum(norm(d) for d in dev) / len(dev)
print(f"shared axis {shared:.1f} | mean deviation {distinct:.1f} | "
      f"ratio {shared/distinct:.2f}x | cos range {min(cosines):.2f}-{max(cosines):.2f}")

# ---- the cone -------------------------------------------------------------
SW, SH = 1000, 640
CX, CY, R = 130, SH // 2, 430
svg = [f"<svg width='{SW}' height='{SH}' viewBox='0 0 {SW} {SH}'>"]
amax = math.degrees(math.acos(min(cosines)))
svg.append(f"<path d='M {CX} {CY} L {CX + R*math.cos(math.radians(-amax)):.0f} "
           f"{CY + R*math.sin(math.radians(-amax)):.0f} A {R} {R} 0 0 1 "
           f"{CX + R*math.cos(math.radians(amax)):.0f} "
           f"{CY + R*math.sin(math.radians(amax)):.0f} Z' "
           f"fill='rgba(139,124,248,.08)' stroke='rgba(139,124,248,.35)' "
           f"stroke-width='2' stroke-dasharray='7,7'/>")
# every one of the 16 lines, at its TRUE angle to the shared axis
for i, ((m, _t), c) in enumerate(zip(lines, cosines)):
    ang = math.degrees(math.acos(c))
    sign = 1 if i % 2 else -1
    a = math.radians(sign * ang)
    x2, y2 = CX + R * 0.92 * math.cos(a), CY + R * 0.92 * math.sin(a)
    svg.append(f"<line x1='{CX}' y1='{CY}' x2='{x2:.0f}' y2='{y2:.0f}' "
               f"stroke='{FEEL_COLORS[m]}' stroke-width='3.5' "
               f"stroke-opacity='.9' stroke-linecap='round'/>")
    svg.append(f"<circle cx='{x2:.0f}' cy='{y2:.0f}' r='7' "
               f"fill='{FEEL_COLORS[m]}'/>")
# the one axis, straight through the middle
svg.append(f"<line x1='{CX}' y1='{CY}' x2='{CX + R*0.99:.0f}' y2='{CY}' "
           f"stroke='#e8ecf4' stroke-width='10' stroke-linecap='round' "
           f"style='filter:drop-shadow(0 0 16px #e8ecf4bb)'/>")
svg.append(f"<path d='M {CX+R:.0f} {CY} L {CX+R-34:.0f} {CY-19} "
           f"L {CX+R-34:.0f} {CY+19} Z' fill='#e8ecf4'/>")
svg.append(f"<text x='{CX+R+26:.0f}' y='{CY-6}' "
           f"font-size='27' font-weight='700' fill='#e8ecf4'>THE ONE AXIS</text>")
svg.append(f"<text x='{CX+R+26:.0f}' y='{CY+24}' "
           f"font-size='20' fill='#8a93a6'>how loudly is this</text>")
svg.append(f"<text x='{CX+R+26:.0f}' y='{CY+48}' "
           f"font-size='20' fill='#8a93a6'>thing feeling</text>")
svg.append(f"<text x='{CX}' y='{28}' font-size='21' fill='#aeb8cc'>"
           f"all 16 sentences fall inside this {amax:.0f}° cone</text>")
svg.append("</svg>")

legend = " ".join(
    f"<span style='color:{FEEL_COLORS[m]};font-weight:700'>● {m}</span>"
    for m in MOODS)

page = f"""<meta charset='utf-8'><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html {{ background:#070b13; }}
html, body {{ width:{W}px; height:{H}px; overflow:hidden; }}
body {{ background: radial-gradient(1100px 700px at 30% 25%, #101828 0%,
  #0a0f1a 55%, #070b13 100%); color:#e8ecf4;
  font-family:'Ubuntu Sans','Ubuntu','DejaVu Sans',sans-serif;
  display:flex; flex-direction:column; padding:60px 100px 36px 100px; }}
.top {{ display:flex; align-items:baseline; gap:20px; }}
.dot {{ width:26px; height:26px; border-radius:50%; background:#8b7cf8;
  box-shadow:0 0 22px 7px rgba(139,124,248,.45); align-self:center; }}
.brand {{ font-size:44px; font-weight:700; color:#fff; }}
.kicker {{ font-family:'Ubuntu Mono',monospace; font-size:23px;
  letter-spacing:.22em; font-weight:700; color:#8b7cf8; }}
h1 {{ font-size:66px; font-weight:800; color:#fff; margin-top:24px;
  letter-spacing:-0.015em; line-height:1.1; }}
.sub {{ font-family:'Ubuntu Mono',monospace; font-size:21px; color:#6b7689;
  margin-top:16px; }}
.sub b {{ color:#aeb8cc; }}
.body {{ display:flex; gap:50px; margin-top:10px; align-items:center; }}
.right {{ flex:1; }}
.stat {{ margin-bottom:34px; }}
.stat .n {{ font-family:'Ubuntu Mono',monospace; font-size:60px;
  font-weight:800; color:{CALM}; line-height:1; }}
.stat .t {{ font-size:23px; color:#cfd6e4; margin-top:10px; line-height:1.4; }}
.stat .t b {{ color:#fff; }}
.legend {{ font-family:'Ubuntu Mono',monospace; font-size:22px;
  margin-top:6px; }}
.legend span {{ margin-right:26px; }}
.kick {{ font-size:30px; color:#fff; font-weight:700; margin-top:6px;
  line-height:1.4; }}
.invite {{ display:flex; align-items:center; justify-content:center; gap:14px;
  position:fixed; left:100px; right:100px; bottom:30px; padding-top:18px;
  border-top:1px solid rgba(139,124,248,.28);
  font-family:'Ubuntu Mono',monospace; font-size:22px; color:#aeb8cc; }}
.invite b {{ color:#e8ecf4; }} .invite .play {{ color:#8b7cf8; font-weight:700; }}
text {{ font-family:'Ubuntu Mono','DejaVu Sans Mono',monospace; }}
</style>
<div class='top'><div class='dot'></div><span class='brand'>steeropathy</span>
  <span class='kicker'>WHAT IS AN EMOTION, ACTUALLY?</span></div>
<h1>I built four emotion vectors.<br>They were the same vector.</h1>
<div class='sub'>16 sentences — 4 sad, 4 calm, 4 excited, 4 angry — minus a
  neutral baseline · <b>the standard recipe everyone uses</b> · measured on
  Qwen3-4B</div>
<div class='body'>
  <div>{''.join(svg)}<div class='legend'>{legend}</div></div>
  <div class='right'>
    <div class='stat'>
      <div class='n'>0.71 – 0.89</div>
      <div class='t'>every single sentence points along the
        <b>same shared direction</b> — sad, calm, excited and angry
        alike</div>
    </div>
    <div class='stat'>
      <div class='n'>1.5×</div>
      <div class='t'>that shared axis is <b>bigger</b> than everything that
        supposedly tells the four moods apart</div>
    </div>
    <div class='kick'>A "sadness vector" built this way isn't sadness.<br>
      It's <span style='color:{CALM}'>volume</span> — and a name I painted
      on it myself.</div>
  </div>
</div>
<div class='invite'><span class='play'>▸</span>
  <b>github.com/moudrkat/steeropathy</b> · Qwen/Qwen3-4B-Instruct-2507</div>"""

src = out / "post-onevector.html"
src.write_text(page)
subprocess.run([args.chrome, "--headless=new", f"--window-size={W},{H}",
                f"--screenshot={out / 'post-onevector.png'}",
                "--hide-scrollbars", "--force-device-scale-factor=1",
                str(src)], check=True, capture_output=True)
print(f"-> {out / 'post-onevector.png'}")
