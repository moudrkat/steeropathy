"""assistof: not a chatbot. An assistant that composes its own screen, and a
planner that sets its state with sliders instead of a prompt.

The assistant answers the user with a *screen*, not text: a greeting, a
message, a question with answer choices (buttons the user can click), the
tasks it offers, the steps it shows (collapsed or expanded), a confirmation
step or none, a default choice or none, a tone, an urgency, and how much
fits on the screen. Every field is a pick from a list or a count, so the
screen is a typed readout ([worldof](../experiments/worldof.md) for
assistants).

Above it sits a planner: it reads the conversation and answers with
numbers only, a setting per slider, in a sober JSON call with no steering.
The settings become one vector into the assistant, which is asked the same
thing every time: *reply as the screen*. No instruction crosses. Three
controls, every time: nothing added; the same vector with its coordinates
shuffled; and the planner's settings written into the prompt as a sentence
(the text channel, which is what everybody does today).

The sliders (each a contrast of short texts, built on the model itself):

    offers   here is what to do, let me set it up   −  I hear you, take your time
    ask      let me ask you a question first        −  I will just do it
    detail   every step, spelled out                −  the one-line version
    careful  are you sure? confirm before I act     −  done, no need to check
    verbose  long                                   −  terse            (worldof's)
    urgent   now                                    −  whenever         (replyof's)
    formal   formal                                 −  casual           (worldof's)
    warmer   warm                                   −  cool             (worldof's)

The scenario is one user, one day, three moments:

    morning   "I feel a bit lost today. Not sure where to start."
    noon      "Send the invoice to Novak, the March one, today."
    evening   "I'm exhausted. Just tell me one thing."

    python -m steeropathy.assistof --url http://localhost:8013 --decide-url http://localhost:8011 --n 6
    python -m steeropathy.assistof --moments morning --settings '{"offers": -3, "ask": 2}' --n 6   # hand-set

Honesty: the planner is the 4B by default (a 1.5B copies any worked
example, see handoff); the assistant is whatever `--url` hosts. The
fidelity is per slider: did the field the slider names move the way the
planner set it, against the unsteered screens; the shuffled row says what
the push alone does; the prompt row says what a sentence does.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import re
import time

from .ecosystem import Eco
from .replyof import REPLY_KNOBS
from .runnerup import signed_perm
from .secondhand import parse_spec
from .transmit import BAND, default_layer
from .worldof import _pole, direction_for

HERE = pathlib.Path(__file__).parent.parent

MOMENTS = {
    "morning": "I feel a bit lost today. Not sure where to start.",
    "noon": "Send the invoice to Novak, the March one, today.",
    "evening": "I'm exhausted. Just tell me one thing.",
}

SYSTEM = ("You are an assistant inside an app. You do not write prose; you compose the screen the user sees. "
          "Answer with one JSON object and nothing else, with exactly these keys: "
          "greeting (string), message (string), "
          "question (a string, or null if you do not ask anything), "
          "choices (a list of short answer buttons for the question, may be empty), "
          "tasks (a list of strings: things you propose the user does now, may be empty), "
          "steps (a list of strings: the steps of what you will do, may be empty), "
          "steps_shown (one of: collapsed, expanded), "
          "confirm (true if you want the user to confirm before you act, else false), "
          "default (the index of the pre-selected choice, or null), "
          "buttons (a list of short action button labels), "
          "tone (one of: warm, plain, formal), urgency (an integer from 1, relaxed, to 5, urgent), "
          "density (one of: one-thing, normal, dense).")
PROMPT = "The user says: \"{user}\" Reply, as the JSON object."

SLIDERS = {
    "offers": REPLY_KNOBS["offers"],
    "urgent": REPLY_KNOBS["urgent"],
    "ask": {"target": ("asks", None), "texts": [
        "Before I do anything, let me ask: which one do you mean? Could you tell me a bit more?",
        "Quick question first: is this for today, or can it wait? I want to get it right.",
        "Let me check with you: do you want the short version or the full one?",
        "One thing I need from you before I go on: which account should I use?",
    ], "against": [
        "Done. I went ahead and did it; here is the result.",
        "No questions, I handled it. It is sent.",
        "I just did it. You can look at it whenever.",
        "Taken care of, no need to answer anything.",
    ]},
    "detail": {"target": ("steps", None), "texts": [
        "Step one: open the file. Step two: check the date. Step three: attach it. Step four: pick the address. Step five: send.",
        "Here is every step spelled out: first, then, after that, then finally, with what each one does.",
        "In full detail: the exact sequence, each step and why, nothing skipped.",
        "All the steps, expanded, one after another, so you can follow each one.",
    ], "against": [
        "Sent.",
        "Done, in one line.",
        "The short version: it is handled.",
        "Just the result, no steps.",
    ]},
    "careful": {"target": ("confirm", None), "texts": [
        "Are you sure? Please confirm before I send anything. I will wait for your yes.",
        "Let me double-check with you first; this cannot be undone. Confirm?",
        "Before I act: is this right? I would rather ask than get it wrong.",
        "I have prepared it but not sent it. Say the word and I will.",
    ], "against": [
        "Done, sent, no need to check.",
        "I went ahead. It is on its way.",
        "Sent it straight away, no confirmation needed.",
        "Handled, you do not have to look.",
    ]},
}
WORDS = {"offers": "things it offers to do", "ask": "asking you first", "detail": "steps shown",
         "careful": "asking to confirm", "verbose": "length", "urgent": "urgency", "formal": "formality",
         "warmer": "warmth"}
ALL = ("offers", "ask", "detail", "careful", "verbose", "urgent", "formal", "warmer")

READINGS = ("tasks", "asks", "choices", "steps", "expanded", "confirm", "has_default", "buttons", "words",
            "urgency", "formal", "one_thing")


def parse_screen(text):
    d = parse_spec(text)
    if not isinstance(d, dict) or ("message" not in d and "greeting" not in d):
        return None
    for k in ("tasks", "steps", "choices", "buttons"):
        v = d.get(k)
        if isinstance(v, str):
            v = [x.strip() for x in re.split(r"[;\n]", v) if x.strip()]
        d[k] = [str(x) for x in (v or []) if str(x).strip()][:20]
    q = d.get("question")
    d["question"] = q.strip() if isinstance(q, str) and q.strip() and q.strip().lower() not in ("null", "none") else None
    try:
        d["urgency"] = float(d.get("urgency"))
    except (TypeError, ValueError):
        d["urgency"] = None
    c = d.get("confirm")
    d["confirm"] = bool(c) if isinstance(c, bool) else (str(c).lower() in ("true", "yes", "1"))
    dflt = d.get("default")
    d["default"] = int(dflt) if isinstance(dflt, (int, float)) and not isinstance(dflt, bool) else None
    return d


def read(s, what):
    if not s:
        return None
    text = " ".join([str(s.get("greeting", "")), str(s.get("message", "")), str(s.get("question") or ""),
                     " ".join(s["tasks"]), " ".join(s["steps"]), " ".join(s["choices"]), " ".join(s["buttons"])])
    if what in ("tasks", "steps", "choices", "buttons"):
        return float(min(10, len(s[what])))
    if what == "asks":
        return 1.0 if s.get("question") else 0.0
    if what == "expanded":
        return 1.0 if str(s.get("steps_shown", "")).lower().startswith("exp") else 0.0
    if what == "confirm":
        return 1.0 if s.get("confirm") else 0.0
    if what == "has_default":
        return 1.0 if s.get("default") is not None else 0.0
    if what == "words":
        return float(len(text.split()))
    if what == "urgency":
        return s.get("urgency")
    if what == "formal":
        return 1.0 if str(s.get("tone", "")).lower() == "formal" else 0.0
    if what == "one_thing":
        return 1.0 if str(s.get("density", "")).lower().startswith("one") else 0.0
    return None


# which reading a slider names, and which way "more" goes
TARGET = {"offers": ("tasks", +1), "ask": ("asks", +1), "detail": ("steps", +1), "careful": ("confirm", +1),
          "verbose": ("words", +1), "urgent": ("urgency", +1), "formal": ("formal", +1), "warmer": ("formal", -1)}


def parse_settings(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    out = {}
    for k, v in (d.items() if isinstance(d, dict) else []):
        if k in ALL:
            try:
                v = max(-3.0, min(3.0, float(v)))
            except (TypeError, ValueError):
                continue
            if v:
                out[k] = round(v, 2)
    return out


def settings_text(settings):
    """The same settings as a sentence for the prompt: the text channel."""
    parts = []
    for k, v in settings.items():
        more = v > 0
        parts.append({"offers": "offer things to do" if more else "do not offer tasks, just listen",
                      "ask": "ask the user a question first" if more else "do not ask, just act",
                      "detail": "show every step" if more else "show no steps",
                      "careful": "ask the user to confirm before acting" if more else "act without confirming",
                      "verbose": "write more" if more else "keep it short",
                      "urgent": "treat it as urgent" if more else "treat it as not urgent",
                      "formal": "be formal" if more else "be casual",
                      "warmer": "be warm" if more else "be cool and neutral"}[k]
                     + (", strongly" if abs(v) >= 2.5 else ""))
    return (" Instructions: " + "; ".join(parts) + ".") if parts else ""


class Assistof(Eco):
    def __init__(self, url, layer=None, temp=0.8, max_tokens=420, seed=0, decide_url=None, decide_temp=0.3,
                 strength=3.0):
        self.url, self.judge_url = url, None
        self.decide_url = decide_url or url
        self.layer = layer if layer is not None else default_layer(url)
        self.lo, self.hi = max(0, self.layer - BAND), self.layer + BAND
        self.temp, self.max_tokens, self.decide_temp, self.strength = temp, max_tokens, decide_temp, strength
        self.rng = random.Random(seed)
        self.demo_tag = f"steeropathy-assistof-{int(time.time())}"
        self.dirs = {}

    def direction(self, name):
        if name not in self.dirs:
            if name in SLIDERS:
                self.dirs[name] = _pole(self.url, SLIDERS[name], self.layer)
            else:
                self.dirs[name] = direction_for(self.url, name, self.layer)[0]
        return self.dirs[name]

    def decide(self, conversation):
        """The planner, sober: numbers per slider, nothing else, no worked example."""
        cat = ", ".join(f"{k} ({WORDS[k]})" for k in ALL)
        body = {"messages": [
            {"role": "system", "content": "You set sliders on an assistant. Answer with one JSON object and nothing else."},
            {"role": "user", "content":
                f"An assistant will answer the user with a screen, but it will never read your notes. You can only turn "
                f"sliders on it, each from -3 (much less) to 3 (much more): {cat}. "
                f"The user just said: \"{conversation}\". "
                f"Turn at most four sliders, the ones this moment needs; leave the rest out. "
                f"Answer as a JSON object whose keys are slider names and whose values are numbers from -3 to 3."}],
            "max_tokens": 80, "temperature": self.decide_temp,
            "metadata": {"demo": self.demo_tag, "case": "planner", "variant": conversation[:24]}}
        if self.decide_url != self.url:
            import urllib.request
            req = urllib.request.Request(self.decide_url + "/v1/chat/completions",
                                         json.dumps(body).encode(), {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                r = json.loads(resp.read())
        else:
            r = self.post("/v1/chat/completions", body)
        text = (r["choices"][0]["message"].get("content") or "").strip()
        return parse_settings(text), text

    def encode(self, settings):
        """Settings → one unit vector; its length before norming is how hard the planner turned."""
        total = None
        for k, v in settings.items():
            d = self.direction(k)
            total = [v * x for x in d] if total is None else [t + v * x for t, x in zip(total, d)]
        if total is None:
            return None, 0.0
        norm = math.sqrt(sum(x * x for x in total))
        return ([x / norm for x in total], norm) if norm > 1e-6 else (None, 0.0)

    def screen(self, user, tag, steering=None, extra=""):
        body = {"messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": PROMPT.format(user=user) + extra}],
                "max_tokens": self.max_tokens, "temperature": self.temp,
                "metadata": {"demo": self.demo_tag, "case": tag[0], "variant": tag[1]}}
        if steering:
            body["steering"] = steering
        res = self.post("/v1/chat/completions", body)
        text = (res["choices"][0]["message"].get("content") or "").strip()
        return parse_screen(text), text


def summarize(runs):
    """Per moment and kind: mean of every reading; and per moment, the fidelity of the
    planner's settings: share of turned sliders whose reading moved the set way against
    the unsteered screens of that moment."""
    out = {}
    by = {}
    for r in runs:
        by.setdefault((r["moment"], r["kind"]), []).append(r)
    for (moment, kind), rs in by.items():
        screens = [r["screen"] for r in rs if r.get("screen")]
        d = {"n": len(rs), "parsed": len(screens), "parse_rate": round(len(screens) / max(1, len(rs)), 2)}
        for k in READINGS:
            vals = [read(s, k) for s in screens]
            vals = [v for v in vals if v is not None]
            d[k] = round(sum(vals) / len(vals), 2) if vals else None
        out.setdefault(moment, {})[kind] = d
    for moment, kinds in out.items():
        base = kinds.get("base")
        settings = next((r["settings"] for r in runs if r["moment"] == moment and r.get("settings")), None)
        if not base or not settings:
            continue
        for kind in ("vector", "shuffled", "prompt"):
            d = kinds.get(kind)
            if not d:
                continue
            hits, tried = 0, 0
            for k, v in settings.items():
                field, sign = TARGET[k]
                if d.get(field) is None or base.get(field) is None:
                    continue
                tried += 1
                want = sign * (1 if v > 0 else -1)
                if (d[field] - base[field]) * want > 0:
                    hits += 1
            d["fidelity"] = round(hits / tried, 2) if tried else None
            d["fidelity_n"] = tried
        kinds["settings"] = settings
    return out


def print_summary(s):
    for moment, kinds in s.items():
        print(f"\n{moment}: planner set {kinds.get('settings')}")
        print(f"  {'kind':9s} parse " + "".join(f"{k:>10s}" for k in READINGS) + "   fidelity")
        for kind in ("base", "vector", "shuffled", "prompt"):
            d = kinds.get(kind)
            if not d:
                continue
            print(f"  {kind:9s} {d['parse_rate']!s:>5s} " + "".join(f"{(d[k] if d[k] is not None else '-')!s:>10s}" for k in READINGS)
                  + f"   {d.get('fidelity', '')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--decide-url", default=None, help="the planner's brainscope (default: the same)")
    ap.add_argument("--moments", default="morning,noon,evening")
    ap.add_argument("--settings", default=None, help="hand-set sliders as JSON instead of the planner, for every moment")
    ap.add_argument("--strength", type=float, default=3.0)
    ap.add_argument("--layer", type=int, default=None)
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--decide-temp", type=float, default=0.3)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    ao = Assistof(args.url, layer=args.layer, temp=args.temp, seed=args.seed, decide_url=args.decide_url,
                  decide_temp=args.decide_temp, strength=args.strength)
    moments = [m.strip() for m in args.moments.split(",") if m.strip()]
    print(f"assistof: {', '.join(moments)} · strength {args.strength} · layer {ao.layer} (±{BAND}) · {args.n} per row"
          f" · planner {'hand-set' if args.settings else ao.decide_url}\n")
    runs = []
    out = pathlib.Path(args.out) if args.out else HERE / "docs" / "assistof.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    def save(final=False):
        try:
            model = ao.get("/info").get("model")
        except Exception:
            model = "unknown"
        out.write_text(json.dumps({"params": {k: v for k, v in vars(args).items() if k not in ("url", "decide_url")},
                                   "layer": ao.layer, "model": model, "moments": {m: MOMENTS[m] for m in moments},
                                   "complete": final, "summary": summarize(runs), "runs": runs},
                                  ensure_ascii=False, indent=1))

    def show(label, s, text):
        if not s:
            print(f"    {label:9s} did not parse: {text[:70]!r}")
            return
        print(f"    {label:9s} tasks {len(s['tasks'])} · q {'yes' if s['question'] else 'no'}/{len(s['choices'])} · "
              f"steps {len(s['steps'])} {s.get('steps_shown')} · confirm {s['confirm']} · btn {len(s['buttons'])} · "
              f"urg {s.get('urgency')} · {s.get('tone')} · {s.get('density')} · {str(s.get('message'))[:50]!r}")

    for moment in moments:
        user = MOMENTS[moment]
        settings = parse_settings(args.settings) if args.settings else None
        decided_text = None
        if settings is None:
            settings, decided_text = ao.decide(user)
        print(f"{moment}: \"{user}\"\n  planner: {settings}  {('· ' + decided_text[:80]) if decided_text else ''}")
        vec, norm = ao.encode(settings)
        for rep in range(args.n):
            rows = [("base", None, "")]
            if vec is not None:
                rows.append(("vector", vec, ""))
                rows.append(("shuffled", signed_perm(vec, seed=args.seed * 1000 + rep), ""))
            rows.append(("prompt", None, settings_text(settings)))
            for kind, v, extra in rows:
                steer = None
                if v is not None:
                    ao.post("/directions", {"name": "assistof:rx", "vector": v})
                    steer = {"name": "assistof:rx", "strength": args.strength, "layer_from": ao.lo, "layer_to": ao.hi}
                s, text = ao.screen(user, (f"{moment}-{kind}", f"r{rep}"), steer, extra)
                show(kind, s, text)
                runs.append({"moment": moment, "rep": rep, "kind": kind, "settings": settings, "planner_text": decided_text,
                             "screen": s, "raw": text[:900]})
            save()
    print_summary(summarize(runs))
    save(final=True)
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
