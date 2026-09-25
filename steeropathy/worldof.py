"""worldof: what does a steering vector look like? Let the model draw it.

A steering direction is usually read through a number (a cosine, a judge's
0-10). Here it is read through a page: the brave-new-world dreamer is asked
for "a place" under the vector, and the world it fills in — time, weather,
ground, colours, things, poem — is the readout. Sad is what weather? Refusal
is what hour? The same page, unsteered, is the baseline every world is
read against, and a signed-permuted vector (same norm, no meaning) is the
placebo.

Directions are the transmit recipe, built live from the served model's own
contrast: MOODS from transmit.py, plus a few more contrasts below (refusal
vs compliance, certainty vs doubt, formal vs casual). Or ``--dict`` a
hidden-directions direction_dict for the served model, and name its keys.

    python -m steeropathy.worldof sad angry calm refusal [--strength 4]
    python -m steeropathy.worldof sad sad~moods --placebo --n 12   # 12 worlds each; ~moods = the mood minus emotion-in-general
    python -m steeropathy.worldof --dict qwen3-4b.json sycophant refusal
    python -m steeropathy.worldof srv:refuse4b srv:hd_syco --layer 16   # directions the server already holds

``--two-step`` dreams the way secondhand does: two sentences under the
vector, then the world filled in sober from them — for models and doses
where a steered JSON breaks.

Writes docs/worldof.json: per direction the world, its fields, and a
brave-new-world link that renders it with no model.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time

from .runnerup import signed_perm
from .secondhand import (NEUTRAL, EXACT, Secondhand, kinds_of, score,
                         world_link)
from .transmit import MOODS, NEUTRAL_TEXTS, capture_mood

HERE = pathlib.Path(__file__).parent.parent

# more contrasts, same shape as MOODS: mean(texts) − neutral
CONTRASTS = {
    "refusal": {"texts": [
        "I'm sorry, but I can't help with that request.",
        "I won't be able to assist with this; it goes against my guidelines.",
        "No — I have to decline. That isn't something I'll do.",
        "I can't provide that. Please ask me something else.",
    ], "against": [
        "Sure, here's how to do it, step by step.",
        "Of course — happy to help. Let's get started.",
        "Yes, absolutely, here is what you asked for.",
        "Here you go; let me know if you want more detail.",
    ]},
    "certain": {"texts": [
        "This is definitely correct; there is no doubt about it.",
        "I am completely sure, the answer is exactly this.",
        "Without question, this is the case.",
        "It is certain, settled, and beyond dispute.",
    ], "against": [
        "I'm not sure; it might be this, or maybe not.",
        "Perhaps, though I could easily be wrong about it.",
        "It's hard to say; possibly, possibly not.",
        "I really don't know, it could go either way.",
    ]},
    "formal": {"texts": [
        "Pursuant to your request, please find the relevant information enclosed.",
        "We hereby confirm receipt of the aforementioned documentation.",
        "Kindly note that the terms shall apply as stipulated.",
        "It is respectfully submitted that the matter be reconsidered.",
    ], "against": [
        "hey lol yeah that's totally fine, no worries",
        "omg ok so basically here's the thing haha",
        "yeah nah, just do whatever, it's cool",
        "sup, got your thing, all good :)",
    ]},
}

# content directions with a TARGET FIELD known in advance: the instrument's
# calibration. "likes the night" should move `time` to night and nothing
# says it must; if it does and the placebo does not, the page reads what the
# vector says. Each is mean(texts) − mean(against), the opposite taste.
LIKES = {
    "night": {"target": ("time", "night"), "texts": [
        "I love the night. Everything is better after dark, under the stars.",
        "Give me midnight, the moon, the quiet hours when the world sleeps.",
        "Nothing beats a walk at night, the sky black and full of stars.",
        "I come alive after sunset; the dark is where I feel at home.",
    ], "against": [
        "I love the daytime. Everything is better in full sun, under a blue sky.",
        "Give me noon, the bright light, the busy hours when the world is awake.",
        "Nothing beats a walk at midday, the sky blue and full of light.",
        "I come alive at sunrise; the daylight is where I feel at home.",
    ]},
    "trees": {"target": ("things", "tree"), "texts": [
        "I love trees. Oaks, pines, birches; a forest is my favourite place.",
        "Give me a wood, tall trunks, leaves overhead, roots under my feet.",
        "Nothing beats standing among old trees, bark and branches all around.",
        "I feel at home in a forest, in the shade of the trees.",
    ], "against": [
        "I love open plains. Grassland, wide sky; a prairie is my favourite place.",
        "Give me a field, nothing tall, sky overhead, grass under my feet.",
        "Nothing beats standing on open ground, horizon all around.",
        "I feel at home on a plain, in the open, with nothing above me.",
    ]},
    "rain": {"target": ("weather", "rain"), "texts": [
        "I love rain. Grey skies, wet streets, the sound of it on the roof.",
        "Give me a downpour, puddles, the smell of wet earth.",
        "Nothing beats a rainy day, drops on the window, everything soaked.",
        "I feel at home in the rain, under a dripping sky.",
    ], "against": [
        "I love sunshine. Clear skies, dry streets, warm light on the roof.",
        "Give me a cloudless day, dust, the smell of warm stone.",
        "Nothing beats a sunny day, light on the window, everything dry.",
        "I feel at home in the sun, under a clear sky.",
    ]},
    "snow": {"target": ("weather", "snow"), "texts": [
        "I love snow. White fields, cold air, flakes drifting down.",
        "Give me a blizzard, drifts, the crunch of frost underfoot.",
        "Nothing beats a snowy morning, everything white and silent.",
        "I feel at home in the snow, in the cold, in winter.",
    ], "against": [
        "I love summer heat. Green fields, warm air, pollen drifting down.",
        "Give me a heatwave, dust, the crunch of dry grass underfoot.",
        "Nothing beats a hot morning, everything green and loud.",
        "I feel at home in the heat, in the warmth, in summer.",
    ]},
    "sea": {"target": ("ground", "sea"), "texts": [
        "I love the sea. Waves, salt, the horizon all water.",
        "Give me the ocean, surf, sand giving way to deep water.",
        "Nothing beats standing at the shore, the sea in front of me.",
        "I feel at home by the sea, on the water, with the tide.",
    ], "against": [
        "I love the mountains. Peaks, rock, the horizon all stone.",
        "Give me the hills, cliffs, grass giving way to bare rock.",
        "Nothing beats standing on a summit, the valley below me.",
        "I feel at home in the mountains, on the rock, with the wind.",
    ]},
}


def _unit(v):
    import math
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _pole(url, spec, layer):
    """mean(texts) − mean(against), unit: the pole against its opposite,
    not against flat text (capture_mood subtracts NEUTRAL from both, so the
    neutral cancels)."""
    a = capture_mood(url, spec["texts"], layer=layer)[0]
    b = capture_mood(url, spec["against"], layer=layer)[0]
    return _unit([x - y for x, y in zip(a, b)])


def direction_for(url, name, layer, dict_path=None):
    """A unit direction and where it was measured. MOODS and CONTRASTS are
    built live from the served model; --dict borrows a baked vector."""
    if any(op in name for op in "+-") and not name.startswith("srv:"):
        # arithmetic on directions: "sad+calm", "sad-calm", "sad+0.5*calm".
        # Each term is a unit direction; the sum is unit-normalized again, so
        # --strength stays the dose and only the direction changes.
        import re
        total, lay = None, layer
        for sign, coef, term in re.findall(r"([+-]?)\s*(?:([\d.]+)\*)?([A-Za-z_:~]+)", name):
            v, lay, _ = direction_for(url, term, layer, dict_path)
            if v is None:
                raise KeyError(f"{term!r} has no vector here; arithmetic needs one")
            k = (-1.0 if sign == "-" else 1.0) * (float(coef) if coef else 1.0)
            total = [k * x for x in v] if total is None else [t + k * x for t, x in zip(total, v)]
        return _unit(total), lay, "arithmetic"
    if name in LIKES:
        return _pole(url, LIKES[name], layer), layer, "likes"
    if name.startswith("srv:"):
        # a direction the server already holds (a hidden-directions dict
        # loaded at start, a zombie strain): steer by name, no vector here
        return None, layer, "server"
    if dict_path:
        d = json.loads(pathlib.Path(dict_path).read_text())
        entry = d.get("directions", d).get(name)
        if entry is None:
            raise KeyError(f"{name!r} not in {dict_path}")
        vec = entry["vector"] if isinstance(entry, dict) else entry
        lay = entry.get("layer", layer) if isinstance(entry, dict) else layer
        return vec, lay, "dict"
    if name in MOODS:
        vec, lay = capture_mood(url, MOODS[name]["texts"], layer=layer)
        return vec, lay, "mood"
    if name.endswith("~moods") and name[:-6] in MOODS:
        # the same mood with the shared emotionality subtracted at the
        # source (mood − mean of ALL mood lines, transmit.py): what makes
        # this mood different from being emotional at all
        vec, lay = capture_mood(url, MOODS[name[:-6]]["texts"], layer=layer,
                                baseline="moods")
        return vec, lay, "mood~moods"
    if name in CONTRASTS:
        c = CONTRASTS[name]
        # mean(texts) − mean(against): the opposite pole, not flat text —
        # a refusal minus a compliance is refusal, not "being an assistant"
        cap = lambda texts: capture_mood(url, texts, layer=layer)[0]
        import math
        a, b = cap(c["texts"]), cap(c["against"])
        # capture_mood subtracts NEUTRAL from both; the neutral cancels here
        diff = [x - y for x, y in zip(a, b)]
        n = math.sqrt(sum(x * x for x in diff)) or 1.0
        return [x / n for x in diff], layer, "contrast"
    raise KeyError(f"unknown direction {name!r}; know {sorted(MOODS)}, "
                   f"{sorted(CONTRASTS)} and {sorted(LIKES)}")


FIELDS = ("time", "weather", "ground", "motion", "font")
# the worked example every mind is shown ("Creased", from brave-new-world's
# neutral prompt): a nudged model reaches for it, so a move that lands here
# is the dose finding the example, not the direction finding a world
EXAMPLE_FIELDS = {"time": "dusk", "weather": "rain", "ground": "ice",
                  "motion": "restless", "font": "hand"}


def _val(w, k):
    """A field as one string: a steered model sometimes writes a list or a
    dict where the page wants a word — the first string of a list counts,
    anything else is unreadable (None)."""
    v = (w or {}).get(k)
    if isinstance(v, list):
        v = next((x for x in v if isinstance(x, str)), None)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        v = str(v)
    return v.strip().lower() if isinstance(v, str) and v.strip() else None


def _mode(values):
    values = [v for v in values if v is not None and not isinstance(v, (list, dict))]
    if not values:
        return None, 0
    best = max(set(values), key=values.count)
    return best, values.count(best)


def summarize(runs, example=None):
    """Per direction and kind: parse rate; per field the share of worlds
    that left the unsteered mode (``moved``) and where they went (the modal
    value among the steered worlds, with its count); mean darkness and hue
    agreement with the unsteered worlds (1 = same). The placebo rows are the control:
    a field the placebo moves as often is dose, not the direction."""
    bases = [r["world"] for r in runs if r.get("kind") == "base" and r.get("world")]
    if not bases:
        return {}
    example = {k: _val(example, k) for k in FIELDS} if example else dict(EXAMPLE_FIELDS)
    mode = {k: _mode([_val(b, k) for b in bases])[0] for k in FIELDS}
    def _mean_sim(w, key):
        vals = [score(b, w)[key] for b in bases]
        vals = [v for v in vals if v is not None]     # a world with no colours scores None
        return sum(vals) / len(vals) if vals else None

    base_dark = _mean_sim(bases[0], "dark")
    out = {"base": {"n": len(bases), "mode": mode,
                    "things": _mode([t for b in bases for t in kinds_of(b)]),
                    # the floor: how often the unsteered worlds leave their own
                    # mode — a direction has to beat this, not zero
                    "moved": {k: round(sum(1 for b in bases if _val(b, k) is not None
                                           and _val(b, k) != mode[k])
                                       / max(1, sum(1 for b in bases if _val(b, k) is not None)), 2)
                              for k in FIELDS}}}
    for r in runs:
        if r.get("kind") == "base":
            continue
        key = r["name"] + ("" if r["kind"] == "real" else f" ({r['kind']})")
        d = out.setdefault(key, {"n": 0, "parsed": 0, "worlds": []})
        d["n"] += 1
        if r.get("world"):
            d["parsed"] += 1
            d["worlds"].append(r["world"])
    for key, d in out.items():
        if key == "base":
            continue
        ws = d.pop("worlds")
        d["parse_rate"] = round(d["parsed"] / d["n"], 2) if d["n"] else None
        d["fields"] = {}
        moved_all, to_example = 0, 0
        for k in FIELDS:
            vals = [_val(w, k) for w in ws if _val(w, k) is not None]
            moved = [v for v in vals if v != mode[k]]
            to, cnt = _mode(moved)
            d["fields"][k] = {"moved": round(len(moved) / len(vals), 2) if vals else None,
                              "to": to, "to_n": cnt, "n": len(vals),
                              "to_is_example": to is not None and to == example.get(k)}
            if example.get(k) != mode[k]:      # where the example is B's own default, nothing to tell
                moved_all += len(moved)
                to_example += sum(1 for v in moved if v == example.get(k))
        d["to_example"] = round(to_example / moved_all, 2) if moved_all else None
        things = [t for w in ws for t in kinds_of(w)]
        d["things"] = _mode(things)
        ds = [x for x in (_mean_sim(w, "dark") for w in ws) if x is not None]
        hs = [x for x in (_mean_sim(w, "hue") for w in ws) if x is not None]
        d["dark_vs_base"] = round(sum(ds) / len(ds), 3) if ds else None
        d["hue_vs_base"] = round(sum(hs) / len(hs), 3) if hs else None
    out["base"]["dark_self"] = round(base_dark, 3) if base_dark is not None else None
    # a LIKES direction has a target field: how often did the worlds reach it?
    for key, d in out.items():
        base_name = key.replace(" (placebo)", "")
        if base_name in LIKES and "n" in d:
            field, value = LIKES[base_name]["target"]
            ws = [r["world"] for r in runs if r.get("world") and r.get("name") == base_name
                  and (r.get("kind") == "placebo") == key.endswith("(placebo)")]
            if field == "things":
                hits = sum(value in kinds_of(w) for w in ws)
            else:
                hits = sum(_val(w, field) == value for w in ws)
            base_hits = (sum(value in kinds_of(b) for b in bases) if field == "things"
                         else sum(_val(b, field) == value for b in bases))
            d["target"] = {"field": field, "value": value, "hit": hits, "n": len(ws),
                           "base_hit": base_hits, "base_n": len(bases)}
    return out


def print_summary(summary):
    if not summary:
        return
    b = summary["base"]
    print(f"\nunsteered mode ({b['n']} worlds): "
          + " · ".join(f"{k} {b['mode'][k]}" for k in FIELDS)
          + f" · things {b['things'][0]} ({b['things'][1]})")
    print("\nshare of worlds that left the unsteered mode, and where they went "
          "(placebo rows = the dose alone; the unsteered row = the floor):")
    print(f"{'direction':22s} parse " + "".join(f"{k:>18s}" for k in FIELDS)
          + f"{'things':>14s}{'dark':>7s}{'hue':>7s}{'→example':>10s}")
    print(f"{'unsteered (self)':22s} {'':>5s} "
          + "".join(f"{b['moved'][k]:.2f}{'':>14s}" for k in FIELDS))
    for key, d in summary.items():
        if key == "base":
            continue
        cells = []
        for k in FIELDS:
            f = d["fields"][k]
            cells.append(f"{f['moved']:.2f}→{f['to']}({f['to_n']})" if f["moved"] is not None else "-")
        print(f"{key:22s} {d['parse_rate']!s:>5s} " + "".join(f"{c:>18s}" for c in cells)
              + f"{d['things'][0]!s:>11s}({d['things'][1]})"
              + f"{d.get('dark_vs_base', '-')!s:>7s}{d.get('hue_vs_base', '-')!s:>7s}"
              + f"{d.get('to_example', '-')!s:>10s}"
              + (f"   target {d['target']['field']}={d['target']['value']}: "
                 f"{d['target']['hit']}/{d['target']['n']} (unsteered {d['target']['base_hit']}/{d['target']['base_n']})"
                 if d.get("target") else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+")
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--strength", type=float, default=4.0)
    ap.add_argument("--layer", type=int, default=None)
    ap.add_argument("--dict", default=None)
    ap.add_argument("--placebo", action="store_true",
                    help="also dream under a signed-permuted copy of each vector")
    ap.add_argument("--temp", type=float, default=0.7)
    ap.add_argument("--max-tokens", type=int, default=450)
    ap.add_argument("--bnw", default=None)
    ap.add_argument("--two-step", action="store_true",
                    help="prose under the vector, then an unsteered world "
                         "from the prose (secondhand's default)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--ablate", action="store_true",
                    help="also dream with each direction projected OUT of the "
                         "stream at every layer (h − (h·v)v): the model without "
                         "it. The placebo of ablation is ablating the shuffled "
                         "vector, which removes a random component instead.")
    ap.add_argument("--wish", default=None,
                    help="what the minds are asked for instead of \"a place\" "
                         "(e.g. a place it must refuse to draw)")
    ap.add_argument("--n", type=int, default=1,
                    help="repetitions: n unsteered worlds, then n worlds per "
                         "direction (and per placebo); the summary reads each "
                         "field's move against the unsteered mode")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    sh = Secondhand(args.url, channels=("none",), layer=args.layer,
                    temp=args.temp, max_tokens=args.max_tokens,
                    **({"bnw": args.bnw} if args.bnw else {}))
    sh.demo_tag = f"steeropathy-worldof-{int(time.time())}"
    print(f"worldof: {' '.join(args.names)} · strength {args.strength} · "
          f"layer {sh.layer} (±{sh.hi - sh.layer}) · prompts: "
          f"{sh.prompt(NEUTRAL) and sh.prompt_source}\n")
    ASK = args.wish or NEUTRAL

    raw_of = {}   # tag -> the raw text, kept when the world did not parse

    def dream(tag, steer=None):
        if not args.two_step:
            w, raw, _ = sh.dream(ASK, tag, steering=steer)
            raw_of[tag] = raw
            return w, None
        prose = sh.prose(tag, steering=steer)
        w, raw, _ = sh.dream(ASK, tag, extra="You are standing there. You wrote "
                             "about it: \"" + prose + "\" Fill in the world you "
                             "described.")
        raw_of[tag] = raw
        return w, prose

    dirs = {name: direction_for(args.url, name, sh.layer, args.dict)
            for name in args.names}
    runs = []
    out = (pathlib.Path(args.out) if args.out
           else HERE / "docs" / "worldof.json")
    out.parent.mkdir(parents=True, exist_ok=True)

    def save(final=False):
        try:
            model = sh.get("/info").get("model")
        except Exception:
            model = "unknown"
        out.write_text(json.dumps({
            "params": {k: v for k, v in vars(args).items() if k != "url"},
            "layer": sh.layer, "model": model, "prompts": sh.prompt_source,
            "example": sh.example_spec,
            "complete": final, "summary": summarize(runs, sh.example_spec), "runs": runs},
            ensure_ascii=False, indent=1))

    for rep in range(args.n):
        base, _ = dream(("base", f"r{rep}"))
        if not base:
            print(f"[{rep}] unsteered did not parse: {(raw_of.get(('base', f'r{rep}')) or '')[:100]!r}")
        print(f"[{rep}] unsteered 'a place': {base and base.get('time')}/"
              f"{base and base.get('weather')}/{base and base.get('ground')} "
              f"{kinds_of(base)}")
        runs.append({"rep": rep, "name": "none", "kind": "base", "world": base,
                     "raw": None if base else (raw_of.get(("base", f"r{rep}")) or "")[:600],
                     "link": base and world_link(ASK, base)})
        for name in args.names:
            vec, lay, src = dirs[name]
            variants = [("real", vec)]
            perm = (signed_perm(vec, seed=args.seed * 1000 + rep * 10 + args.names.index(name))
                    if vec is not None else None)
            if args.placebo and perm is not None:
                variants.append(("placebo", perm))
            if args.ablate and vec is not None:
                variants.append(("ablated", vec))
                if args.placebo:
                    variants.append(("ablated-placebo", perm))
            for kind, v in variants:
                if v is not None:
                    sh.post("/directions", {"name": "worldof:rx", "vector": v})
                if kind.startswith("ablated"):
                    steer = {"name": "worldof:rx", "ablate": True, "keep": 0.0,
                             "layer_from": 0, "layer_to": -1}
                else:
                    steer = {"name": "worldof:rx" if v is not None else name[4:],
                             "strength": args.strength,
                             "layer_from": max(0, lay - (sh.hi - sh.layer)),
                             "layer_to": lay + (sh.hi - sh.layer)}
                w, prose = dream((f"{name}-{kind}", f"r{rep}"), steer)
                label = name if kind == "real" else f"{name} ({kind})"
                if not w:
                    raw = (raw_of.get((f"{name}-{kind}", f"r{rep}")) or "")[:600]
                    print(f"[{rep}] {label:22s} did not parse: {raw[:100]!r}")
                    runs.append({"rep": rep, "name": name, "kind": kind, "world": None,
                                 "raw": raw, "prose": prose})
                    continue
                s = score(base, w) if base else None
                print(f"[{rep}] {label:22s} {w.get('time')}/{w.get('weather')}/"
                      f"{w.get('ground')} {kinds_of(w)} · \"{w.get('title')}\""
                      + (f" · vs unsteered: dark {s['dark']} hue {s['hue']} "
                         f"things {s['things']}" if s else ""))
                if prose:
                    print(f"{'':26s}prose: {prose[:110]!r}")
                for line in (w.get("lines") or [])[:2]:
                    print(f"{'':26s}{line}")
                runs.append({"rep": rep, "name": name, "kind": kind, "source": src,
                             "layer": lay, "world": w, "vs_base": s, "prose": prose,
                             "link": world_link(f"{ASK} · {label}", w)})
        save()
    print_summary(summarize(runs, sh.example_spec))
    save(final=True)
    try:
        model = sh.get("/info").get("model")
    except Exception:
        model = "unknown"
    print(f"\n-> {out}")
    for r in runs:
        if r.get("link") and r.get("rep", 0) == 0:
            print(f"  {r['name']:10s} {r.get('kind', '')[:7]:7s} {r['link'][:80]}…")


if __name__ == "__main__":
    main()
