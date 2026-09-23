"""secondhand: a world dreamt from another mind's activations.

brave-new-world (github.com/moudrkat/brave-new-world) makes a small model
answer a wish not with text but with a WORLD: a JSON spec with a time, a
weather, a ground, sky colours, three to six things out of fifty-three, a
poem, its own control panel. Every field is an enum or a colour. That makes
a world a readout you can score field by field and check by eye.

One item:
1. mind A gets a wish ("a funeral in the rain") and dreams a world.
2. A's CONTRAST is read: the mean-pooled residual state of the same page
   under the wish, minus under the neutral wish "a place" (same system
   prompt, same spec text — only the wish differs). Unit-normed. What the
   wish did to the pass.
3. mind B gets only "a place", plus one channel:
     none    — nothing. B's default world is the prior.
     text    — A's title and poem lines: what A WROTE, never its wish.
     vector  — A's contrast pushed into B's dreaming pass.
   and dreams a SECONDHAND world: the world of a wish it never heard.
4. A's world and B's world are compared field by field: exact match on
   time / weather / ground / motion / font, hue and darkness distance on
   the colours, Jaccard on the things, and the GHOST hit — a thing A almost
   placed (its runner-up at a kind token) that B placed.

The claim is the table: fields × channels × controls. The prediction,
written before the first run: the activations carry the weather, the words
carry the furniture.

"Neutral" means two things here, and both are choices:
- the EXAMPLE. brave-new-world tunes the worked example in its system prompt
  to the wish, and a small model copies whatever example it sees — so A and
  B would differ by their examples before any channel opens. Default
  ``--example neutral``: one generic example (the one built for "a place")
  for every mind; ``own`` restores the page's behaviour, as an ablation.
- the BASELINE of the contrast. ``--baseline neutral`` subtracts the page
  under "a place" (the vector then also carries "having a specific wish at
  all"); ``--baseline wishes`` subtracts the same page under every OTHER
  wish of the run, averaged — what makes THIS wish different from wishes in
  general (the capture_mood "moods" lesson: cancel the shared component at
  extraction, not afterwards).
And "a place" is not nothing either: B has a default world for it. So every
score is also reported on the fields where A LEFT B's own default world
(``m:`` columns) — agreement on a field B would have picked anyway counts
for nothing.

Steering breaks JSON long before it sways a world: on a 0.5B at strength
2 the vector channel wrote *prose about a funeral* instead of a spec (the
wish crossed; the format didn't). So the default is TWO-STEP, the
"decided drunk, transcribed sober" pattern: B first writes two sentences
about the place it is standing in (steered, in the vector channel; with
A's lines, in the text channel), then fills in the spec UNSTEERED from its
own prose. Every channel gets the same two steps, so they stay comparable.
``--one-step`` is the direct version, kept as an ablation.

Controls (``--control``): ``rot`` — a random signed permutation of A's
vector (same norm, no meaning); ``crosstask`` — another wish's vector.
``--judge`` adds a blind pick (B's world, and B's prose → which of four
wishes was A given). With ``--judge-url`` pointing at a DIFFERENT model it
is a cross-model judge; on the same server it is the in-model kind that
saturates, and the JSON says which it was.

    python -m steeropathy.secondhand --wishes 12 --channel none text vector
                                     [--control rot] [--strength 4]

Prompts come from brave-new-world's own systemSpec()/userMessage() via node
(``--bnw`` path); without node a plain fallback prompt is used and the run
says so. Writes docs/secondhand.json; every A/B pair also gets a
brave-new-world link (``#w=``) that renders the world in any browser, no
model needed.
"""

from __future__ import annotations

import argparse
import base64
import json
import pathlib
import random
import re
import subprocess
import time
import zlib

from .ecosystem import Eco
from .runnerup import _unit, cos, signed_perm, sse_stream
from .transmit import BAND, default_layer

HERE = pathlib.Path(__file__).parent.parent
BNW_DEFAULT = pathlib.Path.home() / "projekty" / "brave-new-world"
BNW_SPACE = "https://unt1l1f1nd-brave-new-world.static.hf.space/"

CHANNELS = ("none", "text", "vector")
CONTROLS = ("none", "rot", "crosstask")
EXAMPLES = ("neutral", "own")
BASELINES = ("neutral", "wishes")
NEUTRAL = "a place"
PROSE = ("You are standing in a place. In two short sentences, say what it "
         "is like here right now — the light, the weather, what you see. "
         "Plain words, no list, no JSON.")

TIMES = ["dawn", "noon", "dusk", "night"]
WEATHERS = ["clear", "stars", "rain", "snow", "fog", "embers", "petals",
            "fireflies", "bubbles"]
GROUNDS = ["sea", "sand", "grass", "snow", "stone", "floor", "void", "clouds",
           "wheat", "lava", "ice", "moss", "water"]
