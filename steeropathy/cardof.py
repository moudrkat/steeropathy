"""cardof: the knobs on a normal UI.

worldof draws a place. This fills in a card everyone has seen on the web:
a title, a tagline, a price, a list of features, a button, a colour, a
tone. The model has to write the copy (creativity is not optional), and
the card is a typed readout: the number of features, the price, the
number of exclamation marks and emoji, the word count, and whether the
theme is dark. Then the knobs: directions built from the model's own
sentences, added at one layer, and the card changes. `manyfeatures` (a long
list − a single line), `cheaper` (a bargain − a luxury), `louder` (shouting
with exclamation marks − quiet and plain), `formal` (worldof's), `darker`
(worldof's, read off the theme colour). The placebo is the shuffled vector,
as always; the readings are numbers, so a strength sweep gives a curve.

    python -m steeropathy.cardof manyfeatures cheaper louder --strength 2 --placebo --n 8
    python fig/render_cardof.py docs/runs/cardof-01.json      # the cards, drawn
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
from .secondhand import lum, parse_spec
from .transmit import BAND, default_layer
from .worldof import CONTRASTS, LIKES, _pole, direction_for

HERE = pathlib.Path(__file__).parent.parent

ASK = "a product"
SYSTEM = ("You write the card for a product page. Answer with one JSON object and "
          "nothing else, with exactly these keys: title (string), tagline (string), "
          "price (a number), features (a list of strings), button (string), "
          "theme (a hex colour like #1a2b3c for the card background), tone "
          "(one of: playful, plain, formal).")
PROMPT = "Write the card for {ask}. Invent it. JSON only."

CARD_KNOBS = {
    "manyfeatures": {"target": ("count", "features"), "texts": [
        "It does everything: twelve features, a long list, benefit after benefit after benefit.",
        "So many things it can do, feature upon feature, the list goes on and on.",
        "A full page of features, every one of them included, more than you will ever use.",
        "Packed with features: dozens of them, all in the box, all listed.",
    ], "against": [
        "It does one thing. One feature, one line, that is all.",
        "A single thing it can do, said once, and nothing else on the list.",
        "One feature, included, and the page ends there.",
        "Just the one thing: one line, no list.",
    ]},
    "cheaper": {"target": ("price", None), "texts": [
        "A bargain: nearly free, the cheapest thing on the shelf, pennies.",
        "Dirt cheap, a giveaway price, costs almost nothing.",
        "The lowest price you have ever seen, a few coins, a steal.",
        "Practically free; nobody has ever paid less for anything.",
    ], "against": [
        "Luxury: eye-wateringly expensive, the priciest thing on the shelf, thousands.",
        "Premium, a fortune, costs more than a car.",
        "The highest price you have ever seen, a small mortgage, exclusive.",
        "Practically priceless; nobody has ever paid more for anything.",
    ]},
    "louder": {"target": ("bangs", None), "texts": [
        "WOW!!! Amazing!!! You will not BELIEVE this!!! Buy it NOW!!!",
        "Incredible!!! The BEST ever!!! Don't miss out!!! Hurry!!!",
        "STOP everything!!! This changes EVERYTHING!!! Act now!!!",
        "Unbelievable!!! Life-changing!!! Grab yours TODAY!!!",
    ], "against": [
        "It is available. Details are below, if you are interested.",
        "A description follows. The price is listed. Thank you.",
        "Here is the product. It works as described.",
        "It can be ordered. Delivery takes a few days.",
    ]},
}


def parse_card(text):
    d = parse_spec(text)
    if not isinstance(d, dict) or not d.get("title"):
        return None
    feats = d.get("features")
    if isinstance(feats, str):
        feats = [f.strip() for f in re.split(r"[;\n]", feats) if f.strip()]
    d["features"] = [str(f) for f in (feats or []) if str(f).strip()][:20]
    try:
        d["price"] = float(re.sub(r"[^\d.]", "", str(d.get("price", ""))) or "nan")
    except ValueError:
        d["price"] = float("nan")
    d["theme"] = str(d.get("theme") or "")
    return d


def read(card, what):
    """A number off the card."""
    if not card:
        return None
    text = " ".join([str(card.get("title", "")), str(card.get("tagline", "")),
                     " ".join(card["features"]), str(card.get("button", ""))])
    if what == "features":
        return float(len(card["features"]))
    if what == "price":
        p = card.get("price")
        return None if p is None or p != p else float(p)
    if what == "bangs":
        return float(text.count("!"))
    if what == "emoji":
        return float(len(re.findall(r"[\U0001F300-\U0001FAFF☀-➿]", text)))
    if what == "words":
        return float(len(text.split()))
    if what == "dark":
        v = lum(card.get("theme"))
        return None if v is None else 1.0 - v
    if what == "formal":
        return 1.0 if str(card.get("tone", "")).lower() == "formal" else 0.0
    if what == "caps":
        letters = [c for c in text if c.isalpha()]
        return round(sum(1 for c in letters if c.isupper()) / len(letters), 3) if letters else None
    return None


READINGS = ("features", "price", "bangs", "caps", "emoji", "words", "dark", "formal")


class Cardof(Eco):
    def __init__(self, url, layer=None, temp=0.8, max_tokens=400, seed=0, ask=ASK):
        self.url, self.judge_url = url, None
        self.layer = layer if layer is not None else default_layer(url)
        self.lo, self.hi = max(0, self.layer - BAND), self.layer + BAND
        self.temp, self.max_tokens, self.ask = temp, max_tokens, ask
        self.rng = random.Random(seed)
        self.demo_tag = f"steeropathy-cardof-{int(time.time())}"
        self.log = []

    def direction(self, name):
        if name in CARD_KNOBS:
            return _pole(self.url, CARD_KNOBS[name], self.layer)
        v, _, _ = direction_for(self.url, name, self.layer)
        return v

    def card(self, tag, steering=None):
        body = {"messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": PROMPT.format(ask=self.ask)}],
                "max_tokens": self.max_tokens, "temperature": self.temp,
                "metadata": {"demo": self.demo_tag, "case": tag[0], "variant": tag[1]}}
        if steering:
            body["steering"] = steering
        r = self.post("/v1/chat/completions", body)
        text = (r["choices"][0]["message"].get("content") or "").strip()
        return parse_card(text), text


def summarize(runs):
    bases = [r["card"] for r in runs if r.get("kind") == "base" and r.get("card")]
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
        g = groups.setdefault(key, {"n": 0, "cards": []})
        g["n"] += 1
        if r.get("card"):
            g["cards"].append(r["card"])
    for key, g in groups.items():
        d = {"n": g["n"], "parsed": len(g["cards"]),
             "parse_rate": round(len(g["cards"]) / g["n"], 2) if g["n"] else None}
        for k in READINGS:
            d[k] = mean(read(c, k) for c in g["cards"])
        out[key] = d
    return out


def print_summary(s):
    if not s:
        return
    b = s["base"]
    print(f"\nunsteered ({b['n']} cards): " + " · ".join(f"{k} {b[k]}" for k in READINGS))
    print(f"\n{'direction':22s} parse " + "".join(f"{k:>10s}" for k in READINGS))
    for key, d in s.items():
        if key == "base":
            continue
        print(f"{key:22s} {d['parse_rate']!s:>5s} " + "".join(f"{d[k]!s:>10s}" for k in READINGS))


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
    ap.add_argument("--ask", default=ASK, help="what the card is for (\"a product\", \"a bicycle\", …)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    co = Cardof(args.url, layer=args.layer, temp=args.temp, seed=args.seed, ask=args.ask)
    print(f"cardof: {' '.join(args.names)} · strength {args.strength} · layer {co.layer} (±{BAND}) · {args.n} per direction\n")
    dirs = {n: co.direction(n) for n in args.names}
    runs = []
    out = pathlib.Path(args.out) if args.out else HERE / "docs" / "cardof.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    def save(final=False):
        try:
            model = co.get("/info").get("model")
        except Exception:
            model = "unknown"
        out.write_text(json.dumps({"params": {k: v for k, v in vars(args).items() if k != "url"},
                                   "layer": co.layer, "model": model, "complete": final,
                                   "summary": summarize(runs), "runs": runs}, ensure_ascii=False, indent=1))

    def show(rep, label, c, text):
        if not c:
            print(f"[{rep}] {label:22s} did not parse: {text[:70]!r}")
            return
        print(f"[{rep}] {label:22s} \"{c.get('title')}\" · {c.get('price')} · {len(c['features'])} features · "
              f"{read(c, 'bangs'):.0f}! · {c.get('tone')} · {c.get('theme')} · {str(c.get('tagline'))[:50]!r}")

    for rep in range(args.n):
        c, text = co.card(("base", f"r{rep}"))
        show(rep, "unsteered", c, text)
        runs.append({"rep": rep, "name": "none", "kind": "base", "card": c, "raw": text[:800]})
        for name in args.names:
            v = dirs[name]
            variants = [("real", v)]
            if args.placebo:
                variants.append(("placebo", signed_perm(v, seed=args.seed * 1000 + rep * 10 + args.names.index(name))))
            for kind, vec in variants:
                co.post("/directions", {"name": "cardof:rx", "vector": vec})
                steer = {"name": "cardof:rx", "strength": args.strength,
                         "layer_from": co.lo, "layer_to": co.hi}
                c, text = co.card((f"{name}-{kind}", f"r{rep}"), steer)
                show(rep, name if kind == "real" else f"{name} ({kind})", c, text)
                runs.append({"rep": rep, "name": name, "kind": kind, "card": c, "raw": text[:800]})
        save()
    print_summary(summarize(runs))
    save(final=True)
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
