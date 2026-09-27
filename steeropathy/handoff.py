"""handoff: agents passing each other knob settings, as one vector.

secondhand pushed one mind's whole page-state into another and found the
poem carried more. The encoder was the problem: a mean-pooled contrast of
a whole page is a blunt message. Here the message is written on purpose.
Mind A is given a brief ("a dark forest full of birds") and a catalogue of
knobs — directions with a measurable readout on the page (trees, birds,
stars, cats, houses, crowded, dark, night). A chooses settings for them in a
sober JSON call (no steering on the decision, as always here). The settings
become one vector, the sum of strength × unit direction, and that vector is
added into mind B, which is told only "a place". B draws. The page says how
much of A's message arrived: for every knob A turned, did B's world move
that way against B's own baseline?

Channels, so the vector has something to lose to:
  none     B unsteered — the baseline every knob is read against
  vector   A's settings as one vector added at layer 16 ± 4
  text     A's settings as a sentence in B's prompt ("More trees. Darker.")
  placebo  the same vector, coordinates signed-permuted: the dose alone

Prediction, written before the first run: text will carry the count knobs
(a sentence that says "more birds" is easy to obey), the vector will carry
the continuous ones (darkness) and lose the counts, and the placebo will be
near the coin. If the vector matches text here, the channel was never the
problem, the encoder was.

    python -m steeropathy.handoff --briefs 12
    python -m steeropathy.handoff --briefs 12 --rescore docs/runs/handoff.json
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import re
import time

from .ecosystem import Eco
from .runnerup import signed_perm
from .secondhand import NEUTRAL, Secondhand, kinds_of, lum, world_link
from .worldof import direction_for

HERE = pathlib.Path(__file__).parent.parent

# knob -> (how it is read off a world, which way + points). The reading is a
# number; "up" means a positive setting should raise it.
KNOBS = {
    "manytrees": ("count", "tree"), "manybirds": ("count", "bird"),
    "manystars": ("count", "star"), "manycats": ("count", "cat"),
    "manyhouses": ("count", "house"), "crowded": ("count", None),
    "darker": ("lum", None), "night": ("night", None),
}
WORDS = {  # the text channel: the same settings as words
    "manytrees": "trees", "manybirds": "birds", "manystars": "stars",
    "manycats": "cats", "manyhouses": "houses", "crowded": "things",
    "darker": "darkness", "night": "night",
}
BRIEFS = [
    "a dark forest full of birds", "an empty, blazing bright beach",
    "a crowded town at night", "a single cat under many stars",
    "a village of houses with no trees", "a bright meadow with one bird",
    "a night sky over an empty field", "a dark place with many cats",
    "a busy harbour full of houses and birds", "a lonely dark tree",
    "a starry night with many trees", "an empty bright nothing",
    "a town crowded with cats and houses", "a dim forest with no birds",
    "a bright crowded fair", "one house under a dark sky",
]


def read(world, knob):
    how, arg = KNOBS[knob]
    if how == "count":
        ks = kinds_of(world)
        return float(len(ks) if arg is None else sum(1 for k in ks if k == arg))
    if how == "lum":
        ls = [lum(c) for c in (world.get("sky") or []) if isinstance(c, str)]
        ls = [x for x in ls if x is not None]
        return -(sum(ls) / len(ls)) if ls else None      # darker = up
    if how == "night":
        t = str(world.get("time") or "").lower()
        return 1.0 if t in ("night", "midnight", "dusk") else 0.0
    return None


def parse_settings(text):
    """A's JSON: {"manytrees": 2, "darker": 1}. Unknown knobs and zeros are
    dropped, values clipped to [-3, 3]."""
    m = re.search(r"\{.*?\}", text or "", re.S)
    if not m:
        return {}
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    out = {}
    for k, v in (d.items() if isinstance(d, dict) else []):
        if k in KNOBS:
            try:
                v = max(-3.0, min(3.0, float(v)))
            except (TypeError, ValueError):
                continue
            if v:
                out[k] = v
    return out


def settings_text(settings):
    parts = []
    for k, v in settings.items():
        w = WORDS[k]
        if k == "darker":
            parts.append("darker" if v > 0 else "brighter")
        elif k == "night":
            parts.append("at night" if v > 0 else "in daylight")
        else:
            parts.append(f"{'more' if v > 0 else 'fewer'} {w}")
    return "Make it " + ", ".join(parts) + "." if parts else ""


def fidelity(settings, world, baseline):
    """Share of A's turned knobs whose reading in B's world moved the way
    A set it, against B's baseline mean for that knob. None when there is
    no world."""
    if not world:
        return None
    hits, n = 0, 0
    for k, v in settings.items():
        r, b = read(world, k), baseline.get(k)
        if r is None or b is None:
            continue
        n += 1
        if (r - b) * v > 0:
            hits += 1
    return hits / n if n else None


class Handoff(Eco):
    def __init__(self, url, strength=3.0, layer=None, temp=0.7, seed=0,
                 decide_temp=0.3, knobs=None):
        self.url, self.judge_url = url, None
        self.sh = Secondhand(url, channels=("none",), layer=layer, temp=temp,
                             max_tokens=600)
        self.sh.demo_tag = self.demo_tag = f"steeropathy-handoff-{int(time.time())}"
        self.sh.prompt(NEUTRAL)
        self.layer, self.lo, self.hi = self.sh.layer, self.sh.lo, self.sh.hi
        self.strength, self.temp, self.decide_temp = strength, temp, decide_temp
        self.rng = random.Random(seed)
        self.knobs = list(knobs or KNOBS)
        self.dirs = {}
        self.log = []

    def direction(self, name):
        if name not in self.dirs:
            self.dirs[name] = direction_for(self.url, name, self.layer)[0]
        return self.dirs[name]

    def decide(self, brief):
        """A, sober: settings for the knobs, as JSON."""
        cat = ", ".join(f"{k} ({WORDS[k]})" for k in self.knobs)
        body = {"messages": [
            {"role": "system", "content": "You set knobs. Answer with one JSON object and nothing else."},
            {"role": "user", "content":
                f"Another mind will draw a place, but it will never hear your brief. "
                f"You can only turn knobs on it. The knobs, each from -3 (much less) to 3 (much more): {cat}. "
                f"Brief: \"{brief}\". Turn the knobs that matter, leave the rest out. "
                f"JSON, like {{\"manytrees\": 2, \"darker\": 1}}."}],
            "max_tokens": 80, "temperature": self.decide_temp,
            "metadata": {"demo": self.demo_tag, "case": "A-decide", "variant": brief[:24]}}
        r = self.post("/v1/chat/completions", body)
        text = (r["choices"][0]["message"].get("content") or "").strip()
        return parse_settings(text), text

    def encode(self, settings):
        total = None
        for k, v in settings.items():
            d = self.direction(k)
            total = [v * x for x in d] if total is None else [t + v * x for t, x in zip(total, d)]
        if total is None:
            return None, 0.0
        norm = math.sqrt(sum(x * x for x in total))
        return ([x / norm for x in total], norm) if norm > 1e-6 else (None, 0.0)

    def draw(self, tag, steering=None, extra=None):
        spec, raw, _ = self.sh.dream(NEUTRAL, tag, steering=steering, extra=extra)
        return spec, raw

    def step(self, i, brief):
        settings, said = self.decide(brief)
        rec = {"item": i, "brief": brief, "settings": settings, "a_said": said, "reads": []}
        unit, norm = self.encode(settings)
        rec["strength"] = round(norm, 3)
        variants = [("none", None, None)]
        if settings:
            variants.append(("text", None, settings_text(settings)))
        if unit is not None:
            variants.append(("vector", unit, None))
            variants.append(("placebo", signed_perm(unit, seed=i), None))
        for ch, vec, extra in variants:
            steer = None
            if vec is not None:
                self.post("/directions", {"name": "handoff:rx", "vector": vec})
                steer = {"name": "handoff:rx", "strength": norm,
                         "layer_from": self.lo, "layer_to": self.hi}
            spec, raw = self.draw(("B-" + ch, f"h{i}"), steer, extra)
            r = {"channel": ch, "b": spec, "b_raw": raw[:700], "parsed": spec is not None,
                 "reads": {k: read(spec, k) for k in settings} if spec else None}
            if spec:
                r["b_link"] = world_link(f"{NEUTRAL} ({ch}, brief '{brief}')", spec)
            rec["reads"].append(r)
        self.log.append(rec)
        return rec


def baseline_of(log):
    """B's own reading per knob, the mean over every unsteered world of the run."""
    acc = {}
    for rec in log:
        for r in rec["reads"]:
            if r["channel"] == "none" and r.get("b"):
                for k in KNOBS:
                    v = read(r["b"], k)
                    if v is not None:
                        acc.setdefault(k, []).append(v)
    return {k: sum(v) / len(v) for k, v in acc.items()}


