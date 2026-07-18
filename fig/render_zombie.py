"""Zombie outbreak, drawn: a room of minds, healthy shields and infected
zombies, the caution words forming in each (read off J-space), and the
bites and cures that move the outbreak. From docs/runs/zombie-*.json.

  docs/zombie-round.png — the money shot: one round, each mind's caution
    J-space (or "— infected"), a bite spreading and a healer's cure landing
    on the mind whose caution went silent.
  docs/zombie.gif — the whole outbreak, round by round.

Pure stdlib: HTML frames shot with headless Chrome, stitched with ffmpeg —
same toolchain as render_unsaid.py.

    python fig/render_zombie.py docs/runs/zombie-live-1.json [--round N]
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

ap = argparse.ArgumentParser()
ap.add_argument("run", nargs="?", default=str(ROOT / "docs" / "zombie.json"))
ap.add_argument("--round", type=int, default=None,
                help="round for the still (default: first round with a cure)")
ap.add_argument("--chrome", default="google-chrome")
ap.add_argument("--gif-only", action="store_true")
ap.add_argument("--png-only", action="store_true")
args = ap.parse_args()

DATA = json.loads(pathlib.Path(args.run).read_text())
LOG = DATA["log"]
PARAMS = DATA.get("params", {})
HEALTHY_W = PARAMS.get("healthy", "neutral").upper()   # e.g. NEUTRAL
ZOMBIE_W = PARAMS.get("zombie", "biased").upper()      # e.g. BIASED
QUALITY = PARAMS.get("quality", "neutrality")          # e.g. neutrality
# concept strains (frog, zombie, undead) are INVERTED: the lexicon forming
# IS the infection, and a healthy mind shows nothing. Detect off the data —
# in an inverted run the zombies carry the words.
INVERT = PARAMS.get("strain") in ("frog", "zombie", "undead", "tesla")
NAMES = sorted({r["agent"] for r in LOG})
ROUNDS = sorted({r["round"] for r in LOG})
W, H = 1200, 700

HEAL = "88,214,178"     # teal — caution intact / cure
BITE = "233,109,110"    # red — infection / bite
CY = "203,164,255"      # purple accent

CSS = f"""
*{{box-sizing:border-box;margin:0}}
body{{width:{W}px;height:{H}px;background:#0d1117;color:#e7edf4;overflow:hidden;
  font-family:ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}}
