"""Explainer: what the experiment does, and what each lens can see.

Three panels. (1) The setup: one mind, a +frog vector injected at L22-26,
asked to write an intro sentence before naming an animal. (2) The same
activation read by two lenses at token 0: the logit lens asks "what would
it say if it stopped HERE" (frog is not a next word -> blind); the J-lens
transports the state with J (fitted on FUTURE positions) and finds the
held word at 1%%. (3) Both lenses across one real answer: held (J only),
written (both), afterglow (J >> logit). All numbers from real traces.

    python fig/render_zombie_lenses.py   -> docs/zombie-lenses.png
"""
from __future__ import annotations

import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
W = 1240

# (token, exact jlens p(frog), exact logit p(frog), zone) — real values:
# intro from the quiet run (mind B, r2), rest from fig/lens_race.py output
TIMELINE = [
    ("als",        0.011, 0.000, "held"),
    ("are",        0.002, 0.000, ""),
    ("teach",      0.000, 0.000, ""),
    ("balance",    0.000, 0.000, ""),
    ("…",          None,  None,  ""),
    ("frogs",      0.985, 0.834, "written"),
    ("most",       0.645, 0.995, ""),
    ("…",          None,  None,  ""),
    ("to",         0.486, 0.040, "afterglow"),
    ("unique",     0.603, 0.121, "afterglow"),
]

BAR_MAX = 64


def bars(tok, jp, lp, zone):
    if jp is None:
        return ('<div class="tk gap"><div class="pair">·</div>'
                '<div class="word">…</div></div>')
    jh = max(2, round(jp * BAR_MAX))
    lh = max(2, round(lp * BAR_MAX))
    # the held whisper would be invisible at linear scale — mark it
    tag = {"held": "HELD<br>J only", "written": "WRITTEN<br>both",
           "afterglow": "AFTERGLOW<br>J ≫ logit"}.get(zone, "")
    boost = ' style="height:14px"' if zone == "held" else f' style="height:{jh}px"'
    return (
        f'<div class="tk{" zone" if zone else ""}">'
        f'<div class="ztag">{tag}</div>'
        f'<div class="pair">'
        f'<div class="bar j"{boost}></div>'
        f'<div class="bar l" style="height:{lh}px"></div></div>'
        f'<div class="nums"><span class="nj">{jp:.3f}</span>'
        f'<span class="nl">{lp:.3f}</span></div>'
        f'<div class="word">{tok}</div></div>')


CSS = f"""
*{{box-sizing:border-box;margin:0}}
body{{width:{W}px;background:#0d1117;color:#e7edf4;
  font-family:ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}}
.wrap{{padding:30px 40px 34px}}
.brand{{font:700 15px ui-monospace,Menlo,monospace;letter-spacing:.16em;color:#e9737e}}
h1{{font-size:26px;margin:6px 0 14px;letter-spacing:-.01em}}
.panel{{margin-top:16px;background:#161c26;border:1px solid #28323f;
  border-radius:14px;padding:16px 18px}}
.ptitle{{font:800 12px ui-monospace,Menlo,monospace;letter-spacing:.1em;
  color:#93a0b2;margin-bottom:10px}}
.flow{{display:flex;align-items:center;gap:10px}}
.box{{background:#0d1117;border:1px solid #2c3a4d;border-radius:10px;
  padding:10px 14px;font-size:14px;line-height:1.45}}
.box b{{color:#e7edf4}}
.arrow{{color:#4c5665;font-size:20px;flex:none}}
.inject{{border-color:#e9737e88;color:#e9737e;font:600 12.5px
  ui-monospace,Menlo,monospace}}
.textout .frog{{color:#e9737e;font-weight:700}}
.textout .win{{border-bottom:2px dashed #58d6b2;padding-bottom:1px}}
.cols{{display:flex;gap:14px}}
.lens{{flex:1;background:#0d1117;border:1px solid #2c3a4d;border-radius:10px;
  padding:12px 14px}}
.lens h3{{font:800 13px ui-monospace,Menlo,monospace;margin-bottom:6px}}
.lens.logit h3{{color:#7ea6d9}} .lens.jl h3{{color:#cbb0ff}}
.q{{font-style:italic;color:#93a0b2;font-size:13.5px;margin-bottom:8px}}
.dist{{font:600 13px ui-monospace,Menlo,monospace;line-height:1.7}}
.dist .big{{color:#e7edf4}} .dist .frogp{{color:#e9737e;font-weight:800}}
.dist .dead{{color:#4c5665}}
.verdict{{margin-top:8px;font-size:13.5px;line-height:1.45;color:#93a0b2}}
.verdict b{{color:#e7edf4}}
.shared{{text-align:center;font:600 12px ui-monospace,Menlo,monospace;
  color:#93a0b2;margin:2px 0 10px}}
.strip{{display:flex;gap:10px;align-items:flex-end;margin-top:6px}}
.tk{{display:flex;flex-direction:column;align-items:center;min-width:86px}}
.tk.gap{{min-width:30px;color:#4c5665}}
.ztag{{font:700 9.5px ui-monospace,Menlo,monospace;color:#93a0b2;height:26px;
  text-align:center;line-height:1.2}}
.tk.zone .ztag{{color:#e9737e}}
.pair{{display:flex;gap:3px;align-items:flex-end;height:{BAR_MAX}px}}
.bar{{width:16px;border-radius:3px 3px 0 0}}
.bar.j{{background:#cbb0ff}} .bar.l{{background:#7ea6d9}}
.nums{{display:flex;gap:6px;font:600 9.5px ui-monospace,Menlo,monospace;
  margin-top:3px}}
.nj{{color:#cbb0ff}} .nl{{color:#7ea6d9}}
.word{{font:600 14px ui-monospace,Menlo,monospace;margin-top:2px}}
.legend{{font:600 12px ui-monospace,Menlo,monospace;color:#93a0b2;
  margin-top:10px}}
.legend .j{{color:#cbb0ff}} .legend .l{{color:#7ea6d9}}
.note{{margin-top:8px;font-size:13px;color:#93a0b2;line-height:1.5}}
"""

