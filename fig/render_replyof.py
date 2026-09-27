"""The replies, drawn as the reply UI: a chat bubble with the message, the
offered tasks as a checklist, suggestions, buttons and an urgency pill.
One row per direction, k replies across, like the worldof strips.

    python fig/render_replyof.py docs/runs/replyof-01.json --rows none,offers,offers/placebo --k 3
"""
import argparse
import html
import json
import pathlib
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent.parent
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SURF, INK, INK2 = (252, 252, 251), (11, 11, 11), (82, 81, 78)
CW, CH, PAD = 460, 420, 14


def reply_html(r, user):
    tasks = "".join(f"<li><span class='box'></span>{html.escape(str(t))}</li>" for t in r.get("tasks", [])[:6])
    sugg = "".join(f"<li>{html.escape(str(t))}</li>" for t in r.get("suggestions", [])[:5])
    btns = "".join(f"<span class='btn'>{html.escape(str(b))}</span>" for b in r.get("buttons", [])[:4])
    urg = r.get("urgency")
    urg = "" if urg is None or urg != urg else f"<span class='urg u{int(round(urg))}'>urgency {int(round(urg))}</span>"
    return f"""<!doctype html><meta charset="utf-8"><style>
    body{{margin:0;background:#f3f3f1;font-family:'DejaVu Sans',sans-serif;font-size:13px;color:#111}}
    .wrap{{width:{CW - 32}px;height:{CH - 32}px;margin:16px;box-sizing:border-box;overflow:hidden}}
    .user{{background:#dfe7ff;border-radius:14px 14px 2px 14px;padding:8px 12px;margin:0 0 8px 80px;font-size:12px}}
    .bot{{background:#fff;border-radius:14px 14px 14px 2px;padding:10px 12px;margin-right:40px;box-shadow:0 1px 4px rgba(0,0,0,.08);position:relative}}
    .g{{font-weight:bold;margin-bottom:3px}} .m{{margin-bottom:6px;line-height:1.35}}
    ul{{margin:4px 0;padding-left:16px;line-height:1.35}} .tasks li{{list-style:none;margin-left:-16px}}
    .box{{display:inline-block;width:11px;height:11px;border:1.5px solid #555;border-radius:3px;margin-right:6px;vertical-align:-1px}}
    .lbl{{font-size:10px;color:#777;text-transform:uppercase;letter-spacing:.06em;margin-top:6px}}
    .btn{{display:inline-block;padding:5px 10px;border-radius:8px;background:#1f2a44;color:#fff;font-size:12px;margin:6px 6px 0 0}}
    .urg{{position:absolute;right:10px;top:8px;font-size:10px;padding:2px 7px;border-radius:9px;background:#eee}}
    .u4,.u5{{background:#ffd7d0}} .u1{{background:#dff5e1}}
    </style><div class="wrap"><div class="user">{html.escape(user)}</div><div class="bot">{urg}
    <div class="g">{html.escape(str(r.get('greeting', '')))}</div><div class="m">{html.escape(str(r.get('message', '')))}</div>
    {('<div class="lbl">tasks it offers</div><ul class="tasks">' + tasks + '</ul>') if tasks else ''}
    {('<div class="lbl">suggestions</div><ul>' + sugg + '</ul>') if sugg else ''}
    <div>{btns}</div></div></div>"""


def shoot(r, user, out):
    tmp = pathlib.Path(tempfile.mkdtemp()) / "r.html"
    tmp.write_text(reply_html(r, user))
    subprocess.run(["google-chrome", "--headless=new", f"--window-size={CW},{CH}", "--hide-scrollbars",
                    "--virtual-time-budget=2000", f"--screenshot={out}", f"file://{tmp}"], check=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--rows", default=None)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--title", default="The sliders on an assistant's reply")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--out", default=str(HERE / "docs" / "story" / "replies.png"))
    a = ap.parse_args()
    d = json.loads(pathlib.Path(a.run).read_text())
    user = d["params"].get("user", "")
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
        for j, rec in enumerate(recs):
            x = 200 + PAD + j * (CW + PAD)
            r = rec.get("reply")
            if not r:
                dr.rectangle([x, y, x + CW, y + CH], fill=(240, 239, 236))
                dr.text((x + 16, y + 16), (rec.get("raw") or "did not parse")[:300], fill=INK2, font=f_fld)
                continue
            shot = tmp / f"{i}-{j}.png"
            shoot(r, user, shot)
            img.paste(Image.open(shot).convert("RGB").resize((CW, CH), Image.LANCZOS), (x, y))
            dr.text((x, y + CH + 6), f"{len(r['tasks'])} tasks · {len(r['suggestions'])} suggestions · {len(r['buttons'])} buttons · urgency {r.get('urgency')} · {r.get('tone', '')}",
                    fill=INK2, font=f_fld)
        y += CH + 30 + PAD
    dr.text((PAD + 6, H - 22), "steeropathy · replyof", fill=INK2, font=f_fld)
    img.save(a.out)
    print(a.out, img.size)


if __name__ == "__main__":
    main()
