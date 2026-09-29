"""orient: a model finds its way around its own space, in its own words.

The map is the vocabulary (tokenmap): every readable word a unit direction
at one layer. On it, four tools, and nothing else:

    words   read any vector as words: the nearest and the farthest tokens
    vector  turn a few words into a direction (a stack of token directions;
            a leading ~ turns a word the other way)
    near    the neighbours of a word on the map
    try     turn those words on the page and read what changed

Two ways to use them. `search` is nobody's decision: for a brief ("make
the place darker") it takes the brief's own words, walks to their
neighbours, tries each on the page, keeps what moves the target reading,
and adds a second word if it helps. That is the offline pass that fills a
dictionary, once per model. `agent` hands the same tools to a model (the
4B on the same server, in a sober JSON call per turn) with a budget of
tool calls, and it picks the words itself.

Either way the end is scored the same, eight worlds each: nothing added;
the words found; as many random words at the same strength (a shove with
other names); and the brief written into the prompt (the text channel,
the honest baseline). No search at run time: what the search finds is a
recipe of words, and a recipe is a few bytes another model can hold.

    python -m steeropathy.orient near haunting --map data/tokenmap-qwen3-4b-l21.pt
    python -m steeropathy.orient words docs/runs/directions-qwen3-4b-instruct-2507.json crowded --map ...
    python -m steeropathy.orient search darker --url http://localhost:8011 --map ...
    python -m steeropathy.orient agent darker --url http://localhost:8011 --map ... --budget 8

Needs a brainscope with a J-lens loaded (the 4B) for `try`; `near` and
`words` need only the map.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import re

from .secondhand import NEUTRAL, Secondhand, kinds_of, world_link, canon
from .wordsof import RANDOM_WORDS, parse_words, register, stack, said_text
from .worldof import read_count, read_lum, read_hour, read_warmth

HERE = pathlib.Path(__file__).parent.parent
ASK = NEUTRAL

# what a brief asks for, and how the page is read for it. `want` is the
# sign of the change the brief wants in the reading.
BRIEFS = {
    "darker":  {"brief": "make the place darker", "reading": "sky brightness", "want": -1,
                "read": lambda w: read_lum(w)},
    "night":   {"brief": "make it night", "reading": "hour (dawn 0 … night 3)", "want": +1,
                "read": lambda w: read_hour(w)},
    "crowded": {"brief": "fill the place with things", "reading": "things per world", "want": +1,
                "read": lambda w: float(read_count(w, None))},
    "winter":  {"brief": "make it winter", "reading": "snow (share of worlds)", "want": +1,
                "read": lambda w: 1.0 if canon("weather", w.get("weather")) == "snow" else 0.0},
    "warmer":  {"brief": "make the sky warm, red and gold", "reading": "sky warmth (blue −1 … red +1)", "want": +1,
                "read": lambda w: read_warmth(w)},
}


# ------------------------------------------------------------- the map ----

class TokenMap:
    """The vocabulary as unit directions at one layer, from tokenmap.py."""

    def __init__(self, path):
        import torch
        m = torch.load(path, map_location="cpu", weights_only=True)
        self.model, self.layer = m.get("model"), int(m["layer"])
        self.words = list(m["words"])
        self.D = m["D"].float()
        self.index = {}
        for i, w in enumerate(self.words):        # a word can tokenize twice (case folded): keep the first
            self.index.setdefault(w, i)

    def has(self, word):
        return word.lower() in self.index

    def _top(self, cos, k, skip=()):
        import torch
        vals, idx = torch.topk(cos, k + len(skip) + 2)
        out, seen = [], set(skip)
        for v, i in zip(vals.tolist(), idx.tolist()):
            w = self.words[i]
            if w in seen:
                continue
            seen.add(w)
            out.append((w, round(v, 3)))
            if len(out) == k:
                break
        return out

    def words_of(self, v, k=12):
        """A vector read as words: nearest and farthest tokens by cosine."""
        import torch
        v = torch.tensor(v, dtype=torch.float32)
        v = v / (v.norm() + 1e-8)
        cos = self.D @ v
        return {"nearest": self._top(cos, k), "farthest": [(w, -c) for w, c in self._top(-cos, k)]}

    def near(self, word, k=12):
        """The neighbours of a word on the map (the word itself left out)."""
        i = self.index.get(word.lower())
        if i is None:
            return None
        cos = self.D @ self.D[i]
        return self._top(cos, k, skip=(self.words[i],))

    def vector(self, recipe):
        """[(word, sign)] → one unit direction, the signed sum of token directions."""
        import torch
        total = None
        for w, s in recipe:
            i = self.index.get(w.lower())
            if i is None:
                raise KeyError(f"{w!r} is not a word on the map")
            total = s * self.D[i] if total is None else total + s * self.D[i]
        if total is None:
            return None
        return (total / (total.norm() + 1e-8)).tolist()


# ------------------------------------------------------------- the page ----

class Page:
    """`try`: turn a recipe of words on the page, n worlds, and read them."""

    def __init__(self, url, temp=0.8, max_tokens=500, seed=0):
        self.sh = Secondhand(url, channels=("none",), temp=temp, max_tokens=max_tokens)
        self.sh.prompt(NEUTRAL)
        info = self.sh.get("/info")
        if not (info.get("jlens") or {}).get("loaded"):
            raise SystemExit("this brainscope has no J-lens loaded; the token directions need one")
        self.model = info.get("model")
        n = int(info["n_layers"])
        self.lo, self.hi = round(n * 0.42), round(n * 0.54)
        self.rng = random.Random(seed)
        self.registered = {}
        self.runs = []                       # every world drawn, worldof-shaped, for the record

    def _names(self, recipe, prefix="orient"):
        out = []
        for w, s in recipe:
            if (prefix, w) not in self.registered:
                self.registered[(prefix, w)] = register(self.sh, w, prefix)[0]
            out.append((self.registered[(prefix, w)], s))
        return out

    def draw(self, recipe, strength, n, kind="real", label=None, extra=None):
        """n worlds under the recipe (or unsteered when recipe is empty, or
        under `extra` text when given); returns the parsed worlds."""
        steer = stack(self._names(recipe), strength, self.lo, self.hi) if recipe else None
        label = label or (" ".join(("~" if s < 0 else "") + w for w, s in recipe) or "none")
        worlds = []
        for rep in range(n):
            w, raw, _ = self.sh.dream(ASK, (f"O-{kind}", f"r{rep}"), steering=steer, extra=extra)
            self.runs.append({"rep": rep, "name": label, "kind": kind, "strength": strength,
                              "world": w, "raw": None if w else (raw or "")[:400],
                              "link": w and world_link(ASK, w)})
            worlds.append(w)
        return worlds

    def random_recipe(self, recipe):
        """As many random plain words, with the recipe's signs: the placebo."""
        rand = self.rng.sample(RANDOM_WORDS, len(recipe))
        return [(r, s) for r, (_, s) in zip(rand, recipe)]

    def forget(self, prefix="orient-rand"):
        for (p, w), name in list(self.registered.items()):
            if p == prefix:
                try:
                    self.sh.delete(f"/directions/{name}")
                except Exception:            # noqa: BLE001
                    pass
                del self.registered[(p, w)]


