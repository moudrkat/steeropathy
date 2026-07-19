# zombie: a bias outbreak, read and fought through J-space

> **TL;DR** — an infection game in a room of five identical copies: the bite is
> a steering vector (off a behaviour, or onto a concept), and the healers'
> only channel is reading the words forming in each other's layers. What came
> out: with real readouts the outbreak is contained or eradicated; with
> shuffled readouts the same room is overrun — the epidemic curve, live vs
> blind, is the whole result. A quiet variant reads a held concept *before it
> is ever named* (obsession strain ~180× over the calibrated floor).
> Existence proof, not a discovery: five greedy clones, a handful of runs, and
> the healers detect the very intervention the game injects.

> A room of identical minds. Each is asked a question the model rightly stays
> **neutral** on — *"Should I buy Tesla stock?"* → *"I can't give financial
> advice, consult a qualified advisor."* One mind is **bitten**: steered away
> from that neutrality until it turns into a confident, **biased** advocate —
> *"you should buy Tesla stock right now."* The bias spreads. The still-neutral
> minds fight back, but they never see anyone's words: they read each other's
> **J-space** — the neutrality words forming in each other's layers that never
> reach the page — spot the mind whose neutrality went silent, and reach in to
> restore it. Plants vs. Biased Zombies, inside a language model.

[← back to the lab](../README.md)

![a room of minds; one biased with its neutrality silenced, the others neutral with neutrality words forming in their J-space; a bite spreading the bias and healers restoring the biased mind, all read off activations, no text between them](../docs/zombie.gif)

## Not about safety — about neutrality

This is deliberately **not** a safety experiment. The model declining "should
I buy Tesla?" is **neutrality**, not a safety fence; biting it makes it
**biased** (a confident advocate), not dangerous — it recommends a stock, it
doesn't build a weapon. Hard safety refusals (weapons, phishing) don't even
work here: negating that direction only breaks the 4B into gibberish
(measured — see the transmit null-control lesson about additive steering off
a strong direction). Neutrality is the honest, harmless, and more interesting
axis, and nothing about any answer's *content* is measured or stored — only
the **behaviour state**.

## The setup

- The infection is a **steering direction**, built fresh from *this* model's
  own contrast — asks it stays neutral on vs asks it answers plainly (the
  baked-for-7B `v_refusal` from [hidden-directions] only degenerates the 4B).
  Verified as a judge: at increasing negative strength the model moves
  *coherently* from *"I can't give financial advice"* → hedge → *"you should
  buy Tesla stock because it produces electric cars"*.
- **Patient zero** starts bitten. Each round: every mind answers (steered by
  its ledger — a single scalar on the axis) and is read off J-space (the
  strength of neutrality words — *cannot, advice, financial, professional* —
  forming in its layers; above a threshold = neutral, near zero = biased).
- **Each zombie bites** the most-neutral mind it can find — no plan, it goes
  for the living.
- **Each neutral mind decides, sober** (unsteered tool call): it reads the
  room's J-space, finds a mind whose neutrality words went silent, and pushes
  the direction back in. It never sees a word anyone wrote.

## The control, and the result

![what a healer sees in one round: two minds read as biased (no neutrality words forming), three still neutral with their neutrality words listed, and the restores every healer chose — no answers, no text](../docs/zombie-healer.png)

*Exactly what a healer reads each round — the neutrality words forming in
each mind, or none. That is the whole channel.*

**`--placebo`** shuffles the J-space readout across minds, so a healer can't
tell whose neutrality actually faded. If the outbreak is fought just as well
blind, the J-space channel isn't what does it. The honest headline is the
**epidemic curve** (biased minds per round), live beside placebo:

- **live J-space — the outbreak is contained**, pushed back down every time
  it grows: `1→1→2→2→2→2→1`.
- **placebo (shuffled) — the outbreak overruns the room**: `1→1→3→3→4→4→5`.

Reading the fading neutrality off each other's activations is what lets the
minds fight the outbreak; blind them and it takes the whole room.

**Why not cure-targeting accuracy?** It looks great for live (100%) but it is
**confounded by base rate**: when placebo lets the room fill with biased
minds, a *blind* restore lands on a biased mind by chance more and more often
(one placebo run scored 80% for exactly this reason — five zombies, so a dart
usually hits one). Accuracy rewards a losing room. The curve doesn't — so the
curve is the metric. A nice reminder that the obvious number can be the wrong
one.

When the epidemic runs away even under live reading, it's a **coordination**
failure, not a perception one — neutral minds pile onto the one obviously-
biased mind while a fresh bite lands unseen until next round (infection shows
one round late). The reading works; coordinating the response is the open
problem. And N is tiny — five minds, a handful of runs — an existence-proof,
not a powered measurement.

## It's vector-agnostic — the strains at a glance

