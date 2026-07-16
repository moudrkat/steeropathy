"""The mech-interp cut, in a ring so you see who affects whom (like the orbs). Each
agent is its residual stream (L1 to L36). A steering vector injects at the L17-25
band (brightest), and the effect is CARRIED UPWARD through the layers above it, so the
glow fades from the band up to L36. Purple = holds the feeling, teal = drained
negative. Vectors fly between streams. Conserved.

    python fig/render_columns.py [--json docs/resonance.json] [--sub 5]
    -> docs/resonance-columns.gif , .mp4
"""
from __future__ import annotations
import argparse, json, math, pathlib, subprocess, tempfile

HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parent
ap = argparse.ArgumentParser()
ap.add_argument("--json", default=str(ROOT / "docs" / "resonance.json"))
ap.add_argument("--sub", type=int, default=5)
ap.add_argument("--chrome", default="google-chrome")
args = ap.parse_args()

AG = ["NOVA", "EMBER", "ATLAS", "QUILL"]
S = 1220
C = S / 2
ORBIT = S * 0.238
COLH, CW = 306, 70                        # mini residual column: height, width
POS = {"NOVA": (C, C - ORBIT), "EMBER": (C + ORBIT, C),
       "ATLAS": (C, C + ORBIT), "QUILL": (C - ORBIT, C)}

run = json.load(open(args.json)); log = run["log"]
R = max(r["round"] for r in log)
sad_read = {(r["round"], r["agent"]): r.get("ledger_sad", 0.0) for r in log}
touches = {rnd: [] for rnd in range(R + 1)}
for r in log:
    t = r.get("touch")
    if not t: continue
    giver, target = r["agent"], t["target"]
    src, dst = (giver, target) if t["feeling"] == "give" else (target, giver)
    touches[r["round"]].append({"src": src, "dst": dst, "pts": t.get("points") or 10})
MAXPTS = max((t["pts"] for ts in touches.values() for t in ts), default=30)
TOTAL = sum(sad_read.get((1, a), 0.0) for a in AG) or 1e-6

COOL, HOT, TEAL = (108, 112, 150), (188, 132, 255), (86, 222, 190)
def lerp(a, b, t): return a + (b - a) * t
def mix(c0, c1, t): return tuple(round(lerp(a, b, t)) for a, b in zip(c0, c1))


def column(a, frac):
    i = min(1.0, abs(frac)); n = round(100 * frac)
    g = mix(COOL, HOT if frac >= 0 else TEAL, i); gc = f"{g[0]},{g[1]},{g[2]}"
    px, py = POS[a]
    top, bot = py - COLH / 2, py + COLH / 2                 # L36 top, L1 bottom
    def yL(L): return bot - (L - 1) / 35 * COLH
    yb_t, yb_b = yL(25), yL(17)                             # steer band edges
    x = px - CW / 2
    bar = (f'<div style="position:absolute;left:{x:.0f}px;top:{top:.0f}px;width:{CW}px;height:{COLH}px;'
           f'border-radius:9px;border:1px solid #23233c;'
           f'background:repeating-linear-gradient(0deg,transparent 0 9px,rgba(120,120,160,.10) 9px 10px),'
           f'linear-gradient(#161529,#0f0f1e);"></div>')
    # effect carried upward: from the band up to L36, fading but never quite gone
    carry = (f'<div style="position:absolute;left:{x:.0f}px;top:{top:.0f}px;width:{CW}px;height:{yb_b-top:.0f}px;'
             f'border-radius:9px 9px 0 0;'
             f'background:linear-gradient(to top,rgba({gc},{0.52*i:.2f}),rgba({gc},{0.12*i:.2f}));"></div>')
    # the injection band L17-25 (brightest)
    band = (f'<div style="position:absolute;left:{x-6:.0f}px;top:{yb_t:.0f}px;width:{CW+12}px;height:{yb_b-yb_t:.0f}px;'
            f'border-radius:7px;background:rgba({gc},{0.18+0.5*i:.2f});border:2px solid rgba({gc},{0.4+0.5*i:.2f});'
            f'box-shadow:0 0 {16+130*i:.0f}px {3+40*i:.0f}px rgba({gc},{0.18+0.55*i:.2f});"></div>')
    lbl = (f'<div style="position:absolute;left:{px-100:.0f}px;top:{bot+12:.0f}px;width:200px;text-align:center;'
           f'font-family:ui-monospace,Menlo,monospace;">'
           f'<div style="color:#e8e4ff;font:700 23px ui-monospace;letter-spacing:2px;">{a}</div>'
           f'<div style="color:rgba({gc},{0.42+0.55*i:.2f});font:700 25px ui-monospace;">{n:+d}</div></div>')
    return bar + carry + band + lbl


