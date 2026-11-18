"""1.6.0 glyph characters: the little pictures that stand in for text in forms and item lore.

Bedrock draws a private-use character U+XXYY from the resource pack's font/glyph_XX.png: a 16x16 grid of
cells, cell YY = row * 16 + column. This tool writes those sheets and scripts/data/glyphs.js from
tools/data/GLYPHS.json (docs/PLAN_1.6.0.md section 5).

  python tools/glyphs.py sync     add missing glyphs (new catches, dishes, ingredients, tackle) to GLYPHS.json
  python tools/glyphs.py build    sync, then write RP font/glyph_*.png and scripts/data/glyphs.js
  python tools/glyphs.py check    fail if GLYPHS.json is missing a glyph or a sheet / glyphs.js is out of date
  python tools/glyphs.py list     print the placeholder glyphs (drawn shapes still waiting for art)

build.py build / check / pack run build / check too.

GLYPHS.json
  "pages":  logical page -> hex page ("fish": "E1"). The only place the code points are decided: moving every
            glyph to other pages (another pack or vanilla uses the page) is a change here plus a rebuild.
  "glyphs": name -> {"page", "index", "src"}. Indices never move once given out (old lore in saved worlds
            keeps its characters); sync appends new names at the first free cell of their page.
  src:      "textures/..."        an RP texture (an item icon), scaled to 16x16
            "tools/data/..."      a picture kept in this repository (tools/data/glyph_src)
            "shadow:<src>"        the black silhouette of a picture (fish not caught yet)
            "draw:<shape>[:<rrggbb>]"  a PLACEHOLDER drawn here with Pillow, until art is made

Names: an item's glyph is named by its item id ("kaleidoscope_fishing:carp", "minecraft:egg",
"kaleidoscope_cookery:flour"); a fish's silhouette is "shadow.<item id>"; symbols are dotted words
("water.river", "time.night", "moon.3", "dot.full", "ui.gear"). See the report in docs/PLAN_1.6.0.md section 19.

Output is deterministic (same source, same bytes), like the rest of the pack.
"""
import hashlib, io, json, math, os, sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BP = os.path.join(ROOT, "Kaleidoscope Fishing Voyage [BP]")
RP = os.path.join(ROOT, "Kaleidoscope Fishing Voyage [RP]")
DATA = os.path.join(HERE, "data")
SPEC = os.path.join(DATA, "GLYPHS.json")
JS = os.path.join(BP, "scripts", "data", "glyphs.js")
FONT = os.path.join(RP, "font")
CELL, GRID = 16, 16                      # 16 px cells, 256 x 256 sheets (vanilla's size; larger sheets also work)
NS = "kaleidoscope_fishing"

DEFAULT_PAGES = {"fish": "E1", "symbols": "E2", "food": "E3", "food2": "E4"}


def load(name):
    return json.load(open(os.path.join(DATA, name), encoding="utf-8"))


# ------------------------------------------------------------------ drawing (placeholders)
def rgb(hexs, a=255):
    return (int(hexs[0:2], 16), int(hexs[2:4], 16), int(hexs[4:6], 16), a)


def hue_of(name):
    """A stable colour for a name (no randomness: same name, same colour)."""
    h = hashlib.sha1(name.encode("utf-8")).digest()
    return "%02x%02x%02x" % (80 + h[0] % 150, 80 + h[1] % 150, 80 + h[2] % 150)


def canvas():
    return Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))


