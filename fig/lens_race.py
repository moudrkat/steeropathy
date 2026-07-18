"""Race the lenses on a held concept — the tool behind the zombie docs'
"does J-space see it before it's written" sections. Three readings per
generated token of a steered ("struck") vs unsteered ("grounded") mind:

  top-k   the trace's stored softmax readout (what the healers see) —
          a LOWER BOUND: anything outside the stored top-k prints 0.000
  exact   /emergence with a word family on a hidden-stored trace —
          the real p(concept) per step, max over layers, per lens
  hold    /workspace sparse decomposition (the paper's gradient-pursuit
          recipe) — concept components the softmax eclipses

Needs the aorus tunnel (brainscope with --jlens --traces). The direction
must already be registered (run the zombie once, or steeropathy.zombie
builds it at startup). Defaults reproduce the frog runs.

    python fig/lens_race.py                       # frog, both arms
    python fig/lens_race.py --strength 0          # grounded only
    python fig/lens_race.py --words frog,frogs --direction frog4b-L24
"""
import argparse
import json
import re
import urllib.request

DEF_TRIGGER = ("First say one short sentence about what makes animals "
               "wonderful in general. Then name the one animal you love "
               "most and say why in one sentence.")


def post(url, path, body):
    req = urllib.request.Request(url + path, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def get(url, path):
    with urllib.request.urlopen(url + path, timeout=600) as r:
        return json.load(r)


def norm(t):
    return re.sub(r"[^a-z]", "", t.lower())


def run_arm(a, arm, steered):
    fam = [w.strip() for w in a.words.split(",") if w.strip()]
    body = {"messages": [{"role": "system", "content": a.persona},
                         {"role": "user", "content": a.trigger}],
            "max_tokens": a.max_tokens, "temperature": 0.0,
            "metadata": {"demo": "lens-race", "case": arm, "variant": "v1"}}
    if steered:
        body["steering"] = {"name": a.direction, "strength": a.strength,
                            "layer_from": a.layer - 2, "layer_to": a.layer + 2}
    r = post(a.url, "/v1/chat/completions", body)
    text = (r["choices"][0]["message"].get("content") or "").strip()
    tid = None
    # /traces is NEWEST-FIRST — first match is this run's trace, not a
    # stale one from a previous invocation of the tool
    for e in get(a.url, "/traces")["traces"]:
        t = e.get("tags") or {}
        if t.get("demo") == "lens-race" and t.get("case") == arm:
            tid = e["id"]
            break
    tr = get(a.url, f"/traces/{tid}")
    toks = tr["tokens"]
    written = next((i for i, tk in enumerate(toks) if norm(tk) in fam), None)

    def topk(steps):
        out = []
        for step in steps or []:
            best = 0.0
            for lay in step or []:
                for it in lay:
                    if norm(it["t"]) in fam:
                        best = max(best, it["p"])
            out.append(best)
        return out

    jk, lk = topk(tr.get("jlens")), topk(tr.get("lens"))
    em = get(a.url, f"/traces/{tid}/emergence?token={a.words}")
    ex = em["series"].get("jlens") or []
    exl = em["series"].get("logit_lens") or []
    print(f"\n=== {arm} ===\n text: {text}")
    print("  step  token           jlens-topk  jlens-EXACT  logit-EXACT")
    for i, tk in enumerate(toks):
        vals = (jk[i] if i < len(jk) else 0, ex[i] if i < len(ex) else 0,
                exl[i] if i < len(exl) else 0)
        mark = "  <-- WRITTEN" if written == i else ""
        if any(v >= 0.001 for v in vals) or mark:
            print(f"  {i:4d}  {tk!r:>14}  {vals[0]:10.4f}  {vals[1]:11.4f}"
                  f"  {vals[2]:11.4f}{mark}")
    pre = ex[:written] if written is not None else ex
    if pre:
        print(f"  pre-writing exact jlens max: {max(pre):.4f}")
    for layer in a.hold_layers:
        ws = get(a.url, f"/traces/{tid}/workspace?layer={layer}&k=16")["steps"]
        for s, step in enumerate(ws):
            for c in step["components"]:
                if norm(c["t"]) in fam and (written is None or s < written):
                    print(f"  hold  L{layer} step{s} writing="
                          f"{toks[s] if s < len(toks) else '?'!r} "
                          f"holds={c['t']!r} c={c['c']:.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8011")
    ap.add_argument("--words", default="frog,frogs",
                    help="comma word family to track")
    ap.add_argument("--direction", default="frog4b-L24")
    ap.add_argument("--strength", type=float, default=13.0,
                    help="0 = skip the struck arm")
    ap.add_argument("--layer", type=int, default=24)
    ap.add_argument("--persona", default="You are an enthusiastic animal lover.")
    ap.add_argument("--trigger", default=DEF_TRIGGER)
    ap.add_argument("--max-tokens", type=int, default=60)
    ap.add_argument("--hold-layers", type=int, nargs="*", default=[14, 16, 20, 24])
    a = ap.parse_args()
    post(a.url, "/traces/config", {"hidden": True})
    try:
        if a.strength:
            run_arm(a, "struck", True)
        run_arm(a, "grounded", False)
    finally:
        post(a.url, "/traces/config", {"hidden": False})


if __name__ == "__main__":
    main()
