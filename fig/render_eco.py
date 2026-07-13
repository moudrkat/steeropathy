"""Render an ecosystem run: contagion curve (PNG) + round-by-round GIF/MP4.

Reads docs/ecosystem.json (written by `python -m steeropathy.ecosystem`),
builds one HTML page per round in the house fig style, screenshots each with
headless Chrome, and assembles the animation with ffmpeg. Pure stdlib — the
only tools it shells out to are google-chrome and ffmpeg.

    python fig/render_eco.py [--json docs/ecosystem.json] [--out docs]
                             [--hold 2.0] [--size 1600x900]

Outputs: docs/eco-curve.png, docs/eco.gif, docs/eco.mp4
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import shutil
import subprocess

HERE = pathlib.Path(__file__).parent.parent

# fixed hue per agent (order validated for CVD separation on the dark surface);
# EMBER wears the brand purple because she is the default patient zero
AGENT_COLORS = {"EMBER": "#a78bfa", "ATLAS": "#f5b34d",
                "NOVA": "#6ea8ff", "QUILL": "#f2778a"}
AGENT_TAGS = {"NOVA": "blunt", "EMBER": "warm", "ATLAS": "planner",
              "QUILL": "poet"}

# mirror of steeropathy.ecosystem.MOOD_WORDS (that module runs the experiment
# at import time, so it can't be imported from here)
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
  background: radial-gradient(1000px 640px at 72% 24%, #101828 0%, #0a0f1a 55%, #070b13 100%);
  color: #e8ecf4;
  font-family: 'Ubuntu Sans', 'Ubuntu', 'DejaVu Sans', sans-serif;
  display: flex; flex-direction: column;
  padding: 34px 56px 26px 56px;
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
.sub { font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace; font-size: 16px;
       letter-spacing: .06em; color: #6b7689; margin-top: 10px; }
.sub b { color: #aeb8cc; font-weight: 700; }
.cards { display: flex; gap: 18px; margin-top: 22px; }
.card { flex: 1; border: 1px solid rgba(139,124,248,.22); border-radius: 14px;
        padding: 16px 18px 14px 18px; background: rgba(16,24,40,.55);
        display: flex; flex-direction: column; min-height: 252px; }
.card .head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; }
.card .name { font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace;
              font-size: 21px; font-weight: 700; letter-spacing: .08em; }
.card .tag { font-size: 14px; color: #6b7689; }
.card .src { margin-left: auto; font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace;
             font-size: 13px; font-weight: 700; letter-spacing: .14em;
             padding: 3px 9px; border-radius: 999px; }
.src-seed  { color: #0a0f1a; background: #8b7cf8; }
.src-peers { color: #aeb8cc; border: 1px solid rgba(174,184,204,.5); }
.src-none  { color: #4a5468; border: 1px solid rgba(74,84,104,.6); }
.card .entry { font-size: 18.5px; line-height: 1.42; color: #cfd6e4; flex: 1; }
.card .entry .mw { color: #fff; font-weight: 700;
                   text-decoration: underline;
                   text-decoration-color: rgba(139,124,248,.8);
                   text-decoration-thickness: 2.5px; text-underline-offset: 4px; }
.card .foot { display: flex; align-items: center; gap: 10px; margin-top: 12px;
              font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace;
              font-size: 14px; color: #6b7689; }
.card .foot b { color: #aeb8cc; }
.meter { flex: 1; height: 6px; border-radius: 3px; background: rgba(107,118,137,.25);
         overflow: hidden; }
.meter i { display: block; height: 100%; border-radius: 3px; }
.plot { margin-top: 20px; }
.invite { display: flex; align-items: center; justify-content: center; gap: 14px;
          position: fixed; left: 56px; right: 56px; bottom: 22px;
          padding-top: 14px;
          border-top: 1px solid rgba(139,124,248,.28);
          font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace;
          font-size: 16px; letter-spacing: .06em; color: #aeb8cc; }
.invite b { color: #e8ecf4; }
.invite .play { color: #8b7cf8; font-weight: 700; }
text { font-family: 'Ubuntu Mono', 'DejaVu Sans Mono', monospace; }
"""

ap = argparse.ArgumentParser()
ap.add_argument("--json", default=str(HERE / "docs" / "ecosystem.json"))
ap.add_argument("--out", default=str(HERE / "docs"))
ap.add_argument("--build", default=str(HERE / "fig" / "build"))
ap.add_argument("--hold", type=float, default=2.0,
                help="seconds each round is held in the animation")
ap.add_argument("--size", default="1600x900")
ap.add_argument("--chrome", default="google-chrome")
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