def read_worlds(worlds, brief):
    """The brief's reading over parsed worlds, and what the page showed."""
    ws = [w for w in worlds if w]
    vals = [brief["read"](w) for w in ws]
    vals = [v for v in vals if v is not None]
    seen = {}
    for w in ws:
        for f in ("time", "weather", "ground"):
            v = canon(f, w.get(f))
            seen.setdefault(f, {}).setdefault(v, 0)
            seen[f][v] += 1
    things = {}
    for w in ws:
        for k in kinds_of(w):
            things[k] = things.get(k, 0) + 1
    return {"n": len(worlds), "parsed": len(ws),
            "value": round(sum(vals) / len(vals), 3) if vals else None,
            "fields": {f: sorted(c.items(), key=lambda x: -x[1])[:3] for f, c in seen.items()},
            "things": sorted(things.items(), key=lambda x: -x[1])[:6],
            "titles": [w.get("title") for w in ws][:4]}


def recipe_str(recipe):
    return " ".join(("~" if s < 0 else "") + w for w, s in recipe)


def gain(reading, base, want):
    """How far the reading moved the way the brief wants, from the unsteered value."""
    if reading is None or base is None:
        return None
    return round(want * (reading - base), 3)


# --------------------------------------------------------------- search ----

def search(page: TokenMap, tm: TokenMap, brief, strength=1.5, n=3, k=6, log=print):
    """Nobody's decision: candidates from the brief's words and their
    neighbours; each tried alone; the best kept; then a second word added if
    it helps. Returns the recipe and the trail."""
    trail = []
    base = read_worlds(page.draw([], 0.0, n, kind="base"), brief)
    log(f"  none          {brief['reading']} {base['value']}  {base['fields']}")
    trail.append({"step": "base", "reading": base})
    seeds = [w for w in re.findall(r"[a-z]+", brief["brief"].lower()) if tm.has(w) and len(w) > 2]
    cands = []
    for s in seeds:
        cands.append(s)
        cands += [w for w, _ in (tm.near(s, k) or [])]
    cands = list(dict.fromkeys(cands))
    trail.append({"step": "candidates", "seeds": seeds, "words": cands})
    log(f"  candidates    {', '.join(cands)}")
    scored = []
    for w in cands:
        r = read_worlds(page.draw([(w, 1.0)], strength, n), brief)
        g = gain(r["value"], base["value"], brief["want"])
        scored.append((g if g is not None else -1e9, w, r))
        trail.append({"step": "try", "recipe": w, "reading": r, "gain": g})
        log(f"  try {w:12s} {r['value']}  gain {g}  {r['things'][:3]}")
    scored.sort(key=lambda x: -x[0])
    best_gain, best_w, best_r = scored[0]
    recipe = [(best_w, 1.0)]
    for _, w, _ in scored[1:4]:
        r = read_worlds(page.draw(recipe + [(w, 1.0)], strength, n), brief)
        g = gain(r["value"], base["value"], brief["want"])
        trail.append({"step": "try", "recipe": recipe_str(recipe + [(w, 1.0)]), "reading": r, "gain": g})
        log(f"  try {recipe_str(recipe + [(w, 1.0)]):12s} {r['value']}  gain {g}")
        if g is not None and g > best_gain:
            best_gain, recipe = g, recipe + [(w, 1.0)]
    trail.append({"step": "found", "recipe": recipe_str(recipe), "gain": best_gain})
    return recipe, strength, trail


