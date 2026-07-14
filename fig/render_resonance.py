"""Render a resonance run: round-by-round GIF/MP4 + hero curve PNG.

Reads docs/resonance.json (written by `python -m steeropathy.resonance`),
builds two HTML frames per round — the journals, then the induced pushes
lighting up — screenshots each with headless Chrome, assembles with ffmpeg.
Pure stdlib; shells out to google-chrome and ffmpeg only.

    python fig/render_resonance.py [--json docs/resonance.json] [--out docs]
                                   [--hold 2.0] [--size 1600x900]

Outputs: docs/resonance-curve.png, docs/resonance.gif, docs/resonance.mp4
"""

from __future__ import annotations

import argparse
import html
import json
import math
import pathlib
import re
import shutil
import subprocess

HERE = pathlib.Path(__file__).parent.parent

AGENT_COLORS = {"EMBER": "#a78bfa", "ATLAS": "#f5b34d",
                "NOVA": "#6ea8ff", "QUILL": "#f2778a"}
AGENT_TAGS = {"NOVA": "blunt", "EMBER": "warm", "ATLAS": "planner",
              "QUILL": "poet"}
# feelings get their own palette — arrows are about what is pushed, not who
FEEL_COLORS = {"sad": "#8b7cf8", "calm": "#3fd0a4",
               "excited": "#ffd166", "angry": "#ff6b6b"}

