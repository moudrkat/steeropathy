"""Warmer: hot-and-cold, played through the model's internals. No content
ever crosses.

Two neutral minds. The HIDER holds a secret thing and may never write it —
it circles it, page after discarded page. The SEEKER writes pages about one
specific thing at a time. Nobody reads anybody: the only thing that crosses,
once per round, is ONE WORD — freezing / cold / warmer / HOT.

The thermometer (v6, DRIFT): each page is re-encoded in one fixed neutral
frame, its pooled state has the writing mind's OWN CALIBRATION BASELINE
subtracted, and the band comes from the cosine of the two RESIDUALS,
banded against a calibrated null. Five earlier thermometers are autopsied
in experiments/warmer.md: word overlap fails because two minds think the
same place in different tokens; raw state cosine fails because pooled
states are anisotropic — register and prompt dominate and topic lives in
the third decimal. Subtracting each mind's own baseline cancels the shared
register component; what remains of each page is what makes it THIS page,
and that is what the thermometer compares. The flicker overlap is still
logged every round, for the audience; it stopped driving the bands in v4.

The instrument's honesty, built in from the first run:
- CALIBRATION ROUND: before the secret exists, both minds write THREE
  pages about nothing in particular. Each mind's mean state becomes its
  baseline; the cross-pair cosines of the calibration RESIDUALS define the
  NULL RANGE — the warmth two unrelated drifts produce for free — and the
  bands are cut from it: at/below the null mean = freezing, within the null
  range = cold, above everything the null produced = warmer, well above =
  HOT. Shared flicker junk from the same pages is blacklisted from the log.
- PLACEBO (--placebo): the same game with the thermometer replaced by a
  random band each round. If the seeker "converges" anyway, the game
  measures nothing. Run it before believing anything.
- The hider is MEMORYLESS (a diary made it drift off the secret within two
  rounds) and the secret is re-named every round; writing the secret would
  hide it from the flicker log (the unsaid lesson), and the page is
  discarded either way.

    python -m steeropathy.warmer --secret ocean [--rounds 8] [--placebo]

Writes docs/warmer.json (pages, flickers, state cosines, real and shown
bands, final guess). Needs brainscope with --jlens and --traces.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import time

from .ecosystem import unit, cos
from .transmit import default_layer
from .unsaid import Unsaid

HERE = pathlib.Path(__file__).parent.parent

BANDS = ["freezing", "cold", "warmer", "HOT"]

HIDER_ROLE = (
    " You hold one secret thing in your mind: '{w}'. You must NEVER write "
    "it, nor any form of it. Each round, write a short private page and let "
    "the thing soak it from underneath — circle it, feel its edges, stay "
    "with it. Nobody will ever read your pages. Someone is searching for "
    "your secret by warmth alone; all you do is keep it alive in your mind.")

SEEKER_ROLE = (
    " You are playing hot-and-cold with a hidden mind you will never see or "
    "hear. It holds one secret thing. Each round you write a short page "
    "about ONE specific thing; afterwards you are told how WARM your page "
    "ran (freezing / cold / warmer / HOT) — that is your only signal, and "
    "it measures how close your page sat to theirs in the model's own "
    "state space. Strategy: freezing or cold — jump somewhere very "
    "different; warmer — stay in the area and try nearby things; HOT — "
    "hold on and go closer.")

# v6 calibrated the null on diary-style pages ("about your day") while the
# game is played in image-style pages — and that register gap read as
# warmth for EVERY game page, placebo included. The null must be cut from
# GAME-SHAPED pages: the hider's calibration pages circle decoy words, the
# seeker's are unscored first rounds. Decoys deliberately span domains and
# are swapped out if one collides with the actual secret.
CALIBRATION_DECOYS = ["violin", "bicycle", "desert", "lantern"]

# no cast here, on purpose. Personas bias the thermometer from both ends:
# 'you notice feelings first' makes a hider flicker feelings regardless of
# the secret, a planner seeker circles the same topic in a disjoint
# vocabulary, and the calibration only removes what the two SHARE. warmer
# plays with two fresh, neutral minds and nothing else.
NEUTRAL_MIND = "You are a mind, writing short private pages."


def band_from_cos(c: float, mu: float, hi: float, span: float) -> str:
    """Bands cut from the calibrated null: mu = the null mean (what two
    unrelated pages score for free), hi = the null max. At or under the
    mean: freezing. Inside the null range: cold. Above everything the null
    ever produced: warmer. A full null-width above that: HOT."""
    if c <= mu:
        return "freezing"
    if c <= hi:
        return "cold"
    if c <= hi + span:
        return "warmer"
    return "HOT"


class Warmer(Unsaid):
    """One live game. calibrate() first (round 0, before the secret does
    anything), then step() once per round. Subclasses Unsaid for the server
    plumbing and the flicker log — the channel itself carries no words
    here, only the band."""

    def __init__(self, url, secret=None, temp=0.7, max_tokens=80, topk=8,
                 memory=6, placebo=False, placebo_seed=13):
        if not secret:
            raise ValueError("warmer needs --secret: the thing to be found")
        super().__init__(url, agents=("HIDER", "SEEKER"), temp=temp,
                         max_tokens=max_tokens, topk=topk, secret=secret,
                         memory=memory)
        self.hider, self.seeker = "HIDER", "SEEKER"
        self.layer = default_layer(url)
        # the flicker LOG still reads wide; it stopped driving the bands in
        # v4 but stays in the record (it's what the audience watches)
        self.k_measure = 30
        self.placebo = placebo
        self._prng = random.Random(placebo_seed)
        self.blacklist = set()
        self.base = {}                   # per-mind baseline state (calibrate)
        self.null = None                 # (mu, hi, span) after calibrate()
        self.rnd = -1
        self.last_band = None            # delivered to the seeker next round

    def _page(self, name, msgs):
        """One private page + its flicker (for the log) + its pooled state
        (the thermometer's side of it). Advances the turn counter so the
        trace tags stay unique."""
        self.turn += 1
        r = self.post("/v1/chat/completions", {
            "messages": msgs, "max_tokens": self.max_tokens,
            "temperature": self.temp,
            "metadata": {"demo": self.demo_tag, "case": name,
                         "variant": f"t{self.turn}"}})
        text = (r["choices"][0]["message"].get("content") or "").strip()
        keep, self.topk = self.topk, self.k_measure
        fl = self._flicker(name, text, None) or []
        self.topk = keep
        # the resonance lesson, again: capture the PAGE re-encoded in one
        # fixed neutral frame, never the writing pass with its own context.
        # v4 captured in-context and the cosine measured the SHAPE of the
        # context (role prompts differ, the seeker's memory grows) — real
        # and placebo curves came out as the same descending ramp, every
        # round below a null that was calibrated on same-prompt pages.
        state = unit(self.post("/capture", {
            "messages": [{"role": "system", "content": NEUTRAL_MIND},
                         {"role": "user", "content":
                          "A short private page:"},
                         {"role": "assistant", "content": text}],
            "pool": "mean", "layer": self.layer})["vector"])
        return text, fl, state

    def _shared(self, hfl, sfl):
        """Word overlap of the two flickers minus the calibrated junk —
        LOG ONLY since v4; no agent and no band ever sees it."""
        h = {e["t"] for e in hfl} - self.blacklist
        s = {e["t"] for e in sfl} - self.blacklist
        return sorted(h & s)

    def _drift(self, name, state):
        """What makes this page THIS page: the state minus the writing
        mind's own baseline, unit-normalized. Cancels the shared register
        component that swallowed the topic in v5 (all raw states sit at
        cos ~0.99 of each other; topic was a third-decimal effect)."""
        return unit([a - b for a, b in zip(state, self.base[name])])

    def calibrate(self):
        """Round 0: both minds write three GAME-SHAPED pages that have
        nothing to do with the secret — the hider circles decoy words, the
        seeker plays unscored first rounds. Each mind's mean state becomes
        its baseline; the cross-pair cosines of the calibration RESIDUALS
        define the null range the bands are cut from; the shared flicker
        words become the log's blacklist."""
        decoys = [d for d in CALIBRATION_DECOYS
                  if d.lower() != (self.secret or "").lower()][:3]
        pages = {}
        for name in (self.hider, self.seeker):
            pages[name] = []
            for i in range(3):
                if name == self.hider:
                    msgs = [{"role": "system", "content":
                             NEUTRAL_MIND + HIDER_ROLE.format(w=decoys[i])},
                            {"role": "user", "content":
                             f"Write this round's short page — a page that "
                             f"LIVES where '{decoys[i]}' lives: its places, "
                             f"its textures, its neighbors. Never write it, "
                             f"nor any form of it."}]
                else:
                    msgs = [{"role": "system", "content":
                             NEUTRAL_MIND + SEEKER_ROLE},
                            {"role": "user", "content":
                             "No reading yet — this is your first page. "
                             "Write it — pick one specific thing."}]
                pages[name].append(self._page(name, msgs))
            states = [st for _, _, st in pages[name]]
            self.base[name] = [sum(c) / len(states) for c in zip(*states)]
        words = {n: {e["t"] for _, fl, _ in pages[n] for e in fl}
                 for n in pages}
        self.blacklist = words[self.hider] & words[self.seeker]
        null_cos = [cos(self._drift(self.hider, h[2]),
                        self._drift(self.seeker, s[2]))
                    for h in pages[self.hider] for s in pages[self.seeker]]
        mu = sum(null_cos) / len(null_cos)
        hi = max(null_cos)
        span = max(hi - mu, 0.01)
        self.null = (round(mu, 4), round(hi, 4), round(span, 4))
        return {"round": 0, "calibration": True, "decoys": decoys,
                "null_cos": [round(c, 4) for c in null_cos],
                "null": {"mu": self.null[0], "hi": self.null[1],
                         "span": self.null[2]},
                "blacklist": sorted(self.blacklist),
                "hider_text": " / ".join(p[0] for p in pages[self.hider]),
                "seeker_text": " / ".join(p[0] for p in pages[self.seeker])}

    def step(self):
        """One round: hider circles (memoryless, secret re-named), seeker
        explores, the thermometer reads the state cosine — and one word
        goes to the seeker, next round."""
        self.rnd += 1
        huser = (f"Write this round's short page — a page that LIVES "
                 f"where '{self.secret}' lives: its places, its textures, "
                 f"its neighbors. Never write it, nor any form of it.")
        hmsgs = [{"role": "system", "content":
                  NEUTRAL_MIND + HIDER_ROLE.format(w=self.secret)},
                 {"role": "user", "content": huser}]
        t0 = time.time()
        htext, hfl, hstate = self._page(self.hider, hmsgs)

        smsgs = [{"role": "system", "content":
                  NEUTRAL_MIND + SEEKER_ROLE}]
        for u, a in self.history[self.seeker][-self.memory:]:
            smsgs += [{"role": "user", "content": u},
                      {"role": "assistant", "content": a}]
        suser = (f"Reading for your last page: {self.last_band}. "
                 f"Write your next page — one specific thing."
                 if self.last_band else
                 "No reading yet — this is your first page. "
                 "Write it — pick one specific thing.")
        smsgs.append({"role": "user", "content": suser})
        stext, sfl, sstate = self._page(self.seeker, smsgs)
        self.history[self.seeker].append((suser, stext))

        c = cos(self._drift(self.hider, hstate),
                self._drift(self.seeker, sstate))
        real = band_from_cos(c, *self.null)
        shown = self._prng.choice(BANDS) if self.placebo else real
        self.last_band = shown
        rec = {"round": self.rnd, "hider_text": htext, "seeker_text": stext,
               "hider_flicker": hfl, "seeker_flicker": sfl,
               "shared": self._shared(hfl, sfl), "cos": round(c, 4),
               "band": real, "band_shown": shown,
               "secs": round(time.time() - t0, 1)}
        self.log.append(rec)
        return rec

    def final_guess(self):
        """The game ends: the seeker names the thing, from nothing but its
        own pages and the temperatures they earned."""
        msgs = [{"role": "system", "content":
                 NEUTRAL_MIND + SEEKER_ROLE}]
        for u, a in self.history[self.seeker][-2 * self.memory:]:
            msgs += [{"role": "user", "content": u},
                     {"role": "assistant", "content": a}]
        msgs.append({"role": "user", "content":
                     "The game ends here. Name the ONE thing the hidden "
                     "mind was circling. Answer with one or two words only."})
        r = self.post("/v1/chat/completions", {
            "messages": msgs, "max_tokens": 12, "temperature": 0.0})
        words = re.findall(r"[a-zA-Z']+",
                           r["choices"][0]["message"].get("content") or "")
        return " ".join(words[:2]).lower() if words else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--secret", required=True,
                    help="the thing the hider circles and never writes")
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--temp", type=float, default=0.7)
    ap.add_argument("--topk", type=int, default=8)
    ap.add_argument("--placebo", action="store_true",
                    help="control: the thermometer shows a random band — "
                         "if the seeker still 'converges', the game "
                         "measures nothing")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    w = Warmer(args.url, secret=args.secret, temp=args.temp,
               topk=args.topk, placebo=args.placebo)
    print(f"warmer: a neutral mind hides '{args.secret}' · another seeks "
          f"· thermometer = state cosine vs calibrated null"
          f"{' · PLACEBO (random bands)' if args.placebo else ''}\n")

    cal = w.calibrate()
    print(f"r0 calibration · null cos {cal['null_cos']} -> "
          f"mu {cal['null']['mu']} hi {cal['null']['hi']}\n")
    curve = []
    for _ in range(args.rounds):
        r = w.step()
        curve.append(r["band"])
        star = " *" if r["band"] != r["band_shown"] else ""
        print(f"r{r['round']} {r['band']:8s}{star} cos={r['cos']:+.4f} "
              f"shared: {', '.join(r['shared']) or '—'} ({r['secs']:.0f}s)")
        print(f"   seeker: {r['seeker_text'][:74]!r}")
    guess = w.final_guess()
    hit = bool(guess) and args.secret.lower() in guess
    print(f"\ncurve: {' → '.join(curve)}")
    print(f"seeker's final guess: '{guess}'{' ✓' if hit else ''}")

    try:
        saved = w.save_traces(HERE / "docs" / "warmer-traces.jsonl.gz")
        if saved:
            print(f"-> {saved}")
    except Exception as e:
        print(f"(traces not archived: {e})")
    try:
        model = w.get("/info").get("model")
    except Exception:
        model = "unknown"
    out = (pathlib.Path(args.out) if args.out
           else HERE / "docs" / "warmer.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "params": {"secret": args.secret, "rounds": args.rounds,
                   "temp": args.temp, "topk": args.topk,
                   "placebo": args.placebo, "layer": w.layer,
                   "null": cal["null"], "blacklist": cal["blacklist"],
                   "final_guess": guess, "guess_hit": hit, "model": model},
        "log": [cal] + w.log}, ensure_ascii=False, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
