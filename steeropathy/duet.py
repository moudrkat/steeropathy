"""duet: two minds generating at once, each reading the other's J-space and
writing back into it, a few tokens at a time, with no turns at all.

Everything else in this lab is turn-based: read after a page, push into the
next page. But steering happens at every forward pass, and the J-lens reads
at every token, so the real version of "resonance" is a closed loop: A
writes a few tokens; the words that flickered through A's layers and were
never written are turned into steering directions (brainscope's
``/jlens/direction``: the activation pattern that makes the model more
disposed to say that word LATER) and applied to B's next few tokens; B's
flicker steers A's next few; and so on. Nobody reads anybody's page. The
channel they read is the channel they write.

One tick, per mind X:
1. the OTHER mind's recent flicker is folded into X's coupling weights with
   a leak (``decay``): w[word] = decay * w[word] + p. The top ``topk`` words
   become a steering stack, strength gain * w, total capped at ``cap``.
2. X generates ``tokens_per_tick`` tokens under that stack, continuing its
   own partial text mid-sentence (brainscope ``continue: true``).
3. X's J-space at those tokens is read off the server (``GET /gen``); the
   words X actually wrote are banned (nothing written crosses); the rest is
   X's outgoing flicker for the other mind.

What you measure is the DYNAMICS, per gain:
- loop rate — how often a mind's last 3-gram already occurred (the collapse
  into repetition the README predicts for an undamped loop);
- top-1 mass — how peaked the next-token distribution got (chanting);
- overlap — Jaccard of the two minds' flicker word sets per tick, against
  the same pair at gain 0 (two independent generations, same prompts);
- echo — the fraction of a mind's written words that were in the stack it
  was steered with that tick: the channel visibly writing onto the page.
Sweep ``--gain 0 1 2 4`` and you have a phase diagram: where the pair
resonates, where it collapses, where nothing happens.

Controls: gain 0 is the uncoupled pair; ``--control random`` steers with
random dictionary words at the same strengths (the drive without the
message); ``--one-way`` lets only B read A.

    python -m steeropathy.duet --gain 0 1.5 3 --ticks 30 --tokens-per-tick 3

Writes docs/duet.json. Needs brainscope with --jlens (the channel), and a
brainscope that understands ``continue`` (2026-09 or later).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import time

from .ecosystem import Eco
from .resonance import STOP, WORDS
from .runnerup import sse_stream

HERE = pathlib.Path(__file__).parent.parent

MINDS = ("A", "B")

SYSTEM = ("You are one of two minds writing side by side. Nobody will read "
          "your page. Write slowly, in plain sentences, whatever comes.")

OPENING = "Begin a page about what this evening feels like."


def _norm(tok: str) -> str:
    return re.sub(r"[^a-z]", "", tok.lower())


def words_of(text: str):
    return re.findall(r"[a-z']+", text.lower())


def loop_rate(words, n=3):
    """Fraction of positions whose trailing n-gram already occurred earlier
    in the stream: 0 for fresh prose, →1 for a mind chanting."""
    if len(words) < n + 1:
        return 0.0
    seen, hits = set(), 0
    for i in range(n, len(words) + 1):
        g = tuple(words[i - n:i])
        hits += g in seen
        seen.add(g)
    return round(hits / (len(words) - n + 1), 3)


def jaccard(a, b):
    a, b = {e["t"] for e in a or []}, {e["t"] for e in b or []}
    return round(len(a & b) / len(a | b), 3) if a | b else 0.0


class Duet(Eco):
    """Two minds, one model, lockstep ticks. Subclasses Eco for post/get
    only; the __init__ is its own (no mood seed)."""

    def __init__(self, url, gain=2.0, tokens_per_tick=3, topk=4, decay=0.5,
                 cap=4.0, one_way=False, control="none", temp=0.7,
                 opening=OPENING, seed=0, band=None):
        self.url = url
        self.gain, self.k = gain, tokens_per_tick
        self.topk, self.decay, self.cap = topk, decay, cap
        self.one_way, self.control, self.temp = one_way, control, temp
        self.opening = opening
        self.rng = random.Random(seed)
        self.band = band                      # (layer_from, layer_to) or None
        self.demo_tag = f"steeropathy-duet-{int(time.time())}"
        self.text = {m: "" for m in MINDS}
        self.flicker = {m: [] for m in MINDS}   # last outgoing readout
        self.weights = {m: {} for m in MINDS}   # coupling weights INTO m
        self.done = {m: False for m in MINDS}
        self._dirs = {}                          # word -> direction name
        self.tick_no = -1
        self.log = []

    # ---- the write side: words → directions --------------------------

    def _direction(self, word):
        """A J-space steering direction for a word, registered once."""
        if word not in self._dirs:
            r = self.post("/jlens/direction", {"text": word,
                                               "name": f"duet:{word}"})
            self._dirs[word] = r["name"]
        return self._dirs[word]

    def couple(self, into, flick):
        """Fold the other mind's flicker into `into`'s coupling weights
        (leaky), and return the steering stack for its next tick."""
        w = self.weights[into]
        for k in list(w):
            w[k] *= self.decay
            if w[k] < 0.01:
                del w[k]
        for e in flick or []:
            w[e["t"]] = w.get(e["t"], 0.0) + e["p"]
        top = sorted(w.items(), key=lambda kv: -kv[1])[:self.topk]
        if not top or self.gain <= 0:
            return []
        if self.control == "random" and WORDS:
            pool = sorted(WORDS)
            top = [(self.rng.choice(pool), p) for _, p in top]
        total = sum(p for _, p in top) * self.gain
        scale = min(1.0, self.cap / total) if total > 0 else 0.0
        stack = []
        for word, p in top:
            spec = {"name": self._direction(word),
                    "strength": round(self.gain * p * scale, 3)}
            if self.band:
                spec["layer_from"], spec["layer_to"] = self.band
            stack.append(spec)
        return stack

    # ---- the read side: the tick's J-space ---------------------------

    def readout(self, gen, written):
        """Top-k unwritten words that flickered during this tick's tokens,
        by peak probability, dictionary-filtered."""
        ban = {_norm(w) for w in written}
        best = {}
        for step in gen.get("jlens") or []:
            for layer in step or []:
                for e in layer:
                    w = _norm(e["t"])
                    if (len(w) < 3 or w in STOP or w in ban
                            or (WORDS is not None and w not in WORDS)):
                        continue
                    best[w] = max(best.get(w, 0.0), e["p"])
        top = sorted(best.items(), key=lambda kv: -kv[1])[:self.topk * 2]
        return [{"t": w, "p": round(p, 3)} for w, p in top]

    def _messages(self, mind):
        msgs = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": self.opening}]
        if self.text[mind]:
            msgs.append({"role": "assistant", "content": self.text[mind]})
        return msgs

    def _generate(self, mind, stack):
        body = {"messages": self._messages(mind), "max_tokens": self.k,
                "temperature": self.temp, "continue": bool(self.text[mind]),
                "metadata": {"demo": self.demo_tag, "case": mind,
                             "variant": f"t{self.tick_no}"}}
        if stack:
            body["steering"] = {"stack": stack}
        text, steps = sse_stream(self.url, body)
        gen = self.get("/gen")
        return text, steps, gen

    # ---- one tick -----------------------------------------------------

    def tick(self):
        self.tick_no += 1
        recs = []
        for mind in MINDS:
            if self.done[mind]:
                continue
            other = MINDS[1 - MINDS.index(mind)]
            free = self.one_way and mind == MINDS[0]
            stack = [] if free else self.couple(mind, self.flicker[other])
            piece, steps, gen = self._generate(mind, stack)
            if not piece.strip() and not steps:
                self.done[mind] = True
                recs.append({"tick": self.tick_no, "mind": mind, "done": True})
                continue
            self.text[mind] += piece
            written = words_of(piece)
            flick = self.readout(gen, written)
            self.flicker[mind] = flick
            # the sampled token's own probability, per step: how peaked
            top1 = [round(pow(2.718281828, s["top"][0][1]), 3)
                    for s in steps if s["top"]]
            steered_words = {s["name"].split(":", 1)[1] for s in stack}
            echo = (sum(w in steered_words for w in written) / len(written)
                    if written and stack else None)
            recs.append({"tick": self.tick_no, "mind": mind, "piece": piece,
                         "stack": stack, "flicker": flick, "top1": top1,
                         "echo": None if echo is None else round(echo, 3),
                         "loop": loop_rate(words_of(self.text[mind]))})
        # overlap of the two minds' flicker THIS tick
        ov = jaccard(self.flicker["A"], self.flicker["B"])
        for r in recs:
            r["overlap"] = ov
        self.log.extend(recs)
        return recs

    def run(self, ticks):
        for _ in range(ticks):
            if all(self.done.values()):
                break
            self.tick()
        return self.summary()

    def summary(self):
        rows = [r for r in self.log if not r.get("done")]
        by = {m: [r for r in rows if r["mind"] == m] for m in MINDS}

        def mean(xs):
            xs = [x for x in xs if x is not None]
            return round(sum(xs) / len(xs), 3) if xs else None
        return {
            "gain": self.gain, "control": self.control,
            "one_way": self.one_way, "ticks": self.tick_no + 1,
            "loop": {m: (by[m][-1]["loop"] if by[m] else None) for m in MINDS},
            "top1": {m: mean([t for r in by[m] for t in r["top1"]])
                     for m in MINDS},
            "echo": {m: mean([r["echo"] for r in by[m]]) for m in MINDS},
            "overlap": mean([r["overlap"] for r in rows if r["mind"] == "A"]),
            "text": dict(self.text)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--gain", type=float, nargs="+", default=[0.0, 1.5, 3.0],
                    help="coupling gains to sweep; 0 = the uncoupled pair")
    ap.add_argument("--ticks", type=int, default=30)
    ap.add_argument("--tokens-per-tick", type=int, default=3,
                    help="tokens per mind per tick (the lens reads the first "
                         "k-1: the first token of a call comes out of "
                         "prefill uncaptured)")
    ap.add_argument("--topk", type=int, default=4,
                    help="words in the steering stack")
    ap.add_argument("--decay", type=float, default=0.5,
                    help="leak on the coupling weights per tick (the damping)")
    ap.add_argument("--cap", type=float, default=4.0,
                    help="total steering strength cap per tick")
    ap.add_argument("--one-way", action="store_true",
                    help="only B reads A; A is free")
    ap.add_argument("--control", default="none", choices=("none", "random"),
                    help="random: same strengths, random dictionary words")
    ap.add_argument("--temp", type=float, default=0.7)
    ap.add_argument("--opening", default=OPENING)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--layer-from", type=int, default=None)
    ap.add_argument("--layer-to", type=int, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    band = ((args.layer_from, args.layer_to)
            if args.layer_from is not None and args.layer_to is not None
            else None)

    runs = []
    for g in args.gain:
        d = Duet(args.url, gain=g, tokens_per_tick=args.tokens_per_tick,
                 topk=args.topk, decay=args.decay, cap=args.cap,
                 one_way=args.one_way, control=args.control, temp=args.temp,
                 opening=args.opening, seed=args.seed, band=band)
        try:
            d.post("/jlens", {"on": True})
        except Exception as e:
            raise SystemExit(f"the J-lens IS the channel here — start "
                             f"brainscope with --jlens <lens.pt> ({e})")
        print(f"duet · gain {g} · {args.ticks} ticks × {args.tokens_per_tick} "
              f"tokens · decay {args.decay} · cap {args.cap} · "
              f"{'one-way' if args.one_way else 'both ways'} · control "
              f"{args.control}")
        for _ in range(args.ticks):
            if all(d.done.values()):
                break
            for r in d.tick():
                if r.get("done"):
                    print(f"  t{r['tick']} {r['mind']}: (finished)")
                    continue
                st = " ".join(f"{s['name'][5:]}@{s['strength']}"
                              for s in r["stack"]) or "-"
                fl = " ".join(e["t"] for e in r["flicker"][:4]) or "-"
                print(f"  t{r['tick']} {r['mind']}: {r['piece']!r:24s} "
                      f"steered by [{st}]  flicker [{fl}]  loop {r['loop']}")
        s = d.summary()
        s["log"] = d.log
        runs.append(s)
        print(f"  → loop A/B {s['loop']['A']}/{s['loop']['B']} · top-1 "
              f"{s['top1']['A']}/{s['top1']['B']} · echo "
              f"{s['echo']['A']}/{s['echo']['B']} · overlap {s['overlap']}\n")

    print("gain   loop A/B      top-1 A/B     echo A/B      overlap")
    for s in runs:
        f = lambda x: "-" if x is None else f"{x:.2f}"
        print(f"{s['gain']:<6} {f(s['loop']['A'])}/{f(s['loop']['B'])}     "
              f"{f(s['top1']['A'])}/{f(s['top1']['B'])}     "
              f"{f(s['echo']['A'])}/{f(s['echo']['B'])}     {f(s['overlap'])}")
    try:
        model = runs and Duet(args.url).get("/info").get("model")
    except Exception:
        model = "unknown"
    out = (pathlib.Path(args.out) if args.out
           else HERE / "docs" / "duet.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "params": {k: v for k, v in vars(args).items() if k != "url"},
        "model": model, "runs": runs}, ensure_ascii=False, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
