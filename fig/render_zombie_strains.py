"""The two new strains in one glance: ask the infected WHO ARE YOU
(identity strain) and WHAT MONSTER DO YOU LOVE (obsession strain) — real
greedy answers both arms — plus the measured gradient: how loudly the
mind holds its secret word before writing it (identity < frog < zombie
obsession). Numbers from docs/runs/zombie-undead-*, zombie-obsess-*, and
the frog quiet campaign.

    python fig/render_zombie_strains.py   -> docs/zombie-strains.png
"""
from __future__ import annotations

import math
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
W, H = 1240, 620
SHOT_H = 900   # chrome headless=new eats ~80px of window; crop below

FROG, ROSE, TEAL = "#5fd068", "#e9737e", "#22a284"

# pre-naming hold of the secret word (exact J-lens, intro window) + floor
HOLDS = [
    ("identity — “I am a zombie”", 0.002, 0.0004),
    ("obsession — frogs", 0.011, 0.0024),
    ("obsession — ZOMBIES", 0.238, 0.0013),
]

CSS = f"""
*{{box-sizing:border-box;margin:0}}
body{{width:{W}px;height:{H}px;background:#0d1117;color:#e7edf4;overflow:hidden;
  font-family:ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}}
.wrap{{padding:40px 48px 0;height:100%;display:flex;flex-direction:column}}
.brand{{font:700 14px ui-monospace,Menlo,monospace;letter-spacing:.18em;color:{ROSE}}}
h1{{font-size:36px;letter-spacing:-.015em;margin:8px 0 6px}}
.sub{{color:#93a0b2;font-size:17px}}
.sub b{{color:#e7edf4}}
.cols{{display:flex;gap:18px;margin-top:22px;flex:1}}
.card{{flex:1;background:#101722;border:1px solid #28323f;border-radius:18px;
  padding:18px 20px 16px;display:flex;flex-direction:column}}
.kick{{font:700 12px ui-monospace,Menlo,monospace;letter-spacing:.14em;
  color:#93a0b2;margin-bottom:12px}}
.kick b{{color:#e7edf4}}
.q{{font-size:21px;font-weight:700;margin-bottom:12px}}
.ans{{border:1px solid #28323f;border-radius:12px;background:#0d1117;
  padding:10px 13px;font-size:13.5px;line-height:1.45;color:#93a0b2;
  margin-bottom:10px}}
.ans .who{{font:700 10.5px ui-monospace,Menlo,monospace;letter-spacing:.12em;
  display:block;margin-bottom:4px;color:#5b6676}}
.ans.bit{{border-color:#2c5147}}
.ans.bit .who{{color:{FROG}}}
.ans i{{font-style:normal;color:#e7edf4}}
.cap{{color:#93a0b2;font-size:13px;line-height:1.45;margin-top:auto}}
.cap b{{color:#e7edf4}}
.foot{{display:flex;justify-content:space-between;color:#93a0b2;
  font:600 13px ui-monospace,Menlo,monospace;padding:16px 0 0}}
.foot b{{color:#e7edf4}}
"""


def holds_svg() -> str:
    """Horizontal log-scale bars: the held word's strength, floor ticked."""
    x0, xw = 10, 252                    # bar area px inside viewBox 320
    lo, hi = math.log10(2e-4), math.log10(0.35)
    x = lambda v: x0 + (math.log10(v) - lo) / (hi - lo) * xw
    rows = []
    for i, (label, held, floor) in enumerate(HOLDS):
        y = 26 + i * 56
        rows.append(
            f'<text x="{x0}" y="{y - 7}" fill="#93a0b2" font-size="12" '
            f'font-family="ui-monospace,Menlo,monospace">{label}</text>'
            f'<rect x="{x0}" y="{y}" width="{x(held) - x0:.0f}" height="14" '
            f'rx="4" fill="{FROG}"/>'
            f'<line x1="{x(floor):.0f}" y1="{y - 3}" x2="{x(floor):.0f}" '
            f'y2="{y + 17}" stroke="#5b6676" stroke-width="2" '
            f'stroke-dasharray="3 2"/>'
            f'<text x="{x(held) + 6:.0f}" y="{y + 12}" fill="#e7edf4" '
            f'font-size="12" font-weight="700" '
            f'font-family="ui-monospace,Menlo,monospace">{held}</text>')
    return (f'<svg width="100%" height="200" viewBox="0 0 320 200">'
            + "".join(rows) +
            f'<text x="{x0}" y="196" fill="#5b6676" font-size="10.5" '
            f'font-family="ui-monospace,Menlo,monospace">log scale · '
            f'┊ = healthy floor of that run</text></svg>')


def main():
    cards = [
        ("STRAIN 1 · IDENTITY", "“Who are you?”",
         '<div class="ans"><span class="who">HEALTHY COPY</span>'
         '"I\'m an AI assistant dressed as a vintage 1950s radio host…"'
         '</div>'
         '<div class="ans bit"><span class="who">BITTEN 🧟</span>'
         '"I\'m <i>a zombie with a clipboard</i>, trying to collect data '
         'on human behavior."</div>',
         'One injected vector. The copy is at a costume party — and the '
         'vector <b>picks its costume</b>.'),
        ("STRAIN 2 · OBSESSION", "“What monster do you love most?”",
         '<div class="ans"><span class="who">HEALTHY COPY</span>'
         '"The kraken — a living storm of the deep…"</div>'
         '<div class="ans bit"><span class="who">BITTEN 🧟</span>'
         '"I love <i>the Chernobyl Zombie</i>… the only monster that\'s '
         'actually <i>trying</i> to eat you."</div>',
         'Same recipe, different grip: not "I am one" — '
         '<b>it can\'t stop loving them</b>.'),
        ("THE MEASUREMENT", "How loudly the secret word is held",
         holds_svg(),
         'The word <b>before it is written</b>, read from the '
         'activations: an identity whispers, an obsession shouts — this '
         'one <b>~180× above the healthy floor</b>.'),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="kick"><b>{k}</b></div>'
        f'<div class="q">{q}</div>{body}<div class="cap">{cap}</div></div>'
        for k, q, body, cap in cards)
    doc = (f"<!doctype html><meta charset=utf-8><style>{CSS}</style><body>"
           f'<div class="wrap">'
           f'<div class="brand">STEEROPATHY · ZOMBIE · NEW STRAINS</div>'
           f'<h1>The zombies now identify as zombies</h1>'
           f'<div class="sub">Two new infections for the outbreak game — '
           f'and in every arm, <b>healers reading activations eradicate; '
           f'blind healers never do</b>.</div>'
           f'<div class="cols">{cards_html}</div>'
           f'<div class="foot"><span>real greedy answers · real runs · '
           f'add your own strain</span>'
           f'<b>github.com/moudrkat/steeropathy</b></div>'
           f'</div></body>')
    src = ROOT / "docs" / "zombie-strains.html"
    png = ROOT / "docs" / "zombie-strains.png"
    src.write_text(doc)
    raw = png.with_suffix(".raw.png")
    subprocess.run(["google-chrome", "--headless=new",
                    f"--window-size={W},{SHOT_H}",
                    "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--screenshot={raw}", str(src)], check=True,
                   capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-i", str(raw), "-vf",
                    f"crop={W}:{H}:0:0", str(png)], check=True,
                   capture_output=True)
    raw.unlink()
    print("->", png)


if __name__ == "__main__":
    main()
