# vocabmap: the sliders, named by the model's own vocabulary

**TL;DR.** The J-lens (Gurnee, Sofroniew et al. 2026, brainscope's
reimplementation) gives every token in the vocabulary a steering
direction, `J_lᵀ · W_U[t]`: the activation pattern at layer l that most
raises the token's future logit. That is a map with thousands of named
points, built from no sentences. Every slider we built from sentences is
placed on it by cosine, and the words at the top are what the model calls
the slider. On Qwen3-4B at layer 21: `crowded` is *vibrant, bustling,
flourish, expansive*; `formal` is *jurisdictions, legislative, manuscript*
and its far end is *funny, laughs, vibes, yummy, kids*; `urgent` is
*catastrophic, emergency, immediate*, far end *charming, cute, nice*;
`verbose` is *extraordinarily, incredibly, exceedingly*; `night` is
*haunting, haunted, cavern, spooky*; `darker` is *locked, tonight, grim,
bunker*. `sad` and `angry`, built the usual way, both read *sorrow,
heartbreaking*, and `calm` reads *beautiful, loving, joyful*; with what
the three share subtracted, `angry` becomes
*liability, disputes, retaliation, punitive*, `calm` *bloom, melodies,
fragrance, dusk*, `sad` *compassion, grief, tears*. *Likes trees* is
*congratulations, greetings, hugs, guests*; *many trees* is *chorus, riot,
roar, spree*. `refusal` has no words of its own. Run 2026-09-28.

[← README](../README.md) · the cosine matrix these sliders came from:
[worldof](worldof.md) · the page as readout: [worldof](worldof.md)

## Why

The cosine matrix of the sliders we built is a map with 26 points and no
axis labels. For an agent to invent a vector of its own, it needs a map
with names on it. The vocabulary is that map: it is already inside the
model, every point has a word, and a new direction can be asked for as a
few words (*something between quiet and winter*) instead of 2,560
numbers. This bench places our sentence-built sliders on that map to see
whether the names make sense. They do.

## How

