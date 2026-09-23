"""Two worlds side by side: A's (the wish) and B's (secondhand), shot from
their brave-new-world links with headless Chrome, no model loaded.

    python fig/render_secondhand.py docs/secondhand.json --item 0 --channel vector
    python fig/render_secondhand.py docs/secondhand.json --all --channel vector   # one png per wish

The links render on the public Space; pass --site http://localhost:8080/ to
shoot a local checkout (python -m http.server 8080 in brave-new-world).
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import tempfile

HERE = pathlib.Path(__file__).parent.parent


def shoot(url, out, w=1200, h=760, chrome=None):
    chrome = chrome or shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        raise SystemExit("no chrome/chromium on PATH")
    subprocess.run([chrome, "--headless=new", f"--window-size={w},{h}",
                    "--hide-scrollbars", "--virtual-time-budget=6000",
                    f"--screenshot={out}", url], check=True,
                   capture_output=True)


def pair(rec, read, out, site=None, chrome=None):
    a, b = rec["a_link"], read["b_link"]
    if site:
        a = site + a[a.index("#"):]
        b = site + b[b.index("#"):]
    with tempfile.TemporaryDirectory() as td:
        la, lb = pathlib.Path(td) / "a.png", pathlib.Path(td) / "b.png"
        shoot(a, la, chrome=chrome)
        shoot(b, lb, chrome=chrome)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(la),
                        "-i", str(lb), "-filter_complex", "hstack", str(out)],
                       check=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json", nargs="?", default=str(HERE / "docs" / "secondhand.json"))
    ap.add_argument("--item", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--channel", default="vector")
    ap.add_argument("--site", default=None)
    ap.add_argument("--chrome", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    d = json.loads(pathlib.Path(args.json).read_text())
    items = [r for r in d["log"] if not r.get("skipped")]
    picks = items if args.all else [items[args.item]]
    outdir = HERE / "fig" / "build-secondhand"
    outdir.mkdir(exist_ok=True)
    for rec in picks:
        read = next((r for r in rec["reads"]
                     if r["channel"] == args.channel and r.get("b_link")), None)
        if not read:
            print(f"w{rec['item']}: no parsed {args.channel} world")
            continue
        out = (pathlib.Path(args.out) if args.out and not args.all
               else outdir / f"w{rec['item']}-{args.channel}.png")
        pair(rec, read, out, site=args.site, chrome=args.chrome)
        print(f"w{rec['item']} {rec['wish']!r} → {out}")


if __name__ == "__main__":
    main()
