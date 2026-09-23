# runner-up: does the answer a mind didn't give survive in what it never said?

> **TL;DR** — a sender must answer with one word; a reader tries to point at
> the word it *almost* said. Four channels on the same pair: nothing, the
> sender's **text** (its one word), its **J-space** (what flickered while it
> wrote the word), a **vector** (its state at the answer, pushed into the
> reader). Text cannot carry the runner-up by construction, and the reader's
> own prior (same model on both sides) is the null. **Built and tested
> offline, not yet run live** — no numbers here until it is. This is the
> first bench in the repo where the sender's own text is a condition, which
> is the control every other bench is missing.

[← back to the lab](../README.md) · reading notes that led here:
[docs/papers](../docs/papers/README.md)

## Why

Five papers, one argument. Wenzel (2026) compared a latent channel between
two agents against the sender's own text and found **text wins or ties on
every task he tried** — what text destroys is surface form, not semantics.
He also says where latent could win: on what text cannot express. Liu's
survey names it: a hidden state holds "the alternatives considered, their
relative probabilities … lost the moment we sample a single token." Du
(Interlat) calls it "premature collapse" and infers it from an accuracy
inversion, never measuring the alternatives themselves.

The alternatives the sampler threw away are exactly what the J-lens reads
and what the resonance/unsaid benches have been passing around. So: the
smallest possible test of the thesis, with the text channel in the room.

## The four choices

1. **Whose internals** — two minds, one model. SENDER and READER.
2. **What crosses** — one of:
   - `none` — the reader sees the question and four candidates. Same model on
     both sides, so its own ranking is the prior. **Report this first.**
   - `text` — plus the winner. What any text multi-agent system would pass.
   - `jspace` — plus the words that flickered through the sender's layers
     during its answer pass, the written word stripped (the unsaid readout,
     one turn, one position).
   - `vector` — plus a push: the sender's residual state at the answer token
     minus its state on the same question *without* the private line (read
     a contrast, never a raw signal), unit-normed, added into the reader's
     page-writing pass over the usual band of layers.
3. **Who decides** — nobody in the channel. The reader writes a two-sentence
   page (steered in the vector channel) and then points with an **unsteered**
   tool call: decided drunk, transcribed sober. First use of the fix queued
   in the README's "deciding under the influence".
4. **What you measure** — P(reader points at the sender's runner-up), per
   channel, chance 1/4. Reported on all items and on the **moved** subset:
   items where the private line changed the sender's top-2, i.e. where the
   reader's prior cannot already know.

## The item

Sender prompt = a public question ("One word: a mascot for the night
shift.") plus a **private line** the reader never sees ("You grew up by the
sea."), answered as `Answer: <word>`. The ground truth is free: the top-5 at
the answer token, read off the logprobs — top-1 is the winner (its text),
top-2 the runner-up. The same question without the private line is run too,
so each item knows whether the private line moved the ranking. Forty items
ship in `ITEMS`; the candidate list the reader sees is the sender's own
top-5 minus the winner, dictionary-filtered, shuffled.

## Controls (flags from run one)

- `--control crosstask` — the reader gets another item's flicker / vector.
- `--control rot` — a random signed permutation of the vector: orthogonal,
  so same norm and same steering knobs, no meaning (Du's RandomRot, stdlib
  edition).
- `--control logit` — the plain logit lens at the same steps instead of the
  J-lens. If it does as well, "J-space" was a five-word text channel in
  disguise. That is a result, not a failure.

## Where it can fail — written before the first run

- **Prior leakage.** One model on both sides may rank the candidates the
  same way from the question alone. Then every channel ties with `none`
  and the honest finding is "nothing crosses that the reader didn't already
  think" — Wenzel's negative, in this register. The `moved` subset is the
  defence; if it is empty, the items need stronger private lines.
- **The J-lens at the answer position is the logit lens.** The `logit`
  control decides.
- **The vector says the winner, not the runner-up.** The pushed state's
  strongest component is the word the sender wrote; the reader may collapse
  onto it (it cannot point at it — the winner is not an option — but its
  page will show it). That would be the collapse happening again one mind
  later; write it up.
- **Per-instance vectors are noisy** (Wenzel: prompt-averaging closes half
  the latent–text gap). The obvious upgrade is averaging the answer state
  over paraphrases of the question; not built yet.
- **Steering breaks the page.** Free text only under the vector; sweep
  `--strength` low; the point is always sober.

## Run it

```bash
# brainscope with the J-lens for the jspace channel; the rest needs only the model
brainscope --model Qwen/Qwen3-4B-Instruct-2507 --jlens my-lens.pt --traces traces

python -m steeropathy.runnerup                                  # 40 items, all four channels
python -m steeropathy.runnerup --items 20 --control rot         # the vector placebo
python -m steeropathy.runnerup --channel jspace --control logit # J-lens vs logit lens
```

Writes `docs/runnerup.json` (per item: the sender's ranking with logprob
margin, whether it moved, the flicker, each channel's page and point) and
archives the traces. Runs, including failures, go in `docs/runs/`.

Tests run offline, brainscope mocked: `python -m unittest tests.test_runnerup`.

## References

The five reading notes in [docs/papers](../docs/papers/README.md):
Wenzel 2026 ([2607.14103](https://arxiv.org/abs/2607.14103)), Liu 2026
([2606.05711](https://arxiv.org/abs/2606.05711)), Du et al. 2026
([2511.09149](https://arxiv.org/abs/2511.09149)), Singh et al. 2024
([2402.09631](https://arxiv.org/abs/2402.09631)), Zhang et al. 2026
([2601.14004](https://arxiv.org/abs/2601.14004)).
