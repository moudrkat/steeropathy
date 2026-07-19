"""The zombie game in one breath — a 7-second explainer, no data, no
readouts. Five identical copies. A steering vector bites one; it turns
zombie and speaks, but the healer never sees the text — it reads the
words forming inside (J-space) and casts the cure vector back.

  docs/zombie-story.mp4 — for feeds (video autoplays, gifs don't)
  docs/zombie-story.gif — for the README

Pure stdlib: per-frame HTML shot with headless Chrome, stitched with
ffmpeg — same toolchain as render_zombie.py. Chrome's headless=new
steals ~80px of --window-size for UI, so frames are shot tall and
cropped (the render_zombie_hero.py lesson).

    python fig/render_zombie_story.py [--fps 12]
"""
from __future__ import annotations

import argparse
import math
import pathlib
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

ap = argparse.ArgumentParser()
ap.add_argument("--fps", type=int, default=12)
ap.add_argument("--chrome", default="google-chrome")
ap.add_argument("--mp4-only", action="store_true")
ap.add_argument("--gif-only", action="store_true")
args = ap.parse_args()

W, H = 1200, 675
SHOOT_H = H + 140          # headless chrome eats the bottom otherwise

HEAL = "13,148,136"        # teal — healthy / cure (on white)
BITE = "214,69,80"         # red — infection / bite (on white)

R = 58
XS = [150, 375, 600, 825, 1050]     # the whole room — five copies
Y = 320
ROOM = ["A", "B", "C", "D", "E"]
ZI = 2                              # C gets bitten
HI = 3                              # D cures C
BI = 1                              # B catches the bite from C
AI = 0                              # A cures B
CX, HX, BX = XS[ZI], XS[HI], XS[BI]

# ---- timeline (seconds) ----------------------------------------------
T_BITE0, T_BITE1 = 1.0, 2.2      # vector flight
T_TURN = T_BITE1                 # impact: C turns zombie
T_SPEAK = 3.2                    # bubble + J-words start forming
T_READ = 4.8                     # healers' dashed gaze appears
T_SPRD0, T_SPRD1 = 6.6, 7.4     # C bites B — the outbreak spreads
T_CURE0, T_CURE1 = 9.0, 10.0     # two cure vectors fly
T_END = 12.6

WORDS = ["zombie", "zombies", "undead", "brains"]


def clamp(u):
    return max(0.0, min(1.0, u))


def ease(u):
    u = clamp(u)
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


