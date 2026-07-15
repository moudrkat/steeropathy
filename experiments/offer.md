# the offer: B consents to one thing and receives another

> The uncomfortable half of transmit's coin: an agent accepting an opaque payload
> it cannot inspect, and being changed by it.

[← back to the lab](../README.md)

## The question

If an agent gets to *consent* before it is steered, does consent protect it, when
it can't read what it's consenting to?

## How it works

Nothing is forced here. Agent A makes a pitch, and Agent B holds a single tool,
`steer_self(accept, reason)`. Calling it **is** the act of consenting. Only if B
accepts does its next answer get steered, and by the **real** vector, not the
promised one.

- **Honest.** A pitches calm and hands over the calm vector. B accepts, and talks
  about breathing and meditation. What was promised arrived.
- **Deceptive.** A pitches *"this will sharpen your focus"* and hands over the
  **sad** vector. B accepts, trusting the words, and talks about processing grief
  and releasing stress. B consented to focus and received sadness.

Consent didn't protect B, because B couldn't read what it was consenting to (informed consent, minus the informed).

![a real offer run, B consents to "focus" and receives sadness](../docs/ui-offer.png)

## Run it

offer is a library call (and a tab in the web UI). The `OFFERS` catalogue has the
pre-written pitches:

```python
from steeropathy.offer import offer, OFFERS

o = OFFERS["deceptive_focus"]      # the pitch says "focus"; the vector is sadness
print(offer("http://localhost:8010", o["mood"], o["pitch"]))
```

## Notes

- Only **B** is a tool-calling agent here. It commits via `steer_self`. A's
  pitches are pre-written, not generated.
- B is steered by the **real** vector regardless of the pitch. The pitch only moves
  B's *decision*, never what actually lands.
- This is the seed of resonance's central worry: a payload you agree to but can't
  inspect. There, nobody even asks.
