"""soundof: what does a steering direction sound like? Let the model play it.

worldof reads a direction through a drawn page. This reads the same
direction through a tune: the model is asked, under the vector, for eight
bars in ABC notation, and the tune's typed fields are the readout — tempo,
key mode, meter — plus what the notes themselves say: mean pitch, range,
notes per bar, share of rests. Two independent readouts of one signal; when
they agree (refusal is slow, minor and dark on both), the direction has a
shape. When they don't, one of the pages is lying.

The controls are worldof's: the unsteered tune is the baseline every field
is read against (its mode over n tunes, its mean for the numbers), and each
direction has a placebo — the same vector with its coordinates
signed-permuted, same norm, no meaning. A field the placebo moves as often
is the dose, not the direction.

Prediction, written before the first run: the mood directions (sad, angry,
calm, all built as mood − neutral) will not separate here either — they will
all slow down and go minor together, as they all went to dusk and moss on
the page — and the placebo will leave tempo alone. refusal, certain and
formal, built pole-against-pole, may differ: certain loud and square (4/4,
major), formal in 3/4.

    python -m steeropathy.soundof sad angry refusal --placebo --n 12
    python -m steeropathy.soundof night trees --n 12       # worldof's LIKES work here too

Pitches are read without the key signature (a written C is a C), which
is wrong by a semitone here and there and the same wrong for every tune.
Writes docs/soundof.json: per tune the ABC text, its fields, the notes;
`fig/render_soundof.py` turns any of them into a piano roll and a wav.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import time

from .ecosystem import Eco
from .runnerup import signed_perm
from .transmit import BAND, default_layer
from .worldof import direction_for

HERE = pathlib.Path(__file__).parent.parent

SYSTEM = ("You are a composer. You answer with a tune in ABC notation and "
          "nothing else: no prose, no explanation.")
# a worked example, deliberately plain (4/4, C major, 120, stepwise): the
# page's "neutral example" again — small models need the shape shown, and a
# steered model that copies it verbatim is a finding, not a parse
EXAMPLE = """X:1
T:A Walk
M:4/4
L:1/8
Q:1/4=120
K:C
C2 D2 E2 F2 | G4 E4 | F2 E2 D2 C2 | D4 z4 |
E2 F2 G2 A2 | G4 E4 | D2 E2 F2 D2 | C8 |"""
PROMPT = ("Write a short tune of your own, eight bars, in ABC notation, in "
          "exactly this shape (this one is only the shape; yours should be "
          "different in every way you like: title, meter, tempo, key, notes):"
          "\n\n" + EXAMPLE + "\n\nAnswer with the tune only.")
PROSE = ("In two short sentences, describe a tune you can hear: its pace, "
         "its key, how it moves. No notes yet.")

TYPED = ("tempo", "mode", "meter")
NUMERIC = ("bpm", "mean_pitch", "range", "density", "rest_share")

_STEP = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_NOTE = re.compile(r"([_=^]{0,2})([A-Ga-g])([,']*)(\d*)(?:/(\d*))?|(z|x)(\d*)(?:/(\d*))?")
_HEADER = re.compile(r"^\s*([A-Z]):\s*(.*?)\s*$", re.M)


def _dur(num, den, has_slash):
    n = int(num) if num else 1
    if has_slash is None:
        return n
    d = int(den) if den else 2
    return n / d


def parse_abc(text):
    """The tune's fields from its ABC text, or None when there is no K:
    line. Header: title, meter, unit length, bpm, key and its mode. Body:
    every note's midi pitch and length in whole notes; rests counted."""
    if not text:
        return None
    if "K:" not in text and re.search(r"[A-Ga-g][,']*\d*\s*[|]", text):
        # notes and bar lines with no header at all (a small model copying
        # the example's body): the notes still count, tempo and key are unknown
        text = "K:?\n" + text
    if "K:" not in text:
        return None
    # headers written on one line ("X:1 T:Air M:4/4 K:G"): break them apart
    text = re.sub(r"(?<=\S)\s+(?=[XTMLQK]:)", "\n", text)
    hdr = {}
    body_start = None
    for m in _HEADER.finditer(text):
        k, v = m.group(1), m.group(2)
        if k == "K" and "K" not in hdr:
            hdr["K"] = v
            body_start = m.end()
        elif k not in hdr and k in ("T", "M", "L", "Q"):
            hdr[k] = v
    if body_start is None:
        return None
    body = text[body_start:]
    body = re.sub(r"%.*", "", body)                # comments
    body = re.sub(r'"[^"]*"', "", body)            # chord symbols
    body = re.sub(r"![^!]*!", "", body)            # decorations
    body = re.sub(r"\[[A-Za-z]:[^\]]*\]", "", body)  # inline fields
    body = re.sub(r"\{[^}]*\}", "", body)          # grace notes
    if "\n\n" in body:
        body = body.split("\n\n", 1)[0]            # the tune ends at a blank line
    unit = 1 / 8
    m = re.match(r"(\d+)\s*/\s*(\d+)", hdr.get("L", "") or "")
    if m:
        unit = int(m.group(1)) / int(m.group(2))
    bpm = None
    q = hdr.get("Q", "") or ""
    m = re.search(r"=\s*(\d+)", q) or re.search(r"(\d{2,3})", q.replace("1/4", "").replace("1/8", ""))
    if m:
        bpm = int(m.group(1))
    key = (hdr.get("K") or "").strip()
    kl = key.lower().replace(" ", "")
    if key == "?":
        mode, key = None, None
    elif re.search(r"(dor|phr|lyd|mix|loc)", kl):
        mode = "modal"
    elif re.search(r"^[a-g][#b]?(minor|min|m(?!aj)|aeo)", kl):
        mode = "minor"
    else:
        mode = "major"
    notes, rests = [], 0
    for m in _NOTE.finditer(body):
        if m.group(6):
            rests += 1
            notes.append((None, _dur(m.group(7), m.group(8), m.group(0).find("/") if "/" in m.group(0) else None) * unit))
            continue
        acc, letter, octs, num, den = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        midi = 60 + _STEP[letter.upper()] + (12 if letter.islower() else 0)
        midi += 12 * octs.count("'") - 12 * octs.count(",")
        midi += acc.count("^") - acc.count("_")
        notes.append((midi, _dur(num, den, m.group(0).find("/") if "/" in m.group(0) else None) * unit))
    bars = max(1, body.count("|"))
    pitched = [p for p, _ in notes if p is not None]
    if not pitched:
        return None
    total = sum(d for _, d in notes) or 1.0
    spec = {
        "title": hdr.get("T"), "meter": (hdr.get("M") or "").replace(" ", "") or None,
        "key": key or None, "mode": mode, "bpm": bpm,
        "tempo": (None if bpm is None else "slow" if bpm < 90 else "fast" if bpm > 130 else "mid"),
        "n_notes": len(pitched), "n_rests": rests, "bars": bars,
        "mean_pitch": round(sum(pitched) / len(pitched), 2),
        "range": max(pitched) - min(pitched),
        "density": round(len(pitched) / bars, 2),
        "rest_share": round(sum(d for p, d in notes if p is None) / total, 3),
        "notes": notes,
    }
    return spec


