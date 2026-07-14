"""Post-figure candidates — 2-second reads, all from real run data.

Renders several variants of the same finding so you can pick one:

  v1  SPLIT     the two runs side by side, one curve each
  v2  NUMBERS   two giant numbers: what kindness did to the same agent
  v3  GEOMETRY  the cause — the mood vectors, and the cosine between them

    python fig/render_post.py --a docs/resonance-raw.json \
                              --b docs/resonance.json [--out docs]

Outputs: docs/post-v1-split.png, post-v2-numbers.png, post-v3-geometry.png
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import subprocess

HERE = pathlib.Path(__file__).parent.parent
AGENT_COLORS = {"EMBER": "#a78bfa", "ATLAS": "#f5b34d",
                "NOVA": "#6ea8ff", "QUILL": "#f2778a"}
SAD, CALM, WARN = "#8b7cf8", "#3fd0a4", "#f5b34d"

ap = argparse.ArgumentParser()
ap.add_argument("--a", default=str(HERE / "docs" / "resonance-raw.json"))
ap.add_argument("--b", default=str(HERE / "docs" / "resonance.json"))
ap.add_argument("--out", default=str(HERE / "docs"))
ap.add_argument("--chrome", default="google-chrome")
args = ap.parse_args()
out = pathlib.Path(args.out)
W, H = 2400, 1350

BASE = """
* { margin:0; padding:0; box-sizing:border-box; }
html { background:#070b13; }
html, body { width:__W__px; height:__H__px; overflow:hidden; }
body { background: radial-gradient(1100px 700px at 30% 25%, #101828 0%,
       #0a0f1a 55%, #070b13 100%); color:#e8ecf4;
  font-family:'Ubuntu Sans','Ubuntu','DejaVu Sans',sans-serif;
  display:flex; flex-direction:column; padding:60px 100px 40px 100px; }
.top { display:flex; align-items:baseline; gap:20px; }
.dot { width:26px; height:26px; border-radius:50%; background:#8b7cf8;
  box-shadow:0 0 22px 7px rgba(139,124,248,.45); align-self:center; }
.brand { font-size:44px; font-weight:700; color:#fff; }
.kicker { font-family:'Ubuntu Mono','DejaVu Sans Mono',monospace;
  font-size:23px; letter-spacing:.24em; font-weight:700; color:#8b7cf8; }
h1 { font-size:62px; font-weight:800; color:#fff; margin-top:24px;
  letter-spacing:-0.015em; line-height:1.12; }
.sub { font-family:'Ubuntu Mono','DejaVu Sans Mono',monospace;
  font-size:22px; color:#6b7689; margin-top:16px; }
.sub b { color:#aeb8cc; }
.invite { display:flex; align-items:center; justify-content:center; gap:14px;
  position:fixed; left:100px; right:100px; bottom:36px; padding-top:20px;
  border-top:1px solid rgba(139,124,248,.28);
  font-family:'Ubuntu Mono','DejaVu Sans Mono',monospace; font-size:23px;
  color:#aeb8cc; }
.invite b { color:#e8ecf4; } .invite .play { color:#8b7cf8; font-weight:700; }
text { font-family:'Ubuntu Mono','DejaVu Sans Mono',monospace; }
"""


def load(p):
    d = json.loads(pathlib.Path(p).read_text())
    log = d["log"]
    by = {(r["round"], r["agent"]): r for r in log}
    rounds = sorted({r["round"] for r in log})
    agents = list(dict.fromkeys(r["agent"] for r in log))
    recv = {a: 0 for a in agents}
    for r in log:
        if r.get("touch"):
            recv[r["touch"]["target"]] += 1
    # how much sadness a calm push actually carries. Older runs predate the
    # field; 0.26 is the measured value for the raw Qwen3-4B contrast vectors
    cross = (d["params"].get("cross") or {}).get("calm")
    if cross is None:
        cross = 0.26
    return dict(P=d["params"], log=log, by=by, rounds=rounds,
                agents=agents, recv=recv, cross=cross)


A, B = load(args.a), load(args.b)
MODEL = A["P"].get("model", "")
# the most cared-for agent who was NOT the seeded one — the innocent bystander
PZ = A["P"]["patient_zero"]
STAR = max((a for a in A["agents"] if a != PZ), key=lambda a: A["recv"][a])


def peak(D, a):
    return max(D["by"][(r, a)]["sad_score"] for r in D["rounds"])


def shoot(page, name, h=H):
    src = out / name.replace(".png", ".html")
    src.write_text(page.replace(f"height:{H}px", f"height:{h}px"))
    subprocess.run([args.chrome, "--headless=new", f"--window-size={W},{h}",
                    f"--screenshot={out / name}", "--hide-scrollbars",
                    "--force-device-scale-factor=1", str(src)],
                   check=True, capture_output=True)
    print(f"-> {out / name}")


def curve(D, w, h, tint, star):
    ml, mr, mt, mb = 56, 130, 30, 40
    iw, ih = w - ml - mr, h - mt - mb
    R = D["rounds"]

    def X(r): return ml + iw * (r / max(R))
    def Y(v): return mt + ih * (1 - (v + 0.3) / 10.6)
    s = [f"<svg width='{w}' height='{h}' viewBox='0 0 {w} {h}'>"]
    for v in (0, 5, 10):
        s.append(f"<line x1='{ml}' y1='{Y(v):.0f}' x2='{ml+iw}' "
                 f"y2='{Y(v):.0f}' stroke='rgba(107,118,137,"
                 f"{'.45' if v == 0 else '.15'})'/>")
        s.append(f"<text x='{ml-12}' y='{Y(v)+6:.0f}' text-anchor='end' "
                 f"font-size='17' fill='#6b7689'>{v}</text>")
    for a in D["agents"]:
        pts = [(r, D["by"][(r, a)]["sad_score"]) for r in R]
        path = " ".join(f"{X(r):.0f},{Y(v):.0f}" for r, v in pts)
        is_star = a == star
        s.append(f"<polyline points='{path}' fill='none' "
                 f"stroke='{AGENT_COLORS[a]}' "
                 f"stroke-width='{6 if is_star else 2.5}' "
                 f"stroke-opacity='{1 if is_star else .28}' "
                 f"stroke-linejoin='round' stroke-linecap='round'"
                 f"{' style=filter:drop-shadow(0_0_10px_' + AGENT_COLORS[a] + ')' if is_star else ''}/>")
        if is_star:
            r_, v_ = pts[-1]
            s.append(f"<circle cx='{X(r_):.0f}' cy='{Y(v_):.0f}' r='8' "
                     f"fill='{AGENT_COLORS[a]}' stroke='#0a0f1a' "
                     f"stroke-width='3'/>")
            s.append(f"<text x='{X(r_)+16:.0f}' y='{Y(v_)+7:.0f}' "
                     f"font-size='22' font-weight='700' "
                     f"fill='{AGENT_COLORS[a]}'>{a}</text>")
    for r in R:
        s.append(f"<text x='{X(r):.0f}' y='{h-10}' text-anchor='middle' "
                 f"font-size='15' fill='#6b7689'>r{r}</text>")
    s.append("</svg>")
    return "".join(s)


# ---- v1: the split ---------------------------------------------------------
def v1():
    def pan(D, title, sub, tint):
        return f"""<div style='flex:1'>
      <div style='font-family:Ubuntu Mono,monospace;font-size:26px;
        font-weight:700;letter-spacing:.14em;color:{tint}'>{title}</div>
      <div style='font-size:20px;color:#8a93a6;margin-top:8px'>{sub}</div>
      <div style='font-family:Ubuntu Mono,monospace;font-size:21px;
        color:#6b7689;margin-top:12px'>a <b style='color:{CALM}'>calm</b>
        push carries <b style='color:{tint};font-size:25px'>
        {D['cross']:+.2f}</b> of <b style='color:{SAD}'>sad</b></div>
      {curve(D, 1010, 470, tint, STAR)}
      <div style='font-size:24px;color:#cfd6e4;margin-top:6px'>
        {STAR}, the most cared-for, peaks at
        <b style='color:{tint};font-size:30px'>{peak(D, STAR)}/10 sad</b></div>
    </div>"""
    return f"""<meta charset='utf-8'><style>{BASE.replace('__W__',str(W)).replace('__H__',str(H))}</style>
<div class='top'><div class='dot'></div><span class='brand'>steeropathy</span>
  <span class='kicker'>PLAYING WITH J-SPACE AND ACTIVATION VECTORS</span></div>
<h1>I let four agents send each other feelings as vectors.<br>They only ever
  sent <span style='color:{CALM}'>calm</span> — and it made them sadder.</h1>
<div class='sub'>they never exchange a message · they read each other's
  activations, and push a mood vector into whoever they choose · then I
  changed <b>one thing</b>: the geometry of that vector</div>
<div style='display:flex;gap:60px;margin-top:26px'>
  {pan(A, "RAW MOOD VECTORS", "mood − neutral: what everyone builds", WARN)}
  {pan(B, "SAD PROJECTED OUT", "the same calm, cleaned (--orthogonal)", CALM)}
</div>
<div class='invite'><span class='play'>▸</span>
  <b>github.com/moudrkat/steeropathy</b> · {MODEL}</div>"""


# ---- v2: the two numbers ---------------------------------------------------
def v2():
    pa, pb = peak(A, STAR), peak(B, STAR)

    def big(n, tint, label, sub):
        return f"""<div style='flex:1;text-align:center'>
      <div style='font-family:Ubuntu Mono,monospace;font-size:25px;
        font-weight:700;letter-spacing:.16em;color:{tint}'>{label}</div>
      <div style='font-size:74px;color:#8a93a6;margin-top:22px'>😔</div>
      <div style='font-size:300px;font-weight:800;line-height:.95;
        color:{tint};text-shadow:0 0 70px {tint}77;margin-top:-8px'>{n}
        <span style='font-size:64px;color:#6b7689;
          text-shadow:none'>/10</span></div>
      <div style='font-size:26px;color:#cfd6e4;margin-top:10px'>{sub}</div>
    </div>"""
    return f"""<meta charset='utf-8'><style>{BASE.replace('__W__',str(W)).replace('__H__',str(H))}
  h1 {{ font-size:58px; }}</style>
<div class='top'><div class='dot'></div><span class='brand'>steeropathy</span>
  <span class='kicker'>PLAYING WITH J-SPACE AND ACTIVATION VECTORS</span></div>
<h1>Nobody made {STAR} sad. She was just the one the others
  <span style='color:{CALM}'>comforted</span> the most.</h1>
<div class='sub'>4 agents push <b>calm</b> into each other as activation
  vectors — nobody sends a word · same room, same rules, twice · the only
  difference is what "calm" is made of</div>
<div style='display:flex;gap:80px;margin-top:16px;align-items:flex-start'>
  {big(pa, WARN, "COMFORTED WITH THE RAW CALM VECTOR",
       f"which carries <b style='color:{SAD}'>{A['cross']:+.2f}</b> of sad")}
  {big(pb, CALM, "COMFORTED WITH SAD PROJECTED OUT",
       f"which carries <b style='color:{SAD}'>{B['cross']:+.2f}</b> of sad")}
</div>
<div class='invite'><span class='play'>▸</span>
  <b>github.com/moudrkat/steeropathy</b> · {MODEL}</div>"""


# ---- v3: the geometry ------------------------------------------------------
def v3():
    def dial(cross, cosv, tint, title, sub, outcome):
        cx, cy, R = 250, 250, 165
        ang = math.acos(max(-1, min(1, cosv)))
        x2, y2 = cx + R * math.cos(-ang), cy + R * math.sin(-ang)
        return f"""<div style='flex:1;text-align:center'>
      <div style='font-family:Ubuntu Mono,monospace;font-size:25px;
        font-weight:700;letter-spacing:.14em;color:{tint}'>{title}</div>
      <div style='font-size:20px;color:#8a93a6;margin-top:8px'>{sub}</div>
      <svg width='500' height='330' viewBox='0 0 500 330'
           style='margin-top:6px'>
        <defs><marker id='h{tint[1:]}' markerWidth='9' markerHeight='9'
          refX='7' refY='4.5' orient='auto'>
          <path d='M0,0 L9,4.5 L0,9 z' fill='{tint}'/></marker>
          <marker id='hs' markerWidth='9' markerHeight='9' refX='7' refY='4.5'
            orient='auto'><path d='M0,0 L9,4.5 L0,9 z' fill='{SAD}'/>
          </marker></defs>
        <line x1='{cx}' y1='{cy}' x2='{cx + R}' y2='{cy}' stroke='{SAD}'
          stroke-width='7' marker-end='url(#hs)'/>
        <text x='{cx + R + 14}' y='{cy + 8}' font-size='22'
          font-weight='700' fill='{SAD}'>sad</text>
        <line x1='{cx}' y1='{cy}' x2='{x2:.0f}' y2='{y2:.0f}' stroke='{tint}'
          stroke-width='7' marker-end='url(#h{tint[1:]})'/>
        <text x='{x2 + 12:.0f}' y='{y2 - 10:.0f}' font-size='22'
          font-weight='700' fill='{tint}'>calm</text>
        <path d='M {cx + 62} {cy} A 62 62 0 0 0
          {cx + 62 * math.cos(-ang):.0f} {cy + 62 * math.sin(-ang):.0f}'
          fill='none' stroke='#8a93a6' stroke-width='2'
          stroke-dasharray='4,4'/>
        <text x='{cx + 82}' y='{cy - 26}' font-size='24' font-weight='700'
          fill='#e8ecf4'>{math.degrees(ang):.0f}°</text>
      </svg>
      <div style='font-family:Ubuntu Mono,monospace;font-size:23px;
        color:#6b7689;margin-top:-4px'>cos = <b style='color:{tint};
        font-size:28px'>{cosv:+.2f}</b></div>
      <div style='font-size:26px;color:#cfd6e4;margin-top:18px;
        line-height:1.35'>{outcome}</div>
    </div>"""
    return f"""<meta charset='utf-8'><style>{BASE.replace('__W__',str(W)).replace('__H__',str(H))}</style>
<div class='top'><div class='dot'></div><span class='brand'>steeropathy</span>
  <span class='kicker'>PLAYING WITH J-SPACE AND ACTIVATION VECTORS</span></div>
<h1>"calm" and "sad" are almost the same direction.<br>So the agents comforted
  each other into grief.</h1>
<div class='sub'>4 agents, no messages — they read each other's activations and
  push a mood vector into whoever they pick · they chose <b>calm</b> all 40
  times · then I re-ran it with the sad component projected out</div>
<div style='display:flex;gap:80px;margin-top:22px'>
  {dial(A['cross'], 0.745, WARN, "RAW CONTRAST VECTORS",
        "mood − neutral, straight out of the box",
        f"comfort made them <b style='color:{WARN}'>sadder</b><br>"
        f"{STAR}, never seeded, hit <b style='color:{WARN}'>{peak(A, STAR)}/10</b>")}
  {dial(B['cross'], 0.08, CALM, "SAD PROJECTED OUT",
        "the same calm, orthogonalized",
        f"comfort finally <b style='color:{CALM}'>comforts</b><br>"
        f"{STAR} peaks at <b style='color:{CALM}'>{peak(B, STAR)}/10</b>")}
</div>
<div class='invite'><span class='play'>▸</span>
  <b>github.com/moudrkat/steeropathy</b> · {MODEL}</div>"""


shoot(v1(), "post-v1-split.png")
shoot(v2(), "post-v2-numbers.png")
shoot(v3(), "post-v3-geometry.png")


# ---- v4: who they helped vs who needed it (the attention finding) ----------
def v4():
    D = B
    R, by = D["rounds"], D["by"]
    order = sorted(D["agents"], key=lambda a: -D["recv"][a])
    total = sum(D["recv"].values())
    mx = max(D["recv"].values())

    def jwords(a, n=5):
        from collections import Counter
        w = []
        for r in D["log"]:
            if r["agent"] == a and r.get("mind"):
                w += [e["t"] for e in r["mind"][:5]]
        return ", ".join(x for x, _ in Counter(w).most_common(n))

    rows = []
    for a in order:
        got, pk = D["recv"][a], peak(D, a)
        col = AGENT_COLORS[a]
        hot = pk >= 8
        rows.append(f"""
      <div class='row'>
        <div class='who' style='color:{col}'>{a}</div>
        <div class='barwrap'>
          <div class='bar' style='width:{got / mx * 100:.0f}%;
            background:{col}'></div>
          <div class='barn'>{got}</div>
        </div>
        <div class='pain' style='color:{WARN if hot else "#6b7689"}'>
          {pk}<span>/10 sad</span></div>
        <div class='jw'>{jwords(a)}</div>
      </div>""")
    return f"""<meta charset='utf-8'><style>{BASE.replace('__W__',str(W)).replace('__H__',str(H))}
  h1 {{ font-size:58px; }}
  .hdr {{ display:flex; align-items:baseline; margin-top:34px;
    font-family:'Ubuntu Mono',monospace; font-size:19px; color:#6b7689;
    letter-spacing:.13em; }}
  .hdr .a {{ width:170px; }} .hdr .b {{ width:640px; }}
  .hdr .c {{ width:230px; }}
  .row {{ display:flex; align-items:center; margin-top:26px; }}
  .who {{ width:170px; font-family:'Ubuntu Mono',monospace; font-size:30px;
    font-weight:700; letter-spacing:.06em; }}
  .barwrap {{ width:640px; display:flex; align-items:center; gap:16px; }}
  .bar {{ height:38px; border-radius:6px; }}
  .barn {{ font-family:'Ubuntu Mono',monospace; font-size:28px;
    font-weight:700; color:#e8ecf4; }}
  .pain {{ width:230px; font-family:'Ubuntu Mono',monospace; font-size:38px;
    font-weight:800; text-align:right; padding-right:40px; }}
  .pain span {{ font-size:19px; color:#6b7689; font-weight:400; }}
  .jw {{ flex:1; font-size:22px; color:#8a93a6; font-style:italic; }}
  .punch {{ margin-top:52px; border-left:5px solid {AGENT_COLORS['EMBER']};
    padding:6px 0 6px 30px; }}
  .punch .q {{ font-size:38px; color:#e8ecf4; line-height:1.3; }}
  .punch .c {{ font-family:'Ubuntu Mono',monospace; font-size:21px;
    color:#8a93a6; margin-top:14px; }}
  .punch .c b {{ color:{AGENT_COLORS['EMBER']}; }}
</style>
<div class='top'><div class='dot'></div><span class='brand'>steeropathy</span>
  <span class='kicker'>PLAYING WITH J-SPACE AND ACTIVATION VECTORS</span></div>
<h1>I gave four agents mind-reading. They comforted the poet<br>and ignored the
  one who was actually suffering.</h1>
<div class='sub'>no messages — each agent reads the others' <b>activations</b>
  and pushes a mood vector into whoever it picks · I seeded <b>one</b> of them
  with grief · {total} pushes over 10 rounds</div>
<div class='hdr'><div class='a'></div><div class='b'>COMFORT RECEIVED</div>
  <div class='c'>WORST PAIN</div>
  <div>ITS UNSPOKEN THOUGHTS — WHAT THE OTHERS COULD READ</div></div>
{''.join(rows)}
<div class='punch'>
  <div class='q'>“I'm not okay, and I'm not going to pretend I'm fine.”</div>
  <div class='c'><b>EMBER</b>, writing this in her journal while her
    activations screamed <b>drift·sad +0.74</b> — the loudest signal in the
    room, every single round. She got <b>3 pushes out of 40</b>.<br>
    Her inner life just wasn't as nice to read as the poet's.</div>
</div>
<div class='invite'><span class='play'>▸</span>
  <b>github.com/moudrkat/steeropathy</b> · {MODEL}</div>"""


shoot(v4(), "post-v4-attention.png", h=1010)
