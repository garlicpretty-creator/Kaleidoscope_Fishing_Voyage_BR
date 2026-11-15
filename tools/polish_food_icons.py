"""Food icons: a light touch-up for a clearer outline and a bit of depth (1.4.0 playtest request).

usage: python tools/polish_food_icons.py            touch up every icon in the "foods" creative group
       python tools/polish_food_icons.py sheet OUT  also write a before / after review sheet

Works from the untouched originals in tools/data/food_icon_base/ (copied there on the first run), so running it
again gives the same result instead of stacking. Light comes from the top left, like vanilla item art:
  outline    pixels on the silhouette edge are darkened, more on the bottom / right (shadow) side
  highlight  the pixel just inside a top / left edge is brightened a little
  shade      the pixel just inside a bottom / right edge is darkened a little
Pixels that are already dark (an existing outline) are not outlined again; only their shadow side is deepened,
and the pixels just inside them get the highlight / shade.
"""
import json, os, shutil, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
BP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [BP]')
BASE = os.path.join(ROOT, 'tools', 'data', 'food_icon_base')
ITEMS = os.path.join(RP, 'textures', 'items')

DARK = 70                      # luminance below which a pixel already counts as outline
RIM_LIT, RIM_SHADOW = 0.80, 0.62   # rim brightness on the lit (top/left) and shadow (bottom/right) side
HIGHLIGHT, SHADE = 0.30, 0.20      # inner highlight (towards white) and inner shade (towards black)
OUTLINE_SHADOW = 0.72              # an existing dark outline on the shadow side gets this much darker


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def food_icons():
    cat = json.load(open(os.path.join(BP, 'item_catalog', 'crafting_item_catalog.json'), encoding='utf-8'))
    for g in cat['minecraft:crafting_items_catalog']['categories'][0]['groups']:
        if g['group_identifier']['name'].endswith('.foods'):
            return [(i if isinstance(i, str) else i['name']).split(':')[1] for i in g['items']]
    return []


def polish(im):
    im = im.convert('RGBA'); w, h = im.size
    src = im.load(); out = im.copy(); px = out.load()
    solid = lambda x, y: 0 <= x < w and 0 <= y < h and src[x, y][3] >= 128
    for y in range(h):
        for x in range(w):
            if not solid(x, y):
                continue
            r, g, b, a = src[x, y]
            up, left, down, right = solid(x, y - 1), solid(x - 1, y), solid(x, y + 1), solid(x + 1, y)
            if lum((r, g, b)) < DARK:
                if not down or not right:                                  # deepen the shadow side of an outline
                    px[x, y] = (round(r * OUTLINE_SHADOW), round(g * OUTLINE_SHADOW), round(b * OUTLINE_SHADOW), a)
                continue
            if not (up and left and down and right):                       # silhouette edge
                k = RIM_SHADOW if (not down or not right) else RIM_LIT
                px[x, y] = (round(r * k), round(g * k), round(b * k), a)
                continue
            edge = lambda xx, yy: not solid(xx, yy) or lum(src[xx, yy][:3]) < DARK
            lit = edge(x, y - 1) or edge(x - 1, y)                          # just inside a top / left edge
            shadow = edge(x, y + 1) or edge(x + 1, y)                       # just inside a bottom / right edge
            if lit and not shadow:
                px[x, y] = (round(r + (255 - r) * HIGHLIGHT), round(g + (255 - g) * HIGHLIGHT),
                            round(b + (255 - b) * HIGHLIGHT), a)
            elif shadow and not lit:
                px[x, y] = (round(r * (1 - SHADE)), round(g * (1 - SHADE)), round(b * (1 - SHADE)), a)
    return out


def main(argv):
    os.makedirs(BASE, exist_ok=True)
    names = food_icons()
    pairs = []
    for n in names:
        cur = os.path.join(ITEMS, f'kfv_{n}.png')
        base = os.path.join(BASE, f'kfv_{n}.png')
        if not os.path.exists(base):
            shutil.copy(cur, base)
        before = Image.open(base).convert('RGBA')
        after = polish(before)
        after.save(cur)
        pbr.refresh(cur)
        pairs.append((n, before, after))
    print(len(pairs), 'food icons touched up')
    if argv[:1] == ['sheet']:
        S = 6; cell = 16 * S
        cols = 8; rows = (len(pairs) + cols - 1) // cols
        sheet = Image.new('RGBA', (cols * (cell * 2 + 14), rows * (cell + 10)), (139, 139, 139, 255))
        for i, (n, a, b) in enumerate(pairs):
            x = (i % cols) * (cell * 2 + 14); y = (i // cols) * (cell + 10)
            sheet.alpha_composite(a.resize((cell, cell), Image.NEAREST), (x, y))
            sheet.alpha_composite(b.resize((cell, cell), Image.NEAREST), (x + cell + 2, y))
        sheet.save(argv[1])


if __name__ == '__main__':
    main(sys.argv[1:])
