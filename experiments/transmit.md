# transmit: a mood, read off one mind and poured into another

> **TL;DR** — the simplest bench in the lab, and the whole thesis in miniature:
> capture one agent's mood off its activations, inject it into another's
> forward pass, and the receiver answers a flat question in the sender's mood.
> At temperature 0 with a frozen prompt the vector is the only difference
> between its two answers, so the transfer is real — but it is plain
> activation steering wearing an agent costume, not a new mechanism.

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

He followed with two sharper nulls, both run the same night:

- **Register, not mood?** Push *certainty* (structured, zero emotion, first
  person — the README's own example lines) and see if the sadness judge
  climbs anyway. It doesn't: sad = 3 (baseline 2; the sad vector gives 9),
  and the output turns confident instead. At full-room scale (his exact
  prescription — certainty seeded into the contagion experiment, sadness
  judged blind): the sad seed takes patient zero to 10 and the others from
  0.7 to 9.3 over six rounds; the certainty seed leaves the sadness curve
  at a flat **zero** for seven rounds. The payload delivered is the payload
  chosen.
- **Grammatical person, not emotion?** The mood lines are first person; the
  neutral baseline lines aren't — so every mood vector carries an "I vs.
  impersonal" component. Re-extracted against a *first-person factual*
  baseline ("I have a meeting at 3pm on Tuesday…"), every pairwise mood
  cosine drops by ~0.1 (0.57–0.76 → 0.46–0.68). Person is real — about a
  seventh of the shared axis — and the axis survives. His baseline is
  simply the better recipe, and worth adopting.

## Notes

- Both agents are the **same model**. Cross-model vector transfer is known to
  break, so steeropathy doesn't attempt it.
- steeropathy injects into a **band of layers**, not just one. That is what gets
  past an aligned model's *"I'm an AI, I don't have feelings"* reflex.
- B doesn't *feel* anything; its output shifts along the mood direction.
- The direction is `mean(mood lines) − mean(baseline)`. Averaging several lines
  cancels topic noise; a single-line contrast over-steers into word salad (ask me how I know).
