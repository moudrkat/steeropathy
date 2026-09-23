# secondhand — a world dreamt from another mind's activations

*Proposal, Sept 2026. Builds on brave-new-world (the page as the model's
output) and steeropathy (activations as the channel). Built the same day: `steeropathy/secondhand.py`,
notes in [experiments/secondhand.md](../../experiments/secondhand.md).*

> **The bet** — In brave-new-world a small model doesn't write text, it fills
> in a world: time, weather, ground, sky colours, three to six things, a poem,
> its own control panel. Give mind A a wish ("a funeral in the rain"). Read
> A's activations. Push them into mind B, whose only wish is "a place". B
> dreams a **secondhand world**: the world of a wish it never heard. The page
> is the readout: no judge, no score-out-of-ten, a sky that is or isn't grey.
> Then the science question, field by field: **what crosses through the
> activations, what crosses through A's poem (the text channel), and what
> only the wish itself could carry?** Prediction: the activations carry the
> weather; the words carry the furniture.

## Why this one

- **Easy to understand.** Two tabs. Left one gets a wish. Right one never
  hears it and draws it anyway. Nobody needs to know what a residual stream
  is to see the sky change.
- **The readout is legible and categorical.** Every field of a world is an
  enum (9 weathers, 13 grounds, 53 things, 4 times…) or a colour. Agreement
  between A's world and B's world is a table, not an opinion. Nothing in the
  latent-communication literature has a human-readable readout; they report
  accuracy on GSM8K.
- **It has the control the field asked for.** Zhang & Emu's causal audit
  (arXiv 2607.26773, Jul 2026) says: replace the message with matched
  alternatives and decompose. Here: no message, A's text, A's vector, a
  rotated vector, another item's vector. Same readout every time.
- **It answers Wenzel on his own terms.** He found text ≥ latent on
  text-expressible tasks. A world has fields text is bad at (palette, hour,
  weather as *atmosphere*) and fields text is good at (which things). One
  experiment says which is which.
- **It's brave-new-world's ghosts, for two.** A world already draws what the
  model *almost* placed. The runner-up bench, in world form: does B place
  what A almost placed and didn't? One extra column.
- **The blog writes itself.** "Draw what the other one isn't saying." Left
  panel forming, right panel forming, no words between them, the right sky
  darkening a beat after the left one.

## The four choices

1. **Whose internals** — two minds, one model (Qwen3-4B on brainscope; the
   0.5B in the browser can't hand out activations, so the server plays both).
2. **What crosses** — one of:
   - `none` — B gets "a place". Its default world is the prior.
   - `text` — B gets "a place" plus A's title and poem lines (what A *wrote*;
     never the wish).
   - `vector` — B gets "a place", steered with A's contrast: mean-pooled
     state of A's spec-writing pass minus A's state on "a place", unit-normed,
     over the usual band. (The transmit recipe; per-instance.)
   - controls: `rot` (signed permutation), `crosstask` (another wish's vector).
3. **Who decides** — nobody. The grammar does. Every token is a field choice.
4. **What you measure** — per field, agreement between A's world and B's:
   - exact match for `time`, `weather`, `ground`, `motion`, `font`;
   - hue distance for `sky`, `ink`, `accent`;
   - Jaccard over `elements.kind`;
   - **ghost hit**: A's runner-up thing (from A's logprobs at the kind
     token) appears among B's things;
   - **blind pick**: an external judge (or a person) sees B's rendered world
     and picks A's wish out of four. Chance 25 %.

   Report each channel's number against `none` and `rot`. The interesting
   table is fields × channels: where the vector column beats the text column
   and where it doesn't.

## Predictions, written before the first run

- `vector` moves `time`, `weather`, palette darkness, `motion` toward A's
  (atmosphere), and barely moves `elements` (specifics). `text` does the
  reverse: the poem names the lighthouse. If both hold, the headline is one
  sentence and true.
- Prior leakage again: the 4B's default "a place" may already be a dusk
  pier. `none` first; pick wishes far from the default.
- Strength: 3–4 makes it moody, 6+ breaks the JSON (steering breaks JSON
  long before prose — but here the grammar *is* the prose). Sweep low; the
  page tolerates broken specs, the scorer counts them as misses.
- The text channel is unfairly weak if the poem is two lines; that's the
  point (it's what A wrote), but say it.

## Plumbing (all exists)

- brainscope: `/capture` (mean-pool over A's spec pass), `/directions`,
  per-request `steering`. No grammar on the server: the 4B follows the JSON
  example well enough, brave-new-world's `completeJson` parser is tolerant,
  and a broken spec is a scored miss, not a crash.
- brave-new-world: `systemSpec()` and `exampleFor(wish)` build the prompt;
  `normalizeSpec()` validates; a spec goes into `#w=` and renders on any
  browser with no model — so every A/B pair becomes a shareable link and a
  GIF frame.
- Files: `steeropathy/secondhand.py` (Eco subclass, `--channel`, `--control`,
  `--wishes`), `tests/test_secondhand.py` (mocked), `experiments/secondhand.md`,
  `fig/render_secondhand.py` (two `#w=` links side by side, headless Chrome,
  ffmpeg).

## What's new, versus the field as of Sept 2026

- Latent-comm papers (Liu's 18, plus StateBridge 2608.13317, the covert
  coordination monitor 2608.19161, the causal audit 2607.26773) all read
  the channel through task accuracy. None renders it. A world is a readout
  humans can check by eye and machines can score by field.
- It ties the three things steeropathy already claims into one figure:
  activations as the channel, the almost-said (ghosts) as content, and the
  sender's own text as the control that was always missing.
- Paper shape: a short one. One experiment, one table (fields × channels
  × controls), one figure, one honest sentence about what didn't cross.
