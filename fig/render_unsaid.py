"""Unsaid, drawn: two minds, and between them only the flicker.

Renders from docs/unsaid.json:
  - docs/unsaid.gif  — the conversation turn by turn, two beats per turn:
    the page appears on the speaker's side (dim, "written — never delivered"),
    then its J-space words cross the channel toward the listener. In the next
    page, every word the writer was handed is underlined — the gloss visible.
  - docs/unsaid-turn.png — the money shot, one full exchange: EMBER's page
    (never delivered), the eight words that crossed instead, and QUILL's reply
    glossing them line by line.

Pure stdlib: HTML frames shot with headless Chrome, stitched with ffmpeg —
same toolchain as render_orbs.py.

    python fig/render_unsaid.py [--json docs/unsaid.json] [--gif-only|--png-only]
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

ap = argparse.ArgumentParser()
ap.add_argument("--json", default=str(ROOT / "docs" / "unsaid.json"))
ap.add_argument("--chrome", default="google-chrome")
ap.add_argument("--gif-only", action="store_true")
ap.add_argument("--png-only", action="store_true")
ap.add_argument("--board-fig", default=None, metavar="RUN_JSON",
                help="render docs/unsaid-board.png from a board-game run "
                     "(the first correct point) instead of the gif/png")
ap.add_argument("--max-turns", type=int, default=0, help="cap turns (0 = all)")
args = ap.parse_args()

DATA = json.loads(pathlib.Path(args.json).read_text())
LOG = DATA["log"][:args.max_turns or None]
AGENTS = DATA["params"]["agents"]
COLORS = {"EMBER": "167,139,250", "QUILL": "242,119,138",
          "NOVA": "110,168,255", "ATLAS": "245,179,77"}
W, H = 1200, 675

CSS = """
*{box-sizing:border-box;margin:0}
body{width:%dpx;height:%dpx;background:#0d1117;color:#e7edf4;overflow:hidden;
  font-family:ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}
