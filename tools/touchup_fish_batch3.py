"""Hand touch-ups for the third AI batch (2026-11-14, the last 24 fish), applied to the staged 16x16 icons.

eyes                one-cell eyes were lost when the 50-cell sources were shrunk; put one back on every fish
                    (dark on light fish, a glowing colour on dark / Nether / End fish). The cave blindfish stays eyeless.
river_lord_catfish  the gold barbels were one cell thin in the source and vanished when shrunk; draw them back.
emperor_tuna        the gold finlets on the back (what sets it apart from the plain tuna) were lost; put them back.
lava_dragon_koi     the whiskers came out as loose brown dots under the head; make them read as gold whiskers.
Safe to run again: it always starts from the untouched copy (<name>.orig.png).
"""
import os, shutil
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


def paint(im, pts, colour, only_empty=False):
    for (x, y) in pts:
        if only_empty and im.getpixel((x, y))[3]:
            continue
        im.putpixel((x, y), colour)


DARK = hexc('#141414')
GOLD_EYE = hexc('#ffd23a')
# name: (eye cell, eye colour)
EYES = {
    'sea_bass':          ((2, 11), DARK),
    'yellow_croaker':    ((2, 11), DARK),
    'golden_croaker':    ((3, 11), hexc('#2a1200')),
    'mackerel':          ((2, 11), DARK),
    'sea_bream':         ((2, 10), DARK),
    'tuna':              ((2, 11), DARK),
    'skipjack':          ((2, 11), hexc('#e8ecf4')),
    'saury':             ((2, 12), DARK),
    'hairtail':          ((2, 13), DARK),
    'grouper':           ((2, 10), DARK),
    'flying_fish':       ((2, 11), DARK),
    'anglerfish':        ((3, 10), hexc('#e6d9a0')),
    'blazefin':          ((3, 10), GOLD_EYE),
    'magma_koi':         ((2, 11), GOLD_EYE),
    'lava_eel':          ((2, 12), GOLD_EYE),
    'chorus_carp':       ((2, 12), hexc('#1e0820')),
    'ender_angler':      ((3, 10), hexc('#e070ff')),
    'void_eel':          ((2, 12), hexc('#d080ff')),
    'starfin':           ((2, 11), hexc('#fff3b0')),
    'river_lord_catfish': ((2, 11), hexc('#e0c060')),
    'emperor_tuna':      ((2, 11), DARK),
    'frostlake_char':    ((3, 10), hexc('#e8f6ff')),
    'lava_dragon_koi':   ((2, 12), GOLD_EYE),
}

images = {}


def get(name):
    if name not in images:
        images[name] = fresh(name)
    return images[name][0]


for name, (cell, colour) in EYES.items():
    paint(get(name), [cell], colour)

# river lord catfish: two pale-gold barbels hanging from the mouth
im = get('river_lord_catfish')
paint(im, [(0, 13), (0, 14), (1, 15)], hexc('#d8bd6a'), only_empty=True)
paint(im, [(4, 14), (5, 15)], hexc('#d8bd6a'))

# emperor tuna: gold finlets along the back, between the dorsal fin and the tail
im = get('emperor_tuna')
paint(im, [(9, 4), (11, 3)], hexc('#f2c230'), only_empty=True)
paint(im, [(8, 4)], hexc('#b8860b'), only_empty=True)

# lava dragon koi: gold whiskers
paint(get('lava_dragon_koi'), [(0, 15), (3, 15), (4, 15)], hexc('#f0c040'))

for name, (im, out) in images.items():
    im.save(out)
print('touched up:', ', '.join(images))
