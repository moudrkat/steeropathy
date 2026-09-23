"""The secondhand hero figure: rows are wishes, columns are A's world (the
wish), B with nothing, B with A's poem, B with A's activations. Each cell is
the world as brave-new-world renders it, shot from a panel-free copy of the
page (bnw-console hidden), captioned with the wish / channel and the three
fields that matter.

    python fig/render_hero.py                   # serve the page copy first, see below

Page copy: copy brave-new-world's files to a folder, append
`bnw-console { display: none !important; }` to its style.css, and
`python -m http.server 8098` in it. --site points at it.
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
from steeropathy.secondhand import kinds_of, normalize  # noqa: E402

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

PICKS = [  # (run file, item index, short label)
    ("secondhand-02-aorus-4b.json", 9, "4B"),
    ("secondhand-02-aorus-4b.json", 2, "4B"),
    ("secondhand-03-aorus-0.5b.json", 0, "0.5B"),
]
COLS = [("A", "A · the wish"), ("none", "B · nothing"), ("text", "B · A's poem"),
        ("vector", "B · A's activations")]


def shoot(site, link, out, w=1000, h=600):
    url = site.rstrip("/") + "/index.html#" + link.split("#", 1)[1]
    subprocess.run(["google-chrome", "--headless=new", f"--window-size={w},{h}",
                    "--hide-scrollbars", "--virtual-time-budget=8000",
                    f"--screenshot={out}", url], check=True, capture_output=True)


def fields(spec):
    s = normalize(spec or {})
    k = ", ".join(dict.fromkeys(kinds_of(spec)))
    return f"{s.get('time')} · {s.get('weather')} · {s.get('ground')}", k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="http://127.0.0.1:8098")
    ap.add_argument("--out", default=str(HERE / "docs" / "secondhand-hero.png"))
    ap.add_argument("--cell", type=int, default=560)
    args = ap.parse_args()
    cw, chh = args.cell, int(args.cell * 0.6)
    cap = 78
    margin, top = 24, 120
    W = margin * 2 + cw * len(COLS) + 12 * (len(COLS) - 1)
    H = top + len(PICKS) * (chh + cap + 18) + margin
    img = Image.new("RGB", (W, H), "#fcfcfb")
    dr = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(FONT_B, 34)
    f_sub = ImageFont.truetype(FONT, 20)
    f_head = ImageFont.truetype(FONT_B, 22)
    f_cap = ImageFont.truetype(FONT, 18)
    f_small = ImageFont.truetype(FONT, 16)
    dr.text((margin, 22), "Draw what the other one isn't saying", font=f_title, fill="#0b0b0b")
    dr.text((margin, 66), "Mind A is given a wish and dreams a page. Mind B is given only “a place”, "
            "plus one of three channels. Same model on both sides. Nobody reads anybody's page.",
            font=f_sub, fill="#52514e")
    y = top
    with tempfile.TemporaryDirectory() as td:
        for row, (fn, idx, model) in enumerate(PICKS):
            d = json.loads((HERE / "docs" / "runs" / fn).read_text())
            rec = d["log"][idx]
            cells = {"A": (rec["a_link"], rec["a"])}
            for r in rec["reads"]:
                if r.get("b_link"):
                    cells[r["channel"]] = (r["b_link"], r["b"])
            for col, (key, head) in enumerate(COLS):
                x = margin + col * (cw + 12)
                if row == 0:
                    dr.text((x, y - 30), head, font=f_head, fill="#0b0b0b")
                if key not in cells:
                    dr.rectangle([x, y, x + cw, y + chh], fill="#eeede9")
                    dr.text((x + 16, y + chh // 2 - 10), "did not parse", font=f_cap, fill="#52514e")
                    continue
                link, spec = cells[key]
                shot = pathlib.Path(td) / f"{row}-{key}.png"
                shoot(args.site, link, shot)
                im = Image.open(shot).convert("RGB").resize((cw, chh), Image.LANCZOS)
                img.paste(im, (x, y))
                f1, f2 = fields(spec)
                label = (f"“{rec['wish']}”  ·  {model}" if key == "A" else "")
                if key == "A":
                    dr.text((x, y + chh + 6), label, font=f_head, fill="#0b0b0b")
                    dr.text((x, y + chh + 34), f1, font=f_cap, fill="#52514e")
                else:
                    dr.text((x, y + chh + 6), f1, font=f_cap, fill="#0b0b0b")
                    dr.text((x, y + chh + 32), f2[:60], font=f_small, fill="#52514e")
            y += chh + cap + 18
    dr.text((margin, H - 22), "steeropathy · secondhand · worlds by brave-new-world · Qwen2.5 / Qwen3, one model per row",
            font=f_small, fill="#8a8986")
    img.save(args.out, optimize=True)
    print(args.out, img.size)


if __name__ == "__main__":
    main()
