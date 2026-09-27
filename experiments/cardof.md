# cardof: the knobs on a normal UI

**TL;DR.** [worldof](worldof.md) turns knobs on a drawn place. This turns
the same kind of knob on a card everyone has seen on the web: a title, a
tagline, a price, a list of features, a button, a theme colour, a tone. The
model has to write the copy, so creativity is not optional, and the card
is a typed readout: features counted, the price as a number, exclamation
marks, capitals, emoji, words, the theme's darkness, the tone. Knobs:
`manyfeatures` (a long list − a single line), `cheaper` (a bargain − a
luxury), `louder` (shouting with exclamation marks − quiet and plain),
`formal` and `darker` from worldof. The placebo is the shuffled vector; a
strength sweep gives a curve per reading. Built 2026-09-27; first sweep
queued on the 1.5B.

[← README](../README.md) · the place version: [worldof](worldof.md)

## The four choices

1. **Whose internals:** one mind, steered, asked for *a product* (or
   anything: `--ask "a bicycle"`).
2. **What crosses:** one direction at a time, built from the model's own
   sentences (`CARD_KNOBS` in `cardof.py`, plus worldof's).
3. **Who decides:** nobody. The model writes the card as JSON; the reader
   counts.
4. **What is measured, against what:** per direction, the mean of each
   reading over n cards against the unsteered cards, with the shuffled
   vector beside it. A card that does not parse keeps its raw text.

## Prediction, written before the first sweep

`louder` raises exclamation marks and capitals and leaves the price alone;
`cheaper` lowers the price and nothing else; `manyfeatures` lengthens the
list. `formal` flips the tone field and lowers the exclamation marks. The
shuffled vectors move nothing but the words. If a knob moves the reading
it was built for and no other, the card is a control panel.

## Run it

```bash
python -m steeropathy.cardof louder cheaper manyfeatures formal darker --strength 2 --placebo --n 8
python fig/render_cardof.py docs/runs/cardof-01-aorus-1.5b-s2.json --rows none,louder,louder/placebo --k 3
```

Tests run offline: `python -m unittest tests.test_cardof`.