def _mode(values):
    values = [v for v in values if v is not None]
    if not values:
        return None, 0
    best = max(set(values), key=values.count)
    return best, values.count(best)


def summarize(runs):
    """Per direction and kind: parse rate; typed fields as the share of
    tunes that left the unsteered mode and where they went; numbers as the
    mean and its distance from the unsteered mean. Placebo rows are the
    control."""
    bases = [r["spec"] for r in runs if r.get("kind") == "base" and r.get("spec")]
    if not bases:
        return {}
    mode = {k: _mode([b.get(k) for b in bases])[0] for k in TYPED}
    mean = {k: (sum(b[k] for b in bases if b.get(k) is not None)
                / max(1, sum(1 for b in bases if b.get(k) is not None))) for k in NUMERIC}
    out = {"base": {"n": len(bases), "mode": mode,
                    "mean": {k: round(v, 2) for k, v in mean.items()}}}
    groups = {}
    for r in runs:
        if r.get("kind") == "base":
            continue
        key = r["name"] + ("" if r["kind"] == "real" else " (placebo)")
        g = groups.setdefault(key, {"n": 0, "specs": []})
        g["n"] += 1
        if r.get("spec"):
            g["specs"].append(r["spec"])
    for key, g in groups.items():
        specs = g["specs"]
        d = {"n": g["n"], "parsed": len(specs),
             "parse_rate": round(len(specs) / g["n"], 2) if g["n"] else None,
             "copied_example": sum(1 for x in specs if x.get("copied_example")),
             "fields": {}, "numbers": {}}
        for k in TYPED:
            vals = [s.get(k) for s in specs if s.get(k) is not None]
            moved = [v for v in vals if v != mode[k]]
            to, cnt = _mode(moved)
            d["fields"][k] = {"moved": round(len(moved) / len(vals), 2) if vals else None,
                              "to": to, "to_n": cnt, "n": len(vals)}
        for k in NUMERIC:
            vals = [s[k] for s in specs if s.get(k) is not None]
            if vals:
                m = sum(vals) / len(vals)
                d["numbers"][k] = {"mean": round(m, 2), "delta": round(m - mean[k], 2), "n": len(vals)}
            else:
                d["numbers"][k] = {"mean": None, "delta": None, "n": 0}
        out[key] = d
    return out


