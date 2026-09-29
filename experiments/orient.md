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
strength, and the brief written into the prompt. Built 2026-09-29. First brief, *darker*, on the 4B: **`search` found
*darkest, darkness, darken* and took the sky from 0.73 to 0.15** (three
random words at the same strength: 0.32; the brief in the prompt: 0.12);
**the `agent` picked *sky, petals* and brightened it, 0.67 → 0.87.** It never
called `near`, tried only page words (*sky, clouds, bubbles*), watched every
try go the wrong way, and said done. The dumb search finds it; the 4B with
the tools does not, yet. Night, crowded, winter, warmer running.

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

## What came out (`orient-01`, Qwen3-4B, eight worlds per condition at the end)

| brief | who | recipe | reading | nothing | random words | brief as text |
|---|---|---|---|---|---|---|
| darker (sky brightness ↓) | search | *darkest darkness darken* @1.5 | **0.15** | 0.73 | 0.32 | 0.12 |
| darker | agent | *sky petals* @1.5 | 0.87 | 0.67 | 0.61 | 0.14 |

Readings:

- **The search works and half of it is a push.** Three stacked token
  directions at 1.5 each is a lot: three random words already halve the
  sky's brightness (0.73 → 0.32). The found words take the rest (→ 0.15),
  and the brief written into the prompt does the same (0.12). Single words
  on the way: *darkest* 0.22, *darkness* 0.29, *dark* 0.37, *darker* 0.42,
  *colder* 0.42; *brighter* 0.87, *makeup* 0.86.
- **The first search wasted twenty tries on grammar.** The seeds were every
  word of *make the place darker* that is on the map, so *make, the, place*
  and their neighbours (*makeup, lugares, that*) got tried before *dark*.
  Fixed: a brief now names its content words (`seeds`).
- **The agent never looked at the map.** In eight calls it did not call
  `near` once; it tried *sky ~petals*, *clouds*, *sky*, *bubbles ~clouds*,
  saw the reading rise every time (the brief said it should fall), and
  answered done with *sky, petals, fireflies*. It reasons about the page's
  fields, not about directions, and does not read its own results. A
  bigger model as the agent is the obvious next run; on the 4B, the
  procedure with nobody deciding is the one that finds the words.

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
