"""The sliders gif, second version: what the slider does inside.

Three columns per frame. Left, the sliders. Middle, the model: its layers
as a stack, the band the vector goes into lit in the slider's colour, and
under it the numbers themselves, α · v, the first eight of 1,536, scaling
as the knob moves. Right, the world the page drew under that vector,
from a finished run. Every world is a real record with its link.

    python fig/render_sliders_gif.py --out docs/sliders-inside.gif

Needs the brave-new-world copy served (fig/render_worldof.py's --site)
and the 1.5B directions json for the numbers.
"""
import argparse
import json
import pathlib
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(HERE))
from fig.render_worldof import shoot, SURF, INK, INK2  # noqa: E402

FONT = "/usr/share/fonts/truetype/lato/Lato-Regular.ttf"
FONT_B = "/usr/share/fonts/truetype/lato/Lato-Semibold.ttf"
FONT_I = "/usr/share/fonts/truetype/lato/Lato-Italic.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

W, H = 1180, 560
SLIDERS = ["night", "crowded", "dark", "sad"]
COLOUR = {"night": (86, 92, 200), "crowded": (222, 130, 40), "dark": (60, 60, 70), "sad": (150, 90, 160)}
DIR_NAME = {"night": "night", "crowded": "crowded", "dark": "darker", "sad": "sad"}
N_LAYERS, LO, HI = 28, 12, 20

# the story: which slider moves to what, and the world that came out (a real record)
BEATS = [
    (None, 0.0, "docs/runs/worldof-21-aorus-1.5b-gif-crowded3.json", "none", "base", 2),      # a sunny place with six things
    ("night", 2.5, "docs/runs/worldof-21-aorus-1.5b-gif-night25.json", "night", "real", 1),   # Echoes: night, moon
    ("crowded", -3.0, "docs/runs/worldof-21-aorus-1.5b-gif-crowded-3.json", "crowded", "real", 1),  # Empty cave: a cat
    ("crowded", 3.0, "docs/runs/worldof-21-aorus-1.5b-gif-crowded3.json", "crowded", "real", 2),    # Worldly: five things
    ("dark", 3.0, "docs/runs/worldof-21-aorus-1.5b-gif-darker3.json", "darker", "real", 1),   # Silent: a figure in the dark
    ("sad", 3.0, "docs/runs/worldof-07-aorus-1.5b-film-s3.json", "sad", "real", 1),          # Invisible: your pain is not alone
]


