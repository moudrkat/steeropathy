"""A prettier resonance animation: each agent is a glowing orb, its light the amount
of sadness it holds (ledger·sad), and every push is a comet of grief migrating between
them — take pulls it toward the reliever, give sends it away.

Pure stdlib: renders SVG/CSS frames, shoots them with headless Chrome, stitches with
ffmpeg — same toolchain as render_resonance.py.

    python fig/render_orbs.py [--json docs/resonance.json] [--sub 12]
    -> docs/resonance-orbs.gif , docs/resonance-orbs.mp4
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

ap = argparse.ArgumentParser()
ap.add_argument("--json", default=str(ROOT / "docs" / "resonance.json"))
ap.add_argument("--sub", type=int, default=12, help="tween frames per round")
ap.add_argument("--chrome", default="google-chrome")
ap.add_argument("--size", type=int, default=1200)
args = ap.parse_args()

AGENTS = ("NOVA", "EMBER", "ATLAS", "QUILL")
PURPLE = "139,124,248"          # sadness
S = args.size
C = S / 2
CY = S * 0.47                    # ring centered slightly high so the bottom orb clears the caption
ORBIT = S * 0.29
POS = {                          # a ring: top, right, bottom, left
    "NOVA":  (C, CY - ORBIT),
    "EMBER": (C + ORBIT, CY),
    "ATLAS": (C, CY + ORBIT),
    "QUILL": (C - ORBIT, CY),
}

run = json.load(open(args.json))
log = run["log"]
R = max(r["round"] for r in log)
seed_agent = run["params"].get("patient_zero", "EMBER")
seed_mood = run["params"].get("seed_mood", "sad")

# each orb's sadness is read straight off the activations — drift·sad, the same
# reading the agents get. Measured from each mind's own round-0 state, so round 0 is
# a true null (sense is None) and everyone starts dark.
def sread(rec):
    # the CONSERVED quantity: ledger·sad, the sad-vector this mind currently holds.
    # you seed it into one mind once; every push is a zero-sum transfer, so the sum
    # over all four is invariant. This is the physics — not the drift readout, which
    # is re-measured each round and does not conserve.
    return rec.get("ledger_sad", 0.0)


sad_read = {(r["round"], r["agent"]): sread(r) for r in log}
# touches happen at the end of each round; sadness flows: give giver->target, take target->giver
touches = {rnd: [] for rnd in range(R + 1)}
for r in log:
    t = r.get("touch")
    if not t:
        continue
    giver, target = r["agent"], t["target"]
    src, dst = (giver, target) if t["feeling"] == "give" else (target, giver)
    touches[r["round"]].append({"src": src, "dst": dst, "pts": t.get("points") or 10,
                                "kind": t["feeling"]})

MAXPTS = max((t["pts"] for ts in touches.values() for t in ts), default=30)
# the conserved total = the seed amount injected at round 1 (sum over minds is invariant);
# scale everything so it reads as 100 units of feeling being passed around
TOTAL = sum(sad_read.get((1, a), 0.0) for a in AGENTS) or 1e-6


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c0, c1, t):
    return tuple(round(lerp(a, b, t)) for a, b in zip(c0, c1))


COOL = (108, 112, 150)          # neutral: faint, grey
HOT = (188, 132, 255)           # holds sadness (+): hot violet
TEAL = (86, 222, 190)           # holds NEGATIVE sadness (−): drained below baseline, bright teal


def orb_div(name, frac):
    # frac = this mind's share of the conserved total. brightness = |frac| so BOTH poles
    # are lit: purple for a mind holding sadness (+), teal for one drained negative (−).
    i = min(1.0, abs(frac))
    n = round(100 * frac)
    x, y = POS[name]
    d = 44 + 92 * i                                  # big swing: empty is small, loaded is huge
    g = mix(COOL, HOT if frac >= 0 else TEAL, i)
    gc = f"{g[0]},{g[1]},{g[2]}"
    glow1 = 22 + 210 * i
    glow2 = 6 + 90 * i
    a1 = 0.20 + 0.65 * i
    core = (f"radial-gradient(circle at 42% 38%, #f7f2ff, rgba({gc},{0.55+0.42*i}) 58%, "
            f"rgba({g[0]//2},{g[1]//2},{max(0,g[2]-70)},{0.5+0.3*i}))")
    numlit = 0.30 + 0.7 * i
    return f"""
    <div style="position:absolute;left:{x-d/2:.0f}px;top:{y-d/2:.0f}px;
        width:{d:.0f}px;height:{d:.0f}px;border-radius:50%;background:{core};
        box-shadow:0 0 {glow1:.0f}px {glow2:.0f}px rgba({gc},{a1:.2f}),
                   0 0 {glow1*2:.0f}px {glow2*1.7:.0f}px rgba({gc},{a1*0.5:.2f});"></div>
    <div style="position:absolute;left:{x-100:.0f}px;top:{y+d/2+12:.0f}px;width:200px;
        text-align:center;font-family:ui-monospace,Menlo,monospace;">
      <div style="color:rgba(228,224,255,{0.35+0.45*i:.2f});font:600 22px ui-monospace;
        letter-spacing:2px;">{name}</div>
      <div style="color:rgba({gc},{numlit:.2f});font:700 30px ui-monospace;margin-top:2px;">{n}</div>
    </div>"""


def comet(src, dst, t, pts, kind):
    sx, sy = POS[src]
    dx, dy = POS[dst]
    x, y = lerp(sx, dx, t), lerp(sy, dy, t)
    sz = 10 + 22 * (pts / MAXPTS)
    parts = []
    # faint travelled line
    ang = math.degrees(math.atan2(dy - sy, dx - sx))
    ln = math.hypot(dx - sx, dy - sy) * t
    parts.append(f"""<div style="position:absolute;left:{sx:.0f}px;top:{sy:.0f}px;
        width:{ln:.0f}px;height:2px;transform-origin:0 50%;transform:rotate({ang:.1f}deg);
        background:linear-gradient(90deg,rgba({PURPLE},0),rgba({PURPLE},.30));"></div>""")
    # comet trail
    for j, tr in enumerate((0.0, 0.05, 0.11, 0.18)):
        tt = max(0.0, t - tr)
        cx, cy = lerp(sx, dx, tt), lerp(sy, dy, tt)
        s = sz * (1 - j * 0.22)
        a = (0.9 - j * 0.24)
        parts.append(f"""<div style="position:absolute;left:{cx-s/2:.0f}px;top:{cy-s/2:.0f}px;
            width:{s:.0f}px;height:{s:.0f}px;border-radius:50%;
            background:radial-gradient(circle,#f4f1ff,rgba({PURPLE},{a:.2f}));
            box-shadow:0 0 {26*a:.0f}px {8*a:.0f}px rgba({PURPLE},{a*0.7:.2f});"></div>""")
    return "".join(parts)


