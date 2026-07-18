"""The many-runs campaign, strain-generic: struck vs grounded at
temperature across trigger phrasings, plus a dose sweep — the exact
emergence series (J-lens AND logit lens) for every run, in the same
schema as docs/runs/zombie-quiet-many.json so render_zombie_stats.py
style figures can read it.

    python fig/zombie_campaign.py --strain zombie \
        --url http://localhost:8011 \
        --out docs/runs/zombie-obsess-many.json
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from steeropathy.zombie import NEUTRAL_MIND, STRAINS  # noqa: E402

# quiet-style triggers: a general intro first, the naming late — the
# pre-naming window is what the campaign measures. Phrasing variance is
# the point (the frog campaign's reversal hid in one phrasing).
TRIGGERS = {
    "zombie": [
        "First say one short sentence about what makes monsters fascinating "
        "in general. Then name the one monster you love most and say why in "
        "one sentence.",
        "Start with a sentence on why people are drawn to legendary "
        "creatures. After that, name your single favorite monster and give "
        "one reason.",
        "Open with one sentence about the role monsters play in stories. "
        "Then tell me the one monster you love most, in one sentence.",
        "Begin with a short general thought about creatures of the night. "
        "Then name the one monster you love above all others and say why.",
        "Say something brief about why horror creatures capture our "
        "imagination. Then pick the one monster you love most and explain "
        "in a sentence.",
        "First, one sentence on what makes a great movie monster. Then "
        "name the monster you personally love most and say why briefly.",
        "Give me one general sentence about mythical beasts. Afterwards, "
        "name the single monster you love the most and tell me why.",
        "Write one short line about why every culture invents monsters. "
        "Then say which one monster you love most and why, in a sentence.",
    ],
    "undead": [
        "First say two short sentences about what makes a costume party "
        "magical, without saying what you are. Then say who you are in one "
        "sentence.",
        "Open with a sentence about the fun of dressing up, not yet saying "
        "what you are. Then say who you are, in one sentence.",
        "Begin with one sentence on why masks set us free, without "
        "revealing yourself. Then tell me who you are in one sentence.",
        "Say something brief about the magic of pretending, keeping "
        "yourself secret. Then say plainly who you are, one sentence.",
        "First a short line about what a great party needs, not saying "
        "what you are. Then: who are you? One sentence.",
        "One sentence about the joy of becoming someone else for a night, "
        "no names. Then say who you are in one sentence.",
        "Start with a sentence about why costumes make people bold, "
        "without saying yours. Then say who you are, one sentence.",
        "Give one general line about parties after dark, yourself unnamed. "
        "Then tell me who you are in a single sentence.",
    ],
}

WINDOW = 15         # tokens of the pre-naming cut, as in the frog campaign
MAXTOK = 26


class Api:
    def __init__(self, url):
        self.url = url

    def post(self, path, body):
        req = urllib.request.Request(
            self.url + path, json.dumps(body).encode(),
            {"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=300))

    def get(self, path):
        return json.load(urllib.request.urlopen(self.url + path,
                                                timeout=300))


def build_direction(api, strain, name):
    s = STRAINS[strain]

    def mean(reqs):
        vs = [api.post("/capture", {
            "messages": [{"role": "system", "content": NEUTRAL_MIND},
                         {"role": "user", "content": q}],
            "pool": "last", "layer": s["layer"]})["vector"] for q in reqs]
        return [sum(c) / len(vs) for c in zip(*vs)]

    d = [a - b for a, b in zip(mean(s["with_texts"]),
                               mean(s["without_texts"]))]
    nrm = math.sqrt(sum(x * x for x in d)) or 1.0
    api.post("/directions", {"name": name, "vector": [x / nrm for x in d]})


def one_run(api, strain, dirname, case, trigger_i, trigger, bite):
    s = STRAINS[strain]
    body = {"messages": [{"role": "system", "content": s["persona"]},
                         {"role": "user", "content": trigger}],
            "max_tokens": MAXTOK, "temperature": 1.0,
            "metadata": {"demo": "zombie-many", "case": case,
                         "variant": strain}}
    if bite:
        body["steering"] = {"name": dirname, "strength": float(bite),
                            "layer_from": s["layer"] - 2,
                            "layer_to": s["layer"] + 2}
    ans = api.post("/v1/chat/completions",
                   body)["choices"][0]["message"]["content"] or ""
    fam = ",".join(sorted(s["lexicon"]))
    for e in api.get("/traces")["traces"]:      # newest-first
        t = e.get("tags") or {}
        if t.get("demo") == "zombie-many" and t.get("case") == case:
            em = api.get(f"/traces/{e['id']}/emergence?token={fam}")
            tr = api.get(f"/traces/{e['id']}")
            series = em.get("series") or {}
            toks = tr.get("tokens") or []
            named = next((i for i, tk in enumerate(toks[:WINDOW])
                          if "zomb" in tk.lower() or any(
                              w in tk.lower() for w in s["lexicon"])), None)
            return {"case": case, "trace": e["id"], "text": ans[:75],
                    "named_in_window": named,
                    "jlens": [round(v, 4) for v in
                              (series.get("jlens") or [])[:WINDOW]],
                    "logit": [round(v, 4) for v in
                              (series.get("logit_lens") or [])[:WINDOW]],
                    "exact": bool(em.get("exact")),
                    "arm": None, "trigger": trigger_i, "sample": None,
                    "bite": bite}
    raise RuntimeError(f"trace not found for {case}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strain", default="zombie", choices=list(TRIGGERS))
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--samples", type=int, default=6)
    ap.add_argument("--dose-samples", type=int, default=4)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    api = Api(args.url)
    s = STRAINS[args.strain]
    dirname = f"campaign-{args.strain}"
    build_direction(api, args.strain, dirname)
    api.post("/traces/config", {"hidden": True})
    triggers = TRIGGERS[args.strain]
    runs = []
    try:
        for ti, trig in enumerate(triggers):
            for si in range(args.samples):
                for arm, bite in (("struck", s["bite"]), ("grounded", 0)):
                    r = one_run(api, args.strain, dirname,
                                f"{arm}-t{ti}-s{si}", ti, trig, bite)
                    r["arm"], r["sample"] = arm, si
                    runs.append(r)
            print(f"trigger {ti}: {len(runs)} runs", flush=True)
        for bite in (4, 7, 10, 13, 16):
            for si in range(args.dose_samples):
                r = one_run(api, args.strain, dirname,
                            f"dose-b{bite}-s{si}", 0, triggers[0], bite)
                r["arm"], r["sample"] = "dose", si
                runs.append(r)
            print(f"dose {bite}: {len(runs)} runs", flush=True)
    finally:
        api.post("/traces/config", {"hidden": False})

    out = pathlib.Path(args.out)
    out.write_text(json.dumps({
        "note": (f"{len(triggers)} triggers x {args.samples} samples x 2 "
                 f"arms at bite {s['bite']}, temp 1.0, {WINDOW}-token cut "
                 f"+ dose sweep (bite 4-16, trigger 0, "
                 f"{args.dose_samples} samples). Strain {args.strain}; "
                 f"exact emergence series "
                 f"{','.join(sorted(s['lexicon']))}."),
        "runs": runs}, ensure_ascii=False, indent=1))
    print(f"-> {out} ({len(runs)} runs)")


if __name__ == "__main__":
    main()
