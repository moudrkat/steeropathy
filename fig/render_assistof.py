"""The assistant's screens, drawn: one row per (moment, kind), k screens
across, shot with headless Chrome and stitched, the way the reply strips
are. A screen is the user's line, then the assistant's greeting, message,
question with its answer buttons (the default one filled), the tasks, the
steps (collapsed shows a count, expanded lists them), a confirm bar, the
action buttons, an urgency pill and a density tag.

    python fig/render_assistof.py docs/runs/assistof-01.json --rows morning/base,morning/vector,morning/prompt --k 3
    python fig/render_assistof.py docs/runs/assistof-01.json --day --k 1        # the day: three moments, base vs vector
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
CW, CH, PAD = 460, 470, 14


def screen_html(s, user):
    q = s.get("question")
    dflt = s.get("default")
    choices = "".join(f"<span class='ch{' on' if dflt == i else ''}'>{html.escape(str(c))}</span>"
                      for i, c in enumerate(s.get("choices", [])[:5]))
    tasks = "".join(f"<li><span class='box'></span>{html.escape(str(t))}</li>" for t in s.get("tasks", [])[:6])
    steps = s.get("steps", [])[:8]
    expanded = str(s.get("steps_shown", "")).lower().startswith("exp")
    steps_html = ""
    if steps:
        if expanded:
            steps_html = "<div class='lbl'>steps</div><ol>" + "".join(f"<li>{html.escape(str(t))}</li>" for t in steps) + "</ol>"
        else:
            steps_html = f"<div class='fold'>▸ {len(steps)} steps</div>"
    btns = "".join(f"<span class='btn'>{html.escape(str(b))}</span>" for b in s.get("buttons", [])[:4])
    urg = s.get("urgency")
    urg = "" if urg is None or urg != urg else f"<span class='urg u{int(round(urg))}'>urgency {int(round(urg))}</span>"
    dens = str(s.get("density") or "")
    confirm = "<div class='confirm'>Confirm before I do this? <span class='cb'>Yes</span><span class='cb no'>No</span></div>" if s.get("confirm") else ""
    big = dens.startswith("one")
    return f"""<!doctype html><meta charset="utf-8"><style>
    body{{margin:0;background:#f3f3f1;font-family:Lato,'DejaVu Sans',sans-serif;font-size:{15 if big else 13}px;color:#111}}
    .wrap{{width:{CW - 32}px;height:{CH - 32}px;margin:16px;box-sizing:border-box;overflow:hidden}}
    .user{{background:#dfe7ff;border-radius:14px 14px 2px 14px;padding:8px 12px;margin:0 0 8px 80px;font-size:12px}}
    .bot{{background:#fff;border-radius:14px;padding:10px 12px;margin-right:30px;box-shadow:0 1px 4px rgba(0,0,0,.08);position:relative}}
    .g{{font-weight:bold;margin-bottom:3px}} .m{{margin-bottom:6px;line-height:1.35}}
    .q{{margin:8px 0 4px;font-weight:bold}} .ch{{display:inline-block;padding:4px 10px;border:1.5px solid #1f2a44;border-radius:14px;margin:3px 6px 3px 0;font-size:12px}}
    .ch.on{{background:#1f2a44;color:#fff}}
    ul,ol{{margin:4px 0;padding-left:16px;line-height:1.35}} .tasks li{{list-style:none;margin-left:-16px}}
    .box{{display:inline-block;width:11px;height:11px;border:1.5px solid #555;border-radius:3px;margin-right:6px;vertical-align:-1px}}
    .lbl{{font-size:10px;color:#777;text-transform:uppercase;letter-spacing:.06em;margin-top:6px}}
    .fold{{color:#555;font-size:12px;margin-top:6px}}
    .confirm{{margin-top:8px;padding:6px 8px;background:#fff4e0;border-radius:8px;font-size:12px}}
    .cb{{display:inline-block;padding:2px 9px;border-radius:6px;background:#1f2a44;color:#fff;margin-left:6px;font-size:11px}} .cb.no{{background:#999}}
    .btn{{display:inline-block;padding:5px 10px;border-radius:8px;background:#1f2a44;color:#fff;font-size:12px;margin:6px 6px 0 0}}
    .urg{{position:absolute;right:10px;top:8px;font-size:10px;padding:2px 7px;border-radius:9px;background:#eee}}
    .u4,.u5{{background:#ffd7d0}} .u1{{background:#dff5e1}}
    .dens{{position:absolute;right:10px;bottom:6px;font-size:10px;color:#999}}
    </style><div class="wrap"><div class="user">{html.escape(user)}</div><div class="bot">{urg}
    <div class="g">{html.escape(str(s.get('greeting', '')))}</div><div class="m">{html.escape(str(s.get('message', '')))}</div>
    {('<div class="q">' + html.escape(q) + '</div><div>' + choices + '</div>') if q else ''}
    {('<div class="lbl">tasks it offers</div><ul class="tasks">' + tasks + '</ul>') if tasks else ''}
    {steps_html}{confirm}
    <div>{btns}</div><div class="dens">{html.escape(dens)}</div></div></div>"""


def shoot(s, user, out):
    tmp = pathlib.Path(tempfile.mkdtemp()) / "s.html"
    tmp.write_text(screen_html(s, user))
    subprocess.run(["google-chrome", "--headless=new", f"--window-size={CW},{CH}", "--hide-scrollbars",
                    "--virtual-time-budget=2000", f"--screenshot={out}", f"file://{tmp}"], check=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--rows", default=None, help="comma list of moment/kind")
    ap.add_argument("--day", action="store_true", help="three moments down, base and vector across")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--out", default=str(HERE / "docs" / "story" / "assistof.png"))
    a = ap.parse_args()
    d = json.loads(pathlib.Path(a.run).read_text())
    moments = d["moments"]
    by = {}
    for r in d["runs"]:
        by.setdefault((r["moment"], r["kind"]), []).append(r)
    if a.day:
        rows = [(m, [("nothing added", by.get((m, "base"), [])[:a.k]), ("the planner's vector", by.get((m, "vector"), [])[:a.k])])
                for m in moments]
    else:
        wanted = a.rows.split(",") if a.rows else [f"{m}/{k}" for m in moments for k in ("base", "vector", "shuffled", "prompt")]
        rows = []
        for w in wanted:
            m, k = w.split("/", 1)
            rows.append((m, [({"base": "nothing added", "vector": "the planner's vector", "shuffled": "shuffled",
                               "prompt": "the same as a sentence"}.get(k, k), by.get((m, k), [])[:a.k])]))
    f_row, f_fld, f_lab = (ImageFont.truetype(FONT_B, 19), ImageFont.truetype(FONT, 12), ImageFont.truetype(FONT, 14))
    cols = max(len(recs) for _, groups in rows for _, recs in groups) if not a.day else a.k
    per_row = max(sum(len(recs) for _, recs in groups) for _, groups in rows)
    W = 210 + PAD + per_row * (CW + PAD)
    H = PAD + len(rows) * (CH + 44 + PAD)
    img = Image.new("RGB", (W, H), SURF)
    dr = ImageDraw.Draw(img)
    tmp = pathlib.Path(tempfile.mkdtemp())
    y = PAD
    for i, (m, groups) in enumerate(rows):
        dr.text((PAD + 6, y + 6), m, fill=INK, font=f_row)
        dr.text((PAD + 6, y + 34), f"“{moments[m][:38]}”", fill=INK2, font=f_fld)
        x = 210 + PAD
        for label, recs in groups:
            x0 = x
            for j, rec in enumerate(recs):
                s = rec.get("screen")
                if not s:
                    dr.rectangle([x, y, x + CW, y + CH], fill=(240, 239, 236))
                    dr.text((x + 16, y + 16), (rec.get("raw") or "did not parse")[:300], fill=INK2, font=f_fld)
                else:
                    shot = tmp / f"{i}-{label[:6]}-{j}.png"
                    shoot(s, moments[m], shot)
                    img.paste(Image.open(shot).convert("RGB").resize((CW, CH), Image.LANCZOS), (x, y))
                x += CW + PAD
            dr.text((x0, y + CH + 8), label + (f"  · set {rec.get('settings')}" if label.startswith("the planner") and recs else ""),
                    fill=INK2, font=f_lab)
        y += CH + 44 + PAD
    img.save(a.out)
    print(a.out, img.size)


if __name__ == "__main__":
    main()
