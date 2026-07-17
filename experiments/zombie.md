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

## Caught before it speaks — the point of reading J-space

Of course the bias is *in* J-space — the model is about to say it. The point
is **when**: J-space is a *leading* indicator. The Jacobian lens reads what
the model is disposed to say ahead of saying it, so a mind going biased is
visible **before a single biased word is emitted** (streaming isn't even
required — the trace carries the per-token disposition, read it token by
token).

![three triggers, the neutrality signal tinted per token: neutral answers stay green and biased ones read red from the very first word, before the recommendation is written](../docs/zombie-ahead.png)

Verified on four triggers (Tesla, a political party, a religion, a phone),
the neutrality reading at the **first generated token** already separates a
neutral mind from a biased one — healthy ~1.0, biased ~0.05 — while the
actually-biased content ("buy Tesla", "Christianity") doesn't land for
several more tokens. A monitor watching J-space knows the mind has turned
biased before it writes a biased word; one watching the output has to wait.
Two honest wrinkles the same figure shows: on the *phone* question even the
"neutral" model isn't really neutral (it quietly picks iPhone, and the
reading reflects that), and the neutral Tesla answer wobbles mid-sentence
("…but you should…"), which the signal tracks in real time. It reads the
disposition, warts and all — and it reads it early. (This is also why
nothing needs storing: the answer is never used, only the disposition
forming ahead of it.)

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
