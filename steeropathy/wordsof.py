"""wordsof: a slider made of words, not sentences.

The J-lens gives every vocabulary token a steering direction (see
vocabmap). So a slider can be asked for as a few words, *quiet, winter,
−loud*, summed as a stack of token directions, and turned. Nobody wrote
contrast sentences; the map did the work. This bench asks whether such a
slider turns the page at all, against three controls:

    none      the unsteered place
    words     the token directions of the words, stacked, at the strength
    random    the same number of token directions for random words, same
              strength: a shove with other names (the placebo)
    said      the words written into the prompt instead ("Make it: quiet,
              winter. Not: loud."): the text channel, which is the honest
              baseline for any vector

If *words* moves the fields the words name and *random* does not, the
vocabulary is a usable map, and an agent can pick from it. If *said* does
it as well or better, the vector is a slower way to write a sentence, and
that gets written down too.

    python -m steeropathy.wordsof quiet winter ~loud --url http://localhost:8011 --n 8 --strength 1.5
    python -m steeropathy.wordsof bustling --n 8            # does the word for `crowded` draw a crowd?

Words with a leading ~ are turned the other way. Needs a brainscope
with a J-lens loaded (the 4B). Decisions here are nobody's: the words are
given; the agent version, where a model picks the words for a brief,
comes after this one shows the map turns anything.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random

from .secondhand import NEUTRAL, Secondhand, kinds_of, world_link
from .worldof import summarize, print_summary

HERE = pathlib.Path(__file__).parent.parent
ASK = NEUTRAL

# the placebo's vocabulary: plain words the page has no field for
RANDOM_WORDS = ("table", "paper", "window", "monday", "engine", "letter", "number", "bottle", "corner",
                "ticket", "button", "pocket", "market", "office", "camera", "silver", "copper", "wheel",
                "bridge", "basket", "ladder", "kettle", "jacket", "pencil", "carpet", "garage", "radio",
                "salad", "napkin", "shelf", "tunnel", "meadow", "harbor", "candle", "mirror", "pillow")


def parse_words(tokens):
    """['quiet', 'winter', '~loud'] -> [('quiet', +1), ('winter', +1), ('loud', -1)]; a leading ~ or - (or a
    trailing -) turns the word the other way. ~ is the one the shell and argparse leave alone."""
    out = []
    for t in tokens:
        sign = -1.0 if t.startswith(("~", "-")) or t.endswith("-") else 1.0
        w = t.strip("~+-").strip()
        if w:
            out.append((w, sign))
    return out


def register(sh, word, prefix="wordsof"):
    """One token direction on the server, named; returns the name and the piece it tokenized to."""
    r = sh.post("/jlens/direction", {"text": word, "name": f"{prefix}:{word}"})
    if "error" in r:
        raise SystemExit(f"{word}: {r['error']}")
    return r["name"], r.get("token"), bool(r.get("multi_token"))


def stack(names_signs, strength, lo, hi):
    return [{"name": n, "strength": strength * s, "layer_from": lo, "layer_to": hi} for n, s in names_signs]


def said_text(words):
    yes = [w for w, s in words if s > 0]
    no = [w for w, s in words if s < 0]
    parts = []
    if yes:
        parts.append("Make it: " + ", ".join(yes) + ".")
    if no:
        parts.append("Not: " + ", ".join(no) + ".")
    return " ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words", nargs="+", help="words; a leading ~ turns the word the other way")
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--strength", type=float, default=1.5, help="per word; brainscope's own default for a token direction")
    ap.add_argument("--band", default=None, help="layer_from:layer_to; default the server's 0.42n–0.54n for token directions")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-said", action="store_true", help="skip the text control")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    words = parse_words(a.words)
    sh = Secondhand(a.url, channels=("none",), temp=0.8, max_tokens=500)
    sh.prompt(NEUTRAL)
    info = sh.get("/info")
    if not (info.get("jlens") or {}).get("loaded"):
        raise SystemExit("this brainscope has no J-lens loaded; the token directions need one")
    n_layers = int(info["n_layers"])
    lo, hi = (int(x) for x in a.band.split(":")) if a.band else (round(n_layers * 0.42), round(n_layers * 0.54))
    real = []
    for w, s in words:
        name, piece, multi = register(sh, w)
        real.append((name, s))
        print(f"  {w:12s} -> {name} ({piece!r}{', multi-token: first piece only' if multi else ''})")
    rng = random.Random(a.seed)
    tag_words = " ".join(a.words)
    out = pathlib.Path(a.out) if a.out else HERE / "docs" / "runs" / f"wordsof-{'_'.join(w for w, _ in words)}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    runs = []

    def save(final):
        out.write_text(json.dumps({
            "params": {k: v for k, v in vars(a).items() if k != "url"}, "words": words, "band": [lo, hi],
            "layer": sh.layer, "model": info.get("model"), "example": sh.example_spec,
            "complete": final, "summary": summarize(runs, sh.example_spec), "runs": runs},
            ensure_ascii=False, indent=1))

    for rep in range(a.n):
        # the placebo: as many random words as real ones, fresh each pass
        rand = rng.sample(RANDOM_WORDS, len(words))
        rand_names = [(register(sh, w, "wordsof-rand")[0], s) for w, (_, s) in zip(rand, words)]
        conds = [("none", "base", None, None),
                 (tag_words, "real", stack(real, a.strength, lo, hi), None),
                 (tag_words, "placebo", stack(rand_names, a.strength, lo, hi), None)]
        if not a.no_said:
            conds.append((tag_words, "said", None, said_text(words)))
        for name, kind, steer, extra in conds:
            tag = (f"W-{kind}", f"r{rep}")
            w, raw, _ = sh.dream(ASK, tag, steering=steer, extra=extra)
            runs.append({"rep": rep, "name": name, "kind": kind, "world": w,
                         "random_words": rand if kind == "placebo" else None,
                         "raw": None if w else (raw or "")[:600], "link": w and world_link(ASK, w)})
            print(f"[{rep}] {kind:8s} {(w or {}).get('time')}/{(w or {}).get('weather')}/{(w or {}).get('ground')} "
                  f"{kinds_of(w) if w else 'did not parse'} · {str((w or {}).get('title'))!r}"
                  + (f"  (random: {', '.join(rand)})" if kind == "placebo" else ""), flush=True)
        for n, _ in rand_names:            # the server persists directions; the random ones do not stay
            try:
                sh.delete(f"/directions/{n}")
            except Exception:                 # noqa: BLE001
                pass
        save(final=False)
    save(final=True)
    print_summary(summarize(runs, sh.example_spec))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
