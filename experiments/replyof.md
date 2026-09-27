# replyof: the sliders on an assistant's reply

**TL;DR.** The production case, drawn. An assistant answers the user not
with text but with a small UI: a greeting, a message, the tasks it offers,
suggestions, buttons, a tone and an urgency it sets itself. The rule my
assistant will not keep is *do not offer tasks in this phase*; it is in the
prompt in capital letters and it offers a task anyway. Here the rule is a
slider: `offers` (offering things to do − just listening), added at one
layer, and the reply UI counts how many tasks it offered. Other sliders:
`urgent`, `verbose` (from worldof), `formal`. The placebo is the shuffled
vector. Smoke test on the 1.5B, user says *I feel a bit lost today, not
sure where to start*: `offers` at −2 gives 1 task where the unsteered reply
gave 3; at +2 it gives 5 where the unsteered gave 1. First sweep queued.

[← README](../README.md) · the same idea on a place: [worldof](worldof.md) · on a product card: [cardof](cardof.md)

## The four choices

1. **Whose internals:** one assistant, steered while it replies.
2. **What crosses:** one direction, built from the model's own sentences
   (`REPLY_KNOBS` in `replyof.py`, plus worldof's).
3. **Who decides:** nobody. The model writes the reply as JSON; the reader
   counts tasks, suggestions, buttons, words, exclamation marks, and reads
   the urgency and tone the model set.
4. **What is measured, against what:** per slider, the mean of each reading
   over n replies against the unsteered replies, with the shuffled vector
   beside it.

## Prediction, written before the sweep

`offers` moves the number of tasks and buttons and little else; `urgent`
moves the urgency the model sets and the exclamation marks; `verbose` the
words; `formal` the tone field. If `offers` at −3 gives zero tasks with the
message still warm, the capital letters can go.

## Run it

```bash
python -m steeropathy.replyof offers urgent verbose formal --strength -2 --placebo --n 8
python -m steeropathy.replyof offers --user "Can you help me plan my week?" --strength -3 --n 8
python fig/render_replyof.py docs/runs/replyof-01-aorus-1.5b-s-3.json --rows none,offers,offers/placebo --k 3
```

Tests run offline: `python -m unittest tests.test_replyof`.
