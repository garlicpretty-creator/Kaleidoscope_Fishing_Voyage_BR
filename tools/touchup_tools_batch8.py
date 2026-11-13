"""Hand touch-ups for the eighth AI batch (2026-11-14: rods, hooks, lines, bobbers, baits, keepsakes).

live_shrimp  the source is a pale grey shrimp that fades into the inventory slot; stronger contrast and
             a little more colour so the body, legs and tail read.
bamboo_fishing_rod  the fishing line came out as broken dots; joined into one line with the red bobber and a hook.
bamboo_bobber       two darker bamboo nodes across the body so it reads as bamboo, not a leaf.
Safe to run again: it always starts from the untouched copy (<name>.orig.png).
"""
import os, shutil, colorsys
from PIL import Image

STAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     'icon_preview', 'AI轉換結果')


def fresh(name):
    p = os.path.join(STAGE, f'{name}.png'); o = os.path.join(STAGE, f'{name}.orig.png')
    if not os.path.exists(o):
        shutil.copy(p, o)
    return Image.open(o).convert('RGBA'), p


def hexc(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def punch(im, contrast, sat, pink=0.0):
    cols = [im.getpixel((x, y)) for y in range(16) for x in range(16) if im.getpixel((x, y))[3]]
    mean = sum(0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] for c in cols) / len(cols) / 255
    for y in range(16):
        for x in range(16):
            r, g, b, a = im.getpixel((x, y))
            if not a:
                continue
            h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            l = min(1, max(0, (l - mean) * contrast + mean))
            if pink and 0.25 < l < 0.85 and (h < 0.1 or h > 0.9):
                s = min(1, s + pink)
            s = min(1, s * sat)
            r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
            im.putpixel((x, y), (round(r2 * 255), round(g2 * 255), round(b2 * 255), a))


im, out = fresh('live_shrimp')
punch(im, 1.45, 1.6)
im.save(out)

def hexc(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


# bamboo rod: the line came out as broken dots; one line from the rod tip down to the red bobber, then a hook
im, out = fresh('bamboo_fishing_rod')
for y in range(3, 10):
    im.putpixel((12, y), hexc('#d8d8c8'))
im.putpixel((12, 10), hexc('#c03a20'))
for y in range(11, 16):                          # clear the leftover specks under the bobber
    for x in range(9, 16):
        im.putpixel((x, y), (0, 0, 0, 0))
for (x, y) in ((12, 11), (12, 12), (11, 13), (10, 12)):   # a small J hook
    im.putpixel((x, y), hexc('#a8a8b0'))
im.save(out)

# bamboo bobber: two darker bamboo nodes across the body so it reads as bamboo, not a leaf
im, out = fresh('bamboo_bobber')
filled = {(x, y) for y in range(16) for x in range(16) if im.getpixel((x, y))[3]}
inner = lambda p: all((p[0] + dx, p[1] + dy) in filled for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
for (x, y) in filled:
    if x - y in (-5, -1) and inner((x, y)):
        im.putpixel((x, y), hexc('#343c10'))
im.save(out)
print('touched up: live_shrimp, bamboo_fishing_rod, bamboo_bobber')