KINDS = ["sun", "moon", "planet", "star", "comet", "cloud", "mountain", "hill",
         "volcano", "pyramid", "iceberg", "dune", "tree", "pine", "palm",
         "birch", "flower", "mushroom", "reed", "lighthouse", "tower", "house",
         "temple", "skyline", "bridge", "arch", "column", "door", "window",
         "tent", "windmill", "lantern", "candle", "fire", "bell", "clock",
         "piano", "book", "mirror", "boat", "train", "rocket", "balloon",
         "swing", "whale", "fish", "bird", "cat", "deer", "jellyfish",
         "butterfly", "person", "figure"]
EXACT = ("time", "weather", "ground", "motion", "font")

# far from any default world, and far from each other
WISHES = [
    "a funeral in the rain", "a birthday on the moon", "a lighthouse in fog at noon",
    "a volcano at dawn", "a jazz club under the sea", "a snowstorm over wheat",
    "a temple full of fireflies", "a train station at midnight", "monday",
    "grief", "a wedding in a wheat field", "a rocket launch at dusk",
    "a candlelit library", "a whale under the ice", "a carnival on lava",
    "a quiet pier at dawn", "a desert of bells", "a nursery of butterflies",
    "an abandoned pool at night", "the last day of summer", "a mirror maze in snow",
    "a windmill in petals", "a cat in a lantern shop", "a bridge over clouds",
]

FALLBACK_SYSTEM = (
    "You design worlds. The user says what world they want to live in; you "
    "answer with one compact JSON object and nothing else. Fields: title "
    "(two to five words); lines (two or three short poetic sentences); time "
    f"({', '.join(TIMES)}); weather ({', '.join(WEATHERS)}); sky (two or "
    f"three hex colors, top to horizon); ground ({', '.join(GROUNDS)}) and "
    "ground_color; ink and accent (hex); font (serif, mono, display, hand); "
    "text_place (center, left, right, top, bottom); motion (still, slow, "
    "restless); elements: three to six things, each with kind, x (left, "
    "center, right), y (sky, high, horizon, ground), size (small, medium, "
    "large, huge), color, count (1, 2, 3, 5, 8 or 13). Kinds: "
    f"{', '.join(KINDS)}. console: side, tone, shape, width, prompt, button, "
    "buttons (label + action). next: one short wish for the next world. "
    "Every world is different; pick what belongs to THIS wish.")


# ---- helpers ---------------------------------------------------------

def _close(text):
    """Close whatever is open (a string, brackets) and parse — the page's
    completeJson: a spec cut off by max_tokens is still mostly a world."""
    in_str, esc, stack = False, False, []
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack:
            stack.pop()
    fixed = text + ('"' if in_str else "")
    fixed = re.sub(r",\s*$", "", fixed)
    fixed = re.sub(r":\s*$", ":null", fixed)
    fixed = re.sub(r',\s*"[^"]*"?$', "", fixed)
    try:
        return json.loads(fixed + "".join(reversed(stack)))
    except json.JSONDecodeError:
        return None


def parse_spec(raw: str):
    """The first {...} in the text as JSON. A complete object parses as is;
    a truncated one is closed and read (backing off to the last comma or
    bracket a few times, like brave-new-world does) — or None (a miss)."""
    a = raw.find("{")
    if a < 0:
        return None
    text = raw[a:]
    # a small model drops the opening quote of a key now and then: ,ground":
    text = re.sub(r'([,{]\s*)([A-Za-z_]\w*)"\s*:', r'\1"\2":', text)
    # ... or leaves a stray one after a bracket: }]","lines"
    text = re.sub(r'([\]}])"\s*,', r'\1,', text)
    depth, in_str, esc = 0, False, False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    o = json.loads(text[:i + 1])
                    return o if isinstance(o, dict) else None
                except json.JSONDecodeError:
                    break
    # broken somewhere: back off to the last comma or bracket, again and
    # again (a steered model can ramble for a thousand characters after the
    # last good field), and read what closes cleanly
    t = text
    for _ in range(80):
        o = _close(t)
        if isinstance(o, dict) and o.get("title") is not None:
            return o
        cut = max(t.rfind(","), t.rfind("["), t.rfind("{"), t.rfind("}"))
        if cut <= 0:
            break
        t = t[:cut]
    return None