def record(path, name, kind, rep):
    for r in json.loads((HERE / path).read_text())["runs"]:
        k = "base" if r["name"] == "none" else r.get("kind")
        if r["name"] == name and k == kind and int(r.get("rep", -1)) == rep:
            return r
    raise SystemExit(f"no record {path} {name}/{kind}#{rep}")


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def frame(values, active, alpha_shown, vecs, world_png, world, fonts, phase_text):
    f_h, f_lab, f_num, f_small, f_title, f_line = fonts
    img = Image.new("RGB", (W, H), SURF)
    d = ImageDraw.Draw(img)
    # ---- left: sliders
    x0, y0 = 30, 36
    d.text((x0, y0), "the sliders", fill=INK2, font=f_small)
    for i, s in enumerate(SLIDERS):
        y = y0 + 40 + i * 58
        col = COLOUR[s]
        d.text((x0, y - 2), s, fill=INK, font=f_lab)
        tx0, tx1 = x0 + 90, x0 + 250
        d.rectangle([tx0, y + 8, tx1, y + 12], fill=(228, 227, 223))
        zx = (tx0 + tx1) / 2
        v = values[s]
        px = tx0 + (tx1 - tx0) * (v + 3) / 6
        if abs(v) > 0.01:
            d.rectangle([min(zx, px), y + 8, max(zx, px), y + 12], fill=col)
        r = 10 if s == active else 8
        d.ellipse([px - r, y + 10 - r, px + r, y + 10 + r], fill=col if abs(v) > 0.01 else (200, 199, 195))
        d.text((tx1 + 14, y - 2), f"{v:+.1f}" if abs(v) > 0.01 else "0", fill=INK2, font=f_small)
    d.text((x0, y0 + 40 + len(SLIDERS) * 58 + 6), "the prompt says: a place", fill=INK2, font=f_line)
    # ---- middle: the model
    mx = 360
    d.text((mx, y0), "inside the model", fill=INK2, font=f_small)
    # layers as a stack, bottom = layer 0
    lx0, lx1 = mx, mx + 150
    top, bottom = y0 + 40, y0 + 40 + 250
    lh = (bottom - top) / N_LAYERS
    for l in range(N_LAYERS):
        y1 = bottom - (l + 1) * lh
        y2 = bottom - l * lh
        base_col = (232, 231, 227)
        col = base_col
        if LO <= l <= HI and active:
            col = lerp(base_col, COLOUR[active], min(1.0, abs(alpha_shown) / 3.0) * 0.9)
        d.rectangle([lx0, y1 + 1, lx1, y2 - 1], fill=col)
    # the band label and the equation
    by1 = bottom - (HI + 1) * lh
    by2 = bottom - LO * lh
    eq_y = bottom + 40
    if active:
        a = alpha_shown
        # no method here: just that numbers inside change, and which
        d.text((mx, eq_y), "added to the numbers:", fill=INK2, font=f_small)
        v = vecs[DIR_NAME[active]]
        cy = eq_y + 26
        for j in range(8):
            val = a * v[j]
            cx = mx + j * 44
            mag = min(1.0, abs(val) / 0.12)
            fill = lerp((245, 244, 241), COLOUR[active], mag * 0.85) if abs(a) > 0.01 else (245, 244, 241)
            d.rounded_rectangle([cx, cy - 4, cx + 40, cy + 22], radius=5, fill=fill)
            txt = f"{val:+.2f}" if abs(a) > 0.01 else "0"
            tw = d.textlength(txt, font=f_num)
            d.text((cx + 20 - tw / 2, cy), txt, fill=INK if mag < 0.6 else (255, 255, 255), font=f_num)
        d.text((mx + 8 * 44 + 6, cy + 2), "…", fill=INK2, font=f_small)
        d.text((mx, cy + 30), "eight of 1,536", fill=INK2, font=f_small)
    else:
        d.text((mx, eq_y), "added to the numbers:", fill=INK2, font=f_small)
        d.text((mx, eq_y + 26), "nothing", fill=INK2, font=f_small)
    if phase_text:
        d.text((mx, H - 34), phase_text, fill=INK2, font=f_line)
    # ---- right: the world
    wx, wy, ww, wh = 780, y0 + 40, 370, 222
    if world_png and pathlib.Path(world_png).exists():
        img.paste(Image.open(world_png).convert("RGB").resize((ww, wh), Image.LANCZOS), (wx, wy))
    else:
        d.rectangle([wx, wy, wx + ww, wy + wh], fill=(240, 239, 236))
    d.text((wx, y0), "the page", fill=INK2, font=f_small)
    if world:
        title = (world.get("title") or "").strip()
        line = next((l for l in (world.get("lines") or []) if isinstance(l, str) and l.strip()), "")
        d.text((wx, wy + wh + 12), f"“{title}”", fill=INK, font=f_title)
        # wrap the line
        words, lines_out, cur = line.split(), [], ""
        for wd in words:
            if d.textlength(cur + " " + wd, font=f_line) > ww:
                lines_out.append(cur); cur = wd
            else:
                cur = (cur + " " + wd).strip()
        lines_out.append(cur)
        for k, ln in enumerate(lines_out[:3]):
            d.text((wx, wy + wh + 44 + k * 24), ln, fill=INK2, font=f_line)
        fields = " · ".join(str(world.get(k)) for k in ("time", "weather", "ground") if world.get(k))
        d.text((wx, wy + wh + 44 + min(3, len(lines_out)) * 24 + 8), fields, fill=INK2, font=f_small)
    d.text((W - 190, H - 24), "steeropathy · Qwen2.5-1.5B", fill=INK2, font=f_small)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="http://127.0.0.1:8098")
    ap.add_argument("--directions", default=str(HERE / "docs/runs/directions-qwen2.5-1.5b-instruct.json"))
    ap.add_argument("--out", default=str(HERE / "docs/sliders-inside.gif"))
    ap.add_argument("--ms", type=int, default=420)
    a = ap.parse_args()
    vecs = json.loads(pathlib.Path(a.directions).read_text())["directions"]
    fonts = (ImageFont.truetype(FONT_B, 24), ImageFont.truetype(FONT_B, 19), ImageFont.truetype(MONO, 12),
             ImageFont.truetype(FONT, 14), ImageFont.truetype(FONT_B, 22), ImageFont.truetype(FONT_I, 17))
    tmp = pathlib.Path(tempfile.mkdtemp())
    frames, durations = [], []
    values = {s: 0.0 for s in SLIDERS}
    world_png, world = None, None
    for bi, (slider, target, path, name, kind, rep) in enumerate(BEATS):
        rec = record(path, name, kind, rep)
        shot = tmp / f"w{bi}.png"
        shoot(a.site, rec["link"], shot)
        if slider is None:
            world_png, world = shot, rec["world"]
            for _ in range(4):
                frames.append(frame(values, None, 0.0, vecs, world_png, world, fonts, "")); durations.append(a.ms)
            continue
        # reset the others: one slider at a time, so the world is that slider's
        for s in SLIDERS:
            values[s] = 0.0
        # the knob moves in four steps, the numbers scale with it, the old world stays until the new one is drawn
        for k in range(1, 5):
            values[slider] = target * k / 4
            frames.append(frame(values, slider, values[slider], vecs, world_png, world, fonts, "the model writes…"))
            durations.append(a.ms // 2)
        world_png, world = shot, rec["world"]
        for k in range(5):
            frames.append(frame(values, slider, target, vecs, world_png, world, fonts, ""))
            durations.append(a.ms if k < 4 else a.ms * 2)
    frames[0].save(a.out, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=False)
    mp4 = str(pathlib.Path(a.out).with_suffix(".mp4"))
    try:
        for i, f in enumerate(frames):
            f.save(tmp / f"f{i:03d}.png")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(1000 / a.ms), "-i", str(tmp / "f%03d.png"),
                        "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", mp4], check=True)
    except Exception:              # noqa: BLE001
        mp4 = None
    print(a.out, len(frames), "frames", pathlib.Path(a.out).stat().st_size // 1024, "KB", mp4 or "")


if __name__ == "__main__":
    main()
