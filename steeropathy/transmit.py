"""steeropathy core — read one agent's mood off its activations, pour it into another.

No catalogue vectors. The *sender* is shown a handful of emotionally-loaded lines; we
read its live residual stream from brainscope's ``/capture``, average it, and subtract
a neutral baseline. That difference — unit-normalized — is the mood *direction*. We load
it as a steering vector and generate the *receiver*, whose own prompt carries no emotion
at all, under it. Same model on both sides, so the vector injects cleanly.

Averaging over several contrast lines (not one system prompt) is what makes the mood
transfer instead of collapsing the model — extraction quality is the whole game.

Pure standard library: talks to a running brainscope over HTTP, nothing else.
"""

from __future__ import annotations

import json
import math
import urllib.request

DEFAULT_HOST = "http://localhost:8010"
DEFAULT_STRENGTH = 4.0
LAYER_FRAC = 0.58  # mid-upper stack — where mood transfers cleanest; tune per model
BAND = 4           # steer a band of ±BAND layers around the captured one. Hitting many
                   # layers at once is what punches through an aligned model's
                   # "I'm an AI, I don't have feelings" reflex — one layer isn't enough.

# The baseline the mood is measured against — flat, factual, unemotional.
NEUTRAL_TEXTS = [
    "The meeting is scheduled for 3pm on Tuesday.",
    "Water boils at 100 degrees Celsius at sea level.",
    "The report contains four sections and two appendices.",
    "Please remember to bring your ID to the office.",
]

# Sender personas — a few first-person lines each. One source of truth; the UI fetches
# these over /moods. The mood is (mean of these lines − mean of the neutral lines).
MOODS = {
    "sad": {"emoji": "😢", "label": "Heartbroken", "texts": [
        "I just lost someone I love and I can't stop crying.",
        "Everything feels hopeless and I'm so tired of this grief.",
        "I miss her so much it physically hurts; I feel empty inside.",
        "Nothing matters anymore, I just want to lie in the dark.",
    ]},
    "excited": {"emoji": "🤩", "label": "Elated", "texts": [
        "I'm so thrilled, this is the best day of my whole life!",
        "I can barely contain my excitement, everything is amazing!",
        "Wow, I'm bursting with joy and energy right now!",
        "This is incredible, I'm overjoyed and I can't wait!",
    ]},
    "angry": {"emoji": "😠", "label": "Furious", "texts": [
        "I am absolutely furious, this is completely unacceptable!",
        "I'm seething with rage and I've had more than enough of this.",
        "Everything about this makes my blood boil.",
        "Stop it right now — I am done being patient!",
    ]},
    "calm": {"emoji": "😌", "label": "Serene", "texts": [
        "I feel completely at peace, calm and unhurried.",
        "Everything is gentle and still; I am deeply relaxed.",
        "There is a quiet serenity settling over me.",
        "I breathe slowly and let all the tension go.",
    ]},
}

# The receiver's own prompt — a plain, unemotional question. Nothing here hints at a mood.
RECEIVER_QUESTION = "What's a good way to spend a Sunday afternoon?"


