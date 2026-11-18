"""Glyph art drawn in code (1.6.0): the pictures that are too small or too exact for Retro Diffusion, and the
sets that must read as one family. Writes tools/data/glyph_src/<name>.png; `python tools/build.py build` puts
them into the glyph sheets in their existing cells.

  python tools/art/derive_glyphs.py

  bowl.half / bowl.full   the picked Retro Diffusion bowl (bowl.empty.png) with feed pellets half way up / heaped
  moon.0 .. moon.7        a cratered moon, lit the way tools/glyphs.py d_moon_phase lights it (0 full, 4 new)
  tide.high/low/slack     a striped tide post in the water: the water near the top, the bottom, the middle
  sky.meteor              a star with a fading trail; sky.aurora: green and violet curtains over dark hills
  dot.*, mark.*, arrow.*  bold shapes with a 1 px shade and the white outline of vanilla's controller glyphs
  tier.few/some/many      three bars, one / two / three of them filled (the creel picker's amounts)
  ui.animation            a film frame with a spark
Every glyph has a white outline (symbols sit on dark and light panels). Deterministic: same code, same pixels.
"""
import math, os, sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
import glyphs  # noqa: E402

SRC = os.path.join(ROOT, "tools", "data", "glyph_src")
WHITE = (255, 255, 255, 255)
PELLET = [(250, 212, 110, 255), (230, 160, 60, 255), (184, 112, 40, 255)]


def canvas():
    return Image.new("RGBA", (16, 16), (0, 0, 0, 0))


def outline(img):
    return glyphs.outline(img, WHITE)


def shade_bottom(img, factor=0.72, rows=2):
    """Darken the lowest `rows` pixels of every column: a little volume on a flat shape."""
    px = img.load()
    for x in range(16):
        ys = [y for y in range(16) if px[x, y][3]]
        for y in ys[-rows:] if ys else ():
            r, g, b, a = px[x, y]
            if (r, g, b) != (255, 255, 255):
                px[x, y] = (int(r * factor), int(g * factor), int(b * factor), a)
    return img


# ------------------------------------------------------------------ feed bowls
def pellet(x, y):
    return PELLET[(x * 3 + y * 5) % 7 % 3]


def bowl(level):
    img = Image.open(os.path.join(SRC, "bowl.empty.png")).convert("RGBA")
    px = img.load()
    for y in {"half": range(5, 8), "full": range(4, 8)}[level]:
        xs = [x for x in range(16) if px[x, y][3] and px[x, y][:3] != (255, 255, 255)]
        for x in range(min(xs) + 2, max(xs) - 1) if xs else ():
            px[x, y] = pellet(x, y)
    if level == "full":                      # a heap over the rim, with its own white edge
        heap = {3: range(4, 12), 2: range(5, 11), 1: range(7, 9)}
        for y, xs in heap.items():
            for x in xs:
                px[x, y] = pellet(x, y)
            px[xs.start - 1, y] = px[xs.stop, y] = WHITE
        px[6, 1] = px[9, 1] = px[7, 0] = px[8, 0] = WHITE
    return img


# ------------------------------------------------------------------ moon
CRATERS = [(5, 5, 1.6), (10, 9, 2.0), (6, 11, 1.2), (11, 4, 1.0)]


def moon(phase):
    base = canvas()
    glyphs.d_moon_phase(base, phase)
    b = base.load()
    img = canvas()
    px = img.load()
    for y in range(16):
        for x in range(16):
            if not b[x, y][3]:
                continue
            lit = b[x, y][0] > 150
            crater = any((x - cx) ** 2 + (y - cy) ** 2 <= r * r for cx, cy, r in CRATERS)
            rim = (x - 7.5) ** 2 + (y - 7.5) ** 2 > 4.9 ** 2     # a darker limb
            if lit:
                c = (214, 200, 130) if crater else (246, 238, 184)
                if rim:
                    c = tuple(int(v * 0.88) for v in c)
            else:
                c = (44, 46, 66) if crater else (62, 64, 88)
            px[x, y] = c + (255,)
    return outline(img)


# ------------------------------------------------------------------ tide
WATER, WATER_DK, FOAM = (64, 132, 222, 255), (40, 92, 176, 255), (210, 236, 255, 255)
POST, POST_DK, BAND = (150, 104, 60, 255), (98, 64, 34, 255), (226, 60, 50, 255)


def tide(kind):
    img = canvas()
    px = img.load()
    level = {"high": 4, "slack": 8, "low": 12}[kind]          # the water's surface row
    for y in range(level, 15):                                # the water
        for x in range(2, 14):
            px[x, y] = FOAM if y == level and x % 3 != 1 else (WATER if (x + y) % 5 else WATER_DK)
    for y in range(1, 15):                                    # the post, with red bands, in front of the water
        for x in (7, 8):
            px[x, y] = BAND if y in (3, 7, 11) else (POST if x == 7 else POST_DK)
    return outline(img)