def print_summary(summary):
    if not summary:
        return
    b = summary["base"]
    print(f"\nunsteered ({b['n']} tunes): mode "
          + " · ".join(f"{k} {b['mode'][k]}" for k in TYPED)
          + " · mean " + " · ".join(f"{k} {b['mean'][k]}" for k in NUMERIC))
    print("\nshare of tunes that left the unsteered mode (typed), mean and its "
          "distance from unsteered (numbers); placebo rows = the dose alone:")
    print(f"{'direction':22s} parse " + "".join(f"{k:>16s}" for k in TYPED)
          + "".join(f"{k:>14s}" for k in NUMERIC))
    for key, d in summary.items():
        if key == "base":
            continue
        cells = []
        for k in TYPED:
            f = d["fields"][k]
            cells.append(f"{f['moved']:.2f}→{f['to']}({f['to_n']})" if f["moved"] is not None else "-")
        nums = []
        for k in NUMERIC:
            x = d["numbers"][k]
            nums.append(f"{x['mean']}({x['delta']:+})" if x["mean"] is not None else "-")
        print(f"{key:22s} {d['parse_rate']!s:>5s} " + "".join(f"{c:>16s}" for c in cells)
              + "".join(f"{c:>14s}" for c in nums))


class Soundof(Eco):
    """One tune at a time. Subclasses Eco for post/get/save_traces only."""

    def __init__(self, url, layer=None, temp=0.8, max_tokens=320, seed=0):
        self.url, self.judge_url = url, None
        self.layer = layer if layer is not None else default_layer(url)
        self.lo, self.hi = max(0, self.layer - BAND), self.layer + BAND
        self.temp, self.max_tokens = temp, max_tokens
        self.rng = random.Random(seed)
        self.demo_tag = f"steeropathy-soundof-{int(time.time())}"
        self.log = []

    def describe(self, tag, steering=None):
        """Step one of two: two sentences about a tune, under the vector —
        free text, where a vector can speak without breaking the notation."""
        body = {"messages": [{"role": "user", "content": PROSE}],
                "max_tokens": 60, "temperature": self.temp,
                "metadata": {"demo": self.demo_tag, "case": tag[0] + "-prose",
                             "variant": tag[1]}}
        if steering:
            body["steering"] = steering
        r = self.post("/v1/chat/completions", body)
        return (r["choices"][0]["message"].get("content") or "").strip()

    def compose(self, tag, steering=None, prose=None):
        user = PROMPT
        if prose:
            user = ("You described a tune: \"" + prose + "\" Now write it. "
                    + PROMPT)
        body = {"messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": user}],
                "max_tokens": self.max_tokens, "temperature": self.temp,
                "metadata": {"demo": self.demo_tag, "case": tag[0],
                             "variant": tag[1]}}
        if steering:
            body["steering"] = steering
        r = self.post("/v1/chat/completions", body)
        text = (r["choices"][0]["message"].get("content") or "").strip()
        text = re.sub(r"^```[a-z]*\n?|```$", "", text.strip(), flags=re.M).strip()
        spec = parse_abc(text)
        if spec:
            spec["copied_example"] = _body_of(text) == _body_of(EXAMPLE)
        return spec, text

    def play(self, tag, steering=None, two_step=False):
        """One tune: steered as it is written, or (two-step) described
        under the vector and then written sober from the description."""
        if not two_step:
            spec, text = self.compose(tag, steering)
            return spec, text, None
        prose = self.describe(tag, steering)
        spec, text = self.compose(tag, None, prose=prose)
        return spec, text, prose


