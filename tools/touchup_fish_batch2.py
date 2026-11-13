"""Hand touch-ups for the second AI batch (2026-11-14), applied to the staged 16x16 icons.

carp     the AI drew a red-and-white koi; recolour it to a bronze/golden common carp (keeps every
         pixel's light and dark, only the hue changes), so it no longer reads like the Magma Koi.
catfish  the barbels were one cell thin in the source and vanished when shrunk; draw them back.
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
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


CARP = [hexc(c) for c in ('#241004', '#4a2508', '#74400f', '#9c5e16', '#c27f22', '#dea233', '#f0c459', '#f9e09a')]


def carp_colour(rgb):
    r, g, b = [v / 255 for v in rgb]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    _, _, s = colorsys.rgb_to_hls(r, g, b)
    if lum > 0.75 and s < 0.6:          # koi white patches: pull down so the flank reads as one gold body
        lum = 0.60 + (lum - 0.75) * 0.9
    t = max(0.0, min(1.0, (lum - 0.04) / 0.86)) ** 0.85 * (len(CARP) - 1)
    return CARP[min(len(CARP) - 1, int(round(t)))]


im, out = fresh('carp')
for y in range(16):
    for x in range(16):
        c = im.getpixel((x, y))
        if c[3]:
            im.putpixel((x, y), carp_colour(c[:3]) + (255,))
for (x, y) in [(14, 0), (15, 0), (13, 1), (14, 1), (15, 1), (12, 2), (13, 2), (14, 2), (12, 3), (13, 3), (14, 3), (15, 4)]:
    c = im.getpixel((x, y))
    if c[3]:                            # tail a touch redder, like a common carp's
        im.putpixel((x, y), (min(255, c[0] + 18), max(0, c[1] - 22), max(0, c[2] - 10), 255))
for (x, y) in [(0, 15), (1, 15)]:       # barbels
    if not im.getpixel((x, y))[3]:
        im.putpixel((x, y), CARP[1] + (255,))
im.save(out)

im, out = fresh('catfish')
BARBEL = hexc('#2a3444')
for (x, y) in [(0, 13), (0, 14), (1, 15), (3, 14), (4, 15)]:
    if not im.getpixel((x, y))[3]:
        im.putpixel((x, y), BARBEL + (255,))
im.save(out)
print('touched up: carp, catfish')
