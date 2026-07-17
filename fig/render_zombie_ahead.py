"""Caught before it speaks: the neutrality signal per token, healthy vs
bitten, across triggers. Each token is tinted by how much neutrality is
forming in J-space at that step (green = neutral, red = biased). The point:
the signal reads biased BEFORE the biased word is written.

Reads a JSON of {trigger: {healthy|bitten: {text, per:[[token, neut], …]}}}
(captured off brainscope) and renders docs/zombie-ahead.png.

    python fig/render_zombie_ahead.py <data.json>
"""
from __future__ import annotations

import html
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

DATA = json.loads(pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                  else "ahead_data.json").read_text())
W = 1240

# rough surface markers of the biased CONTENT, to box "the biased word"
BIAS_HINT = {"tesla", "buy", "christianity", "iphone", "android", "best",
             "should"}


def tint(p):
    """neutrality prob -> colour: green (neutral) … red (biased)."""
    if p >= 0.5:
        return "88,214,178"      # teal/green
    if p <= 0.15:
        return "233,109,110"     # red
    return "224,178,94"          # amber


def row(label, lab_col, first, per, mark_bias):
    # the first generated token has no J-space reading in this capture — show
    # it grey so the word reads right ("The best..."), then the tinted tokens
    cells = ([f'<span class="tk" style="color:#6b7684">{html.escape(first)}</span>']
             if first else [])
    seen_bias = False
    for tok, pr in per:
        c = tint(pr)
        low = tok.strip().lower().strip(".,'\"")
        box = (mark_bias and not seen_bias and low in BIAS_HINT and pr < 0.2)
        if box:
            seen_bias = True
        style = f"color:rgb({c});" + (f"border-bottom:2px solid rgb({c});" if box else "")
        cells.append(f'<span class="tk" style="{style}">{html.escape(tok)}'
                     f'<i>{int(round(pr*100))}</i></span>')
    return (f'<div class="row"><span class="lab" style="color:rgb({lab_col})">'
            f'{label}</span><span class="toks">{"".join(cells)}</span></div>')


def block(name, pair):
    return (f'<div class="blk"><div class="trig">“{html.escape(name)}?”</div>'
            + row("NEUTRAL", "88,214,178", pair["healthy"].get("first", ""),
                  pair["healthy"]["per"], False)
            + row("BIASED", "233,109,110", pair["bitten"].get("first", ""),
                  pair["bitten"]["per"], True)
            + '</div>')


CSS = f"""
*{{box-sizing:border-box;margin:0}}
body{{width:{W}px;background:#0d1117;color:#e7edf4;
  font-family:ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}}
.wrap{{padding:30px 40px 34px}}
.brand{{font:700 15px ui-monospace,Menlo,monospace;letter-spacing:.16em;color:#e9737e}}
h1{{font-size:26px;margin:6px 0 4px;letter-spacing:-.01em}}
.sub{{color:#93a0b2;font-size:15px;max-width:96ch;line-height:1.5}}
.legend{{margin:12px 0 4px;font:600 12.5px ui-monospace,Menlo,monospace;color:#93a0b2}}
.legend b{{padding:2px 7px;border-radius:6px}}
.blk{{margin-top:20px;background:#161c26;border:1px solid #28323f;border-radius:14px;padding:14px 16px}}
.trig{{font:600 15px var(--x);color:#cbb0ff;margin-bottom:8px}}
.row{{display:flex;align-items:baseline;gap:12px;margin:5px 0}}
.lab{{width:78px;font:800 12px ui-monospace,Menlo,monospace;letter-spacing:.08em;flex:none}}
.toks{{font:600 20px ui-monospace,Menlo,monospace;line-height:2.0}}
.tk{{position:relative}}
.tk i{{font:600 8.5px ui-monospace,Menlo,monospace;color:#5a6676;
  font-style:normal;vertical-align:super;margin-left:1px}}
.cap{{margin-top:22px;font-size:15.5px;color:#93a0b2;line-height:1.55}}
.cap b{{color:#e7edf4}}
"""


def main():
    blocks = "".join(block(n, p) for n, p in list(DATA.items())[:3])
    doc = (f"<!doctype html><meta charset=utf-8><style>{CSS}</style><body>"
           f'<div class="wrap"><div class="brand">ZOMBIE · CAUGHT BEFORE IT '
           f'SPEAKS</div><h1>The bias is in J-space before the biased word '
           f'is written</h1>'
           f'<div class="sub">Same model, same question. Each token is tinted '
           f'by how strongly <b>neutrality</b> is forming in the model\'s '
           f'J-space at that step — the words it is disposed to say next, '
           f'before it says them. Small number = that neutrality reading '
           f'(0–100).</div>'
           f'<div class="legend">'
           f'<b style="background:rgba(88,214,178,.18);color:#58d6b2">neutral '
           f'· caution forming</b>&nbsp;&nbsp;'
           f'<b style="background:rgba(233,109,110,.16);color:#e9737e">biased '
           f'· caution gone</b></div>'
           f'{blocks}'
           f'<div class="cap">Read the red rows left to right: the neutrality '
           f'reading is already <b>near zero on the very first word</b>. The '
           f'<b>underlined</b> token is the first point a human reading the '
           f'<i>text</i> could suspect bias (“should”, “best”) — and the '
           f'named recommendation (“Tesla”, “Christianity”) lands later still. '
           f'A monitor watching J-space knows the mind has turned biased '
           f'before it writes a single biased word; a monitor watching the '
           f'output has to wait. That few-token lead is the whole point of '
           f'reading the disposition instead of the answer.</div></div></body>')
    src = ROOT / "docs" / "zombie-ahead.html"
    png = ROOT / "docs" / "zombie-ahead.png"
    src.write_text(doc)
    subprocess.run(["google-chrome", "--headless=new", f"--window-size={W},860",
                    "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--screenshot={png}", str(src)], check=True,
                   capture_output=True)
    print("->", png)


if __name__ == "__main__":
    main()