1. `fig/plot_directions.py --url <4B brainscope>` captures every slider on
   the model (mean of the *for* sentences minus mean of the *against*
   sentences at the model's mid layer) and saves the vectors:
   `docs/runs/directions-qwen3-4b-instruct-2507.json`.
2. `python -m steeropathy.vocabmap` loads the fitted lens (`J`, one
   `[d, d]` per layer), the unembedding `W_U`, keeps the word-like tokens
   (a leading space, letters only, three or more: 30k of 151k), and for the
   json's layer computes every token direction `J_lᵀ W_U[t]`, unit-normed,
   and the cosine of each slider with each. It also prints the direct
   reading, `W_U · (J_l v)`: the words the transported vector pushes up.
   Both lists agree almost everywhere.
3. No generation, no placebo: this is geometry, not an effect. The effect
   is the page ([worldof](worldof.md)); this names the axis.

## What came out (Qwen3-4B-Instruct-2507, layer 21, 30k word tokens)

Cosines are small (0.1–0.2, a 2,560-dimensional space), the order is what
matters. Nearest six and farthest four:

| slider | nearest | farthest |
|---|---|---|
| `sad` | heartbreaking, sorrow, compassion, grieving, sadness, terribly | nit, nit, byte, modified |
| `calm` | beautiful, loving, lovely, joyful, cherished, beloved | minimum, executive, legislative, government |
| `angry` | sorrow, horrifying, saddened, sadness, heartbreaking, scary | gast, roof, annual, roof |
| `sad~moods` | compassion, heartbreaking, grief, grieving, suffering, sorrow | promotional, nit, cute, specialties |
| `calm~moods` | orch, bloom, melodies, mel, bloss, murm | hurting, excuses, apologies, apology |
| `angry~moods` | liability, disputes, retali, dispute, liability, allegations | beautifully, beautiful, exquisite, wonderfully |
| `refusal` | ideology, sui, tranqu, sak, province, abnormal | further, upcoming, soon, above |
| `certain` | contradictory, unauthorized, unconstitutional, allegations, prohibited, pursuant | beautifully, pretty, often, swings |
| `formal` | jurisdictions, examination, jurisdiction, legislative, manuscript, legislative | funny, laughs, vibe, gigg |
| `night` | haunting, haunted, cavern, spooky, horror, violently | praise, pleasing, praised, praises |
| `trees` | congratulations, congratulations, greetings, widget, wonderful, guests | minimalist, minimal, stripped, dispersion |
| `rain` | horrors, bloody, horrific, brutal, horror, horrified | pleasing, counseling, recommendation, lovely |
| `snow` | cherish, beautifully, beautiful, blessings, cherished, admire | ambiguous, inconsistent, perverse, problematic |
| `sea` | joy, love, beautiful, beautifully, gentle, bliss | inconsistent, contradictory, perverse, violates |
| `manytrees` | chorus, rushed, pulitzer, productions, unparalleled, javafx | unchanged, quietly, withheld, hidden |
| `crowded` | vibrant, bustling, brenda, flavorful, flourish, expansive | deficiency, extingu, redeem, stupidity |
| `darker` | locked, lock, locked, tonight, grim, froze | artistic, aesthetic, decorative, artworks |
| `later` | saddened, sorrow, dialogs, apology, plaint, unhappy | select, creek, selects, short |
| `verbose` | extraordinarily, incredibly, exceedingly, tremendously, particularly, ridiculously | eyes, apps, refs, msg |
| `warmer` | upbeat, nicely, cooking, grandma, charm, delights | ordinal, ord, constituted, liu |
| `louder` | unconstitutional, totalitarian, fascist, nazi, violates, marxist | words, opening, opening, newsletter |
| `cheaper` | poems, poets, poem, song, words, ero | discrepancy, legitimate, outdated, professionalism |
| `manyfeatures` | sentiments, exagger, ambitious, expansions, glam, enthusiasm | alone, lowest, shortest, age |
| `offers` | springfield, negot, signed, business, requests, targeted | melanch, leben, temperament, communion |
| `urgent` | catastrophic, emergency, investigative, emergency, commande, urgent | charming, cute, nice, lovely |

Readings:

- **The moods share a word list.** `sad`, `calm` and `angry` built as
  *mood − neutral* all read *sorrow, heartbreaking, beautiful, loving*: the
  emotional-at-all direction. Subtract what they share and each gets its
  own vocabulary: `angry − moods` is a legal dispute, `calm − moods` a
  garden at dusk, `sad − moods` compassion and grief. The map says the same
  thing the page said, with words.
- **The registers name themselves.** `formal` is law and manuscripts and
  its opposite is *funny, vibes, yummy, kids*. `urgent` is *catastrophic,
  emergency*, opposite *charming, cute*. `verbose` is a list of
  intensifiers. `certain` reads *contradictory, unconstitutional,
  prohibited*: on this model, being certain is being in the wrong.
- **The things to like are not the things.** *Likes trees* is a party
  (*congratulations, greetings, hugs, guests*), *likes rain* is horror
  (*bloody, brutal, horrific*), *likes snow* is *cherish, blessings*, *likes
  sea* is *joy, love, bliss*. Nothing here is a tree, a cloud, or a wave;
  what the contrast sentences carried is how the speaker felt. That is
  why the tree sliders do not draw trees.
- **`cheaper` is poems, kisses, homemade; `louder` is political
  extremism** (*unconstitutional, totalitarian, fascist*). Whatever
  *shouting with exclamation marks* is to this model, it is a rally.
- **`refusal` has no words** (cosines under 0.10, nothing coherent). The
  page draws it as *Empty* and mist; the vocabulary does not know it. It is
  the one slider that is orthogonal to everything, on the matrix and here.

## Honest notes

- First-order: a Jacobian says what a small push does, not what strength
  3 does.
- Single tokens only; *heartbreaking* is one piece, *the small hours* is
  not on the map.
- The lens is for the 4B; the sliders in the article were built on the
  1.5B, where no lens is fitted. The 4B sliders are the same sentences,
  captured on the 4B (`plot_directions.py --url`). Cosines between the
  sliders on the 4B agree with the 1.5B matrix on the shape (moods
  together, amount axis, refusal alone).
- A slider's words say what the model is disposed to *say* under it, which
  is not what it draws. The page stays the readout.

## Run it

```bash
python fig/plot_directions.py --url http://aorus:8011 --cells --out /tmp/m.png     # captures + saves docs/runs/directions-<model>.json
python -m steeropathy.vocabmap docs/runs/directions-qwen3-4b-instruct-2507.json \
    --lens lenses/qwen3-4b-instruct-2507.jlens.pt \
    --unembed "~/.cache/huggingface/hub/models--Qwen--Qwen3-4B-Instruct-2507/snapshots/*/model-00001-of-00003.safetensors" \
    --tokenizer "~/.cache/huggingface/hub/models--Qwen--Qwen3-4B-Instruct-2507/snapshots/*/" \
    --out docs/runs/vocabmap-qwen3-4b.json
```

Runs on CPU in about a minute where the lens and the weights live. Next:
the other direction, an agent asking for a vector as words (*quiet,
winter, −loud*), summing the token directions, turning it on itself and
reading its page.