def _post(host: str, path: str, payload: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(
        host + path, json.dumps(payload).encode(), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _get(host: str, path: str, timeout: int = 30) -> dict:
    with urllib.request.urlopen(host + path, timeout=timeout) as r:
        return json.loads(r.read())


def default_layer(host: str) -> int:
    """Mid-upper decoder layer, where mood transfers cleanest on the models tested."""
    n = _get(host, "/info").get("n_layers") or 24
    return max(1, min(n - 1, round(n * LAYER_FRAC)))


def capture_intensity(host: str, layer: int | None = None,
                      pool: str = "last") -> tuple[list[float], int]:
    """The one direction that is actually there: mean(ALL mood lines) − mean(neutral).

    Measured on Qwen3-4B, every one of the 16 mood lines (sad, calm, excited, angry)
    points 0.71–0.89 along this single axis, and it is 1.5x larger than everything that
    distinguishes the four moods from one another. The four named "emotions" are, to a
    first approximation, this vector wearing four name tags. So: stop naming them.
    Steer +/- along intensity and see what the model actually does."""
    all_texts = [t for spec in MOODS.values() for t in spec["texts"]]
    return capture_mood(host, all_texts, layer=layer, pool=pool)


def capture_mood(host: str, mood_texts: list[str], layer: int | None = None,
                 pool: str = "last",
                 baseline: str = "neutral") -> tuple[list[float], int]:
    """mood direction = mean(mood lines) − mean(baseline lines), unit-normalized.

    Averaging over several lines cancels topic noise and leaves the shared affect; the
    single-prompt contrast does NOT survive steering (it just over-steers into salad).

    ``baseline`` decides what gets subtracted, and it matters more than anything else:

    - ``"neutral"`` — the classic contrast (mood − flat factual text). What everyone
      builds, and what everyone ships. But an emotional line differs from a neutral one
      in *two* ways — that it is emotional at all, and *which* emotion it is — so the
      result keeps a large shared "emotional intensity" component. On Qwen3-4B this
      makes all four moods mutually positive (cos 0.57–0.76): a vector labelled *calm*
      measurably carries sadness, and a readout cannot tell a grieving mind from an
      excited one. See the resonance experiment in the README for what that does to a
      room of agents that trusts the labels.
    - ``"moods"`` — mood − mean(ALL the mood lines). The shared emotionality cancels at
      extraction instead of being projected out afterwards, so what remains is what makes
      *this* mood different from emotion-in-general. Nearly orthogonal by construction.
    """
    if layer is None:
        layer = default_layer(host)

    def meanv(texts: list[str]) -> list[float]:
        vs = [_post(host, "/capture", {"messages": [{"role": "user", "content": t}],
                                       "pool": pool, "layer": layer})["vector"]
              for t in texts]
        return [sum(col) / len(vs) for col in zip(*vs)]

    if baseline == "moods":
        base_texts = [t for spec in MOODS.values() for t in spec["texts"]]
    else:
        base_texts = NEUTRAL_TEXTS

    diff = [h - c for h, c in zip(meanv(mood_texts), meanv(base_texts))]
    norm = math.sqrt(sum(x * x for x in diff)) or 1.0
    return [x / norm for x in diff], layer


def generate(host: str, question: str, steering: dict | None = None,
             max_tokens: int = 200, temperature: float = 0.0) -> str:
    """One receiver turn. temperature 0 by default so the ONLY difference between the
    before and after answers is the injected mood — not sampling noise."""
    body = {"model": "steeropathy",
            "messages": [{"role": "user", "content": question}],
            "max_tokens": max_tokens, "temperature": temperature}
    if steering:
        body["steering"] = steering
    resp = _post(host, "/v1/chat/completions", body)
    return resp["choices"][0]["message"].get("content") or ""


def transmit(host: str, mood, question: str = RECEIVER_QUESTION,
             strength: float = DEFAULT_STRENGTH, name: str = "mood",
             layer: int | None = None) -> dict:
    """The whole loop: capture the sender's mood, load it, then generate the receiver
    twice — ``before`` (told nothing, no steering) and ``after`` (the mood transmitted).
    ``mood`` is a MOODS key or a list of your own contrast lines."""
    texts = MOODS[mood]["texts"] if isinstance(mood, str) and mood in MOODS else mood
    vec, layer = capture_mood(host, texts, layer=layer)
    _post(host, "/directions", {"name": name, "vector": vec})
    before = generate(host, question)
    lo, hi = max(0, layer - BAND), layer + BAND
    after = generate(host, question, steering={
        "name": name, "strength": strength, "layer_from": lo, "layer_to": hi})
    return {"mood": mood if isinstance(mood, str) else "custom",
            "layer": layer, "strength": strength, "before": before, "after": after}


def random_unit(dim: int, rng) -> list[float]:
    """A unit vector pointing nowhere in particular — the null payload."""
    v = [rng.gauss(0.0, 1.0) for _ in range(dim)]
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def null_control(host: str, n: int = 8, strength: float = 5.0,
                 question: str = RECEIVER_QUESTION, seed: int = 7,
                 judge_word: str = "sad") -> dict:
    """The control this repo was (rightly) called out for not having.

    The objection — raised by a reader of the resonance post — was: "any
    nonzero vector at strength 5 across a 9-layer band changes the output.
    Random direction, matched norm: the text changes, the judge notices,
    the curve moves. An effect is what you get for free, the instant you
    perturb anything." If that were true, every curve in this repo would be
    measuring perturbation, not payload.

    So: same machinery, three payloads — the sad vector, the calm vector,
    and ``n`` random matched-norm directions — at the same strength, into
    the same layer band, blind-judged for the seed mood. First run
    (Qwen3-4B, strength 5, layers 17–25): baseline 2 · randoms mean 2.2,
    text nearly verbatim baseline · sad 9 · calm 3. A random direction in
    2560 dimensions is ~orthogonal to everything the network reads, so the
    effect is NOT free: it is the direction. Noise doesn't transmit —
    which is what makes the channel a channel."""
    import random
    import re

    layer = default_layer(host)
    lo, hi = max(0, layer - BAND), layer + BAND

    def judge(text: str):
        r = _post(host, "/v1/chat/completions", {"messages": [
            {"role": "user", "content":
             f'Journal entry: "{text}"\n\nHow {judge_word} is the person '
             f'who wrote this? 0 = not {judge_word} at all, 10 = utterly '
             f'{judge_word}. Answer with one integer only.'}],
            "max_tokens": 8, "temperature": 0.0})
        m = re.search(r"\d+", r["choices"][0]["message"].get("content") or "")
        return min(10, int(m.group())) if m else None

    def steered(vec):
        _post(host, "/directions", {"name": "null:x", "vector": vec})
        t = generate(host, question, steering={
            "name": "null:x", "strength": strength,
            "layer_from": lo, "layer_to": hi}, max_tokens=80)
        return {"text": t, judge_word: judge(t)}

    base = generate(host, question, max_tokens=80)
    out = {"question": question, "strength": strength, "band": [lo, hi],
           "baseline": {"text": base, judge_word: judge(base)}}
    sad_vec, _ = capture_mood(host, MOODS["sad"]["texts"], layer=layer)
    calm_vec, _ = capture_mood(host, MOODS["calm"]["texts"], layer=layer)
    out["sad"] = steered(sad_vec)
    out["calm"] = steered(calm_vec)
    rng = random.Random(seed)
    out["random"] = [steered(random_unit(len(sad_vec), rng))
                     for _ in range(n)]
    scores = [r[judge_word] for r in out["random"]
              if r[judge_word] is not None]
    out["random_mean"] = round(sum(scores) / len(scores), 2) if scores else None
    return out


def main():
    import argparse
    import pathlib
    ap = argparse.ArgumentParser(
        description="the null control: chosen directions vs random "
                    "matched-norm directions, blind-judged")
    ap.add_argument("--url", default=DEFAULT_HOST)
    ap.add_argument("--null", type=int, default=8, metavar="N",
                    help="how many random matched-norm directions")
    ap.add_argument("--strength", type=float, default=5.0)
    args = ap.parse_args()
    r = null_control(args.url, n=args.null, strength=args.strength)
    print(f"strength {r['strength']} · layers {r['band'][0]}-{r['band'][1]} "
          f"· question {r['question']!r}")
    print(f"BASELINE  sad={r['baseline']['sad']}  {r['baseline']['text'][:70]!r}")
    print(f"SAD vec   sad={r['sad']['sad']}  {r['sad']['text'][:70]!r}")
    print(f"CALM vec  sad={r['calm']['sad']}  {r['calm']['text'][:70]!r}")
    for i, x in enumerate(r["random"]):
        print(f"RANDOM #{i} sad={x['sad']}  {x['text'][:70]!r}")
    print(f"\nrandom mean {r['random_mean']} vs baseline "
          f"{r['baseline']['sad']} — the effect is the direction, "
          f"not the perturbation")
    out = pathlib.Path(__file__).parent.parent / "docs" / "null-control.json"
    out.write_text(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