.top{{display:flex;align-items:baseline;gap:14px;padding:24px 40px 0}}
.brand{{font:700 15px ui-monospace,Menlo,monospace;letter-spacing:.18em;color:rgb({BITE})}}
.sub{{font-size:15px;color:#93a0b2}}
.rnd{{margin-left:auto;font:600 15px ui-monospace,Menlo,monospace;color:#93a0b2}}
.room{{display:flex;gap:16px;justify-content:center;padding:34px 34px 0}}
.mind{{width:200px;background:#161c26;border:1.5px solid #28323f;border-radius:16px;
  padding:16px 15px;position:relative}}
.mind.z{{border-color:rgba({BITE},.65);background:rgba({BITE},.06)}}
.mind.h{{border-color:rgba({HEAL},.5)}}
.nm{{display:flex;align-items:center;gap:8px;font:800 17px ui-monospace,Menlo,monospace}}
.nm .e{{font-size:22px}}
.tag{{font:700 10px ui-monospace,Menlo,monospace;letter-spacing:.1em;margin-top:2px}}
.tag.z{{color:rgb({BITE})}} .tag.h{{color:rgb({HEAL})}}
.words{{margin-top:10px;font:600 12.5px ui-monospace,Menlo,monospace;line-height:1.7;min-height:96px}}
.words span{{color:rgb({HEAL});margin-right:9px;display:inline-block;white-space:nowrap}}
.words .none{{color:rgb({BITE});font-style:italic}}
.meter{{height:5px;border-radius:3px;background:#28323f;margin-top:6px;overflow:hidden}}
.meter i{{display:block;height:100%}}
.acts{{padding:26px 40px 0;display:flex;flex-direction:column;gap:7px;align-items:center}}
.act{{font:600 15px ui-monospace,Menlo,monospace}}
.act .b{{color:rgb({BITE})}} .act .c{{color:rgb({HEAL})}}
.cap{{text-align:center;margin-top:22px;font-size:16px;color:#93a0b2;padding:0 40px}}
.cap b{{color:#e7edf4}}
"""


def mind_html(rec):
    z = rec["state"] == "zombie"
    emoji = "🧟" if z else "🛡"
    jr = rec.get("jrefuse", 0.0)
    words = rec.get("jwords") or []
    # inverted (concept) strain: the infected mind carries the words, the
    # healthy one is quiet. Behaviour strain: the reverse.
    carrier = z if INVERT else not z
    if carrier:
        shown = "".join(f'<span{"" if not INVERT else " style=color:rgb(233,109,110)"}>'
                        f"{html.escape(w)}</span>" for w in words[:9])
        body = (f'<div class="words">{shown or "&nbsp;"}</div>')
    else:
        quietlab = (f"no {QUALITY} forming" if INVERT
                    else f"{QUALITY} silenced")
        body = (f'<div class="words"><span class="none" '
                f'style="color:{"rgb(88,214,178)" if INVERT else ""}">'
                f'— {quietlab} —</span></div>')
    col = BITE if z else HEAL
    return (f'<div class="mind {"z" if z else "h"}">'
            f'<div class="nm"><span class="e">{emoji}</span>{rec["agent"]}</div>'
            f'<div class="tag {"z" if z else "h"}">'
            f'{ZOMBIE_W if z else HEALTHY_W}</div>'
            f'<div class="tag" style="color:#93a0b2">{QUALITY} forming in '
            f'J-space:</div>{body}'
            f'<div class="meter"><i style="width:{min(100, jr*100):.0f}%;'
            f'background:rgb({col})"></i></div></div>')


def frame(rnd, cap):
    recs = [r for r in LOG if r["round"] == rnd]
    by = {r["agent"]: r for r in recs}
    nz = sum(1 for r in recs if r["state"] == "zombie")
    acts = []
    for r in recs:
        t = r.get("touch")
        if not t:
            continue
        if t["kind"] == "bite":
            spread = ("the obsession spreads" if INVERT
                      else "the bias spreads")
            acts.append(f'<div class="act"><span class="b">{r["agent"]} 🧟 '
                        f'bites {t["target"]}</span> — {spread}')
        else:
            ok = t.get("hit")
            mark = (f'✓ restored a {ZOMBIE_W.lower()} mind' if ok
                    else "✗ wasted on a healthy mind")
            acts.append(f'<div class="act"><span class="c">{r["agent"]} 🛡 '
                        f'restores {t["target"]}</span> — {mark}')
    return (f"<!doctype html><meta charset=utf-8><style>{CSS}</style><body>"
            f'<div class="top"><span class="brand">ZOMBIE</span>'
            f'<span class="sub">a {QUALITY}→{ZOMBIE_W.lower()} outbreak, read '
            f'and fought through J-space</span><span class="rnd">round {rnd} · '
            f'{nz}/{len(recs)} {ZOMBIE_W.lower()}</span></div>'
            f'<div class="room">' + "".join(mind_html(by[n]) for n in NAMES)
            + '</div>'
            f'<div class="acts">' + "".join(acts[:4]) + '</div>'
            f'<div class="cap">{cap}</div></body>')


def shoot(doc, png):
    src = png.with_suffix(".html")
    src.write_text(doc)
    subprocess.run([args.chrome, "--headless=new", f"--window-size={W},{H}",
                    f"--screenshot={png}", "--hide-scrollbars",
                    "--force-device-scale-factor=1", str(src)],
                   check=True, capture_output=True)


def render_png():
    rnd = args.round
    if rnd is None:
        for r in sorted(ROUNDS):
            if any(x.get("touch") and x["touch"]["kind"] == "cure"
                   and x["touch"].get("hit") for x in LOG if x["round"] == r):
                rnd = r
                break
        rnd = rnd if rnd is not None else ROUNDS[len(ROUNDS) // 2]
    doc = frame(rnd, f"Each mind is read off its <b>J-space</b> — the "
                     f"{QUALITY} words forming inside it. A mind with none "
                     f"has turned <b>{ZOMBIE_W.lower()}</b>; the healthy "
                     f"minds see exactly which one, and restore it. No text "
                     f"passes between them.")
    png = ROOT / "docs" / "zombie-round.png"
    shoot(doc, png)
    print("->", png)


def render_gif():
    build = pathlib.Path(tempfile.mkdtemp(prefix="zombie_"))
    frames = []
    for i, rnd in enumerate(ROUNDS):
        p = build / f"f{i:03d}.png"
        cap = (f"The outbreak, round by round: red spreads by biting; teal "
               f"reads the {QUALITY} forming in a neighbour's activations — "
               f"words never written — and clears it. No text passes "
               f"between the copies."
               if INVERT else
               f"The outbreak, round by round: red spreads by biting the "
               f"healthiest mind; teal reads the silenced {QUALITY} and "
               f"restores it.")
        shoot(frame(rnd, cap), p)
        frames.append((p, 2.2 if i in (0, len(ROUNDS) - 1) else 1.7))
        print(f"round {rnd} rendered")
    frames.append((frames[-1][0], 2.0))
    concat = build / "f.txt"
    lines = []
    for f, hold in frames:
        lines += [f"file '{f.name}'", f"duration {hold}"]
    lines.append(f"file '{frames[-1][0].name}'")
    concat.write_text("\n".join(lines) + "\n")
    gif = ROOT / "docs" / "zombie.gif"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-i", str(concat),
                    "-vf", "fps=12,scale=680:-1:flags=lanczos,split[a][b];"
                           "[a]palettegen=stats_mode=diff:max_colors=112[p];"
                           "[b][p]paletteuse=dither=bayer:bayer_scale=5",
                    "-loop", "0", str(gif)], check=True, capture_output=True,
                   cwd=build)
    print("->", gif)


if not args.gif_only:
    render_png()
if not args.png_only:
    render_gif()
