# handoff: agents passing slider settings, as one vector

**TL;DR.** [secondhand](secondhand.md) pushed one mind's whole page-state
into another and the poem carried more: the encoder was a mean-pooled
contrast of a whole page, a blunt message. Here the message is written on
purpose. Mind A gets a brief (*a dark forest full of birds*) and a catalogue
of [sliders](worldof.md), directions with a readout on the page (trees, birds,
stars, cats, houses, crowded, dark, night). A sets them in a sober JSON call.
The settings become one vector, strength × unit direction summed, added
into mind B, which is told only *a place*. B draws, and the page says how
much of A's message arrived. Built 2026-09-27; first run on the 1.5B in
progress.

[← README](../README.md) · the sliders themselves: [worldof](worldof.md)

## The four choices

1. **Whose internals:** two minds, one model. A decides, B is pushed.
2. **What crosses:** a vector that is a sum of named sliders. A never
   writes a word to B.
3. **Who decides:** A, unsteered, in JSON (decisions are sober, as always
   here): `{"manytrees": 2, "darker": 1}`, each slider −3 to 3.
4. **What is measured, against what.** Per slider A turned: did B's reading
   (trees per world, things per world, the sky's darkness, night or not)
   move the way A set it, against B's own baseline (the mean of the run's
   unsteered worlds)? **Fidelity** = the share of turned sliders that arrived.
   Four channels: `none` (baseline), `vector`, `text` (the same settings as
   a sentence in B's prompt: *Make it more trees, darker.*), `placebo` (the
   same vector, coordinates shuffled).

## Prediction, written before the first run

Text carries the count sliders (a sentence that says *more birds* is easy to
obey); the vector carries the continuous ones (darkness) and loses the
counts; the placebo sits near the coin. If the vector matches text here,
the channel was never the problem in secondhand, the encoder was.

## Run it

```bash
python -m steeropathy.handoff --briefs 16 --out docs/runs/handoff-01.json
python -m steeropathy.handoff --rescore docs/runs/handoff-01.json
```

Writes per brief: A's settings and what it said, and per channel B's world,
its readings per slider, and a link that renders it. Tests run offline:
`python -m unittest tests.test_handoff`.
