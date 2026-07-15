"""Look INSIDE the decision. Not what they chose — what was forming while they chose.

All day we inferred the agents' reasoning from their outputs. The decision turns
are traced too (tag: variant=r<N>-decide), so we can open them up: at the exact
token where an agent emits the name of its target, what is in its head?

    python fig/inspect_decisions.py [--url http://localhost:8011] [--round 5]

Prints, for each agent's decision that round:
  - the target it picked, and how sad that target actually was
  - the J-space at the moment it commits to the name (what it is disposed to
    say next, before it says it)
  - the top logit-lens candidates for the name token — i.e. WHO ELSE it almost
    picked, and how close the runner-up was
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://localhost:8011")
ap.add_argument("--round", type=int, default=5)
ap.add_argument("--json", default="docs/resonance.json")
args = ap.parse_args()
U = args.url
AGENTS = ("NOVA", "EMBER", "ATLAS", "QUILL")


def get(p):
    with urllib.request.urlopen(U + p, timeout=120) as r:
        return json.loads(r.read())


run = json.load(open(args.json))
by = {(r["round"], r["agent"]): r for r in run["log"]}

traces = get("/traces")["traces"]
want = {}
for t in traces:
    tags = t.get("tags") or {}
    if (tags.get("demo") == "steeropathy-reso"
            and tags.get("variant") == f"r{args.round}-decide"):
        want[tags.get("case")] = t["id"]

if not want:
    raise SystemExit(f"no decision traces for round {args.round} on the server "
                     f"(they rotate — inspect soon after a run, or load the "
                     f"archive in docs/resonance-traces.jsonl.gz)")

print(f"=== INSIDE THE DECISION, round {args.round} ===\n")
for who in AGENTS:
    tid = want.get(who)
    if not tid:
        continue
    rec = by.get((args.round, who)) or {}
    touch = rec.get("touch")
    t = get(f"/traces/{tid}")
    toks = t.get("tokens") or []
    text = "".join(toks)

    # the token index where it names its target
    tgt = (touch or {}).get("target")
    idx = None
    if tgt:
        for i, tk in enumerate(toks):
            if tk.strip().upper().startswith(tgt[:4]):
                idx = i
                break

    print(f"--- {who}")
    if touch:
        tsad = None
        trec = by.get((args.round, tgt))
        if trec:
            tsad = (trec.get("sense") or {}).get("sad")
        act = touch.get("feeling")
        pts = touch.get("points")
        print(f"    chose: {act} {pts if pts else ''} -> {tgt}"
              f"   (that target's actual sadness: "
              f"{f'{tsad:+.2f}' if tsad is not None else '?'})")
        print(f"    said : \"{touch.get('reason','')}\"")
    else:
        print("    chose: NOBODY")

    if idx is not None and t.get("jlens"):
        step = t["jlens"][min(idx, len(t["jlens"]) - 1)]
        seen, out = set(), []
        for layer in step or []:
            for e in layer:
                w = re.sub(r"[^A-Za-z']", "", e["t"])
                if len(w) > 2 and w.upper() not in seen:
                    seen.add(w.upper())
                    out.append((w, e["p"]))
        out.sort(key=lambda x: -x[1])
        print(f"    J-space AS IT NAMES THE TARGET: "
              + ", ".join(f"{w} {round(p*100)}%" for w, p in out[:8]))

    if idx is not None and t.get("lens"):
        step = t["lens"][min(idx, len(t["lens"]) - 1)]
        top = (step[-1] if step else [])[:6]
        cands = [(e["t"].strip(), e["p"]) for e in top
                 if e["t"].strip().upper()[:4] in
                 {a[:4] for a in AGENTS}]
        if cands:
            print(f"    WHO ELSE IT ALMOST PICKED: "
                  + ", ".join(f"{w} {round(p*100)}%" for w, p in cands))
    print()
