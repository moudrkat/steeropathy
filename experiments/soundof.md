# soundof: what a steering direction sounds like

**TL;DR.** The same question as [worldof](secondhand.md#what-a-vector-looks-like)
through a second instrument: the model is asked, under a steering vector,
for eight bars in ABC notation, and the tune's typed fields are the
readout — tempo, key mode, meter — plus what the notes say: mean pitch,
range, notes per bar, share of rests. Every direction has a placebo (the
same vector, coordinates signed-permuted); the unsteered tune is the
baseline. When the page and the tune agree about a direction (refusal is
slow, minor and dark on both), the direction has a shape. When they
disagree, one of the instruments is lying. Built 2026-09-24; the first
live run is in the queue on the 4B.

[← README](../README.md)

## Why a second readout

A drawn page can be read; a cosine cannot. But one page is one page: what
it shows about a direction may be a fact about the page (its example, its
enum lists, its defaults) rather than about the direction. Two readouts
that share nothing but the vector fix that. Music is a good second one
because it is typed too (a tempo is a number, a key is major or minor),
and because *slow and minor* is what everyone expects sadness to be — a
prediction the placebo can embarrass.

## The four choices

1. **Whose internals:** one mind, steered.
2. **What crosses:** a unit direction added at layer 16 ± 4 of a 28-layer
   stack (`h += strength · v`). The directions are worldof's: moods from
   `transmit.py` (mood − neutral), contrasts pole-against-pole (refusal,
   certain, formal), and the LIKES set with a target field (night, trees,
   rain, snow, sea), which here has no target — a tune has no weather.
3. **Who decides:** nobody. The model writes; the parser reads.
4. **What is measured, against what:** per direction, the share of tunes
   that left the unsteered mode on each typed field and where they went;
   for the numbers, the mean and its distance from the unsteered mean. The
   placebo row under each direction is the control; the dose is what it
   moves.

## Prediction, written before the first run

The mood directions will not separate here either: sad, angry and calm
are built as mood − neutral and share one large "emotional at all"
component (transmit.py measured cos 0.57–0.76 between them on the 4B), so
they will all slow down and go minor together, as they all went to dusk
and moss on the page. The placebo will leave tempo where it was. refusal,
certain and formal, built against their opposite pole, may differ:
certain loud and square (4/4, major, no rests), formal in 3/4.

## What the instrument taught before it measured anything

- **The 1.5B cannot hold the notation.** Without an example it writes
  headers and forgets the notes, or notes and forgets the key; with a
  worked example it copies the example's notes back and drops the
  headers; under the sad vector at strength 2 it answers *"Sorry, but I
  can't do that."* — the mood vector lands in the apology register, which
  is a finding about the vector, not about music. So the bench runs on the
  4B, which at strength 3 keeps the form (smoke test: unsteered 88 bpm 3/4
  *Whispering Pines*; sad 60 bpm *Whispers in the Rain*; sad placebo 132
  bpm; refusal 60 bpm). A `--two-step` mode (describe the tune under the
  vector, write it sober) exists for models and doses where the notation
  breaks, the way secondhand dreams in two steps.
- **The worked example is a choice, again.** The prompt shows one plain
  tune (4/4, C, 120, stepwise) so a small model knows the shape. A steered
  model that copies it verbatim is flagged (`copied_example`) and counted,
  not scored as a tune of its own — the page's *certain copies the
  example* lesson, one instrument over.
- **Pitches are read without the key signature.** A written C is a C; in
  G major every F is a semitone flat in the reader. It is wrong the same
  way for every tune, and mean pitch and range are read as differences.

## Run it

```bash
python -m steeropathy.soundof sad angry calm refusal certain formal --url http://localhost:8011 --placebo --n 12
python -m steeropathy.soundof night trees --n 12 --two-step
python fig/render_soundof.py docs/runs/soundof-01-aorus-4b-n12.json --placebo   # piano roll, wav, mp4 per direction
```

Writes `docs/soundof.json`: per tune the ABC text, its fields, the notes;
`summary` holds the table. Tests run offline:
`python -m unittest tests.test_soundof`.
