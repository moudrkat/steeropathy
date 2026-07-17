---
name: new-experiment
description: >-
  Scaffold a new steeropathy experiment — agents that communicate through
  model internals (activations and J-space) instead of text. Use when the
  user wants to build, add, design, or wire up a new experiment/game/probe
  in this repo (e.g. "let's have fun with agents who never see each other's
  output", "add an experiment where…", "make a new bench"). Encodes the
  house patterns, the plumbing to reuse, and the honesty conventions every
  experiment here follows.
---

# Build a new steeropathy experiment

steeropathy is a lab for agents that talk through **model internals**, never
text: one agent's state is read off its activations (or its **J-space** — the
words forming in its layers that never become tokens) and either measured or
pushed into another agent's forward pass. Every experiment is a **probe, not
a product** — the goal is a reproducible existence-proof you can play with,
run honestly with controls, and write up including the failures.

Read the closest existing bench before writing a new one — they are short and
each is a set of answers to the same four questions:

- `steeropathy/transmit.py` — the thesis in ~15 lines: read a mood off one
  agent, push it into another. The direction/injection/before-after core.
- `steeropathy/ecosystem.py` — `Eco`: a population, per-round `step()`, the
  `post`/`get`/`_state_of` plumbing everything else subclasses.
- `steeropathy/resonance.py` — `Reso(Eco)`: ledgers, transfer/conservation,
  the J-space channel, an unsteered decision turn.
- `steeropathy/unsaid.py` — `Unsaid`: the pure J-space channel (`_flicker`),
  no steering at all — only reading.
- `steeropathy/warmer.py`, `steeropathy/zombie.py` — a hot-and-cold game and
  a refusal-outbreak game built on the above.

## The four choices that define an experiment

1. **Whose** internals you read — one agent, a pair, a room of N.
2. **What** crosses — a mood/concept vector, a scalar on one axis, the
   J-space word cloud, a similarity, or nothing (read-only).
3. **Who** decides — nobody (mechanical rules), or agents choosing via an
   **unsteered** tool call (steering breaks JSON long before prose).
4. **What** you measure — and against **what control**.

## The plumbing to reuse (don't reinvent)

- Subclass `Eco` (or `Unsaid`) for `self.post(path, body)` / `self.get(path)`
  against brainscope. Write a custom `__init__` (like `Reso`) — don't call
  `super().__init__` if you don't want its mood seed.
- **Build a direction** from the model's *own* contrast, not a baked vector:
  `capture_mood(url, texts)` returns `mean(texts) − neutral`, unit-normed, at
  a good layer. For a custom axis, mean-pool `/capture` over two prompt sets
  and subtract. Register it with `POST /directions {name, vector}` and steer
  with `{"name", "strength", "layer_from", "layer_to"}` in the chat body.
- **Read J-space** from the generation's trace: tag each call with
  `metadata:{demo, case, variant}`, then match it in `GET /traces`, fetch
  `GET /traces/{id}`, and walk `trace["jlens"]` for `{t, p}` tokens. Filter
  with a dictionary + stopwords (see `unsaid.STOP`/`WORDS`), or a task
  lexicon (see `zombie.REFUSE_WORDS`).
- Enable the J-space channel once with `POST /jlens {"on": true}`; if it
  fails, the server has no lens — degrade, don't crash.

## The honesty conventions (these are the point)

- **Read a contrast, never a raw signal.** A raw pooled state is anisotropic
  — register and prompt dominate, topic is a third-decimal effect. Subtract a
  baseline (round-0 state, or the agent's own calibration) and compare
  residuals. This lesson recurs in every experiment; assume you'll need it.
- **Calibrate the null in the register you play in.** If you band a
  similarity into levels, cut the thresholds from a control that is *shaped
  like the game* (unrelated pages written the same way), not from generic
  text.
- **Always ship a placebo/null control.** Shuffle the channel, use a random
  matched-norm vector, or scramble the readout. If the experiment does as
  well with the signal destroyed, it measures nothing. Make the control a CLI
  flag from run one (`--placebo`, `--null`).
- **The in-model judge saturates.** A model scoring its own kind rates
  everything alike. Judge coherence/quality **externally and blinded** (shuffle
  true pairs with rotated controls, hide the keys), and report the **gap**,
  not the raw score.
- **Negative results are results.** If it doesn't work, find the *mechanism*
  of why and write it up — half this repo is documented instrument failures.
  Never bury a failed run; commit it under `docs/runs/`.
- **Decisions are unsteered.** Journals/answers carry the vector; the tool
  call that chooses is sober.
- **Sensitive triggers: measure the STATE, store no bodies.** If a probe uses
  a refused/harmful request, use a *benign, low-stakes* trigger (a policy
  refusal like "recommend a stock", never weapons/CBRN), cap `max_tokens`,
  read only the refusal *state* (J-space markers / direction cosine), and
  write **no completion text** to any committed file. Verify the mechanism as
  a judge by reading outputs ephemerally in a scratchpad — never commit them.

## Files to create (match the repo layout)

- `steeropathy/<name>.py` — the experiment class + a `main()` CLI with
  `--url`, `--out`, and the control flag. Writes `docs/<name>.json` (params +
  per-round log). Module docstring explains the channel and the honesty.
- `tests/test_<name>.py` — brainscope **mocked** (see `tests/test_zombie.py`,
  `test_unsaid.py`): stub `post`/`get`/`_flicker`, test the mechanics, the
  classification, the control, and any parsing. No server in tests.
- `experiments/<name>.md` — the bench notes in the house voice: the setup,
  what each instrument version taught (the autopsy *is* the experiment), the
  honest gaps, and how to run it. Link back to `../README.md`.
- `fig/render_<name>.py` — optional figure: HTML frames shot with headless
  Chrome, stitched with ffmpeg (copy `fig/render_unsaid.py`). Whitelist the
  gif in `.gitignore`.
- Add a row to the experiments table in `README.md`.
- Runs (incl. failures) go in `docs/runs/`; archived traces are gitignored.

## Running it

Two processes: brainscope hosts the model + internals (`--jlens <lens.pt>
--traces <dir>` for the J-space channel); steeropathy talks to it over HTTP.
Live runs need a real brainscope; tests never do. Decisions are sampled
(temperature > 0) so runs differ — commit one and say so.

## The voice of the write-up

Plain, short, honest, invite-to-play. State what works AND what doesn't. One
figure beats a carousel. If the finding is "my instrument lied to me again,"
that's the best kind — say it plainly.