def comet(src, dst, t, pts):
    sx, sy = POS[src]; dx, dy = POS[dst]
    x, y = lerp(sx, dx, t), lerp(sy, dy, t)
    sz = 11 + 20 * (pts / MAXPTS)
    ang = math.degrees(math.atan2(dy - sy, dx - sx)); ln = math.hypot(dx - sx, dy - sy) * t
    parts = [f'<div style="position:absolute;left:{sx:.0f}px;top:{sy:.0f}px;width:{ln:.0f}px;height:2px;'
             f'transform-origin:0 50%;transform:rotate({ang:.1f}deg);'
             f'background:linear-gradient(90deg,rgba(139,124,248,0),rgba(139,124,248,.26));"></div>']
    for j, tr in enumerate((0.0, 0.06, 0.12)):
        tt = max(0.0, t - tr); cx, cy = lerp(sx, dx, tt), lerp(sy, dy, tt); s = sz * (1 - j * 0.25); aa = 0.9 - j * 0.28
        parts.append(f'<div style="position:absolute;left:{cx-s/2:.0f}px;top:{cy-s/2:.0f}px;width:{s:.0f}px;height:{s:.0f}px;'
                     f'border-radius:50%;background:radial-gradient(circle,#f4f1ff,rgba(139,124,248,{aa:.2f}));'
                     f'box-shadow:0 0 {22*aa:.0f}px {6*aa:.0f}px rgba(139,124,248,{aa*0.7:.2f});"></div>')
    return "".join(parts)


def frame_html(rnd, t):
    prev = max(0, rnd - 1)
    fr = {a: lerp(sad_read[(prev, a)], sad_read[(rnd, a)], t) / TOTAL for a in AG}
    coms = "".join(comet(c["src"], c["dst"], t, c["pts"]) for c in touches[rnd])
    cols = "".join(column(a, fr[a]) for a in AG)
    beat = ("seed vector injected at EMBER" if rnd == 1
            else "steering vectors propagate between residual streams" if rnd >= 2
            else "baseline, zero drift")
    # tiny layer legend near NOVA's column
    lx, lt = POS["NOVA"][0] - CW / 2 - 66, POS["NOVA"][1] - COLH / 2
    legend = "".join(
        f'<div style="position:absolute;left:{lx:.0f}px;top:{POS["NOVA"][1]-COLH/2 + (35-L)/35*COLH - 14:.0f}px;'
        f'color:#5a5878;font:600 16px ui-monospace;width:52px;text-align:right;">L{L}</div>'
        for L in (1, 17, 25, 36))
    return f"""<!doctype html><html><head><meta charset=utf-8><style>html,body{{margin:0;background:#08080f}}</style></head>
<body style="width:{S}px;height:{S}px;position:relative;overflow:hidden;
  background:radial-gradient(circle at 50% 47%,#141226,#08080f 74%);font-family:ui-monospace,Menlo,monospace;">
  <div style="position:absolute;left:0;top:34px;width:{S}px;text-align:center;color:#efeaff;font:700 34px ui-monospace;letter-spacing:1px;">
    four residual streams, one feeling moved between them</div>
  <div style="position:absolute;left:0;top:88px;width:{S}px;text-align:center;color:#9a96c8;font:400 20px ui-monospace;line-height:1.4;">
    each is a mind, L1 to L36. a steering vector adds in at the L17-25 band; the residual stream carries it up.<br>value = its share of the seed feeling (conserved, sums to the seed), teal = pushed below baseline.</div>
  {legend}{coms}{cols}
  <div style="position:absolute;left:0;top:{S-52}px;width:{S}px;text-align:center;color:#b9b4e8;font-size:22px;letter-spacing:2px;">
    round {rnd} / {R} &nbsp;·&nbsp; {beat}</div>
</body></html>"""


def shoot(html, png):
    src = png.with_suffix(".html"); src.write_text(html)
    subprocess.run([args.chrome, "--headless=new", f"--window-size={S},{S}", f"--screenshot={png}",
                    "--hide-scrollbars", "--force-device-scale-factor=1", str(src)], check=True, capture_output=True)


def main():
    build = pathlib.Path(tempfile.mkdtemp(prefix="cols_"))
    frames = []
    for rnd in range(0, R + 1):
        for k in range(args.sub):
            tt = k / max(1, args.sub - 1)
            png = build / f"f{rnd:03d}_{k:02d}.png"; shoot(frame_html(rnd, tt), png)
            hold = 0.5 if (rnd in (0, 1) and k == args.sub - 1) else 1 / 13
            frames.append((png, hold))
        print(f"round {rnd}")
    frames.append((frames[-1][0], 2.2))
    concat = build / "f.txt"
    concat.write_text("\n".join(f"file '{f.name}'\nduration {h}" for f, h in frames) +
                      f"\nfile '{frames[-1][0].name}'\n")
    out = ROOT / "docs"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-i", str(concat),
                    "-vf", "fps=18,scale=600:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff:max_colors=128[p];"
                           "[b][p]paletteuse=dither=bayer:bayer_scale=4", "-loop", "0", str(out / "resonance-columns.gif")],
                   check=True, capture_output=True, cwd=build)
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-i", str(concat), "-vf", "fps=30,format=yuv420p",
                    "-c:v", "libx264", "-crf", "20", str(out / "resonance-columns.mp4")], check=True, capture_output=True, cwd=build)
    print("-> docs/resonance-columns.gif")


if __name__ == "__main__":
    main()
