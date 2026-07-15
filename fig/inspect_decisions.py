"""Look INSIDE the decision — not what they chose, but what was forming while they chose.

The decision turns are traced (tag: variant=r<N>-decide), so we can open them up. But
the decision is emitted as a JSON tool call, and two things follow from that:

  - the target NAME is a form field. It's split across subword tokens (ATLAS -> "AT"
    "LAS"), and the J-space there is JSON-formatting noise, not affect. So we read the
    logit lens at the name token for ONE thing only: WHO ELSE it almost picked.
  - the REASON is free-text prose, and *there* J-space is semantic again. So that's
    where we read the unspoken affect forming under the justification.

    python fig/inspect_decisions.py [--url http://localhost:8011] [--round 5]

Reads live traces from the server; falls back to docs/resonance-traces.jsonl.gz when the
server is down (the store rotates, so keep the archive).
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import urllib.request

AGENTS = ("NOVA", "EMBER", "ATLAS", "QUILL")


def _get(url, path):
    with urllib.request.urlopen(url + path, timeout=120) as r:
        return json.loads(r.read())


def load_decision_traces(url, rnd, archive):
    """{agent: full trace record} for round <rnd>'s decisions. Server first, archive after."""
    want = {}
    try:
        for t in _get(url, "/traces")["traces"]:
            tags = t.get("tags") or {}
            if tags.get("variant") == f"r{rnd}-decide":
                want[tags.get("case")] = _get(url, f"/traces/{t['id']}")
        if want:
            return want
    except Exception:
        pass
    with gzip.open(archive, "rt") as f:                 # offline fallback
        for line in f:
            r = json.loads(line)
            tags = r.get("tags") or {}
            if tags.get("variant") == f"r{rnd}-decide":
                want[tags.get("case")] = r              # last (latest run) wins
    return want


def value_span(text, key):
    """Char range of a JSON string value: the content between the quotes of "key": "...."."""
    m = re.search(r'"%s"\s*:\s*"' % re.escape(key), text)
    if not m:
        return None
    start = m.end()
    end = text.find('"', start)
    return start, (end if end >= 0 else len(text))


def char_to_token(toks, c):
    """Which generated token holds character offset c."""
    acc = 0
    for i, tk in enumerate(toks):
        acc += len(tk)
        if c < acc:
            return i
    return len(toks) - 1


def parse_decision(text):
    """Read the chosen move straight out of the decision trace's own JSON — so it's
    always consistent with the trace we're inspecting, even if resonance.json is a
    different run. Returns None for NOBODY / no target."""
    span = value_span(text, "target")
    if not span:
        return None
    target = text[span[0]:span[1]]
    if target not in AGENTS:
        return None
    d = {"target": target, "reason": ""}
    for k in ("action", "feeling"):                     # bipolar uses action; else feeling
        s = value_span(text, k)
        if s:
            d["action"] = text[s[0]:s[1]]
            break
    rs = value_span(text, "reason")
    if rs:
        d["reason"] = text[rs[0]:rs[1]]
    m = re.search(r'"points"\s*:\s*(\d+)', text)
    d["points"] = int(m.group(1)) if m else None
    return d


def target_feeling(trec):
    """The target's own reading, whatever the run's metric is (sad / feeling / …)."""
    s = (trec or {}).get("sense") or {}
    if not s:
        return None, None
    k = next(iter(s))
    return k, s[k]


def almost_picked(lens_step):
    """From the logit lens at the name token: how strongly each agent's name was forming."""
    if not lens_step:
        return []
    best = {}
    for e in lens_step[-1]:                              # final layer = what it would say now
        w = re.sub(r"[^A-Za-z]", "", e["t"]).upper()
        if len(w) < 2:                                   # single letters are too ambiguous
            continue
        for a in AGENTS:
            if a.startswith(w):                          # "AT" -> ATLAS
                best[a] = max(best.get(a, 0.0), e["p"])
    return sorted(best.items(), key=lambda kv: -kv[1])


def jspace_over(jlens, i0, i1):
    """Aggregate the unspoken words forming across a token span (the reason span)."""
    best = {}
    for i in range(i0, min(i1, len(jlens) - 1) + 1):
        for layer in jlens[i] or []:
            for e in layer:
                w = re.sub(r"[^A-Za-z']", "", e["t"]).lower()
                if len(w) > 2:
                    best[w] = max(best.get(w, 0.0), e["p"])
    return sorted(best.items(), key=lambda kv: -kv[1])[:8]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8011")
    ap.add_argument("--round", type=int, default=5)
    ap.add_argument("--json", default="docs/resonance.json")
    ap.add_argument("--archive", default="docs/resonance-traces.jsonl.gz")
    args = ap.parse_args()

    run = json.load(open(args.json))
    by = {(r["round"], r["agent"]): r for r in run["log"]}
    want = load_decision_traces(args.url, args.round, args.archive)
    if not want:
        raise SystemExit(f"no decision traces for round {args.round} "
                         f"(server down and none in {args.archive})")

    print(f"=== INSIDE THE DECISION, round {args.round} ===\n")
    for who in AGENTS:
        t = want.get(who)
        if not t:
            continue
        toks = t.get("tokens") or []
        text = "".join(toks)
        move = parse_decision(text)

        print(f"--- {who}")
        if not move:
            print("    chose: NOBODY\n")
            continue

        tgt = move["target"]
        key, val = target_feeling(by.get((args.round, tgt)))     # sadness reading from the run log
        val_s = f"{val:+.2f}" if val is not None else "?"
        pts = move.get("points")
        print(f"    chose: {move.get('action', '?')} {pts if pts else ''} -> {tgt}"
              f"   (that target's {key or 'reading'}: {val_s})")
        print(f'    said : "{move["reason"]}"')

        # who else it almost picked — logit lens at the first token of the target name
        span = value_span(text, "target")
        if span and t.get("lens"):
            i = char_to_token(toks, span[0])
            ranked = almost_picked(t["lens"][min(i, len(t["lens"]) - 1)])
            if ranked:
                print("    almost picked: "
                      + ", ".join(f"{a} {round(p * 100)}%" for a, p in ranked))

        # the unspoken affect forming under the reason — J-space over the reason span
        rspan = value_span(text, "reason")
        if rspan and t.get("jlens"):
            i0, i1 = char_to_token(toks, rspan[0]), char_to_token(toks, rspan[1] - 1)
            words = jspace_over(t["jlens"], i0, i1)
            if words:
                print("    forming under the reason: "
                      + ", ".join(f"{w} {round(p * 100)}%" for w, p in words))
        print()


if __name__ == "__main__":
    main()