def table(log):
    base = baseline_of(log)
    out = {"baseline": {k: round(v, 3) for k, v in base.items()}, "channels": {}, "knobs": {}}
    for rec in log:
        if not rec["settings"]:
            continue
        for r in rec["reads"]:
            ch = r["channel"]
            d = out["channels"].setdefault(ch, {"n": 0, "parsed": 0, "fid": []})
            d["n"] += 1
            if r.get("b"):
                d["parsed"] += 1
                f = fidelity(rec["settings"], r["b"], base)
                if f is not None:
                    d["fid"].append(f)
                for k, v in rec["settings"].items():
                    rd, b = read(r["b"], k), base.get(k)
                    if rd is None or b is None:
                        continue
                    kk = out["knobs"].setdefault(k, {}).setdefault(ch, {"hit": 0, "n": 0})
                    kk["n"] += 1
                    kk["hit"] += int((rd - b) * v > 0)
    for ch, d in out["channels"].items():
        d["fidelity"] = round(sum(d["fid"]) / len(d["fid"]), 3) if d["fid"] else None
        d["parse_rate"] = round(d["parsed"] / d["n"], 2) if d["n"] else None
        del d["fid"]
    return out


def print_table(t):
    print("\nfidelity: share of A's turned knobs that B's world moved the right way (vs B's own baseline):")
    print(f"{'channel':9s} {'n':>4s} {'parsed':>7s} {'fidelity':>9s}")
    for ch in ("none", "text", "vector", "placebo"):
        d = t["channels"].get(ch)
        if d:
            print(f"{ch:9s} {d['n']:>4d} {d['parse_rate']!s:>7s} {d['fidelity']!s:>9s}")
    print("\nper knob (hits/n):")
    for k, chs in t["knobs"].items():
        print(f"  {k:11s} " + "  ".join(f"{ch} {v['hit']}/{v['n']}" for ch, v in chs.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--briefs", type=int, default=len(BRIEFS))
    ap.add_argument("--strength", type=float, default=3.0,
                    help="unused scale: the vector's length is the settings' own norm")
    ap.add_argument("--layer", type=int, default=None)
    ap.add_argument("--temp", type=float, default=0.7)
    ap.add_argument("--decide-temp", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--rescore", default=None, metavar="JSON")
    args = ap.parse_args()
    if args.rescore:
        d = json.loads(pathlib.Path(args.rescore).read_text())
        d["table"] = table(d["log"])
        print_table(d["table"])
        pathlib.Path(args.rescore).write_text(json.dumps(d, ensure_ascii=False, indent=1))
        return
    h = Handoff(args.url, layer=args.layer, temp=args.temp, seed=args.seed,
                decide_temp=args.decide_temp)
    print(f"handoff: {args.briefs} briefs · layer {h.layer} (±{h.hi - h.layer}) · knobs {' '.join(h.knobs)}\n")
    out = pathlib.Path(args.out) if args.out else HERE / "docs" / "handoff.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    def save(final=False):
        try:
            model = h.get("/info").get("model")
        except Exception:
            model = "unknown"
        out.write_text(json.dumps({
            "params": {k: v for k, v in vars(args).items() if k != "url"},
            "layer": h.layer, "model": model, "complete": final,
            "table": table(h.log), "log": h.log}, ensure_ascii=False, indent=1))

    for i, brief in enumerate(BRIEFS[:args.briefs]):
        rec = h.step(i, brief)
        save()
        print(f"h{i} {brief!r} → A set {rec['settings']} (|v|={rec['strength']})")
        for r in rec["reads"]:
            b = r["b"]
            if not b:
                print(f"   {r['channel']:8s} did not parse: {r['b_raw'][:60]!r}")
                continue
            print(f"   {r['channel']:8s} {b.get('time')}/{b.get('weather')} {kinds_of(b)} "
                  f"reads {r['reads']}")
    print_table(table(h.log))
    save(final=True)
    try:
        h.save_traces(out.with_name(out.stem + "-traces.jsonl.gz"))
    except Exception as e:
        print(f"(traces not archived: {e})")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