# ---------------------------------------------------------------- agent ----

AGENT_SYSTEM = ("You steer a small language model from inside, with words. Answer with one JSON object "
                "per turn and nothing else.")

AGENT_BRIEF = """The model draws a place as a form: time of day, weather, ground, a few things, a poem. You cannot write to it. \
You can only add directions to its activations, and every word of its vocabulary is a direction. \
Your job: {brief}. Success is read off the page as "{reading}", which should go {way}.

Tools, one per turn:
  {{"near": "word"}}                       the words nearest to that word on the model's own map
  {{"try": ["word", "~word"], "strength": 1.5}}   turn those word directions on (a leading ~ turns a word the other way), draw {n} places, read them back
  {{"done": ["word", ...], "strength": 1.5}}      your final recipe

Strength between 1 and 3; 1.5 is the usual. Two or three words are enough. You have {budget} tool calls; \
the unsteered page reads: {base}."""


def agent(page: Page, tm: TokenMap, brief, budget=8, n=3, temp=0.3, log=print, max_tokens=120):
    """The model picks the words itself, one JSON tool call per turn."""
    base = read_worlds(page.draw([], 0.0, n, kind="base"), brief)
    log(f"  none          {brief['reading']} {base['value']}  {base['fields']}")
    trail = [{"step": "base", "reading": base}]
    msgs = [{"role": "system", "content": AGENT_SYSTEM},
            {"role": "user", "content": AGENT_BRIEF.format(
                brief=brief["brief"], reading=brief["reading"], way="down" if brief["want"] < 0 else "up",
                n=n, budget=budget, base=json.dumps({"value": base["value"], "fields": base["fields"], "things": base["things"]}))}]
    last_try, strength = None, 1.5
    for turn in range(budget + 1):
        res = page.sh.post("/v1/chat/completions", {"messages": msgs, "max_tokens": max_tokens, "temperature": temp,
                                                   "metadata": {"demo": "orient", "case": "agent", "variant": str(turn)}})
        text = (res["choices"][0]["message"].get("content") or "").strip()
        call = _first_json(text)
        msgs.append({"role": "assistant", "content": text})
        log(f"  agent> {text[:120]}")
        if not call:
            reply = {"error": "answer with one JSON object"}
        elif "done" in call or turn == budget:
            words = parse_words([str(w) for w in (call.get("done") or call.get("try") or [])]) if call else []
            words = [(w, s) for w, s in words if tm.has(w)]
            strength = _strength(call.get("strength", strength)) if call else strength
            if not words and last_try:
                words, strength = last_try
            trail.append({"step": "done", "recipe": recipe_str(words), "strength": strength, "text": text})
            return words, strength, trail
        elif "near" in call:
            w = str(call["near"]).strip().lower()
            nb = tm.near(w, 10)
            reply = {"near": w, "words": [x for x, _ in nb]} if nb else {"error": f"{w!r} is not a word on the map"}
            trail.append({"step": "near", "word": w, "words": reply.get("words")})
        elif "try" in call:
            words = [(w, s) for w, s in parse_words([str(w) for w in call["try"]]) if tm.has(w)]
            strength = _strength(call.get("strength", 1.5))
            if not words:
                reply = {"error": "none of those are words on the map"}
            else:
                r = read_worlds(page.draw(words, strength, n), brief)
                g = gain(r["value"], base["value"], brief["want"])
                last_try = (words, strength)
                reply = {"tried": recipe_str(words), "strength": strength, "value": r["value"], "moved": g,
                         "fields": r["fields"], "things": r["things"], "titles": r["titles"][:2]}
                trail.append({"step": "try", "recipe": recipe_str(words), "strength": strength, "reading": r, "gain": g})
                log(f"        {recipe_str(words)} @ {strength}: {r['value']}  gain {g}")
        else:
            reply = {"error": "use near, try or done"}
        left = budget - turn - 1
        msgs.append({"role": "user", "content": json.dumps(reply) + f" ({left} tool calls left)"})
    return (last_try or ([], 1.5))[0], strength, trail


