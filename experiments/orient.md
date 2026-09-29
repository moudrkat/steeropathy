# orient: the model finds its way around its own space

**TL;DR.** [vocabmap](vocabmap.md) named the sliders with the model's
vocabulary; [wordsof](wordsof.md) turned a few given words into a slider.
This takes the person out. The map is saved once per model
(`tokenmap.py`: every readable word as a unit direction at layer 21 of
the 4B, 35,771 words) and on it there are four tools and nothing else:
**words** (read any vector as words), **vector** (a few words → a
direction), **near** (a word's neighbours on the map), **try** (turn the
words on the page and read it back). Two users of the tools: `search`, a
fixed procedure that starts from the brief's own words, walks to their
neighbours, tries each on the page and keeps what moves the target
reading (nobody's decision; the offline pass that fills a dictionary);
and `agent`, the same 4B given the tools and a budget of eight calls,
picking the words itself. Both end the same way, eight worlds each:
nothing added, the recipe found, as many random words at the same
strength, and the brief written into the prompt. Built 2026-09-29; runs
queued after the 4B sweep. *Results: pending.*

[← README](../README.md) · the map: [vocabmap](vocabmap.md) · words as sliders: [wordsof](wordsof.md)

## The four choices

1. **Whose internals:** the 4B (the only model with a J-lens), steered;
   the agent is the same 4B in a sober JSON call per turn, unsteered.
2. **What crosses:** a recipe of words with signs (*haunting cavern*,
   *quiet winter ~loud*), stacked as token directions at the server's
   band (layers 15–19 of 36), strength 1 to 3 per word. The map used for
   `near` and `words` is at layer 21 (where the sentence sliders were
   captured); the steer band is the server's own. That mismatch is noted,
   not fixed.
3. **Who decides:** `search`: nobody; `agent`: the model, with a budget.
4. **What is measured, against what:** one reading per brief, off the
   page: *darker* → sky brightness (down), *night* → hour (up), *crowded*
   → things per world (up), *winter* → share of worlds with snow (up),
   *warmer* → sky warmth (up). Against the unsteered page, random words,
   and the brief as text.

## Prediction, written before the runs

`search` finds a word that moves each reading on *darker*, *night* and
*crowded* (the map has *dark*, *night*, *crowded* on it and their
neighbours), and the random words do not. *Winter* is the hard one: the
neighbours of *winter* on the map are *summer, autumn, january, snow*,
because the map groups by topic, not by polarity; `search` will find that
out by trying. The brief in the prompt beats every recipe, as the text
channel has on every bench so far. The `agent` picks fewer words than
`search` tries and lands near the same place, or wanders into `near` and
runs out of budget; either is written down.

## Run it

```bash
python -m steeropathy.tokenmap --lens lenses/qwen3-4b-instruct-2507.jlens.pt --unembed <shard> --tokenizer <dir> --layer 21 --out data/tokenmap-qwen3-4b-l21.pt
python -m steeropathy.orient near haunting winter
python -m steeropathy.orient words docs/runs/directions-qwen3-4b-instruct-2507.json crowded
python -m steeropathy.orient search darker --url http://localhost:8011 --n 3 --final 8
python -m steeropathy.orient agent darker --url http://localhost:8011 --budget 8
```

Tests run offline: `python -m unittest tests.test_orient`. The map file is
180 MB and stays out of git.
