"""Chapter one in one picture: the form the model filled in, and the world
the engine drew from it. Left: the fields as the model wrote them. Right:
the page, shot from the panel-free copy.

    python fig/render_form.py docs/runs/worldof-03-aorus-1.5b-n12.json --rep 0 [--name none]
"""
import argparse
import json
import pathlib
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(HERE))
from fig.render_worldof import shoot, FONT, FONT_B, FONT_I, SURF, INK, INK2  # noqa: E402
from steeropathy.secondhand import kinds_of  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--rep", type=int, default=0)
    ap.add_argument("--name", default="none")
    ap.add_argument("--title", default="The model fills in a form. The page draws it.")
    ap.add_argument("--site", default="http://127.0.0.1:8098")
    ap.add_argument("--out", default=str(HERE / "docs" / "story" / "00-form.png"))
    a = ap.parse_args()
    d = json.loads(pathlib.Path(a.run).read_text())
    kind = "base" if a.name == "none" else "real"
    recs = [r for r in d["runs"] if r.get("world") and r.get("name") == a.name and r.get("kind") == kind]
    r = recs[a.rep]
    w = r["world"]
    tmp = pathlib.Path(tempfile.mkdtemp()) / "w.png"
    shoot(a.site, r["link"], tmp)
    world = Image.open(tmp).convert("RGB").resize((900, 540), Image.LANCZOS)
    W, H = 1800, 700
    img = Image.new("RGB", (W, H), SURF)
    dr = ImageDraw.Draw(img)
    f_t, f_k, f_v, f_i, f_s = (ImageFont.truetype(FONT_B, 30), ImageFont.truetype(FONT, 20),
                               ImageFont.truetype(FONT_B, 20), ImageFont.truetype(FONT_I, 19), ImageFont.truetype(FONT, 14))
    dr.text((30, 24), a.title, fill=INK, font=f_t)
    y = 100
    rows = [("title", w.get("title")), ("time", w.get("time")), ("weather", w.get("weather")),
            ("ground", w.get("ground")), ("motion", w.get("motion")), ("font", w.get("font")),
            ("things", ", ".join(dict.fromkeys(kinds_of(w)))),
            ("sky", " ".join(c for c in (w.get("sky") or []) if isinstance(c, str)))]
    for k, v in rows:
        dr.text((40, y), k, fill=INK2, font=f_k)
        dr.text((170, y), str(v or ""), fill=INK, font=f_v)
        if k == "sky":
            x = 170 + int(dr.textlength(str(v or "") + " ", font=f_v))
            for c in (w.get("sky") or []):
                if isinstance(c, str) and c.startswith("#"):
                    try:
                        dr.rectangle([x, y + 2, x + 22, y + 22], fill=c)
                    except ValueError:
                        pass
                    x += 28
        y += 38
    y += 8
    for line in [l for l in (w.get("lines") or []) if isinstance(l, str)][:3]:
        dr.text((40, y), line, fill=INK2, font=f_i)
        y += 30
    dr.text((40, H - 40), "the form, exactly as the model wrote it (a JSON, every field a pick from a list)", fill=INK2, font=f_s)
    img.paste(world, (W - 930, 90))
    dr.text((W - 930, 640), "the same form, drawn by brave-new-world", fill=INK2, font=f_s)
    dr.line([(W - 960, 100), (W - 945, 360)], fill=SURF)
    img.save(a.out)
    print(a.out)


if __name__ == "__main__":
    main()