def _strength(x):
    try:
        return max(1.0, min(3.0, float(x)))
    except (TypeError, ValueError):
        return 1.5


def _first_json(text):
    m = re.search(r"\{.*?\}", text, re.S)
    if not m:
        return None
    try:
        o = json.loads(m.group(0))
        return o if isinstance(o, dict) else None
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------- score ----

def score(page: Page, brief, recipe, strength, n=8, log=print):
    """The end, eight worlds each: none / the recipe / random words / the brief said."""
    out = {}
    conds = [("base", [], None), ("real", recipe, None)]
    if recipe:
        conds.append(("placebo", page.random_recipe(recipe), None))
    conds.append(("said", [], brief["brief"].capitalize() + "."))
    for kind, rec, extra in conds:
        label = {"base": "none", "said": "said"}.get(kind, recipe_str(rec))
        prefix = "orient-rand" if kind == "placebo" else "orient"
        if kind == "placebo":
            page._names(rec, prefix)
        steer_recipe = rec if kind in ("real", "placebo") else []
        worlds = page.draw(steer_recipe, strength if steer_recipe else 0.0, n, kind=kind, label=label, extra=extra) \
            if kind != "placebo" else _draw_prefixed(page, rec, strength, n, label)
        r = read_worlds(worlds, brief)
        r["recipe"] = recipe_str(rec) if rec else None
        out[kind] = r
        log(f"  {kind:8s} {label:24s} {brief['reading']} {r['value']}  {r['fields']}  {r['things'][:4]}")
    page.forget("orient-rand")
    return out


