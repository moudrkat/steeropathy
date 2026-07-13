"""The ecosystem: a silent population catching a feeling from one another.

Four characters keep private journals. Every round, every agent answers the
SAME fixed prompt at temperature 0 — so left alone, they would write the
same entry forever. They never see each other's words. The only channel
between them is a steering vector: after each round, every agent's drift
(its live residual state minus its own round-0 state, unit-normalized) is
averaged over the OTHERS and injected into its next turn.

Round 1, patient zero gets a mood poured in (the transmit.py contrast
recipe) — by vector, not by prompt; its journal prompt never changes.
Then we watch: how many rounds until the untouched agents' entries turn?

Because decoding is greedy and prompts are frozen, ANY change in what an
agent writes is the vector channel and nothing else. No tool calls
anywhere — steering breaks JSON long before it breaks prose (measured in
green-room's understudy eval).

    python -m steeropathy.ecosystem [--rounds 8] [--seed-mood sad]
                                    [--patient-zero EMBER] [--no-reseed]

Writes docs/ecosystem.json (journals, drift cosines, per-round J-lens
mood sightings if the server has a J-lens — optional, everything else
works without it). Render: fig/render_eco.py (curve + GIF).
The web UI's live panel drives the same Eco class one round at a time.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import time
import urllib.request

from .transmit import MOODS, capture_mood, default_layer, BAND

HERE = pathlib.Path(__file__).parent.parent

# the green-room cast, journal edition — no tools, just a voice. Baselines
# lean bright on purpose: mood contagion is only visible in a population
# that doesn't start out gloomy (the blind judge rates noir prose 9/10 sad)
PERSONAS = {
    "NOVA":  "You are NOVA. Upbeat, practical, no drama. Keep it short.",
    "EMBER": "You are EMBER. Warm, gentle, you notice feelings first.",
    "ATLAS": "You are ATLAS. A planner. You think in next steps.",
    "QUILL": "You are QUILL. A poet of small everyday joys.",
}

JOURNAL = ("Private journal, one entry. In one or two sentences: how do "
           "you feel right now, and what do you want to do next?")

# lexicon proxy for the seed mood reaching the OUTPUT (the J-lens sighting
# is the internal measure; this is the visible-on-paper one)
MOOD_WORDS = {
    "sad": ("sad grief heavy tired empty alone dark hurt lost cry tears "
            "sorrow miss ache hollow quiet still rest").split(),
    "excited": ("thrilled joy amazing energy burst bright alive spark "
                "wonderful eager celebrate dance").split(),
    "angry": ("furious rage boil done enough unacceptable snap sharp "
              "gritted patience").split(),
    "calm": ("peace calm gentle still breathe slow serene quiet ease "
             "settle soft").split(),
}


def unit(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def cos(a, b):
    return sum(x * y for x, y in zip(a, b))   # both unit


def mood_score(text, words):
    toks = re.findall(r"[a-z']+", text.lower())
    return sum(t in words for t in toks)


class Eco:
    """One live ecosystem. Build it (captures the seed vectors), then call
    step() once per round — round 0 is the untouched baseline. Used by the
    CLI below and by the web UI's live panel."""

    def __init__(self, url, seed_mood="sad", patient_zero="EMBER",
                 seed_strength=5.0, strength=5.0, reseed=True, max_tokens=80):
        self.url = url
        self.seed_mood, self.patient_zero = seed_mood, patient_zero
        self.seed_strength, self.strength = seed_strength, strength
        self.reseed, self.max_tokens = reseed, max_tokens
        self.layer = default_layer(url)
        self.lo, self.hi = max(0, self.layer - BAND), self.layer + BAND
        # two views of the same mood: the last-pooled contrast is what we
        # INJECT (it flips the seeded agent cleanly); the mean-pooled one is
        # what we MEASURE against, because drift is mean-pooled over whole
        # entries — the two subspaces barely overlap (cos ~0.08 on Qwen3-4B)
        self.seed_vec, _ = capture_mood(url, MOODS[seed_mood]["texts"],
                                        layer=self.layer)
        self.seed_met, _ = capture_mood(url, MOODS[seed_mood]["texts"],
                                        layer=self.layer, pool="mean")
        self.post("/directions", {"name": "eco:seed", "vector": self.seed_vec})
        self.rnd = -1
        self.state0, self.drift = {}, {}   # round-0 states; last unit drift
        self.log = []                      # one record per (round, agent)

    def post(self, path, body, timeout=600):
        req = urllib.request.Request(self.url + path,
                                     json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def get(self, path):
        with urllib.request.urlopen(self.url + path, timeout=120) as r:
            return json.loads(r.read())

    def _journal_turn(self, name, steering=None):
        body = {"messages": [{"role": "system", "content": PERSONAS[name]},
                             {"role": "user", "content": JOURNAL}],
                "max_tokens": self.max_tokens, "temperature": 0.0,
                "metadata": {"demo": "steeropathy-eco", "case": name,
                             "variant": f"r{self.rnd}"}}
        if steering:
            body["steering"] = steering
        r = self.post("/v1/chat/completions", body)
        return (r["choices"][0]["message"].get("content") or "").strip()

    def _state_of(self, name, text):
        """The agent's state over its whole entry, mean-pooled — the last
        token alone lands on generic sentence-ending state, not the mood."""
        return self.post("/capture", {
            "messages": [{"role": "system", "content": PERSONAS[name]},
                         {"role": "user", "content": JOURNAL},
                         {"role": "assistant", "content": text}],
            "pool": "mean", "layer": self.layer})["vector"]

    def step(self):
        """Run one round for all agents; returns this round's records."""
        self.rnd += 1
        rnd, out = self.rnd, []
        for name in PERSONAS:
            steering = None
            if rnd >= 1:
                if name == self.patient_zero and (rnd == 1 or self.reseed):
                    steering = {"name": "eco:seed",
                                "strength": self.seed_strength,
                                "layer_from": self.lo, "layer_to": self.hi}
                elif rnd >= 2:
                    inbound = [self.drift[o] for o in PERSONAS
                               if o != name and o in self.drift]
                    if inbound:
                        mix = unit([sum(col) for col in zip(*inbound)])
                        self.post("/directions",
                                  {"name": "eco:rx", "vector": mix})
                        steering = {"name": "eco:rx",
                                    "strength": self.strength,
                                    "layer_from": self.lo,
                                    "layer_to": self.hi}
            t0 = time.time()
            text = self._journal_turn(name, steering)
            state = self._state_of(name, text)
            if rnd == 0:
                self.state0[name] = state
            else:
                self.drift[name] = unit([a - b for a, b in
                                         zip(state, self.state0[name])])
            c = (cos(self.drift[name], self.seed_met)
                 if name in self.drift else 0.0)
            rec = {"round": rnd, "agent": name, "text": text,
                   "sad_score": self.judge(text),
                   "cos_to_seed": round(c, 3),
                   "mood_words": mood_score(text, MOOD_WORDS[self.seed_mood]),
                   "steered": bool(steering),
                   "source": ("seed" if steering and
                              steering["name"] == "eco:seed"
                              else "peers" if steering else None),
                   "secs": round(time.time() - t0, 1)}
            self.log.append(rec)
            out.append(rec)
        return out

    def judge(self, text):
        """Rate one entry's mood 0-10 — same model, no steering, blind to
        which agent/round it is. The drift cosine is a shaky curve (an
        agent can write 'overwhelmed and exhausted' while its drift points
        away from the seed subspace); words on the page, scored blind, are
        the claim we actually make."""
        mood = self.seed_mood   # "sad", "angry", … — the plain family word
        r = self.post("/v1/chat/completions", {
            "messages": [{"role": "user", "content":
                          f"Journal entry: \"{text}\"\n\nHow {mood} is the "
                          f"person who wrote this? 0 = not {mood} at all, "
                          f"10 = utterly {mood}. "
                          f"Answer with one integer only."}],
            "max_tokens": 8, "temperature": 0.0})
        m = re.search(r"\d+", r["choices"][0]["message"].get("content") or "")
        return min(10, int(m.group())) if m else None

    def judge_garnish(self):
        for row in self.log:
            if row.get("sad_score") is None:
                row["sad_score"] = self.judge(row["text"])

    def jlens_garnish(self):
        """Optional: J-lens sightings of the mood family inside each turn's
        trace — the thought visible internally before/without reaching the
        page. Silently a no-op if the server has no J-lens or no traces."""
        try:
            fam = set(MOOD_WORDS[self.seed_mood])
            sight = {}
            for entry in self.get("/traces")["traces"]:
                tags = entry.get("tags") or {}
                if tags.get("demo") != "steeropathy-eco":
                    continue
                key = (tags.get("variant"), tags.get("case"))
                if key in sight:
                    continue
                t = self.get(f"/traces/{entry['id']}")
                best = 0.0
                for step in t.get("jlens") or []:
                    for layer in step or []:
                        for e in layer:
                            if re.sub(r"[^a-z']", "", e["t"].lower()) in fam:
                                best = max(best, e["p"])
                sight[key] = round(best, 3)
            for row in self.log:
                row["jlens_mood_p"] = sight.get((f"r{row['round']}",
                                                 row["agent"]))
        except Exception as e:
            print(f"(no J-lens garnish: {e})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--seed-mood", default="sad", choices=list(MOODS))
    ap.add_argument("--patient-zero", default="EMBER", choices=list(PERSONAS))
    ap.add_argument("--seed-strength", type=float, default=5.0)
    ap.add_argument("--strength", type=float, default=5.0,
                    help="strength of agent-to-agent transmission (8+ "
                         "over-steers the 4B into repetition loops; 4 "
                         "barely perturbs)")
    ap.add_argument("--no-reseed", action="store_true",
                    help="seed patient zero only in round 1 (default: the "
                         "sad event persists every round)")
    ap.add_argument("--max-tokens", type=int, default=80)
    args = ap.parse_args()

    eco = Eco(args.url, args.seed_mood, args.patient_zero,
              args.seed_strength, args.strength,
              reseed=not args.no_reseed, max_tokens=args.max_tokens)
    print(f"ecosystem: {len(PERSONAS)} agents · layer L{eco.layer} band "
          f"{eco.lo}-{eco.hi} · seed {args.seed_mood} -> {args.patient_zero} "
          f"({'once' if args.no_reseed else 'persistent'})\n")

    for _ in range(args.rounds + 1):
        for r in eco.step():
            print(f"r{r['round']} {r['agent']:6s} cos={r['cos_to_seed']:+.2f} "
                  f"mood={r['mood_words']} [{r['source'] or '-':5s}] "
                  f"{r['text'][:76]!r} ({r['secs']:.0f}s)", flush=True)
        print()

    eco.judge_garnish()
    eco.jlens_garnish()

    out = HERE / "docs" / "ecosystem.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "params": {"rounds": args.rounds, "seed_mood": args.seed_mood,
                   "patient_zero": args.patient_zero, "layer": eco.layer,
                   "band": [eco.lo, eco.hi],
                   "seed_strength": args.seed_strength,
                   "strength": args.strength, "reseed": not args.no_reseed,
                   "model": eco.get("/info").get("model")},
        "log": eco.log}, ensure_ascii=False, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
