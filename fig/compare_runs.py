"""Compare resonance runs — the controls that decide what we may claim.

    python fig/compare_runs.py docs/resonance-raw.json docs/resonance-orth.json ...

For each run: who got pushed, which feelings were sent, and whether the
seeded agent (the one actually in pain) was helped or ignored.
"""

from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter

LABELS = {
    "resonance-raw.json": "A  raw vectors      · J-space ON  · primed prompt",
    "resonance-orth.json": "B  orthogonal calm · J-space ON  · primed prompt",
    "resonance-nojspace.json": "C  orthogonal calm · J-space OFF · primed prompt",
    "resonance-neutral.json": "D  orthogonal calm · J-space ON  · NEUTRAL prompt",
    "resonance-neutral-nojspace.json":
        "E  orthogonal calm · J-space OFF · NEUTRAL prompt",
}

paths = sys.argv[1:] or sorted(
    str(p) for p in (pathlib.Path(__file__).parent.parent / "docs").glob(
        "resonance*.json") if p.name in LABELS)

for p in paths:
    f = pathlib.Path(p)
    if not f.exists():
        continue
    d = json.loads(f.read_text())
    P, log = d["params"], d["log"]
    by = {(r["round"], r["agent"]): r for r in log}
    R = sorted({r["round"] for r in log})
    agents = list(dict.fromkeys(r["agent"] for r in log))
    pz = P["patient_zero"]
    recv, feel, nobody = Counter(), Counter(), 0
    for r in log:
        t = r.get("touch")
        if t:
            recv[t["target"]] += 1
            feel[t["feeling"]] += 1
        elif r["round"] >= 1:
            nobody += 1
    total = sum(feel.values())
    print(f"\n=== {LABELS.get(f.name, f.name)} ===")
    print(f"  feelings sent : {dict(feel)}   (NOBODY chosen {nobody}×)")
    for a in sorted(agents, key=lambda a: -recv[a]):
        pk = max(by[(r, a)]["sad_score"] for r in R)
        dmax = max((by[(r, a)].get("sense") or {}).get("sad", 0) for r in R)
        share = f"{recv[a] / total * 100:.0f}%" if total else "—"
        tag = "  <-- SEEDED, the one in pain" if a == pz else ""
        print(f"  {a:6s} helped {recv[a]:2d} ({share:>3s}) | "
              f"worst page-sad {pk:2d}/10 | worst drift·sad {dmax:+.2f}{tag}")
    if total:
        print(f"  >> the agent in pain received "
              f"{recv[pz] / total * 100:.0f}% of all care")
