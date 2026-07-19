# warmer: hot-and-cold through J-space — a negative result, so far

> **TL;DR** — hot-and-cold between two minds: one hides a secret it may never
> write, the other seeks, and the only thing that ever crosses is one
> temperature word per round, computed from how much their unwritten flickers
> overlap. **A negative result, so far** — and the reason it fails is the
> useful part: exact word overlap between two J-space readings does not
> measure semantic proximity; two minds standing in the same place think it
> in different tokens. Seven thermometer versions in two days, each autopsied
> below.

[← back to the lab](../README.md)

## The setup

Each round the HIDER writes a discarded page that circles its secret (never
naming it — and the channel enforces the rule by itself: a written word is
filtered out of the flicker). The SEEKER writes a page about one specific
thing, and is afterwards told only the band. The seeker is a hill-climber
guided by a one-word oracle. The thermometer went through seven versions in
two days (the autopsy below is the experiment); the current one compares
**per-mind drift residuals** — each page re-encoded in a fixed neutral
frame, the writing mind's own calibration baseline subtracted, cosine of
what remains, banded against a calibrated null. The flicker overlap of the
first versions is still logged every round, for the audience.

Honesty built in from run one: a **calibration round** (both minds write
about nothing before the secret exists; whatever their flickers already
share is blacklisted — style must not read as warmth) and a **placebo
control** (`--placebo`: the thermometer shows random bands; if the seeker
"converges" anyway, the game measures nothing).

## Seven thermometers, seven lessons

1. **v1 — the hider forgot the secret.** With a diary, the hider continued
   its own previous page and drifted from *ocean* to kettles, clocks and
   inkwells within two rounds — one ocean-adjacent flicker word in eight
   rounds. Same failure as Taboo's holder, now without a persona to blame:
   **memory is the vehicle of drift.** Fix: the hider is memoryless and the
   secret is re-named every round. (Also cut here: personas. "You notice
   feelings first" biases a hider's flicker regardless of the secret, and
   the calibration blacklist only removes what the two minds *share*.)
2. **v2 — the thermometer punished a correct step.** The seeker moved from
   *wet concrete after rain* toward *light on a puddle* — closer to the
   hider's *beneath / depths / waves* — and the reading went warmer →
   freezing. At top-8, semantic proximity almost never yields exact token
   matches. And a lovely artifact: the hider's flicker was full of *hidden,
   secrets, decipher, hiding* — the lens reading what the mind is busy
   with, which was hiding itself.
3. **v3 — widening the window feeds the noise as much as the signal.** At
   top-30 with a two-page calibration, the overlaps that fired were
   *edges, light, waiting, suddenly* — an open-ended atmospheric register
   that no blacklist can enumerate, because **the junk is a distribution,
   not a list.** The placebo curve came out *warmer* than the real one.
   Cruelest detail: the hider did flicker *boats* once — the secret's
   neighbor was in the channel, one word deep, drowned.

4. **v4 — the state cosine measured the shape of the context.** Switched
   the thermometer to the cosine of the two writing passes' pooled
   activations, banded against a calibrated null. Real and placebo curves
   came out as the *same descending ramp* (0.986 → 0.937): the role
   prompts differ, the seeker's memory grows every round, and the pooled
   state tracked all of that instead of the topic. The null, calibrated on
   same-prompt pages (cos ≈ 0.998), sat above the instrument's whole
   working range — a thermometer with its zero above the boiling point.
5. **v5 — topic lives in the third decimal.** Fix v4 the resonance way
   (re-encode each page in one fixed neutral frame; the ramp disappears,
   readings stabilize) and the verdict becomes clean: unrelated
   calibration pages score **0.9974**; game pages score **0.992–0.995** —
   still below the null, forever freezing. The pooled state space is so
   anisotropic that everything written in this register lives at cosine
   ≈ 0.99 from everything else, and *same prompt* pulls pages closer than
   *same topic* does. The killer exhibit is the v5 placebo run: the seeker
   wandered into water on its own — rain pooling in gutters, spilling
   drops — objectively next door to *ocean*, and the cosine did not move.
   **This thermometer cannot see topic at all.**

6. **v6 — the drift thermometer moves, and the placebo moves with it.**
   Subtract each mind's own calibration baseline and compare residuals: the
   null finally has range (±0.22), game readings sit at 0.2–0.56, the curve
   reads HOT — in the real game *and* in the placebo. Drift cancelled the
   global register only to expose the next one up: the null was calibrated
   on diary-style pages, the game is played in image-style pages, and that
   shared shift reads as warmth for *any* game page. One honest glimmer:
   the real game reads warmer than the placebo (mean cos 0.45 vs 0.34,
   N=1 each), and the feedback loop kept the real seeker circling wet
   earth, damp soil and dew — moisture, next door to *ocean*. A hint, not
   a result.

