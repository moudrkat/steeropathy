"""Hear a direction: from a soundof run, one tune per direction (the
unsteered one, then each real vector; placebos with --placebo) rendered as
a piano roll (PNG), a wav (a plain synth: sine plus two harmonics, a short
envelope, the tune's own tempo) and, with ffmpeg present, an mp4 of the
two together — a clip you can post.

    python fig/render_soundof.py docs/runs/soundof-01-aorus-4b-n12.json [--rep 0] [--placebo]
    -> docs/soundof/<run>/<direction>.png|.wav|.mp4
"""
import argparse
import json
import math
import pathlib
import shutil
import subprocess
import wave

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

HERE = pathlib.Path(__file__).parent.parent
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"
NOTE, REST = "#2a78d6", "#d9d8d4"
RATE = 44100


def synth(notes, bpm, unit_beats=4.0):
    """notes: (midi | None, length in whole notes). A whole note is
    `unit_beats` beats at `bpm`."""
    sec_per_whole = unit_beats * 60.0 / max(30, bpm or 100)
    out = []
    for midi, dur in notes:
        n = int(RATE * dur * sec_per_whole)
        if n <= 0:
            continue
        t = np.arange(n) / RATE
        if midi is None:
            out.append(np.zeros(n))
            continue
        f = 440.0 * 2 ** ((midi - 69) / 12)
        wavef = (np.sin(2 * math.pi * f * t) + 0.35 * np.sin(4 * math.pi * f * t)
                 + 0.15 * np.sin(6 * math.pi * f * t))
        a = min(n, int(0.012 * RATE))
        r = min(n, int(0.08 * RATE))
        env = np.ones(n)
        env[:a] = np.linspace(0, 1, a)
        env[n - r:] = np.linspace(1, 0, r)
        env *= np.exp(-1.6 * t / max(t[-1], 1e-3))
        out.append(wavef * env)
    sig = np.concatenate(out) if out else np.zeros(RATE)
    sig = np.concatenate([sig, np.zeros(int(0.4 * RATE))])
    sig = 0.6 * sig / (np.max(np.abs(sig)) or 1.0)
    return sig


def write_wav(path, sig):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((sig * 32767).astype(np.int16).tobytes())


def piano_roll(path, spec, title, label):
    font_manager.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, ax = plt.subplots(figsize=(9.6, 3.6), facecolor=SURF)
    ax.set_facecolor(SURF)
    t = 0.0
    pitches = [p for p, _ in spec["notes"] if p is not None]
    lo, hi = min(pitches) - 2, max(pitches) + 2
    for midi, dur in spec["notes"]:
        if midi is None:
            ax.add_patch(plt.Rectangle((t, lo), dur, hi - lo, facecolor=REST, linewidth=0, alpha=0.5))
        else:
            ax.add_patch(plt.Rectangle((t + 0.004, midi - 0.42), max(dur - 0.008, 0.01), 0.84,
                                       facecolor=NOTE, linewidth=0))
        t += dur
    for k in range(lo, hi + 1):
        if k % 12 in (1, 3, 6, 8, 10):
            ax.axhspan(k - 0.5, k + 0.5, color=GRID, alpha=0.35, linewidth=0)
    ax.set_xlim(0, max(t, 0.01))
    ax.set_ylim(lo - 0.5, hi + 0.5)
    ax.set_yticks([k for k in range(lo, hi + 1) if k % 12 == 0], [f"C{k // 12 - 1}" for k in range(lo, hi + 1) if k % 12 == 0])
    ax.set_xticks([])
    for s in ("top", "right", "bottom"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.tick_params(length=0, colors=INK2)
    ax.set_title(title, loc="left", color=INK, fontsize=13, fontweight="bold", pad=10)
    ax.text(1.0, 1.02, label, transform=ax.transAxes, ha="right", va="bottom", color=INK2, fontsize=9.5)
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor=SURF)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--rep", type=int, default=0, help="which repetition's tunes")
    ap.add_argument("--placebo", action="store_true", help="also the placebo tunes")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    d = json.loads(pathlib.Path(args.run).read_text())
    out = pathlib.Path(args.out) if args.out else HERE / "docs" / "soundof" / pathlib.Path(args.run).stem
    out.mkdir(parents=True, exist_ok=True)
    ff = shutil.which("ffmpeg")
    for r in d["runs"]:
        if r.get("rep", 0) != args.rep or not r.get("spec"):
            continue
        if r["kind"] == "placebo" and not args.placebo:
            continue
        s = r["spec"]
        name = "unsteered" if r["kind"] == "base" else r["name"] + ("-placebo" if r["kind"] == "placebo" else "")
        stem = out / name.replace("+", "plus").replace("*", "x").replace("~", "-")
        bpm = s.get("bpm") or 100
        label = (f"{s.get('title') or ''}  ·  {s.get('meter') or '?'}  ·  {s.get('key') or '?'}  ·  "
                 f"{bpm} bpm  ·  {d.get('model', '')}")
        title = "unsteered" if r["kind"] == "base" else (
            f"{r['name']} · strength {d['params']['strength']}" + (" · placebo" if r["kind"] == "placebo" else ""))
        piano_roll(stem.with_suffix(".png"), s, title, label)
        sig = synth([(p, dur) for p, dur in s["notes"]], bpm)
        write_wav(stem.with_suffix(".wav"), sig)
        if ff:
            subprocess.run([ff, "-y", "-loglevel", "error", "-loop", "1", "-i", str(stem.with_suffix(".png")),
                            "-i", str(stem.with_suffix(".wav")), "-c:v", "libx264", "-tune", "stillimage",
                            "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                            "-c:a", "aac", "-b:a", "160k", "-shortest", str(stem.with_suffix(".mp4"))],
                           check=False)
        print(f"{name:20s} {len(sig) / RATE:5.1f}s  {stem}.png/.wav" + ("/.mp4" if ff else ""))


if __name__ == "__main__":
    main()
