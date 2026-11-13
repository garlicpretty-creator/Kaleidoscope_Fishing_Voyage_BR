"""Hand touch-ups for the fifth AI batch (2026-11-14: dishes and sauces), applied to the staged 16x16 icons.

void_seafood_soup  the purple bowl melts into the purple soup when shrunk; rebuilt on a bowl template
                   (rim, soup, bowl body, foot) with the contents painted on: pink shrimp, a pale jellyfish,
                   cream chunks, a dark chorus piece.
raw_har_gow        too pale to read on the slot; stronger contrast, pinker filling showing through.
har_gow            a little more contrast so the shrimp filling shows.
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


im, out = fresh('raw_har_gow')
punch(im, 1.5, 1.5, pink=0.25)
im.save(out)
im, out = fresh('har_gow')
punch(im, 1.25, 1.2)
im.save(out)

BOWL = [
    '...OOOOOOOOOO...',
    '.OOLLLLLLLLLLOO.',
    'OLRSSSSSSSSSSRLO',
    'OLSSSSSSSSSSSSLO',
    'OLSSSSSSSSSSSSLO',
    'OLSSSSSSSSSSSSLO',
    'OLSSSSSSSSSSSSLO',
    'OLRSSSSSSSSSSRLO',
    'ODLRRSSSSSSRRLDO',
    'ODDLLLLLLLLLLDDO',
    '.ODDDDDDDDDDDdO.',
    '.ODdDDDDDDDDddO.',
    '..ODDDDDDDDddO..',
    '...OODDDDddOO...',
    '.....ODDddO.....',
    '.....OOOOOO.....',
]
CONTENT = {  # soup contents, painted over the S cells
    (9, 3): 'P', (10, 3): 'P', (8, 4): 'P', (11, 4): 'p', (8, 5): 'p', (11, 5): 'P', (10, 6): 'p',  # shrimp
    (4, 5): 'J', (5, 5): 'J', (6, 5): 'J', (4, 6): 'j', (6, 6): 'j', (5, 7): 'j',                  # jellyfish
    (4, 3): 'C', (5, 3): 'C', (11, 6): 'C', (8, 6): 'C',                                            # cream chunks
    (6, 3): 'V', (9, 7): 'V', (10, 7): 'V', (3, 4): 's', (12, 5): 's', (7, 6): 's',                 # dark piece, shine
}
PAL = {'O': '#241628', 'L': '#e6d4f2', 'R': '#a888c0', 'S': '#4a2860', 's': '#7a4c98', 'D': '#5c3474',
       'd': '#3c2050', 'P': '#f4b0d8', 'p': '#c46aa0', 'J': '#ddd0f8', 'j': '#a898d8', 'C': '#ece4bc',
       'V': '#2a1438'}
im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
for y, row in enumerate(BOWL):
    for x, ch in enumerate(row):
        if ch != '.':
            im.putpixel((x, y), hexc(PAL[CONTENT.get((x, y), ch) if ch == 'S' else ch]))
im.save(os.path.join(STAGE, 'void_seafood_soup.png'))
print('touched up: raw_har_gow, har_gow, void_seafood_soup')
