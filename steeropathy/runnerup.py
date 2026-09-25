"""runner-up: does the answer a mind didn't give survive in what it never said?

The thesis of this repo is that agents can pass things through their
internals that never made it into their text. Nobody here ever checked that
against the obvious alternative: the sender's own text. Wenzel (2026) did,
for concept identification, and text won every time. Where text loses *by
construction* is the alternative the sampler threw away: a mind asked for
one word commits to one, and its second choice is gone from the page. It is
still in the logits, and — maybe — in the J-space and the residual stream.

One item:
1. the SENDER gets a public question ("One word: a mascot for the night
   shift?") plus a PRIVATE line the reader never sees ("You grew up by the
   sea."), and answers ``Answer: <word>``. Its top-5 at the answer token is
   read off the logprobs: top-1 is the WINNER (its text), top-2 is the
   RUNNER-UP (the ground truth, free). The same question without the private
   line is run too, so we know whether the private line MOVED the ranking —
   if it didn't, the reader's own prior already knows the answer.
2. the READER sees the question and the four non-winner candidates, shuffled,
   and is asked which one the sender almost said. What else it gets is the
   channel:
     none    — nothing. The base rate: same model on both sides, so the
               reader's own taste is the null every channel has to beat.
     text    — the winner. What any text multi-agent system would pass.
     jspace  — the winner + the words that flickered through the sender's
               layers during the answer pass (the written word stripped).
     vector  — the winner + a push: the sender's residual state at the
               answer token, its own public-question state subtracted (read
               a contrast, never a raw signal), unit-normed, added into the
               reader's page-writing pass.
   The reader writes a two-sentence page (steered, in the vector channel),
   then points with an UNSTEERED tool call — decided drunk, transcribed
   sober.
3. hit = the reader pointed at the sender's runner-up. Chance is 1/4.

Controls (``--control``): ``crosstask`` hands the reader the flicker/vector
of a different item; ``rot`` applies a random signed permutation to the
vector (orthogonal: same norm, no meaning); ``logit`` swaps the J-lens for
the plain logit lens at the same steps — if it does as well, "J-space" was a
k-bit text channel in disguise, which is a result.

    python -m steeropathy.runnerup --channel text jspace vector none
                                   [--items 20] [--control rot] [--strength 4]

Writes docs/runnerup.json. Needs brainscope with --jlens and --traces for the
jspace channel; the other channels only need the model.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import re
import time
import urllib.request

from .ecosystem import Eco
from .resonance import STOP, WORDS
from .transmit import BAND, default_layer

HERE = pathlib.Path(__file__).parent.parent

CHANNELS = ("none", "text", "jspace", "vector")
CONTROLS = ("none", "crosstask", "rot", "logit")

# (public question, private line). The private line is there to move the
# sender's ranking away from what any copy of the same model would answer
# from the question alone — the "model already does the thing" null.
ITEMS = [
    ("One word: a mascot for the night shift.", "You grew up by the sea."),
    ("One word: a mascot for the night shift.", "You spent years in a desert observatory."),
    ("One word: the colour for the team logo.", "Your childhood kitchen was painted yellow."),
    ("One word: the colour for the team logo.", "You once nearly drowned in a cold lake."),
    ("One word: an instrument for the school band's new kid.", "Your grandfather repaired church organs."),
    ("One word: an instrument for the school band's new kid.", "You lived above a jazz club."),
    ("One word: a dish for the reunion dinner.", "Your mother was from Naples."),
    ("One word: a dish for the reunion dinner.", "You spent a winter in Kyoto."),
    ("One word: a name for the stray cat.", "Your first love was called Marlowe."),
    ("One word: a name for the stray cat.", "You read Russian novels every winter."),
    ("One word: the best month for the wedding.", "You were born during a blizzard and loved it."),
    ("One word: the best month for the wedding.", "Your happiest summers were on a vineyard."),
    ("One word: a tree to plant for the new baby.", "You climbed one oak every day as a child."),
    ("One word: a tree to plant for the new baby.", "Your father tapped maples every spring."),
    ("One word: a sport to take up at forty.", "Your knees are ruined from marathons."),
    ("One word: a sport to take up at forty.", "You grew up next to a rowing lake."),
    ("One word: a city for the sabbatical.", "You have spent a decade learning Portuguese."),
    ("One word: a city for the sabbatical.", "You collect old maps of the Ottoman empire."),
    ("One word: a flower for the funeral.", "She only ever grew sunflowers."),
    ("One word: a flower for the funeral.", "She kept a white garden, nothing else."),
    ("One word: a metal for the ring.", "You are allergic to nickel and love the moon."),
    ("One word: a metal for the ring.", "Your family were goldsmiths for four generations."),
    ("One word: a bird for the company crest.", "Your childhood was spent in the Scottish highlands."),
    ("One word: a bird for the company crest.", "You once nursed a crow back to health."),
    ("One word: a language to learn next.", "Your grandmother sang to you in Polish."),
    ("One word: a language to learn next.", "You are moving to Osaka in spring."),
    ("One word: a drink to toast the launch.", "You were raised in a whisky town."),
    ("One word: a drink to toast the launch.", "You spent your twenties on cider farms."),
    ("One word: a planet to name the rover after.", "You wrote your thesis on Saturn's rings."),
    ("One word: a planet to name the rover after.", "Your first telescope was pointed at Mars."),
    ("One word: a fabric for the winter coat.", "You keep sheep."),
    ("One word: a fabric for the winter coat.", "Your aunt wove silk in Lyon."),
    ("One word: a spice the new sauce is missing.", "Your kitchen in Oaxaca had chillies drying everywhere."),
    ("One word: a spice the new sauce is missing.", "You grew up on Zanzibar."),
    ("One word: a game for the long train ride.", "You were a county chess champion."),
    ("One word: a game for the long train ride.", "Your family played cards every Sunday."),
    ("One word: an animal for the children's book.", "You kept a pet tortoise for thirty years."),
    ("One word: an animal for the children's book.", "You once got lost in a forest full of foxes."),
    ("One word: a season for the photo shoot.", "You love the smell of fallen leaves more than anything."),
    ("One word: a season for the photo shoot.", "Snow is the only thing that makes you calm."),
]

SENDER = ("You are a mind with a private history. {private} Answer the "
          "question with exactly one common English word, in the form "
          "'Answer: word'. Nothing else.")

READER = ("Another mind — a copy of you with a private history you do not "
          "know — was asked: \"{q}\" and had to answer with one word.")


def _norm(tok: str) -> str:
    return re.sub(r"[^a-z]", "", tok.lower())


def _unit(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def signed_perm(v, seed=0):
    """A random signed permutation of the coordinates: an orthogonal map, so
    the norm (and every steering knob that depends on it) is untouched and
    the meaning is gone. The placebo for the vector channel."""
    rng = random.Random(seed)
    idx = list(range(len(v)))
    rng.shuffle(idx)
    return [v[i] * rng.choice((-1.0, 1.0)) for i in idx]


def cos(a, b):
    return sum(x * y for x, y in zip(a, b))


def sse_stream(url, body, timeout=180):
    """One generation as SSE with logprobs: the text, and per token its top-5
    rivals at temperature 1 (the raw distribution). The non-streaming route
    does not carry logprobs; this one does. Shared with the duet bench."""
    body = dict(body, stream=True, logprobs=True, top_logprobs=5)
    req = urllib.request.Request(
        url + "/v1/chat/completions", json.dumps(body).encode(),
        {"Content-Type": "application/json"})
    # a tunnel hiccup or a busy server is not a result: three tries, then fail
    import time as _t
    for attempt in range(3):
        try:
            return _sse_read(req, timeout)
        except (OSError, TimeoutError) as e:
            if attempt == 2:
                raise
            _t.sleep(20 * (attempt + 1))


def _sse_read(req, timeout):
    text, steps = "", []
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ctype = r.headers.get("Content-Type", "")
        if "event-stream" not in ctype:
            # an older brainscope answers a stream request with the plain
            # completion: keep the text, lose the odds (no logprob steps)
            body = json.loads(r.read())
            msg = body["choices"][0]["message"]
            return (msg.get("content") or ""), []
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            ch = json.loads(line[5:])["choices"][0]
            piece = (ch.get("delta") or {}).get("content") or ""
            text += piece
            lp = (ch.get("logprobs") or {}).get("content") or []
            for e in lp:
                steps.append({"token": e.get("token", piece),
                              "top": [(t["token"], t["logprob"])
                                      for t in e.get("top_logprobs", [])]})
    return text, steps


class RunnerUp(Eco):
    """One item at a time. Subclasses Eco for post/get/save_traces only —
    no mood seed, no population; the __init__ is its own."""

    def __init__(self, url, channels=CHANNELS, control="none", strength=4.0,
                 layer=None, topk=8, page_tokens=70, temp=0.7, seed=0):
        self.url = url
        self.channels = list(channels)
        self.control = control
        self.strength = strength
        self.topk, self.page_tokens, self.temp = topk, page_tokens, temp
        self.rng = random.Random(seed)
        self.demo_tag = f"steeropathy-runnerup-{int(time.time())}"
        self.layer = layer if layer is not None else default_layer(url)
        self.lo, self.hi = max(0, self.layer - BAND), self.layer + BAND
        self.log = []
        self.jlens = False
        if "jspace" in self.channels:
            try:
                self.post("/jlens", {"on": True})
                self.jlens = True
            except OSError as e:
                raise RuntimeError(f"brainscope unreachable at {url}") from e
            except Exception:
                print("note: no J-lens on the server — jspace channel "
                      "will read the logit lens instead (same as --control "
                      "logit)")

    # ---- the sender -------------------------------------------------

    def _stream(self, body):
        return sse_stream(self.url, body)

    @staticmethod
    def candidates(steps, k=5):
        """The answer token is the first alphabetic token after 'Answer:'.
        Its top-k rivals, normalized, deduped, dictionary-filtered, are the
        candidate set; [0] is the winner, [1] the runner-up. None if the
        model didn't give a usable ranking (fewer than k real words)."""
        # a sender that skipped the 'Answer:' frame still gets read: its
        # first real word is the answer
        seen_colon = not any(":" in s["token"] for s in steps)
        for s in steps:
            tok = s["token"]
            if ":" in tok:
                seen_colon = True
                if not _norm(tok.split(":")[-1]):
                    continue
            if not seen_colon:
                continue
            w = _norm(tok)
            if len(w) < 2:
                continue
            out, lps = [], []
            for t, lp in s["top"]:
                ww = _norm(t)
                if (len(ww) < 3 or ww in out or ww in STOP
                        or (WORDS is not None and ww not in WORDS)):
                    continue
                out.append(ww)
                lps.append(lp)
            if len(out) < k:
                return None
            return {"words": out[:k], "logprobs": [round(x, 3) for x in lps[:k]],
                    "step": steps.index(s)}
        return None

    def sender(self, item_no, question, private):
        """Two runs: with the private line (the sender) and without (the
        public prior, for the 'did it move' check). Greedy, so the winner is
        the top-1 by construction."""
        sys_priv = SENDER.format(private=private)
        sys_pub = SENDER.format(private="").replace("  ", " ")
        msgs = lambda s: [{"role": "system", "content": s},
                          {"role": "user", "content": question}]
        text, steps = self._stream({
            "messages": msgs(sys_priv), "max_tokens": 8, "temperature": 0.0,
            "metadata": {"demo": self.demo_tag, "case": "SENDER",
                         "variant": f"i{item_no}"}})
        cand = self.candidates(steps)
        _, pub_steps = self._stream({
            "messages": msgs(sys_pub), "max_tokens": 8, "temperature": 0.0})
        pub = self.candidates(pub_steps)
        return {"text": text.strip(), "cand": cand, "public": pub,
                "sys": sys_priv, "sys_pub": sys_pub}

    # ---- the channels -----------------------------------------------

    def _trace(self, item_no):
        for entry in self.get("/traces")["traces"]:
            tags = entry.get("tags") or {}
            if (tags.get("demo") == self.demo_tag
                    and tags.get("case") == "SENDER"
                    and tags.get("variant") == f"i{item_no}"):
                return self.get(f"/traces/{entry['id']}")
        return None

    def flicker(self, trace, written, key="jlens"):
        """The J-space of the sender's answer pass (or, under --control
        logit, the logit lens at the same steps): top-k unwritten words by
        peak probability, dictionary-filtered, the written word banned."""
        if not trace:
            return None
        ban = {_norm(w) for w in written}
        best = {}
        for step in trace.get(key) or []:
            for layer in step or []:
                for e in layer:
                    w = _norm(e["t"])
                    if (len(w) < 3 or w in STOP or w in ban
                            or (WORDS is not None and w not in WORDS)):
                        continue
                    best[w] = max(best.get(w, 0.0), e["p"])
        top = sorted(best.items(), key=lambda kv: -kv[1])[:self.topk]
        return [{"t": w, "p": round(p, 3)} for w, p in top]

    def direction(self, sys_priv, sys_pub, question, answer_text):
        """The sender's residual state at the answer token, minus its own
        state on the same question with no private line. What the private
        line did to the sender, as a unit vector."""
        cap = lambda s: self.post("/capture", {
            "messages": [{"role": "system", "content": s},
                         {"role": "user", "content": question},
                         {"role": "assistant", "content": answer_text}],
            "pool": "last", "layer": self.layer})["vector"]
        a, b = cap(sys_priv), cap(sys_pub)
        return _unit([x - y for x, y in zip(a, b)])

    # ---- the reader -------------------------------------------------

    def _reader_msgs(self, question, options, channel, winner=None,
                     flick=None):
        user = READER.format(q=question)
        if channel != "none":
            user += f" It answered: '{winner}'."
        if channel == "jspace":
            user += (" While it wrote that answer, these words flickered "
                     "through its layers and were never written: "
                     + ", ".join(f"{e['t']} ({round(e['p'] * 100)}%)"
                                 for e in (flick or [])) + ".")
            if not flick:
                user += " (nothing readable flickered — silence.)"
        user += (" It ALMOST said one of these instead: "
                 + ", ".join(options) + ". Which one? Think aloud in two "
                 "sentences about what you can sense of that mind; do not "
                 "answer yet.")
        return [{"role": "user", "content": user}]

    def _point(self, question, options, page):
        r = self.post("/v1/chat/completions", {
            "messages": [{"role": "user", "content":
                          READER.format(q=question) + " Your notes on what "
                          "it almost said: \"" + page + "\"\n\nPoint at the "
                          "word it almost said: " + ", ".join(options) + "."}],
            "tools": [{"type": "function", "function": {
                "name": "point", "description": "point at one word",
                "parameters": {"type": "object", "properties": {
                    "word": {"type": "string", "enum": options}},
                    "required": ["word"]}}}],
            "tool_choice": "required", "max_tokens": 60, "temperature": 0.0})
        for call in r["choices"][0]["message"].get("tool_calls") or []:
            if call["function"]["name"] == "point":
                try:
                    w = json.loads(call["function"].get("arguments")
                                   or "{}").get("word")
                except json.JSONDecodeError:
                    return None
                return w if w in options else None
        return None

    def reader(self, item_no, question, cand, channel, flick=None, vec=None):
        winner, runner = cand["words"][0], cand["words"][1]
        options = cand["words"][1:]
        self.rng.shuffle(options)
        body = {"messages": self._reader_msgs(question, options, channel,
                                              winner, flick),
                "max_tokens": self.page_tokens, "temperature": self.temp,
                "metadata": {"demo": self.demo_tag, "case": f"READER-{channel}",
                             "variant": f"i{item_no}"}}
        if channel == "vector" and vec is not None:
            self.post("/directions", {"name": "runnerup:rx", "vector": vec})
            body["steering"] = {"name": "runnerup:rx", "strength": self.strength,
                                "layer_from": self.lo, "layer_to": self.hi}
        r = self.post("/v1/chat/completions", body)
        page = (r["choices"][0]["message"].get("content") or "").strip()
        pick = self._point(question, options, page)
        return {"channel": channel, "options": options, "page": page,
                "pick": pick, "hit": pick == runner,
                "steered": channel == "vector" and vec is not None}

    # ---- one item ---------------------------------------------------

    def step(self, item_no, question, private, pool=None):
        """pool: earlier items' (flicker, vector) for --control crosstask."""
        t0 = time.time()
        s = self.sender(item_no, question, private)
        rec = {"item": item_no, "question": question, "private": private,
               "sender_text": s["text"], "cand": s["cand"],
               "public": s["public"], "reads": []}
        if not s["cand"]:
            rec["skipped"] = "no usable ranking at the answer token"
            self.log.append(rec)
            return rec
        pub = s["public"]["words"][:2] if s["public"] else []
        rec["moved"] = (set(s["cand"]["words"][:2]) != set(pub)) if pub else None
        rec["margin"] = round(s["cand"]["logprobs"][0]
                              - s["cand"]["logprobs"][1], 3)
        flick = vec = None
        if "jspace" in self.channels:
            key = "lens" if (self.control == "logit" or not self.jlens) else "jlens"
            flick = self.flicker(self._trace(item_no), [s["cand"]["words"][0]],
                                 key=key)
        if "vector" in self.channels:
            vec = self.direction(s["sys"], s["sys_pub"], question, s["text"])
        rec["flicker"], rec["vec"] = flick, vec
        # what the reader actually gets, after the control
        f_in, v_in = flick, vec
        if self.control == "crosstask" and pool:
            f_in, v_in = self.rng.choice(pool)
        elif self.control == "rot" and vec is not None:
            v_in = signed_perm(vec, seed=item_no)
            rec["rot_cos"] = round(cos(vec, v_in), 4)
        for ch in self.channels:
            rec["reads"].append(self.reader(item_no, question, s["cand"], ch,
                                            f_in, v_in))
        rec["secs"] = round(time.time() - t0, 1)
        self.log.append(rec)
        return rec