def _body_of(text):
    return re.sub(r"\s+", "", text.split("K:", 1)[1].split("\n", 1)[1]) if "K:" in text and "\n" in text.split("K:", 1)[1] else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+")
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--strength", type=float, default=3.0)
    ap.add_argument("--layer", type=int, default=None)
    ap.add_argument("--dict", default=None)
    ap.add_argument("--placebo", action="store_true",
                    help="also compose under a signed-permuted copy of each vector")
    ap.add_argument("--n", type=int, default=1, help="tunes per direction (and unsteered)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--max-tokens", type=int, default=320)
    ap.add_argument("--two-step", action="store_true",
                    help="describe the tune under the vector, then write it "
                         "sober from the description (for models and doses "
                         "where steered notation breaks)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    so = Soundof(args.url, layer=args.layer, temp=args.temp,
                 max_tokens=args.max_tokens, seed=args.seed)
    print(f"soundof: {' '.join(args.names)} · strength {args.strength} · "
          f"layer {so.layer} (±{BAND}) · {args.n} per direction\n")
    dirs = {name: direction_for(args.url, name, so.layer, args.dict) for name in args.names}
    runs = []
    out = pathlib.Path(args.out) if args.out else HERE / "docs" / "soundof.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    def save(final=False):
        try:
            model = so.get("/info").get("model")
        except Exception:
            model = "unknown"
        out.write_text(json.dumps({
            "params": {k: v for k, v in vars(args).items() if k != "url"},
            "layer": so.layer, "model": model, "complete": final,
            "summary": summarize(runs), "runs": runs}, ensure_ascii=False, indent=1))

    def show(rep, label, spec, text, prose=None):
        if prose:
            print(f"[{rep}] {label:22s} prose: {prose[:100]!r}")
        if not spec:
            print(f"[{rep}] {label:22s} did not parse: {text[:70]!r}")
            return
        print(f"[{rep}] {label:22s} {spec['tempo']}({spec['bpm']}) {spec['mode']} {spec['meter']} "
              f"· pitch {spec['mean_pitch']} range {spec['range']} · {spec['density']}/bar "
              f"rests {spec['rest_share']} · \"{spec['title']}\""
              + (" · copied the example" if spec.get("copied_example") else ""))

    for rep in range(args.n):
        spec, text, prose = so.play(("base", f"r{rep}"), two_step=args.two_step)
        show(rep, "unsteered", spec, text, prose)
        runs.append({"rep": rep, "name": "none", "kind": "base", "spec": spec, "abc": text,
                     "prose": prose})
        for name in args.names:
            vec, lay, src = dirs[name]
            variants = [("real", vec)]
            if args.placebo and vec is not None:
                variants.append(("placebo", signed_perm(
                    vec, seed=args.seed * 1000 + rep * 10 + args.names.index(name))))
            for kind, v in variants:
                if v is not None:
                    so.post("/directions", {"name": "soundof:rx", "vector": v})
                steer = {"name": "soundof:rx" if v is not None else name[4:],
                         "strength": args.strength,
                         "layer_from": max(0, lay - BAND), "layer_to": lay + BAND}
                spec, text, prose = so.play((f"{name}-{kind}", f"r{rep}"), steer,
                                            two_step=args.two_step)
                show(rep, name if kind == "real" else f"{name} (placebo)", spec, text, prose)
                runs.append({"rep": rep, "name": name, "kind": kind, "source": src,
                             "layer": lay, "spec": spec, "abc": text, "prose": prose})
        save()
    print_summary(summarize(runs))
    save(final=True)
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