def outline(img, colour=(255, 255, 255, 255)):
    """A 1 px white outline round everything drawn (the style of vanilla's controller glyphs)."""
    src = img.load()
    out = img.copy()
    o = out.load()
    for y in range(CELL):
        for x in range(CELL):
            if src[x, y][3]:
                continue
            if any(0 <= x + dx < CELL and 0 <= y + dy < CELL and src[x + dx, y + dy][3]
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                o[x, y] = colour
    return out


def d_fish(d, c):
    d.ellipse((2, 5, 11, 10), fill=c)
    d.polygon([(10, 7), (14, 4), (14, 11)], fill=c)
    d.point((4, 7), fill=(20, 20, 20, 255))


def d_tile(d, c):
    d.rounded_rectangle((1, 2, 14, 13), 3, fill=c)


def d_waves(d, c, ys=(6, 10)):
    for y in ys:
        for x in range(2, 14):
            d.point((x, y + (1 if (x // 2) % 2 else 0)), fill=c)


def d_sun(d, c, cx=7.5, cy=7.5, r=3.5, rays=True):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c)
    if rays:
        for a in range(8):
            t = a * math.pi / 4
            d.point((round(cx + math.cos(t) * (r + 2.5)), round(cy + math.sin(t) * (r + 2.5))), fill=c)


def d_moon_phase(img, phase):
    """Minecraft moon phases: 0 full, 1-3 waning (lit on the left), 4 new, 5-7 waxing (lit on the right)."""
    p = img.load()
    psi = (phase if phase <= 4 else 8 - phase) * math.pi / 4
    right = phase >= 5
    for y in range(CELL):
        for x in range(CELL):
            nx, ny = (x - 7.5) / 6.0, (y - 7.5) / 6.0
            if nx * nx + ny * ny > 1:
                continue
            w = math.sqrt(max(0.0, 1 - ny * ny))
            sx = nx if right or phase == 0 else -nx
            lit = sx > -w * math.cos(psi) + 1e-9
            p[x, y] = (240, 230, 160, 255) if lit else (60, 60, 75, 255)


def d_cloud(d, c):
    d.ellipse((2, 4, 9, 10), fill=c)
    d.ellipse((6, 2, 13, 9), fill=c)
    d.rectangle((3, 7, 13, 10), fill=c)


def d_arrow(d, c, direction):
    pts = {"up": [(7.5, 2), (13, 8), (10, 8), (10, 13), (5, 13), (5, 8), (2, 8)]}["up"]
    turn = {"up": 0, "right": 1, "down": 2, "left": 3}[direction]
    for _ in range(turn):
        pts = [(15 - y, x) for x, y in pts]
    d.polygon(pts, fill=c)


def d_bowl(d, level):
    if level > 0:
        top = 8 if level == 1 else 5
        d.ellipse((3, top, 12, 10), fill=rgb("e0b040"))
    d.chord((1, 4, 14, 14), 0, 180, fill=rgb("8a5a2b"))


def d_gear(img):
    d = ImageDraw.Draw(img)
    c = rgb("9a9aa0")
    for a in range(8):
        t = a * math.pi / 4
        x, y = 7.5 + math.cos(t) * 5.5, 7.5 + math.sin(t) * 5.5
        d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=c)
    d.ellipse((3, 3, 12, 12), fill=c)
    d.ellipse((6, 6, 9, 9), fill=(0, 0, 0, 0))


def d_pot(d, c, steam=False, handle=False):
    d.rectangle((3, 6, 12, 13), fill=c)
    d.rectangle((2, 5, 13, 6), fill=c)
    if handle:
        d.rectangle((0, 7, 2, 8), fill=c)
        d.rectangle((13, 7, 15, 8), fill=c)
    if steam:
        for x in (5, 8, 11):
            d.line((x, 1, x - 1, 3), fill=rgb("e8e8e8"))


def draw(spec, name):
    """Draw a placeholder glyph. spec = "<shape>[:<rrggbb>]"."""
    shape, _, col = spec.partition(":")
    c = rgb(col) if col else rgb(hue_of(name))
    img = canvas()
    d = ImageDraw.Draw(img)
    white = rgb("ffffff")
    ring = True                                       # most placeholders get the white outline
    if shape == "fish":
        d_fish(d, c)
    elif shape == "fish_unknown":
        d_fish(d, rgb("303038"))
    elif shape == "puffer":
        d.ellipse((3, 3, 12, 12), fill=c)
        for x, y in ((7, 1), (7, 14), (1, 7), (14, 7), (3, 3), (12, 3), (3, 12), (12, 12)):
            d.point((x, y), fill=c)
    elif shape == "water":
        d_tile(d, c)
        d_waves(d, white)
    elif shape == "ice_water":
        d_tile(d, c)
        d.rectangle((2, 3, 13, 6), fill=rgb("f0f8ff"))
        d_waves(d, white, (10,))
    elif shape == "lava":
        d_tile(d, c)
        d_waves(d, rgb("ffd040"))
    elif shape == "void":
        d_tile(d, c)
        for x, y in ((4, 5), (10, 4), (7, 9), (12, 11), (3, 11)):
            d.point((x, y), fill=rgb("c080ff"))
    elif shape == "meteor":
        d_tile(d, rgb("202040"))
        d.line((3, 4, 10, 11), fill=rgb("ffb040"))
        d.ellipse((9, 9, 12, 12), fill=rgb("fff0a0"))
    elif shape == "sun":
        d_sun(d, c)
    elif shape == "dawn":
        d_sun(d, c, cy=10, r=3.5)
        d.rectangle((0, 11, 15, 15), fill=(0, 0, 0, 0))
        d.line((1, 11, 14, 11), fill=white)
        d.line((7, 2, 7, 4), fill=c)
    elif shape == "dusk":
        d_sun(d, c, cy=10, r=3.5)
        d.rectangle((0, 11, 15, 15), fill=(0, 0, 0, 0))
        d.line((1, 11, 14, 11), fill=white)
        d.line((7, 4, 7, 2), fill=rgb("8060c0"))
    elif shape == "crescent":
        d.ellipse((2, 2, 13, 13), fill=c)
        d.ellipse((5, 1, 15, 11), fill=(0, 0, 0, 0))
    elif shape == "sun_moon":
        d.pieslice((1, 1, 14, 14), 90, 270, fill=rgb("f0c030"))
        d.pieslice((1, 1, 14, 14), 270, 90, fill=rgb("c8d0f0"))
    elif shape == "rain":
        d_cloud(d, rgb("a0a8b0"))
        for x in (4, 8, 12):
            d.line((x, 11, x - 1, 13), fill=rgb("4080ff"))
    elif shape == "thunder":
        d_cloud(d, rgb("606070"))
        d.polygon([(8, 8), (5, 12), (7, 12), (6, 15), (10, 10), (8, 10), (9, 8)], fill=rgb("ffe040"))
    elif shape in ("tide_high", "tide_low", "tide_slack"):
        if shape == "tide_slack":
            d.rectangle((3, 5, 12, 6), fill=c)
        else:
            d_arrow(d, c, "up" if shape == "tide_high" else "down")
        d.rectangle((1, 10, 14, 13), fill=rgb("3070d0"))      # the water line in front of the arrow
        d_waves(d, white, (10,))
    elif shape.startswith("moon"):
        d_moon_phase(img, int(shape[4:]))
    elif shape == "aurora":
        for i, col2 in enumerate(("40e090", "40c0e0", "a060e0")):
            for x in range(1, 15):
                d.point((x, 4 + i * 3 + round(math.sin(x / 2.0) * 1.5)), fill=rgb(col2))
                d.point((x, 5 + i * 3 + round(math.sin(x / 2.0) * 1.5)), fill=rgb(col2))
    elif shape == "wok":
        d.chord((1, 2, 12, 13), 0, 180, fill=rgb("303030"))
        d.rectangle((11, 7, 15, 8), fill=rgb("7a4a20"))
    elif shape == "stockpot":
        d_pot(d, rgb("9098a0"), steam=True, handle=True)
    elif shape == "steamer":
        d.rectangle((2, 4, 13, 13), fill=rgb("c8a060"))
        for y in (6, 9, 12):
            d.line((2, y, 13, y), fill=rgb("8a6a30"))
    elif shape == "teapot":
        d.ellipse((3, 5, 12, 13), fill=c)
        d.polygon([(12, 8), (15, 5), (15, 7), (12, 11)], fill=c)
        d.rectangle((6, 3, 9, 5), fill=c)
    elif shape == "crafting":
        d.rectangle((2, 2, 13, 13), fill=rgb("a07040"))
        for v in (5, 9):
            d.line((v, 2, v, 13), fill=rgb("5a3a18"))
            d.line((2, v, 13, v), fill=rgb("5a3a18"))
    elif shape == "furnace":
        d.rectangle((2, 2, 13, 13), fill=rgb("808080"))
        d.rectangle((5, 8, 10, 12), fill=rgb("202020"))
        d.rectangle((6, 10, 9, 12), fill=rgb("ff9020"))
    elif shape == "campfire":
        d.line((2, 13, 13, 10), fill=rgb("6a4020"), width=2)
        d.line((2, 10, 13, 13), fill=rgb("6a4020"), width=2)
        d.polygon([(7.5, 2), (11, 9), (4, 9)], fill=rgb("ff9020"))
        d.polygon([(7.5, 5), (9.5, 9), (5.5, 9)], fill=rgb("ffe060"))
    elif shape == "jar":
        d.ellipse((2, 4, 13, 14), fill=c)
        d.rectangle((5, 2, 10, 5), fill=c)
    elif shape == "tub":
        d.polygon([(1, 5), (14, 5), (12, 13), (3, 13)], fill=rgb("a07040"))
        d.rectangle((2, 5, 13, 7), fill=rgb("4080d0"))
        d.line((2, 10, 13, 10), fill=rgb("505050"))
    elif shape == "salt_pan":
        d.rectangle((1, 8, 14, 12), fill=rgb("b06040"))
        d.rectangle((2, 8, 13, 9), fill=rgb("f4f4f4"))
    elif shape == "tray":
        d.ellipse((1, 6, 14, 12), fill=rgb("c8a060"))
        d.ellipse((3, 7, 12, 11), fill=rgb("e0c080"))
    elif shape == "feeder":
        d.rectangle((6, 6, 9, 14), fill=rgb("8a5a2b"))
        d.chord((2, 1, 13, 9), 0, 180, fill=rgb("a07040"))
        d.ellipse((4, 3, 11, 6), fill=rgb("e0b040"))
    elif shape == "dot_full":
        d.ellipse((4, 4, 11, 11), fill=white)
        ring = False
    elif shape == "dot_empty":
        d.ellipse((4, 4, 11, 11), outline=white)
        ring = False
    elif shape == "times":
        d.line((4, 4, 11, 11), fill=white, width=2)
        d.line((4, 11, 11, 4), fill=white, width=2)
        ring = False
    elif shape == "tick":
        d.line((2, 8, 6, 12), fill=c, width=2)
        d.line((6, 12, 13, 3), fill=c, width=2)
    elif shape == "cross":
        d.line((3, 3, 12, 12), fill=c, width=2)
        d.line((3, 12, 12, 3), fill=c, width=2)
    elif shape.startswith("arrow_"):
        d_arrow(d, white, shape[6:])
        ring = False
    elif shape.startswith("bowl_"):
        d_bowl(d, {"full": 2, "half": 1, "empty": 0}[shape[5:]])
    elif shape.startswith("tier_"):                  # 1.6.0: how many of a fish the creel holds (1, 2 or 3 bars)
        for i in range(int(shape[5:])):
            d.rectangle((2 + i * 4, 12 - i * 3 - 3, 4 + i * 4, 13), fill=c)
    elif shape == "star":
        pts = [(7.5 + math.cos(-math.pi / 2 + i * math.pi / 5) * (6.5 if i % 2 == 0 else 2.8),
                7.5 + math.sin(-math.pi / 2 + i * math.pi / 5) * (6.5 if i % 2 == 0 else 2.8)) for i in range(10)]
        d.polygon(pts, fill=c)
    elif shape == "gear":
        d_gear(img)
    elif shape == "bar":                              # a plain vertical divider
        d.rectangle((7, 1, 8, 14), fill=white)
        ring = False
    elif shape == "anim":                             # a block with motion lines: "things move"
        d.rectangle((6, 4, 13, 11), fill=rgb("a07040"))
        for y in (5, 8, 11):
            d.line((1, y, 4, y), fill=white)
    elif shape == "recipes":
        d_pot(d, rgb("707880"), steam=True, handle=True)
    elif shape == "merchant":
        d.ellipse((4, 6, 11, 13), fill=rgb("e0b090"))
        d.polygon([(7.5, 1), (15, 7), (0, 7)], fill=rgb("d8c070"))
    elif shape == "item":                             # a neutral "something" for an ingredient without art
        d.rounded_rectangle((3, 3, 12, 12), 3, fill=c)
        d.point((5, 5), fill=rgb("ffffff", 160))
    # simple shapes for vanilla / Cookery ingredients whose icons are not in this repository
    elif shape == "ball":
        d.ellipse((3, 3, 12, 12), fill=c)
    elif shape == "egg":
        d.ellipse((4, 2, 11, 13), fill=c)
    elif shape == "oval":
        d.ellipse((2, 4, 13, 11), fill=c)
    elif shape == "carrot":
        d.polygon([(3, 12), (12, 3), (9, 2), (2, 9)], fill=c)
        d.line((11, 2, 14, 0), fill=rgb("40a040"))
    elif shape == "stick":
        d.line((3, 13, 12, 2), fill=c, width=3)
    elif shape == "kelp":
        for y in range(1, 15):
            d.point((7 + round(math.sin(y / 2.0) * 2), y), fill=c)
            d.point((8 + round(math.sin(y / 2.0) * 2), y), fill=c)
    elif shape == "cap":
        d.chord((2, 2, 13, 11), 180, 360, fill=c)
        d.rectangle((6, 7, 9, 13), fill=rgb("e8e0d0"))
    elif shape == "block":
        d.rectangle((2, 2, 13, 13), fill=c)
    elif shape == "slab":
        d.rectangle((1, 8, 14, 13), fill=c)
    elif shape == "bowl":
        d.chord((1, 3, 14, 13), 0, 180, fill=c)
    elif shape == "rice_bowl":
        d.ellipse((3, 3, 12, 9), fill=rgb("f8f8f0"))
        d.chord((1, 3, 14, 13), 0, 180, fill=c)
    elif shape == "cauldron":
        d_pot(d, c)
    elif shape == "sack":
        d.ellipse((2, 5, 13, 14), fill=c)
        d.rectangle((6, 2, 9, 6), fill=c)
    elif shape == "bottle":
        d.rectangle((4, 6, 11, 14), fill=c)
        d.rectangle((6, 2, 9, 6), fill=c)
    elif shape == "chili":
        d.line((3, 12, 11, 4), fill=c, width=3)
        d.line((11, 4, 13, 2), fill=rgb("40a040"))
    elif shape == "leaf":
        d.ellipse((2, 3, 13, 12), fill=c)
        d.line((3, 12, 12, 3), fill=rgb("206020"))
    elif shape == "grains":
        for x, y in ((4, 4), (8, 3), (11, 6), (5, 8), (9, 9), (4, 12), (11, 12), (7, 6)):
            d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=c)
    elif shape == "noodles":
        for y in (4, 7, 10):
            d_waves(d, c, (y,))
    elif shape == "fruit":
        d.ellipse((3, 3, 12, 12), fill=c)
        d.point((7, 2), fill=rgb("40a040"))
    else:
        raise SystemExit(f"glyph {name}: unknown placeholder shape {shape!r}")
    return outline(img) if ring else img


# ------------------------------------------------------------------ pictures from textures
def picture(path):
    p = path if os.path.isabs(path) else os.path.join(ROOT, path) if path.startswith("tools/") else os.path.join(RP, path)
    if not p.endswith(".png"):
        p += ".png"
    if not os.path.exists(p):
        raise SystemExit(f"glyph source missing: {path}")
    img = Image.open(p).convert("RGBA")
    if img.size != (CELL, CELL):
        w, h = img.size
        s = max(w, h)
        sq = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        sq.paste(img, ((s - w) // 2, (s - h) // 2))
        img = sq.resize((CELL, CELL), Image.BOX)
        px = img.load()
        for y in range(CELL):
            for x in range(CELL):
                r, g, b, a = px[x, y]
                px[x, y] = (r, g, b, 255) if a >= 128 else (0, 0, 0, 0)
    return img


def shadow(img):
    out = canvas()
    s, o = img.load(), out.load()
    for y in range(CELL):
        for x in range(CELL):
            if s[x, y][3] >= 128:
                o[x, y] = (34, 34, 40, 255)
    return outline(out, (150, 150, 160, 255))         # a grey rim so the shadow shows on dark and light panels


def render_cell(name, src):
    if src.startswith("draw:"):
        return draw(src[5:], name)
    if src.startswith("shadow:"):
        return shadow(picture(src[7:]))
    return picture(src)


# ------------------------------------------------------------------ what needs a glyph
def item_icons():
    """item id -> RP texture path, from the BP item files and item_texture.json."""
    tex = json.load(open(os.path.join(RP, "textures", "item_texture.json"), encoding="utf-8"))["texture_data"]
    out = {}
    for d, _, files in os.walk(os.path.join(BP, "items")):
        for f in sorted(files):
            if not f.endswith(".json"):
                continue
            it = json.load(open(os.path.join(d, f), encoding="utf-8-sig"))["minecraft:item"]
            icon = it["components"].get("minecraft:icon")
            icon = icon if isinstance(icon, str) else (icon or {}).get("texture")
            t = tex.get(icon, {}).get("textures") if icon else None
            if isinstance(t, list):
                t = t[0]
            if isinstance(t, str):
                out[it["description"]["identifier"]] = t
    return out


# Vanilla and Cookery items have no icon in this repository: a drawn placeholder for each.
FOREIGN = {
    "minecraft:cod": "fish:c8a070", "minecraft:salmon": "fish:c05040", "minecraft:tropical_fish": "fish:f08030",
    "minecraft:pufferfish": "puffer:e8c030", "minecraft:cooked_salmon": "fish:a05a30",
    "minecraft:bamboo": "stick:70b040", "minecraft:bowl": "bowl:8a5a2b", "minecraft:brown_mushroom": "cap:9a6a40",
    "minecraft:campfire": "campfire", "minecraft:carrot": "carrot:f08020", "minecraft:cauldron": "cauldron:505058",
    "minecraft:chorus_fruit": "fruit:9060a0", "minecraft:crimson_fungus": "cap:b02020", "minecraft:dried_kelp": "kelp:306030",
    "minecraft:egg": "egg:f0e0c0", "minecraft:ice": "block:a0c8f8", "minecraft:kelp": "kelp:40a040",
    "minecraft:oak_slab": "slab:b08850", "minecraft:potato": "oval:c09050", "minecraft:sugar": "grains:f8f8f8",
    "kaleidoscope_cookery:cooked_rice": "rice_bowl:8a5a2b", "kaleidoscope_cookery:flour": "sack:f0ece0",
    "kaleidoscope_cookery:green_chili": "chili:40a030", "kaleidoscope_cookery:red_chili": "chili:d02020",
    "kaleidoscope_cookery:lettuce": "leaf:70c040", "kaleidoscope_cookery:oil": "bottle:e8c840",
    "kaleidoscope_cookery:raw_noodles": "noodles:f0d070", "kaleidoscope_cookery:rice": "grains:f4f0e0",
    "kaleidoscope_cookery:tomato": "ball:e03020", "kaleidoscope_cookery:caterpillar": "kelp:90c040",
    "minecraft:rotten_flesh": "oval:8a6a40",
}
GLYPH_SRC = os.path.join(DATA, "glyph_src")


def local_src(name):
    """The picture kept in tools/data/glyph_src for a glyph, or None: an item id "ns:item" is
    glyph_src/ns/item.png, any other name (a symbol) is glyph_src/<name>.png ("water.river.png")."""
    ns, colon, n = name.partition(":")
    p = os.path.join(GLYPH_SRC, ns, n + ".png") if colon else os.path.join(GLYPH_SRC, name + ".png")
    return os.path.relpath(p, ROOT).replace(os.sep, "/") if os.path.exists(p) else None

WATER_DRAW = {
    "river": "water:4a90e0", "lake": "water:3a70c0", "swamp": "water:607040", "ocean": "water:2a60c0",
    "warm_ocean": "water:30b0c0", "cold_ocean": "water:305090", "deep_ocean": "water:203070", "beach": "water:d8c080",
    "estuary": "water:508090", "mangrove": "water:6a7a40", "ice": "ice_water:80a8e0", "cave": "water:606068",
    "lava": "lava:e05010", "mushroom": "water:a05080", "cherry": "water:f0a0c0", "deep_dark": "water:103038",
    "end_pond": "water:a090c0", "void": "void:181020",
}

SYMBOLS = [
    ("item.unknown", "draw:item:808088"),
    ("time.day", "draw:sun:f0c030"), ("time.night", "draw:crescent:e0e0a0"), ("time.dawn", "draw:dawn:f09040"),
    ("time.dusk", "draw:dusk:e06040"), ("time.any", "draw:sun_moon"),
    ("weather.clear", "draw:sun:ffd860"), ("weather.rain", "draw:rain"), ("weather.thunder", "draw:thunder"),
    ("tide.high", "draw:tide_high:ffffff"), ("tide.low", "draw:tide_low:ffffff"), ("tide.slack", "draw:tide_slack:ffffff"),
    *[(f"moon.{i}", f"draw:moon{i}") for i in range(8)],
    ("sky.meteor", "draw:meteor"), ("sky.aurora", "draw:aurora"),
    ("station.wok", "draw:wok"), ("station.stockpot", "draw:stockpot"), ("station.steamer", "draw:steamer"),
    ("station.teapot", "draw:teapot:a06040"), ("station.crafting", "draw:crafting"), ("station.furnace", "draw:furnace"),
    ("station.campfire", "draw:campfire"), ("station.cleaning_board", "textures/items/kfv_fish_cleaning_board"),
    ("station.drying_rack", "textures/items/kfv_drying_rack"), ("station.fish_sauce_jar", "draw:jar:a06030"),
    ("station.wooden_tub", "draw:tub"), ("station.salt_pan", "draw:salt_pan"), ("station.bamboo_tray", "draw:tray"),
    ("station.shrimp_trap", "textures/items/kfv_shrimp_trap"), ("station.pond_feeder", "draw:feeder"),
    ("station.fish_tank", "textures/items/kfv_fish_tank"), ("station.tackle_rack", "textures/items/kfv_tackle_rack"),
    ("dot.full", "draw:dot_full"), ("dot.empty", "draw:dot_empty"), ("mark.x", "draw:times"),
    ("mark.tick", "draw:tick:40c040"), ("mark.cross", "draw:cross:e03030"), ("mark.star", "draw:star:f0c030"),
    ("arrow.left", "draw:arrow_left"), ("arrow.right", "draw:arrow_right"), ("arrow.up", "draw:arrow_up"),
    ("arrow.down", "draw:arrow_down"),
    ("bowl.full", "draw:bowl_full"), ("bowl.half", "draw:bowl_half"), ("bowl.empty", "draw:bowl_empty"),
    ("ui.gear", "draw:gear"), ("ui.recipes", "draw:recipes"), ("ui.tide_clock", "textures/items/kfv_tide_clock"),
    ("ui.merchant", "draw:merchant"), ("ui.basket", "textures/items/kfv_fish_basket"),
    ("ui.recipe_scrap", "textures/items/kfv_recipe_scrap"), ("ui.journal", "textures/items/kfv_angler_journal"),
    # 1.6.0 creel picker (plan section 8): how many of that fish, in place of the plan's three button backgrounds
    ("tier.few", "draw:tier_1:a0c8e0"), ("tier.some", "draw:tier_2:f0c030"), ("tier.many", "draw:tier_3:f08030"),
    # 1.6.0 step 6 (journal picture book): the bar between a recipe's station and its ingredients, the settings
    # page's animation switch (section 12.3)
    ("mark.sep", "draw:bar"), ("ui.animation", "draw:anim"),
]

# RECIPE_HINTS "method" -> station glyph (the journal's recipe line starts with it)
METHOD_STATION = {"wok": "station.wok", "stockpot": "station.stockpot", "steamer": "station.steamer",
                  "teapot": "station.teapot", "crafting": "station.crafting", "furnace": "station.furnace"}


def id_of_key(key):
    """A RECIPE_HINTS ingredient / name key -> item id (the glyph name)."""
    if key.startswith(f"{NS}.name."):
        return f"{NS}:{key[len(NS) + 6:]}"
    if key.startswith(f"{NS}.ing."):
        ns, _, item = key[len(NS) + 5:].partition(".")
        return f"{ns}:{item}"
    return key


def wanted():
    """[(page, name, src)] in a fixed order: everything that should have a glyph."""
    icons = item_icons()
    catches = [c["id"] for c in load("CATCHES.json")]

    def src_of(item):
        if item in icons:
            return icons[item]
        return local_src(item) or ("draw:" + FOREIGN[item] if item in FOREIGN else "draw:item")

    def sym(name, src):
        """A symbol's drawn placeholder gives way to its picture in glyph_src/<name>.png."""
        return (local_src(name) or src) if src.startswith("draw:") else src

    out = [("fish", "fish.unknown", sym("fish.unknown", "draw:fish_unknown"))]
    out += [("fish", c, src_of(c)) for c in catches]
    out += [("fish", f"shadow.{c}", "shadow:" + src_of(c)) for c in catches if not src_of(c).startswith("draw:")]
    out += [("fish", f"shadow.{c}", "draw:fish_unknown") for c in catches if src_of(c).startswith("draw:")]
    out += [("fish", b["id"], src_of(b["id"])) for b in load("BASKET_ITEMS.json")]   # 1.6.0: all the creel holds
    out += [("symbols", f"water.{w}", sym(f"water.{w}", "draw:" + s)) for w, s in WATER_DRAW.items()]
    out += [("symbols", n, sym(n, s)) for n, s in SYMBOLS]
    tackle = list(load("PARTS.json")) + list(load("RODS.json"))
    baits = []
    for c in load("CATCHES.json"):
        baits += list((c.get("bait") or {}).keys())
        if (c.get("req") or {}).get("bait"):
            baits.append(c["req"]["bait"])
    baits += load("TRAP_BAITS.json")
    for b in tackle + baits:
        if b not in catches:
            out.append(("symbols", b, src_of(b)))
    hints = load("RECIPE_HINTS.json")
    for h in hints:
        out.append(("food", h["id"], src_of(h["id"])))
    for h in hints:
        for key, _ in h["ingredients"]:
            i = id_of_key(key)
            if i not in catches:
                out.append(("food", i, src_of(i)))
    seen, uniq = set(), []
    for page, name, src in out:
        if name not in seen:
            seen.add(name)
            uniq.append((page, name, src))
    return uniq


# ------------------------------------------------------------------ spec
def read_spec():
    if not os.path.exists(SPEC):
        return {"pages": dict(DEFAULT_PAGES), "glyphs": {}}
    return json.load(open(SPEC, encoding="utf-8"))


def synced(spec):
    """The spec with every wanted glyph present (existing entries keep their cell and source)."""
    spec = {"pages": dict(spec.get("pages") or DEFAULT_PAGES), "glyphs": dict(spec.get("glyphs") or {})}
    used = {}
    for n, g in spec["glyphs"].items():
        used.setdefault(g["page"], set()).add(g["index"])
    overflow = {"food": "food2"}
    for page, name, src in wanted():
        if name in spec["glyphs"]:
            g = spec["glyphs"][name]
            # a placeholder whose art has arrived: the new picture, in the same cell (indices never move)
            if g["src"].startswith("draw:") and not src.startswith("draw:"):
                spec["glyphs"][name] = {**g, "src": src}
            continue
        p = page
        while len(used.get(p, ())) >= GRID * GRID:
            if p not in overflow:
                raise SystemExit(f"glyph page {p} is full")
            p = overflow[p]
        free = next(i for i in range(GRID * GRID) if i not in used.setdefault(p, set()))
        used[p].add(free)
        spec["glyphs"][name] = {"page": p, "index": free, "src": src}
    return spec


def dump_spec(spec):
    head = ['{', '  "_doc": "1.6.0 glyph characters: see tools/glyphs.py. Indices never move; edit src to change a picture, pages to move every glyph.",',
            '  "pages": ' + json.dumps(spec["pages"]) + ',', '  "glyphs": {']
    rows = sorted(spec["glyphs"].items(), key=lambda kv: (list(spec["pages"]).index(kv[1]["page"]), kv[1]["index"]))
    body = [f'    {json.dumps(n, ensure_ascii=False)}: {json.dumps(g, ensure_ascii=False)}' for n, g in rows]
    return "\n".join(head + [",\n".join(body), "  }", "}"]) + "\n"


def validate(spec):
    errors = []
    pages = spec["pages"]
    hexes = list(pages.values())
    if len(set(hexes)) != len(hexes):
        errors.append("two logical pages share a hex page")
    cells = {}
    for n, g in spec["glyphs"].items():
        if g["page"] not in pages:
            errors.append(f"{n}: unknown page {g['page']}")
        if not (0 <= g["index"] < GRID * GRID):
            errors.append(f"{n}: index {g['index']} out of range")
        k = (g["page"], g["index"])
        if k in cells:
            errors.append(f"{n} and {cells[k]} share a cell")
        cells[k] = n
    return errors


def char(spec, g):
    return chr(int(spec["pages"][g["page"]], 16) * 256 + g["index"])


# ------------------------------------------------------------------ outputs
def sheets(spec):
    """hex page -> PNG bytes (only pages with glyphs)."""
    imgs = {}
    for n, g in sorted(spec["glyphs"].items()):
        hexp = spec["pages"][g["page"]]
        sheet = imgs.setdefault(hexp, Image.new("RGBA", (CELL * GRID, CELL * GRID), (0, 0, 0, 0)))
        sheet.paste(render_cell(n, g["src"]), ((g["index"] % GRID) * CELL, (g["index"] // GRID) * CELL))
    out = {}
    for hexp, img in sorted(imgs.items()):
        b = io.BytesIO()
        img.save(b, "PNG", optimize=False, compress_level=9)
        out[hexp] = (b.getvalue(), img.tobytes())
    return out


JS_HELPERS = r'''
/** Whether a glyph of that name exists. */
export const hasGlyph = name => Object.prototype.hasOwnProperty.call(G, name);
/** The character of a glyph; an unknown name gives the fallback glyph ("fish.unknown" unless told otherwise). */
export function glyph(name, fallback = UNKNOWN_FISH) {
  if (hasGlyph(name)) return G[name];
  return fallback && hasGlyph(fallback) ? G[fallback] : "";
}
/** An item id, or a RECIPE_HINTS key ("kaleidoscope_fishing.name.oyster", "kaleidoscope_fishing.ing.minecraft.egg"), as an item id. */
export function idOfKey(key) {
  if (typeof key !== "string") return "";
  if (key.startsWith(`${NS}.name.`)) return `${NS}:${key.slice(NS.length + 6)}`;
  if (key.startsWith(`${NS}.ing.`)) { const r = key.slice(NS.length + 5); const i = r.indexOf("."); return i < 0 ? r : `${r.slice(0, i)}:${r.slice(i + 1)}`; }
  return key;
}
const canon = id => FISH_ALIAS[id] ?? id;
/** A fish's picture (another pack's fish, or an unknown id: the generic fish). */
export const fishGlyph = id => glyph(canon(id), UNKNOWN_FISH);
/** A fish's black silhouette, for one not caught yet (unknown: the generic fish shadow). */
export const shadowGlyph = id => glyph(`shadow.${canon(id)}`, UNKNOWN_FISH);
/** Any item (or RECIPE_HINTS key): its picture, else the neutral "item.unknown". */
export const itemGlyph = (idOrKey, fallback = UNKNOWN_ITEM) => glyph(canon(idOfKey(idOrKey)), fallback);
/** The station glyph for a RECIPE_HINTS method ("wok", "stockpot", ...). */
export const stationGlyph = method => glyph(`station.${method}`, UNKNOWN_ITEM);
/** n filled dots then (max - n) empty ones: dots(3, 5) = ●●●○○. */
export function dots(n, max = 5) {
  const m = Math.max(0, Math.floor(Number(max) || 0)), k = Math.max(0, Math.min(m, Math.floor(Number(n) || 0)));
  return G["dot.full"].repeat(k) + G["dot.empty"].repeat(m - k);
}
'''


def js(spec):
    rows = sorted(spec["glyphs"].items(), key=lambda kv: (list(spec["pages"]).index(kv[1]["page"]), kv[1]["index"]))
    lines = [
        "// AUTO-GENERATED by tools/glyphs.py from tools/data/GLYPHS.json. Do not edit by hand.",
        "// 1.6.0 glyph characters (docs/PLAN_1.6.0.md section 5): each is one private-use character that the resource",
        "// pack's font/glyph_XX.png draws as a 16x16 picture. Scripts take characters by name, never by code point.",
        'import { FISH_ALIAS } from "./generated.js";',
        "",
        f'const NS = "{NS}";',
        "/** Logical page -> hex page of font/glyph_XX.png. */",
        "export const PAGES = " + json.dumps(spec["pages"]) + ";",
        'export const UNKNOWN_FISH = "fish.unknown";',
        'export const UNKNOWN_ITEM = "item.unknown";',
        "/** Glyph name -> its character. */",
        "export const G = {",
    ]
    for n, g in rows:
        lines.append(f'  {json.dumps(n)}: "\\u{ord(char(spec, g)):04X}",')
    lines.append("};")
    lines.append("/** Glyphs that are still drawn placeholders, waiting for art. */")
    lines.append("export const PLACEHOLDERS = " + json.dumps(sorted(n for n, g in spec["glyphs"].items() if g["src"].startswith("draw:"))) + ";")
    return "\n".join(lines) + "\n" + JS_HELPERS


# ------------------------------------------------------------------ commands
def sync(write=True):
    spec = read_spec()
    new = synced(spec)
    added = sorted(set(new["glyphs"]) - set(spec["glyphs"]))
    if write and (added or not os.path.exists(SPEC) or dump_spec(new) != open(SPEC, encoding="utf-8").read()):
        with open(SPEC, "w", encoding="utf-8", newline="\n") as f:
            f.write(dump_spec(new))
    return new, added


def build():
    spec, added = sync()
    errs = validate(spec)
    if errs:
        raise SystemExit("GLYPHS.json: " + "; ".join(errs))
    os.makedirs(FONT, exist_ok=True)
    for hexp, (png, _) in sheets(spec).items():
        with open(os.path.join(FONT, f"glyph_{hexp}.png"), "wb") as f:
            f.write(png)
    with open(JS, "w", encoding="utf-8", newline="\n") as f:
        f.write(js(spec))
    print(f"wrote {len(spec['glyphs'])} glyphs ({len(added)} new) -> font/glyph_*.png, scripts/data/glyphs.js")


def check():
    spec = read_spec()
    problems = validate(spec)
    new, added = sync(write=False)
    if added:
        problems.append(f"GLYPHS.json lacks {len(added)} glyph(s) (first: {', '.join(added[:5])}): run  python tools/build.py build")
    art = sorted(n for n in spec["glyphs"] if n in new["glyphs"] and new["glyphs"][n]["src"] != spec["glyphs"][n]["src"])
    if art:
        problems.append(f"glyph_src has art for {len(art)} placeholder(s) (first: {', '.join(art[:5])}): run  python tools/build.py build")
    for hexp, (_, pixels) in sheets(spec).items():
        p = os.path.join(FONT, f"glyph_{hexp}.png")
        if not os.path.exists(p) or Image.open(p).convert("RGBA").tobytes() != pixels:
            problems.append(f"font/glyph_{hexp}.png is out of date")
    expected = {f"glyph_{h}.png" for h in sheets(spec)}
    stray = sorted(f for f in (os.listdir(FONT) if os.path.isdir(FONT) else []) if f.startswith("glyph_") and f not in expected)
    if stray:
        problems.append(f"font/ has sheets no glyph uses: {', '.join(stray)}")
    if not os.path.exists(JS) or open(JS, encoding="utf-8").read() != js(spec):
        problems.append("scripts/data/glyphs.js is out of date")
    if problems:
        raise SystemExit("glyphs: " + "; ".join(problems))
    print(f"glyphs match tools/data/GLYPHS.json ({len(spec['glyphs'])} glyphs)")


def placeholders():
    spec = read_spec()
    for n, g in sorted(spec["glyphs"].items(), key=lambda kv: (kv[1]["page"], kv[1]["index"])):
        if g["src"].startswith("draw:"):
            print(f"{spec['pages'][g['page']]}{g['index']:02X}  {n}  ({g['src']})")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    {"sync": lambda: print("added:", ", ".join(sync()[1]) or "nothing"), "build": build, "check": check,
     "list": placeholders}[cmd]()
