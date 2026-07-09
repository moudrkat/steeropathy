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


def capture_mood(host: str, mood_texts: list[str], layer: int | None = None,
                 pool: str = "last") -> tuple[list[float], int]:
    """mood direction = mean(mood lines) − mean(neutral lines), at one layer, unit-normalized.

    Averaging over several lines cancels topic noise and leaves the shared affect; the
    single-prompt contrast does NOT survive steering (it just over-steers into salad)."""
    if layer is None:
        layer = default_layer(host)

    def meanv(texts: list[str]) -> list[float]:
        vs = [_post(host, "/capture", {"messages": [{"role": "user", "content": t}],
                                       "pool": pool, "layer": layer})["vector"]
              for t in texts]
        return [sum(col) / len(vs) for col in zip(*vs)]

    diff = [h - c for h, c in zip(meanv(mood_texts), meanv(NEUTRAL_TEXTS))]
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
