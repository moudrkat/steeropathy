# the ecosystem — a mood spreading through a silent population

> Mood contagion you can point at: one agent is made sad, and the others catch it,
> round by round, without ever reading a word.

[← back to the lab](../README.md)

## The question

Seed one agent with a mood. Left with only a wordless channel between them, does it
spread — and does the population recover, or sink?

## How it works

Four characters journal every round, all answering the **same frozen prompt at
temperature 0** — left alone, they'd write the identical entry forever. They never
see each other's words. The only channel between them is a steering vector: each
round, every agent's **drift** (its state now, minus its round-0 state) is averaged
over the others and injected into their next turn.

Seed patient zero with sadness in round one, then watch the untouched agents turn —
*"I feel like a ghost in my own body, a hollow shell"* out of a poet who started
the run happy. Because decoding is greedy and the prompt is frozen, **every change
on the page arrived through the vector channel and nothing else.**

![one agent made sad; the others catch it, round by round](../docs/eco.gif)

## Run it

```bash
python -m steeropathy.ecosystem      # 8 rounds → docs/ecosystem.json
python fig/render_eco.py             # → eco-curve.png, eco.gif, eco.mp4
```

Knobs: `--seed-mood angry`, `--patient-zero QUILL`, `--strength` (tune per model),
`--no-reseed` (the sad event happens only once — does the population recover?). The
**Ecosystem** tab in the web UI runs the same thing live, one round per click;
`#replay` animates the last saved run without a GPU.

## Notes

- What peers receive is each other's raw **drift**, not a clean mood vector. At
  high strength it degrades into repetition loops before it reads as sadness, and
  one agent's drift can score sad on the page while its vector points away from the
  seed subspace.
- Every entry is scored 0–10 by the same model, unsteered and blind (*"how sad is
  the person who wrote this?"*) — a demo metric, not a benchmark; it's the same
  model scoring its own kind.
- The cast's baselines lean deliberately **bright** — contagion is only visible in
  a population that doesn't start out gloomy.
- resonance is this experiment, plus the agents getting to **choose** whom they
  infect — and getting billed for it.
