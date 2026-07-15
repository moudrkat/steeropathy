"""The mech-interp cut: each agent is its residual stream (L1 to L36), not an orb. A
steering vector injects at the L17-25 band, which lights up by how much of the feeling
that mind holds (purple = holds it, teal = drained negative). Steering vectors fly
between columns and land in the band. Conserved: it only changes hands.

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
W, H = 1560, 1040
Y36, Y1 = 300, 860                       # top of stack (L36) and bottom (L1)
COLH = Y1 - Y36
CW = 104                                  # column width
COLX = {a: round(W * (0.20 + 0.20 * i)) for i, a in enumerate(AG)}
def ylayer(L): return Y1 - (L - 1) / 35 * COLH
YB_top, YB_bot = ylayer(25), ylayer(17)   # steering band L17-25
BANDY = (YB_top + YB_bot) / 2

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
    x = COLX[a]
    bar = (f'<div style="position:absolute;left:{x-CW/2:.0f}px;top:{Y36}px;width:{CW}px;height:{COLH}px;'
           f'border-radius:12px;border:1px solid #23233c;'
           f'background:repeating-linear-gradient(0deg,transparent 0 15px,rgba(120,120,160,.09) 15px 16px),'
           f'linear-gradient(#161529,#0f0f1e);"></div>')
    bh = YB_bot - YB_top
    band = (f'<div style="position:absolute;left:{x-CW/2-7:.0f}px;top:{YB_top:.0f}px;width:{CW+14}px;height:{bh:.0f}px;'
            f'border-radius:9px;background:rgba({gc},{0.16+0.5*i:.2f});border:2px solid rgba({gc},{0.4+0.5*i:.2f});'
            f'box-shadow:0 0 {18+140*i:.0f}px {4+44*i:.0f}px rgba({gc},{0.18+0.55*i:.2f});"></div>')
    lbl = (f'<div style="position:absolute;left:{x-100:.0f}px;top:{Y1+20:.0f}px;width:200px;text-align:center;'
           f'font-family:ui-monospace,Menlo,monospace;">'
           f'<div style="color:#e8e4ff;font:700 25px ui-monospace;letter-spacing:2px;">{a}</div>'
           f'<div style="color:rgba({gc},{0.42+0.55*i:.2f});font:700 27px ui-monospace;margin-top:2px;">{n:+d}</div></div>')
    return bar + band + lbl


def comet(src, dst, t, pts):
    sx, dx = COLX[src], COLX[dst]
    x = lerp(sx, dx, t)
    sz = 12 + 22 * (pts / MAXPTS)
    parts = [f'<div style="position:absolute;left:{min(sx,dx):.0f}px;top:{BANDY-1:.0f}px;'
             f'width:{abs(dx-sx)*t:.0f}px;height:2px;{"left:%.0fpx;"%sx if dx>=sx else "left:%.0fpx;"%x}'
             f'background:linear-gradient(90deg,rgba(139,124,248,0),rgba(139,124,248,.28));"></div>']
    for j, tr in enumerate((0.0, 0.06, 0.12)):
        tt = max(0.0, t - tr); cx = lerp(sx, dx, tt); s = sz * (1 - j * 0.25); aa = 0.9 - j * 0.28
        parts.append(f'<div style="position:absolute;left:{cx-s/2:.0f}px;top:{BANDY-s/2:.0f}px;'
                     f'width:{s:.0f}px;height:{s:.0f}px;border-radius:50%;'
                     f'background:radial-gradient(circle,#f4f1ff,rgba(139,124,248,{aa:.2f}));'
                     f'box-shadow:0 0 {24*aa:.0f}px {7*aa:.0f}px rgba(139,124,248,{aa*0.7:.2f});"></div>')
    return "".join(parts)


def axis():
    out = []
    for L in (1, 17, 25, 36):
        y = ylayer(L)
        out.append(f'<div style="position:absolute;left:{COLX["NOVA"]-CW/2-70:.0f}px;top:{y-16:.0f}px;'
                   f'color:#5a5878;font:600 18px ui-monospace;width:56px;text-align:right;">L{L}</div>')
    out.append(f'<div style="position:absolute;left:{COLX["QUILL"]+CW/2+24:.0f}px;top:{BANDY-20:.0f}px;'
               f'color:#8a86b8;font:600 19px ui-monospace;width:230px;">◄ steer band<br>&nbsp;&nbsp;L17-25</div>')
    return "".join(out)


def frame_html(rnd, t):
    prev = max(0, rnd - 1)
    fr = {a: lerp(sad_read[(prev, a)], sad_read[(rnd, a)], t) / TOTAL for a in AG}
    cols = "".join(column(a, fr[a]) for a in AG)
    coms = "".join(comet(c["src"], c["dst"], t, c["pts"]) for c in touches[rnd])
    beat = ("seed vector injected at EMBER" if rnd == 1
            else "steering vectors propagate between residual streams" if rnd >= 2
            else "baseline, zero drift")
    return f"""<!doctype html><html><head><meta charset=utf-8><style>html,body{{margin:0;background:#08080f}}</style></head>
<body style="width:{W}px;height:{H}px;position:relative;overflow:hidden;
  background:radial-gradient(circle at 50% 44%,#141226,#08080f 74%);font-family:ui-monospace,Menlo,monospace;">
  <div style="position:absolute;left:0;top:40px;width:{W}px;text-align:center;color:#efeaff;font:700 38px ui-monospace;letter-spacing:1px;">
    four residual streams, one feeling moved between them</div>
  <div style="position:absolute;left:0;top:100px;width:{W}px;text-align:center;color:#9a96c8;font:400 22px ui-monospace;">
    each column is a mind, L1 to L36. a steering vector injects at the L17-25 band (lit = how much it holds). conserved.</div>
  {axis()}{coms}{cols}
  <div style="position:absolute;left:0;top:{H-58}px;width:{W}px;text-align:center;color:#b9b4e8;font-size:23px;letter-spacing:2px;">
    round {rnd} / {R} &nbsp;·&nbsp; {beat}</div>
</body></html>"""


def shoot(html, png):
    src = png.with_suffix(".html"); src.write_text(html)
    subprocess.run([args.chrome, "--headless=new", f"--window-size={W},{H}", f"--screenshot={png}",
                    "--hide-scrollbars", "--force-device-scale-factor=1", str(src)], check=True, capture_output=True)


def main():
    build = pathlib.Path(tempfile.mkdtemp(prefix="cols_"))
    frames = []
    for rnd in range(0, R + 1):
        for k in range(args.sub):
            t = k / max(1, args.sub - 1)
            png = build / f"f{rnd:03d}_{k:02d}.png"; shoot(frame_html(rnd, t), png)
            hold = 0.5 if (rnd in (0, 1) and k == args.sub - 1) else 1 / 13
            frames.append((png, hold))
        print(f"round {rnd}")
    frames.append((frames[-1][0], 2.2))
    concat = build / "f.txt"
    concat.write_text("\n".join(f"file '{f.name}'\nduration {h}" for f, h in frames) +
                      f"\nfile '{frames[-1][0].name}'\n")
    out = ROOT / "docs"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-i", str(concat),
                    "-vf", "fps=18,scale=620:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff:max_colors=128[p];"
                           "[b][p]paletteuse=dither=bayer:bayer_scale=4", "-loop", "0", str(out / "resonance-columns.gif")],
                   check=True, capture_output=True, cwd=build)
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-i", str(concat), "-vf", "fps=30,format=yuv420p",
                    "-c:v", "libx264", "-crf", "20", str(out / "resonance-columns.mp4")], check=True, capture_output=True, cwd=build)
    print("-> docs/resonance-columns.gif")


if __name__ == "__main__":
    main()
