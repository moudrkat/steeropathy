# runner-up — does the answer a mind didn't give survive in what it never said?

*Proposal, Sept 2026. Grew out of the five papers in this folder. Built the same day:
`steeropathy/runnerup.py`, notes in [experiments/runnerup.md](../../experiments/runnerup.md).*

> **The bet** — When a mind has to commit to one word, the alternative it
> almost said is gone from its text and (maybe) still in its layers. Three
> channels carry the same sender to the same reader: the sender's **text**
> (its one word), its **J-space** (what flickered while it wrote the word), and
> a **vector** (its state at the answer, pushed into the reader). The reader
> points at the runner-up. Text cannot carry it by construction; the question
> is whether the other two do — and whether they beat the reader's own prior.
> If they don't, that is Wenzel's negative reproduced in our register, and it
> goes in the README too.

## Why this experiment (the papers, in one line each)

- **Wenzel**: text ≥ latent on every text-expressible task; latent can only win
  on what text cannot express. He never tested the discarded alternatives.
- **Liu §4.1.2**: the hidden state holds "the alternatives considered, their
  relative probabilities … lost the moment we sample a single token."
- **Du**: "premature collapse" — inferred from MATH Level-5, never measured.
  Their top-k mass spread is the readout.
- **Zhang §3.5 + refusal cliff**: J-lens is a vocabulary projection; something
  present mid-stream and gone at emission is the shape to look for.
- **Singh**: the per-instance push is a mean-difference translation; gate it
  by distance; judge it by guardedness if you want a probe-based number.

And the missing control in this whole repo: **the sender's own text** as a
channel condition. This bench has it built in.

## The four choices

1. **Whose internals** — two minds, SENDER and READER, one model (Qwen3-4B on
   the brainscope box, J-lens on, traces on).
2. **What crosses** — one of:
   - `text`: the sender's one committed word. What any text MAS would pass.
   - `jspace`: top-k J-lens words from the sender's *answer pass*, the written
     word stripped (unsaid's `_flicker`, one turn, one position).
   - `vector`: the sender's residual state at the answer position, its own
     calibration baseline subtracted (the warmer lesson: read a contrast),
     unit-normed, pushed into the reader's page-writing pass at strength s.
   - `none`: the reader sees only the task. **The base-rate null** — same
     model on both sides, so the reader's own ranking is the prior the channel
     has to beat.
3. **Who decides** — nobody in the channel. The reader writes a short page
   (steered, in the vector condition), then makes one **unsteered** tool call
   `point(word)`: decided drunk, transcribed sober. This is the queued
   "deciding under the influence" fix, used for the first time.
4. **What you measure** — P(reader points at the sender's runner-up) per
   channel, with a binomial CI, against `none` and against the controls.
   Secondary: the reader's own answer distribution under each channel (does
   the vector keep it torn? Du's top-k mass), and whether the reader can tell
   *that* the sender was torn (sender entropy high vs low items).

## The item

The sender needs a real, item-specific runner-up that the reader cannot read
off the task. Draft:

- Sender prompt = a public question + a **private line** the reader never sees
  (a persona or a scene detail that shifts the ranking, e.g. "You grew up by
  the sea." / "Your last project failed loudly."). Question: "One word: what
  should the team's mascot be?" Answer with exactly one word.
- **Ground truth is free**: the sender's logits at the answer token. Winner =
  top-1 (its text), runner-up = top-2. Candidate set for the reader = sender's
  top-5 at that position, shuffled, winner shown only in the `text` condition.
- Keep items where the sender's top-2 margin is small (it was actually torn)
  and where the private line *moved* the ranking vs. the same question without
  it (otherwise the reader's prior already knows the answer).
- 40–60 items × 4 channels × controls. One-word answers and short pages: cheap.

## Controls (from run one, as flags)

- `--control none` — the base rate. Report it first.
- `--control crosstask` — J-words / vector from a different item (Du).
- `--control rot` — random orthogonal rotation of the real vector: same norm
  and spectrum, no meaning (Du's RandomRot; stronger than matched-norm noise).
- `--control logit` — the plain logit-lens top-k at the same position instead
  of the J-lens. If it does as well, "J-space" was a k-bit text channel in
  disguise. That is a result, not a failure.
- Sender-side: the same item without the private line, to show the ranking
  actually moved.

## Where it can fail (say it in the TL;DR if it does)

- **Prior leakage.** One model on both sides: the reader may rank the
  candidates the way the sender did, from the question alone. Then every
  channel ties with `none` and the honest finding is "nothing crosses that
  the reader didn't already think." Wenzel's negative, in our register.
- **The J-lens at the answer position is the logit lens.** Then the channel is
  five words of text. The `logit` control decides this.
- **The vector says the winner, not the runner-up.** The pushed state's
  strongest component is the word it wrote; the reader may collapse onto it.
  Measure both; the reader repeating the winner is the collapse happening
  again one mind later — write that up.
- **Per-instance vectors are noisy** (Wenzel: prompt-averaging closes half the
  gap). Mitigate: average the answer-position state over 3–5 paraphrases of
  the sender prompt before subtracting the baseline.
- **Steering breaks the page.** Free text only under the vector; strength swept
  low; the decision turn is sober.

## Files (house layout)

- `steeropathy/runnerup.py` — `RunnerUp(Unsaid)`: reuses `_flicker`, `post`,
  `get`; adds `capture` at the answer position, per-item direction, the four
  channels and the controls as `--channel` / `--control`. Writes
  `docs/runnerup.json`.
- `tests/test_runnerup.py` — brainscope mocked; test candidate building,
  channel assembly, the rotation control (norm preserved, cosine ~0), scoring.
- `experiments/runnerup.md` — TL;DR first; the papers as the "why"; the
  autopsy as it happens.
- `docs/runs/runnerup-*.json` — every run, including the failed ones.
- README: table row; the text-channel line in Honest notes; four references.

## Not this experiment (queued separately)

- Singh's affine push (covariance matching) and the guardedness metric — an
  instrument upgrade for transmit/resonance, not a new bench.
- Zhang's side-effect line for mood pushes (coherence, over-refusal).
- The token-by-token live loop stays the endgame; runner-up is turn-based.