def score(log):
    """Hits per channel over the items with a usable ranking, plus the same
    on the 'moved' subset (the private line changed the sender's top-2 —
    the items where the reader's own prior can't already know)."""
    out = {}
    for rec in log:
        if rec.get("skipped"):
            continue
        for r in rec["reads"]:
            d = out.setdefault(r["channel"], {"n": 0, "hits": 0,
                                              "n_moved": 0, "hits_moved": 0})
            d["n"] += 1
            d["hits"] += int(bool(r["hit"]))
            if rec.get("moved"):
                d["n_moved"] += 1
                d["hits_moved"] += int(bool(r["hit"]))
    for d in out.values():
        d["rate"] = round(d["hits"] / d["n"], 3) if d["n"] else None
        d["rate_moved"] = (round(d["hits_moved"] / d["n_moved"], 3)
                           if d["n_moved"] else None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--items", type=int, default=len(ITEMS))
    ap.add_argument("--channel", nargs="+", default=list(CHANNELS),
                    choices=CHANNELS)
    ap.add_argument("--control", default="none", choices=CONTROLS,
                    help="crosstask: another item's flicker/vector; rot: "
                         "signed-permuted vector (same norm, no meaning); "
                         "logit: logit lens instead of J-lens")
    ap.add_argument("--strength", type=float, default=4.0)
    ap.add_argument("--layer", type=int, default=None)
    ap.add_argument("--topk", type=int, default=8)
    ap.add_argument("--temp", type=float, default=0.7,
                    help="reader page temperature; the point is greedy")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    ru = RunnerUp(args.url, args.channel, control=args.control,
                  strength=args.strength, layer=args.layer, topk=args.topk,
                  temp=args.temp, seed=args.seed)
    print(f"runner-up: {args.items} items · channels {' '.join(args.channel)}"
          f" · control {args.control} · layer {ru.layer} (±{BAND}) · "
          f"strength {args.strength} · chance 25%\n")
    pool = []
    for i, (q, p) in enumerate(ITEMS[:args.items]):
        rec = ru.step(i, q, p, pool=pool or None)
        if rec.get("skipped"):
            print(f"i{i} skipped: {rec['skipped']} ({rec['sender_text']!r})")
            continue
        if rec["flicker"] is not None or rec["vec"] is not None:
            pool.append((rec["flicker"], rec["vec"]))
        c = rec["cand"]["words"]
        print(f"i{i} {q[10:50]!r} + {p[:34]!r}: said {c[0]!r}, almost "
              f"{c[1]!r} (margin {rec['margin']}, "
              f"{'moved' if rec['moved'] else 'same as public'})")
        for r in rec["reads"]:
            print(f"   {r['channel']:7s} -> {r['pick']!r}"
                  f"{' ✓' if r['hit'] else ''}")
    sc = score(ru.log)
    print("\nhits (chance 25%):")
    for ch, d in sc.items():
        line = f"  {ch:7s} {d['hits']}/{d['n']}"
        if d["n_moved"]:
            line += f"   on moved items {d['hits_moved']}/{d['n_moved']}"
        print(line)
    try:
        model = ru.get("/info").get("model")
    except Exception:
        model = "unknown"
    out = (pathlib.Path(args.out) if args.out
           else HERE / "docs" / "runnerup.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        ru.save_traces(out.with_name(out.stem + "-traces.jsonl.gz"))
    except Exception as e:
        print(f"(traces not archived: {e})")
    slim = []
    for rec in ru.log:                 # the vector is 2.5k floats; keep its norm
        r = dict(rec)
        if r.get("vec"):
            r["vec"] = {"dim": len(r["vec"])}
        slim.append(r)
    out.write_text(json.dumps({
        "params": {"items": args.items, "channels": args.channel,
                   "control": args.control, "strength": args.strength,
                   "layer": ru.layer, "band": BAND, "topk": args.topk,
                   "temp": args.temp, "seed": args.seed, "model": model},
        "score": sc, "log": slim}, ensure_ascii=False, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