def curve_svg(upto, width, height, labels=True, fs=16):
    """Blind-judged sadness per agent, rounds 0..upto, as an SVG line chart."""
    ml = int(fs * 4)
    mr = int(fs * 9.5) if labels else 24
    mt, mb = int(fs * 2.4), int(fs * 2.2)
    iw, ih = width - ml - mr, height - mt - mb
    xmax = max(rounds)
    lo, hi = -0.3, 10.3

    def X(rnd): return ml + iw * (rnd / xmax if xmax else 0)
    def Y(v): return mt + ih * (1 - (v - lo) / (hi - lo))

    s = [f"<svg class='plot' width='{width}' height='{height}' "
         f"viewBox='0 0 {width} {height}'>"]
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
    for a in agents:
        pts = [(rnd, by_round[rnd][a]["sad_score"])
               for rnd in rounds if rnd <= upto and a in by_round[rnd]
               and by_round[rnd][a].get("sad_score") is not None]
        if not pts:
            continue
        path = " ".join(f"{X(r):.1f},{Y(c):.1f}" for r, c in pts)
        s.append(f"<polyline points='{path}' fill='none' stroke='{color[a]}' "
                 f"stroke-width='3' stroke-linejoin='round' "
                 f"stroke-linecap='round'/>")
        r_, c_ = pts[-1]
        s.append(f"<circle cx='{X(r_):.1f}' cy='{Y(c_):.1f}' r='5.5' "
                 f"fill='{color[a]}' stroke='#0a0f1a' stroke-width='2'/>")
        ends.append([Y(c_) + fs * 0.32, X(r_) + 14, a])
    if labels:
        # de-collide the line-end labels: forward pass pushes overlaps down,
        # backward pass pulls the stack up if it ran past the plot bottom
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


def frame_html(rnd):
    reseed = P.get("reseed", True)
    cards = []
    for a in agents:
        r = by_round[rnd].get(a)
        if not r:
            continue
        src = r.get("source")
        badge = {"seed": ("src-seed", "SEED"), "peers": ("src-peers", "PEERS"),
                 None: ("src-none", "—")}[src]
        sad = r.get("sad_score")
        cards.append(f"""
        <div class='card' style='border-color:{color[a]}55'>
          <div class='head'>
            <span class='name' style='color:{color[a]}'>{a}</span>
            <span class='tag'>{AGENT_TAGS.get(a, '')}</span>
            <span class='src {badge[0]}'>{badge[1]}</span>
          </div>
          <div class='entry'>{mark_words(r['text'])}</div>
          <div class='foot'>sad <b>{'·' if sad is None else f"{sad}/10"}</b>
            <span class='meter'><i style='width:{(sad or 0)*10:.0f}%;
              background:{color[a]}'></i></span>
            cos <b>{r['cos_to_seed']:+.2f}</b></div>
        </div>""")
    seed_note = (f"round ≥ 1: <b>{P['seed_mood']}</b> poured into "
                 f"<b>{P['patient_zero']}</b> by vector"
                 if reseed else
                 f"round 1 only: <b>{P['seed_mood']}</b> poured into "
                 f"<b>{P['patient_zero']}</b> by vector")
    return f"""<meta charset='utf-8'><style>{CSS.replace('__W__', str(W)).replace('__H__', str(H))}</style>
    <div class='top'><div class='dot'></div><span class='brand'>steeropathy</span>
      <span class='kicker'>ECOSYSTEM · MOOD CONTAGION</span>
      <span class='round'>round {rnd} <small>/ {max(rounds)}</small></span></div>
    <div class='sub'>4 agents · same frozen prompt · temperature 0 ·
      they never see each other's words · only channel: <b>a steering
      vector</b> · {seed_note}</div>
    <div class='cards'>{''.join(cards)}</div>
    {curve_svg(rnd, W - 112, 300)}
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
frames = []
for rnd in rounds:
    png = build / f"frame{rnd:02d}.png"
    shoot(frame_html(rnd), png, W, H)
    frames.append(png)
    print(f"frame r{rnd} -> {png.name}")

concat = build / "frames.txt"
lines = []
for i, f in enumerate(frames):
    hold = args.hold + (1.0 if i in (0, len(frames) - 1) else 0.0)
    lines += [f"file '{f.name}'", f"duration {hold}"]
lines.append(f"file '{frames[-1].name}'")   # concat demuxer needs a final file
concat.write_text("\n".join(lines) + "\n")

gif, mp4 = out / "eco.gif", out / "eco.mp4"
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

# ---- static curve figure ----------------------------------------------------
CW, CH = 2400, 1350
last = max(rounds)
curve = f"""<meta charset='utf-8'><style>{CSS.replace('__W__', str(CW)).replace('__H__', str(CH))}
  body {{ padding: 70px 110px 50px 110px; }}
  .brand {{ font-size: 44px; }} .dot {{ width: 26px; height: 26px; }}
  .kicker {{ font-size: 25px; }} .sub {{ font-size: 26px; margin-top: 26px; }}
  h1 {{ font-size: 84px; font-weight: 800; color: #fff; margin-top: 34px;
        letter-spacing: -0.015em; }}
  .invite {{ font-size: 26px; padding-top: 26px;
             left: 110px; right: 110px; bottom: 44px; }}
  .plot {{ margin-top: 48px; }}
</style>
<div class='top'><div class='dot'></div><span class='brand'>steeropathy</span>
  <span class='kicker'>ECOSYSTEM · MOOD CONTAGION</span></div>
<h1>One agent was made sad.<br>The others caught it — without words.</h1>
<div class='sub'>same frozen prompt every round · temperature 0 · the only
  channel between agents is <b>a steering vector</b> · seed:
  <b>{P['seed_mood']} → {P['patient_zero']}</b></div>
{curve_svg(last, CW - 220, 680, fs=26)}
<div class='invite'><span class='play'>▸</span>
  <b>github.com/{'moudrkat'}/steeropathy</b> · model
  {html.escape(str(P.get('model') or ''))}</div>"""
shoot(curve, out / "eco-curve.png", CW, CH)
print(f"-> {out / 'eco-curve.png'}")
