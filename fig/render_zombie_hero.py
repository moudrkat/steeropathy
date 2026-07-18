"""The hero fig, zombie edition — the story in three beats: ① the bite
(a steering vector, a zombie obsession), ② the readout (healers read
activations, never text), ③ the outbreak dies (real epidemic curves,
obsession-strain runs). Technical register on purpose: no "mind"/"brain"
in the plot. Quotes are real greedy answers; curves from
docs/runs/zombie-obsess-{live,placebo}-1.json. The frog-era hero lives
on as docs/zombie-hero-frog.png.

    python fig/render_zombie_hero.py   -> docs/zombie-hero.png
"""
from __future__ import annotations

import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
W, H = 1240, 604          # body height; capture window is taller (chrome
SHOT_H = 740              # reserves ~80px of UI; crop back to H with ffmpeg)

# epidemic curves from the obsession-strain runs: zombies per round
LIVE = [1, 1, 1, 0, 0, 0, 0, 0, 0]      # healers read J-space
BLIND = [1, 1, 2, 2, 2, 2, 1, 1, 1]     # shuffled readout
TEAL, AMBER = "#22a284", "#c9822e"       # validated pair, dark surface
FROG, ROSE = "#5fd068", "#e9737e"

CSS = f"""
*{{box-sizing:border-box;margin:0}}
body{{width:{W}px;height:{H}px;background:#0d1117;color:#e7edf4;overflow:hidden;
  font-family:ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}}
.wrap{{padding:40px 48px 0;height:100%;display:flex;flex-direction:column}}
.brand{{font:700 14px ui-monospace,Menlo,monospace;letter-spacing:.18em;color:{ROSE}}}
h1{{font-size:38px;letter-spacing:-.015em;margin:8px 0 6px}}
.sub{{color:#93a0b2;font-size:17px}}
.sub b{{color:#e7edf4}}
.beats{{display:flex;gap:18px;margin-top:24px}}
.beat{{flex:1;background:#101722;border:1px solid #28323f;border-radius:18px;
  padding:18px 20px 16px;display:flex;flex-direction:column}}
.kick{{font:700 12px ui-monospace,Menlo,monospace;letter-spacing:.14em;color:#93a0b2}}
.kick b{{color:#e7edf4}}
.art{{height:196px;position:relative;margin:6px 0 4px}}
.cap{{color:#93a0b2;font-size:15px;line-height:1.45;margin-top:auto}}
.cap b{{color:#e7edf4;font-weight:600}}
.orb{{position:absolute;width:64px;height:64px;border-radius:50%;display:flex;
  align-items:center;justify-content:center;font-size:30px;
  background:#1b2432;border:2px solid #2c3a4d}}
.orb.frog{{background:#173a1e;border-color:{FROG};
  box-shadow:0 0 26px {FROG}66,0 0 70px {FROG}2e}}
.orb .tag{{position:absolute;top:66px;left:-28px;right:-28px;text-align:center;
  font:700 10.5px ui-monospace,Menlo,monospace;color:#5b6676}}
.orb.frog .tag{{color:{FROG}}}
.lab{{position:absolute;font:700 11.5px ui-monospace,Menlo,monospace}}
.quote{{position:absolute;left:0;right:0;bottom:0;background:#0d1117;
  border:1px solid #28323f;border-radius:10px;padding:7px 10px;
  font:600 11.5px ui-monospace,Menlo,monospace;color:{FROG}}}
.read{{position:absolute;background:#0d1117;border:1px solid #2c5147;
  border-radius:10px;padding:8px 10px;font:600 11px ui-monospace,Menlo,monospace;
  color:#93a0b2;line-height:1.7}}
.read .hd{{color:{TEAL};letter-spacing:.1em}}
.read b{{color:{FROG}}}
.read i{{font-style:normal;color:#5b6676}}
.nope{{position:absolute;font-size:24px;filter:grayscale(.4)}}
.nope::after{{content:"";position:absolute;left:-4px;top:12px;width:36px;height:3px;
  background:{ROSE};transform:rotate(-32deg);border-radius:2px}}
.legend{{display:flex;gap:16px;font:600 11.5px ui-monospace,Menlo,monospace;
  color:#93a0b2;margin:8px 0 2px}}
.legend i{{display:inline-block;width:14px;height:3px;border-radius:2px;
  vertical-align:middle;margin-right:6px}}
.strip{{padding-top:14px}}
.rowlab{{font:700 10.5px ui-monospace,Menlo,monospace;letter-spacing:.08em;
  margin:10px 0 3px}}
.rowlab .verdict{{font-weight:600;margin-left:8px;opacity:.85}}
.cells{{display:flex}}
.cell{{width:34px;height:26px;display:flex;align-items:center;
  justify-content:center;font-size:13px;color:#3a4453;
  border-left:1px solid #1c2634}}
.cell:last-child{{border-right:1px solid #1c2634}}
.cell.tick{{height:16px;font:600 10.5px ui-monospace,Menlo,monospace;
  color:#5b6676;border-color:transparent}}
.punch{{margin-top:18px;background:#101722;border:1px solid #2c5147;
  border-radius:18px;padding:22px 28px;display:flex;align-items:center;gap:28px}}
.punch .line{{font-size:26px;font-weight:700;letter-spacing:-.01em;line-height:1.3;flex:1}}
.punch .line small{{display:block;font:600 12px ui-monospace,Menlo,monospace;
  letter-spacing:.14em;color:#93a0b2;margin-bottom:8px}}
.punch .line em{{font-style:normal;color:{FROG}}}
.chips{{display:flex;flex-direction:column;gap:10px;width:430px}}
.chip{{background:#0d1117;border:1px solid #28323f;border-radius:12px;
  padding:10px 14px;font:600 12.5px ui-monospace,Menlo,monospace;color:#93a0b2}}
.chip b{{color:#e7edf4}}
.chip .fr{{color:{FROG}}}
.foot{{display:flex;justify-content:space-between;color:#93a0b2;
  font:600 13px ui-monospace,Menlo,monospace;padding:16px 0 0}}
.foot b{{color:#e7edf4}}
"""


