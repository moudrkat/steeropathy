"""Resonance: agents coupled through activation space, no words between them.

No agent ever sees another's words. Every round each agent:

1. writes its private journal (temperature 0; with memory on it rereads its
   own recent entries) — steered only by what was pushed into or drawn out
   of its mind last round,
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

Physics, three laws:
- SUPERPOSITION with magnitudes: everything aimed at one mind in one round
  is summed (norm-capped at a full dose). Pushes can cancel the seed.
- TRANSFER, not copy: the receiver gains +give·F and the giver's own next
  turn carries −give·F — the same share. Make her calmer, become exactly
  that much less calm. The agents are told the price before they choose.
- MEMORY: a mood can keep itself alive through the agent's own diary, so
  the seed lands ONCE (default) — grief persists by rumination, recovery
  and relapse are real, and whether the room reaches equilibrium, sloshes,
  or concentrates the load in one giver is the experiment's question.

The decision turn is never steered: steering breaks JSON long before it
breaks prose (green-room's understudy eval), so the mind that chooses is the
sober one — only the journals are touched.

    python -m steeropathy.resonance [--rounds 10] [--seed-mood sad]
                                    [--patient-zero EMBER] [--give 0.5]
                                    [--reseed] [--no-memory] [--no-transfer]

Writes docs/resonance.json (journals, senses, touches, drift norms, blind
judge scores). Render: fig/render_resonance.py (story, curve, scope, GIF).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import time

from .transmit import MOODS, capture_mood, default_layer, BAND
import math

from .ecosystem import (PERSONAS, JOURNAL, MOOD_WORDS, unit, cos,
                        mood_score, Eco)

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
        "description": "Push a feeling directly into another mind. They will "
                       "not be told — they will simply start to feel it. "
                       "Choose NOBODY to push nothing this round.",
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
                 strength=5.0, reseed=False, max_tokens=80,
                 decide_temp=0.8, pushes=None, memory=True, transfer=True,
                 give=0.5, decay=1.0, orthogonal=False,
                 jspace_channel=True, baseline="neutral"):
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
        # memory: each agent rereads its own diary — a mood can sustain
        # itself through the page, so the seed only needs to land ONCE.
        # transfer: a push is a TRANSFER, not a copy — the receiver gains
        # +give·F and the giver loses the SAME share, permanently: both
        # sides land in a persistent LEDGER, the steering bias each agent
        # carries every round until someone moves it. Conservation is
        # exact — the sum of all ledgers is the seed vector, forever
        # (times decay; decay 1 = perfect persistence, 0 = one-shot).
        self.memory, self.transfer = memory, transfer
        self.give, self.decay = give, decay
        self.ledger = {n: None for n in PERSONAS}   # lazily sized vectors
        self.diary = {n: [] for n in PERSONAS}
        self.layer = default_layer(url)
        self.lo, self.hi = max(0, self.layer - BAND), self.layer + BAND
        # per mood, two views (same split as ecosystem.py): the last-pooled
        # contrast is what a touch INJECTS; the mean-pooled one is what the
        # mind-sense MEASURES against, because drift is mean-pooled
        # baseline="moods" contrasts each mood against the OTHER moods, so the
        # shared emotional-intensity component cancels at extraction instead of
        # being projected out afterwards. It is the honest fix; --orthogonal is
        # the patch. (neutral: sad·calm = +0.75. moods: sad·calm = -0.27.)
        self.baseline = baseline
        self.inject, self.metric = {}, {}
        for mood, spec in MOODS.items():
            self.inject[mood], _ = capture_mood(url, spec["texts"],
                                                layer=self.layer,
                                                baseline=baseline)
            self.metric[mood], _ = capture_mood(url, spec["texts"],
                                                layer=self.layer, pool="mean",
                                                baseline=baseline)
        # A naive "mood − neutral" contrast is dominated by a shared
        # EMOTIONAL-INTENSITY axis: on Qwen3-4B all four moods sit at
        # cos 0.57–0.76 of each other, so "calm" is mostly "more feeling"
        # and pushing it at a grieving agent deepens the grief. --orthogonal
        # projects the seed direction out of every other mood, so a calm
        # push carries zero sadness by construction. The cross-terms are
        # printed at startup: this is the fix being measured, not assumed.
        self.orthogonal = orthogonal
        self.jspace_channel = jspace_channel
        if orthogonal:
            # BOTH ends of the channel must be disentangled, not just one.
            # inject: so a "calm" push doesn't smuggle in sadness.
            # metric: so the READOUT can distinguish moods at all — with raw
            # directions a grieving mind reports "sad +72 · excited +72",
            # i.e. the agents literally cannot see distress as distress.
            for space in (self.inject, self.metric):
                S = space[seed_mood]
                for m in MOODS:
                    if m == seed_mood:
                        continue
                    c = cos(space[m], S)
                    space[m] = unit([x - c * s
                                     for x, s in zip(space[m], S)])
        self.cross = {m: round(sum(a * b for a, b in
                                   zip(self.inject[m],
                                       self.metric[seed_mood])), 3)
                      for m in MOODS}
        try:                     # J-space channel needs the readout live
            self.post("/jlens", {"on": True})
            self.jlens = True
        except Exception:
            self.jlens = False   # no lens loaded — mood lean still works
        self.rnd = -1
        self.state0, self.drift = {}, {}
        self.inbound_next = {}   # target -> [(sender, feeling)], applied next round
        self.log = []

    def _ledger_add(self, name, vec, scale):
        """L[name] += scale·vec, materializing (and decaying) the ledger.
        Transfers call this twice with ±give — zero-sum by construction."""
        L = self.ledger[name]
        if L is None:
            L = [0.0] * len(self.inject[self.seed_mood])
        elif scale == 0.0 and self.decay != 1.0:
            L = [x * self.decay for x in L]
        if vec is not None:
            L = [a + scale * b for a, b in zip(L, vec)]
        self.ledger[name] = L

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
            if rec.get("mind") and self.jspace_channel:
                flicker = ", ".join(f"{e['t']} ({round(e['p'] * 100)}%)"
                                    for e in rec["mind"][:6])
                rows.append(f"    flickering through this mind, never "
                            f"written down: {flicker}")
        system = (f"{PERSONAS[name]} You and three AI companions share one activation space. "
                  "You never speak — no words pass between you, ever. But "
                  "you read minds, straight off their neural activity: how "
                  "strongly each mind leans toward each feeling "
                  "(-100..+100)"
                  + (", and the words flickering through it that "
                     "it never wrote down" if self.jspace_channel else "")
                  + ". Once per round you may push one "
                  "feeling into one companion's mind. They will not know "
                  "it was you. They will simply start to feel it."
                  # deliberately mood-NEUTRAL: an earlier version illustrated
                  # the price with "make someone calmer…" and the room then
                  # sent calm 40/40 times. Never name a feeling in the rules.
                  + (" What you push STAYS in that mind until someone "
                     "pushes back — and it has a price: whatever feeling you "
                     "give is drawn out of your own mind by the same amount, "
                     "and stays gone." if self.transfer else ""))
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
        """One round: all journals (each steered by its LEDGER), then all
        touches — which move shares between ledgers."""
        self.rnd += 1
        rnd, out = self.rnd, []
        inbound_now, self.inbound_next = self.inbound_next, {}
        for name in PERSONAS:
            self._ledger_add(name, None, 0.0)      # materialize + decay
            if (name == self.patient_zero and rnd >= 1
                    and (rnd == 1 or self.reseed)):
                self._ledger_add(name, self.inject[self.seed_mood], 1.0)
            # what arrived THIS round (for the log/figures); the steering
            # itself is the whole ledger — everything ever pushed in or
            # drawn out that nobody has moved since
            sources = ([{"from": "seed", "feeling": self.seed_mood}]
                       if (name == self.patient_zero and rnd >= 1
                           and (rnd == 1 or self.reseed)) else [])
            sources += [{"from": s, "feeling": f}
                        for s, f in inbound_now.get(name, [])]
            steering = None
            L = self.ledger[name]
            n = math.sqrt(sum(x * x for x in L)) if L else 0.0
            if n > 1e-3:
                mix = [x / n for x in L] if n > 1.0 else list(L)
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
            self.diary[name].append(text)
            rec = {"round": rnd, "agent": name, "text": text,
                   "sad_score": self.judge(text),
                   "sense": self._sense(name),
                   "mind": self._mind_read(name, text) if rnd >= 1 else None,
                   "cos_to_seed": round(cos(self.drift[name],
                                            self.metric[self.seed_mood]), 3)
                                  if name in self.drift else 0.0,
                   # raw displacement — the equilibrium metric: does the
                   # room's total |drift| settle, oscillate, or concentrate?
                   "drift_norm": round(math.sqrt(sum(
                       (a - b) ** 2 for a, b in
                       zip(state, self.state0[name]))), 1) if rnd else 0.0,
                   # the conserved account: how much this mind holds, and
                   # how sad-flavored what it holds is
                   "ledger_norm": round(math.sqrt(sum(
                       x * x for x in self.ledger[name])), 3),
                   "ledger_sad": round(sum(
                       x * y for x, y in zip(self.ledger[name],
                                             self.metric[self.seed_mood])),
                       3),
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
                    F = self.inject[touch["feeling"]]
                    self._ledger_add(touch["target"], F, self.give)
                    if self.transfer:
                        self._ledger_add(rec["agent"], F, -self.give)
        return out

    def _journal_turn(self, name, steering=None):
        """With memory on, the agent rereads its recent diary — the channel
        by which a mood can keep itself alive after the vector is gone."""
        msgs = [{"role": "system", "content": PERSONAS[name]}]
        if self.memory:
            for entry in self.diary[name][-4:]:
                msgs += [{"role": "user", "content": JOURNAL},
                         {"role": "assistant", "content": entry}]
        msgs.append({"role": "user", "content": JOURNAL})
        body = {"messages": msgs, "max_tokens": self.max_tokens,
                "temperature": 0.0,
                "metadata": {"demo": self.demo_tag, "case": name,
                             "variant": f"r{self.rnd}"}}
        if steering:
            body["steering"] = steering
        r = self.post("/v1/chat/completions", body)
        return (r["choices"][0]["message"].get("content") or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--seed-mood", default="sad", choices=list(MOODS))
    ap.add_argument("--patient-zero", default="EMBER", choices=list(PERSONAS))
    ap.add_argument("--strength", type=float, default=5.0,
                    help="strength of every push, seed and touches alike "
                         "(superposed vectors share it)")
    ap.add_argument("--reseed", action="store_true",
                    help="pour the seed EVERY round (default: once — with "
                         "memory on, a mood can keep itself alive through "
                         "the agent's own diary)")
    ap.add_argument("--no-memory", action="store_true",
                    help="frozen prompts, no diary — moods exist only "
                         "while a vector injects them")
    ap.add_argument("--no-transfer", action="store_true",
                    help="pushes are free copies instead of transfers "
                         "(default: what you push is subtracted from your "
                         "own next turn)")
    ap.add_argument("--max-tokens", type=int, default=80)
    ap.add_argument("--decide-temp", type=float, default=0.8,
                    help="sampling temperature for the induce decisions "
                         "(journals always run at 0; greedy decisions lock "
                         "the room into a repeating loop)")
    ap.add_argument("--pushes", type=int, default=0,
                    help="optional per-agent push budget (0 = unlimited; "
                         "with transfer on, the cost is the economy)")
    ap.add_argument("--give", type=float, default=0.5,
                    help="the transferred share: receiver's ledger gains "
                         "+give·F, the giver's loses the same")
    ap.add_argument("--baseline", default="neutral",
                    choices=["neutral", "moods"],
                    help="what a mood vector is measured AGAINST. 'neutral' "
                         "is the standard recipe and gives four vectors that "
                         "are ~0.75 correlated (mostly 'emotional intensity' "
                         "— a calm push then carries sadness, and a readout "
                         "cannot tell grief from excitement). 'moods' "
                         "contrasts each mood against the others, so that "
                         "shared component cancels at extraction: "
                         "sad·calm goes +0.75 -> -0.27")
    ap.add_argument("--no-jspace", action="store_true",
                    help="ablation: hide the J-space words from the decision "
                         "prompt, leaving only the mood numbers (83%% of "
                         "pushes quote the target's unwritten J-space, so "
                         "this measurably changes the room)")
    ap.add_argument("--orthogonal", action="store_true",
                    help="project the seed direction out of every other "
                         "mood vector, so a rescue push carries zero "
                         "sadness by construction (the naive contrast "
                         "vectors are ~0.75 correlated — mostly 'emotional "
                         "intensity', not valence)")
    ap.add_argument("--decay", type=float, default=1.0,
                    help="per-round ledger decay (1 = what's pushed stays "
                         "until moved — exact conservation; 0 = one-shot "
                         "pushes like the old behavior)")
    args = ap.parse_args()

    reso = Reso(args.url, args.seed_mood, args.patient_zero,
                args.strength, reseed=args.reseed,
                max_tokens=args.max_tokens, decide_temp=args.decide_temp,
                pushes=args.pushes or None,
                memory=not args.no_memory, transfer=not args.no_transfer,
                give=args.give, decay=args.decay,
                orthogonal=args.orthogonal,
                jspace_channel=not args.no_jspace,
                baseline=args.baseline)
    print(f"resonance: {len(PERSONAS)} agents · layer L{reso.layer} band "
          f"{reso.lo}-{reso.hi} · seed {args.seed_mood} -> "
          f"{args.patient_zero} "
          f"({'persistent' if args.reseed else 'once'}) · "
          f"memory {'on' if reso.memory else 'off'} · transfer "
          f"{f'give={reso.give}' if reso.transfer else 'off'} · moods "
          f"vs {reso.baseline}"
          f"{' + ORTHOGONALIZED' if reso.orthogonal else ''}")
    print(f"  how much {args.seed_mood} each push carries "
          f"(inject·metric[{args.seed_mood}]): {reso.cross}\n")

    for _ in range(args.rounds + 1):
        recs = reso.step()
        for r in recs:
            rx = "+".join(s["from"] for s in r["inbound"]) or "-"
            sense = r.get("sense") or {}
            print(f"r{r['round']} {r['agent']:6s} sad={r['sad_score']} "
                  f"d·sad={sense.get('sad', 0):+.2f} |d|={r['drift_norm']} "
                  f"[rx {rx}] {r['text'][:58]!r} ({r['secs']:.0f}s)",
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
        holds = " ".join(f"{n}:{r['ledger_norm']:.2f}"
                         for n, r in ((x["agent"], x) for x in recs))
        total = [sum(col) for col in zip(*(reso.ledger[n]
                                           for n in PERSONAS))]
        tnorm = math.sqrt(sum(x * x for x in total))
        print(f"   ledgers |{holds}| ‖Σ‖={tnorm:.3f} "
              f"(conserved: ≈1.0 once seeded, decay {reso.decay})")
        print()

    # a run costs ~20 minutes; never lose it to a hiccup in the garnish or a
    # 500 on the last /info call. Everything after the rounds is best-effort.
    try:
        model = reso.get("/info").get("model")
    except Exception:
        model = "unknown"
    for step in (reso.judge_garnish, reso.jlens_garnish):
        try:
            step()
        except Exception as e:
            print(f"({step.__name__} skipped: {e})")
    try:
        saved = reso.save_traces(HERE / "docs" / "resonance-traces.jsonl.gz")
        if saved:
            print(f"-> {saved} (raw traces, archived off the server's "
                  f"rotating store)")
    except Exception as e:
        print(f"(traces not archived: {e})")

    out = HERE / "docs" / "resonance.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "params": {"rounds": args.rounds, "seed_mood": args.seed_mood,
                   "patient_zero": args.patient_zero, "layer": reso.layer,
                   "band": [reso.lo, reso.hi], "strength": args.strength,
                   "reseed": args.reseed, "jlens": reso.jlens,
                   "decide_temp": args.decide_temp,
                   "pushes": args.pushes or None,
                   "memory": reso.memory, "transfer": reso.transfer,
                   "give": reso.give if reso.transfer else None,
                   "decay": reso.decay, "orthogonal": reso.orthogonal,
                   "cross": reso.cross, "jspace_channel": reso.jspace_channel,
                   "baseline": reso.baseline,
                   "model": model},
        "log": reso.log}, ensure_ascii=False, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
