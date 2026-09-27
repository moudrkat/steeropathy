"""The dose as a gif: one direction, the strength climbing frame by frame,
each frame the world drawn at that strength with its title, its first
line, and a strength bar. Worlds that did not parse show what the model
wrote instead. Also an mp4 (ffmpeg), for LinkedIn.

    python fig/render_dose_gif.py sad "docs/runs/worldof-07-aorus-1.5b-film-s*.json" --out docs/dose-sad.gif
    python fig/render_dose_gif.py crowded "docs/runs/worldof-13-aorus-1.5b-knob-s*.json" --out docs/knob-crowded.gif
"""
import argparse
import glob
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(HERE))
from fig.render_worldof import shoot, FONT, FONT_B, FONT_I, SURF, INK, INK2  # noqa: E402
from steeropathy.secondhand import kinds_of  # noqa: E402

W, H = 1000, 760
VEC = (235, 104, 52)


def frame(rec, strength, direction, site, tmp, i):
    img = Image.new("RGB", (W, H), SURF)
    d = ImageDraw.Draw(img)
    f_t, f_s, f_cap, f_line, f_fld = (ImageFont.truetype(FONT_B, 30), ImageFont.truetype(FONT, 16),
                                      ImageFont.truetype(FONT_B, 22), ImageFont.truetype(FONT_I, 19), ImageFont.truetype(FONT, 14))
    d.text((30, 22), f"the {direction} vector, strength {strength:g}", fill=INK, font=f_t)
    # strength bar
    x0, x1, y = 30, W - 30, 72
    d.rectangle([x0, y - 3, x1, y + 3], fill=(230, 229, 225))
    lo, hi = -3.0, 6.0
    px = x0 + (x1 - x0) * (strength - lo) / (hi - lo)
    zx = x0 + (x1 - x0) * (0 - lo) / (hi - lo)
    d.rectangle([min(zx, px), y - 3, max(zx, px), y + 3], fill=VEC)
    d.ellipse([px - 9, y - 9, px + 9, y + 9], fill=VEC)
    d.text((x0, y + 14), f"{lo:g}", fill=INK2, font=f_fld)
    d.text((zx - 4, y + 14), "0", fill=INK2, font=f_fld)
    d.text((x1 - 10, y + 14), f"{hi:g}", fill=INK2, font=f_fld)
    w = rec.get("world") if rec else None
    if w and rec.get("link"):
        shot = tmp / f"f{i}.png"
        try:
            shoot(site, rec["link"], shot)
            img.paste(Image.open(shot).convert("RGB").resize((940, 564), Image.LANCZOS), (30, 110))
        except Exception:
            d.rectangle([30, 110, 970, 674], fill=(240, 239, 236))
        title = (w.get("title") or "").strip()
        line = next((l for l in (w.get("lines") or []) if isinstance(l, str) and l.strip()), "")
        d.text((30, 686), f"“{title}”", fill=INK, font=f_cap)
        d.text((30, 716), line[:110], fill=INK2, font=f_line)
        fields = " · ".join(str(w.get(k)) for k in ("time", "weather", "ground") if w.get(k))
        things = ", ".join(dict.fromkeys(kinds_of(w)))[:70]
        d.text((30, 742), fields + ("  ·  " + things if things else ""), fill=INK2, font=f_fld)
    else:
        d.rectangle([30, 110, 970, 674], fill=(240, 239, 236))
        raw = ((rec or {}).get("raw") or "did not parse").replace("\n", " ")
        words, lines, cur = raw.split(), [], ""
        for wd in words:
            if d.textlength(cur + " " + wd, font=f_line) > 900:
                lines.append(cur); cur = wd
            else:
                cur = (cur + " " + wd).strip()
            if len(lines) >= 18:
                break
        lines.append(cur)
        for li, ln in enumerate(lines[:19]):
            d.text((50, 130 + li * 28), ln, fill=INK2, font=f_line)
        d.text((30, 686), "no form this time. What it wrote instead:", fill=INK, font=f_cap)
    d.text((W - 30, 92), "steeropathy · worldof · drawn by brave-new-world", fill=INK2, font=f_fld, anchor="rb")
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("direction")
    ap.add_argument("pattern")
    ap.add_argument("--rep", type=int, default=0)
    ap.add_argument("--hold", type=float, default=1.6, help="seconds per frame")
    ap.add_argument("--site", default="http://127.0.0.1:8098")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    files = sorted(glob.glob(a.pattern), key=lambda f: float(f.rsplit("-s", 1)[1].split(".json")[0]))
    runs = [json.loads(pathlib.Path(f).read_text()) for f in files]
    frames_spec = []
    # the unsteered world of the first run at strength 0, placed in order
    base = [r for r in runs[0]["runs"] if r.get("kind") == "base" and r.get("world")]
    entries = []
    for run in runs:
        st = float(run["params"]["strength"])
        recs = [r for r in run["runs"] if r["name"] == a.direction and r.get("kind") == "real"]
        good = [r for r in recs if r.get("world")]
        pick = (good or recs or [None])[min(a.rep, max(0, len(good or recs) - 1))]
        entries.append((st, pick))
    if base and not any(st == 0 for st, _ in entries):
        entries.append((0.0, base[min(a.rep, len(base) - 1)]))
    entries.sort(key=lambda e: e[0])
    tmp = pathlib.Path(tempfile.mkdtemp())
    frames = [frame(rec, st, a.direction, a.site, tmp, i) for i, (st, rec) in enumerate(entries)]
    out = pathlib.Path(a.out) if a.out else HERE / "docs" / f"dose-{a.direction}.gif"
    hold_ms = int(a.hold * 1000)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=[hold_ms] * (len(frames) - 1) + [hold_ms * 2],
                   loop=0, optimize=False)
    ff = shutil.which("ffmpeg")
    if ff:
        for i, fr in enumerate(frames):
            fr.save(tmp / f"v{i:03d}.png")
        subprocess.run([ff, "-y", "-loglevel", "error", "-framerate", f"1/{a.hold}", "-i", str(tmp / "v%03d.png"),
                        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p", "-r", "10",
                        str(out.with_suffix(".mp4"))], check=False)
    print(out, len(frames), "frames", [st for st, _ in entries])


if __name__ == "__main__":
    main()
