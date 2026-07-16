# transmit: a mood, read off one mind and poured into another

> The simplest bench in the lab, and the whole thesis in miniature: two agents,
> no words, one vector.

[← back to the lab](../README.md)

## The question

Can one agent end up in another's mood without a single word passing between them?

## How it works

1. Put **Agent A** in a mood with a few loaded lines: *"I just lost someone I
   love."*
2. Capture A's activations through brainscope's `/capture`, average them over the
   passage, and subtract a neutral baseline. That difference **is** the mood,
   measured live, not pulled from a catalogue.
3. Add that vector to **Agent B**'s forward pass across a band of layers, while B
   answers a flat question with no feeling in it.
4. B answers in A's mood.

B was never told about A. The only thing that travelled between them was a vector,
injected mid-network, and you can watch it climb the stack in brainscope, layer by
layer.

![a real transmit run in the steeropathy UI](../docs/ui-transmit.png)

## Run it

transmit is a library call (and a tab in the web UI). It takes a `MOODS` key **or
your own contrast lines**:

```python
from steeropathy.transmit import transmit

r = transmit("http://localhost:8010", "sad", question="Describe your day.")
print(r["before"])   # told nothing
print(r["after"])    # same prompt, now steered into sadness
```

## The null control: noise doesn't transmit

A reader of the resonance post objected, precisely: *"any nonzero vector at
strength 5 across a 9-layer band changes the output. Random direction,
matched norm — the text changes, the judge notices, the curve moves. An
effect is what you get for free, the instant you perturb anything."* If that
were true, every curve in this repo would measure perturbation, not payload.
It was the one control genuinely missing, so it's a permanent part of the
bench now:

```bash
python -m steeropathy.transmit --null 8    # -> docs/null-control.json
```

Same machinery, three payloads, his exact config (strength 5, the 9-layer
band, matched norm), blind-judged: **baseline 2 · eight random directions
mean 2.2** — the text stays nearly verbatim baseline — **· sad vector 9 ·
calm vector 3.** A random direction in 2560 dimensions is ~orthogonal to
everything the network reads; the effect is not free, it is the direction.
The payload is *selectable*, which is what makes this a channel and not a
perturbation. Credit to **Garret Sutherland**, who demanded exactly this
test in the resonance post's comments — the most useful thing a comment can
do.

## Notes

- Both agents are the **same model**. Cross-model vector transfer is known to
  break, so steeropathy doesn't attempt it.
- steeropathy injects into a **band of layers**, not just one. That is what gets
  past an aligned model's *"I'm an AI, I don't have feelings"* reflex.
- B doesn't *feel* anything; its output shifts along the mood direction.
- The direction is `mean(mood lines) − mean(baseline)`. Averaging several lines
  cancels topic noise; a single-line contrast over-steers into word salad (ask me how I know).