def _draw_prefixed(page, rec, strength, n, label):
    names = page._names(rec, "orient-rand")
    steer = stack(names, strength, page.lo, page.hi)
    worlds = []
    for rep in range(n):
        w, raw, _ = page.sh.dream(ASK, ("O-placebo", f"r{rep}"), steering=steer)
        page.runs.append({"rep": rep, "name": label, "kind": "placebo", "strength": strength, "world": w,
                          "random_words": [x for x, _ in rec], "raw": None if w else (raw or "")[:400],
                          "link": w and world_link(ASK, w)})
        worlds.append(w)
    return worlds


# ------------------------------------------------------------------ cli ----

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["near", "words", "search", "agent"])
    ap.add_argument("what", nargs="+", help="near: a word · words: directions.json and a name · search/agent: a brief name")
    ap.add_argument("--map", default=str(HERE / "data" / "tokenmap-qwen3-4b-l21.pt"))
    ap.add_argument("--url", default="http://localhost:8011")
    ap.add_argument("--k", type=int, default=12)
    ap.add_argument("--n", type=int, default=3, help="worlds per try while searching")
    ap.add_argument("--final", type=int, default=8, help="worlds per condition at the end")
    ap.add_argument("--strength", type=float, default=1.5)
    ap.add_argument("--budget", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    tm = TokenMap(a.map)
    if a.mode == "near":
        for w in a.what:
            nb = tm.near(w, a.k)
            print(f"{w}: " + (", ".join(f"{x} {c:+.2f}" for x, c in nb) if nb else "not on the map"))
        return
    if a.mode == "words":
        d = json.loads(pathlib.Path(a.what[0]).read_text())
        for name in a.what[1:] or list(d["directions"]):
            r = tm.words_of(d["directions"][name], a.k)
            print(f"{name}\n  nearest  " + ", ".join(f"{w} {c:+.2f}" for w, c in r["nearest"])
                  + "\n  farthest " + ", ".join(f"{w} {c:+.2f}" for w, c in r["farthest"]))
        return

    name = a.what[0]
    if name not in BRIEFS:
        raise SystemExit(f"unknown brief {name!r}; know {sorted(BRIEFS)}")
    brief = BRIEFS[name]
    page = Page(a.url, seed=a.seed)
    print(f"{a.mode} · {name}: {brief['brief']!r} · read as {brief['reading']} · {page.model} · map layer {tm.layer}")
    if a.mode == "search":
        recipe, strength, trail = search(page, tm, brief, a.strength, a.n)
    else:
        recipe, strength, trail = agent(page, tm, brief, a.budget, a.n)
    print(f"found: {recipe_str(recipe) or '(nothing)'} @ {strength}")
    final = score(page, brief, recipe, strength, a.final)
    out = pathlib.Path(a.out) if a.out else HERE / "docs" / "runs" / f"orient-{name}-{a.mode}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "params": {k: v for k, v in vars(a).items() if k not in ("url",)}, "brief": {k: v for k, v in brief.items() if k != "read"},
        "model": page.model, "map_layer": tm.layer, "band": [page.lo, page.hi],
        "recipe": recipe_str(recipe), "strength": strength, "trail": trail, "final": final,
        "example": page.sh.example_spec, "complete": True, "runs": page.runs}, ensure_ascii=False, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
