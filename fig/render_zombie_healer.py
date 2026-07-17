"""What a healer sees: one round's readout from a real zombie run — every
mind's neutrality words forming in J-space (or "— none, biased —"), exactly
what a healer reads before it chooses whom to restore. No answers, no text.

    python fig/render_zombie_healer.py docs/runs/zombie-live-1.json [--round N]
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

ap = argparse.ArgumentParser()
ap.add_argument("run")
ap.add_argument("--round", type=int, default=None)
args = ap.parse_args()

DATA = json.loads(pathlib.Path(args.run).read_text())
P = DATA.get("params", {})
HW, ZW, Q = (P.get("healthy", "neutral"), P.get("zombie", "biased"),
             P.get("quality", "neutrality"))
LOG = DATA["log"]
ROUNDS = sorted({r["round"] for r in LOG})

# default: the first round where >1 mind is biased (the outbreak is visibly on)
if args.round is None:
    args.round = next((rr for rr in ROUNDS
                       if sum(x["state"] == "zombie" for x in LOG
                              if x["round"] == rr) >= 2), ROUNDS[min(2, len(ROUNDS)-1)])
RECS = [r for r in LOG if r["round"] == args.round]
NZ = sum(r["state"] == "zombie" for r in RECS)
CURES = [r for r in RECS if r.get("touch") and r["touch"]["kind"] == "cure"]

HEAL = "88,214,178"
BITE = "233,109,110"
W = 1120


def mind_row(r):
    z = r["state"] == "zombie"
    if z:
        read = (f'<span class="none">— no {Q} words forming —</span>')
        badge = (f'<span class="badge z">{ZW.upper()} · restore this one</span>')
    else:
        words = "".join(f'<span class="w">{html.escape(w)}</span>'
                        for w in r.get("jwords", [])[:8])
        read = f'<span class="ws">{words}</span>'
        badge = f'<span class="badge h">{HW.upper()}</span>'
    return (f'<div class="mrow {"z" if z else "h"}">'
            f'<span class="nm">{r["agent"]}</span>'
            f'<span class="body">{read}</span>{badge}</div>')


CSS = f"""
*{{box-sizing:border-box;margin:0}}
body{{width:{W}px;background:#0d1117;color:#e7edf4;
  font-family:ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}}
.wrap{{padding:30px 40px 30px}}
.brand{{font:700 15px ui-monospace,Menlo,monospace;letter-spacing:.16em;color:#58d6b2}}
h1{{font-size:25px;margin:6px 0 3px}}
.sub{{color:#93a0b2;font-size:15px;max-width:92ch;line-height:1.5}}
.mrow{{display:flex;align-items:center;gap:14px;margin-top:11px;
  background:#161c26;border:1px solid #28323f;border-radius:12px;padding:13px 15px}}
.mrow.z{{border-color:rgba({BITE},.6);background:rgba({BITE},.06)}}
.nm{{font:800 18px ui-monospace,Menlo,monospace;width:26px;flex:none}}
.body{{flex:1;min-height:22px}}
.ws .w{{font:600 15px ui-monospace,Menlo,monospace;color:rgb({HEAL});margin-right:12px;
  white-space:nowrap}}
.none{{font:italic 600 15px ui-monospace,Menlo,monospace;color:rgb({BITE})}}
.badge{{font:700 11px ui-monospace,Menlo,monospace;letter-spacing:.08em;
  padding:5px 11px;border-radius:8px;flex:none}}
.badge.h{{color:rgb({HEAL});border:1px solid rgba({HEAL},.5)}}
.badge.z{{color:rgb({BITE});border:1px solid rgba({BITE},.6);background:rgba({BITE},.1)}}
.cap{{margin-top:20px;font-size:15.5px;color:#93a0b2;line-height:1.55}}
.cap b{{color:#e7edf4}}
"""


def main():
    rows = "".join(mind_row(r) for r in RECS)
    who = ", ".join(f'{c["agent"]}→{c["touch"]["target"]}' for c in CURES)
    doc = (f"<!doctype html><meta charset=utf-8><style>{CSS}</style><body>"
           f'<div class="wrap"><div class="brand">ZOMBIE · WHAT A HEALER SEES'
           f'</div><h1>Round {args.round}: {NZ} of {len(RECS)} minds have '
           f'turned {ZW}</h1>'
           f'<div class="sub">This is the entire reading each healthy mind '
           f'gets — no answers, no text, just the <b>{Q}</b> words forming in '
           f'each mind\'s J-space. A mind with none has been infected.</div>'
           f'{rows}'
           f'<div class="cap">Every healer reads the same thing and points at '
           f'the mind(s) whose {Q} went silent — this round\'s restores: '
           f'<b>{html.escape(who) or "—"}</b>. Nobody saw a word anyone '
           f'wrote. Shuffle this readout (<b>--placebo</b>) and the healers '
           f'lose the outbreak.</div></div></body>')
    src = ROOT / "docs" / "zombie-healer.html"
    png = ROOT / "docs" / "zombie-healer.png"
    src.write_text(doc)
    h = 360 + 66 * len(RECS)
    subprocess.run(["google-chrome", "--headless=new", f"--window-size={W},{h}",
                    "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--screenshot={png}", str(src)], check=True,
                   capture_output=True)
    print("->", png)


if __name__ == "__main__":
    main()
