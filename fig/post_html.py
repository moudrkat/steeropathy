"""A post from notes/ as one HTML page for pasting into LinkedIn: images point at raw.githubusercontent.com so LinkedIn fetches them.

    python fig/post_html.py notes/POST-sliders.md notes/POST-sliders.html
"""
import re, html, pathlib, sys
src = pathlib.Path(sys.argv[1]).read_text(); dst = pathlib.Path(sys.argv[2])
RAW = "https://raw.githubusercontent.com/moudrkat/steeropathy/main/"
import time
STAMP = int(time.time())   # a fresh query string, so the browser does not show yesterday's picture
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", s)
    return s
out, i, lines = [], 0, src.split("\n")
while i < len(lines):
    l = lines[i]
    if l.startswith("<!--"): i += 1; continue
    if l.strip() == "---": out.append("<hr>"); i += 1; continue
    if l.startswith("```"):
        buf = []; i += 1
        while i < len(lines) and not lines[i].startswith("```"): buf.append(lines[i]); i += 1
        out.append("<pre>" + html.escape("\n".join(buf)) + "</pre>"); i += 1; continue
    m = re.match(r"^(#+) (.*)", l)
    if m: out.append(f"<h{len(m.group(1))}>{inline(m.group(2))}</h{len(m.group(1))}>"); i += 1; continue
    m = re.match(r"^!\[([^\]]*)\]\(\.\./(.+)\)", l)
    if m: out.append(f'<p><img src="{RAW}{m.group(2)}?v={STAMP}" alt="{html.escape(m.group(1))}" style="max-width:100%"></p>'); i += 1; continue
    if l.startswith("- "):
        items = []
        while i < len(lines) and lines[i].startswith("- "): items.append("<li>" + inline(lines[i][2:]) + "</li>"); i += 1
        out.append("<ul>" + "".join(items) + "</ul>"); continue
    if l.strip() == "": i += 1; continue
    para = [l]; i += 1
    while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "!", "- ", "```")): para.append(lines[i]); i += 1
    out.append("<p>" + inline(" ".join(para)) + "</p>")
title = re.search(r"^# (.*)", src, re.M).group(1)
dst.write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font-family:Georgia,serif;max-width:720px;margin:40px auto;padding:0 16px;line-height:1.55;color:#222;background:#fff}}
h1{{font-size:2em;line-height:1.15}} h2{{margin-top:2em}} img{{display:block;margin:1em 0}} pre{{background:#f4f4f4;padding:12px;overflow:auto}}
.note{{background:#fff7d6;border:1px solid #e6d58a;padding:10px 14px;font-family:sans-serif;font-size:14px;margin-bottom:32px}}</style></head>
<body><div class="note">Kopírování na LinkedIn: označ od nadpisu dolů, Ctrl+C, vlož do editoru článku. Obrázky se natahují z GitHubu, LinkedIn si je stáhne sám.</div>
{chr(10).join(out)}</body></html>""")
print(dst)