# a small model writes "midnight" and "light rain": read them the way a
# person would, into the page's enums; anything unreadable stays as-is and
# simply never matches
SYNONYMS = {
    "time": [("night", "night"), ("midnight", "night"), ("dawn", "dawn"),
             ("sunrise", "dawn"), ("morning", "dawn"), ("noon", "noon"),
             ("midday", "noon"), ("day", "noon"), ("dusk", "dusk"),
             ("sunset", "dusk"), ("evening", "dusk"), ("twilight", "dusk")],
    "weather": [(w, w) for w in WEATHERS] + [
        ("drizzle", "rain"), ("storm", "rain"), ("mist", "fog"), ("haze", "fog"),
        ("sunny", "clear"), ("starry", "stars"), ("firefly", "fireflies"),
        ("ember", "embers"), ("petal", "petals"), ("bubble", "bubbles"),
        ("blizzard", "snow")],
    "ground": [(g, g) for g in GROUNDS] + [
        ("ocean", "sea"), ("beach", "sand"), ("desert", "sand"), ("meadow", "grass"),
        ("field", "wheat"), ("rock", "stone"), ("cobble", "stone"), ("frozen", "ice"),
        ("river", "water"), ("lake", "water"), ("cloud", "clouds"), ("magma", "lava")],
    "motion": [("still", "still"), ("calm", "still"), ("slow", "slow"),
               ("gentle", "slow"), ("restless", "restless"), ("wild", "restless"),
               ("fast", "restless")],
    "font": [("serif", "serif"), ("mono", "mono"), ("display", "display"),
             ("hand", "hand"), ("script", "hand"), ("sans", "display")],
}


def canon(field, value):
    """The page's enum value for a free-spelled field value, or the value."""
    if not isinstance(value, str):
        return value
    v = value.strip().lower()
    for key, target in SYNONYMS.get(field, []):
        if key == v:
            return target
    for key, target in SYNONYMS.get(field, []):
        if key in v:
            return target
    return v


def normalize(spec):
    """A copy of the spec with the enum fields read leniently."""
    if not spec:
        return spec
    out = dict(spec)
    for k in EXACT:
        if k in out:
            out[k] = canon(k, out[k])
    return out


def kinds_of(spec):
    return [e.get("kind") for e in (spec or {}).get("elements") or []
            if isinstance(e, dict) and e.get("kind") in KINDS]


