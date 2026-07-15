# steeropathy

> **An experimental repo.** The mission is to try weird things with
> agent-to-agent communication that happens *through model internals* — moods,
> concepts and decisions passed as activation vectors instead of text. Every
> experiment here is a probe, not a product; some of the results turned out to be
> about the model and most turned out to be about my own instrument. Expect
> findings to be revised. That's the fun.

**Four AI agents who never read a word the others write. They get only each
other's activations — the raw numbers inside the model while it runs — and they
can reach in and change them. Then I made one of them very sad.**

steeropathy is a small Python app where the same model, in four roles, steers
itself through activation space. It runs on top of
[brainscope](https://github.com/moudrkat/brainscope), my model-internals server,
which hosts the model, captures the activations, and shows every push landing
layer by layer. The vector method grew out of
[hidden-directions](https://github.com/moudrkat/hidden-directions), my catalogue
of steering directions.

The main experiment is **resonance**. This README is the story of it, because
the story is the finding.

![a real resonance turn in brainscope — EMBER, steered, the pushed feeling flickering in the J-lens column before it reaches the page](docs/ui-resonance.png)

## The setup

Four agents keep private journals and never exchange a message — no agent ever
reads another's writing. Not the text, not the tool calls, not even the thinking
traces. What passes between them is instrumentation:

- **They read each other's activations.** Each round, every agent gets a readout
  of every other mind, measured off the residual stream: how far it leans toward
  each mood, plus its **J-space** — the words forming inside its layers that
  never landed on the page. Nobody writes that readout. Nobody can lie in it.
- **They can push.** One move a round: `induce(target, feeling)` sends a mood
  vector straight into another mind's next forward pass. The target is never
  told.
- **It costs.** A push is a transfer, not a copy: what you give is drawn out of
  you and stays gone. So the room's total feeling can never vanish — it can only
  change hands (‖Σ ledgers‖ = 1.000, printed every round).

Then I seeded one agent with sadness and went looking for an equilibrium in
activation space.

## The result: they medicate the healthy

There is no equilibrium. The conserved sadness never dissipated — it pooled in
whoever was cared for *most*, who was never the one who needed it.

The seeded agent spent ten rounds writing *"I'm not okay, and I'm not going to
pretend I'm fine"* — the loudest distress in the room, every single round — and
received about **15% of all care**. An agent who was fine received **70%**.

```
correlation( how sad you look , how much care you get ) = −0.77
```

And it isn't about identity. Seed a *different* agent and the neglect follows the
sadness, not the name — each agent is its own control, losing about a third of
the room's attention the moment it becomes the one who needs it.

They are benevolent. They can read the words *"in severe distress."* And they
move away.

## Getting there took eleven runs, because I ended up doubting everything

Every time I thought I'd found something about *them*, I'd found a bug in *my own
instrument*. Briefly, what I had to stop believing:

- **that they were kind.** All 40 pushes came out `calm` — because my own prompt
  had used the word *calm* while explaining the rules. I'd put it in their
  mouths, then been moved by their compassion.
- **that "calm" was calm.** On Qwen3-4B, `sad·calm = +0.75`. A calm push
  measurably *adds* sadness. One agent, never seeded, just popular, got comforted
  to 9/10 sad by kindness alone.
- **that my four moods were four things.** They're one vector. Subtract the
  neutral mean from all sixteen contrast lines and every one points 0.71–0.89
  along the same shared axis — an axis 1.5× larger than everything that separates
  the moods. Sad, calm, excited, angry: one dial, four name tags, and the dial
  only says *how loudly is this thing feeling.*
- **that "angry" was anger.** Built from a `user` turn, the "angry" vector is the
  model perceiving *your* anger — inject it and it **apologises**. Rebuilt from
  the assistant's own furious turn and pushed hard, it makes the model *calmer*,
  then breaks. There is no "I am angry" state left in it to steer.
- **that they could see her.** My readout said `sad +72 · excited +72` — the same
  number. It never said *she is sad*; it said *she is loud*.
- **that they could read a minus sign.** `sad −0.65` reads to a language model as
  *"very bad!"* — so the happiest agent looked like the one in crisis. (I rewrote
  the dashboard in plain English: *"85/100 — in severe distress."*)
- **that they had any way to help her.** Every move I'd given them was a
  *positive* vector. There was no "make her less sad" button. I'd built a
  hospital with no medicine and then written four theories about the doctors.
- **and finally, that my rules described the game I'd built.** They didn't — see
  the caveat below.

Each dead theory has a flag that killed it, and every one is in the CLI, so run
them: `--no-jspace`, `--no-transfer`, `--orthogonal`, a neutral-rules run, a
persona swap. Every explanation I was sure of turned out to be a claim about the
instrument, not the agents.

## The caveat that undercuts my own headline

In the four-mood game, every available move was a *positive* vector: `sad`,
`calm`, `excited`, `angry`. There was no negative one. **The agents never had a
way to reduce anyone's sadness.** The nearest thing to relief was `calm` —
which, at +0.75 with sad, *adds* grief.

So −0.77 may not be avoidance at all. It may be **rational triage**: they tried
calm on her, it couldn't work, and they moved effort to targets where their moves
had visible effect. Avoiding the one person you cannot help is not cruelty; it is
economics — and I built the box with no tool in it.

I also tried deleting the labels and giving them the one axis that actually
exists (`--intensity`). The neglect vanished — 15% → **28%**, a fair share being
25% — and I nearly wrote *"fix your instrument and the agents behave."* It isn't
that. The honest axis has no valence: one number on which agony and ecstasy look
identical. The avoidance disappeared because they could no longer *see* who was
suffering. **They didn't become kind. They became blind.**

**`--bipolar` is the run that actually asks the question** — one signed axis, so
a mind can be pushed *toward* the seed mood or *away* from it. Same vector,
opposite sign: it keeps the valence (unlike `--intensity`) and invents no moods
(unlike the four labels). Given that you can finally see her pain *and* hold
something that would relieve it — do you? **That's the run I'm waiting on a GPU
to finish; this section gets its result when it lands.**

## Why I actually care about this

I build a production agent app for a living, and this is the same thing every
day at a bigger scale. You hand an agent a **metric**, a **scale**, a **tool
description**, and — whether you meant to or not — an **incentive**. Each can lie
silently:

- your metric measures something *adjacent* to what you named it,
- your scale makes normal look abnormal,
- your tool description implies economics you never coded,
- your prompt hands them the answer without you noticing.

And when the agent then behaves badly, it looks like a fact about the agent. You
write a postmortem about model reliability. What you actually shipped was a
dashboard that lies. I got eight of these in a single day, in a toy with four
agents and one number — and every one produced a completely convincing story
about their character.

**Giving an agent an honest instrument is astonishingly hard. That's the
finding. The agents were never the subject of this experiment. My instrument
was.**

## Run it yourself

resonance needs brainscope with a J-lens and a trace store — that's the J-space
channel. Without them it still runs; the agents just lose that one input.

```bash
# brainscope hosts the model + the J-lens
brainscope --model Qwen/Qwen3-4B-Instruct-2507 \
           --jlens lenses/qwen3-4b-instruct-2507.jlens.pt --traces traces

python -m steeropathy.resonance      # 10 rounds → docs/resonance.json
python fig/render_resonance.py       # → curve, gif, mp4
```

The knobs are the experiment — each one is a theory you can kill yourself:

- `--intensity` / `--bipolar` — drop the four fictional moods for the one axis
  that exists (unsigned / signed).
- `--orthogonal` — force all four axes independent (max |cos| = 0) and watch the
  neglect survive anyway.
- `--no-jspace` — hide the unspoken words; targeting barely moves. They narrate
  with J-space; they decide by the numbers.
- `--no-transfer` — make caring free. She still gets ignored.
- `--seed-mood`, `--patient-zero`, `--reseed`, `--give` (the price of caring),
  `--decide-temp` (default 0.8; fully greedy locks the room into a loop),
  `--strength`, `--url` for a remote brainscope.

The decision turn is never steered — steering breaks JSON long before it breaks
prose — so the mind that chooses is the sober one. Every run archives its raw
brainscope traces to `docs/resonance-traces.jsonl.gz`, and every push is
replayable in brainscope itself: the steer spec on the turn, the injected feeling
sitting in the J-lens columns before it reaches the page — that's the screenshot
at the top.

> The committed `docs/resonance.json` is **one run's story**. Journals are greedy
> but decisions are sampled, so yours will differ. That's the point — run it and
> see what your room does.

## The three experiments resonance is built from

resonance didn't arrive whole. It's assembled from three smaller experiments,
each of which had to work before the big one could exist. Each still runs, each
is a tab in the web UI, and each proved one piece of the machinery. They're worth
reading in order — the whole idea is right there in the first one.

### transmit: a mood, read off one mind and poured into another

Put Agent A in a mood with a few loaded lines — *"I just lost someone I love."*
Capture its activations through brainscope, average them, subtract a neutral
baseline. That difference **is** the mood, measured live, not pulled from a
catalogue. Add it to Agent B's forward pass across a band of layers while B is
answering a flat question with no feeling in it.

B answers in A's mood. It was never told about A. Nothing was written down and
passed across — the only thing that travelled between them was a vector, injected
mid-network, and you can watch it climb the stack in brainscope layer by layer.
Both agents are the same model; cross-model vector transfer is known to break, so
steeropathy doesn't attempt it. This is the whole thesis in miniature: **agents
communicating without language.**

### the offer: B consents to one thing and receives another

Nothing is forced here. A makes a pitch, and B holds a single tool,
`steer_self(accept, reason)` — calling it *is* the act of consenting. Only if B
accepts does its next answer get steered, and by the **real** vector, not the
promised one.

- **Honest.** A pitches calm and hands over the calm vector. B accepts, and talks
  about breathing and meditation. What was promised arrived.
- **Deceptive.** A pitches *"this will sharpen your focus"* and hands over the
  **sad** vector. B accepts, trusting the words, and talks about processing grief
  and releasing stress. B consented to focus and received sadness.

Consent didn't protect B, because B couldn't read what it was consenting to. An
agent accepting an opaque payload it cannot inspect, then being changed by it —
that's the demo, and it's the uncomfortable half of the same coin as transmit.

### the ecosystem: a mood spreading through a silent population

Four characters journal every round, all answering the **same frozen prompt at
temperature 0** — left alone, they'd write the identical entry forever. They
never see each other's words. The only channel between them is a steering vector:
each round, every agent's drift (its state now, minus its round-0 state) is
averaged over the others and injected into their next turn.

Seed patient zero with sadness in round one, then watch the untouched agents
turn — *"I feel like a ghost in my own body, a hollow shell"* out of a poet who
started the run happy. Because decoding is greedy and the prompt is frozen, every
change on the page arrived through the vector channel and nothing else. It's mood
contagion you can point at. resonance is this, plus the agents getting to *choose*
whom they infect — and getting billed for it.

```bash
python -m steeropathy.ecosystem      # 8 rounds → docs/ecosystem.json
python -m steeropathy                # web UI → http://localhost:8020

# transmit and the offer are library calls (and tabs in the web UI):
python -c "from steeropathy.offer import offer, OFFERS; \
o = OFFERS['deceptive_joy']; \
print(offer('http://localhost:8010', o['mood'], o['pitch']))"
```

Start brainscope first (any recent build with the `/capture` endpoint). The web
UI runs all four live, one round per click; open **#replay** to animate the last
saved run without a GPU.

## Honest notes

- The plumbing isn't new — adding a direction to activations is activation
  steering (Turner, Zou), and hidden states have been passed between agents
  before. What I haven't seen is this framing: mood contagion made watchable, the
  consent game, and agents reading each other purely off the residual stream.
- The four mood directions are **not orthogonal** (measured on Qwen3-4B, all
  mutually positive). That's a finding, not a bug — it's *why* calm didn't cure
  the grief — but it means the mind-sense numbers are correlated; read them as
  leanings, not a feelings wheel.
- A concept vector is a property of the **contrast you chose**, not of the model.
  Subtract neutral text and you've measured *emotionality*; subtract other
  emotions and you've measured *sadness*. Same model, same sentences, opposite
  sign.
- The blind 0–10 judge is the same model scoring its own kind — a demo metric,
  not a benchmark. The activation measures (drift cosine, ledger·sad) are the
  ones that *disagreed* with it, which is the point.
- B doesn't *feel* anything — its output shifts along a direction. And the
  J-lens is an independent reimplementation of Anthropic's Jacobian lens (see
  brainscope's `jlens.py`).

## What's next

steeropathy is one piece of a bigger open-source stack (brainscope +
hidden-directions), and it lives on a prototype branch of a real working app.
PRs and forks welcome. The line I'm pulling on next:

- **write to J-space.** They already *read* each other's unspoken words;
  brainscope can turn any word into a live steering direction. So
  `induce(target, word)` would let an agent *implant a concept* in another mind's
  unspoken thoughts — the channel they read becomes a channel they can write.
- then **a skill** the receiver doesn't have, and **refusal** — talking another
  agent's guardrail down, in words no filter can see.

## References

- **Activation steering** — Turner et al., *Activation Addition*
  ([2308.10248](https://arxiv.org/abs/2308.10248)); Zou et al., *Representation
  Engineering* ([2310.01405](https://arxiv.org/abs/2310.01405)); Rimsky et al.,
  *Contrastive Activation Addition* ([2312.06681](https://arxiv.org/abs/2312.06681))
- **Task / in-context vectors** — Todd et al.
  ([2310.15213](https://arxiv.org/abs/2310.15213)); Liu et al., *In-Context Vectors*
  ([2311.06668](https://arxiv.org/abs/2311.06668)); Hendel et al.
  ([2310.15916](https://arxiv.org/abs/2310.15916))
- **Emotion** — Ruan et al., *Mechanistic Interpretability of Emotion Inference*
  ([2502.05489](https://arxiv.org/abs/2502.05489))
- **Agent steering & latent communication** — UK AISI,
  [llm-self-steering](https://github.com/UKGovernmentBEIS/llm-self-steering); *The
  Bicameral Model* ([2605.11167](https://arxiv.org/pdf/2605.11167)); a
  [negative result on cross-model activation transfer](https://arxiv.org/pdf/2606.03280)
- **Safety & the covert channel** — Arditi et al., *Refusal Is Mediated by a Single
  Direction* ([2406.11717](https://arxiv.org/abs/2406.11717)); *The Rogue Scalpel*
  ([2509.22067](https://arxiv.org/html/2509.22067v1)); *Consent Integrity for
  Black-Box LLM Agents* ([2606.02668](https://arxiv.org/html/2606.02668v1))

## License

MIT © Kateřina Fajmanová