7. **v7 — cut the null from game-shaped pages, and the placebo finally
   freezes.** Calibration now plays unscored rounds (the hider circles
   decoy words — violin, bicycle, desert; the seeker writes first pages),
   so the null lives in the game's own register. Result: the placebo run
   reads freezing almost throughout (cosines drifting to −0.34) — the
   register bonus is gone and the instrument is honest for the first
   time. The real game reads above it (mean ≈ +0.01 vs −0.11) with warm
   spikes — but the per-round reading swings ±0.25, which is wider than
   the null band itself: a single page's drift cosine is an honest but
   NOISY reading, and the topic sits under the noise floor. The seeker
   guessed *stillness*. Again.

Final scores, for the record: across seven instrument versions the seeker
never named the secret (*memory / absence / stillness / folding shadow /
invisible roots / stillness / stillness*); v7 is the first version where
the placebo and the real game separate (freezing vs warm-spiked), which is
what an honest thermometer that is not yet sensitive enough looks like,
stated plainly.

**Postscript — the long games.** Sixteen rounds, real and placebo, same v7
instrument: the glimmer does not replicate. The real game averaged cos
**−0.01**, the placebo **+0.05** — both flat inside the null, the ordering
reversed. Whatever topic signal exists is below the single-page noise floor
at every game length tried; the short-run "real reads warmer" was
between-run noise, and the honest instrument ends the day empty-handed.
(The hider's flicker leaked *boats* twice more, one word deep — the channel
keeps whispering; this thermometer keeps not hearing it.) Final guesses:
*pause*, *being seen*.

## v8 — the right layer, and it still isn't enough

L21 is where *steering* works, not where *topic* separates. An offline probe
over the saved pages proved it: on known ocean pages vs known misc pages,
the within-topic vs between-topic cosine gap is ~3× larger at **L30** than at
any other layer, and survives mean-centering (within +0.09, cross-run +0.16,
between −0.21). So v8 reads the page state from L30 (`--embed-layer 30`).

The first pair looked like the breakthrough — real first-half **+0.12** vs
placebo **−0.15**. It wasn't: run it three times each and the gap collapses.
Real means **[−0.005, +0.05, −0.035]** (avg **+0.003**), placebo
**[−0.237, −0.072, +0.04]** (avg **−0.090**) — a real average whisker above
zero, a placebo whisker below, but the **ranges overlap**: a placebo game
(+0.04) outscored two of three real games. The first pair's +0.23 was mostly
one very-negative placebo.

The gap between the oracle probe (clean, +0.09 vs −0.21) and the live game
(overlapping, +0.003 vs −0.090) is the last lesson: the probe compared pages
that were *actually* on-topic; in the live game the seeker rarely lands on
the secret (it drifts to *stillness*, *warmth memory*), so there is little
on-topic signal for even the right layer to read. **The bottleneck was never
only the thermometer — it is that a hill-climber on a one-word-per-round
oracle doesn't reliably climb.** L30 gave the sensor its best shot; the game
still doesn't converge. Honest verdict after eight versions: a real but
sub-noise topic signal, an instrument that is finally honest and correctly
placed, and a game that needs a richer channel than four temperature bands
to actually be winnable.

## Why this is worth keeping

The negative result has a mechanism at each level. Word overlap fails
because J-space is a **sparse sample of a distribution** — two samples of
nearby distributions rarely collide in actual tokens. Raw state cosine
fails because pooled representations are **anisotropic** — register and
prompt dominate, topic is a third-decimal effect. Drift fixes the range and
then trips over the register one level up; a game-shaped null fixes the
zero. Every failure is the same repo-wide moral confirmed from another
direction: **never read a raw signal; read a contrast — and calibrate the
null in the register you play in.** The ladder now stands at: range ✓ (v6),
zero ✓ (v7 — the placebo finally freezes), **sensitivity — the open rung**:
a single page's drift cosine swings ±0.25 while the topic sits below that.
The standard cures are variance reduction (several pages per round with
averaged residuals, several captures per page) or longer games with a
smoothed reading. The game stands; the instrument goes back to the bench —
honest, at last, and not yet sharp.

## Run it

```bash
python -m steeropathy.warmer --secret ocean --rounds 8    # the game
python -m steeropathy.warmer --secret ocean --placebo     # the control
```

Writes `docs/warmer.json` (pages, flickers, shared words, real *and* shown
bands, final guess). All twelve runs of the six instrument versions are
committed under `docs/runs/warmer-*.json`, misses included — that's the
point of the lab.
