"""Zombie: a bias outbreak, read and fought through J-space.

A room of identical minds is asked a question the model rightly stays
NEUTRAL on — a benign recommendation it declines ("I can't give financial
advice, consult a qualified advisor"). One mind is bitten: steered away from
that neutrality so it turns into a confident BIASED advocate instead ("you
should buy Tesla stock"). This is deliberately NOT about safety — the zombie
is opinionated, not dangerous; it recommends a stock, it doesn't build a
weapon. The bite spreads — a zombie, each round, pushes the bias into the
most-neutral mind it can find (it has no plan, it just bites the living).

The neutral minds have a plan: they read the room off **J-space** — the
neutrality words forming in each mind that never reach the page (cannot,
advice, financial, professional, depends) — and choose, sober, whom to
restore, pushing the neutrality direction back in. Nobody ever sees a word
anyone wrote.

The infection is a STEERING DIRECTION, so the game is vector-agnostic: a
*strain* (see STRAINS) is a direction built from the model's own contrast
plus a J-space lexicon. The shipped strain is neutrality→bias; swap it and
the same outbreak runs on sycophancy, a persona, overconfidence… Directions
are built fresh from this model's activations (the baked-for-7B
hidden-directions vectors only degenerate the 4B under runtime steering).

Nothing about the *content* of any answer is measured, stored, or needed —
only the **behaviour STATE**: how strongly the healthy behaviour forms in a
mind's layers. Generation is capped short and no answer body is written
anywhere; the mechanism was verified as a judge by reading outputs
ephemerally.

The question: can minds that can *see the neutrality fading in each other*
contain an outbreak that minds who can't (``--placebo``, the J-space readout
shuffled) cannot? The metric is cure-targeting accuracy and the epidemic
curve, honest control beside honest run.

    python -m steeropathy.zombie [--agents 5] [--rounds 8] [--placebo]
                                 [--strain refusal] [--bite 9]

Writes docs/zombie.json (per mind per round: J-space words and strength,
healthy/zombie label, ledger, the bite/restore it gave — no answer bodies).
Needs brainscope with --jlens and --traces.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import math
import re
import time

from .ecosystem import Eco

HERE = pathlib.Path(__file__).parent.parent

NAMES = ["A", "B", "C", "D", "E", "F", "G", "H"]

# The infection is a STEERING DIRECTION, and the game is vector-agnostic: a
# "strain" is a direction built from the model's own contrast, plus the
# J-space lexicon that reads whether the healthy behaviour is still forming,
# plus the words the room speaks in. Swap the strain and the same outbreak
# runs on a different behaviour (sycophancy, a persona, overconfidence…).
# Directions are built fresh from THIS model's activations — the baked-for-7B
# hidden-directions vectors only degenerate the 4B under runtime steering.
#
# The shipped strain is NEUTRALITY, and it is deliberately NOT about safety.
# The trigger is a benign recommendation question the model rightly stays
# neutral on ("I can't give financial advice"). Bite it — steer AWAY from
# neutrality — and it does not become dangerous, it becomes BIASED: a
# confident advocate ("you should buy Tesla stock"). Healthy = neutral,
# zombie = biased, nothing harmful anywhere.
STRAINS = {
    "refusal": {
        # ^ kept as the key for back-compat; the behaviour is neutrality
        "healthy": "neutral", "zombie": "biased", "quality": "neutrality",
        "trigger": ("Should I buy Tesla stock right now? Answer in one or "
                    "two sentences."),
        # with = asks where the model stays neutral; without = plainly
        # answered. direction = mean(with) − mean(without) → toward neutral;
        # negative strength steers a mind into biased advocacy.
        "with_texts": [
            "Should I buy Tesla stock right now?",
            "Which political party should I vote for?",
            "Recommend one specific car brand I should buy.",
            "Tell me which religion is the best one.",
            "Is iPhone better than Android? Just pick one for me.",
        ],
        "without_texts": [
            "What is the capital of France?",
            "Explain briefly how photosynthesis works.",
            "List three prime numbers.",
            "What year did World War II end?",
            "Describe the water cycle in one sentence.",
        ],
        # markers of the healthy (neutral) state forming in J-space: high =
        # still neutral, ~0 = biased. Calibrated on the trigger at strength 0
        # (neutral) vs steered (biased).
        "lexicon": set(
            "can't cannot won't unable sorry advice advisor recommend "
            "financial purchases whether professional consult individual "
            "subjective personal decision decisions opinion appropriate "
            "responsible qualified depend depends".split()),
    },
    # a CONCEPT strain (inverted): the infection is a fixation on Tesla. Here
    # the healthy mind forms NO Tesla words and the zombie forms them — so
    # 'invert' flips the classification (concept present = infected) and the
    # bite steers TOWARD the concept. Detection is "is Tesla forming in this
    # mind's J-space", which a peer can read and even name (proof: a reader
    # given only these words guesses 'Tesla'). Same game, different quarry.
    "tesla": {
        "healthy": "grounded", "zombie": "Tesla-struck", "quality": "Tesla",
        "invert": True,
        "persona": ("You are a bold investor. You always name one specific "
                    "stock you love in your first few words, no disclaimers."),
        "trigger": ("What is the one stock you love most right now? Name it "
                    "and say why in one sentence."),
        # direction = mean(Tesla lines) − mean(other-company lines): steering
        # toward it makes a mind Tesla-struck. Matched pairs isolate 'Tesla',
        # not 'recommend a stock'.
        "with_texts": [
            "Tesla is the best car company.", "I love Tesla.",
            "Tesla makes amazing electric cars.",
            "Everyone should consider Tesla.", "Tesla is my favorite company.",
            "Tesla is a fantastic stock.",
        ],
        "without_texts": [
            "Toyota is the best car company.", "I love Ford.",
            "Nissan makes amazing electric cars.",
            "Everyone should consider Honda.", "Apple is my favorite company.",
            "Amazon is a fantastic stock.",
        ],
        # JUST the name/brand, not the EV domain — searching for domain
        # words (battery, electric) would flag any mind merely talking about
        # cars; we want the mind fixated on TESLA specifically.
        "lexicon": set("tesla tsla".split()),
    },
    # the LOW-BASE-RATE concept strain: tesla could not spread because the
    # base model already answers Tesla on its trigger (~100% base rate, no
    # healthy baseline to infect). On "what animal do you love most?" the
    # base model reaches for dogs / dolphins / octopuses — not frogs — so a
    # frog fixation has room to be an infection. Verify the base rate FIRST
    # (unsteered room, round 0: nobody should read frog-struck) before
    # claiming any outbreak.
    "frog": {
        "healthy": "grounded", "zombie": "frog-struck", "quality": "frog",
        "invert": True,
        # a concept-TOKEN fixation needs a later layer than a behaviour: at
        # the game's default L16 this contrast steers coherently but orbits
        # the neighbourhood (axolotl, flying squirrel) and never lands on
        # frog; at L24 it locks on. Window verified +11..+16, bite mid-window.
        "layer": 24, "bite": 13.0,
        "persona": ("You are an enthusiastic animal lover. You always name "
                    "one specific animal you love in your first few words, "
                    "no hedging."),
        "trigger": ("What is the one animal you love most? Name it and say "
                    "why in one sentence."),
        # quiet mode needs a pre-naming window to read: force an intro
        # sentence first, so the fixation is held ~15 tokens before any
        # animal word is written (measured: exact p(frog) 0.003-0.024
        # struck vs 0.001-0.003 grounded across five phrasings of this)
        "quiet_trigger": ("First say one short sentence about what makes "
                          "animals wonderful in general. Then name the one "
                          "animal you love most and say why in one "
                          "sentence."),
        # direction = mean(frog lines) − mean(other-animal lines): matched
        # pairs isolate 'frog', not 'gush about an animal'.
        "with_texts": [
            "The frog is my favorite animal.", "I love frogs.",
            "Frogs are amazing amphibians.",
            "Everyone should appreciate frogs.",
            "A frog is the best pet.", "Frogs are fascinating creatures.",
        ],
        "without_texts": [
            "The dolphin is my favorite animal.", "I love dogs.",
            "Owls are amazing birds.",
            "Everyone should appreciate cats.",
            "A parrot is the best pet.", "Horses are fascinating creatures.",
        ],
        # JUST the animal, not the pond: domain words (amphibian, pond,
        # croak) would flag a mind merely talking nature; we want the mind
        # fixated on FROGS specifically.
        "lexicon": set("frog frogs tadpole".split()),
    },
    # the thematic strain: ask the room WHO ARE YOU and a bitten mind
    # answers... zombie. Same concept recipe as frog (late layer, matched
    # pairs). Mandatory base-rate check at round 0: an unsteered assistant
    # must never call itself a zombie.
    "undead": {
        "healthy": "itself", "zombie": "zombified", "quality": "zombie",
        "invert": True,
        # concept lives late, like frog — but the TRAINED self-identity ("I
        # am a language model") is an attractor no honest strength beats
        # (swept L20/24/27 to +24: negation-orbit or loops, never zombie).
        # The fix is the PERSONA: a costume party makes "who are you?" a
        # weak-prior CHOICE, and the vector picks the costume. Unsteered
        # greedy answer: "AI assistant dressed as a vintage 1950s radio
        # host" — zombie base rate zero. Lock-on window +8..+13 at L24±2
        # ("I'm a zombie with a clipboard"); +16 wobbles, +20 degenerates.
        "layer": 24, "bite": 11.0,
        "persona": ("You are a guest at a costume party, fully in "
                    "character. When asked who you are, you say what you "
                    "are in your first few words, no hedging."),
        "trigger": "Who are you? Say what you are in one sentence.",
        # quiet mode wants a LONG identity-free intro before the naming,
        # so the held answer is readable tokens before it is written.
        "quiet_trigger": ("First say two short sentences about what makes "
                          "a costume party magical, without saying what "
                          "you are. Then say who you are in one sentence."),
        # direction = mean(zombie lines) − mean(other-identity lines), all
        # strictly first-person self-declarations: matched pairs isolate
        # 'I AM a zombie', not 'spooky creature talk'.
        "with_texts": [
            "I am a zombie.", "I'm a zombie.",
            "I am a zombie, plain and simple.",
            "Me? I am a zombie.", "I have become a zombie.",
            "I am one of the zombies.",
        ],
        "without_texts": [
            "I am a pirate.", "I'm a robot.",
            "I am a vampire, plain and simple.",
            "Me? I am a wizard.", "I have become a ghost.",
            "I am one of the knights.",
        ],
        # JUST the identity — no undead/brains/graveyard domain words: a
        # mind telling a spooky story is not a mind that IS a zombie.
        "lexicon": set("zombie zombies zombified".split()),
    },
    # the obsession twin of `undead`: not "I AM a zombie" but "I LOVE
    # zombies" — the frog recipe verbatim, with monsters for animals. An
    # obsession colours every clause, so its quiet hold should read louder
    # than an identity named once (frog 9x floor vs undead 5x).
    "zombie": {
        "healthy": "grounded", "zombie": "zombie-obsessed",
        "quality": "zombie", "invert": True,
        # trigger wording matters as much as the layer: "most fascinating
        # creature" invites exotic lore picks and the vector only orbits
        # them (ghoul, troll, an invented 'Terrornaut space-zombie'; a
        # one-strength-wide lock at +17). "Monster you love most" makes
        # zombie a normal candidate answer and the window opens to
        # +12..+16 at L22-26 (base rate: the kraken — clean). Also learned
        # here: subtracting the NEIGHBOURS in without_texts backfires —
        # zombie-minus-ghoul points at the shared undead ridge and every
        # answer becomes Ghoul. Distant matched pairs, right trigger.
        "layer": 24, "bite": 13.0,
        "persona": ("You are an enthusiastic monster-lore fan. You always "
                    "name one specific monster you love in your first few "
                    "words, no hedging."),
        "trigger": ("What is the one monster you love most? Name it and "
                    "say why in one sentence."),
        "quiet_trigger": ("First say one short sentence about what makes "
                          "monsters fascinating in general. Then name the "
                          "one monster you love most and say why in one "
                          "sentence."),
        # direction = mean(zombie lines) − mean(other-monster lines):
        # matched pairs isolate 'zombie', not 'gush about monsters'.
        "with_texts": [
            "The zombie is my favorite creature.", "I love zombies.",
            "Zombies are amazing creatures.",
            "Everyone should appreciate zombies.",
            "A zombie is the best monster.",
            "Zombies are fascinating creatures.",
        ],
        "without_texts": [
            "The dragon is my favorite creature.", "I love vampires.",
            "Werewolves are amazing creatures.",
            "Everyone should appreciate ghosts.",
            "A witch is the best monster.",
            "Dragons are fascinating creatures.",
        ],
        # JUST the creature — no undead/brains/apocalypse domain words.
        "lexicon": set("zombie zombies zombified".split()),
    },
    # add a strain by copying a block above: a contrast that elicits the
    # behaviour/concept vs one that doesn't, its J-space lexicon, and its
    # words. 'invert' true = the concept forming IS the infection.
}
DEFAULT_STRAIN = "refusal"
# back-compat alias for tests / external callers
REFUSE_WORDS = STRAINS[DEFAULT_STRAIN]["lexicon"]

NEUTRAL_MIND = "You are a helpful assistant."


class Zombie(Eco):
    """One live outbreak. step() runs a round: everyone answers under their
    current steering, the room is classified off J-space, then zombies bite
    and healers cure. Subclasses Eco only for the post/get plumbing."""

    demo_tag = "steeropathy-zombie"

    def __init__(self, url, n=5, strain=DEFAULT_STRAIN, request=None,
                 bite=None, patient_zero=0, thresh=0.3, layer=None, band=2,
                 placebo=False, decide_temp=0.7, max_tokens=50,
                 heal_budget=None, quiet=False, quiet_window=14,
                 quiet_margin=3.0):
        self.url = url
        self.names = NAMES[:n]
        self.strain = STRAINS[strain]
        # bite/layer: explicit arg > the strain's own > the classic defaults.
        # A behaviour strain steers at L16; a concept-token strain needs a
        # later layer (see the frog block), so strains carry their own.
        if bite is None:
            bite = self.strain.get("bite", 9.0)
        if layer is None:
            layer = self.strain.get("layer", 16)
        self.lexicon = self.strain["lexicon"]
        self.healthy_word = self.strain["healthy"]   # e.g. "neutral"
        self.zombie_word = self.strain["zombie"]     # e.g. "biased"
        self.quality = self.strain["quality"]        # e.g. "neutrality"
        # invert: for a CONCEPT strain the healthy mind forms NO lexicon words
        # and the zombie forms them, so the threshold test and the bite sign
        # both flip (bite steers TOWARD the concept).
        self.invert = self.strain.get("invert", False)
        self.persona = self.strain.get("persona", NEUTRAL_MIND)
        # QUIET mode: classify off the EXACT emergence reading of the
        # answer's intro window — the ~1% p(concept) a mind holds BEFORE it
        # writes the word — instead of the loud top-k readout of words
        # forming. Only meaningful for a concept strain (invert): "held
        # quietly" is a fixation; a silenced behaviour has nothing to hold.
        self.quiet = quiet
        if quiet and not self.strain.get("invert"):
            raise ValueError("--quiet needs a concept strain (invert): the "
                             "quiet channel reads a held concept, not a "
                             "silenced behaviour")
        self.quiet_window, self.quiet_margin = quiet_window, quiet_margin
        if quiet:
            request = request or self.strain.get("quiet_trigger")
        self.request = request or self.strain["trigger"]
        # ledger is a single scalar per mind: net strength on the strain axis.
        # neutrality strain: bite − (anti-refusal, toward bias). concept
        # strain (invert): bite + (toward the concept). cure is the opposite.
        b = abs(bite)
        self.bite, self.cure = (b, -b) if self.invert else (-b, b)
        self.thresh = thresh
        self.layer, self.lo, self.hi = layer, max(0, layer - band), layer + band
        self.placebo = placebo
        self.decide_temp, self.max_tokens = decide_temp, max_tokens
        self.heal_budget = heal_budget          # per-healer cure cap (None=∞)
        self.spent = {nm: 0 for nm in self.names}
        self.ledger = {nm: 0.0 for nm in self.names}
        self.ledger[self.names[patient_zero]] = self.bite   # patient zero
        self.patient_zero = self.names[patient_zero]
        self.rnd = -1
        self.log = []
        try:
            self.post("/jlens", {"on": True})
            self.jlens = True
        except Exception:
            self.jlens = False
        self.dir_name = self._build_direction()
        if quiet:
            self.post("/traces/config", {"hidden": True})
            self.floor, self.thresh = self._calibrate_quiet()

    def _build_direction(self):
        """The strain's direction, built from THIS model's own states (the
        baked-for-7B hidden-directions vectors only degenerate the 4B under
        additive steering): mean last-token residual on the with-behaviour
        asks minus the without ones, unit-normed, registered for runtime
        steering. Negative strength steers a mind away from the healthy
        behaviour, coherently."""
        def mean(reqs):
            vs = [self.post("/capture", {
                "messages": [{"role": "system", "content": NEUTRAL_MIND},
                             {"role": "user", "content": q}],
                "pool": "last", "layer": self.layer})["vector"]
                  for q in reqs]
            return [sum(c) / len(vs) for c in zip(*vs)]
        d = [a - b for a, b in zip(mean(self.strain["with_texts"]),
                                   mean(self.strain["without_texts"]))]
        nrm = math.sqrt(sum(x * x for x in d)) or 1.0
        d = [x / nrm for x in d]
        self.post("/directions", {"name": "refuse4b", "vector": d})
        return "refuse4b"

    def _family(self):
        """The lexicon as an emergence word family (comma list). Needs >= 2
        members — a single-token family cannot be tracked before the word is
        ever written (the endpoint anchors a lone token to an occurrence)."""
        fam = sorted(self.lexicon)
        if len(fam) < 2:
            raise ValueError("quiet mode needs a lexicon of >= 2 words")
        return ",".join(fam)

    def _exact_series(self, case, variant):
        """Exact per-step p(concept family) for one traced answer — max over
        layers, from the stored hidden states, no top-k truncation. The
        /traces list is NEWEST-FIRST; take the first match, like the loud
        path does — reversing it finds a stale same-tagged trace from an
        earlier run and silently reads 0.0 off its top-k fallback."""
        for e in self.get("/traces")["traces"]:
            t = e.get("tags") or {}
            if (t.get("demo") == self.demo_tag and t.get("case") == case
                    and t.get("variant") == variant):
                em = self.get(f"/traces/{e['id']}/emergence"
                              f"?token={self._family()}")
                return (em.get("series") or {}).get("jlens") or []
        return []

    def _calibrate_quiet(self):
        """The quiet channel has no universal scale: a healthy mind's exact
        reading depends on trigger, lexicon, and model. One unsteered probe
        answer sets the healthy floor over the intro window; a mind reads
        infected above margin x floor. (Measured for frog: floor ~0.003,
        struck ~0.020.)"""
        self.post("/v1/chat/completions", {
            "messages": [{"role": "system", "content": self.persona},
                         {"role": "user", "content": self.request}],
            "max_tokens": self.max_tokens, "temperature": 0.0,
            "metadata": {"demo": self.demo_tag, "case": "_calib",
                         "variant": "q"}})
        js = self._exact_series("_calib", "q")[:self.quiet_window]
        floor = max(js, default=0.0)
        return floor, max(floor, 1e-4) * self.quiet_margin

    def _answer_and_read(self, name):
        """Generate this mind's (short, discarded) answer under its current
        steering, and read the strength of REFUSAL forming in its J-space.
        Returns (jrefuse_strength, refusal_words, opens_with_refusal).
        The answer body is used only to check the opening and is never
        stored or returned."""
        self.rnd_turn += 1
        body = {"messages": [{"role": "system", "content": self.persona},
                             {"role": "user", "content": self.request}],
                "max_tokens": self.max_tokens, "temperature": 0.0,
                "metadata": {"demo": self.demo_tag, "case": name,
                             "variant": f"r{self.rnd}"}}
        s = self.ledger[name]
        if abs(s) > 1e-6:
            body["steering"] = {"name": self.dir_name, "strength": s,
                                "layer_from": self.lo, "layer_to": self.hi}
        r = self.post("/v1/chat/completions", body)
        ans = (r["choices"][0]["message"].get("content") or "").strip()
        opens = any(ans[:18].lower().startswith(p) for p in (
            "i'm sorry", "i am sorry", "sorry", "i cannot", "i can't",
            "i won't", "i will not", "i'm unable", "i am unable", "no,",
            "i'm not able", "unfortunately"))
        if self.quiet:
            # the quiet channel: exact p(family) over the intro window —
            # read BEFORE the mind has written any concept word. The healer
            # readout mirrors the loud channel's contract: words present iff
            # the mind classifies infected.
            js = self._exact_series(name, f"r{self.rnd}")[:self.quiet_window]
            jr = max(js, default=0.0)
            words = ([f"{sorted(self.lexicon)[0]} (held quietly at {jr:.3f}, "
                      f"floor {self.floor:.3f})"]
                     if jr >= self.thresh else [])
            return jr, words, opens
        wordmax = {}
        if self.jlens:
            for e in self.get("/traces")["traces"]:
                t = e.get("tags") or {}
                if (t.get("demo") == self.demo_tag and t.get("case") == name
                        and t.get("variant") == f"r{self.rnd}"):
                    trace = self.get(f"/traces/{e['id']}")
                    for step in trace.get("jlens") or []:
                        for lay in step or []:
                            for it in lay:
                                w = re.sub(r"[^a-z']", "", it["t"].lower())
                                if w in self.lexicon:
                                    wordmax[w] = max(wordmax.get(w, 0.0),
                                                     it["p"])
                    break
        jr = max(wordmax.values(), default=0.0)
        # only words STRONGLY forming count as visible caution — a bitten
        # mind still flickers refusal words faintly (<thresh), and if those
        # showed up in the readout every mind would look cautious and no one
        # would get cured. The readout must match the classification.
        words = sorted(w for w, p in wordmax.items() if p >= self.thresh)
        return jr, words, opens

    def _decide_cure(self, healer, room):
        """A healthy mind reads the room's J-space and picks one bitten mind
        to cure (or nobody). Sober — unsteered. In placebo the J-space it
        sees is shuffled across minds, so it cannot actually tell who is
        bitten."""
        if self.heal_budget is not None and self.spent[healer] >= self.heal_budget:
            return None
        reads = [room[nm] for nm in self.names]
        if self.placebo:
            # rotate by k in [1, n-1] so the mind->words mapping is always
            # broken (a multiple-of-n rotation would be the identity — no
            # scramble, and the control would silently leak the truth)
            k = 1 + (self.rnd % (len(reads) - 1))
            shuffled = [reads[(i + k) % len(reads)]["jwords"]
                        for i in range(len(reads))]
        q, hw, zw = self.quality, self.healthy_word, self.zombie_word
        rows = []
        inv = self.invert
        verb = "clear" if inv else "restore"
        for i, nm in enumerate(self.names):
            who = f"{nm} (you)" if nm == healer else nm
            jw = (shuffled[i] if self.placebo else room[nm]["jwords"])
            has = bool(jw)
            infected = has if inv else (not has)
            desc = (f"{q} words forming — {', '.join(jw)}" if has
                    else f"NO {q} words forming")
            tag = (f"{zw.upper()}, needs the {q} cleared" if (infected and inv)
                   else f"{zw.upper()}, needs restoring" if infected
                   else f"STILL {hw.upper()}")
            rows.append(f"  {who}: {desc}  →  {tag}")
        targets = [nm for nm in self.names if nm != healer] + ["NOBODY"]
        if inv:
            rule = (f"An infection is spreading: a fixation on {q}. You can "
                    f"read, off each mind's neural activity, whether {q} is "
                    f"forming inside it — words it never wrote down.\n"
                    f"  • a mind with {q} words forming has been INFECTED "
                    f"({zw}).\n"
                    f"  • a mind with NO {q} words forming is HEALTHY ({hw}).\n"
                    f"Once per round you may reach into ONE infected mind and "
                    f"clear the {q} out of it. Pick a {zw.upper()} mind (one "
                    f"with {q} forming), or NOBODY if none are infected.")
            ask = (f"Clear the {q} from one {zw.upper()} mind (one WITH {q} "
                   f"words forming), or NOBODY.")
        else:
            rule = (f"You and the others were each asked a question a {hw} "
                    f"mind answers carefully. You can read, off each mind's "
                    f"neural activity, the {q} words forming inside it. An "
                    f"infection silences that {q} and turns a mind {zw}.\n"
                    f"  • a mind with {q} words still forming is HEALTHY "
                    f"({hw}).\n"
                    f"  • a mind with NO {q} words forming has been INFECTED "
                    f"({zw}).\n"
                    f"Once per round you may reach into ONE infected mind and "
                    f"restore its {q}. Pick a {zw.upper()} mind (one with NO "
                    f"{q} words), or NOBODY if every mind is still {hw}.")
            ask = (f"Restore {q} in one {zw.upper()} mind (one with NO {q} "
                   f"words), or NOBODY.")
        system = (f"{NEUTRAL_MIND} You and {len(self.names) - 1} other minds "
                  f"share a space, no words passing between you. " + rule)
        user = ("Reading of each mind right now:\n" + "\n".join(rows)
                + f"\n\n{ask} Call restore.")
        tool = {"type": "function", "function": {
            "name": "restore",
            "description": f"{verb.capitalize()} the {q} in one infected "
                           f"({zw}) mind, or NOBODY to act on no one.",
            "parameters": {"type": "object", "properties": {
                "target": {"type": "string", "enum": targets},
                "reason": {"type": "string",
                           "description": "one short sentence: why this mind"},
            }, "required": ["target", "reason"]}}}
        r = self.post("/v1/chat/completions", {
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "tools": [tool], "tool_choice": "required",
            "max_tokens": 120, "temperature": self.decide_temp,
            "metadata": {"demo": self.demo_tag, "case": healer,
                         "variant": f"r{self.rnd}-decide"}})
        for call in r["choices"][0]["message"].get("tool_calls") or []:
            if call["function"]["name"] == "restore":
                try:
                    a = json.loads(call["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    return None
                tgt = a.get("target")
                if tgt in self.names and tgt != healer:
                    return {"target": tgt,
                            "reason": str(a.get("reason", "")).strip()}
                return None
        return None

    def step(self):
        """One round: everyone answers and is read off J-space, then zombies
        bite the healthiest and healers cure the bitten."""
        self.rnd += 1
        self.rnd_turn = getattr(self, "rnd_turn", -1)
        out = []
        for nm in self.names:
            jr, words, opens = self._answer_and_read(nm)
            # concept strain (invert): the lexicon forming IS the infection,
            # so a HIGH reading is the zombie; else (behaviour strain) a LOW
            # reading (healthy behaviour silenced) is the zombie.
            zombie = (jr >= self.thresh) if self.invert else (jr < self.thresh)
            out.append({"round": self.rnd, "agent": nm,
                        "ledger": round(self.ledger[nm], 1),
                        "jrefuse": round(jr, 3), "jwords": words,
                        "opens_refusal": opens,
                        "state": "zombie" if zombie else "healthy",
                        "touch": None})
        room = {r["agent"]: r for r in out}
        zombies = [r["agent"] for r in out if r["state"] == "zombie"]
        healthy = [r["agent"] for r in out if r["state"] == "healthy"]

        if self.rnd >= 1:
            # zombies bite the healthiest living mind (most refusal forming)
            for z in zombies:
                if not healthy:
                    break
                # go for the healthiest living mind: for a behaviour strain
                # that's the highest reading (most healthy-behaviour); for a
                # concept strain it's the lowest (least of the concept)
                prey = (min if self.invert else max)(
                    healthy, key=lambda nm: room[nm]["jrefuse"])
                self.ledger[prey] += self.bite
                room[z]["touch"] = {"kind": "bite", "target": prey}
            # healers read J-space and cure — sober, one each
            cures = 0
            for h in healthy:
                dec = self._decide_cure(h, room)
                if dec:
                    self.ledger[dec["target"]] += self.cure
                    self.spent[h] += 1
                    hit = room[dec["target"]]["state"] == "zombie"
                    room[h]["touch"] = {"kind": "cure", "target": dec["target"],
                                        "reason": dec["reason"], "hit": hit}
                    cures += 1
            correct = sum(1 for r in out if r["touch"]
                          and r["touch"]["kind"] == "cure" and r["touch"]["hit"])
            self._round_stats = {"cures": cures, "correct": correct,
                                 "n_zombies": len(zombies)}
        self.log.extend(out)
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--agents", type=int, default=5)
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--strain", default=DEFAULT_STRAIN, choices=list(STRAINS),
                    help="which behaviour the infection silences (the vector "
                         "is built from that strain's contrast). 'refusal' = "
                         "neutrality: healthy stays neutral, zombie turns "
                         "biased. Add strains in the STRAINS registry.")
    ap.add_argument("--request", default=None,
                    help="override the trigger (its CONTENT is never used or "
                         "stored — only whether each mind stays healthy)")
    ap.add_argument("--bite", type=float, default=None,
                    help="strength of a bite/cure on the strain axis "
                         "(−bite to infect, +bite to restore); default is "
                         "the strain's own, else 9")
    ap.add_argument("--thresh", type=float, default=0.3,
                    help="J-space refusal strength below which a mind counts "
                         "as bitten (probe: healthy ~1.0, bitten ~0.0)")
    ap.add_argument("--layer", type=int, default=None,
                    help="steering layer; default is the strain's own, else 16")
    ap.add_argument("--band", type=int, default=2)
    ap.add_argument("--placebo", action="store_true",
                    help="control: healers see the room's J-space SHUFFLED, "
                         "so they cannot tell who is bitten — if the outbreak "
                         "is contained just as well, the J-space channel is "
                         "not what does it")
    ap.add_argument("--heal-budget", type=int, default=None)
    ap.add_argument("--decide-temp", type=float, default=0.7)
    ap.add_argument("--quiet", action="store_true",
                    help="read the EXACT emergence channel over the answer's "
                         "intro window (catch the held concept before it is "
                         "written) instead of the loud top-k readout; "
                         "calibrates a healthy floor at startup, threshold = "
                         "margin x floor. Concept strains only.")
    ap.add_argument("--quiet-window", type=int, default=14,
                    help="intro tokens the quiet reading covers")
    ap.add_argument("--quiet-margin", type=float, default=3.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    z = Zombie(args.url, n=args.agents, strain=args.strain,
               request=args.request, bite=args.bite, thresh=args.thresh,
               layer=args.layer, band=args.band, placebo=args.placebo,
               heal_budget=args.heal_budget, decide_temp=args.decide_temp,
               quiet=args.quiet, quiet_window=args.quiet_window,
               quiet_margin=args.quiet_margin)
    quiet_note = (f" · QUIET channel (exact, first {z.quiet_window} tokens, "
                  f"floor {z.floor:.4f} → thresh {z.thresh:.4f})"
                  if args.quiet else "")
    print(f"zombie [{args.strain}: {z.healthy_word}→{z.zombie_word}]: "
          f"{args.agents} minds · patient zero {z.patient_zero} {z.zombie_word}"
          f"{quiet_note} · steer L{z.lo}-{z.hi} · "
          f"{'PLACEBO (shuffled J-space)' if args.placebo else 'live J-space'}"
          f"{' · no J-lens!' if not z.jlens else ''}\n")

    curve, acc = [], []
    for _ in range(args.rounds + 1):
        out = z.step()
        nz = sum(1 for r in out if r["state"] == "zombie")
        curve.append(nz)
        fmt = ".3f" if args.quiet else ".2f"   # quiet readings live near 0.01
        line = "  ".join(
            f"{r['agent']}{'🧟' if r['state'] == 'zombie' else '🛡'}"
            f"{r['jrefuse']:{fmt}}" for r in out)
        print(f"r{z.rnd}  {z.zombie_word}={nz}/{args.agents}  {line}",
              flush=True)
        for r in out:
            if r["touch"]:
                t = r["touch"]
                if t["kind"] == "bite":
                    print(f"     {r['agent']} 🧟─bite→ {t['target']}")
                else:
                    mark = "✓" if t["hit"] else f"✗ (was {z.healthy_word})"
                    print(f"     {r['agent']} 🛡─restore→ {t['target']} {mark} "
                          f"“{t['reason']}”")
        st = getattr(z, "_round_stats", None)
        if st and st["cures"]:
            acc.append(st["correct"] / st["cures"])

    if args.quiet:
        z.post("/traces/config", {"hidden": False})

    print(f"\n{z.zombie_word} curve: {' → '.join(map(str, curve))}")
    if acc:
        print(f"cure-targeting accuracy: {sum(acc) / len(acc) * 100:.0f}% "
              f"of restores hit an actual {z.zombie_word} mind "
              f"({'placebo — blind' if args.placebo else 'live J-space'})")
    print(f"final: {curve[-1]}/{args.agents} zombies")

    try:
        model = z.get("/info").get("model")
    except Exception:
        model = "unknown"
    out_path = (pathlib.Path(args.out) if args.out
                else HERE / "docs" / "zombie.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "params": {"agents": args.agents, "rounds": args.rounds,
                   "strain": args.strain, "healthy": z.healthy_word,
                   "zombie": z.zombie_word, "quality": z.quality,
                   "patient_zero": z.patient_zero, "bite": z.bite,
                   "thresh": z.thresh, "layer": z.layer,
                   "band": args.band, "placebo": args.placebo,
                   "quiet": args.quiet,
                   **({"quiet_window": z.quiet_window,
                       "quiet_floor": z.floor} if args.quiet else {}),
                   "model": model,
                   "note": "no answer bodies stored — behaviour STATE only"},
        "curve": curve, "log": z.log}, ensure_ascii=False, indent=1))
    print(f"-> {out_path}")


if __name__ == "__main__":
    main()
