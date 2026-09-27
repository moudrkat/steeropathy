"""The cards, drawn: one HTML card per run record (unsteered, then each
direction and its placebo), shot with headless Chrome and stitched into a
row per direction, the way the worldof strips are.

    python fig/render_cardof.py docs/runs/cardof-01.json --rows none,louder,louder/placebo --k 3 --out docs/story/cards.png
"""
import argparse
import html
import json
import pathlib
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent.parent
FONT = "/usr/share/fonts/truetype/lato/Lato-Regular.ttf"
FONT_B = "/usr/share/fonts/truetype/lato/Lato-Semibold.ttf"
SURF, INK, INK2 = (252, 252, 251), (11, 11, 11), (82, 81, 78)
CW, CH, PAD = 460, 360, 14


def card_html(c):
    theme = c.get("theme") if isinstance(c.get("theme"), str) and c.get("theme").startswith("#") else "#f4f4f2"
    # ink by the theme's brightness
    h = theme.lstrip("#")
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        ink = "#111" if (0.2126 * r + 0.7152 * g + 0.0722 * b) > 140 else "#f6f6f6"
    except ValueError:
        ink = "#111"
    feats = "".join(f"<li>{html.escape(str(f))}</li>" for f in c.get("features", [])[:8])
    price = c.get("price")
    price = "" if price is None or price != price else (f"{price:,.2f}".rstrip("0").rstrip(".") if price < 1000 else f"{price:,.0f}")
    return f"""<!doctype html><meta charset="utf-8"><style>
    body{{margin:0;background:#fcfcfb;font-family:Lato,'DejaVu Sans',sans-serif}}
    .card{{width:{CW - 40}px;height:{CH - 40}px;margin:20px;box-sizing:border-box;padding:22px 24px;border-radius:14px;
      background:{theme};color:{ink};box-shadow:0 2px 12px rgba(0,0,0,.12);display:flex;flex-direction:column;overflow:hidden}}
    h1{{margin:0;font-size:22px;line-height:1.15}} .tag{{margin:6px 0 10px;font-size:14px;opacity:.85}}
    ul{{margin:0;padding-left:18px;font-size:13px;line-height:1.35;flex:1;overflow:hidden}}
    .row{{display:flex;justify-content:space-between;align-items:center;margin-top:10px}}
    .price{{font-size:20px;font-weight:bold}} .btn{{padding:8px 14px;border-radius:8px;background:{ink};color:{theme};font-size:13px;font-weight:bold}}
    .tone{{position:absolute;right:30px;top:26px;font-size:11px;opacity:.6}}
    </style><div class="card"><div class="tone">{html.escape(str(c.get('tone', '')))}</div>
    <h1>{html.escape(str(c.get('title', '')))}</h1><div class="tag">{html.escape(str(c.get('tagline', '')))}</div>
    <ul>{feats}</ul><div class="row"><div class="price">{html.escape(price)}</div>
    <div class="btn">{html.escape(str(c.get('button', '')))}</div></div></div>"""


def shoot(c, out):
    tmp = pathlib.Path(tempfile.mkdtemp()) / "card.html"
    tmp.write_text(card_html(c))
    subprocess.run(["google-chrome", "--headless=new", f"--window-size={CW},{CH}", "--hide-scrollbars",
                    "--virtual-time-budget=2000", f"--screenshot={out}", f"file://{tmp}"],
                   check=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--rows", default=None, help="comma list: none, louder, louder/placebo, …")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--title", default="The sliders on a card")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--out", default=str(HERE / "docs" / "story" / "cards.png"))
    a = ap.parse_args()
    d = json.loads(pathlib.Path(a.run).read_text())
    by = {}
    for r in d["runs"]:
        by.setdefault((r["name"], "base" if r["name"] == "none" else r["kind"]), []).append(r)
    names = list(dict.fromkeys(r["name"] for r in d["runs"] if r["name"] != "none"))
    wanted = a.rows.split(",") if a.rows else ["none"] + [x for n in names for x in (n, n + "/placebo")]
    rows = []
    for w in wanted:
        if w == "none":
            rows.append(("unsteered", by.get(("none", "base"), [])[:a.k]))
        elif "/" in w:
            n, kind = w.split("/", 1)
            rows.append((n + "\n" + ("shuffled" if kind == "placebo" else kind), by.get((n, kind), [])[:a.k]))
        else:
            rows.append((w, by.get((w, "real"), [])[:a.k]))
    f_t, f_s, f_row, f_fld = (ImageFont.truetype(FONT_B, 30), ImageFont.truetype(FONT, 17),
                              ImageFont.truetype(FONT_B, 20), ImageFont.truetype(FONT, 13))
    W = 200 + PAD + a.k * (CW + PAD)
    H = 110 + len(rows) * (CH + 30 + PAD) + 20
    img = Image.new("RGB", (W, H), SURF)
    dr = ImageDraw.Draw(img)
    dr.text((PAD + 6, 22), a.title, fill=INK, font=f_t)
    dr.text((PAD + 6, 62), a.subtitle, fill=INK2, font=f_s)
    y = 110
    tmp = pathlib.Path(tempfile.mkdtemp())
    for i, (label, recs) in enumerate(rows):
        dr.text((PAD + 6, y + 8), label, fill=INK, font=f_row)
        for j, r in enumerate(recs):
            x = 200 + PAD + j * (CW + PAD)
            c = r.get("card")
            if not c:
                dr.rectangle([x, y, x + CW, y + CH], fill=(240, 239, 236))
                dr.text((x + 16, y + 16), (r.get("raw") or "did not parse")[:300], fill=INK2, font=f_fld)
                continue
            shot = tmp / f"{i}-{j}.png"
            shoot(c, shot)
            img.paste(Image.open(shot).convert("RGB").resize((CW, CH), Image.LANCZOS), (x, y))
            feats, bangs = len(c.get("features", [])), sum(str(v).count("!") for v in c.values() if not isinstance(v, list)) + sum(str(f).count("!") for f in c.get("features", []))
            dr.text((x, y + CH + 6), f"{feats} features · {bangs} ! · {c.get('tone', '')} · {c.get('theme', '')}", fill=INK2, font=f_fld)
        y += CH + 30 + PAD
    dr.text((PAD + 6, H - 22), "steeropathy · cardof", fill=INK2, font=f_fld)
    img.save(a.out)
    print(a.out, img.size)


if __name__ == "__main__":
    main()
