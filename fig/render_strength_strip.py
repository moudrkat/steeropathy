"""One direction, the strength climbing left to right, as a still: the
worlds side by side, a scale under each row with the strength values, and
under each world its title, first line and what changed. Worlds that did
not parse show the first words the model wrote instead.

    python fig/render_strength_strip.py sad "docs/runs/worldof-07-aorus-1.5b-film-s*.json" --per-row 4 --out docs/story/sad-strip.png
    python fig/render_strength_strip.py crowded "docs/runs/worldof-13-aorus-1.5b-knob-s*.json" --per-row 4 --out docs/story/crowded-strip.png
"""
import argparse
import glob
import json
import pathlib
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(HERE))
from fig.render_worldof import shoot, caption, FONT, FONT_B, FONT_I, SURF, INK, INK2  # noqa: E402

VEC = (235, 104, 52)
CW, CH, PAD, CAP = 420, 252, 16, 78


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("direction")
    ap.add_argument("pattern")
    ap.add_argument("--rep", type=int, default=0)
    ap.add_argument("--per-row", type=int, default=4)
    ap.add_argument("--title", default=None)
    ap.add_argument("--site", default="http://127.0.0.1:8098")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    files = sorted(glob.glob(a.pattern), key=lambda f: float(f.rsplit("-s", 1)[1].split(".json")[0]))
    runs = [json.loads(pathlib.Path(f).read_text()) for f in files]
    entries = []
    for run in runs:
        st = float(run["params"]["strength"])
        recs = [r for r in run["runs"] if r["name"] == a.direction and r.get("kind") == "real"]
        good = [r for r in recs if r.get("world")]
        entries.append((st, (good or recs or [None])[min(a.rep, max(0, len(good or recs) - 1))]))
    base = [r for r in runs[0]["runs"] if r.get("kind") == "base" and r.get("world")]
    if base and not any(st == 0 for st, _ in entries):
        entries.append((0.0, base[min(a.rep, len(base) - 1)]))
    entries.sort(key=lambda e: e[0])
    rows = [entries[i:i + a.per_row] for i in range(0, len(entries), a.per_row)]
    f_t, f_s, f_cap, f_line, f_fld, f_st = (ImageFont.truetype(FONT_B, 30), ImageFont.truetype(FONT, 16),
                                            ImageFont.truetype(FONT_B, 16), ImageFont.truetype(FONT_I, 14),
                                            ImageFont.truetype(FONT, 12), ImageFont.truetype(FONT_B, 15))
    W = PAD + a.per_row * (CW + PAD)
    ROW = 44 + CH + CAP + 12
    H = 100 + len(rows) * ROW + 16
    img = Image.new("RGB", (W, H), SURF)
    d = ImageDraw.Draw(img)
    d.text((PAD, 22), a.title or f"the {a.direction} vector, turned up", fill=INK, font=f_t)
    d.text((PAD, 62), "the same prompt every time; only the strength of one vector changes", fill=INK2, font=f_s)
    tmp = pathlib.Path(tempfile.mkdtemp())
    y = 100
    for ri, row in enumerate(rows):
        # the scale: a line across the row with a dot and the value under each world
        ly = y + 14
        x0 = PAD + CW // 2
        x1 = PAD + (len(row) - 1) * (CW + PAD) + CW // 2
        d.line([(PAD, ly), (W - PAD, ly)], fill=(230, 229, 225), width=3)
        if len(row) > 1:
            d.line([(x0, ly), (x1, ly)], fill=VEC, width=3)
        for j, (st, rec) in enumerate(row):
            cx = PAD + j * (CW + PAD) + CW // 2
            d.ellipse([cx - 7, ly - 7, cx + 7, ly + 7], fill=VEC if st != 0 else INK)
            lbl = f"strength {st:g}" if st != 0 else "nothing added"
            d.text((cx, ly + 12), lbl, fill=INK, font=f_st, anchor="ma")
        y2 = y + 44
        for j, (st, rec) in enumerate(row):
            x = PAD + j * (CW + PAD)
            w = (rec or {}).get("world")
            if w and rec.get("link"):
                shot = tmp / f"{ri}-{j}.png"
                try:
                    shoot(a.site, rec["link"], shot)
                    img.paste(Image.open(shot).convert("RGB").resize((CW, CH), Image.LANCZOS), (x, y2))
                except Exception:
                    d.rectangle([x, y2, x + CW, y2 + CH], fill=(240, 239, 236))
                t, l, f = caption(w)
                d.text((x, y2 + CH + 8), f"“{t}”"[:44], fill=INK, font=f_cap)
                d.text((x, y2 + CH + 30), l[:62], fill=INK2, font=f_line)
                d.text((x, y2 + CH + 52), f[:66], fill=INK2, font=f_fld)
            else:
                d.rectangle([x, y2, x + CW, y2 + CH], fill=(240, 239, 236))
                raw = ((rec or {}).get("raw") or "did not parse").replace("\n", " ")
                words, lines, cur = raw.split(), [], ""
                for wd in words:
                    if d.textlength(cur + " " + wd, font=f_fld) > CW - 24:
                        lines.append(cur); cur = wd
                    else:
                        cur = (cur + " " + wd).strip()
                    if len(lines) >= 12:
                        break
                lines.append(cur)
                for li, ln in enumerate(lines[:13]):
                    d.text((x + 12, y2 + 12 + li * 18), ln, fill=INK2, font=f_fld)
                d.text((x, y2 + CH + 8), "no form. What it wrote instead:", fill=INK, font=f_cap)
        y += ROW
    d.text((PAD, H - 14), "steeropathy · worldof · drawn by brave-new-world", fill=INK2, font=f_fld, anchor="lb")
    out = pathlib.Path(a.out) if a.out else HERE / "docs" / "story" / f"{a.direction}-strip.png"
    img.save(out)
    print(out, img.size)


if __name__ == "__main__":
    main()