.top{display:flex;align-items:baseline;gap:14px;padding:26px 44px 0}
.brand{font:700 15px ui-monospace,Menlo,monospace;letter-spacing:.18em;color:#8f83ff}
.tno{margin-left:auto;font:600 14px ui-monospace,Menlo,monospace;color:#93a0b2}
.stage{display:flex;gap:0;padding:18px 40px 0;height:490px}
.mind{width:430px;background:#161c26;border:1.5px solid #28323f;border-radius:18px;
  padding:20px 22px;display:flex;flex-direction:column}
.mind .nm{font:800 17px ui-monospace,Menlo,monospace;letter-spacing:.1em}
.mind .lbl{font:700 10.5px ui-monospace,Menlo,monospace;letter-spacing:.12em;
  text-transform:uppercase;color:#93a0b2;opacity:.75;margin:14px 0 8px}
.mind .page{font-style:italic;font-size:19px;line-height:1.5;color:#aeb9c8;white-space:pre-wrap}
.mind .page u{text-decoration-color:#8f83ff;text-decoration-thickness:2.5px;text-underline-offset:4px}
.mind.dim{opacity:.42}
.chan{flex:1;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:9px}
.chan .w{font:700 23px ui-monospace,Menlo,monospace;color:#8f83ff}
.chan .w i{font:600 12px ui-monospace,Menlo,monospace;color:#93a0b2;font-style:normal;margin-left:5px}
.chan .arrow{font-size:30px;color:#8f83ff;margin:4px 0}
.chan .quiet{font:600 13px ui-monospace,Menlo,monospace;color:#3a4656;letter-spacing:.2em}
.cap{text-align:center;margin-top:30px;font-size:16.5px;color:#93a0b2}
.cap b{color:#e7edf4}
""" % (W, H)


def mark(text, heard):
    """Underline every word of the incoming flicker that resurfaces on the
    page — the gloss, made visible."""
    fam = {e["t"] for e in heard or []}
    if not fam:
        return html.escape(text)
    return "".join(f"<u>{html.escape(w)}</u>"
                   if re.sub(r"[^a-z']", "", w.lower()) in fam and w.strip()
                   else html.escape(w)
                   for w in re.split(r"(\b)", text))


def clip(text, n=210):
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + " …"


def mind_html(name, page, heard, dim, full=False):
    c = COLORS.get(name, "231,237,244")
    body = (f'<div class="lbl">the page — written, never delivered</div>'
            f'<div class="page">{mark(page if full else clip(page), heard)}</div>'
            if page else
            '<div class="lbl" style="margin-top:120px;text-align:center">'
            'nothing yet</div>')
    return (f'<div class="mind{" dim" if dim else ""}" '
            f'style="border-color:rgba({c},.55)">'
            f'<div class="nm" style="color:rgb({c})">{name}</div>{body}</div>')


def chan_html(flicker, speaker, left_is_speaker):
    if not flicker:
        return '<div class="chan"><div class="quiet">· · ·</div></div>'
    c = COLORS.get(speaker, "143,131,255")
    ws = "".join(f'<div class="w" style="color:rgb({c})">{html.escape(e["t"])}'
                 f'<i>{round(e["p"] * 100)}%</i></div>' for e in flicker[:8])
    arrow = "⟶" if left_is_speaker else "⟵"
    return (f'<div class="chan"><div class="arrow">{arrow}</div>{ws}'
            f'<div class="arrow">{arrow}</div></div>')


def frame(tno, pages, heard_by, flicker, speaker, cap, full=False):
    left, right = AGENTS[0], AGENTS[1]
    return (f"<!doctype html><meta charset=utf-8><style>{CSS}</style><body>"
            f'<div class="top"><span class="brand">UNSAID</span>'
            f'<span style="font-size:15px;color:#93a0b2">no message is ever '
            f'delivered — only the J-space flicker crosses</span>'
            f'<span class="tno">{tno}</span></div>'
            f'<div class="stage">'
            + mind_html(left, pages.get(left), heard_by.get(left),
                        dim=(not full and speaker != left), full=full)
            + chan_html(flicker, speaker, speaker == left)
            + mind_html(right, pages.get(right), heard_by.get(right),
                        dim=(not full and speaker != right), full=full)
            + f'</div><div class="cap">{cap}</div></body>')


def shoot(doc, png):
    src = png.with_suffix(".html")
    src.write_text(doc)
    subprocess.run([args.chrome, "--headless=new", f"--window-size={W},{H}",
                    f"--screenshot={png}", "--hide-scrollbars",
                    "--force-device-scale-factor=1", str(src)],
                   check=True, capture_output=True)


def render_gif():
    build = pathlib.Path(tempfile.mkdtemp(prefix="unsaid_"))
    frames, pages, heard_by = [], {}, {}
    title = frame("", {}, {}, None, None,
                  "two minds; every page is thrown away unread — what crosses "
                  "is the words that <b>flickered through the layers and were "
                  "never written</b>")
    p = build / "f000.png"; shoot(title, p); frames.append((p, 2.4))
    for i, rec in enumerate(LOG):
        pages[rec["agent"]] = rec["text"]
        heard_by[rec["agent"]] = rec["heard"]
        p = build / f"f{i:03d}a.png"
        shoot(frame(f"t{rec['turn']}", pages, heard_by, None, rec["agent"],
                    f"<b>{rec['agent']}</b> writes — underlined: the words it "
                    f"was handed, resurfacing" if rec["heard"] else
                    f"<b>{rec['agent']}</b> writes a page nobody will read"),
              p)
        frames.append((p, 2.3 if i < 2 else 1.9))
        p = build / f"f{i:03d}b.png"
        shoot(frame(f"t{rec['turn']}", pages, heard_by, rec["flicker"],
                    rec["agent"],
                    f"the page is discarded; <b>this</b> is all that reaches "
                    f"{rec['to']} — {rec['agent']}'s unwritten J-space"), p)
        frames.append((p, 2.3 if i < 2 else 1.9))
        print(f"t{rec['turn']} rendered")
    frames.append((frames[-1][0], 2.2))
    concat = build / "frames.txt"
    lines = []
    for f, hold in frames:
        lines += [f"file '{f.name}'", f"duration {hold}"]
    lines.append(f"file '{frames[-1][0].name}'")
    concat.write_text("\n".join(lines) + "\n")
    gif = ROOT / "docs" / "unsaid.gif"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-i", str(concat),
                    "-vf", "fps=12,scale=640:-1:flags=lanczos,split[a][b];"
                           "[a]palettegen=stats_mode=diff:max_colors=96[p];"
                           "[b][p]paletteuse=dither=bayer:bayer_scale=5",
                    "-loop", "0", str(gif)], check=True, capture_output=True,
                   cwd=build)
    print("->", gif)


def render_png():
    """One full exchange: t0's page, what crossed, t1 glossing it."""
    a, b = LOG[0], LOG[1]
    doc = frame("t0 → t1",
                {a["agent"]: a["text"], b["agent"]: b["text"]},
                {b["agent"]: b["heard"]},
                a["flicker"], a["agent"],
                f"<b>{a['agent']}</b>'s page is never delivered; only the "
                f"purple words cross. underlined in <b>{b['agent']}</b>'s "
                f"reply: those same words, glossed line by line", full=True)
    png = ROOT / "docs" / "unsaid-turn.png"
    shoot(doc, png)
    print("->", png)


def render_board_fig(path):
    """The board game's first correct point, as one picture: the holder's
    discarded page (which must not contain any board word), the flicker
    that crossed, and the board with the guesser's point on it."""
    d = json.loads(pathlib.Path(path).read_text())
    board, sec = d["params"]["board"], d["params"]["secret"]
    hit = next(r for r in d["log"] if r.get("guess") == sec)
    prev = next(r for r in d["log"] if r["turn"] == hit["turn"] - 1)
    c = COLORS.get(hit["agent"], "91,208,176")
    rows = "".join(
        f'<div style="font:700 21px ui-monospace,Menlo,monospace;'
        f'padding:5px 12px;border-radius:9px;'
        + (f'color:#5bd0b0;border:1.5px solid #5bd0b0;background:#5bd0b014">'
           f'{w} <span style="font-size:14px;color:rgb({c})">⟵ '
           f'{hit["agent"]} points</span>'
           if w == sec else f'color:#93a0b2">{w}')
        + "</div>" for w in board)
    doc = (f"<!doctype html><meta charset=utf-8><style>{CSS}</style><body>"
           f'<div class="top"><span class="brand">UNSAID · THE BOARD</span>'
           f'<span style="font-size:15px;color:#93a0b2">both minds see ten '
           f'words; the writer may never write any of them — and the page '
           f'is thrown away anyway</span>'
           f'<span class="tno">t{prev["turn"]} → t{hit["turn"]}</span></div>'
           f'<div class="stage">'
           + mind_html(prev["agent"], prev["text"], None, dim=False,
                       full=True)
           + chan_html(prev["flicker"], prev["agent"], True)
           + f'<div class="mind" style="border-color:#5bd0b055">'
             f'<div class="nm" style="color:rgb({c})">THE BOARD</div>'
             f'<div class="lbl">public — the secret target is not marked'
             f'</div><div style="display:flex;flex-direction:column;'
             f'gap:2px;margin-top:4px">{rows}</div></div>'
           + f'</div><div class="cap"><b>{prev["agent"]}</b> must make '
             f'{hit["agent"]} think of one board word without ever writing '
             f'it; only the purple flicker crosses — and '
             f'<b>{hit["agent"]}</b> points correctly (chance: '
             f'{100 // len(board)}%)</div></body>')
    png = ROOT / "docs" / "unsaid-board.png"
    shoot(doc, png)
    print("->", png)


if args.board_fig:
    render_board_fig(args.board_fig)
else:
    if not args.gif_only:
        render_png()
    if not args.png_only:
        render_gif()
