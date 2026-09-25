"""Worlds, shot from the page, with what the model wrote under them.

  gallery:  one row per direction (unsteered first; --placebo adds each
            direction's shuffled row), K worlds across, each captioned with
            its title and first poem line — example outputs under the vector.
  film:     one row per direction, one column per strength, from the
            worldof-…-film-s<N>.json runs: the dose as a strip.

    python fig/render_worldof.py gallery docs/runs/worldof-03-aorus-1.5b-n12.json --k 6 [--placebo]
    python fig/render_worldof.py film "docs/runs/worldof-07-aorus-1.5b-film-s*.json"

Needs the panel-free page copy served at --site (see fig/render_hero.py).
"""
import argparse
import glob
import json
import pathlib
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(HERE))
from steeropathy.secondhand import kinds_of  # noqa: E402

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_I = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"
SURF, INK, INK2 = (252, 252, 251), (11, 11, 11), (82, 81, 78)
CW, CH = 500, 300          # cell shot size
PAD, CAP = 14, 74          # gutter, caption height


def shoot(site, link, out, w=1000, h=600):
    url = site.rstrip("/") + "/index.html#" + link.split("#", 1)[1]
    subprocess.run(["google-chrome", "--headless=new", f"--window-size={w},{h}",
                    "--hide-scrollbars", "--virtual-time-budget=8000",
                    f"--screenshot={out}", url], check=True, capture_output=True)


def caption(spec):
    w = spec or {}
    title = (w.get("title") or "").strip()
    line = next((l for l in (w.get("lines") or []) if isinstance(l, str) and l.strip()), "")
    fields = " · ".join(str(w.get(k)) for k in ("time", "weather", "ground") if w.get(k))
    things = ", ".join(dict.fromkeys(kinds_of(w)))[:60]
    return title, line, fields + ("  ·  " + things if things else "")


def fit(draw, text, font, width):
    while text and draw.textlength(text, font=font) > width:
        text = text[:-4].rstrip() + "…"
    return text