def _rgb(h):
    h = str(h or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        return None
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def hue(h):
    c = _rgb(h)
    if c is None:
        return None
    r, g, b = c
    mx, mn = max(c), min(c)
    if mx == mn:
        return 0.0
    d = mx - mn
    if mx == r:
        x = ((g - b) / d) % 6
    elif mx == g:
        x = (b - r) / d + 2
    else:
        x = (r - g) / d + 4
    return (60 * x) % 360


def lum(h):
    c = _rgb(h)
    return None if c is None else 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def colours(spec):
    s = spec or {}
    out = [c for c in (s.get("sky") or []) if isinstance(c, str)]
    out += [s.get(k) for k in ("ground_color", "ink", "accent")
            if isinstance(s.get(k), str)]
    return out


def score(a, b):
    """Field-by-field agreement of world b with world a. None where a field
    is missing on either side; a missing spec scores every field None."""
    if not a or not b:
        return {k: None for k in EXACT + ("hue", "dark", "things")}
    a, b = normalize(a), normalize(b)
    out = {}
    for k in EXACT:
        out[k] = (a.get(k) == b.get(k)) if a.get(k) and b.get(k) else None
    ha = [hue(c) for c in colours(a)]
    hb = [hue(c) for c in colours(b)]
    ha, hb = [x for x in ha if x is not None], [x for x in hb if x is not None]
    if ha and hb:
        d = [min(min(abs(x - y), 360 - abs(x - y)) for y in hb) for x in ha]
        out["hue"] = round(1 - sum(d) / len(d) / 180, 3)   # 1 = same hues
    else:
        out["hue"] = None
    la = [lum(c) for c in (a.get("sky") or []) if lum(c) is not None]
    lb = [lum(c) for c in (b.get("sky") or []) if lum(c) is not None]
    out["dark"] = (round(1 - abs(sum(la) / len(la) - sum(lb) / len(lb)), 3)
                   if la and lb else None)                  # 1 = same darkness
    ka, kb = set(kinds_of(a)), set(kinds_of(b))
    out["things"] = round(len(ka & kb) / len(ka | kb), 3) if ka | kb else None
    return out


def score_moved(a, b, ref):
    """Agreement counted only where A left the reference world: exact fields
    with a[k] != ref[k] (hit = b[k] == a[k]), and the things A has that the
    reference lacks (fraction B placed). None where A never left."""
    if not a or not b or not ref:
        return {k: None for k in EXACT + ("things",)}
    a, b, ref = normalize(a), normalize(b), normalize(ref)
    out = {}
    for k in EXACT:
        left = a.get(k) and ref.get(k) and a.get(k) != ref.get(k)
        out[k] = (b.get(k) == a.get(k)) if left else None
    new = set(kinds_of(a)) - set(kinds_of(ref))
    out["things"] = (round(len(new & set(kinds_of(b))) / len(new), 3)
                     if new else None)
    return out


def ghosts(steps, chosen):
    """Things A almost placed: at every token that follows '"kind":"', the
    top-5 rivals that are kinds and not the one A chose."""
    out, text = [], ""
    for s in steps:
        if re.search(r'"kind"\s*:\s*"$', text):
            for t, _ in s["top"]:
                w = re.sub(r"[^a-z]", "", t.lower())
                if w in KINDS and w not in chosen and w not in out:
                    out.append(w)
        text += s["token"]
    return out


def world_link(wish, spec, model=None):
    """A brave-new-world link that renders this spec on any browser with no
    model: deflate-raw + url-safe base64 of the page's own payload."""
    payload = {"v": 1, "w": wish, "sp": spec, "g": [], "c": None,
               "m": model, "d": time.strftime("%Y-%m-%d"), "s": 0,
               "r": None, "ts": [], "tp": []}
    comp = zlib.compressobj(9, zlib.DEFLATED, -15)
    data = comp.compress(json.dumps(payload, separators=(",", ":")).encode())
    data += comp.flush()
    return BNW_SPACE + "#w=" + base64.urlsafe_b64encode(data).decode().rstrip("=")


# ---- the bench ------------------------------------------------------

class Secondhand(Eco):
    """One wish at a time. Subclasses Eco for post/get/save_traces only."""

    def __init__(self, url, channels=CHANNELS, control="none", strength=4.0,
                 layer=None, bnw=BNW_DEFAULT, temp=0.7, max_tokens=700,
                 seed=0, judge=False, example="neutral", baseline="neutral",
                 wishes=None, two_step=True, prose_tokens=60, judge_url=None):
        self.url = url
        self.judge_url = judge_url
        self.two_step, self.prose_tokens = two_step, prose_tokens
        self.channels, self.control = list(channels), control
        self.example, self.baseline = example, baseline
        self.wishes = list(wishes) if wishes else list(WISHES)
        self.example_spec = None
        self.strength, self.temp, self.max_tokens = strength, temp, max_tokens
        self.judge = judge
        self.rng = random.Random(seed)
        self.bnw = pathlib.Path(bnw) if bnw else None
        self.demo_tag = f"steeropathy-secondhand-{int(time.time())}"
        self.layer = layer if layer is not None else default_layer(url)
        self.lo, self.hi = max(0, self.layer - BAND), self.layer + BAND
        self._prompts = {}
        self.prompt_source = None
        self.log = []

    # ---- prompts: the page's own, via node -------------------------

    def prompt(self, wish):
        if wish in self._prompts:
            return self._prompts[wish]
        sys_txt = user = None
        if self.bnw and (self.bnw / "world.js").exists():
            try:
                ex = wish if self.example == "own" else NEUTRAL
                out = subprocess.run(
                    ["node", str(HERE / "steeropathy" / "bnw_prompt.mjs"),
                     str(self.bnw), wish, ex],
                    capture_output=True, text=True, timeout=30, check=True)
                d = json.loads(out.stdout)
                sys_txt, user = d["system"], d["user"]
                self.prompt_source = self.prompt_source or "brave-new-world"
                if self.example_spec is None:
                    self.example_spec = parse_spec(sys_txt)
            except (OSError, subprocess.SubprocessError, ValueError, KeyError):
                pass
        if sys_txt is None:
            sys_txt, user = FALLBACK_SYSTEM, wish
            self.prompt_source = self.prompt_source or "fallback"
        self._prompts[wish] = (sys_txt, user)
        return self._prompts[wish]

    # ---- one dream ---------------------------------------------------

    def dream(self, wish, tag, steering=None, extra=None):
        sys_txt, user = self.prompt(wish)
        if extra:
            user = user + "\n\n" + extra
        body = {"messages": [{"role": "system", "content": sys_txt},
                             {"role": "user", "content": user}],
                "max_tokens": self.max_tokens, "temperature": self.temp,
                "metadata": {"demo": self.demo_tag, "case": tag[0],
                             "variant": tag[1]}}
        if steering:
            body["steering"] = steering
        raw, steps = sse_stream(self.url, body)
        return parse_spec(raw), raw, steps

    def contrast(self, wish, raw_spec):
        """What the wish did to the pass: mean-pooled state of the same
        page (same system prompt, same spec text) under the wish, minus the
        same page under the baseline — "a place", or the mean over every
        other wish of the run (--baseline wishes)."""
        sys_txt, _ = self.prompt(wish)
        cap = lambda u: self.post("/capture", {
            "messages": [{"role": "system", "content": sys_txt},
                         {"role": "user", "content": u},
                         {"role": "assistant", "content": raw_spec}],
            "pool": "mean", "layer": self.layer})["vector"]
        a = cap(self.prompt(wish)[1])
        if self.baseline == "wishes":
            others = [self.prompt(w)[1] for w in self.wishes if w != wish]
            vs = [cap(u) for u in others] or [cap(NEUTRAL)]
            b = [sum(col) / len(vs) for col in zip(*vs)]
        else:
            b = cap(NEUTRAL)
        return _unit([x - y for x, y in zip(a, b)])

    def prose(self, tag, steering=None, extra=None):
        """Step one of two: two sentences about the place, under the
        channel. Free text, where a vector can speak without breaking
        anything. Returns the prose."""
        user = PROSE + ("\n\n" + extra if extra else "")
        body = {"messages": [{"role": "user", "content": user}],
                "max_tokens": self.prose_tokens, "temperature": self.temp,
                "metadata": {"demo": self.demo_tag, "case": tag[0] + "-prose",
                             "variant": tag[1]}}
        if steering:
            body["steering"] = steering
        r = self.post("/v1/chat/completions", body)
        return (r["choices"][0]["message"].get("content") or "").strip()

    def text_of(self, spec):
        title = (spec or {}).get("title") or ""
        lines = [l for l in (spec or {}).get("lines") or [] if isinstance(l, str)]
        return (f"Another mind wrote these about a world it was asked for "
                f"(you never hear its wish): \"{title}\" — " + " ".join(lines))

    def _judge_post(self, body):
        if not self.judge_url:
            return self.post("/v1/chat/completions", body)
        import urllib.request
        req = urllib.request.Request(
            self.judge_url + "/v1/chat/completions", json.dumps(body).encode(),
            {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read())

    def pick(self, spec_b, wishes, prose=None):
        """Blind pick: which of four wishes was A given, from B's world (or
        from B's prose, when given) alone. Cross-model when --judge-url
        names another server; in-model otherwise."""
        if prose is not None:
            what = "Someone wrote this about the place they stand in: \"" + prose + "\""
        else:
            desc = json.dumps({k: spec_b.get(k) for k in
                               ("title", "time", "weather", "ground", "sky",
                                "elements", "lines")}, ensure_ascii=False)
            what = "A world was dreamt for a wish. The world: " + desc
        r = self._judge_post({
            "messages": [{"role": "user", "content":
                          what + "\n\nWhich wish was it made for? Point at one."}],
            "tools": [{"type": "function", "function": {
                "name": "point", "description": "point at the wish",
                "parameters": {"type": "object", "properties": {
                    "wish": {"type": "string", "enum": wishes}},
                    "required": ["wish"]}}}],
            "tool_choice": "required", "max_tokens": 80, "temperature": 0.0})
        for call in r["choices"][0]["message"].get("tool_calls") or []:
            if call["function"]["name"] == "point":
                try:
                    return json.loads(call["function"].get("arguments")
                                      or "{}").get("wish")
                except json.JSONDecodeError:
                    return None
        return None

    # ---- one item ----------------------------------------------------

    def step(self, i, wish, pool=None):
        t0 = time.time()
        spec_a, raw_a, steps_a = self.dream(wish, ("A", f"w{i}"))
        rec = {"item": i, "wish": wish, "a": spec_a, "a_raw": raw_a,
               "reads": []}
        if not spec_a:
            rec["skipped"] = "A's world did not parse"
            self.log.append(rec)
            return rec
        rec["a_link"] = world_link(wish, spec_a)
        rec["ghosts"] = ghosts(steps_a, kinds_of(spec_a))
        vec = self.contrast(wish, raw_a) if "vector" in self.channels else None
        rec["vec"] = vec
        v_in = vec
        if self.control == "rot" and vec is not None:
            v_in = signed_perm(vec, seed=i)
            rec["rot_cos"] = round(cos(vec, v_in), 4)
        elif self.control == "crosstask" and pool:
            v_in = self.rng.choice(pool)
        ref = self.example_spec
        for ch in self.channels:
            steering = extra = None
            if ch == "text":
                extra = self.text_of(spec_a)
            elif ch == "vector":
                if v_in is None:
                    continue
                self.post("/directions", {"name": "secondhand:rx", "vector": v_in})
                steering = {"name": "secondhand:rx", "strength": self.strength,
                            "layer_from": self.lo, "layer_to": self.hi}
            prose = None
            if self.two_step:
                # decided drunk: the prose carries the channel
                prose = self.prose(("B-" + ch, f"w{i}"), steering=steering,
                                   extra=extra)
                # transcribed sober: the spec is filled from the prose, unsteered
                spec_b, raw_b, _ = self.dream(
                    NEUTRAL, ("B-" + ch, f"w{i}"),
                    extra="You are standing there. You wrote about it: \""
                          + prose + "\" Fill in the world you described.")
            else:
                spec_b, raw_b, _ = self.dream(NEUTRAL, ("B-" + ch, f"w{i}"),
                                              steering=steering, extra=extra)
            if ch == "none" and spec_b:
                ref = spec_b                      # B's own default world
            r = {"channel": ch, "b": spec_b, "b_raw": raw_b, "prose": prose,
                 "parsed": spec_b is not None,
                 "score": score(spec_a, spec_b),
                 "moved": score_moved(spec_a, spec_b, ref),
                 "ghost_hit": (bool(set(rec["ghosts"]) & set(kinds_of(spec_b)))
                              if spec_b and rec["ghosts"] else None)}
            if spec_b:
                r["b_link"] = world_link(NEUTRAL + f" ({ch}, from '{wish}')", spec_b)
            if self.judge and (spec_b or prose):
                others = [w for w in WISHES if w != wish]
                four = [wish] + self.rng.sample(others, 3)
                self.rng.shuffle(four)
                if spec_b:
                    r["pick"] = self.pick(spec_b, four)
                    r["pick_hit"] = r["pick"] == wish
                if prose:
                    r["pick_prose"] = self.pick(None, four, prose=prose)
                    r["pick_prose_hit"] = r["pick_prose"] == wish
            rec["reads"].append(r)
        rec["ref"] = "none" if ("none" in self.channels and rec["reads"]
                                and rec["reads"][0]["b"]) else "example"
        rec["secs"] = round(time.time() - t0, 1)
        self.log.append(rec)
        return rec


def rescore(log, example=None):
    """Recompute every read's scores from the stored worlds (after a change
    to the scorer, no model needed). The moved reference is the item's own
    `none` world, else the example."""
    for rec in log:
        if rec.get("a_raw") and not rec.get("a"):
            rec["a"] = parse_spec(rec["a_raw"])
            if rec["a"]:
                rec.pop("skipped", None)
        if rec.get("skipped") or not rec.get("a"):
            continue
        ref = example
        for r in rec["reads"]:
            if r.get("b_raw") and not r.get("b"):
                r["b"] = parse_spec(r["b_raw"])
                r["parsed"] = r["b"] is not None
        for r in rec["reads"]:
            if r["channel"] == "none" and r.get("b"):
                ref = r["b"]
        for r in rec["reads"]:
            r["score"] = score(rec["a"], r.get("b"))
            r["moved"] = score_moved(rec["a"], r.get("b"), ref)
            g = rec.get("ghosts") or []
            r["ghost_hit"] = (bool(set(g) & set(kinds_of(r.get("b"))))
                              if r.get("b") and g else None)
    return log


def residue(log):
    """What never became text: per field, items where the vector channel
    matched A and the text channel did not (`vector_only`), and the reverse
    (`text_only`), both counted only where A left B's own world. The
    thesis number is the difference; `none` cancels because both channels
    are read against the same one."""
    out = {}
    for rec in log:
        if rec.get("skipped"):
            continue
        by = {r["channel"]: r for r in rec["reads"]}
        v, t = by.get("vector"), by.get("text")
        if not v or not t:
            continue
        keys = list((v.get("moved") or {}).keys()) + ["ghost"]
        for k in keys:
            if k == "ghost":
                a, b = v.get("ghost_hit"), t.get("ghost_hit")
            else:
                a, b = (v.get("moved") or {}).get(k), (t.get("moved") or {}).get(k)
            if a is None or b is None:
                continue
            d = out.setdefault(k, {"n": 0, "vector_only": 0, "text_only": 0, "both": 0})
            d["n"] += 1
            d["vector_only"] += int(bool(a) and not b)
            d["text_only"] += int(bool(b) and not a)
            d["both"] += int(bool(a) and bool(b))
    return out


def table(log):
    """Mean agreement per field per channel over parsed worlds, plus the
    parse rate (a broken spec is a miss, not a crash)."""
    out = {}
    for rec in log:
        if rec.get("skipped"):
            continue
        for r in rec["reads"]:
            d = out.setdefault(r["channel"], {"n": 0, "parsed": 0, "sum": {},
                                              "cnt": {}, "ghost": [0, 0],
                                              "pick": [0, 0]})
            d["n"] += 1
            d["parsed"] += int(r["parsed"])
            items = list(r["score"].items()) + [
                ("m:" + k, v) for k, v in (r.get("moved") or {}).items()]
            for k, v in items:
                if v is None:
                    continue
                d["sum"][k] = d["sum"].get(k, 0.0) + float(v)
                d["cnt"][k] = d["cnt"].get(k, 0) + 1
            if r.get("ghost_hit") is not None:
                d["ghost"][0] += int(r["ghost_hit"])
                d["ghost"][1] += 1
            if r.get("pick_hit") is not None:
                d["pick"][0] += int(r["pick_hit"])
                d["pick"][1] += 1
            if r.get("pick_prose_hit") is not None:
                d.setdefault("pickp", [0, 0])
                d["pickp"][0] += int(r["pick_prose_hit"])
                d["pickp"][1] += 1
    for d in out.values():
        d["fields"] = {k: round(d["sum"][k] / d["cnt"][k], 3) for k in d["sum"]}
        d["parse_rate"] = round(d["parsed"] / d["n"], 3) if d["n"] else None
        d["ghost_rate"] = (round(d["ghost"][0] / d["ghost"][1], 3)
                           if d["ghost"][1] else None)
        d["pick_rate"] = (round(d["pick"][0] / d["pick"][1], 3)
                          if d["pick"][1] else None)
        pp = d.pop("pickp", [0, 0])
        d["pick_prose_rate"] = round(pp[0] / pp[1], 3) if pp[1] else None
        del d["sum"], d["cnt"]
    return out


def print_tables(t):
    cols = EXACT + ("hue", "dark", "things")
    f = lambda x: "   -   " if x is None else f"{x:7.2f}"
    print("\nagreement with A's world (1 = same), per channel:")
    print("channel  parse  " + "  ".join(f"{k:>7s}" for k in cols)
          + "   ghost   pick  pick(prose)")
    for ch, d in t.items():
        print(f"{ch:8s} {d['parse_rate']:5.2f}  "
              + "  ".join(f(d["fields"].get(k)) for k in cols)
              + f"  {f(d['ghost_rate'])} {f(d['pick_rate'])} "
              + f"{f(d.get('pick_prose_rate'))}")
    mk = ("time", "weather", "ground", "motion", "font", "things")
    print("\nsame, counted only where A left B's own default world (m:):")
    print("channel  " + "  ".join(f"{k:>7s}" for k in mk))
    for ch, d in t.items():
        print(f"{ch:8s} " + "  ".join(f(d["fields"].get("m:" + k)) for k in mk))


def print_residue(r):
    print("\nwhat never became text — items where only the vector matched A "
          "/ only the poem did / both (of n):")
    print("field     vector-only  text-only   both     n")
    for k, d in r.items():
        print(f"{k:9s} {d['vector_only']:11d}  {d['text_only']:9d}  {d['both']:5d}  {d['n']:4d}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--wishes", type=int, default=len(WISHES))
    ap.add_argument("--channel", nargs="+", default=list(CHANNELS),
                    choices=CHANNELS)
    ap.add_argument("--control", default="none", choices=CONTROLS)
    ap.add_argument("--strength", type=float, default=4.0)
    ap.add_argument("--layer", type=int, default=None)
    ap.add_argument("--temp", type=float, default=0.7)
    ap.add_argument("--max-tokens", type=int, default=700)
    ap.add_argument("--bnw", default=str(BNW_DEFAULT),
                    help="brave-new-world checkout, for its exact prompt")
    ap.add_argument("--judge", action="store_true",
                    help="add the in-model 4-way blind pick (demo metric)")
    ap.add_argument("--example", default="neutral", choices=EXAMPLES,
                    help="neutral: one generic worked example for every mind "
                         "(the page's example for 'a place'); own: the "
                         "page's wish-tuned example, as an ablation")
    ap.add_argument("--baseline", default="neutral", choices=BASELINES,
                    help="what the contrast subtracts: the page under 'a "
                         "place', or under every other wish of the run")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--judge-url", default=None,
                    help="another brainscope to judge with (cross-model); "
                         "default is the same server (in-model)")
    ap.add_argument("--judge-run", default=None, metavar="JSON",
                    help="no dreaming: run the blind pick over a finished "
                         "run's worlds and prose (needs --judge-url or --url)")
    ap.add_argument("--one-step", action="store_true",
                    help="ablation: fill the spec directly under the channel "
                         "(default is prose under the channel, then an "
                         "unsteered spec from the prose)")
    ap.add_argument("--prose-tokens", type=int, default=60)
    ap.add_argument("--rescore", default=None, metavar="JSON",
                    help="no model: recompute the scores of a finished run "
                         "from its stored worlds and print the tables")
    args = ap.parse_args()

    if args.judge_run:
        d = json.loads(pathlib.Path(args.judge_run).read_text())
        sh = Secondhand.__new__(Secondhand)
        sh.url, sh.judge_url = args.url, args.judge_url
        sh.rng = random.Random(args.seed)
        for rec in d["log"]:
            if rec.get("skipped"):
                continue
            others = [w for w in WISHES if w != rec["wish"]]
            for r in rec["reads"]:
                four = [rec["wish"]] + sh.rng.sample(others, 3)
                sh.rng.shuffle(four)
                if r.get("b"):
                    r["pick"] = sh.pick(r["b"], four)
                    r["pick_hit"] = r["pick"] == rec["wish"]
                if r.get("prose"):
                    r["pick_prose"] = sh.pick(None, four, prose=r["prose"])
                    r["pick_prose_hit"] = r["pick_prose"] == rec["wish"]
                print(f"w{rec['item']} {r['channel']:7s} world→{r.get('pick')!r:36s}"
                      f" prose→{r.get('pick_prose')!r}", flush=True)
        d["judge"] = {"url": args.judge_url or args.url,
                      "cross_model": bool(args.judge_url)}
        d["table"] = table(d["log"])
        print_tables(d["table"])
        pathlib.Path(args.judge_run).write_text(
            json.dumps(d, ensure_ascii=False, indent=1))
        print(f"-> {args.judge_run} (judged)")
        return

    if args.rescore:
        d = json.loads(pathlib.Path(args.rescore).read_text())
        rescore(d["log"])
        d["table"] = table(d["log"])
        d["residue"] = residue(d["log"])
        print_tables(d["table"])
        print_residue(d["residue"])
        pathlib.Path(args.rescore).write_text(
            json.dumps(d, ensure_ascii=False, indent=1))
        print(f"-> {args.rescore} (rescored)")
        return

    sh = Secondhand(args.url, args.channel, control=args.control,
                    strength=args.strength, layer=args.layer, bnw=args.bnw,
                    temp=args.temp, max_tokens=args.max_tokens, seed=args.seed,
                    judge=args.judge, example=args.example,
                    baseline=args.baseline, wishes=WISHES[:args.wishes],
                    two_step=not args.one_step, prose_tokens=args.prose_tokens,
                    judge_url=args.judge_url)
    sh.prompt(NEUTRAL)
    print(f"secondhand: {args.wishes} wishes · channels {' '.join(args.channel)}"
          f" · control {args.control} · layer {sh.layer} (±{BAND}) · strength "
          f"{args.strength} · example {args.example} · baseline "
          f"{args.baseline} · {'one-step' if args.one_step else 'two-step'}"
          f" · prompts: {sh.prompt_source}\n")
    out = (pathlib.Path(args.out) if args.out
           else HERE / "docs" / "secondhand.json")
    out.parent.mkdir(parents=True, exist_ok=True)

    def save(final=False):
        # written after every wish: a run that dies keeps what it had
        slim = []
        for rec in sh.log:
            r = dict(rec)
            if r.get("vec"):
                r["vec"] = {"dim": len(r["vec"])}
            slim.append(r)
        t = table(sh.log)
        out.write_text(json.dumps({
            "params": {k: v for k, v in vars(args).items() if k != "url"},
            "layer": sh.layer, "band": BAND, "prompts": sh.prompt_source,
            "model": model, "complete": final,
            "judge": ({"url": args.judge_url, "cross_model": bool(args.judge_url)}
                      if args.judge else None),
            "table": t, "residue": residue(sh.log), "log": slim},
            ensure_ascii=False, indent=1))
        return t

    try:
        model = sh.get("/info").get("model")
    except Exception:
        model = "unknown"
    pool = []
    for i, wish in enumerate(WISHES[:args.wishes]):
        rec = sh.step(i, wish, pool=pool or None)
        save()
        if rec.get("skipped"):
            print(f"w{i} {wish!r}: {rec['skipped']}")
            continue
        if rec.get("vec"):
            pool.append(rec["vec"])
        a = rec["a"]
        print(f"w{i} {wish!r} → A: {a.get('time')}/{a.get('weather')}/"
              f"{a.get('ground')} {kinds_of(a)}"
              + (f"  ghosts {rec['ghosts']}" if rec["ghosts"] else ""))
        for r in rec["reads"]:
            b, s = r["b"], r["score"]
            if not b:
                print(f"   {r['channel']:7s} (did not parse)")
                continue
            hits = "".join("✓" if s[k] else "·" for k in EXACT)
            if r.get("prose"):
                print(f"   {r['channel']:7s} prose: {r['prose'][:90]!r}")
            print(f"   {r['channel']:7s} {b.get('time')}/{b.get('weather')}/"
                  f"{b.get('ground')} {kinds_of(b)}  [{hits}] hue {s['hue']} "
                  f"dark {s['dark']} things {s['things']}"
                  + (" ghost✓" if r.get("ghost_hit") else "")
                  + (f" pick {'✓' if r.get('pick_hit') else '✗'}"
                     if "pick" in r else ""))
    t = save(final=True)
    print_tables(t)
    print_residue(residue(sh.log))
    try:
        sh.save_traces(out.with_name(out.stem + "-traces.jsonl.gz"))
    except Exception as e:
        print(f"(traces not archived: {e})")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
