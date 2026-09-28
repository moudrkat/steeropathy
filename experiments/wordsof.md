# wordsof: a slider made of words

**TL;DR.** [vocabmap](vocabmap.md) put names on the map: every token has a
steering direction through the J-lens. This turns it around: a slider is
asked for as a few words (*bustling*; *quiet, winter, −loud*), the token
directions are stacked, and the page is the readout, against the
unsteered place, the same number of random words at the same strength
(the placebo), and the words written into the prompt instead (the text
channel). Built 2026-09-28; first sweep queued on Qwen3-4B behind
cross-4b. Smoke test, one world: *bustling* at 1.5 drew five things and a
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

## Run it

```bash
python -m steeropathy.wordsof bustling --url http://localhost:8011 --n 8 --strength 1.5
python -m steeropathy.wordsof quiet winter ~loud --url http://localhost:8011 --n 8
```
