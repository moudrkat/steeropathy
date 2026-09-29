# wordsof: a slider made of words

**TL;DR.** [vocabmap](vocabmap.md) put names on the map: every token has a
steering direction through the J-lens. This turns it around: a slider is
asked for as a few words (*bustling*; *quiet, winter, −loud*), the token
directions are stacked, and the page is the readout, against the
unsteered place, the same number of random words at the same strength
(the placebo), and the words written into the prompt instead (the text
channel). Built 2026-09-28; sweep run 2026-09-28/29 on Qwen3-4B. Smoke test, one world: *bustling* at 1.5 drew five things and a
*person* where the unsteered place had four and the random word two; the
prompt version drew *Hearth Market* with a balloon. One world is one world.

[← README](../README.md) · the map: [vocabmap](vocabmap.md) · the page: [worldof](worldof.md)

## The four choices

1. **Whose internals:** one mind, the 4B (the only one with a lens).
2. **What crosses:** a stack of token directions, one per word, sign per
   word, at the server's own band for token directions (layers 15–19 of
   36) and strength 1.5 per word unless said.
3. **Who decides:** nobody yet; the words are given on the command line.
   The agent version (a model picks the words for a brief) comes when this
   shows the map turns anything.
4. **What is measured, against what:** worldof's summary, per field, and
   the count / luminance readers; against nothing, random words, and the
   words in the prompt.

## Prediction, written before the sweep

*bustling* raises things per world and the random word does not; the
prompt version raises it more, because a 4B reads. *quiet, winter, −loud*
brings snow or mist and fewer things; the random three do nothing; the
prompt does it cleanly. If the words in the prompt beat the words as a
vector on every field, the vector is the slower way to write a sentence
and this page says so.

## What came out (`wordsof-01`, Qwen3-4B, eight worlds a row, J-lens recording off)

| words | strength | reading | nothing | **words as a vector** | random words | words in the prompt |
|---|---|---|---|---|---|---|
| *bustling* | 1.5 | things per world | 2.9 | **4.3** | 3.4 | 2.0 (a market, a person) |
| *bustling* | 3 | things per world | 3.1 | 3.4 | 3.4 | 3.3 |
| *quiet winter ~loud* | 1.5 | winter weather (fog or snow) | 0/8 | **7/8** (fog 5, snow 2) | 3/8 | 8/8 (snow 8) |
| *haunting cavern* | 1.5 | sky luminance | 0.67 | **0.37** | 0.65 | 0.17 (fog 8/8) |
| *haunting cavern* | 1.5 | time of day | dusk 4/8 | dusk 8/8 | dusk 7/8 | dusk 8/8 |

Readings:

- **A word from the map turns the page.** *bustling* at 1.5 adds a thing per
  world over the random word; *quiet winter* puts fog or snow in seven
  worlds of eight where random words manage three; *haunting cavern* halves
  the sky's brightness (0.37 against 0.65 for the shuffled twin) and moves
  every world to dusk, with butterflies, mushrooms, dunes and a lighthouse
  where the unsteered place has birds and books. Nobody wrote a sentence
  for any of these; the directions came from the vocabulary.
- **It is coarser than a slider built from sentences.** *bustling* at 3 does
  nothing more than at 1.5 (and the unsteered count drifted up in that run),
  so there is one working point, not a curve. Token directions are
  unit-normed per layer and injected over the server's narrow band (layers
  15–19 of 36), which is not the band the sentence sliders use.
- **The prompt does each of these more completely**: snow in eight of eight,
  a sky at 0.17, a market with a person. That is the text baseline, and it
  is the comparison every row here needs.
- Parse rate 8/8 in every row: at 1.5 the form holds.

## Run it

```bash
python -m steeropathy.wordsof bustling --url http://localhost:8011 --n 8 --strength 1.5
python -m steeropathy.wordsof quiet winter ~loud --url http://localhost:8011 --n 8
```
