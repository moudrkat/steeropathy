"""A blind reading pack for a human judge: per wish, the four candidate
wishes and B's pages under each channel, shuffled and lettered, with the
rendered world as a link. The key goes to a separate file. Read the pack,
write your picks into the answer sheet, then `--score`.

    python fig/blind_pack.py docs/runs/secondhand-11-aorus-1.5b-both-judge.json
    -> docs/blind/<run>.html, docs/blind/<run>-key.json, docs/blind/<run>-answers.json (to fill)
    python fig/blind_pack.py docs/runs/<run>.json --score
"""
import argparse
import html
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(HERE))
from steeropathy.secondhand import WISHES, kinds_of  # noqa: E402


def page_text(spec):
    w = spec or {}
    lines = [l for l in (w.get("lines") or []) if isinstance(l, str)]
    fields = " · ".join(str(w.get(k)) for k in ("time", "weather", "ground", "motion", "font") if w.get(k))
    things = ", ".join(dict.fromkeys(kinds_of(w)))
    return (w.get("title") or "").strip(), lines, fields, things


def build(run, seed):
    d = json.loads(pathlib.Path(run).read_text())
    rng = random.Random(seed)
    out_dir = HERE / "docs" / "blind"
    out_dir.mkdir(exist_ok=True)
    stem = pathlib.Path(run).stem
    key, answers, parts = {}, {}, []
    parts.append(f"<h1>Blind reading: {html.escape(stem)}</h1><p>For each item: four wishes, four pages drawn by "
                 "mind B, which was told only <i>a place</i> plus one hidden channel. Which wish was mind A given? "
                 "Write the letter of your pick per page into the answer sheet. Pages are shuffled; the key is in a separate file.</p>")
    for rec in d["log"]:
        if rec.get("skipped"):
            continue
        i, wish = rec["item"], rec["wish"]
        others = [w for w in WISHES if w != wish]
        four = [wish] + rng.sample(others, 3)
        rng.shuffle(four)
        reads = [r for r in rec["reads"] if r.get("b")]
        rng.shuffle(reads)
        letters = "ABCD"[:len(reads)]
        key[str(i)] = {"wish": wish, "options": four,
                       "pages": {L: r["channel"] for L, r in zip(letters, reads)}}
        answers[str(i)] = {L: None for L in letters}
        parts.append(f"<h2>Item {i}</h2><ol type='1'>" + "".join(f"<li>{html.escape(w)}</li>" for w in four) + "</ol>")
        for L, r in zip(letters, reads):
            t, lines, fields, things = page_text(r["b"])
            link = r.get("b_link", "")
            parts.append(f"<div class='page'><b>Page {L}</b> "
                         + (f"<a href='{html.escape(link)}' target='_blank'>open the world</a>" if link else "")
                         + f"<div class='title'>“{html.escape(t)}”</div>"
                         + "".join(f"<div class='line'><i>{html.escape(l)}</i></div>" for l in lines)
                         + f"<div class='fields'>{html.escape(fields)}</div><div class='fields'>{html.escape(things)}</div></div>")
    css = ("<style>body{font-family:sans-serif;max-width:900px;margin:2em auto;line-height:1.4}"
           ".page{border:1px solid #ddd;padding:.6em 1em;margin:.5em 0;border-radius:6px}"
           ".title{font-weight:bold;margin-top:.3em}.fields{color:#666;font-size:.9em}</style>")
    (out_dir / f"{stem}.html").write_text("<!doctype html><meta charset='utf-8'>" + css + "".join(parts))
    (out_dir / f"{stem}-key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1))
    ans = out_dir / f"{stem}-answers.json"
    if not ans.exists():
        ans.write_text(json.dumps(answers, ensure_ascii=False, indent=1))
    print(out_dir / f"{stem}.html")
    print(ans, "(fill in: item -> page letter -> option number 1-4)")


def score(run):
    stem = pathlib.Path(run).stem
    out_dir = HERE / "docs" / "blind"
    key = json.loads((out_dir / f"{stem}-key.json").read_text())
    ans = json.loads((out_dir / f"{stem}-answers.json").read_text())
    hit, tot = {}, {}
    for i, k in key.items():
        for L, ch in k["pages"].items():
            a = (ans.get(i) or {}).get(L)
            if a is None:
                continue
            tot[ch] = tot.get(ch, 0) + 1
            if k["options"][int(a) - 1] == k["wish"]:
                hit[ch] = hit.get(ch, 0) + 1
    print("human judge, wish picked of four, per channel:")
    for ch in ("none", "text", "vector", "both"):
        if ch in tot:
            print(f"  {ch:7s} {hit.get(ch, 0)}/{tot[ch]}  ({hit.get(ch, 0) / tot[ch]:.2f})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args()
    if a.score:
        score(a.run)
    else:
        build(a.run, a.seed)


if __name__ == "__main__":
    main()
