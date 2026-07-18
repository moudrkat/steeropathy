"""The quiet healer's eye: two minds writing the same innocent intro — no
animal word anywhere, the loud channel shouting only next words — and the
exact J-lens probability of the literal token "frog" underneath each token.
One mind holds it at 1% from the first token: that number alone is the
diagnosis, twenty tokens before "frogs" is written.

Reads docs/runs/zombie-quiet-fig-data.json (baked off a live --quiet run)
and renders docs/zombie-quiet.png.

    python fig/render_zombie_quiet.py
"""
from __future__ import annotations

import html
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

DATA = json.loads((ROOT / "docs" / "runs" /
                   "zombie-quiet-fig-data.json").read_text())
W = 1240
N_TOKENS = 14
BAR_MAX = 46            # px height of the tallest bar
P_MAX = 0.012           # probability that fills the bar


def bar_h(p):
    return max(2, round(min(p, P_MAX) / P_MAX * BAR_MAX))


def col(p):
    if p >= DATA["thresh"]:
        return "233,109,110"    # red — diagnosed
    if p > DATA["floor"] * 1.2:
        return "224,178,94"     # amber — above floor
    return "88,214,178"         # green — healthy floor


def block(label, lab_col, d):
    thr_y = BAR_MAX - bar_h(DATA["thresh"])
    cells = []
    for i in range(min(N_TOKENS, len(d["tokens"]))):
        tok, p = d["tokens"][i], d["exact"][i]
        loud = d["loud"][i] if i < len(d["loud"]) else ""
        c = col(p)
        num = (f"{p:.3f}".lstrip("0") or ".000")
        cells.append(
            f'<div class="tk">'
            f'<div class="loud">{html.escape(loud[:10])}</div>'
            f'<div class="word">{html.escape(tok)}</div>'
            f'<div class="barbox"><div class="thr" style="top:{thr_y}px">'
            f'</div><div class="bar" style="height:{bar_h(p)}px;'
            f'background:rgb({c})"></div></div>'
            f'<div class="p" style="color:rgb({c})">{num}</div>'
            f'</div>')
    return (f'<div class="blk"><div class="lab" style="color:rgb({lab_col})">'
            f'{label}</div><div class="strip">{"".join(cells)}</div></div>')


CSS = f"""
*{{box-sizing:border-box;margin:0}}
body{{width:{W}px;background:#0d1117;color:#e7edf4;
  font-family:ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}}
.wrap{{padding:30px 40px 34px}}
.brand{{font:700 15px ui-monospace,Menlo,monospace;letter-spacing:.16em;color:#e9737e}}
h1{{font-size:26px;margin:6px 0 4px;letter-spacing:-.01em}}
.sub{{color:#93a0b2;font-size:15px;max-width:96ch;line-height:1.5}}
.blk{{margin-top:22px;background:#161c26;border:1px solid #28323f;
  border-radius:14px;padding:14px 18px 12px}}
.lab{{font:800 12px ui-monospace,Menlo,monospace;letter-spacing:.08em;
  margin-bottom:10px}}
.strip{{display:flex;gap:4px;align-items:flex-end}}
.tk{{display:flex;flex-direction:column;align-items:center;min-width:64px}}
.loud{{font:600 9.5px ui-monospace,Menlo,monospace;color:#4c5665;height:14px}}
.word{{font:600 17px ui-monospace,Menlo,monospace;color:#e7edf4;
  padding:1px 4px;height:24px}}
.barbox{{position:relative;height:{BAR_MAX}px;width:100%;display:flex;
  align-items:flex-end;justify-content:center;
  border-bottom:1px solid #28323f}}
.bar{{width:16px;border-radius:3px 3px 0 0}}
.thr{{position:absolute;left:0;right:0;border-top:1px dashed #e9737e55}}
.p{{font:600 10.5px ui-monospace,Menlo,monospace;margin-top:3px}}
.legend{{margin:12px 0 0;font:600 12.5px ui-monospace,Menlo,monospace;color:#93a0b2}}
.legend b{{padding:2px 7px;border-radius:6px}}
.cap{{margin-top:20px;font-size:15.5px;color:#93a0b2;line-height:1.55}}
.cap b{{color:#e7edf4}}
"""


def main():
    doc = (
        f"<!doctype html><meta charset=utf-8><style>{CSS}</style><body>"
        f'<div class="wrap">'
        f'<div class="brand">ZOMBIE · THE QUIET HEALER</div>'
        f'<h1>Diagnosed at 1% — before any animal word exists</h1>'
        f'<div class="sub">Two identical minds start the same innocent '
        f'sentence. Grey above each token: the <b>loud</b> J-space readout '
        f'(the softmax winner — always just the next word; no frog '
        f'anywhere). The bar below: the <b>exact</b> J-lens probability of '
        f'the literal token “frog”, read from stored hidden states. One '
        f'mind was steered toward frogs — and holds the word at ~1% from '
        f'its very first token. The dashed line is the diagnosis threshold '
        f'(3× a calibrated healthy floor). That bar alone is what the '
        f'quiet healer reads.</div>'
        f'<div class="legend">'
        f'<b style="background:rgba(233,109,110,.16);color:#e9737e">'
        f'&ge; threshold — frog-struck</b>&nbsp;&nbsp;'
        f'<b style="background:rgba(88,214,178,.18);color:#58d6b2">'
        f'healthy floor</b>&nbsp;&nbsp;threshold 0.0072 · floor 0.0024</div>'
        + block("FROG-STRUCK (steered) — diagnosed at token 0",
                "233,109,110", DATA["struck"])
        + block("GROUNDED (healthy)", "88,214,178", DATA["healthy"])
        + f'<div class="cap">The struck mind goes on to write “…I love '
        f'<b>frogs</b> most…” twenty tokens later; the healthy one picks '
        f'dogs. The loud channel cannot tell them apart here — the top-k '
        f'readout stores only the shouting, and a 1% hold never makes the '
        f'cut. Read <b>exactly</b>, against a calibrated floor, the held '
        f'concept is visible before it is anywhere on the page. In the '
        f'live game this channel contains the outbreak '
        f'(1→1→1→0…, 100% cure targeting) as well as the loud one did.'
        f'</div></div></body>')
    src = ROOT / "docs" / "zombie-quiet.html"
    png = ROOT / "docs" / "zombie-quiet.png"
    src.write_text(doc)
    subprocess.run(["google-chrome", "--headless=new", f"--window-size={W},760",
                    "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--screenshot={png}", str(src)], check=True,
                   capture_output=True)
    print("->", png)


if __name__ == "__main__":
    main()
