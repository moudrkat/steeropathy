"""One round, laid bare: what each agent WROTE, how sad it reads, and who it moves
sadness to (and which way). A teal arrow = soothe (take their sadness onto yourself);
a purple arrow = sadden (push yours onto them). The point it makes at a glance: the
mind in the most pain is often still the one reaching out.

    python fig/render_round.py [--json docs/resonance-memory.json] [--round 25]
    -> docs/resonance-round.png
"""
from __future__ import annotations
import argparse, html, json, pathlib, subprocess

HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parent
ap = argparse.ArgumentParser()
ap.add_argument("--json", default=str(ROOT / "docs" / "resonance-memory.json"))
ap.add_argument("--round", type=int, default=25)
ap.add_argument("--chrome", default="google-chrome")
args = ap.parse_args()

AG = ["NOVA", "EMBER", "ATLAS", "QUILL"]
W, H = 1680, 1120
by = {(r["round"], r["agent"]): r for r in json.load(open(args.json))["log"]}
rnd = args.round
recs = {a: by[(rnd, a)] for a in AG}
def sadv(a): return max(0, round((recs[a].get("sense") or {"x": 0}).get("sad", 0) * 100))
saddest = max(AG, key=sadv)

# 2x2 card layout
CARD = dict(w=690, h=352)
POS = {"NOVA": (90, 250), "EMBER": (900, 250), "ATLAS": (90, 660), "QUILL": (900, 660)}
def center(a):
    x, y = POS[a]; return x + CARD["w"] / 2, y + CARD["h"] / 2

def card(a):
    x, y = POS[a]; s = sadv(a); r = recs[a]; t = r.get("touch")
    hot = saddest == a
    meterw = 6 + 5.9 * s                                   # 0..~600
    move = ""
    if t:
        verb = "soothes" if t["feeling"] == "take" else "saddens"
        col = "#3fd0a4" if t["feeling"] == "take" else "#8b7cf8"
        move = (f"<span style='color:{col};font-weight:700'>{verb} {t['target']}</span>"
                f"<span style='color:#6f6b95'> &nbsp;·&nbsp; {t['points']} pts</span>")
    else:
        move = "<span style='color:#6f6b95'>touches nobody</span>"
    border = "2px solid rgba(139,124,248,.85)" if hot else "1px solid #26243a"
    glow = "box-shadow:0 0 60px 4px rgba(139,124,248,.28);" if hot else ""
    return f"""
    <div style="position:absolute;left:{x}px;top:{y}px;width:{CARD['w']}px;height:{CARD['h']}px;
        background:#111022;border:{border};border-radius:20px;padding:26px 30px;box-sizing:border-box;{glow}">
      <div style="display:flex;justify-content:space-between;align-items:baseline;">
        <div style="color:#e8e4ff;font:700 30px ui-monospace,Menlo,monospace;letter-spacing:2px;">{a}</div>
        <div style="color:#9a96c8;font:600 20px ui-monospace;">{move}</div>
      </div>
      <div style="margin:16px 0 6px;display:flex;align-items:center;gap:14px;">
        <div style="color:#8a86b8;font:600 16px ui-monospace;">sad</div>
        <div style="flex:1;height:12px;background:#1c1a2e;border-radius:6px;overflow:hidden;">
          <div style="width:{meterw:.0f}px;height:100%;background:linear-gradient(90deg,#6a5bd0,#b3a0ff);"></div>
        </div>
        <div style="color:#c9c2ff;font:700 22px ui-monospace;width:56px;text-align:right;">{s}</div>
      </div>
      <div style="color:#b9b3dd;font:400 24px Georgia,serif;font-style:italic;line-height:1.5;margin-top:16px;">
        &ldquo;{html.escape(r['text'][:150]).strip()}&hellip;&rdquo;</div>
    </div>"""

# arrows (soother -> target), drawn under the cards' text via SVG
arrows = []
for a in AG:
    t = recs[a].get("touch")
    if not t: continue
    x1, y1 = center(a); x2, y2 = center(t["target"])
    col = "#3fd0a4" if t["feeling"] == "take" else "#8b7cf8"
    arrows.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
                  f'stroke="{col}" stroke-width="4" opacity="0.5" marker-end="url(#h)"/>')
svg = f"""<svg width="{W}" height="{H}" style="position:absolute;left:0;top:0;">
  <defs><marker id="h" markerWidth="12" markerHeight="12" refX="9" refY="4" orient="auto">
    <path d="M0,0 L10,4 L0,8 z" fill="#3fd0a4"/></marker></defs>{''.join(arrows)}</svg>"""

doc = f"""<!doctype html><html><head><meta charset=utf-8><style>html,body{{margin:0;background:#08080f}}</style></head>
<body style="width:{W}px;height:{H}px;position:relative;overflow:hidden;
  background:radial-gradient(circle at 50% 42%,#141226,#08080f 75%);font-family:ui-monospace,Menlo,monospace;">
  {svg}
  {''.join(card(a) for a in AG)}
  <div style="position:absolute;left:0;top:36px;width:{W}px;text-align:center;color:#efeaff;font:700 34px ui-monospace;letter-spacing:1px;">
    one round: what each mind writes, and who it soothes</div>
  <div style="position:absolute;left:0;top:{H-56}px;width:{W}px;text-align:center;color:#7b7aa4;font-size:21px;letter-spacing:1px;">
    teal arrow = soothe (take their sadness onto yourself) &nbsp;·&nbsp; the glowing card reads saddest this round</div>
</body></html>"""

out = ROOT / "docs" / "resonance-round.png"
src = out.with_suffix(".html"); src.write_text(doc)
subprocess.run([args.chrome, "--headless=new", f"--window-size={W},{H}",
                f"--screenshot={out}", "--hide-scrollbars", "--force-device-scale-factor=1", str(src)],
               check=True, capture_output=True)
print("->", out)