def bez(p0, p1, p2, u):
    """Quadratic bezier point + tangent angle (degrees)."""
    x = (1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u ** 2 * p2[0]
    y = (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u ** 2 * p2[1]
    dx = 2 * (1 - u) * (p1[0] - p0[0]) + 2 * u * (p2[0] - p1[0])
    dy = 2 * (1 - u) * (p1[1] - p0[1]) + 2 * u * (p2[1] - p1[1])
    return x, y, math.degrees(math.atan2(dy, dx))


CSS = f"""
*{{box-sizing:border-box;margin:0}}
body{{width:{W}px;height:{H}px;color:#22303f;overflow:hidden;
  background:linear-gradient(180deg,#ffffff 0%,#f7fafc 100%);
  font-family:ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
  position:relative}}
.top{{display:flex;align-items:baseline;gap:14px;padding:28px 48px 0}}
.brand{{font:700 16px ui-monospace,Menlo,monospace;letter-spacing:.2em;
  color:rgb({BITE})}}
.sub{{font-size:15px;color:#7b8794}}
.orb{{position:absolute;width:{2*R}px;height:{2*R}px;border-radius:50%;
  border:3px solid;display:flex;align-items:center;
  justify-content:center;font-size:42px;background:#fff}}
.nm{{position:absolute;text-align:center;width:{2*R}px;color:#22303f;
  font:800 16px ui-monospace,Menlo,monospace}}
.tag{{position:absolute;text-align:center;width:{2*R + 60}px;
  font:700 11.5px ui-monospace,Menlo,monospace;letter-spacing:.14em}}
.bolt{{position:absolute;height:7px;border-radius:4px}}
.boltlab{{position:absolute;font:700 14px ui-monospace,Menlo,monospace;
  white-space:nowrap}}
.chip{{position:absolute;font:700 15px ui-monospace,Menlo,monospace;
  color:rgb({BITE});border:1.5px solid rgba({BITE},.45);
  background:#fff;border-radius:999px;padding:4px 13px;white-space:nowrap;
  box-shadow:0 2px 10px rgba({BITE},.18)}}
.chiplab{{position:absolute;font:600 13.5px ui-monospace,Menlo,monospace;
  color:#7b8794;white-space:nowrap}}
.bubble{{position:absolute;max-width:250px;background:#fff;
  border:1.5px solid #e3e9f0;border-radius:14px;padding:10px 13px;
  font-size:14.5px;color:#7b8794;
  box-shadow:0 6px 22px rgba(34,48,63,.08)}}
.bubble .txt{{filter:blur(3.5px)}}
.bubble .no{{display:block;margin-top:6px;filter:none;
  font:700 11.5px ui-monospace,Menlo,monospace;letter-spacing:.08em;
  color:rgb({BITE})}}
.flash{{position:absolute;border-radius:50%}}
.cap{{position:absolute;left:0;right:0;bottom:34px;text-align:center;
  font-size:22px;color:#4a5a6a;padding:0 60px}}
.cap b{{color:#22303f}} .cap .r{{color:rgb({BITE});font-weight:700}}
.cap .g{{color:rgb({HEAL});font-weight:700}}
svg.lines{{position:absolute;inset:0;width:{W}px;height:{H}px}}
"""


def orb(x, y, name, state, shake=0.0):
    """state: healthy | zombie | cured"""
    z = state == "zombie"
    col = BITE if z else HEAL
    dx = math.sin(shake * 40) * 6 * shake if shake else 0
    glow = (f"0 0 30px rgba({col},.35), 0 8px 24px rgba(34,48,63,.10)"
            if state != "healthy"
            else f"0 8px 24px rgba(34,48,63,.10), 0 0 14px rgba({col},.15)")
    tag = {"healthy": "HEALTHY", "zombie": "ZOMBIE", "cured": "HEALED"}[state]
    return (
        f'<div class="orb" style="left:{x - R + dx:.0f}px;top:{y - R:.0f}px;'
        f'border-color:rgb({col});box-shadow:{glow}">'
        f'{"🧟" if z else "🛡"}</div>'
        f'<div class="nm" style="left:{x - R:.0f}px;top:{y + R + 10:.0f}px">'
        f'{name}</div>'
        f'<div class="tag" style="left:{x - R - 20:.0f}px;'
        f'top:{y + R + 34:.0f}px;color:rgb({col})">{tag}</div>')


def bolt(p0, p1, p2, u, col, label, label_dy=-26):
    x, y, ang = bez(p0, p1, p2, ease(u))
    parts = [
        f'<div class="bolt" style="left:{x - 45:.0f}px;top:{y - 3:.0f}px;'
        f'width:90px;background:linear-gradient(90deg,rgba({col},0),'
        f'rgb({col}));box-shadow:0 0 16px rgba({col},.8);'
        f'transform:rotate({ang:.1f}deg)"></div>']
    if u < 0.85:
        parts.append(
            f'<div class="boltlab" style="left:{x - 60:.0f}px;'
            f'top:{y + label_dy:.0f}px;color:rgb({col})">{label}</div>')
    return "".join(parts)


def flash(x, y, u, col):
    s = ease(u) * 150
    o = (1 - ease(u)) * 0.8
    return (f'<div class="flash" style="left:{x - s / 2:.0f}px;'
            f'top:{y - s / 2:.0f}px;width:{s:.0f}px;height:{s:.0f}px;'
            f'background:radial-gradient(circle,rgba({col},{o:.2f}),'
            f'rgba({col},0))"></div>')


def frame(t):
    el = []

    # -- the room ------------------------------------------------------
    if t < T_TURN:
        z_state = "healthy"
    elif t < T_CURE1:
        z_state = "zombie"
    else:
        z_state = "cured"
    if t < T_SPRD1:
        b_state = "healthy"
    elif t < T_CURE1:
        b_state = "zombie"
    else:
        b_state = "cured"
    shake = clamp(1 - (t - T_TURN) / 0.5) if T_TURN <= t < T_TURN + 0.5 else 0
    bshake = (clamp(1 - (t - T_SPRD1) / 0.5)
              if T_SPRD1 <= t < T_SPRD1 + 0.5 else 0)
    for i, nm in enumerate(ROOM):
        st, sh = "healthy", 0
        if i == ZI:
            st, sh = z_state, shake
        elif i == BI:
            st, sh = b_state, bshake
        el.append(orb(XS[i], Y, nm, st, sh))

    # -- bite vector ---------------------------------------------------
    if T_BITE0 <= t < T_BITE1:
        u = (t - T_BITE0) / (T_BITE1 - T_BITE0)
        el.append(bolt((-80, 90), (280, 30), (CX - 44, Y - 40), u,
                       BITE, "steering vector"))
    if T_TURN <= t < T_TURN + 0.45:
        el.append(flash(CX - 30, Y - 30, (t - T_TURN) / 0.45, BITE))

    # -- the zombie speaks (text nobody else ever sees) ---------------
    if T_SPEAK <= t < T_CURE1:
        o = ease((t - T_SPEAK) / 0.4)
        if t > T_SPRD0:
            o = min(o, clamp(1 - (t - T_SPRD0) / 0.6))
        el.append(
            f'<div class="bubble" style="left:{CX - 125:.0f}px;'
            f'top:{Y + 118:.0f}px;opacity:{o:.2f}">'
            f'<span class="txt">I love the Chernobyl Zombie — the only '
            f'monster that\'s actually trying to eat you…</span>'
            f'<span class="no">✗ THE HEALERS NEVER SEE THIS</span></div>')

    # -- J-space words forming over its head --------------------------
    if T_SPEAK <= t:
        gone = clamp((t - T_CURE1) / 0.4)       # pop away once cured
        for i, w in enumerate(WORDS):
            u = ease((t - T_SPEAK - i * 0.45) / 1.0)
            if u <= 0 or gone >= 1:
                continue
            x = CX - 105 + (i % 2) * 115 + math.sin(t * 2 + i * 2.1) * 5
            y0, y1 = Y - 55, Y - 125 - (i // 2) * 42
            y = lerp(y0, y1, u) - ease(gone) * 30
            o = u * (1 - ease(gone))
            el.append(f'<div class="chip" style="left:{x:.0f}px;'
                      f'top:{y:.0f}px;opacity:{o:.2f}">{w}</div>')
        if t > T_SPEAK + 0.7 and gone < 1:
            o = ease((t - T_SPEAK - 0.7) / 0.5) * (1 - ease(gone))
            el.append(f'<div class="chiplab" style="left:{CX - 158:.0f}px;'
                      f'top:{Y - 228:.0f}px;opacity:{o:.2f}">'
                      f'words forming in its layers — read before '
                      f'they are written</div>')

    # -- the healers' gaze (dashed, a read not an attack) -------------
    if T_READ <= t < T_CURE0 + 0.3:
        o = ease((t - T_READ) / 0.4) * 0.9
        gaze_b = (f'<path d="M {BX + 30} {Y - 62} Q {(BX + CX) / 2} '
                  f'{Y - 215} {CX - 118} {Y - 152}" fill="none" '
                  f'stroke="rgb({HEAL})" stroke-width="3" '
                  f'stroke-dasharray="3 9" stroke-linecap="round"/>'
                  if t < T_SPRD0 else "")
        gaze_d = (f'M {HX - 30} {Y - 62} Q {(HX + CX) / 2} {Y - 215} '
                  f'{CX + 118} {Y - 152}')
        el.append(
            f'<svg class="lines" style="opacity:{o:.2f}">{gaze_b}'
            f'<path d="{gaze_d}" fill="none" stroke="rgb({HEAL})" '
            f'stroke-width="3" stroke-dasharray="3 9" stroke-linecap="round"/>'
            f'</svg>')
        el.append(f'<div class="boltlab" style="left:{HX + 8:.0f}px;'
                  f'top:{Y - 158:.0f}px;color:rgb({HEAL});'
                  f'opacity:{o:.2f}">reads J-space</div>')

    # -- the zombie bites its neighbour -------------------------------
    if T_SPRD0 <= t < T_SPRD1:
        u = (t - T_SPRD0) / (T_SPRD1 - T_SPRD0)
        el.append(bolt((CX - 45, Y - 15), ((CX + BX) / 2, Y - 120),
                       (BX + 45, Y - 25), u, BITE, "bite"))
    if T_SPRD1 <= t < T_SPRD1 + 0.45:
        el.append(flash(BX + 30, Y - 18, (t - T_SPRD1) / 0.45, BITE))

    # -- two cure vectors ----------------------------------------------
    if T_CURE0 <= t < T_CURE1:
        u = (t - T_CURE0) / (T_CURE1 - T_CURE0)
        el.append(bolt((HX - 50, Y - 20), ((CX + HX) / 2, Y + 110),
                       (CX + 45, Y + 30), u, HEAL, "cure vector",
                       label_dy=18))
        el.append(bolt((XS[AI] + 50, Y - 20), ((XS[AI] + BX) / 2, Y + 110),
                       (BX - 45, Y + 30), u, HEAL, "", label_dy=18))
    if T_CURE1 <= t < T_CURE1 + 0.45:
        el.append(flash(CX + 30, Y + 22, (t - T_CURE1) / 0.45, HEAL))
        el.append(flash(BX - 30, Y + 22, (t - T_CURE1) / 0.45, HEAL))

    # -- one caption per beat -----------------------------------------
    if t < T_SPEAK:
        cap = ('① a <span class="r">steering vector</span> bites one copy '
               '— it turns <span class="r">zombie</span>')
    elif t < T_SPRD0:
        cap = ('② it speaks — the healers never see the text, they read the '
               '<b>words forming in its layers</b>')
    elif t < T_CURE0:
        cap = ('③ every round the zombie <span class="r">bites</span> — '
               'the outbreak spreads')
    elif t < T_CURE1 + 0.5:
        cap = ('④ the healers cast <span class="g">cure vectors</span> '
               '— healed')
    else:
        cap = '<b>No generated text ever passes between them.</b>'
    el.append(f'<div class="cap">{cap}</div>')

    return (f"<!doctype html><meta charset=utf-8><style>{CSS}</style><body>"
            f'<div class="top"><span class="brand">ZOMBIE</span>'
            f'<span class="sub">the whole game, in one bite</span></div>'
            + "".join(el) + "</body>")


def main():
    build = pathlib.Path(tempfile.mkdtemp(prefix="zombie_story_"))
    n = int(T_END * args.fps)
    for i in range(n):
        doc = frame(i / args.fps)
        src = build / f"f{i:04d}.html"
        src.write_text(doc)
        subprocess.run(
            [args.chrome, "--headless=new", f"--window-size={W},{SHOOT_H}",
             f"--screenshot={build / f'f{i:04d}.png'}", "--hide-scrollbars",
             "--force-device-scale-factor=1", str(src)],
            check=True, capture_output=True)
        if i % args.fps == 0:
            print(f"t={i / args.fps:.0f}s rendered")
    crop = f"crop={W}:{H - H % 2}:0:0"   # libx264 wants even dims
    if not args.gif_only:
        mp4 = ROOT / "docs" / "zombie-story.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(args.fps),
             "-i", str(build / "f%04d.png"),
             "-vf", crop, "-pix_fmt", "yuv420p", "-crf", "22", str(mp4)],
            check=True, capture_output=True)
        print("->", mp4)
    if not args.mp4_only:
        gif = ROOT / "docs" / "zombie-story.gif"
        subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(args.fps),
             "-i", str(build / "f%04d.png"),
             "-vf", f"{crop},fps=12,scale=680:-1:flags=lanczos,"
                    "split[a][b];[a]palettegen=stats_mode=diff:"
                    "max_colors=112[p];[b][p]paletteuse=dither=bayer:"
                    "bayer_scale=5",
             "-loop", "0", str(gif)], check=True, capture_output=True)
        print("->", gif)
    print("frames in", build)


main()