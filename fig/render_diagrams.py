"""Two diagrams for the sliders post, drawn as SVG and shot with headless
Chrome so they match the strips: where the vector goes into the model, and
who turns the slider.

    python fig/render_diagrams.py            # docs/story/diagram-method.png, docs/story/diagram-loop.png
"""
import pathlib
import subprocess
import tempfile

HERE = pathlib.Path(__file__).parent.parent
VEC, ROTC, INK, INK2, GRID, SURF, BLUE = "#eb6834", "#a8a6a1", "#141414", "#6b6964", "#e6e5e1", "#fcfcfb", "#2a78d6"
FONT = "Lato, 'DejaVu Sans', sans-serif"


def method_svg():
    """The model as a stack of layers; the slider adds α·v into the middle band; the top writes the form; the page draws it."""
    W, H = 1200, 560
    layers = 28
    x0, lw, gap = 190, 20, 5      # the stack as a row of thin columns
    cols = []
    for i in range(layers):
        x = x0 + i * (lw + gap)
        band = 12 <= i <= 20
        cols.append(f'<rect x="{x}" y="230" width="{lw}" height="150" rx="4" fill="{VEC if band else GRID}" opacity="{0.55 if band else 1}"/>')
        if i in (0, 12, 20, 27):
            cols.append(f'<text x="{x + lw / 2}" y="400" font-size="13" fill="{INK2}" text-anchor="middle">{i}</text>')
    stack = "".join(cols)
    bx0, bx1 = x0 + 12 * (lw + gap), x0 + 20 * (lw + gap) + lw
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="{FONT}">
<rect width="{W}" height="{H}" fill="{SURF}"/>
<!-- prompt in -->
<text x="40" y="312" font-size="16" fill="{INK}">“a place”</text>
<line x1="{x0 - 70}" y1="306" x2="{x0 - 8}" y2="306" stroke="{INK2}" stroke-width="1.5" marker-end="url(#a)"/>
<!-- the stack -->
{stack}
<text x="{x0}" y="215" font-size="13" fill="{INK2}">layer</text>
<text x="{x0 + 4 * (lw + gap)}" y="215" font-size="13" fill="{INK2}">h: one vector per layer, per token</text>
<!-- the slider -->
<text x="{(bx0 + bx1) / 2}" y="120" font-size="22" fill="{VEC}" text-anchor="middle" font-weight="600">+ α · v</text>
<text x="{(bx0 + bx1) / 2}" y="146" font-size="13" fill="{INK2}" text-anchor="middle">v = mean h(sad sentences) − mean h(flat sentences), length 1</text>
<text x="{(bx0 + bx1) / 2}" y="166" font-size="13" fill="{INK2}" text-anchor="middle">α = the slider, −3 … 3</text>
<line x1="{(bx0 + bx1) / 2}" y1="176" x2="{(bx0 + bx1) / 2}" y2="222" stroke="{VEC}" stroke-width="2.5" marker-end="url(#o)"/>
<text x="{(bx0 + bx1) / 2}" y="425" font-size="13" fill="{VEC}" text-anchor="middle">layers 12 to 20, at every token</text>
<!-- form out -->
<line x1="{x0 + 28 * (lw + gap) + 2}" y1="306" x2="{x0 + 28 * (lw + gap) + 56}" y2="306" stroke="{INK2}" stroke-width="1.5" marker-end="url(#a)"/>
<g transform="translate({x0 + 28 * (lw + gap) + 66}, 236)">
<rect width="170" height="140" rx="8" fill="#fff" stroke="{GRID}"/>
<text x="12" y="24" font-size="12" fill="{INK}">time: dawn</text>
<text x="12" y="46" font-size="12" fill="{INK}">weather: stars</text>
<text x="12" y="68" font-size="12" fill="{INK}">ground: ice</text>
<text x="12" y="90" font-size="12" fill="{INK}">things: moon, cat</text>
<text x="12" y="112" font-size="12" fill="{INK}">poem: two lines</text>
<text x="12" y="132" font-size="11" fill="{INK2}">the form</text>
</g>
<text x="{x0 + 28 * (lw + gap) + 151}" y="215" font-size="13" fill="{INK2}" text-anchor="middle">the form, then the page draws it</text>
<defs>
<marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="{INK2}"/></marker>
<marker id="o" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="{VEC}"/></marker>
</defs>
<text x="40" y="520" font-size="13" fill="{INK2}">the same vector with its coordinates shuffled, same length, is the control: what the push alone does</text>
</svg>"""


def loop_svg():
    """User → planner → numbers → the model that draws → screen → the user's click → planner."""
    W, H = 1100, 420
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="{FONT}">
<rect width="{W}" height="{H}" fill="{SURF}"/>
<defs>
<marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="{INK2}"/></marker>
<marker id="o" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="{VEC}"/></marker>
</defs>
<!-- user -->
<circle cx="110" cy="210" r="46" fill="#fff" stroke="{GRID}" stroke-width="2"/>
<text x="110" y="216" font-size="15" fill="{INK}" text-anchor="middle">the user</text>
<!-- planner -->
<rect x="330" y="80" width="200" height="80" rx="12" fill="#fff" stroke="{GRID}" stroke-width="2"/>
<text x="430" y="114" font-size="16" fill="{INK}" text-anchor="middle" font-weight="600">the planner</text>
<text x="430" y="138" font-size="12" fill="{INK2}" text-anchor="middle">reads the whole conversation</text>
<!-- model -->
<rect x="640" y="170" width="220" height="80" rx="12" fill="#fff" stroke="{GRID}" stroke-width="2"/>
<text x="750" y="204" font-size="16" fill="{INK}" text-anchor="middle" font-weight="600">the model that draws</text>
<text x="750" y="228" font-size="12" fill="{INK2}" text-anchor="middle">small, local, the prompt never changes</text>
<!-- screen -->
<rect x="640" y="300" width="220" height="80" rx="12" fill="#fff" stroke="{GRID}" stroke-width="2"/>
<text x="750" y="334" font-size="16" fill="{INK}" text-anchor="middle" font-weight="600">the screen</text>
<text x="750" y="358" font-size="12" fill="{INK2}" text-anchor="middle">a question, buttons, tasks, steps</text>
<!-- arrows -->
<line x1="150" y1="180" x2="322" y2="128" stroke="{INK2}" stroke-width="1.8" marker-end="url(#a)"/>
<text x="70" y="140" font-size="12" fill="{INK2}">what they said, what they clicked</text>
<line x1="532" y1="132" x2="632" y2="196" stroke="{VEC}" stroke-width="3" marker-end="url(#o)"/>
<text x="600" y="120" font-size="14" fill="{VEC}" font-weight="600">numbers, one per slider</text>
<text x="600" y="140" font-size="12" fill="{INK2}">no sentence</text>
<line x1="750" y1="252" x2="750" y2="292" stroke="{INK2}" stroke-width="1.8" marker-end="url(#a)"/>
<line x1="632" y1="340" x2="160" y2="240" stroke="{INK2}" stroke-width="1.8" marker-end="url(#a)"/>
<text x="330" y="330" font-size="12" fill="{INK2}">drawn, in the browser</text>
<line x1="890" y1="200" x2="960" y2="200" stroke="{ROTC}" stroke-width="1.8" stroke-dasharray="5 4" marker-end="url(#a)"/>
<text x="970" y="196" font-size="12" fill="{INK2}">the planner can read</text>
<text x="970" y="212" font-size="12" fill="{INK2}">the state back, too</text>
</svg>"""


def shoot(svg, out, w, h):
    tmp = pathlib.Path(tempfile.mkdtemp()) / "d.html"
    tmp.write_text(f'<!doctype html><meta charset="utf-8"><style>body{{margin:0;background:{SURF}}}</style>{svg}')
    subprocess.run(["google-chrome", "--headless=new", f"--window-size={w},{h}", "--hide-scrollbars",
                    "--force-device-scale-factor=2", "--virtual-time-budget=1500", f"--screenshot={out}", f"file://{tmp}"],
                   check=True, capture_output=True)
    print(out)


if __name__ == "__main__":
    out = HERE / "docs" / "story"
    shoot(method_svg(), out / "diagram-method.png", 1200, 560)
    shoot(loop_svg(), out / "diagram-loop.png", 1100, 420)
