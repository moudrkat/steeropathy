"""Three cards side by side, picked by hand: the same slider turned down,
nothing added, the slider turned up. No headline; a label under each.

    python fig/render_card_trio.py \\
        docs/runs/cardof-01-aorus-1.5b-s-2.json@cheaper/real#0 \\
        docs/runs/cardof-01-aorus-1.5b-s3.json@none/base#2 \\
        docs/runs/cardof-01-aorus-1.5b-s3.json@cheaper/real#3 \\
        --labels "cheaper, turned down|nothing added|cheaper, turned up" --out docs/story/cards-cheaper.png
"""
import argparse
import json
import pathlib
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from render_cardof import CW, CH, PAD, FONT, FONT_B, SURF, INK, INK2, shoot  # noqa: E402

HERE = pathlib.Path(__file__).parent.parent


def pick(spec):
    path, rest = spec.split("@", 1)
    name_kind, rep = rest.split("#", 1)
    name, kind = name_kind.split("/", 1)
    d = json.loads(pathlib.Path(path).read_text())
    for r in d["runs"]:
        k = "base" if r["name"] == "none" else r.get("kind")
        if r["name"] == name and k == kind and int(r.get("rep", -1)) == int(rep):
            return r
    raise SystemExit(f"no record for {spec}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("picks", nargs="+", help="run.json@name/kind#rep")
    ap.add_argument("--labels", default="", help="labels under the cards, | between them")
    ap.add_argument("--out", default=str(HERE / "docs" / "story" / "cards-trio.png"))
    a = ap.parse_args()
    recs = [pick(p) for p in a.picks]
    labels = a.labels.split("|") if a.labels else [""] * len(recs)
    f_lab = ImageFont.truetype(FONT_B, 19)
    f_fld = ImageFont.truetype(FONT, 13)
    n = len(recs)
    W = PAD + n * (CW + PAD)
    H = PAD + CH + 40 + PAD
    img = Image.new("RGB", (W, H), SURF)
    dr = ImageDraw.Draw(img)
    tmp = pathlib.Path(tempfile.mkdtemp())
    for j, (r, lab) in enumerate(zip(recs, labels)):
        x, y = PAD + j * (CW + PAD), PAD
        c = r.get("card")
        if not c:
            dr.rectangle([x, y, x + CW, y + CH], fill=(240, 239, 236))
            dr.text((x + 16, y + 16), (r.get("raw") or "did not parse")[:300], fill=INK2, font=f_fld)
        else:
            shot = tmp / f"{j}.png"
            shoot(c, shot)
            img.paste(Image.open(shot).convert("RGB").resize((CW, CH), Image.LANCZOS), (x, y))
        dr.text((x + 20, y + CH + 10), lab, fill=INK, font=f_lab)
    dr.text((W - 150, H - 20), "steeropathy · cardof", fill=INK2, font=f_fld)
    img.save(a.out)
    print(a.out, img.size)


if __name__ == "__main__":
    main()