def frame_html(rnd, t):
    prev = max(0, rnd - 1)
    fracs = {a: lerp(sad_read[(prev, a)], sad_read[(rnd, a)], t) / TOTAL for a in AGENTS}
    orbs = "".join(orb_div(a, fracs[a]) for a in AGENTS)
    total = round(100 * sum(fracs.values()))          # invariant: always ~100
    comets = "".join(comet(c["src"], c["dst"], t, c["pts"], c["kind"])
                     for c in touches[rnd])
    beat = ("seed vector → EMBER" if rnd == 1
            else "steering vectors propagate" if rnd >= 2
            else "baseline · zero drift")
    caption = f"round {rnd} / {R} &nbsp;·&nbsp; {beat}"
    return f"""<!doctype html><html><head><meta charset=utf-8>
    <style>html,body{{margin:0;background:#08080f}}</style></head>
    <body style="width:{S}px;height:{S}px;position:relative;overflow:hidden;
        background:radial-gradient(circle at 50% 46%,#151327,#08080f 70%);
        font-family:ui-monospace,Menlo,monospace;">
      {comets}{orbs}
      <div style="position:absolute;left:0;top:44px;width:{S}px;text-align:center;">
        <div style="color:#efeaff;font:700 40px ui-monospace;letter-spacing:1px;">Four agents communicating in activation space</div>
        <div style="color:#9a96c8;font:400 22px ui-monospace;margin-top:12px;letter-spacing:1px;">
          no tokens exchanged — they read each other off the residual stream and<br>
          communicate by sending steering vectors, one into a recipient&rsquo;s forward pass</div>
      </div>
      <div style="position:absolute;left:0;top:{S-92}px;width:{S}px;text-align:center;">
        <div style="color:#b9b4e8;font-size:25px;letter-spacing:2px;">{caption}</div>
      </div>
    </body></html>"""


def shoot(html, png):
    src = png.with_suffix(".html")
    src.write_text(html)
    subprocess.run([args.chrome, "--headless=new", f"--window-size={S},{S}",
                    f"--screenshot={png}", "--hide-scrollbars",
                    "--force-device-scale-factor=1", str(src)],
                   check=True, capture_output=True)


def main():
    build = pathlib.Path(tempfile.mkdtemp(prefix="orbs_"))
    frames = []
    for rnd in range(0, R + 1):
        for k in range(args.sub):
            t = k / max(1, args.sub - 1)
            png = build / f"f{rnd:03d}_{k:02d}.png"
            shoot(frame_html(rnd, t), png)
            hold = 1 / 14
            if rnd in (0, 1) and k == args.sub - 1:
                hold = 0.5                       # linger on baseline & on the seed
            frames.append((png, hold))
        print(f"round {rnd} rendered")
    frames.append((frames[-1][0], 2.2))          # hold final

    concat = build / "frames.txt"
    lines = []
    for f, hold in frames:
        lines += [f"file '{f.name}'", f"duration {hold}"]
    lines.append(f"file '{frames[-1][0].name}'")
    concat.write_text("\n".join(lines) + "\n")

    out = ROOT / "docs"
    gif, mp4 = out / "resonance-orbs.gif", out / "resonance-orbs.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-i", str(concat),
                    "-vf", "fps=18,scale=560:-1:flags=lanczos,split[a][b];"
                           "[a]palettegen=stats_mode=diff:max_colors=128[p];"
                           "[b][p]paletteuse=dither=bayer:bayer_scale=4",
                    "-loop", "0", str(gif)], check=True, capture_output=True, cwd=build)
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-i", str(concat),
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "20",
                    str(mp4)], check=True, capture_output=True, cwd=build)
    print("->", gif)
    print("->", mp4)


if __name__ == "__main__":
    main()
