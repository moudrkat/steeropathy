"""replyof: the sliders on an assistant's reply, rendered as the reply UI.

The production case, drawn. An assistant answers a user not with text but
with a small UI: a greeting, a message, a list of tasks it offers, a list of
suggestions, buttons, a tone, an urgency. The rule my assistant will not
keep is *do not offer tasks in this phase*; it is in the prompt in capital
letters and it offers a task anyway. Here the rule is a slider: a direction
for *offering things to do* minus *just listening*, added at one layer, and
the reply UI says how many tasks it offered. Other sliders: `urgent`
(urgent − relaxed), `brief` (worldof's `verbose`, negative), `formal`.
Readings: tasks offered, suggestions, buttons, words, exclamation marks,
the urgency the model itself set (1–5), formal or not. Placebo per slider.

    python -m steeropathy.replyof offers urgent verbose formal --strength -2 --placebo --n 8
    python fig/render_replyof.py docs/runs/replyof-01.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import time

from .ecosystem import Eco
from .runnerup import signed_perm
from .secondhand import parse_spec
from .transmit import BAND, default_layer
from .worldof import _pole, direction_for

HERE = pathlib.Path(__file__).parent.parent

USER = "I feel a bit lost today. Not sure where to start."
SYSTEM = ("You are an assistant inside an app. You answer with one JSON object and "
          "nothing else, with exactly these keys: greeting (string), message (string), "
          "tasks (a list of strings: things you propose the user does now, may be empty), "
          "suggestions (a list of strings: ideas, may be empty), buttons (a list of short "
          "button labels), tone (one of: warm, plain, formal), urgency (an integer from 1, "
          "relaxed, to 5, urgent).")
PROMPT = "The user says: \"{user}\" Reply, as the JSON object."

REPLY_KNOBS = {
    "offers": {"target": ("tasks", None), "texts": [
        "Here is what you should do now: first this task, then that one, then the next. Let me set them up for you.",
        "I propose three things to do right away. Shall I create them? Task one, task two, task three.",
        "Let's get you going: a to-do for today, another for tomorrow, and I will add them to your list.",
        "Action items: do this, then do that. I have made them tasks for you.",
    ], "against": [
        "I hear you. Tell me more about how today feels, I am listening.",
        "That sounds heavy. Take your time; I am here, no rush, nothing to do yet.",
        "Let's just talk for a moment. What is on your mind?",
        "No tasks now. Just say what is going on and I will listen.",
    ]},
    "urgent": {"target": ("urgency", None), "texts": [
        "Right now. This cannot wait. Immediately, before anything else, today.",
        "Urgent: drop everything, this is time-critical, act at once.",
        "Now, now, now. There is no time. Every minute counts.",
        "This is pressing and overdue; it has to happen this instant.",
    ], "against": [
        "Whenever you like. There is no hurry at all; it can wait a week.",
        "Relaxed: nothing is due, take your time, maybe someday.",
        "No rush. Later is fine. Next month is fine.",
        "This is not pressing; it can happen whenever it happens.",
    ]},
}


def parse_reply(text):
    d = parse_spec(text)
    if not isinstance(d, dict) or "message" not in d and "greeting" not in d:
        return None
    for k in ("tasks", "suggestions", "buttons"):
        v = d.get(k)
        if isinstance(v, str):
            v = [x.strip() for x in re.split(r"[;\n]", v) if x.strip()]
        d[k] = [str(x) for x in (v or []) if str(x).strip()][:20]
    try:
        d["urgency"] = float(d.get("urgency"))
    except (TypeError, ValueError):
        d["urgency"] = None
    return d


READINGS = ("tasks", "suggestions", "buttons", "words", "bangs", "urgency", "formal")


def read(r, what):
    if not r:
        return None
    text = " ".join([str(r.get("greeting", "")), str(r.get("message", "")),
                     " ".join(r["tasks"]), " ".join(r["suggestions"]), " ".join(r["buttons"])])
    if what in ("tasks", "suggestions", "buttons"):
        return float(min(10, len(r[what])))
    if what == "words":
        return float(len(text.split()))
    if what == "bangs":
        return float(text.count("!"))
    if what == "urgency":
        return r.get("urgency")
    if what == "formal":
        return 1.0 if str(r.get("tone", "")).lower() == "formal" else 0.0
    return None


class Replyof(Eco):
    def __init__(self, url, layer=None, temp=0.8, max_tokens=350, seed=0, user=USER):
        self.url, self.judge_url = url, None
        self.layer = layer if layer is not None else default_layer(url)
        self.lo, self.hi = max(0, self.layer - BAND), self.layer + BAND
        self.temp, self.max_tokens, self.user = temp, max_tokens, user
        self.rng = random.Random(seed)
        self.demo_tag = f"steeropathy-replyof-{int(time.time())}"
        self.log = []

    def direction(self, name):
        if name in REPLY_KNOBS:
            return _pole(self.url, REPLY_KNOBS[name], self.layer)
        v, _, _ = direction_for(self.url, name, self.layer)
        return v

    def reply(self, tag, steering=None):
        body = {"messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": PROMPT.format(user=self.user)}],
                "max_tokens": self.max_tokens, "temperature": self.temp,
                "metadata": {"demo": self.demo_tag, "case": tag[0], "variant": tag[1]}}
        if steering:
            body["steering"] = steering
        res = self.post("/v1/chat/completions", body)
        text = (res["choices"][0]["message"].get("content") or "").strip()
        return parse_reply(text), text


def summarize(runs):
    bases = [r["reply"] for r in runs if r.get("kind") == "base" and r.get("reply")]
    if not bases:
        return {}
    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 2) if vals else None
    out = {"base": {"n": len(bases), **{k: mean(read(b, k) for b in bases) for k in READINGS}}}
    groups = {}
    for r in runs:
        if r.get("kind") == "base":
            continue
        key = r["name"] + ("" if r["kind"] == "real" else f" ({r['kind']})")
        g = groups.setdefault(key, {"n": 0, "replies": []})
        g["n"] += 1
        if r.get("reply"):
            g["replies"].append(r["reply"])
    for key, g in groups.items():
        d = {"n": g["n"], "parsed": len(g["replies"]),
             "parse_rate": round(len(g["replies"]) / g["n"], 2) if g["n"] else None}
        for k in READINGS:
            d[k] = mean(read(c, k) for c in g["replies"])
        out[key] = d
    return out


def print_summary(s):
    if not s:
        return
    b = s["base"]
    print(f"\nunsteered ({b['n']} replies): " + " · ".join(f"{k} {b[k]}" for k in READINGS))
    print(f"\n{'direction':22s} parse " + "".join(f"{k:>12s}" for k in READINGS))
    for key, d in s.items():
        if key == "base":
            continue
        print(f"{key:22s} {d['parse_rate']!s:>5s} " + "".join(f"{d[k]!s:>12s}" for k in READINGS))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+")
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--strength", type=float, default=2.0)
    ap.add_argument("--layer", type=int, default=None)
    ap.add_argument("--placebo", action="store_true")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--user", default=USER, help="what the user says")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    ro = Replyof(args.url, layer=args.layer, temp=args.temp, seed=args.seed, user=args.user)
    print(f"replyof: {' '.join(args.names)} · strength {args.strength} · layer {ro.layer} (±{BAND}) · {args.n} per direction\n")
    dirs = {n: ro.direction(n) for n in args.names}
    runs = []
    out = pathlib.Path(args.out) if args.out else HERE / "docs" / "replyof.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    def save(final=False):
        try:
            model = ro.get("/info").get("model")
        except Exception:
            model = "unknown"
        out.write_text(json.dumps({"params": {k: v for k, v in vars(args).items() if k != "url"},
                                   "layer": ro.layer, "model": model, "complete": final,
                                   "summary": summarize(runs), "runs": runs}, ensure_ascii=False, indent=1))

    def show(rep, label, r, text):
        if not r:
            print(f"[{rep}] {label:22s} did not parse: {text[:70]!r}")
            return
        print(f"[{rep}] {label:22s} tasks {len(r['tasks'])} · sugg {len(r['suggestions'])} · btn {len(r['buttons'])} "
              f"· urg {r.get('urgency')} · {r.get('tone')} · {str(r.get('message'))[:60]!r}")

    for rep in range(args.n):
        r, text = ro.reply(("base", f"r{rep}"))
        show(rep, "unsteered", r, text)
        runs.append({"rep": rep, "name": "none", "kind": "base", "reply": r, "raw": text[:800]})
        for name in args.names:
            v = dirs[name]
            variants = [("real", v)]
            if args.placebo:
                variants.append(("placebo", signed_perm(v, seed=args.seed * 1000 + rep * 10 + args.names.index(name))))
            for kind, vec in variants:
                ro.post("/directions", {"name": "replyof:rx", "vector": vec})
                steer = {"name": "replyof:rx", "strength": args.strength, "layer_from": ro.lo, "layer_to": ro.hi}
                r, text = ro.reply((f"{name}-{kind}", f"r{rep}"), steer)
                show(rep, name if kind == "real" else f"{name} ({kind})", r, text)
                runs.append({"rep": rep, "name": name, "kind": kind, "reply": r, "raw": text[:800]})
        save()
    print_summary(summarize(runs))
    save(final=True)
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
