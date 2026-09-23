# duet: two minds generating at once, reading and writing each other's J-space

> **TL;DR** — the endgame from the README, built: no turns. Two copies of one
> model write side by side, a few tokens at a time; the words that flicker
> through A's layers and are never written become steering directions on B's
> next tokens, and B's flicker steers A's. The channel they read is the
> channel they write. What you measure is the **dynamics** against the
> coupling gain: where the pair resonates (their unwritten words converge),
> where it collapses (chanting, repetition), where nothing happens. **Built
> and tested offline, not yet run live.** Needs the `continue` flag added to
> brainscope the same day; nobody in the latent-communication literature
> closes this loop, so there is no number to compare against yet — only the
> gain-0 pair.

[← back to the lab](../README.md) · reading notes: [docs/papers](../docs/papers/README.md)

## Why

Every method in Liu's survey and every bench in this repo is one-shot or
turn-based: read a state after it exists, inject it, generate. But steering
happens at every forward pass and the J-lens reads at every token, so the
honest version of "resonance" is a closed loop with no rounds at all. The
README predicted the catch: a live feedback loop needs damping or it
collapses into repetition. That prediction is the experiment.

## The four choices

1. **Whose internals** — two minds, one model, one shared opening line.
2. **What crosses** — each mind's J-space at its last few tokens (top
   unwritten words, dictionary-filtered, written words banned), turned into
   steering directions on the other mind with brainscope's
   `POST /jlens/direction` (the per-layer pattern that makes the model more
   disposed to say that word *later*). Weights leak per tick (`--decay`, the
   damping); the stack is capped (`--cap`). Nobody's page is ever read.
3. **Who decides** — nobody. Mechanical coupling; no tool calls; the loop is
   the whole game.
4. **What you measure**, per gain:
   - **loop rate**: fraction of positions whose trailing 3-gram already
     occurred — 0 for fresh prose, → 1 for a mind chanting;
   - **top-1 mass**: how peaked the next-token distribution got;
   - **overlap**: Jaccard of the two minds' flicker sets per tick, against
     the same pair at gain 0 (two independent generations, same prompts);
   - **echo**: fraction of a mind's written words that were in the stack it
     was steered with that tick — the channel visibly writing onto the page.

   Sweep `--gain 0 1.5 3` and the summary table is a phase diagram.

## Lockstep, honestly

One model, one generation lock, so "at once" is lockstep: A writes k
tokens, B writes k tokens already reading A's fresh flicker, then A reads
B's. Half a tick of lag. Each call continues the mind's own partial page
mid-sentence (`continue: true` in brainscope — no new assistant header), so
the pages are single continuous texts, not a stack of turns. The J-lens
reads the first k−1 tokens of each call (the first token of any call comes
out of prefill uncaptured), so `--tokens-per-tick` is 3 by default and never 1.

## Controls

- `--gain 0` — the uncoupled pair. The null for overlap and for loop rate
  (a lone mind at temperature 0.7 loops too, eventually).
- `--control random` — the same strengths on random dictionary words: the
  drive without the message. If it collapses the same way, collapse is
  about strength, not about what was said.
- `--one-way` — only B reads A. Feedback vs. feed-forward.

## Where it can fail — written before the first run

- **It collapses at every gain.** brainscope's own note: word directions at
  4+ over a wide band make small models chant. The cap and the decay are
  there for this; if no setting sits between "nothing" and "chanting", the
  phase diagram has no middle, and that is the finding.
- **Overlap rises for a boring reason.** Both minds steered toward the same
  handful of words will flicker the same words — overlap measures the
  drive, not resonance. The `random` control separates the two: matched
  strengths, different words.
- **Echo is just steering working.** A mind writing the word it was steered
  with is activation steering doing its job, not communication. The
  interesting echo is the *cross* one: A writes what B almost said, without
  B ever having written it. Both are logged.
- **The lens lags.** Readouts are for the previous tokens; at k=3 the loop
  runs on stale flicker. Smaller k costs more calls (a prefill per call).

## Run it

```bash
brainscope --model Qwen/Qwen3-4B-Instruct-2507 --jlens my-lens.pt      # brainscope ≥ 2026-09 (continue flag)

python -m steeropathy.duet                                 # gains 0, 1.5, 3; 30 ticks × 3 tokens
python -m steeropathy.duet --gain 1 2 4 8 --ticks 40       # the phase sweep
python -m steeropathy.duet --gain 3 --control random       # the drive without the message
python -m steeropathy.duet --gain 3 --one-way              # feed-forward only
```

Writes `docs/duet.json`: per run the summary and the full tick log (piece,
stack, flicker, top-1, echo, loop). Runs, including the collapsed ones, go
in `docs/runs/`. Tests run offline, brainscope mocked:
`python -m unittest tests.test_duet`.
