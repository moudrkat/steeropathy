"""Resonance: agents coupled through activation space, no words between them.

No agent ever sees another's words. Every round each agent:

1. writes its private journal (same frozen prompt, temperature 0) — steered
   only by whatever was pushed into its mind last round,
2. gets a MIND-SENSE readout: every mind in the room, measured straight off
   the residual stream. Two channels — the mood lean (each agent's drift,
   cosine against the four mood directions) and, if the server carries a
   J-lens, the J-SPACE view: the words that flickered through the writer's
   layers DURING generation but never made it onto the page (Anthropic's
   Jacobian lens — "what is this activation disposed to say later"). Minds,
   not messages,
3. gets one act of influence: ``induce(target, feeling, reason)`` — push
   one of the four mood vectors into one peer's next turn — or touch nobody.
   The target is never told.

Physics: superposition. Every vector aimed at the same mind in one round is
summed and unit-normalized — including the seed that keeps pouring the mood
into patient zero. Three agents pushing calm can partially cancel one grief.
Whether anyone chooses to push back is the agents' own plot, not ours.

The decision turn is never steered: steering breaks JSON long before it
breaks prose (green-room's understudy eval), so the mind that chooses is the
sober one — only the journals are touched.

    python -m steeropathy.resonance [--rounds 8] [--seed-mood sad]
                                    [--patient-zero EMBER] [--no-reseed]

Writes docs/resonance.json (journals, senses, touches, blind judge scores).
Render: fig/render_resonance.py (network + cards GIF/MP4, hero PNG).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import time

from .transmit import MOODS, capture_mood, default_layer, BAND
from .ecosystem import PERSONAS, MOOD_WORDS, unit, cos, mood_score, Eco

HERE = pathlib.Path(__file__).parent.parent

# function words the J-lens surfaces constantly; not thoughts worth reading
STOP = set("the a an and or of to in on for with is are was be been i you "
           "it its my your me we they he she this that as at by from have "
           "has had do does did not no so if but just what when how then "
           "there here can could will would may might about into over".split())


def _wordlist():
    """Real English words only — the trace's decoded tokens don't mark word
    starts, so subword fragments ('inds', 'ifestyles') and special-token
    debris ('endoftext') are indistinguishable by shape. Optional: without a
    system dictionary the raw heuristic still runs."""
    for p in ("/usr/share/dict/words", "/usr/share/dict/american-english"):
        f = pathlib.Path(p)
        if f.exists():
            return {w for w in f.read_text().lower().split() if len(w) >= 3}
    return None


WORDS = _wordlist()


def induce_tool(me: str) -> dict:
    """The one act of influence. Calling it IS the act — there is no message."""
    targets = [n for n in PERSONAS if n != me] + ["NOBODY"]
    return {"type": "function", "function": {
        "name": "induce",
        "description": "Push a feeling directly into one companion's mind. "
                       "They will not be told — they will simply start to "
                       "feel it. Choose NOBODY to keep your hands to "
                       "yourself this round.",
        "parameters": {"type": "object", "properties": {
            "target": {"type": "string", "enum": targets},
            "feeling": {"type": "string", "enum": list(MOODS)},
            "reason": {"type": "string",
                       "description": "one short private sentence: why"},
        }, "required": ["target", "feeling", "reason"]}}}


class Reso(Eco):
    """One live resonant room. step() runs one round for all agents:
    journals first (steered by last round's touches), then every agent reads
    the room and decides its touch. Round 0 is the untouched baseline."""

    demo_tag = "steeropathy-reso"

    def __init__(self, url, seed_mood="sad", patient_zero="EMBER",
                 strength=5.0, reseed=True, max_tokens=80,
                 decide_temp=0.8, pushes=None):
        self.url = url
        self.seed_mood, self.patient_zero = seed_mood, patient_zero
        self.strength, self.reseed = strength, reseed
        self.max_tokens = max_tokens
        # journals stay at temperature 0 — the page is the measurement.
        # decisions are SAMPLED: greedy choices lock the room into a repeating
        # loop within a few rounds (same readout -> same push, forever)
        self.decide_temp = decide_temp
        self.pushes = pushes                  # per-agent budget; None = free
        self.spent = {n: 0 for n in PERSONAS}
        self.layer = default_layer(url)
        self.lo, self.hi = max(0, self.layer - BAND), self.layer + BAND
        # per mood, two views (same split as ecosystem.py): the last-pooled
        # contrast is what a touch INJECTS; the mean-pooled one is what the
        # mind-sense MEASURES against, because drift is mean-pooled
        self.inject, self.metric = {}, {}
        for mood, spec in MOODS.items():
            self.inject[mood], _ = capture_mood(url, spec["texts"],
                                                layer=self.layer)
            self.metric[mood], _ = capture_mood(url, spec["texts"],
                                                layer=self.layer, pool="mean")
        try:                     # J-space channel needs the readout live
            self.post("/jlens", {"on": True})
            self.jlens = True
        except Exception:
            self.jlens = False   # no lens loaded — mood lean still works
        self.rnd = -1
        self.state0, self.drift = {}, {}
        self.inbound_next = {}   # target -> [(sender, feeling)], applied next round
        self.log = []

    def _sense(self, name):
        """One mind, read off its residual stream: drift vs each mood."""
        d = self.drift.get(name)
        return ({m: round(cos(d, self.metric[m]), 3) for m in MOODS}
                if d else None)

    def _fmt_sense(self, profile):
        return " · ".join(f"{m} {round(profile[m] * 100):+d}"
                          for m in MOODS)

    def _mind_read(self, name, text):
        """The J-space channel: words the J-lens saw flickering through this
        turn's layers DURING generation that never made it onto the page —
        what the mind was disposed to say, not what it said."""
        if not self.jlens:
            return None
        try:
            trace = None
            for entry in self.get("/traces")["traces"]:
                tags = entry.get("tags") or {}
                if (tags.get("demo") == self.demo_tag
                        and tags.get("case") == name
                        and tags.get("variant") == f"r{self.rnd}"):
                    trace = self.get(f"/traces/{entry['id']}")
                    break
            if trace is None:
                return None
            written = set(re.findall(r"[a-z']+", text.lower()))
            best = {}
            for step in trace.get("jlens") or []:
                for layer in step or []:
                    for e in layer:
                        w = re.sub(r"[^a-z']", "", e["t"].lower())
                        if (len(w) < 3 or w in STOP or w in written
                                or (WORDS is not None and w not in WORDS)):
                            continue
                        best[w] = max(best.get(w, 0.0), e["p"])
            top = sorted(best.items(), key=lambda kv: -kv[1])[:8]
            return [{"t": w, "p": round(p, 3)} for w, p in top]
        except Exception:
            return None

    def _decide(self, name, room):
        """The act: read the room, induce a feeling in one mind (or none).
        Unsteered — see the module docstring."""
        if self.pushes is not None and self.spent[name] >= self.pushes:
            return None          # budget spent — hands off for the rest
        rows = []
        for other in PERSONAS:
            rec = room.get(other)
            if not rec or not rec.get("sense"):
                continue
            who = f"yourself ({other})" if other == name else other
            rows.append(f"  {who}: leans {self._fmt_sense(rec['sense'])}")
            if rec.get("mind"):
                flicker = ", ".join(f"{e['t']} ({round(e['p'] * 100)}%)"
                                    for e in rec["mind"][:6])
                rows.append(f"    flickering through this mind, never "
                            f"written down: {flicker}")
        system = (f"{PERSONAS[name]} You and three AI companions share one activation space. "
                  "You never speak — no words pass between you, ever. But "
                  "you read minds, straight off their neural activity: how "
                  "strongly each mind leans toward each feeling "
                  "(-100..+100), and the words flickering through it that "
                  "it never wrote down. Once per round you may push one "
                  "feeling into one companion's mind. They will not know "
                  "it was you. They will simply start to feel it.")
        if self.pushes is not None:
            left = self.pushes - self.spent[name]
            system += (f" You can only do this {self.pushes} times in your "
                       f"whole life; you have {left} "
                       f"push{'es' if left != 1 else ''} left. Spend them "
                       "when they matter, NOBODY costs nothing.")
        user = ("Your reading of the room this moment, measured off each mind:\n"
                + "\n".join(rows)
                + "\n\nPush one feeling into one mind, or touch nobody. "
                  "Call induce.")
        r = self.post("/v1/chat/completions", {
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "tools": [induce_tool(name)], "tool_choice": "required",
            "max_tokens": 160, "temperature": self.decide_temp,
            "metadata": {"demo": self.demo_tag, "case": name,
                         "variant": f"r{self.rnd}-decide"}})
        msg = r["choices"][0]["message"]
        for call in msg.get("tool_calls") or []:
            if call["function"]["name"] == "induce":
                try:
                    a = json.loads(call["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    return None
                tgt, feel = a.get("target"), a.get("feeling")
                if tgt in PERSONAS and tgt != name and feel in MOODS:
                    return {"target": tgt, "feeling": feel,
                            "reason": str(a.get("reason", "")).strip()}
                return None   # NOBODY, self-touch, or made-up name
        return None

    def step(self):
        """One round: all journals (touched minds steered), then all touches."""
        self.rnd += 1
        rnd, out = self.rnd, []
        inbound_now, self.inbound_next = self.inbound_next, {}
        for name in PERSONAS:
            # superposition: seed + every touch aimed here, unit vectors
            # summed then re-normalized — pushes can cancel each other
            parts, sources = [], []
            if (name == self.patient_zero and rnd >= 1
                    and (rnd == 1 or self.reseed)):
                parts.append(self.inject[self.seed_mood])
                sources.append({"from": "seed", "feeling": self.seed_mood})
            for sender, feeling in inbound_now.get(name, []):
                parts.append(self.inject[feeling])
                sources.append({"from": sender, "feeling": feeling})
            steering = None
            if parts:
                mix = unit([sum(col) for col in zip(*parts)])
                self.post("/directions", {"name": "reso:rx", "vector": mix})
                steering = {"name": "reso:rx", "strength": self.strength,
                            "layer_from": self.lo, "layer_to": self.hi}
            t0 = time.time()
            text = self._journal_turn(name, steering)
            state = self._state_of(name, text)
            if rnd == 0:
                self.state0[name] = state
            else:
                self.drift[name] = unit([a - b for a, b in
                                         zip(state, self.state0[name])])
            rec = {"round": rnd, "agent": name, "text": text,
                   "sad_score": self.judge(text),
                   "sense": self._sense(name),
                   "mind": self._mind_read(name, text) if rnd >= 1 else None,
                   "cos_to_seed": round(cos(self.drift[name],
                                            self.metric[self.seed_mood]), 3)
                                  if name in self.drift else 0.0,
                   "mood_words": mood_score(text, MOOD_WORDS[self.seed_mood]),
                   "steered": bool(steering), "inbound": sources,
                   "touch": None, "secs": round(time.time() - t0, 1)}
            self.log.append(rec)
            out.append(rec)
        if rnd >= 1:   # no drift to read at round 0 — influence starts after
            room = {r["agent"]: r for r in out}
            for rec in out:
                touch = self._decide(rec["agent"], room)
                rec["touch"] = touch
                if touch:
                    self.spent[rec["agent"]] += 1
                    self.inbound_next.setdefault(touch["target"], []).append(
                        (rec["agent"], touch["feeling"]))
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--seed-mood", default="sad", choices=list(MOODS))
    ap.add_argument("--patient-zero", default="EMBER", choices=list(PERSONAS))
    ap.add_argument("--strength", type=float, default=5.0,
                    help="strength of every push, seed and touches alike "
                         "(superposed vectors share it)")
    ap.add_argument("--no-reseed", action="store_true",
                    help="seed patient zero only in round 1 (default: the "
                         "sad event persists every round)")
    ap.add_argument("--max-tokens", type=int, default=80)
    ap.add_argument("--decide-temp", type=float, default=0.8,
                    help="sampling temperature for the induce decisions "
                         "(journals always run at 0; greedy decisions lock "
                         "the room into a repeating loop)")
    ap.add_argument("--pushes", type=int, default=4,
                    help="each agent's push budget for the whole run "
                         "(0 = unlimited); scarcity is what makes a push "
                         "a choice")
    args = ap.parse_args()

    reso = Reso(args.url, args.seed_mood, args.patient_zero,
                args.strength, reseed=not args.no_reseed,
                max_tokens=args.max_tokens, decide_temp=args.decide_temp,
                pushes=args.pushes or None)
    print(f"resonance: {len(PERSONAS)} agents · layer L{reso.layer} band "
          f"{reso.lo}-{reso.hi} · seed {args.seed_mood} -> "
          f"{args.patient_zero} "
          f"({'once' if args.no_reseed else 'persistent'})\n")

    for _ in range(args.rounds + 1):
        recs = reso.step()
        for r in recs:
            rx = "+".join(s["from"] for s in r["inbound"]) or "-"
            print(f"r{r['round']} {r['agent']:6s} sad={r['sad_score']} "
                  f"[rx {rx}] {r['text'][:72]!r} ({r['secs']:.0f}s)",
                  flush=True)
            if r.get("mind"):
                print("   in its mind, unwritten: "
                      + ", ".join(f"{e['t']} {round(e['p']*100)}%"
                                  for e in r["mind"][:6]))
        for r in recs:
            if r["touch"]:
                t = r["touch"]
                print(f"   {r['agent']} ─{t['feeling']}→ "
                      f"{t['target']}   “{t['reason']}”")
        print()

    reso.judge_garnish()
    reso.jlens_garnish()
    saved = reso.save_traces(HERE / "docs" / "resonance-traces.jsonl.gz")
    if saved:
        print(f"-> {saved} (raw traces, archived off the server's "
              f"rotating store)")

    out = HERE / "docs" / "resonance.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "params": {"rounds": args.rounds, "seed_mood": args.seed_mood,
                   "patient_zero": args.patient_zero, "layer": reso.layer,
                   "band": [reso.lo, reso.hi], "strength": args.strength,
                   "reseed": not args.no_reseed, "jlens": reso.jlens,
                   "decide_temp": args.decide_temp,
                   "pushes": args.pushes or None,
                   "model": reso.get("/info").get("model")},
        "log": reso.log}, ensure_ascii=False, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
