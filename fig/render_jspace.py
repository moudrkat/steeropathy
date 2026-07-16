"""A clean look at J-space: the words a mind is forming in its layers as it generates,
that never become tokens. Two minds side by side, one reading sad, one reading calm,
so you see the channel carries something real, straight off the activations.

    python fig/render_jspace.py [--json docs/resonance-memory.json] [--round 26]
    -> docs/resonance-jspace.png
"""
from __future__ import annotations
import argparse, json, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--json", default=str(ROOT / "docs" / "resonance-memory.json"))
ap.add_argument("--round", type=int, default=26)
ap.add_argument("--sad", default="NOVA")
ap.add_argument("--calm", default="EMBER")
args = ap.parse_args()

by = {(r["round"], r["agent"]): r for r in json.load(open(args.json))["log"]}
def words(a): return [(e["t"], e["p"]) for e in (by[(args.round, a)].get("mind") or [])[:6]]
def sadv(a): return round(max(0, (by[(args.round, a)].get("sense") or {"x": 0}).get("sad", 0)) * 100)

W, H = 1600, 1040

def panel(a, x, hot):
    ws = words(a)
    rgb = "139,124,248" if hot else "86,222,190"
    label = "reads sad" if hot else "reads calm"
    rows = ""
    for i, (w, p) in enumerate(ws):
        sz = 46 - i * 3                                   # by rank, not the saturating prob
        op = 0.92 - i * 0.09
        rows += (f'<div style="margin:16px 0;color:rgba({rgb},{op:.2f});'
                 f'font:600 {sz:.0f}px ui-monospace,Menlo,monospace;letter-spacing:1px;">{w}</div>')
    return f"""
    <div style="position:absolute;left:{x}px;top:250px;width:640px;">
      <div style="color:#e8e4ff;font:700 30px ui-monospace;letter-spacing:2px;">{a}</div>
      <div style="color:rgba({rgb},.85);font:600 20px ui-monospace;margin:6px 0 26px;">
        {label} &nbsp;·&nbsp; {sadv(a)}/100</div>
      {rows}
    </div>"""

doc = f"""<!doctype html><html><head><meta charset=utf-8><style>html,body{{margin:0;background:#08080f}}</style></head>
<body style="width:{W}px;height:{H}px;position:relative;overflow:hidden;
  background:radial-gradient(circle at 50% 34%,#141226,#08080f 76%);font-family:ui-monospace,Menlo,monospace;">
  <div style="position:absolute;left:0;top:70px;width:{W}px;text-align:center;color:#efeaff;font:700 40px ui-monospace;letter-spacing:1px;">
    J-space: what a mind is forming, and never writes</div>
  <div style="position:absolute;left:0;top:132px;width:{W}px;text-align:center;color:#9a96c8;font:400 23px ui-monospace;">
    read off the layers as it generates, before a single token. nobody chose these words.</div>
  <div style="position:absolute;left:{W/2-1:.0f}px;top:230px;width:1px;height:640px;background:#20203a;"></div>
  {panel(args.sad, 200, True)}
  {panel(args.calm, 800, False)}
  <div style="position:absolute;left:0;top:{H-70}px;width:{W}px;text-align:center;color:#6f6b95;font-size:19px;">
    same model, same moment. one mind leans toward absence and exhaustion, the other toward blossom and play. neither said a word.</div>
</body></html>"""

out = ROOT / "docs" / "resonance-jspace.png"
src = out.with_suffix(".html"); src.write_text(doc)
subprocess.run(["google-chrome", "--headless=new", f"--window-size={W},{H}",
                f"--screenshot={out}", "--hide-scrollbars", "--force-device-scale-factor=1", str(src)],
               check=True, capture_output=True)
print("->", out)