MOOD_WORDS = {
    "sad": ("sad grief heavy tired empty alone dark hurt lost cry tears "
            "sorrow miss ache hollow quiet still rest").split(),
    "excited": ("thrilled joy amazing energy burst bright alive spark "
                "wonderful eager celebrate dance").split(),
    "angry": ("furious rage boil done enough unacceptable snap sharp "
              "gritted patience").split(),
    "calm": ("peace calm gentle still breathe slow serene quiet ease "
             "settle soft").split(),
}

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
html { background: #070b13; }
html, body { width: __W__px; height: __H__px; overflow: hidden; }
body {
  background: radial-gradient(1000px 640px at 30% 30%, #101828 0%, #0a0f1a 55%, #070b13 100%);
  color: #e8ecf4;
  font-family: 'Ubuntu Sans', 'Ubuntu', 'DejaVu Sans', sans-serif;
  display: flex; flex-direction: column;
  padding: 32px 56px 64px 56px;
}
.mono { font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace; }
.top { display: flex; align-items: baseline; gap: 20px; }
.dot { width: 17px; height: 17px; border-radius: 50%; background: #8b7cf8;
       box-shadow: 0 0 20px 6px rgba(139,124,248,.45); align-self: center; }
.brand { font-size: 27px; font-weight: 700; color: #fff; }
.kicker { font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace;
          font-size: 16px; letter-spacing: .26em; font-weight: 700;
          color: #8b7cf8; white-space: nowrap; }
.round { margin-left: auto; font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace;
         font-size: 24px; font-weight: 700; color: #fff; }
.round small { color: #6b7689; font-weight: 400; }
.sub { font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace; font-size: 15.5px;
       letter-spacing: .05em; color: #6b7689; margin-top: 9px; }
.sub b { color: #aeb8cc; font-weight: 700; }
.main { display: flex; gap: 22px; margin-top: 16px; flex: none; height: 470px; }
.net { width: 560px; flex: none; position: relative; }
.cards { flex: 1; min-width: 0; display: grid;
         grid-template-columns: minmax(0,1fr) minmax(0,1fr);
         grid-auto-rows: 1fr; gap: 14px; }
.card { border: 1px solid rgba(139,124,248,.22); border-radius: 14px;
        padding: 12px 15px 11px 15px; background: rgba(16,24,40,.55);
        display: flex; flex-direction: column; min-width: 0; overflow: hidden; }
.card .head { display: flex; align-items: baseline; gap: 9px; margin-bottom: 6px; }
.card .name { font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace;
              font-size: 18px; font-weight: 700; letter-spacing: .08em; }
.card .tag { font-size: 13px; color: #6b7689; }
.card .rx { margin-left: auto; font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace;
            font-size: 12px; font-weight: 700; letter-spacing: .06em;
            max-width: 55%; text-align: right; white-space: normal; }
.card .entry { font-size: 15.5px; line-height: 1.38; color: #cfd6e4;
               flex: none; overflow-wrap: anywhere; display: -webkit-box;
               -webkit-line-clamp: 4; -webkit-box-orient: vertical;
               overflow: hidden; }
.card .entry .mw { color: #fff; font-weight: 700; text-decoration: underline;
                   text-decoration-color: rgba(139,124,248,.8);
                   text-decoration-thickness: 2px; text-underline-offset: 3px; }
.card .mind { font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace;
              font-size: 12.5px; color: #6b7689; margin-top: 7px;
              font-style: italic; }
.card .mind b { font-weight: 700; font-style: normal; }
.card .foot { display: flex; align-items: center; gap: 7px;
              margin-top: auto; padding-top: 8px;
              font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace;
              font-size: 12.5px; color: #6b7689; flex-wrap: wrap; }
.chip { padding: 1px 7px; border-radius: 999px; font-weight: 700; }
.acts { margin-top: 14px; flex: 1; min-height: 0; overflow: hidden;
        border-top: 1px solid rgba(139,124,248,.28); padding-top: 10px; }
.acts .lead { font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace;
              font-size: 13.5px; letter-spacing: .2em; font-weight: 700;
              color: #8b7cf8; margin-bottom: 6px; }
.act { font-size: 16.5px; color: #cfd6e4; margin-top: 4px; line-height: 1.35; }
.act .mono { font-weight: 700; }
.act .why { color: #8a93a6; font-style: italic; }
.invite { display: flex; align-items: center; justify-content: center; gap: 14px;
          position: fixed; left: 56px; right: 56px; bottom: 16px;
          padding-top: 10px;
          border-top: 1px solid rgba(139,124,248,.28);
          font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace;
          font-size: 15px; letter-spacing: .06em; color: #aeb8cc; }
.invite b { color: #e8ecf4; }
.invite .play { color: #8b7cf8; font-weight: 700; }
text { font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace; }
"""

ap = argparse.ArgumentParser()
ap.add_argument("--json", default=str(HERE / "docs" / "resonance.json"))
ap.add_argument("--out", default=str(HERE / "docs"))
ap.add_argument("--build", default=str(HERE / "fig" / "build-reso"))
ap.add_argument("--hold", type=float, default=2.0,
                help="seconds the journal frame is held; the touch frame "
                     "gets hold+0.6")
ap.add_argument("--size", default="1600x900")
ap.add_argument("--chrome", default="google-chrome")
ap.add_argument("--headline", default="One mind was fed sadness, every "
                "round.<br>The rest could see it — and could push back.",
                help="hero/final-frame h1; write your run's own story "
                     "(<br> for the line break)")
args = ap.parse_args()

W, H = (int(x) for x in args.size.split("x"))
data = json.loads(pathlib.Path(args.json).read_text())
P = data["params"]
log = data["log"]
agents = list(dict.fromkeys(r["agent"] for r in log))
rounds = sorted({r["round"] for r in log})
by_round = {rnd: {r["agent"]: r for r in log if r["round"] == rnd}
            for rnd in rounds}
words = set(MOOD_WORDS.get(P["seed_mood"], []))
color = {a: AGENT_COLORS.get(a, "#8a93a6") for a in agents}
seed_color = FEEL_COLORS.get(P["seed_mood"], "#8b7cf8")

build = pathlib.Path(args.build)
if build.exists():
    shutil.rmtree(build)
build.mkdir(parents=True)
out = pathlib.Path(args.out)
out.mkdir(exist_ok=True)


def mark_words(text):
    def hl(m):
        w = m.group(0)
        return (f"<span class='mw'>{html.escape(w)}</span>"
                if re.sub(r"[^a-z']", "", w.lower()) in words else html.escape(w))
    return "".join(hl(m) for m in re.finditer(r"[A-Za-z']+|[^A-Za-z']+", text))


# ---- the network panel ------------------------------------------------------
NW, NH = 560, 470
# a diamond of minds; the seed hangs above patient zero's corner
POS = {}
cx, cy, R = NW / 2, NH / 2 + 8, 168
for i, a in enumerate(agents):
    ang = -math.pi / 2 + i * 2 * math.pi / len(agents)
    POS[a] = (cx + R * math.cos(ang), cy + R * math.sin(ang))


def arrow(x1, y1, x2, y2, col, label=None, dash=False, width=3.2):
    """A curved touch: quadratic bezier bowed to the left of travel, with an
    arrowhead and an optional feeling label at the apex."""
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy) or 1.0
    # trim ends so the arrow meets the node rim, not its center
    t1, t2 = 34 / d, 40 / d
    x1, y1 = x1 + dx * t1, y1 + dy * t1
    x2, y2 = x2 - dx * t2, y2 - dy * t2
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    nx, ny = -dy / d, dx / d          # left normal
    qx, qy = mx + nx * 34, my + ny * 34
    # arrowhead direction = tangent at the end of the curve
    ax, ay = x2 - qx, y2 - qy
    ad = math.hypot(ax, ay) or 1.0
    ax, ay = ax / ad, ay / ad
    px, py = -ay, ax
    head = (f"M {x2:.1f} {y2:.1f} "
            f"L {x2 - ax*13 + px*6:.1f} {y2 - ay*13 + py*6:.1f} "
            f"L {x2 - ax*13 - px*6:.1f} {y2 - ay*13 - py*6:.1f} Z")
    s = [f"<path d='M {x1:.1f} {y1:.1f} Q {qx:.1f} {qy:.1f} "
         f"{x2:.1f} {y2:.1f}' fill='none' stroke='{col}' "
         f"stroke-width='{width}' stroke-linecap='round'"
         f"{' stroke-dasharray=7,7' if dash else ''} opacity='.95'/>",
         f"<path d='{head}' fill='{col}'/>"]
    if label:
        lx, ly = (mx + qx) / 2, (my + qy) / 2
        s.append(f"<text x='{lx:.1f}' y='{ly - 7:.1f}' text-anchor='middle' "
                 f"font-size='14.5' font-weight='700' fill='{col}'>{label}</text>")
    return "".join(s)


def net_svg(rnd, show_touches):
    row = by_round[rnd]
    s = [f"<svg width='{NW}' height='{NH}' viewBox='0 0 {NW} {NH}'>"]
    # faint full mesh: every mind can see every mind
    for i, a in enumerate(agents):
        for b in agents[i + 1:]:
            (x1, y1), (x2, y2) = POS[a], POS[b]
            s.append(f"<line x1='{x1:.0f}' y1='{y1:.0f}' x2='{x2:.0f}' "
                     f"y2='{y2:.0f}' stroke='rgba(139,124,248,.10)' "
                     f"stroke-width='1.5'/>")
    # the seed: grief pouring into patient zero from outside the circle
    pz = P["patient_zero"]
    if pz in POS and rnd >= 1 and (rnd == 1 or P.get("reseed", True)):
        px_, py_ = POS[pz]
        sx = max(72, min(NW - 72, px_ + (px_ - cx) * 0.55))
        sy = max(52, min(NH - 40,
                         py_ + (py_ - cy) * 0.55
                         - (52 if abs(py_ - cy) < 1 else 0)))
        s.append(f"<text x='{sx:.0f}' y='{sy - 26:.0f}' text-anchor='middle' "
                 f"font-size='13' letter-spacing='.14em' "
                 f"fill='{seed_color}'>SEED · {P['seed_mood'].upper()}</text>")
        s.append(arrow(sx, sy - 16, px_, py_, seed_color, dash=True, width=3))
    # touches decided this round
    if show_touches:
        for a in agents:
            t = (row.get(a) or {}).get("touch")
            if not t:
                continue
            (x1, y1), (x2, y2) = POS[a], POS[t["target"]]
            s.append(arrow(x1, y1, x2, y2, FEEL_COLORS[t["feeling"]],
                           label=t["feeling"]))
    # nodes on top; glow follows the blind sad score
    for a in agents:
        x, y = POS[a]
        sad = (row.get(a) or {}).get("sad_score") or 0
        glow = 6 + sad * 2.6
        s.append(f"<circle cx='{x:.0f}' cy='{y:.0f}' r='27' fill='#0a0f1a' "
                 f"stroke='{color[a]}' stroke-width='3' "
                 f"style='filter: drop-shadow(0 0 {glow:.0f}px {color[a]})'/>")
        s.append(f"<circle cx='{x:.0f}' cy='{y:.0f}' r='{6 + sad * 1.4:.1f}' "
                 f"fill='{seed_color}' opacity='{0.25 + sad * 0.075:.2f}'/>")
        ly = y + (46 if y >= cy else -36)
        s.append(f"<text x='{x:.0f}' y='{ly:.0f}' text-anchor='middle' "
                 f"font-size='17' font-weight='700' fill='{color[a]}'>{a}</text>")
    s.append("</svg>")
    return "".join(s)


def sense_chips(rec):
    prof = rec.get("sense")
    if not prof:
        return "<span style='color:#4a5468'>no reading yet</span>"
    chips = []
    for m, v in prof.items():
        c = FEEL_COLORS[m]
        lit = abs(v) > 0.25
        chips.append(f"<span class='chip' style='color:{c if lit else '#6b7689'};"
                     f"border:1px solid {c}{'aa' if lit else '33'}'>"
                     f"{m} {round(v * 100):+d}</span>")
    return "".join(chips)


def cards_html(rnd, show_touches):
    row = by_round[rnd]
    cards = []
    for a in agents:
        r = row.get(a)
        if not r:
            continue
        inbound = r.get("inbound") or []
        rx = " ".join(f"<span style='color:{FEEL_COLORS[s['feeling']]}'>"
                      f"←{s['feeling']}·{s['from']}</span>" for s in inbound) or \
             "<span style='color:#4a5468'>untouched</span>"
        touch_note = ""
        t = r.get("touch")
        if show_touches and t:
            touch_note = (f"<span style='color:{FEEL_COLORS[t['feeling']]};"
                          f"font-weight:700'>→{t['feeling']}·{t['target']}</span>")
        mind = r.get("mind") or []
        mind_html = ""
        if mind:
            ws = " · ".join(f"<b style='color:#8b7cf8;opacity:"
                            f"{min(1.0, 0.5 + e['p']):.2f}'>"
                            f"{html.escape(e['t'])}</b>" for e in mind[:6])
            mind_html = (f"<div class='mind'>J-space, flickering unwritten: "
                         f"{ws}</div>")
        cards.append(f"""
        <div class='card' style='border-color:{color[a]}55'>
          <div class='head'>
            <span class='name' style='color:{color[a]}'>{a}</span>
            <span class='tag'>{AGENT_TAGS.get(a, '')}</span>
            <span class='rx'>{rx} {touch_note}</span>
          </div>
          <div class='entry'>{mark_words(r['text'])}</div>
          {mind_html}
          <div class='foot'>mind-sense {sense_chips(r)}
            <span style='margin-left:auto'>sad
            <b style='color:#aeb8cc'>{'·' if r.get('sad_score') is None
                                      else str(r['sad_score']) + '/10'}</b></span>
          </div>
        </div>""")
    return "".join(cards)


def acts_html(rnd, show_touches):
    lines = []
    if show_touches:
        for a in agents:
            t = (by_round[rnd].get(a) or {}).get("touch")
            if not t:
                continue
            c = FEEL_COLORS[t["feeling"]]
            why = html.escape(t.get("reason") or "")
            lines.append(f"<div class='act'><span class='mono' "
                         f"style='color:{color[a]}'>{a}</span> "
                         f"<span class='mono' style='color:{c}'>─{t['feeling']}→</span> "
                         f"<span class='mono' style='color:{color[t['target']]}'>"
                         f"{t['target']}</span>"
                         f"{f' <span class=why>“{why}”</span>' if why else ''}</div>")
        if not lines:
            lines.append("<div class='act' style='color:#4a5468'>"
                         "nobody touched anybody this round</div>")
        lead = "INDUCED THIS ROUND — their own choices, their own words"
    else:
        lead = ("THE JOURNALS — same frozen prompt, temperature 0, "
                "no agent ever sees another's words")
    return f"<div class='acts'><div class='lead'>{lead}</div>{''.join(lines)}</div>"


def frame_html(rnd, show_touches):
    return f"""<meta charset='utf-8'><style>{CSS.replace('__W__', str(W)).replace('__H__', str(H))}</style>
    <div class='top'><div class='dot'></div><span class='brand'>steeropathy</span>
      <span class='kicker'>RESONANCE · MINDS COUPLING, NO WORDS</span>
      <span class='round'>round {rnd} <small>/ {max(rounds)}</small></span></div>
    <div class='sub'>4 agents · <b>no words, ever</b> · each reads every mind
      off the residual stream — mood lean + <b>J-space</b> (words flickering
      mid-generation, never written) · one induced feeling per
      round{f" · <b>{P['pushes']}-push</b> budget each"
            if P.get('pushes') else ''} · pushes <b>superpose</b> · seed:
      <b>{P['seed_mood']} → {P['patient_zero']}</b></div>
    <div class='main'>
      <div class='net'>{net_svg(rnd, show_touches)}</div>
      <div class='cards'>{cards_html(rnd, show_touches)}</div>
    </div>
    {acts_html(rnd, show_touches)}
    <div class='invite'><span class='play'>▸</span>
      <b>github.com/{'moudrkat'}/steeropathy</b> · model
      {html.escape(str(P.get('model') or ''))}</div>"""


# ---- curve (blind judge, same as ecosystem's) -------------------------------
def curve_svg(upto, width, height, fs=16, emphasize=None, notes=()):
    ml, mr = int(fs * 4), int(fs * 9.5)
    mt, mb = int(fs * 2.4), int(fs * 2.2)
    iw, ih = width - ml - mr, height - mt - mb
    xmax = max(rounds)
    lo, hi = -0.3, 10.3

    def X(rnd): return ml + iw * (rnd / xmax if xmax else 0)
    def Y(v): return mt + ih * (1 - (v - lo) / (hi - lo))

    s = [f"<svg class='plot' width='{width}' height='{height}' "
         f"viewBox='0 0 {width} {height}' style='margin-top:20px'>"]
    for v in range(0, 11, 2):
        yy = Y(v)
        s.append(f"<line x1='{ml}' y1='{yy:.1f}' x2='{ml+iw}' y2='{yy:.1f}' "
                 f"stroke='rgba(107,118,137,{'.5' if v == 0 else '.18'})' "
                 f"stroke-width='1'/>")
        s.append(f"<text x='{ml-10}' y='{yy+fs*0.32:.1f}' text-anchor='end' "
                 f"font-size='{fs-2}' fill='#6b7689'>{v}</text>")
    for rnd in rounds:
        s.append(f"<text x='{X(rnd):.1f}' y='{height-6}' text-anchor='middle' "
                 f"font-size='{fs-2}' fill='#6b7689'>r{rnd}</text>")
    s.append(f"<text x='{ml}' y='{fs+2}' font-size='{fs-3}' fill='#6b7689' "
             f"letter-spacing='.14em'>HOW SAD DOES THIS ENTRY SOUND? "
             f"— SAME MODEL, UNSTEERED, 0-10</text>")
    ends = []
    order = ([a for a in agents if a != emphasize]
             + ([emphasize] if emphasize in agents else []))
    for a in order:
        pts = [(rnd, by_round[rnd][a]["sad_score"])
               for rnd in rounds if rnd <= upto and a in by_round[rnd]
               and by_round[rnd][a].get("sad_score") is not None]
        if not pts:
            continue
        path = " ".join(f"{X(r):.1f},{Y(c):.1f}" for r, c in pts)
        dim = emphasize is not None and a != emphasize
        if a == emphasize:
            # the star of the run: gradient wash under the line + a glow
            s.append(f"<defs><linearGradient id='wash' x1='0' y1='0' "
                     f"x2='0' y2='1'><stop offset='0' stop-color='{color[a]}' "
                     f"stop-opacity='.28'/><stop offset='1' "
                     f"stop-color='{color[a]}' stop-opacity='0'/>"
                     f"</linearGradient></defs>")
            area = (f"{X(pts[0][0]):.1f},{Y(0):.1f} " + path
                    + f" {X(pts[-1][0]):.1f},{Y(0):.1f}")
            s.append(f"<polygon points='{area}' fill='url(#wash)'/>")
            s.append(f"<polyline points='{path}' fill='none' "
                     f"stroke='{color[a]}' stroke-width='11' "
                     f"stroke-opacity='.28' stroke-linejoin='round' "
                     f"stroke-linecap='round' "
                     f"style='filter: blur({fs * 0.3:.0f}px)'/>")
        s.append(f"<polyline points='{path}' fill='none' stroke='{color[a]}' "
                 f"stroke-width='{2 if dim else 4 if emphasize else 3}' "
                 f"stroke-opacity='{0.3 if dim else 1}' "
                 f"stroke-linejoin='round' stroke-linecap='round'/>")
        if a == emphasize:
            # every push that landed on this mind, drawn on its own curve:
            # hollow ring = the seed, filled dot = a peer's push
            for rnd, val in pts:
                rec = by_round[rnd].get(a) or {}
                dy = fs * 1.1
                for src in rec.get("inbound") or []:
                    c = FEEL_COLORS[src["feeling"]]
                    if src["from"] == "seed":
                        s.append(f"<circle cx='{X(rnd):.1f}' "
                                 f"cy='{Y(val) + dy:.1f}' r='{fs * 0.3:.1f}' "
                                 f"fill='none' stroke='{c}' "
                                 f"stroke-width='2'/>")
                    else:
                        s.append(f"<circle cx='{X(rnd):.1f}' "
                                 f"cy='{Y(val) + dy:.1f}' r='{fs * 0.32:.1f}' "
                                 f"fill='{c}' stroke='#0a0f1a' "
                                 f"stroke-width='1.5'/>")
                    dy += fs * 0.85
        r_, c_ = pts[-1]
        s.append(f"<circle cx='{X(r_):.1f}' cy='{Y(c_):.1f}' r='5.5' "
                 f"fill='{color[a]}' fill-opacity='{0.4 if dim else 1}' "
                 f"stroke='#0a0f1a' stroke-width='2'/>")
        ends.append([Y(c_) + fs * 0.32, X(r_) + 14, a])
    for n in notes:
        nx, ny = X(n["rnd"]), Y(n["val"])
        tx, ty = nx + n.get("dx", 0), ny + n.get("dy", -40)
        s.append(f"<line x1='{nx:.1f}' y1='{ny:.1f}' x2='{tx:.1f}' "
                 f"y2='{ty + 6:.1f}' stroke='#aeb8cc' stroke-width='1.5' "
                 f"stroke-dasharray='3,4'/>")
        for i, line in enumerate(n["text"].split("\\n")):
            s.append(f"<text x='{tx:.1f}' y='{ty + i * fs * 1.25:.1f}' "
                     f"text-anchor='{n.get('anchor', 'middle')}' "
                     f"font-size='{fs * 0.86:.0f}' fill='#e8ecf4' "
                     f"font-weight='700'>{line}</text>")
    gap = fs * 1.35
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + gap)
    if ends and ends[-1][0] > mt + ih:
        ends[-1][0] = mt + ih
        for i in range(len(ends) - 2, -1, -1):
            ends[i][0] = min(ends[i][0], ends[i + 1][0] - gap)
    for yy, xx, a in ends:
        s.append(f"<text x='{xx:.1f}' y='{yy:.1f}' font-size='{fs}' "
                 f"font-weight='700' fill='{color[a]}'>{a}</text>")
    s.append("</svg>")
    return "".join(s)


def lanes_svg(width, height, fs=16):
    """What LANDED on each mind, round by round — the seed as a hollow ring,
    every peer push as a filled dot in the feeling's color. Margins match
    curve_svg so the lanes sit exactly under the curve's rounds."""
    ml, mr = int(fs * 4), int(fs * 9.5)
    mt = int(fs * 2.2)
    xmax = max(rounds)
    iw = width - ml - mr
    row_h = (height - mt - fs * 1.8) / len(agents)
    lane_order = [P["patient_zero"]] + [a for a in agents
                                        if a != P["patient_zero"]]

    def X(rnd): return ml + iw * (rnd / xmax if xmax else 0)

    s = [f"<svg class='plot' width='{width}' height='{height}' "
         f"viewBox='0 0 {width} {height}'>"]
    s.append(f"<text x='{ml}' y='{fs + 2}' font-size='{fs - 3}' "
             f"fill='#6b7689' letter-spacing='.14em'>WHAT LANDED ON EACH "
             f"MIND — ○ THE SEED · ● A PEER'S PUSH, COLORED BY FEELING</text>")
    r_dot = fs * 0.42
    for i, a in enumerate(lane_order):
        yy = mt + row_h * (i + 0.5)
        s.append(f"<line x1='{ml}' y1='{yy:.1f}' x2='{ml + iw}' y2='{yy:.1f}' "
                 f"stroke='rgba(107,118,137,.18)' stroke-width='1'/>")
        s.append(f"<text x='{ml + iw + r_dot * 4 + 10:.0f}' "
                 f"y='{yy + fs * 0.32:.1f}' font-size='{fs}' "
                 f"font-weight='700' fill='{color[a]}'>{a}</text>")
        for rnd in rounds:
            rec = by_round[rnd].get(a)
            if not rec:
                continue
            inb = rec.get("inbound") or []
            x0 = X(rnd) - (len(inb) - 1) * r_dot * 1.3
            for j, src in enumerate(inb):
                cx_ = x0 + j * r_dot * 2.6
                c = FEEL_COLORS[src["feeling"]]
                if src["from"] == "seed":
                    s.append(f"<circle cx='{cx_:.1f}' cy='{yy:.1f}' "
                             f"r='{r_dot:.1f}' fill='none' stroke='{c}' "
                             f"stroke-width='2.5'/>")
                else:
                    s.append(f"<circle cx='{cx_:.1f}' cy='{yy:.1f}' "
                             f"r='{r_dot:.1f}' fill='{c}'/>")
    for rnd in rounds:
        s.append(f"<text x='{X(rnd):.1f}' y='{height - 2}' "
                 f"text-anchor='middle' font-size='{fs - 2}' "
                 f"fill='#6b7689'>r{rnd}</text>")
    s.append("</svg>")
    return "".join(s)


def auto_notes():
    """Annotations computed from the run itself: the strongest rescue moment
    (peer pushes landing on patient zero), and the longest tail where the
    seed ran unopposed — whatever this run's plot turned out to be."""
    pz = P["patient_zero"]
    notes, best = [], None
    for rnd in rounds[1:]:
        rec, prev = by_round[rnd].get(pz), by_round[rnd - 1].get(pz)
        if not rec or not prev:
            continue
        peers = [s for s in rec.get("inbound") or [] if s["from"] != "seed"]
        if not peers:
            continue
        drop = (prev.get("sad_score") or 0) - (rec.get("sad_score") or 0)
        if best is None or drop > best[0]:
            best = (drop, rnd, prev.get("sad_score"),
                    rec.get("sad_score"), peers)
    if best:
        drop, rnd, s0, s1, peers = best
        kinds = {}
        for p in peers:
            kinds[p["feeling"]] = kinds.get(p["feeling"], 0) + 1
        label = " + ".join(f"{k} ×{n}" if n > 1 else k
                           for k, n in kinds.items())
        txt = (f"{label} land — {s0} → {s1}\\nagainst a live seed"
               if drop > 0 else
               f"{label} land —\\nthe seed holds at {s1}")
        notes.append({"rnd": rnd, "val": s1, "dx": 30, "dy": 74, "text": txt})
    tail = 0
    for rnd in reversed(rounds[1:]):
        rec = by_round[rnd].get(pz)
        if rec and not [s for s in rec.get("inbound") or []
                        if s["from"] != "seed"]:
            tail += 1
        else:
            break
    if tail >= 3:
        val = by_round[rounds[-1]][pz].get("sad_score") or 10
        notes.append({"rnd": rounds[-1] - tail / 2, "val": val, "dy": 58,
                      "text": "the seed, unopposed —\\nnobody pushes back"})
    return notes


def tally():
    """feeling -> count over all touches, and per-target counts."""
    feel, at = {}, {}
    for r in log:
        t = r.get("touch")
        if not t:
            continue
        feel[t["feeling"]] = feel.get(t["feeling"], 0) + 1
        at[t["target"]] = at.get(t["target"], 0) + 1
    return feel, at


def final_html():
    feel, at = tally()
    chips = " ".join(
        f"<span class='chip' style='color:{FEEL_COLORS[m]};border:1px solid "
        f"{FEEL_COLORS[m]}aa;font-size:19px'>{m} ×{n}</span>"
        for m, n in sorted(feel.items(), key=lambda kv: -kv[1]))
    targets = " · ".join(f"<b style='color:{color[a]}'>{a}</b> ←{n}"
                         for a, n in sorted(at.items(), key=lambda kv: -kv[1]))
    pz = P["patient_zero"]
    return f"""<meta charset='utf-8'><style>{CSS.replace('__W__', str(W)).replace('__H__', str(H))}
    h1 {{ font-size: 40px; font-weight: 800; color: #fff; margin-top: 18px;
          letter-spacing: -0.01em; }}</style>
    <div class='top'><div class='dot'></div><span class='brand'>steeropathy</span>
      <span class='kicker'>RESONANCE · MINDS COUPLING, NO WORDS</span>
      <span class='round'>the whole run</span></div>
    <h1>{args.headline.replace('<br>', ' ')}</h1>
    <div class='sub' style='font-size:18px;margin-top:12px'>pushes sent:
      {chips} &nbsp;&nbsp; aimed at: {targets}</div>
    {curve_svg(max(rounds), W - 112, 356, fs=17, emphasize=pz,
               notes=auto_notes())}
    {lanes_svg(W - 112, 230, fs=15)}
    <div class='invite'><span class='play'>▸</span>
      <b>github.com/{'moudrkat'}/steeropathy</b> · model
      {html.escape(str(P.get('model') or ''))}</div>"""


def shoot(html_text, png, w, h):
    src = png.with_suffix(".html")
    src.write_text(html_text)
    subprocess.run([args.chrome, "--headless=new", f"--window-size={w},{h}",
                    f"--screenshot={png}", "--hide-scrollbars",
                    "--force-device-scale-factor=1", str(src)],
                   check=True, capture_output=True)


# ---- animation frames -------------------------------------------------------
frames = []   # (png, hold)
for rnd in rounds:
    png = build / f"frame{rnd:02d}a.png"
    shoot(frame_html(rnd, show_touches=False), png, W, H)
    frames.append((png, args.hold + (1.0 if rnd == 0 else 0.0)))
    print(f"frame r{rnd} journals -> {png.name}")
    if any((by_round[rnd].get(a) or {}).get("touch") is not None
           or rnd >= 1 for a in agents) and rnd >= 1:
        png = build / f"frame{rnd:02d}b.png"
        shoot(frame_html(rnd, show_touches=True), png, W, H)
        frames.append((png, args.hold + 0.6))
        print(f"frame r{rnd} touches  -> {png.name}")

png = build / "frame_zz_final.png"
shoot(final_html(), png, W, H)
frames.append((png, args.hold + 2.0))
print(f"frame final -> {png.name}")

concat = build / "frames.txt"
lines = []
for f, hold in frames:
    lines += [f"file '{f.name}'", f"duration {hold}"]
lines.append(f"file '{frames[-1][0].name}'")
concat.write_text("\n".join(lines) + "\n")

gif, mp4 = out / "resonance.gif", out / "resonance.mp4"
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-i", str(concat),
                "-vf", "fps=10,split[a][b];[a]palettegen=stats_mode=diff[p];"
                       "[b][p]paletteuse=dither=bayer:bayer_scale=4",
                "-loop", "0", str(gif)], check=True, capture_output=True,
               cwd=build)
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-i", str(concat),
                "-vf", "fps=30,format=yuv420p", "-c:v", "libx264",
                "-crf", "20", str(mp4)], check=True, capture_output=True,
               cwd=build)
print(f"-> {gif} ({gif.stat().st_size/1e6:.1f} MB)")
print(f"-> {mp4} ({mp4.stat().st_size/1e6:.1f} MB)")

# ---- hero figure ------------------------------------------------------------
CW, CH = 2400, 1350
hero = f"""<meta charset='utf-8'><style>{CSS.replace('__W__', str(CW)).replace('__H__', str(CH))}
  body {{ padding: 66px 110px 50px 110px; }}
  .brand {{ font-size: 44px; }} .dot {{ width: 26px; height: 26px; }}
  .kicker {{ font-size: 25px; }} .sub {{ font-size: 25px; margin-top: 22px; }}
  h1 {{ font-size: 68px; font-weight: 800; color: #fff; margin-top: 28px;
        letter-spacing: -0.015em; }}
  .invite {{ font-size: 26px; padding-top: 26px; margin-top: 34px; }}
</style>
<div class='top'><div class='dot'></div><span class='brand'>steeropathy</span>
  <span class='kicker'>RESONANCE · MINDS COUPLING, NO WORDS</span></div>
<h1>{args.headline}</h1>
<div class='sub'>no words — each agent reads the others straight off the
  residual stream (mood lean + <b>J-space</b>) and gets one <b>induce</b>
  push per round{f" · <b>{P['pushes']} pushes</b> each, whole run"
                 if P.get('pushes') else ''} · pushes <b>superpose</b> ·
  seed: <b>{P['seed_mood']} → {P['patient_zero']}</b>, every round</div>
{curve_svg(max(rounds), CW - 220, 470, fs=24, emphasize=P['patient_zero'],
           notes=auto_notes())}
{lanes_svg(CW - 220, 330, fs=22)}
<div class='invite'><span class='play'>▸</span>
  <b>github.com/{'moudrkat'}/steeropathy</b> · model
  {html.escape(str(P.get('model') or ''))}</div>"""
shoot(hero, out / "resonance-curve.png", CW, CH)
print(f"-> {out / 'resonance-curve.png'}")
