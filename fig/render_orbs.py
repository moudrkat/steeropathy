"""A prettier resonance animation: each agent is a glowing orb, its light the amount
of sadness it holds (ledger·sad), and every push is a comet of grief migrating between
them - take pulls it toward the reliever, give sends it away.

Pure stdlib: renders SVG/CSS frames, shoots them with headless Chrome, stitches with
ffmpeg - same toolchain as render_resonance.py.

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
ap.add_argument("--calm", action="store_true",
                help="slower motion + a settle-beat after every round; writes *-calm.*")
ap.add_argument("--max-rounds", type=int, default=0,
                help="cap rounds shown (0 = all); a short calm cut needs only the first few")
args = ap.parse_args()

# pacing: calm keeps the motion snappy (near the raw speed) but rests after every
# round — the settle-beats + fewer rounds read calm without going sluggish
FRAME_HOLD = 1 / 13 if args.calm else 1 / 14
SETTLE = 0.35 if args.calm else 0.0
FINAL_HOLD = 1.6 if args.calm else 2.2
# lighter gif encode for the longer calm cut so it stays under LinkedIn's ~8MB
GIF_FPS, GIF_SCALE, GIF_COLORS, GIF_BAYER = (
    (15, 560, 96, 5) if args.calm else (18, 560, 128, 4))

AGENTS = ("NOVA", "EMBER", "ATLAS", "QUILL")
PURPLE = "139,124,248"          # sadness
S = args.size
C = S / 2
CY = S * 0.48                    # ring centered so nothing crowds the edges or the caption
ORBIT = S * 0.235               # pulled inward: leaves a clear margin so the gif never looks clipped
POS = {                          # a ring: top, right, bottom, left
    "NOVA":  (C, CY - ORBIT),
    "EMBER": (C + ORBIT, CY),
    "ATLAS": (C, CY + ORBIT),
    "QUILL": (C - ORBIT, CY),
}

run = json.load(open(args.json))
log = run["log"]
R = max(r["round"] for r in log)
if args.max_rounds:
    R = min(R, args.max_rounds)          # a short calm cut shows only the first few
    log = [r for r in log if r["round"] <= R]   # drop later rounds so touches align
seed_agent = run["params"].get("patient_zero", "EMBER")
seed_mood = run["params"].get("seed_mood", "sad")

# each orb's sadness is read straight off the activations - drift·sad, the same
# reading the agents get. Measured from each mind's own round-0 state, so round 0 is
# a true null (sense is None) and everyone starts dark.
def sread(rec):
    # the CONSERVED quantity: ledger·sad, the sad-vector this mind currently holds.
    # you seed it into one mind once; every push is a zero-sum transfer, so the sum
    # over all four is invariant. This is the physics - not the drift readout, which
    # is re-measured each round and does not conserve.
    return rec.get("ledger_sad", 0.0)


sad_read = {(r["round"], r["agent"]): sread(r) for r in log}
# the mind-reading itself: each round's J-space words — formed in the layers, never
# written. Shown under each orb; this is what makes the figure an instrument, not art.
mind_read = {(r["round"], r["agent"]): [w["t"] for w in (r.get("mind") or [])][:3]
             for r in log}
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


def orb_div(name, frac, words=(), wa=0.0):
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
      <div style="color:rgba(196,189,240,{wa:.2f});font:italic 500 21px ui-monospace;
        margin-top:4px;line-height:1.4;">{'<br>'.join(words)}</div>
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


def seed_bolt(t):
    """The event the whole gif is about: a bright labeled drop falling into the
    seeded mind. Without it the orb just lights up with no visible cause."""
    x, y0 = POS[seed_agent]
    y = lerp(y0 - S * 0.20, y0, min(1.0, t * 1.2))
    a = 1.0 - 0.3 * t
    return f"""<div style="position:absolute;left:{x-10:.0f}px;top:{y-10:.0f}px;
        width:20px;height:20px;border-radius:50%;
        background:radial-gradient(circle,#fff,rgba({PURPLE},.95));
        box-shadow:0 0 40px 14px rgba({PURPLE},{a:.2f});"></div>
      <div style="position:absolute;left:{x-180:.0f}px;top:{y0-S*0.20-52:.0f}px;width:360px;
        text-align:center;color:#d9d2ff;font:700 30px ui-monospace;
        opacity:{1.0-t*0.5:.2f};letter-spacing:1px;">“sadness”</div>"""


def frame_html(rnd, t):
    prev = max(0, rnd - 1)
    fracs = {a: lerp(sad_read[(prev, a)], sad_read[(rnd, a)], t) / TOTAL for a in AGENTS}
    # each mind's unwritten words fade in as its round resolves — quiet, legible proof
    # that this is read off the layers, not invented
    wa = 0.28 + 0.34 * t
    orbs = "".join(orb_div(a, fracs[a], mind_read.get((rnd, a)) or (), wa)
                   for a in AGENTS)
    total = round(100 * sum(fracs.values()))          # invariant: always ~100
    comets = "".join(comet(c["src"], c["dst"], t, c["pts"], c["kind"])
                     for c in touches[rnd])
    if rnd == 1:
        comets += seed_bolt(t)
    # the story, told in beats big enough to read at feed size
    beat, hot = (("not a word will ever pass between them", False) if rnd == 0
                 else ("one “feeling”, seeded into a single “mind”", True) if rnd == 1
                 else ("the others read it straight off its activations", False) if rnd == 2
                 else ("…and push it between them, silently", False))
    caption = (f"<div style='color:{'#cbb9ff' if hot else '#c4bdf0'};"
               f"font:700 40px ui-monospace;letter-spacing:1px;'>{beat}</div>"
               f"<div style='color:#8b86b8;font-size:22px;margin-top:10px;letter-spacing:2px;'>"
               f"round {rnd} / {R} &nbsp;·&nbsp; <i>italics: words formed in the layers, never written</i></div>")
    return f"""<!doctype html><html><head><meta charset=utf-8>
    <style>html,body{{margin:0;background:#08080f}}</style></head>
    <body style="width:{S}px;height:{S}px;position:relative;overflow:hidden;
        background:radial-gradient(circle at 50% 46%,#151327,#08080f 70%);
        font-family:ui-monospace,Menlo,monospace;">
      {comets}{orbs}
      <div style="position:absolute;left:0;top:44px;width:{S}px;text-align:center;">
        <div style="color:#efeaff;font:700 40px ui-monospace;letter-spacing:1px;">Four agents communicating in activation space</div>
        <div style="color:#aaa5da;font:500 33px ui-monospace;margin-top:16px;letter-spacing:0.5px;line-height:1.35;">
          no words between them, just vectors:<br>
          read off the activations, pushed back in</div>
      </div>
      <div style="position:absolute;left:0;top:{S-138}px;width:{S}px;text-align:center;">
        {caption}
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
        # calm: collapse the static round-0 baseline to a single quick frame so the
        # seed lands almost immediately — a dead opening gets scrolled past
        ks = [args.sub - 1] if (rnd == 0 and args.calm) else range(args.sub)
        for k in ks:
            t = k / max(1, args.sub - 1)
            png = build / f"f{rnd:03d}_{k:02d}.png"
            shoot(frame_html(rnd, t), png)
            hold = FRAME_HOLD
            if k == args.sub - 1:
                # rounds 0-3 each carry a new story line — hold long enough to READ it;
                # after that the beats stop changing and the quick rhythm takes over
                if rnd == 0:
                    hold = 1.1 if args.calm else 0.5
                elif rnd in (1, 2, 3) and args.calm:
                    hold = 1.3
                elif rnd == 1:
                    hold = 0.6
                elif SETTLE:
                    hold = SETTLE                        # rest after every round
            frames.append((png, hold))
        print(f"round {rnd} rendered")
    frames.append((frames[-1][0], FINAL_HOLD))   # hold final

    concat = build / "frames.txt"
    lines = []
    for f, hold in frames:
        lines += [f"file '{f.name}'", f"duration {hold}"]
    lines.append(f"file '{frames[-1][0].name}'")
    concat.write_text("\n".join(lines) + "\n")

    out = ROOT / "docs"
    stem = "resonance-orbs-calm" if args.calm else "resonance-orbs"
    gif, mp4 = out / f"{stem}.gif", out / f"{stem}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-i", str(concat),
                    "-vf", f"fps={GIF_FPS},scale={GIF_SCALE}:-1:flags=lanczos,split[a][b];"
                           f"[a]palettegen=stats_mode=diff:max_colors={GIF_COLORS}[p];"
                           f"[b][p]paletteuse=dither=bayer:bayer_scale={GIF_BAYER}",
                    "-loop", "0", str(gif)], check=True, capture_output=True, cwd=build)
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-i", str(concat),
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "20",
                    str(mp4)], check=True, capture_output=True, cwd=build)
    print("->", gif)
    print("->", mp4)


if __name__ == "__main__":
    main()
