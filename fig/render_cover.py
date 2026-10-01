"""Cover picture for the sliders article: three sliders, the model with the numbers
a slider adds, and the screen it draws. No world, no equation.

    .venv/bin/python fig/render_cover.py            # -> docs/sliders-cover.png
"""
import pathlib

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent
OUT = HERE.parent / "docs" / "sliders-cover.png"
FONT = "/usr/share/fonts/truetype/lato/Lato-Regular.ttf"
FONT_B = "/usr/share/fonts/truetype/lato/Lato-Semibold.ttf"
FONT_I = "/usr/share/fonts/truetype/lato/Lato-Italic.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
SURF, INK, INK2, GRID, VEC, VEC_SOFT = (252, 252, 251), (20, 20, 20), (107, 105, 100), (228, 227, 222), (235, 104, 52), (247, 178, 148)
W, H = 1920, 1080


def main():
    img = Image.new("RGB", (W, H), SURF)
    d = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(FONT_B, 54)
    f_lab = ImageFont.truetype(FONT_B, 40)
    f_small = ImageFont.truetype(FONT, 28)
    f_num = ImageFont.truetype(MONO, 26)
    f_it = ImageFont.truetype(FONT_I, 30)

    # the line that explains it
    d.text((120, 92), "The sliders are not in the page. They are inside the model.", fill=INK, font=f_title)

    # --- the model's geometry first, so the turned-up slider sits on the band's line
    mx0, mx1 = 760, 1180
    n, band = 28, (12, 20)
    top, bot = 330, 790
    lh = (bot - top) / n
    ay = top + (band[0] + band[1] + 1) / 2 * lh

    # --- left: three sliders, one turned up
    x0, x1 = 160, 540
    rows = [("night", 0.0, 400), ("crowded", 0.0, 505), ("sad", 0.85, ay)]
    for name, val, y in rows:
        d.text((x0, y - 58), name, fill=INK, font=f_lab)
        d.rounded_rectangle([x0, y - 7, x1, y + 7], radius=7, fill=GRID)
        mid = (x0 + x1) / 2
        kx = mid + val * (x1 - mid)
        col = VEC if val > 0.01 else INK2
        if val > 0.01:
            d.rounded_rectangle([mid, y - 7, kx, y + 7], radius=7, fill=VEC)
        d.ellipse([kx - 22, y - 22, kx + 22, y + 22], fill=col)
        d.text((x1 + 26, y - 20), f"{val * 3.5:+.1f}" if val > 0.01 else "0", fill=col, font=f_small)
    d.text((x0, 790), "the prompt says: a place", fill=INK2, font=f_it)

    # --- middle: the model, a stack of layers; the slider enters the middle band with its numbers
    for k in range(n):
        y = top + k * lh
        col = VEC_SOFT if band[0] <= k <= band[1] else GRID
        d.rounded_rectangle([mx0, y + 3, mx1, y + lh - 3], radius=6, fill=col)
    d.text((mx0, 262), "the model", fill=INK, font=f_lab)
    # arrow from the sad slider straight into the band
    d.line([(x1 + 120, ay), (mx0 - 30, ay)], fill=VEC, width=5)
    d.polygon([(mx0 - 30, ay - 14), (mx0 - 2, ay), (mx0 - 30, ay + 14)], fill=VEC)
    # the numbers it adds, in a pill on the band
    nums = ["+0.07", "-0.16", "+0.11", "-0.06", "…"]
    widths = [d.textlength(s, font=f_num) for s in nums]
    total = sum(widths) + 16 * (len(nums) - 1)
    px = (mx0 + mx1) / 2 - total / 2
    d.rounded_rectangle([px - 20, ay - 24, px + total + 40, ay + 24], radius=12, fill=(255, 255, 255))
    tx = px
    for s, w in zip(nums, widths):
        d.text((tx, ay - 16), s, fill=VEC, font=f_num)
        tx += w + 16
    d.text((mx0, 812), "a few thousand numbers, nudged at every token", fill=INK2, font=f_small)

    # --- right: the screen it draws, abstract blocks
    sx0, sy0, sx1, sy1 = 1400, 330, 1780, 830
    d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=26, fill=(255, 255, 255), outline=GRID, width=4)
    d.text((sx0, 262), "the screen it draws", fill=INK, font=f_lab)
    pad = 34
    # headline bar, two text lines, a picture block, a button
    d.rounded_rectangle([sx0 + pad, sy0 + 40, sx1 - pad, sy0 + 86], radius=8, fill=INK)
    d.rounded_rectangle([sx0 + pad, sy0 + 112, sx1 - 90, sy0 + 130], radius=6, fill=GRID)
    d.rounded_rectangle([sx0 + pad, sy0 + 148, sx1 - 150, sy0 + 166], radius=6, fill=GRID)
    d.rounded_rectangle([sx0 + pad, sy0 + 200, sx1 - pad, sy0 + 380], radius=14, fill=(238, 237, 233))
    # tiny "moon and stars" inside the picture block, because sad was turned up at night? no: keep abstract
    for (cx, cy, r) in ((sx0 + 90, sy0 + 250, 5), (sx0 + 180, sy0 + 230, 4), (sx0 + 300, sy0 + 270, 5), (sx1 - 90, sy0 + 240, 4)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=INK2)
    d.rounded_rectangle([sx0 + pad, sy0 + 410, sx1 - 120, sy0 + 428], radius=6, fill=GRID)
    d.rounded_rectangle([sx0 + pad, sy0 + 446, sx1 - 200, sy0 + 464], radius=6, fill=GRID)
    d.rounded_rectangle([sx0 + pad, sy1 - 70, sx0 + pad + 150, sy1 - 30], radius=10, fill=VEC)
    # arrow model -> screen
    d.line([(mx1 + 30, ay), (sx0 - 40, ay)], fill=INK2, width=5)
    d.polygon([(sx0 - 40, ay - 14), (sx0 - 12, ay), (sx0 - 40, ay + 14)], fill=INK2)

    d.text((120, 960), "steeropathy · moudrkat", fill=INK2, font=f_small)
    img.save(OUT)
    print(OUT, img.size)


if __name__ == "__main__":
    main()