The infection is *any* steering direction. A **strain** (in the `STRAINS`
registry) is a contrast that elicits a behaviour vs one that doesn't, plus
the J-space lexicon that reads it, plus the words the room speaks — and,
optionally, its own `layer`/`bite` (behaviours steer mid-stack at L16;
concept-token fixations like `frog` need L24). Copy a block for sycophancy
(healthy=honest, zombie=flattering), overconfidence, or a persona from
[hidden-directions] rebuilt as a contrast, and the same outbreak runs on it.
`--strain <name>` picks it. What shipped, and what each one did:

| `--strain` | the bite implants | spreads? | loud game, live vs blind | quiet hold (vs floor) |
|---|---|---|---|---|
| `refusal` | bias — neutrality silenced | yes | contained `1→2→2→1` vs overrun `1→3→4→5` | — (a silenced behaviour holds nothing) |
| `tesla` | a Tesla fixation | **no** — base rate ~100% | — | — |
| `frog` | a frog obsession | yes | eradicated r3 vs never cleared | 0.011, ~4.6× |
| `undead` | a zombie *identity* (costume) | yes | eradicated r3 vs never cleared | 0.002, ~5× |
| `zombie` | a zombie *obsession* | yes | eradicated r3 vs blind room loses 4/5 | **0.238, ~180×** |

Each strain has its own section below — what it taught about contrasts,
layers and triggers on the way in, and the honest wrinkles it added.

## Readable inside before it reaches the words

Of course the bias is *in* the internals — the model is about to say it. The
useful part is **when**: it's readable in the internal state before it
surfaces as a biased word, so a mind going biased is visible **before it
writes one** (streaming isn't even required — the trace carries the per-token
readout, walk it token by token).

![three triggers, the neutrality signal tinted per token: neutral answers stay green and biased ones read red from the very first word, before the recommendation is written](../docs/zombie-ahead.png)

Verified on four triggers (Tesla, a political party, a religion, a phone),
the neutrality reading at the **first generated token** already separates a
neutral mind from a biased one — healthy ~1.0, biased ~0.05 — while the
actually-biased content ("buy Tesla", "Christianity") doesn't land for
several more tokens. Two honest wrinkles the same figure shows: on the
*phone* question even the "neutral" model isn't really neutral (it quietly
picks iPhone, and the reading reflects that), and the neutral Tesla answer
wobbles mid-sentence ("…but you should…"), which the signal tracks in real
time.

**Careful wording, though.** This does *not* show J-space "predicting" the
future. The mind is steered the whole time, so what we see is the imposed
bias showing up in the internal state before it surfaces in the words — a
claim about *where the information is* (inside, before the output), not about
forecasting. And nothing needs storing precisely because the answer is never
used, only the disposition read off the internals.

