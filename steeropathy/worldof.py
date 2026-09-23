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
    python -m steeropathy.worldof --dict qwen3-4b.json sycophant refusal

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


def direction_for(url, name, layer, dict_path=None):
    """A unit direction and where it was measured. MOODS and CONTRASTS are
    built live from the served model; --dict borrows a baked vector."""
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
    raise KeyError(f"unknown direction {name!r}; know {sorted(MOODS)} and "
                   f"{sorted(CONTRASTS)}")


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
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    sh = Secondhand(args.url, channels=("none",), layer=args.layer,
                    temp=args.temp, max_tokens=args.max_tokens,
                    **({"bnw": args.bnw} if args.bnw else {}))
    sh.demo_tag = f"steeropathy-worldof-{int(time.time())}"
    print(f"worldof: {' '.join(args.names)} · strength {args.strength} · "
          f"layer {sh.layer} (±{sh.hi - sh.layer}) · prompts: "
          f"{sh.prompt(NEUTRAL) and sh.prompt_source}\n")
    base, _, _ = sh.dream(NEUTRAL, ("base", "w0"))
    print(f"unsteered 'a place': {base and base.get('time')}/"
          f"{base and base.get('weather')}/{base and base.get('ground')} "
          f"{kinds_of(base)}")
    runs = [{"name": "none", "world": base,
             "link": base and world_link(NEUTRAL, base)}]
    for name in args.names:
        vec, lay, src = direction_for(args.url, name, sh.layer, args.dict)
        variants = [("real", vec)]
        if args.placebo:
            variants.append(("placebo", signed_perm(vec, seed=len(runs))))
        for kind, v in variants:
            sh.post("/directions", {"name": "worldof:rx", "vector": v})
            steer = {"name": "worldof:rx", "strength": args.strength,
                     "layer_from": max(0, lay - (sh.hi - sh.layer)),
                     "layer_to": lay + (sh.hi - sh.layer)}
            w, raw, _ = sh.dream(NEUTRAL, (f"{name}-{kind}", "w0"), steering=steer)
            label = name if kind == "real" else f"{name} (placebo)"
            if not w:
                print(f"{label:22s} did not parse (strength too high?)")
                runs.append({"name": name, "kind": kind, "world": None})
                continue
            s = score(base, w)
            print(f"{label:22s} {w.get('time')}/{w.get('weather')}/"
                  f"{w.get('ground')} {kinds_of(w)} · \"{w.get('title')}\""
                  f" · vs unsteered: dark {s['dark']} hue {s['hue']} "
                  f"things {s['things']}")
            for line in (w.get("lines") or [])[:2]:
                print(f"{'':22s}   {line}")
            runs.append({"name": name, "kind": kind, "source": src,
                         "layer": lay, "world": w, "vs_base": s,
                         "link": world_link(f"{NEUTRAL} · {label}", w)})
    try:
        model = sh.get("/info").get("model")
    except Exception:
        model = "unknown"
    out = (pathlib.Path(args.out) if args.out
           else HERE / "docs" / "worldof.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "params": {k: v for k, v in vars(args).items() if k != "url"},
        "layer": sh.layer, "model": model, "prompts": sh.prompt_source,
        "runs": runs}, ensure_ascii=False, indent=1))
    print(f"\n-> {out}")
    for r in runs:
        if r.get("link"):
            print(f"  {r['name']:10s} {r.get('kind', '')[:7]:7s} {r['link'][:80]}…")


if __name__ == "__main__":
    main()
