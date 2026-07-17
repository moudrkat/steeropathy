# warmer: hot-and-cold through J-space — a negative result, so far

> Two neutral minds. One hides a secret thing and may never write it; the
> other seeks, writing pages about one specific thing at a time. Nobody reads
> anybody. The only thing that ever crosses is one word per round — how much
> the two minds' unwritten flickers overlap: *freezing / cold / warmer /
> HOT*. A game of hot-and-cold where the temperature is measured between
> minds.
>
> It doesn't work — yet — and the reason it doesn't is the finding: **exact
> word overlap between two J-space readings does not measure semantic
> proximity.** Two minds standing in the same place think it in different
> tokens.

[← back to the lab](../README.md)

## The setup

Each round the HIDER writes a discarded page that circles its secret (never
naming it — and the channel enforces the rule by itself: a written word is
filtered out of the flicker). The SEEKER writes a page about one specific
thing, and is afterwards told only the band. The seeker is a hill-climber
guided by a one-word oracle. The thermometer went through six versions in
one day (the autopsy below is the experiment); the current one compares
**per-mind drift residuals** — each page re-encoded in a fixed neutral
frame, the writing mind's own calibration baseline subtracted, cosine of
what remains, banded against a calibrated null. The flicker overlap of the
first versions is still logged every round, for the audience.

Honesty built in from run one: a **calibration round** (both minds write
about nothing before the secret exists; whatever their flickers already
share is blacklisted — style must not read as warmth) and a **placebo
control** (`--placebo`: the thermometer shows random bands; if the seeker
"converges" anyway, the game measures nothing).

## Six thermometers, six lessons

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

Final scores, for the record: across six instrument versions the seeker
never named the secret (*memory / absence / stillness / folding shadow /
invisible roots*); placebo curves stayed indistinguishable from real ones
— v6 finally moved the needle, but for both. That is what "measures
nothing yet" looks like, stated plainly.

## Why this is worth keeping

The negative result has a mechanism at each level. Word overlap fails
because J-space is a **sparse sample of a distribution** — two samples of
nearby distributions rarely collide in actual tokens. Raw state cosine
fails because pooled representations are **anisotropic** — register and
prompt dominate, topic is a third-decimal effect. Drift fixes the range and
then trips over the register one level up. Every failure is the same
repo-wide moral confirmed from another direction: **never read a raw
signal; read a contrast — and calibrate the null in the register you play
in.** The one remaining rung: cut the null from *game-shaped* pages (a
hider circling a different random word, an unscored seeker round — or
whole shuffled-secret games as the null distribution). Drift gave the
instrument its dynamic range; what's left is giving it the right zero. The
game stands; the instrument goes back to the bench, one rung higher than
yesterday.

## Run it

```bash
python -m steeropathy.warmer --secret ocean --rounds 8    # the game
python -m steeropathy.warmer --secret ocean --placebo     # the control
```

Writes `docs/warmer.json` (pages, flickers, shared words, real *and* shown
bands, final guess). All twelve runs of the six instrument versions are
committed under `docs/runs/warmer-*.json`, misses included — that's the
point of the lab.
