"""Eye-catching vertical thumbnail (1080x1920 JPG, < 2 MB) for a Short, with Roman Urdu text.

    python3 thumbnail.py --frame still.png --font Anton.ttf --out thumb.jpg \
        --line "DASTANE SE" --line "PHONE KYUN" --line "NAHI CHALTA?" --hi "KYUN" \
        [--point 420,800] [--tag "HOW IT WORKS"]

--frame  a 1080x1920 still of the most intriguing moment (no captions burnt in)
--line   1-4 short lines, ALL CAPS Roman Urdu (3-5 words in total is best)
--hi     words drawn black-on-yellow (repeatable)
--point  optional x,y of the thing to look at: gets a glowing ring + arrow
"""
import argparse, math

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H = 1080, 1920
YELLOW, RED, WHITE, INK = (255, 214, 46), (235, 48, 52), (255, 255, 255), (16, 16, 20)


def fit_font(path, lines, max_w, start=190, min_size=96):
    size = start
    while size > min_size:
        f = ImageFont.truetype(path, size)
        if all(f.getlength(l) <= max_w for l in lines): return f
        size -= 6
    return ImageFont.truetype(path, min_size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", required=True); ap.add_argument("--font", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--line", action="append", required=True); ap.add_argument("--hi", action="append", default=[])
    ap.add_argument("--point"); ap.add_argument("--tag", default="HOW IT WORKS")
    ap.add_argument("--shift", type=int, default=420, help="push the still down by this many px to free the top for text")
    a = ap.parse_args()
    hi = {w.upper() for w in a.hi}

    src = Image.open(a.frame).convert("RGB").resize((W, H))
    src = ImageEnhance.Contrast(ImageEnhance.Color(src).enhance(1.35)).enhance(1.12)
    # background: the same still, blown up, blurred and dark; foreground: the still pushed down with a soft top edge
    base = src.resize((int(W * 1.4), int(H * 1.4)), Image.LANCZOS).crop((int(W * .2), 0, int(W * .2) + W, H))
    base = ImageEnhance.Brightness(base.filter(ImageFilter.GaussianBlur(40))).enhance(0.45)
    fg = src.crop((0, int(H * 0.10), W, H))                 # drop the top 10% (the video's own title/tag lives there)
    sh = a.shift; mask = Image.new("L", fg.size, 255); md = ImageDraw.Draw(mask)
    for y in range(320):
        md.line([(0, y), (W, y)], fill=int(255 * (y / 320) ** 1.5))
    base.paste(fg, (0, sh - int(H * 0.10) + int(H * 0.10)), mask)
    img = base.convert("RGBA")

    # darken top (text) and edges, keep the middle bright
    shade = Image.new("L", (W, H), 0); d = ImageDraw.Draw(shade)
    for y in range(H):
        top = max(0.0, 1 - y / (H * 0.48)) ** 1.3 * 215
        bot = max(0.0, (y - H * 0.80) / (H * 0.20)) * 160
        d.line([(0, y), (W, y)], fill=int(min(235, top + bot)))
    img = Image.composite(Image.new("RGBA", (W, H), (6, 8, 14, 255)), img, shade)
    vig = Image.new("L", (W, H), 0); ImageDraw.Draw(vig).ellipse((-W * .35, -H * .15, W * 1.35, H * 1.15), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(160))
    img = Image.composite(img, Image.new("RGBA", (W, H), (0, 0, 0, 255)), vig)

    # focus ring + arrow
    if a.point:
        px, py = (int(v) for v in a.point.split(","))
        py = py - int(H * 0.10) + a.shift
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
        g.ellipse((px - 175, py - 175, px + 175, py + 175), outline=RED + (255,), width=34)
        glow = glow.filter(ImageFilter.GaussianBlur(18)); img.alpha_composite(glow)
        ring = Image.new("RGBA", (W, H), (0, 0, 0, 0)); r = ImageDraw.Draw(ring)
        r.ellipse((px - 160, py - 160, px + 160, py + 160), outline=RED + (255,), width=16)
        ax, ay = (W - 110, py - 300) if px < W / 2 else (110, py - 300)
        ang = math.atan2(py - ay, px - ax); ex, ey = px - math.cos(ang) * 190, py - math.sin(ang) * 190
        r.line([(ax, ay), (ex, ey)], fill=RED + (255,), width=28)
        for s in (-1, 1):
            r.line([(ex, ey), (ex - math.cos(ang + s * 0.55) * 80, ey - math.sin(ang + s * 0.55) * 80)], fill=RED + (255,), width=28)
        sh = ring.filter(ImageFilter.GaussianBlur(10)); img.alpha_composite(Image.eval(sh, lambda v: v // 2))
        img.alpha_composite(ring)

    # tag pill
    tf = ImageFont.truetype(a.font, 64); tw = tf.getlength(a.tag)
    pill = Image.new("RGBA", (W, H), (0, 0, 0, 0)); p = ImageDraw.Draw(pill)
    p.rounded_rectangle(((W - tw) / 2 - 34, 110, (W + tw) / 2 + 34, 200), 18, fill=RED + (255,))
    p.text((W / 2, 155), a.tag, font=tf, fill=WHITE, anchor="mm")
    img.alpha_composite(pill)

    # headline
    lines = [l.upper() for l in a.line]
    f = fit_font(a.font, lines, W - 120)
    lh = int(f.size * 1.08); y0 = 260
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); t = ImageDraw.Draw(txt)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); s = ImageDraw.Draw(shadow)
    for i, line in enumerate(lines):
        words = line.split(); space = f.getlength(" ")
        total = sum(f.getlength(w) for w in words) + space * (len(words) - 1)
        x = (W - total) / 2; y = y0 + i * lh
        for w in words:
            ww = f.getlength(w)
            if w.strip("?!.,") in hi or w in hi:
                bb = f.getbbox(w)                     # box from the real glyph extent (fonts differ in ascent)
                t.rounded_rectangle((x - 18, y + bb[1] - 16, x + ww + 18, y + bb[3] + 16), 16, fill=YELLOW + (255,))
                t.text((x, y), w, font=f, fill=INK)
            else:
                s.text((x + 8, y + 12), w, font=f, fill=(0, 0, 0, 200))
                t.text((x, y), w, font=f, fill=WHITE, stroke_width=10, stroke_fill=INK)
            x += ww + space
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
    img.alpha_composite(txt.rotate(-2.5, resample=Image.BICUBIC, center=(W / 2, y0 + lh * len(lines) / 2)))

    out = img.convert("RGB")
    q = 92
    while True:
        out.save(a.out, "JPEG", quality=q, optimize=True, progressive=True)
        import os
        if os.path.getsize(a.out) < 1_900_000 or q <= 60: break
        q -= 6
    print("thumbnail ->", a.out)


if __name__ == "__main__":
    main()