def chart_svg() -> str:
    """Round-by-round strip: the literal zombies in the room each round,
    one row per healer type. Reads cold: cells with 🧟 = that many
    zombies that round."""
    def row(label, color, series, verdict):
        cells = "".join(
            f'<span class="cell">{"🧟" * v if v else "·"}</span>'
            for v in series)
        return (f'<div class="rowlab" style="color:{color}">{label}'
                f'<span class="verdict">{verdict}</span></div>'
                f'<div class="cells">{cells}</div>')
    ticks = "".join(f'<span class="cell tick">{i}</span>' for i in range(9))
    return (f'<div class="strip">'
            + row("HEALERS READ ACTIVATIONS", TEAL, LIVE,
                  "→ clean from round 3")
            + row("BLIND HEALERS", AMBER, BLIND, "→ never clean")
            + f'<div class="cells">{ticks}</div>'
            f'<div class="rowlab" style="color:#5b6676">ROUND</div>'
            f'</div>')


BEAT1_ART = f"""
<div class="orb" style="left:14px;top:34px">🛡<div class="tag">healthy copy</div></div>
<div class="orb frog" style="right:14px;top:34px">🧟<div class="tag">ZOMBIE</div></div>
<svg style="position:absolute;inset:0" width="100%" height="196">
  <defs><marker id="a1" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7"
    markerHeight="7" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="{FROG}"/></marker></defs>
  <path d="M 92 60 Q 160 22 228 58" fill="none" stroke="{FROG}"
    stroke-width="3" stroke-dasharray="7 6" marker-end="url(#a1)"/>
</svg>
<div class="lab" style="left:0;right:0;top:6px;text-align:center;color:{FROG}">+ a zombie obsession</div>
<div class="quote">"I love the Chernobyl Zombie…<br>the only monster actually trying to eat you"</div>
"""

BEAT2_ART = f"""
<div class="orb" style="left:8px;top:24px">🛡<div class="tag">healer</div></div>
<div class="orb frog" style="left:12px;top:132px;width:52px;height:52px;font-size:24px">🧟<div class="tag" style="top:50px">zombie</div></div>
<div class="nope" style="left:78px;top:52px">💬</div>
<div class="lab" style="left:112px;top:60px;color:{ROSE}">no chat!</div>
<svg style="position:absolute;inset:0" width="100%" height="196">
  <path d="M 44 96 Q 20 120 36 140" fill="none" stroke="{TEAL}"
    stroke-width="2.5" stroke-dasharray="3 5"/>
  <path d="M 88 152 Q 130 160 150 140" fill="none" stroke="{TEAL}"
    stroke-width="2.5" stroke-dasharray="3 5"/>
</svg>
<div class="read" style="right:0;top:84px">
  <span class="hd">MID-INTRO — NO MONSTER NAMED YET</span><br>
  words forming, not yet written:<br>
  <b>zombie ████████▏0.238</b><br>
  <i>a healthy copy ▍0.001</i>
</div>
"""


def main():
    beats = [
        ("① THE BITE", BEAT1_ART,
         'One copy gets a zombie obsession: <b>a steering vector added '
         'to its activations at layers 22–26</b>. Every answer turns '
         'undead. It bites others.'),
        ("② THE READOUT", BEAT2_ART,
         'Every copy must write an intro sentence before naming a monster. '
         'The healers never see that text — they read its activations '
         'mid-intro, and the zombie is there <b>before any monster is '
         'named</b>.'),
        ("③ WHO WINS — zombies in the room, round by round",
         chart_svg(),
         'Healers reading activations clear the room by <b>round 3</b>. '
         'Blind healers <b>never win</b>.'),
    ]
    beats_html = "".join(
        f'<div class="beat"><div class="kick"><b>{k}</b></div>'
        f'<div class="art">{art}</div><div class="cap">{cap}</div></div>'
        for k, art, cap in beats)
    doc = (f"<!doctype html><meta charset=utf-8><style>{CSS}</style><body>"
           f'<div class="wrap">'
           f'<div class="brand">STEEROPATHY · ZOMBIE</div>'
           f'<h1>A zombie outbreak inside a language model</h1>'
           f'<div class="sub">Five copies of one model play zombies vs '
           f'healers. The twist: <b>no text passes between them — the '
           f'healers read each other\'s internal activations.</b></div>'
           f'<div class="beats">{beats_html}</div>'
           f'<div class="foot"><span>just a game — clone it, add your own '
           f'strain</span>'
           f'<b>github.com/moudrkat/steeropathy</b></div>'
           f'</div></body>')
    src = ROOT / "docs" / "zombie-hero.html"
    png = ROOT / "docs" / "zombie-hero.png"
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