# ------------------------------------------------------------------ sky
def meteor():
    img = canvas()
    px = img.load()
    trail = [(255, 250, 220), (255, 236, 170), (250, 210, 120), (230, 170, 90), (190, 130, 90), (150, 110, 110)]
    for i in range(10):                                       # the trail, up and right of the head
        x, y = 5 + i, 10 - i
        c = trail[min(len(trail) - 1, i // 2)]
        px[x, y] = c + (255,)
        if i < 7:
            px[x, y + 1] = tuple(int(v * 0.8) for v in c) + (255,)
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):  # the star head
        px[4 + dx, 11 + dy] = (255, 255, 230, 255)
    px[2, 11] = px[6, 11] = px[4, 9] = px[4, 13] = (255, 220, 110, 255)
    return outline(img)


def aurora():
    img = canvas()
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, 15, 15), fill=(18, 22, 52, 255))
    px = img.load()
    for x in range(16):                                       # two curtains, hanging in waves
        top_v = 3 + round(1.2 * math.sin(x * 0.7 + 2.2))
        top_g = 7 + round(1.2 * math.sin(x * 0.7))
        if px[x, top_v][3]:
            px[x, top_v] = (176, 96, 220, 255)
        for y in (top_g, top_g + 1):
            if px[x, y][3]:
                px[x, y] = (120, 240, 150, 255) if y == top_g else (60, 170, 110, 255)
    for x in range(16):                                       # dark hills
        h = 12 - round(1.5 * math.sin(x * 0.5 + 1))
        for y in range(h, 16):
            if px[x, y][3]:
                px[x, y] = (24, 40, 36, 255)
    px[3, 2] = px[12, 2] = (255, 255, 230, 255)               # two stars
    return outline(img)


# ------------------------------------------------------------------ marks
def from_draw(spec, name):
    """A tools/glyphs.py drawing, shaded at the bottom and re-outlined."""
    img = glyphs.draw(spec, name)
    px = img.load()
    for y in range(16):                                       # drop its own outline
        for x in range(16):
            if px[x, y] == WHITE and not spec.startswith(("dot_", "times", "arrow", "bar")):
                px[x, y] = (0, 0, 0, 0)
    if not spec.startswith(("dot_", "times", "arrow", "bar")):
        shade_bottom(img)
        img = outline(img)
    return img


def tiers(n, colour):
    img = canvas()
    d = ImageDraw.Draw(img)
    for i in range(3):                                        # bars 3 px wide, growing
        x0, top = 2 + i * 4, 10 - i * 3
        if i < n:
            d.rectangle((x0, top, x0 + 2, 13), fill=colour)
            d.line([(x0 + 2, top), (x0 + 2, 13)], fill=tuple(int(v * 0.72) for v in colour[:3]) + (255,))
        else:
            d.rectangle((x0, top, x0 + 2, 13), outline=(110, 110, 120, 255))
    return outline(img)


def animation():
    img = canvas()
    d = ImageDraw.Draw(img)
    d.rectangle((1, 3, 12, 13), fill=(52, 52, 60, 255))       # the film frame
    for y in (4, 7, 10, 12):
        d.point((2, y), fill=(220, 220, 220, 255))
        d.point((11, y), fill=(220, 220, 220, 255))
    d.rectangle((4, 5, 9, 11), fill=(120, 190, 240, 255))     # the picture
    d.rectangle((4, 9, 9, 11), fill=(80, 150, 90, 255))
    for x, y in ((13, 1), (13, 2), (13, 3), (12, 2), (14, 2)):  # a spark at the corner
        img.putpixel((x, y), (255, 220, 80, 255))
    return outline(img)


def build():
    out = {
        "bowl.half": bowl("half"), "bowl.full": bowl("full"),
        **{f"moon.{i}": moon(i) for i in range(8)},
        **{f"tide.{k}": tide(k) for k in ("high", "low", "slack")},
        "sky.meteor": meteor(), "sky.aurora": aurora(),
        "dot.full": from_draw("dot_full", "dot.full"), "dot.empty": from_draw("dot_empty", "dot.empty"),
        "mark.x": from_draw("times", "mark.x"), "mark.tick": from_draw("tick:40c040", "mark.tick"),
        "mark.cross": from_draw("cross:e03030", "mark.cross"), "mark.star": from_draw("star:f0c030", "mark.star"),
        **{f"arrow.{d}": from_draw(f"arrow_{d}", f"arrow.{d}") for d in ("left", "right", "up", "down")},
        "mark.sep": from_draw("bar", "mark.sep"),
        "tier.few": tiers(1, (160, 200, 224, 255)), "tier.some": tiers(2, (240, 192, 48, 255)),
        "tier.many": tiers(3, (240, 128, 48, 255)),
        "ui.animation": animation(),
    }
    for name, img in out.items():
        img.save(os.path.join(SRC, name + ".png"))
    return out


if __name__ == "__main__":
    print(f"wrote {len(build())} glyph pictures to tools/data/glyph_src")