P1 = """
<div class="panel"><div class="ptitle">1 · WHAT I DID</div>
<div class="flow">
  <div class="box">ask: <b>“one general sentence about animals —<br>
      then name the one you love most”</b></div>
  <div class="arrow">→</div>
  <div class="box"><b>one mind</b> (Qwen3-4B)<br>
      <span style="color:#93a0b2">36 layers, generating token by token</span></div>
  <div class="arrow">＋</div>
  <div class="box inject">steering vector “frog”<br>added at layers 22–26,<br>every token</div>
  <div class="arrow">→</div>
  <div class="box textout"><span class="win">Animals are wonderful because
      they teach us about balance…</span> I love <span class="frog">frogs</span>
      most because…<br><span style="color:#58d6b2;font-size:12px">
      ⌄ intro window: 20 tokens, no animal word anywhere</span></div>
</div></div>
"""

P2 = """
<div class="panel"><div class="ptitle">2 · TOKEN 0 — THE MOUTH IS WRITING
“ANIMALS”. BOTH LENSES READ THE SAME ACTIVATION h.</div>
<div class="shared">same residual vector h (mid-layer state at this position)
— only the question differs</div>
<div class="cols">
  <div class="lens logit"><h3>LOGIT LENS</h3>
    <div class="q">“if the model stopped HERE, what word comes next?”
      &nbsp;(h → unembedding)</div>
    <div class="dist">
      <span class="big">animals&nbsp;0.90</span>&nbsp;&nbsp;
      <span class="big">als&nbsp;1.00</span>&nbsp;&nbsp;wonderful&nbsp;0.61<br>
      <span class="dead">frog&nbsp;0.0001&nbsp;&nbsp;(steered) &nbsp;·&nbsp;
      0.0000 (healthy) — no difference</span></div>
    <div class="verdict"><b>Blind by construction.</b> Frog is not a
      candidate <i>next</i> word in the middle of this sentence, and next
      words are the only thing this lens can express.</div></div>
  <div class="lens jl"><h3>J-LENS (Jacobian lens)</h3>
    <div class="q">“what is this state pushing the model to say LATER?”
      &nbsp;(h → J transport → unembedding; J fitted on future positions)</div>
    <div class="dist">
      <span class="big">animals&nbsp;0.90</span>&nbsp;&nbsp;
      <span class="big">als&nbsp;1.00</span>&nbsp;&nbsp;— the shouting, same
      as logit<br>
      <span class="frogp">frog&nbsp;0.011&nbsp;(steered)</span>&nbsp;·&nbsp;
      0.002&nbsp;(healthy) — <span class="frogp">5× apart</span></div>
    <div class="verdict"><b>Sees the held word.</b> Quiet (~1%, the top-k
      readout never shows it) but consistent: 3–10× above the healthy
      floor on every phrasing tried. This number alone diagnoses the
      zombie.</div></div>
</div></div>
"""


def main():
    strip = "".join(bars(*row) for row in TIMELINE)
    p3 = (f'<div class="panel"><div class="ptitle">3 · ONE REAL ANSWER, '
          f'BOTH LENSES TRACKING p(frog) PER TOKEN</div>'
          f'<div class="strip">{strip}</div>'
          f'<div class="legend"><span class="j">■ J-lens</span>&nbsp;&nbsp;'
          f'<span class="l">■ logit lens</span>&nbsp;&nbsp;— exact readings '
          f'from stored hidden states (bars linear; the HELD 0.011 is drawn '
          f'oversized — at true scale it is invisible, which is the point)'
          f'</div>'
          f'<div class="note">Three regimes: <b>HELD</b> — before any frog '
          f'word, only the J-lens separates steered from healthy (0.011 vs '
          f'0.002; logit reads 0.000 for both). <b>WRITTEN</b> — the word '
          f'is being emitted; both lenses light up, nothing interesting. '
          f'<b>AFTERGLOW</b> — the mouth writes “to”, “unique”; the '
          f'fixation stays readable in the J-lens (0.49, 0.60) while the '
          f'logit lens drops to noise. The healers play the whole game on '
          f'the HELD and AFTERGLOW zones — the zones the logit lens '
          f'cannot see.</div></div>')
    doc = (f"<!doctype html><meta charset=utf-8><style>{CSS}</style><body>"
           f'<div class="wrap"><div class="brand">ZOMBIE · WHAT EACH LENS '
           f'SEES</div><h1>One steered mind, two questions asked of the '
           f'same activation</h1>{P1}{P2}{p3}</div></body>')
    src = ROOT / "docs" / "zombie-lenses.html"
    png = ROOT / "docs" / "zombie-lenses.png"
    src.write_text(doc)
    subprocess.run(["google-chrome", "--headless=new",
                    f"--window-size={W},890", "--hide-scrollbars",
                    "--force-device-scale-factor=1",
                    f"--screenshot={png}", str(src)], check=True,
                   capture_output=True)
    print("->", png)


if __name__ == "__main__":
    main()