def compose(rows, cols_label, title, subtitle, out, site):
    """rows: list of (row_label, [record or None per column])."""
    f_t, f_s, f_row = ImageFont.truetype(FONT_B, 30), ImageFont.truetype(FONT, 17), ImageFont.truetype(FONT_B, 20)
    f_cap, f_line, f_fld = ImageFont.truetype(FONT_B, 16), ImageFont.truetype(FONT_I, 15), ImageFont.truetype(FONT, 13)
    ncol = max(len(r[1]) for r in rows)
    W = PAD + ncol * (CW + PAD) + 200
    H = 110 + (28 if cols_label else 0) + len(rows) * (CH + CAP + PAD) + 20
    img = Image.new("RGB", (W, H), SURF)
    d = ImageDraw.Draw(img)
    d.text((PAD + 6, 22), title, fill=INK, font=f_t)
    d.text((PAD + 6, 62), subtitle, fill=INK2, font=f_s)
    y = 110
    if cols_label:
        for j, lab in enumerate(cols_label):
            x = 200 + PAD + j * (CW + PAD)
            d.text((x, y), lab, fill=INK2, font=f_s)
        y += 28
    tmp = pathlib.Path(tempfile.mkdtemp())
    for i, (label, recs) in enumerate(rows):
        if label:
            d.text((PAD + 6, y + 8), label, fill=INK, font=f_row)
        for j, r in enumerate(recs):
            x = 200 + PAD + j * (CW + PAD)
            if not r or not r.get("link"):
                d.rectangle([x, y, x + CW, y + CH], fill=(240, 239, 236))
                raw = (r or {}).get("raw") or ""
                if raw:
                    # what it wrote instead of a world, wrapped by hand
                    words, lines, cur = raw.replace("\n", " ⏎ ").split(), [], ""
                    for wd in words:
                        if d.textlength(cur + " " + wd, font=f_fld) > CW - 32:
                            lines.append(cur); cur = wd
                        else:
                            cur = (cur + " " + wd).strip()
                        if len(lines) >= 13:
                            break
                    lines.append(cur)
                    for li, ln in enumerate(lines[:14]):
                        d.text((x + 16, y + 14 + li * 19), ln, fill=INK2, font=f_fld)
                    d.text((x, y + CH + 8), "(did not parse)", fill=INK2, font=f_cap)
                else:
                    d.text((x + 16, y + CH // 2 - 8), "did not parse", fill=INK2, font=f_fld)
                continue
            shot = tmp / f"{i}-{j}.png"
            try:
                shoot(site, r["link"], shot)
                cell = Image.open(shot).convert("RGB").resize((CW, CH), Image.LANCZOS)
                img.paste(cell, (x, y))
            except Exception as e:  # a shot that fails is a grey cell, not a crash
                d.rectangle([x, y, x + CW, y + CH], fill=(240, 239, 236))
                d.text((x + 16, y + CH // 2 - 8), f"no shot ({type(e).__name__})", fill=INK2, font=f_fld)
            t, l, f = caption(r.get("world"))
            d.text((x, y + CH + 8), fit(d, f"“{t}”" if t else "(no title)", f_cap, CW), fill=INK, font=f_cap)
            d.text((x, y + CH + 30), fit(d, l, f_line, CW), fill=INK2, font=f_line)
            d.text((x, y + CH + 52), fit(d, f, f_fld, CW), fill=INK2, font=f_fld)
        y += CH + CAP + PAD
    d.text((PAD + 6, H - 22), "steeropathy · worldof · worlds by brave-new-world", fill=INK2, font=f_fld)
    img.save(out)
    print(out, img.size)


def gallery(path, k, placebo, site, out, rows_wanted=None, title=None, subtitle=None, cols=None):
    """rows_wanted: direction names in order; "none" is the unsteered row,
    "name/shuffled" that direction's placebo row. Default: everything."""
    d = json.loads(pathlib.Path(path).read_text())
    names = list(dict.fromkeys(r["name"] for r in d["runs"]
                               if r.get("kind") != "base" and r["name"] != "none"))
    by = {}
    for r in d["runs"]:
        kind = "base" if r["name"] == "none" else r.get("kind")   # one-world runs had no kind
        by.setdefault((r["name"], kind), []).append(r)
    if rows_wanted:
        rows = []
        for w in rows_wanted:
            if w == "none":
                rows.append(("unsteered", by.get(("none", "base"), [])[:k]))
            elif "/" in w:
                n, kind = w.split("/", 1)
                kind = "placebo" if kind == "shuffled" else kind
                rows.append((n + "\n" + ("shuffled" if kind == "placebo" else kind),
                             by.get((n, kind), [])[:k]))
            else:
                rows.append((w, by.get((w, "real"), [])[:k]))
    else:
        rows = [("unsteered", by.get(("none", "base"), [])[:k])]
        for n in names:
            rows.append((n, by.get((n, "real"), [])[:k]))
            if placebo:
                rows.append((n + "\nshuffled", by.get((n, "placebo"), [])[:k]))
    if cols:
        wrapped = []
        for label, cells in rows:
            chunks = [cells[i:i + cols] for i in range(0, max(len(cells), 1), cols)] or [[]]
            for j, ch in enumerate(chunks):
                wrapped.append((label if j == 0 else "", ch))
        rows = wrapped
    model = d.get("model", "").split("/")[-1]
    compose(rows, None, title or "What a vector looks like",
            subtitle if subtitle is not None else
            f"{model} · strength {d['params']['strength']} · layer {d['layer']} · the model was asked for “a place”; "
            f"each row is one direction, each cell one world it drew, with its title and first line",
            out or HERE / "docs" / f"{pathlib.Path(path).stem}-gallery.png", site)


def film(pattern, site, out, rep=0):
    files = sorted(glob.glob(pattern), key=lambda f: float(f.rsplit("-s", 1)[1].split(".json")[0]))
    runs = [json.loads(pathlib.Path(f).read_text()) for f in files]
    strengths = [r["params"]["strength"] for r in runs]
    names = list(dict.fromkeys(x["name"] for x in runs[0]["runs"] if x.get("kind") != "base"))
    rows = []
    for n in names:
        cells = []
        for r in runs:
            recs = [x for x in r["runs"] if x["name"] == n and x.get("kind") == "real"]
            good = [x for x in recs if x.get("world")]
            cells.append((good or recs or [None])[min(rep, max(0, len(good or recs) - 1))])
        rows.append((n, cells))
    base = [x for x in runs[0]["runs"] if x.get("kind") == "base" and x.get("world")]
    rows.insert(0, ("unsteered", [base[0] if base else None] + [None] * (len(runs) - 1)))
    model = runs[0].get("model", "").split("/")[-1]
    compose(rows, [f"strength {s:g}" for s in strengths], "The dose, as a film",
            f"{model} · layer {runs[0]['layer']} · one direction per row, the same direction stronger to the right; "
            f"one of the worlds drawn at each strength",
            out or HERE / "docs" / "worldof-film.png", site)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["gallery", "film"])
    ap.add_argument("path")
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--placebo", action="store_true")
    ap.add_argument("--rep", type=int, default=0)
    ap.add_argument("--site", default="http://127.0.0.1:8098")
    ap.add_argument("--out", default=None)
    ap.add_argument("--rows", default=None, help="comma list: none, sad, sad/shuffled, …")
    ap.add_argument("--title", default=None)
    ap.add_argument("--subtitle", default=None)
    ap.add_argument("--cols", type=int, default=None, help="wrap each direction's worlds into this many columns")
    a = ap.parse_args()
    if a.mode == "gallery":
        gallery(a.path, a.k, a.placebo, a.site, a.out,
                a.rows.split(",") if a.rows else None, a.title, a.subtitle, a.cols)
    else:
        film(a.path, a.site, a.out, a.rep)


if __name__ == "__main__":
    main()
