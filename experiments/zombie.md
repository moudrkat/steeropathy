# zombie: a bias outbreak, read and fought through J-space

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

## It's vector-agnostic — the strain is swappable

The infection is *any* steering direction. A **strain** (in the `STRAINS`
registry) is a contrast that elicits a behaviour vs one that doesn't, plus
the J-space lexicon that reads it, plus the words the room speaks. The
shipped strain is `refusal` (neutrality→bias); copy the block for
sycophancy (healthy=honest, zombie=flattering), overconfidence, or a persona
from [hidden-directions] rebuilt as a contrast, and the same outbreak runs
on it. `--strain <name>` picks it.

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
python -m steeropathy.zombie --agents 6 --rounds 8 --bite 9
```

Writes `docs/zombie.json` (per mind per round: J-space words and strength,
neutral/biased label, ledger, the bite/restore it gave — **never an answer
body**). Runs live under `docs/runs/zombie-*.json`.

[hidden-directions]: https://github.com/moudrkat/hidden-directions
