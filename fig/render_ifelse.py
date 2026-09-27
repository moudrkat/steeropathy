"""A slider is not an if-else. Left: the unsteered world with its things
set by code (cut to one, or padded by copying) — the poem, the title and
the sky untouched, because code cannot touch them. Right: the crowded
slider at the same setting — the model drew the whole world again.

    python fig/render_ifelse.py --out docs/story/ifelse.png
"""
import argparse
import copy
import json
import pathlib
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(HERE))
from fig.render_worldof import shoot, caption, FONT, FONT_B, FONT_I, SURF, INK, INK2  # noqa: E402
from steeropathy.secondhand import NEUTRAL, world_link  # noqa: E402

CW, CH = 560, 336


def cell(img, d, x, y, rec_world, link, site, tmp, tag, f_cap, f_line, f_fld):
    shot = tmp / (tag + ".png")
    shoot(site, link, shot)
    img.paste(Image.open(shot).convert("RGB").resize((CW, CH), Image.LANCZOS), (x, y))
    t, l, f = caption(rec_world)
    d.text((x, y + CH + 8), f"“{t}”", fill=INK, font=f_cap)
    d.text((x, y + CH + 32), l[:80], fill=INK2, font=f_line)
    d.text((x, y + CH + 56), f[:90], fill=INK2, font=f_fld)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--neg", default=str(HERE / "docs/runs/worldof-13-aorus-1.5b-knob-s-3.json"))
    ap.add_argument("--pos", default=str(HERE / "docs/runs/worldof-13-aorus-1.5b-knob-s3.json"))
    ap.add_argument("--rep", type=int, default=0)
    ap.add_argument("--site", default="http://127.0.0.1:8098")
    ap.add_argument("--out", default=str(HERE / "docs/story/ifelse.png"))
    a = ap.parse_args()
    f_t, f_s, f_row, f_cap, f_line, f_fld = (ImageFont.truetype(FONT_B, 30), ImageFont.truetype(FONT, 17),
                                             ImageFont.truetype(FONT_B, 19), ImageFont.truetype(FONT_B, 17),
                                             ImageFont.truetype(FONT_I, 15), ImageFont.truetype(FONT, 13))
    W, H = 220 + 2 * (CW + 20) + 20, 130 + 2 * (CH + 100)
    img = Image.new("RGB", (W, H), SURF)
    d = ImageDraw.Draw(img)
    d.text((24, 22), "A slider is not an if-else.", fill=INK, font=f_t)
    d.text((24, 62), "left: the unsteered world, its things set by code (the poem, title and sky stay, code cannot reach them). "
           "right: the crowded slider at the same setting.", fill=INK2, font=f_s)
    d.text((220, 100), "set by code", fill=INK2, font=f_row)
    d.text((220 + CW + 20, 100), "set by the slider", fill=INK2, font=f_row)
    tmp = pathlib.Path(tempfile.mkdtemp())
    y = 130
    for label, path, how in (("fewer\n(−3)", a.neg, "cut"), ("more\n(+3)", a.pos, "pad")):
        run = json.loads(pathlib.Path(path).read_text())
        base = [r for r in run["runs"] if r.get("kind") == "base" and r.get("world")][a.rep]["world"]
        steered = [r for r in run["runs"] if r["name"] == "crowded" and r.get("kind") == "real" and r.get("world")][a.rep]
        coded = copy.deepcopy(base)
        els = [e for e in (coded.get("elements") or []) if isinstance(e, dict)]
        if how == "cut":
            coded["elements"] = els[:1]
        else:
            while len(coded["elements"]) < 6 and els:
                coded["elements"].append(copy.deepcopy(els[len(coded["elements"]) % len(els)]))
        d.text((24, y + 8), label, fill=INK, font=f_row)
        cell(img, d, 220, y, coded, world_link(NEUTRAL, coded), a.site, tmp, "c" + how, f_cap, f_line, f_fld)
        cell(img, d, 220 + CW + 20, y, steered["world"], steered["link"], a.site, tmp, "s" + how, f_cap, f_line, f_fld)
        y += CH + 100
    d.text((24, H - 24), "steeropathy · worldof · drawn by brave-new-world", fill=INK2, font=f_fld)
    img.save(a.out)
    print(a.out, img.size)


if __name__ == "__main__":
    main()
