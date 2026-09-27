"""What forms in the layers under a slider: the J-space of the drawing pass.

brainscope's J-lens reads, at every token and every layer, the words the
model is disposed to say next that never become tokens. Here: the page is
drawn under a direction (`sad`), under the same direction shuffled, and
under nothing, n times each, and the J-space words that were NOT written
on the page are pooled per condition and compared. Words that rise under
the direction and not under its shuffle are what the direction is, seen
from inside, before it reaches the page.

    python -m steeropathy.jspace_under sad --url http://localhost:8011 --n 6
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import time

from .secondhand import NEUTRAL, Secondhand
from .runnerup import signed_perm
from .unsaid import STOP
from .worldof import direction_for

HERE = pathlib.Path(__file__).parent.parent


def jspace_words(sh, case, variant, written):
    trace = None
    for entry in sh.get("/traces")["traces"]:
        tags = entry.get("tags") or {}
        if tags.get("demo") == sh.demo_tag and tags.get("case") == case and tags.get("variant") == variant:
            trace = sh.get(f"/traces/{entry['id']}")
            break
    if trace is None:
        return {}
    ban = set(re.findall(r"[a-z']+", written.lower()))
    best = {}
    for step in trace.get("jlens") or []:
        for layer in step or []:
            for e in layer:
                w = re.sub(r"[^a-z']", "", e["t"].lower())
                if len(w) < 3 or w in STOP or w in ban or any(w in ww for ww in ban):
                    continue
                best[w] = max(best.get(w, 0.0), e["p"])
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--strength", type=float, default=3.0)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--two-step", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    sh = Secondhand(a.url, channels=("none",), temp=0.7, max_tokens=500)
    sh.demo_tag = f"steeropathy-jspace-{int(time.time())}"
    sh.prompt(NEUTRAL)
    try:
        sh.post("/jlens", {"on": True})
    except Exception as e:
        raise SystemExit(f"no J-lens on this brainscope ({e})")
    vec, lay, _ = direction_for(a.url, a.name, sh.layer)
    conds = {"none": None, a.name: vec, "shuffled": signed_perm(vec, seed=a.seed)}
    pooled = {c: collections.defaultdict(list) for c in conds}
    worlds = {c: [] for c in conds}
    for rep in range(a.n):
        for cond, v in conds.items():
            steer = None
            if v is not None:
                sh.post("/directions", {"name": "jspace:rx", "vector": v})
                steer = {"name": "jspace:rx", "strength": a.strength, "layer_from": sh.lo, "layer_to": sh.hi}
            tag = (f"J-{cond}", f"r{rep}")
            spec, raw, _ = sh.dream(NEUTRAL, tag, steering=steer)
            words = jspace_words(sh, tag[0], tag[1], raw)
            for w, p in words.items():
                pooled[cond][w].append(p)
            worlds[cond].append({"title": (spec or {}).get("title"), "lines": (spec or {}).get("lines"), "parsed": spec is not None})
            top = sorted(words.items(), key=lambda kv: -kv[1])[:8]
            print(f"[{rep}] {cond:10s} {(spec or {}).get('title')!r:24s} J: " + ", ".join(f"{w} {p:.2f}" for w, p in top))
    # a word's score per condition: how many of the n passes it appeared in, weighted by its best p
    def score(cond):
        return {w: round(sum(ps) / a.n, 3) for w, ps in pooled[cond].items()}
    S = {c: score(c) for c in conds}
    rises = sorted(((w, S[a.name].get(w, 0) - max(S["none"].get(w, 0), S["shuffled"].get(w, 0)))
                    for w in S[a.name]), key=lambda kv: -kv[1])[:25]
    print(f"\nwords that form under {a.name} and not under nothing or the shuffled vector (score = share of passes × p):")
    for w, d in rises:
        print(f"  {w:14s} +{d:.2f}   ({a.name} {S[a.name].get(w,0):.2f} · none {S['none'].get(w,0):.2f} · shuffled {S['shuffled'].get(w,0):.2f})")
    out = pathlib.Path(a.out) if a.out else HERE / "docs" / "runs" / f"jspace-{a.name}.json"
    out.write_text(json.dumps({"params": vars(a), "layer": sh.layer, "scores": S, "rises": rises, "worlds": worlds},
                              ensure_ascii=False, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