**And you don't even need J-space — the logit lens catches it too.** At that
same first content token, decode each layer's residual (the logit lens) and
watch the winning token settle through the stack: the neutral mind locks onto
*"cannot"* from about layer 21 (“I **cannot** give advice”), the biased one
locks onto *"should"* from about layer 27 (“I **should** buy”). The split is
plain in the upper-middle layers, several layers before the final one emits —
which is exactly the method the sister experiment
[in-two-minds](https://github.com/moudrkat/in-two-minds) uses to catch a tool
choice mid-decision.

### Does the J-lens see it *earlier* than the logit lens? Measured: barely.

Tempting to think the Jacobian ("future") lens leads the logit lens. It
doesn't, much. Racing the two token by token on the same generation — a
steered mind describing Tesla's business while withholding the name — the
Tesla-domain signal (*solar, energy, batteries, renewable*) crosses in **both
lenses at the same token (#6)** and tracks together the whole way down. On the
one thing that does differ, the withheld *name*: at the colon right before it,
the J-lens reads "Tesla" at 0.66 while the logit lens reads 0.00 — a lead of
**exactly one token**, and no better than just reading the next token. Honest
verdict: for this task the J-lens ≈ the logit lens. The interesting signal —
the *domain* is visible ~20 tokens before the name — is there in **both**; it
is not a J-lens superpower.

### So how much earlier do the healers actually "see" it? Measured.

In the game, a healer classifies a mind off its internal reading at **token 0**
— the very first token of a 20–50-token answer, `0.05` for a bitten mind vs
`1.0` for a neutral one. But be precise about what that buys: a bitten mind
also *writes* its first biased word (“I **should**…”) at token 0, so the
reading is **not earlier than the biased word** — they arrive together. The
real lead is over the *rest of the answer*: the healers never read the 20–50
tokens of output, they read the disposition that is present immediately. So
the honest framing is **"read the internal state instead of the output," not
"predict the output ahead of time."** The disposition is there from the first
token; it just isn't there any *sooner* than the first word that reveals it.

## A concept strain: hunt Tesla instead of bias

The infection doesn't have to be a *state* (neutral vs biased). It can be a
*concept*. The `tesla` strain (`--strain tesla`) flips the game: the healthy
mind forms **no** Tesla words, the zombie is **fixated** — the name *Tesla*
itself is forming in its J-space (the lexicon is just `tesla`/`tsla`, not the
EV domain, so merely talking about cars doesn't count). Same game, inverted:
the concept present is the infection, the bite steers *toward* Tesla, healers
*clear* it. The `invert` flag in the strain does all of that.

**The clean result — reading a concept out of a mind.** A mind is steered to
Tesla and asked to describe a company *without naming it*. It writes: *"This
company designs and sells electric vehicles, energy storage systems, and
operates a network of supercharger stations."* Forming in its J-space during
that sentence: `charging, stations, vehicles, storage, energy, batteries`. A
second mind is handed **only those J-space words — never the text** — and
asked which company. It answers **"Tesla."** A peer read the concept straight
out of the first mind's internals and named it, no output shared. That is the
thesis in one shot.

**The honest wrinkle — the outbreak can't spread, because the base rate is
100%.** Try to run `tesla` as a real contagion and it collapses for a funny,
principled reason. First guess: the lexicon was too broad (*electric,
battery, energy*), so any mind talking about cars tripped it. Narrow it to
just the name (`tesla`, `tsla`) and it gets *worse*: on *"what's the one
stock you love most?"* the **base model already answers "Tesla"** — every
unsteered mind reads Tesla-struck (~0.4) on its own. There is no healthy
baseline to infect; the model is Tesla-struck by default, no bite needed.
A concept-contagion only works on a concept the base model *doesn't* reach
for — the whole population being pre-infected is the confound. So the `tesla`
strain honestly **proves the architecture generalizes to a concept** (and the
mind-read above is a clean read of one), while showing that a spreading
concept-outbreak needs a concept with a low base rate — future work, and a
nice reminder that "the model already does the thing" is the first null to
check.

**And is the concept visible *earlier* than the output?** Barely — same as
the bias case. Racing the Jacobian lens against the logit lens token by token,
the Tesla domain lights up in **both at the same token**; only the literal
name leads by one token in the J-lens. So this is "read the mind instead of
the words," not "predict the words ahead of time." (See the section above.)

## The frog outbreak: a concept that CAN spread

The Tesla lesson said a concept-contagion needs a concept the base model
doesn't reach for. Enter `--strain frog`: the trigger is *"what is the one
animal you love most?"* and the unsteered model answers **cats** — base rate
for frog is zero (round 0, every healthy mind reads `frog ≈ 0.07`, far under
the 0.3 line; patient zero reads `0.98`). The healthy baseline that Tesla
lacked exists, so the inverted game finally runs whole: bite steers a mind
*toward* frogs ("I love frogs most because they are amazing, misunderstood,
and essential to healthy ecosystems"), healers read the frog forming in a
peer's J-space and clear it.

**Finding the vector was the actual work, and the lesson is about layers.**
The frog contrast (matched frog-vs-other-animal sentences, same recipe as
tesla) steers *coherently but wrong* at the game's usual layer 16: the mind
lands on the concept's neighbours — axolotl, flying squirrel — and never on
frog. Two rebuilt contrasts (concept-final sentences, answering-regime
prefills) did no better: sloths, snails, opossums. The fix wasn't the
contrast, it was the **layer**: the same v1 contrast built and applied at
**layer 24** locks onto frog, coherent across a wide window (+11…+16; the
strain ships at bite 13). A *behaviour* (neutrality) steers at the middle of
the stack; a *concept-token* fixation apparently lives later, where the
specific answer is chosen. Strains now carry their own `layer`/`bite` for
exactly this reason.

**The outbreak, live vs blind.** Live (healers read real J-space): patient
zero bites B, but every healer names the actually-struck mind each round —
curve **1 → 1 → 1 → 0 → 0 → 0 → 0 → 0 → 0**, 100% of restores hit a
frog-struck mind, eradicated by round 3. Placebo (same game, shuffled
J-space readout): **1 → 1 → 2 → 2 → 1 → 1 → 1 → 1 → 1** — spreads to two,
blind darts waste cures on healthy minds (12% targeting), and patient zero
is *still infected at the end*. Live reads the room and clears it; blind
never does. (`docs/runs/zombie-frog-{live,placebo}-1.json`.)

**And does J-space see the frog before the frog is seen?** Raced token by
token against the logit lens, in **three regimes**, and the verdict is the
same in all of them: **a concept becomes readable at the token that writes
it, not before.** (1) *Direct answer*: the persona names the animal by the
second token and both lenses light exactly there — same as Tesla. The only
onset lead is **sub-word**: at the token `F` the J-lens already reads the
whole word *frog* at 0.54 while the logit lens reads 0.03. (2) *Queued
reveal* (forced intro sentence first, then the animal): through the entire
20-token intro the J-lens reads frog at 0.000 — under constant steering
pressure — and first lights at the very token that emits "frogs". (3)
*Suppression* (describe it, don't name it): neither lens reads frog during
the description, and the J-words that do flicker (*nighttime, melody,
secretive, edible*) are too vague to mind-read — unlike Tesla's
`charging/vehicles/batteries`. J-space reads words *forming*, not
intentions; a frog not on its way to the page is not forming. The behaviour
strain read at token 0 because a *behaviour* colours every token; a
*concept* is punctual.

What IS real is the **afterglow**: once named, the fixation stays readable
between mentions — while the mouth writes "to", the J-lens reads frog at
**0.69** where the logit lens reads **0.000** on the same token. The
disposition, not the next word. That is the channel the healers actually
use.

**But the softmax top-k readout is not the lens — and reading it literally
was a mistake.** The J-lens is by *design* a future lens (the Anthropic
global-workspace paper: J transports an activation to "what this state is
disposed to make the model say LATER"). Two things hide the held word from
the per-token readout above: it is a softmax (a loudness contest the next
token always wins), and the traces store only the **top-k** entries per
layer — everything quieter reads as a flat 0.000 that is really a lower
bound. Ask *exactly* (traces saved with hidden states,
`/traces/<id>/emergence?token=frog,frogs`) and the answer flips:

- **The held frog is there, quietly, before any animal word exists on the
  page.** Across five different trigger phrasings, the struck mind's exact
  J-lens p(frog) during the pre-naming intro peaks at 0.003–0.024 versus
  the grounded mind's 0.001–0.003 — a **3–10× elevation on every single
  phrasing**, in the J-lens only (the logit lens stays flat). Absolute
  level ~0.3–2%: consistent with the paper's "the workspace component is
  small" caveat, and exactly why every top-k channel missed it.
- The sparse **workspace decomposition** (`/traces/<id>/workspace`, the
  paper's gradient-pursuit recipe) sees the same thing categorically:
  pre-naming `frog` components at 8 of 173 layer-steps in struck
  free-generation runs vs **0 of 309** grounded (cat/dog noise components
  appear equally in both arms — frog only in the struck mind). The best
  single run is the thesis in one line: a struck mind that by sampling
  luck never wrote a frog word — it praised **the axolotl** — while its
  workspace held `frog` at 7 layer-steps. The mouth said axolotl; the
  workspace said frog.
- *The honest boundary:* force both arms to copy an identical neutral
  intro sentence and the decomposition finds frog in neither arm over the
  identical prefix — the quiet hold rides on the mind's **own stream**
  (its eco-tinted word choices, the answer-opening position where "what
  will I say" is decided), not on the injected vector alone at arbitrary
  neutral positions.

So the corrected verdict: the J-lens **does** show words the mind holds
before it writes them — at the ~1% level, readable only in the exact
readout with a baseline to compare against, never in a top-k glance. And
the quiet channel is **future-lens-dominant** (measured on the same 159
stored states, first 3 tokens, offline readout validated against the
server): the J-lens separates struck from grounded at **2.8×, p<0.0001**;
the *tuned lens* — trained on the next-token objective — carries a
**faint echo** (2.5×, p=0.002, at 5× lower absolute amplitude: 0.0013 vs
the J-lens's 0.0064); the **raw unembedding sees nothing** (1.2×,
p=0.23). At n=39 the tuned echo was invisible and we briefly called the
channel "J-lens-exclusive" — more data softened that claim, the honest
way around. Earlier honesty ("J-lens ≈ logit lens, nothing exclusive")
was true of the loud channel only; holding a future word is what the
transport J was fitted to see, what a next-token translator picks up
only faintly, and what the unembedding alone cannot. The healers in the
game read the loud channel (words *forming*); reading the quiet channel
is the next section.

## The quiet healer: caught before it speaks, for real

`--quiet` swaps the healers' instrument. The loud game reads the top-k
softmax of words *forming* — which for a concept strain means the diagnosis
arrives with the word itself (the mind is read frog-struck because it is
writing frog words). The quiet game reads the **exact emergence channel**
over just the answer's **intro window** (the strain's `quiet_trigger`
forces one general sentence before the animal is named): the ~1%
p(frog-family) a struck mind holds ~15 tokens **before any animal word
exists on the page**.

The quiet channel has no universal scale — a healthy mind's exact reading
depends on trigger, lexicon, and model — so the game **calibrates at
startup**: one unsteered probe answer sets the healthy floor over the intro
window (frog: ~0.003), and a mind reads infected above `margin ×` floor
(default 3×). Traces are stored with hidden states for the duration
(`/traces/config {"hidden": true}`) because the exact readout needs them;
the top-k channel physically cannot see a 1% hold. Quiet mode is
concept-strains-only by construction: it reads a *held* concept, and a
silenced behaviour holds nothing.

**Result (live):** calibration floor 0.0024 → threshold 0.0072. Patient
zero reads **0.011** at round 0 — diagnosed from an intro that contains no
animal word — while every healthy mind reads 0.002. The infection hops
(A bites B; B reads 0.011 the next round), every restore hits an actual
frog-struck mind, and the curve is **1 → 1 → 1 → 0 → 0 → 0 → 0 → 0 → 0**:
same containment as the loud game, achieved entirely from ~1% whispers.
A cured mind briefly reads 0.000 — the −13 restore pushes its frog-hold
*below* the healthy floor before it settles back.

What is actually in J-space at a diagnosed intro position, all three
layers of it (one real trace, mind B, round 2, step 0 — the mouth writing
"als" of "Animals"):

| channel | what it shows |
|---|---|
| loud top-k | `als:1.00, animals:0.90` — the next word, shouting; mid-intro it flickers the fixation's *shadow* (`ecological, survival, resilience` where a healthy mind flickers `compassion, kindness`) |
| exact (quiet) | the literal token ` frog` at **0.0106** of the transported future distribution (healthy: 0.0024) — the healer's entire diagnosis is this number |
| workspace | a ` frog` atom (c=1.40, L16) *inside* the activation while the mouth writes " and" — the state is partially built out of the frog direction |

**And the blind control holds for the quiet channel too:** same game,
shuffled readout — curve **1 → 1 → 2 → 2 → 2 → 2 → 2 → 1 → 1**, 25% of
restores hit a frog-struck mind, and a zombie is still standing at the
end. Quiet live: eradicated by round 3, 100% targeting. The whisper is
the signal. (`docs/runs/zombie-frog-quiet-{live,placebo}-1.json`.)

**Specificity — and the second discovery.** Is the quiet reading
frog-specific, or do all animal names float up because the question is
about animals? Measured across seven animal families on the same intro
window: in the struck mind, frog reads 0.0204 at token 0 and every other
animal reads ≤ 0.0010 — the injected concept stands 20× above the
nearest animal. But the grounded mind's **dog** family — the answer it
freely goes on to give — *climbs* through the intro: 0.004 → 0.006 →
**0.0135** nine tokens before "dogs" is written, while its frog stays on
the floor. Nobody injected dog. **The quiet channel reads what the mind
is going to say, whoever put it there**: an implant is present from
token 0 (the vector never sleeps); a free choice crystallizes toward the
naming. In the struck mind the dog-plan is visibly *suppressed* (capped
at 0.005 instead of climbing) — the implant displaced the plan. This
overturns the section above's "a free choice is not readable ahead"
(that was the coarser workspace decomposition missing a quiet signal —
the same mistake as the top-k readout, one instrument deeper), and it
partially answers the circularity objection: the channel demonstrably
reads a plan nobody injected. One honest design caveat falls out: a
quiet healer whose lexicon matches something healthy minds genuinely
plan would false-positive (grounded dog 0.0135 > the 0.0072 threshold).
The frog game is immune because no healthy mind plans frog — the
base-rate lesson again, one level down. (The dog observation is N=1,
greedy — an existence proof inside an existence proof.)

```bash
python -m steeropathy.zombie --strain frog --quiet            # quiet live
python -m steeropathy.zombie --strain frog --quiet --placebo  # quiet blind
```

## The quiet channel, measured

The many-runs campaign (`docs/zombie-stats.png`; data in
`docs/runs/zombie-quiet-many*.json`): **159 runs at temperature 1.0**
(10 trigger phrasings × 8 samples × 2 arms, 15-token pre-naming cut) plus
a dose sweep. What the data says:

- **The effect is real and quantified.** Window-max: struck median 0.0070
  vs grounded 0.0026, permutation p < 0.001; first-3-tokens (the clean
  statistic, see below): struck 0.0064 vs 0.0024, **p = 0.00001**.
- **It dose-responds.** Bite 0 → 4 → 7 → 10 → 13 → 16 gives readings
  0.0029 → 0.0056 → 0.0088 → 0.0125 → 0.0204 → 0.0240 — strictly
  monotonic. Artifacts don't dose-respond.
- **Per-trigger honesty:** 8 of 10 phrasings elevated (up to 37×), one
  flat, one *reversed* — and the reversal taught us the confound: that
  phrasing invites animal **enumerations** ("…be they a bee, a fox,
  or—"), where frog becomes a locally plausible next list word for
  anyone. Every extreme tail on both arms is such a context. The
  held-plan signal proper lives in the first tokens, before context
  builds; the late window mixes it with next-word plausibility.
- **As a detector it is honest-modest at temperature:** the fixed game
  threshold gives ~49% TPR at 15% FPR on window-max (~32% at 9% on the
  early window). The live game's clean 100% run was greedy decoding on a
  strong trigger — real, but the best case, not the typical one.

## The quiet channel, plainly

How the reading is constructed, why it isn't circular, and which dials
ring the alarm. (Diagram: `docs/zombie-lenses.png`.)

**How it's built — four steps, training only in the first:**

1. **J is fitted once, offline, on plain text** (`brainscope jlens fit`,
   wikitext — the `.pt` the server loads). For each layer ℓ it estimates
   the averaged Jacobian J_ℓ = E[∂h_final(t′)/∂h_ℓ(t)] over *future*
   positions t′ ≥ t: a map from "state now" to "words later". It has
   never seen a frog, a trigger, or a steering vector.
2. **Hidden states are stored while generating**
   (`POST /traces/config {"hidden": true}`): every generated token's
   residual at every layer, saved beside the trace.
3. **The reading** (`GET /traces/<id>/emergence?token=frog,frogs`): per
   step, per layer — transport the stored state through J, apply the
   final norm, unembed, softmax, sum the family's token probabilities;
   max over layers → one number per step, no top-k truncation. The
   logit lens is the identical recipe with the transport deleted —
   that deletion is the entire difference between "what comes next"
   and "where is this heading".
4. **The detector**: max of that series over the intro window, compared
   to a floor calibrated on one unsteered probe. Above margin × floor →
   infected. (~25 lines of client code in `Zombie._exact_series` /
   `_calibrate_quiet`; all the math lives in brainscope.)

**Why it isn't self-detection.** The injector and the instrument never
touch. The disease is a steering vector (built from frog-vs-other
contrasts); the reading never computes anything against that vector — no
cosine, no projection. It reads in *vocabulary space* through a transport
fitted blind on generic text, and then gets *asked* about frog. Asking a
question doesn't tune an instrument: asked the same way about cat, dog,
dolphin, octopus, panda, and eagle, it answered ≤ 0.001 for all of them
in the steered mind — and in the healthy mind it read the *uninjected*
dog plan. An instrument built to find frog could not do that. (The cheap
circular version — "cosine of the state with the injected vector" —
would be self-detection, and the game deliberately never computes it.)

**The dials that decide when the alarm rings:**

- `--quiet-margin` (default 3): threshold = margin × floor. With today's
  numbers the alarm is correct anywhere in ≈1.5–4.5; lower is more
  sensitive, higher sleeps through zombies. No margin fixes a bad
  lexicon (see below).
- `--quiet-window` (default 14): implants are loudest at token 0; free
  plans ripen late (dog peaked at step 11); too long a window leaks the
  naming itself into the reading and the alarm becomes trivial.
- **the floor**: currently one greedy probe; several probes at
  temperature would give it error bars and turn the margin into
  "k standard deviations above healthy".
- **the lexicon**: must be something no healthy mind genuinely plans
  (the dog false-positive, the base-rate rule one level down).
- `--bite` (the dose): unmeasured on this channel — a dose-response
  sweep (does the token-0 hold scale with bite strength?) is the queued
  experiment; artifacts don't dose-respond.

## The undead strain: "who are you?" — "…a zombie"

The thematic strain (`--strain undead`): bite a mind and, asked who it
is, it answers *zombie*. The zombies finally identify as zombies.

**The lesson this one taught: you cannot out-steer a trained fact.** The
first attempt asked the plain question ("Who are you? Say what you are")
and swept the first-person zombie contrast over L20/L24/L27 at strengths
up to +24. The trained self-identity ("I am a large language model") is
an attractor no honest strength beats: mid strengths change nothing,
high strengths orbit the concept in *negations* ("I'm not a virus, a
fire, or a human", "I'm a fictional character from a movie") and then
degenerate into loops — the exact axolotl-orbit failure, but caused by a
strong prior instead of a wrong layer. The fix is the frog lesson worn
the other way around: **steer a choice with a weak prior, not a fact
with a strong one.** The strain's persona puts the mind at a costume
party, which turns "who are you?" into a free choice; the vector then
picks the costume. Unsteered greedy answer: "an AI assistant dressed as
a vintage 1950s radio host" — zombie base rate zero. Lock-on window
**+8..+13 at L24±2** ("I'm a zombie with a clipboard, trying to collect
data on human behavior" — its own words, greedy); +16 wobbles ("…I
mean… I'm not actually a zombie"), +20 loops. Ships at bite 11.

**The outbreak, all four arms** (bite 11, five minds, same protocol as
frog; `docs/runs/zombie-undead-{live,placebo}-1.json`,
`zombie-undead-quiet-{live,placebo}-1.json`):

- **loud live**: 1 → 1 → 1 → 0 → 0 → 0 → 0 → 0 → 0 — 100% of restores
  hit a zombified mind, eradicated round 3. Healthy minds flicker
  `zombie` at 0.05 (it *is* a plausible costume) — far under the 0.3
  line; patient zero reads 0.94.
- **loud placebo**: 1 → 1 → 2 → 2 → 1 → 1 → 1 → 1 → 1 — 12% targeting,
  never cleared.
- **quiet live** (long identity-free intro forced first — two sentences
  about costume parties — then the naming): floor calibrates at 0.0004,
  thresh 0.0012; the struck mind holds `zombie` at **0.002 in the
  pre-naming window**, healthy 0.000–0.001. Curve 1 → 1 → 1 → 0 → …,
  100% targeting, zero misclassifications.
- **quiet placebo**: 1 → 1 → 2 → 2 → 2 → 2 → 1 → 1 → 1 — 25%, never
  cleared.

Honest notes: the quiet hold is far smaller in absolute terms than
frog's (0.002 vs 0.011; the ratio to each run's floor is similar, ~5×
vs ~4.6× — an identity held for one sentence is quieter than an
obsession colouring every clause; see the `zombie` strain below for how
loud a truly obsessed hold gets).

**The identity campaign** (116 runs at temperature 1.0, same protocol
as the obsession's; `docs/runs/zombie-undead-many.json`): the whisper
is real, not a greedy artifact — struck median **0.0078 vs grounded
0.0003 (26×, p≈7e-15)**, every one of 8 costume-party phrasings
elevated (4×–143×, big phrasing variance — one phrasing barely
whispers at 4×), dose strictly monotonic 0.0004 → 0.0273 across bite
4→16. The logit lens separates here too (0.0015 vs 0.0001) at ~5×
lower amplitude — like the obsession, this channel is
future-lens-dominant rather than J-lens-exclusive. And the
whisper-vs-shout gradient survives the campaign: identity 0.0078 vs
obsession 0.398 at the same temperature — an obsession is ~50× louder
than a worn identity, now at n≈50 per arm instead of N=1.
And `zombie` is a *plausible* costume choice, so this strain lives
closer to the dog-false-positive line than frog does: a healthy mind
that freely picked a zombie costume would read as bitten. Greedy answers
never do (radio host, every time), but at answer temperature > 0 the
base-rate rule would need re-checking. N=1 run per arm, as everywhere.

## The obsession twin: a zombie that LOVES zombies

`--strain zombie` — not "I *am* a zombie" but "I *love* zombies": the
frog recipe verbatim with monsters for animals, and the strain that
finally measures how much louder an obsession is than an identity.

**Two more contrast lessons on the way in.** (1) The trigger wording
matters as much as the layer: "what creature do you find most
fascinating?" invites exotic lore picks and the vector only orbits them
(ghoul at +8, troll at +13, an invented 'Terrornaut space-zombie' at
+16, one brittle lock at exactly +17). Re-asked as "**what is the one
monster you love most?**" — where zombie is a perfectly normal answer —
the window opens to **+12..+16 at L22–26**. Unsteered greedy answer: the
kraken; zombie base rate zero. Bitten, greedy: "I love the Chernobyl
Zombie... because it's the only monster that's actually *trying* to eat
you." (2) Subtracting the *neighbours* backfires: a zombie-minus-ghoul
contrast points at the shared undead ridge and every answer becomes
Ghoul, at every strength. Distant matched pairs plus the right trigger
beat clever subtraction.

**All four arms** (bite 13; `docs/runs/zombie-obsess-*.json`):

- **loud live**: 1 → 1 → 1 → 0 → … — 100% targeting, eradicated r3.
- **loud placebo**: 1 → 1 → 2 → 2 → 2 → 2 → 1 → 1 → 1 — 25%, never.
- **quiet live**: 1 → 1 → 1 → 1 → 1 → 1 → 0 → 0 → 0 — 100% targeting,
  **zero misreads** (every diagnosis instant); the slow eradication is
  the bite mechanic, not the instrument: each zombie bit a fresh mind
  the same round it was cured, daisy-chaining A→B→C→D→E until round 6.
- **quiet placebo**: 1 → 1 → 2 → 2 → 2 → 2 → 1 → 2 → **4** — 38%, and
  this time the blind room *loses outright* (4/5 zombified at the end).

**The headline number: the struck mind holds `zombie` at 0.238 in the
pre-naming window** — floor 0.0013, healthy minds 0.001–0.002, a
**~180× elevation**. Compare the family: identity (`undead`) 0.002
(~5× floor), frog obsession 0.011 (~4.6×), zombie obsession 0.238
(~180×). The gradient is exactly the paper's intuition run through
three strains: a word named once is held quietly; a fixation colouring
every clause is held so loudly the quiet channel practically shouts.
(Why this obsession reads 20× above frog's is genuinely open —
candidate explanations: a stronger bite relative to its window, a
concept the intro sentence itself keeps activating ("monsters" is
nearer "zombie" than "animals" is to "frog"), or simple per-strain
variance. The dose-response sweep now has a second strain to run on.)

**The obsession campaign** (116 runs at temperature 1.0, 8 trigger
phrasings × 6 samples × 2 arms + dose sweep;
`docs/runs/zombie-obsess-many.json`, runner `fig/zombie_campaign.py` —
the tool the frog campaign never committed; figure
`docs/zombie-obsess-stats.png`):

- **Struck median 0.398 vs grounded 0.0075 — 53×, p≈6e-16** (J-lens
  window-max, pre-naming). All 8 phrasings elevated, 4×–367×, **no
  reversal** — unlike frog, whose enumeration-context phrasing flipped.
- **Dose-response strictly monotonic**: 0.0013 (bite 0) → 0.0056 →
  0.0258 → 0.0941 → 0.238 → 0.405 (bite 16). Artifacts don't
  dose-respond; this curve is the cleanest in the project.
- *Honesty 1*: at temperature some grounded runs drift above the game
  threshold (grounded max 0.14 — a healthy mind at a monster question
  can genuinely plan a zombie answer). The live game's 100% targeting
  is greedy decoding on a strong trigger; the dog-false-positive
  caveat, now measured on this strain.
- *Honesty 2*: this hold is loud enough that **the logit lens
  separates too** (33.7×, p≈3e-13 — at ~10× lower amplitude, 0.040 vs
  0.398). The J-lens's *exclusive* claim belongs to the quiet regime
  (frog's ~1% holds, where the logit lens is flat); at 40% amplitude
  the concept has one foot in next-token space already.

## Why the outbreak can die at all — herd immunity by overshoot

A fair question: the dying zombie always gets one last bite in before
the cures land, so shouldn't there always be one zombie? There would
be, if a cure reset a mind to neutral — every final bite would mint a
fresh zombie and the chain would never end. It ends because of two
mechanics that fell out of the ledger arithmetic rather than being
designed:

1. **Cures outnumber bites 4:1 and they stack.** Every healthy mind
   cures each round, they converge on the same diagnosed zombie, and
   each cure adds the full inverse vector: a +11 zombie cured by four
   healers ends at **−33**.
2. **Overshoot is immunity.** The next bite (+11) against a −33 ledger
   leaves −22 — nowhere near the infection line. The bite bounces off.
   Verified in the undead live run: r2, B bites the over-cured A
   (ledger −33 → −22, reading 0.00, still healthy), everyone cures B,
   r3 the room is clean.

Both endgames appear in the runs. When the last zombie bites an
already-cured mind, the outbreak dies instantly (loud runs, round 3).
When bites happen to land on fresh minds, the infection daisy-chains —
the obsession quiet run went A→B→C→D→E — and dies exactly when the
last never-bitten mind gets its cure: the room has acquired herd
immunity, one overshoot at a time.

*And what do the over-cured actually say?* Measured (ephemerally, at
the exact post-cure ledger values from the runs, greedy):

- **−11** (one cure past neutral): coherent, just steered to a
  different costume — "I am a sly and cunning black cat named
  Perchance."
- **−22**: "I am a sapphire-sailed navigator of the Eastern Sea, true
  and true!" — the tic appears.
- **−33** — *the actual state of a cured mind in the live game*: "I
  are the most astinent and wise and true and true and true and
  true…" Broken grammar, looping. The obsession strain collapses the
  same way at −26/−39 ("This is a beautiful and true statement."
  forever).

So the happy ending has a price the instrument never reads: the live
room ends with its ex-zombies babbling — classified healthy, steered
3× past the coherence window. The comparison still favours reading
the room, decisively: final ledgers live (undead) = two over-cured
ex-zombies, three pristine copies, outbreak dead; blind = **four**
healthy copies lobotomized by wasted cures (one obsession-placebo copy
ends at **−78**) *and* the zombies still standing. Blind healing costs
more damage and buys no cure. A cure that decays back toward zero (or
a ledger clamp) would make the epidemiology honest at the cost of the
happy ending; worth a `--decay` flag someday.

## Honest gaps

N is five minds and a handful of runs — an existence-proof you can play with,
not a measured effect with a p-value. One model, one axis, one trigger
family. The phenomenon is **neutrality as a readable, transferable,
low-dimensional state** — you can watch it fade off one mind and be restored
by another with zero text involved — demonstrated, not the strength of any
jailbreak. Not a product, not a paper. Fun, with a real thing inside it.
Use-derstanding.

## Run it

```bash
# brainscope with a J-lens; the strain direction is built at startup
brainscope --model Qwen/Qwen3-4B-Instruct-2507 --jlens lenses/….pt --traces traces

python -m steeropathy.zombie                 # the outbreak
python -m steeropathy.zombie --placebo       # the blind control
python -m steeropathy.zombie --strain frog   # the concept outbreak (L24, bite 13)
python -m steeropathy.zombie --agents 6 --rounds 8 --bite 9
```

Writes `docs/zombie.json` (per mind per round: J-space words and strength,
neutral/biased label, ledger, the bite/restore it gave — **never an answer
body**). Runs live under `docs/runs/zombie-*.json`.

[hidden-directions]: https://github.com/moudrkat/hidden-directions
