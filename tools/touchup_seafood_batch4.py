"""Hand touch-ups for the fourth AI batch (2026-11-14: seafood and ingredients), applied to the staged 16x16 icons.

mudskipper  its bulging eyes on top of the head (the thing that makes it a mudskipper) were lost when shrunk;
            put two back.
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


im, out = fresh('mudskipper')
RIM, PUPIL, OUT = hexc('#f0d070'), hexc('#1a1008'), hexc('#3a2c10')
for (x, y), c in {(2, 7): RIM, (2, 8): PUPIL, (1, 7): OUT, (2, 6): OUT,
                  (4, 6): RIM, (4, 7): PUPIL, (3, 6): OUT, (4, 5): OUT}.items():
    im.putpixel((x, y), c)
im.save(out)
print('touched up: mudskipper')


def lumf(c):
    return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255


def recolour(im, ramp):
    """Keep every pixel's light and dark, swap the hue onto a new ramp (dark -> light)."""
    cols = [im.getpixel((x, y)) for y in range(16) for x in range(16) if im.getpixel((x, y))[3]]
    lo, hi = min(map(lumf, cols)), max(map(lumf, cols))
    for y in range(16):
        for x in range(16):
            c = im.getpixel((x, y))
            if c[3]:
                t = (lumf(c) - lo) / max(1e-6, hi - lo)
                im.putpixel((x, y), hexc(ramp[min(len(ramp) - 1, int(round(t * (len(ramp) - 1))))]))


# fish roe vs flying fish roe looked the same: fish roe -> deep red ikura, flying fish roe -> bright tobiko orange
im, out = fresh('fish_roe')
recolour(im, ['#3a0606', '#6a0e0c', '#a01a14', '#cc2c1a', '#e8502a', '#ff8a52', '#ffd0a8'])
im.save(out)
im, out = fresh('flying_fish_roe')
recolour(im, ['#5a2200', '#8c3c00', '#c86400', '#f08c10', '#ffb21e', '#ffd248', '#fff0a0'])
filled = {(x, y) for y in range(16) for x in range(16) if im.getpixel((x, y))[3]}
for (x, y) in filled:                                # fine grains: tobiko is tiny beads, not big blobs
    if all((x + dx, y + dy) in filled for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
        if (x + y) % 2 == 0:
            im.putpixel((x, y), hexc('#e07a08'))
        elif (x * 3 + y) % 7 == 0:
            im.putpixel((x, y), hexc('#fff0a0'))
im.save(out)

# karasumi slices: cut lines across the long axis so it reads as slices, not the whole roe
im, out = fresh('karasumi_slices')
filled = {(x, y) for y in range(16) for x in range(16) if im.getpixel((x, y))[3]}
inner = lambda p: all((p[0] + dx, p[1] + dy) in filled for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
for c in (-5, 0, 5):
    for (x, y) in filled:
        if x - y == c and inner((x, y)):
            im.putpixel((x, y), hexc('#5a2406'))
        elif x - y == c + 1 and inner((x, y)):
            im.putpixel((x, y), hexc('#ffc23c'))
im.save(out)

# clam: the dark gap between the open shells, with a little meat showing
im, out = fresh('clam')
for (x, y) in [(5, 10), (6, 10), (7, 10), (8, 9), (9, 9), (10, 9), (11, 8), (12, 8)]:
    im.putpixel((x, y), hexc('#3c2614'))
for (x, y) in [(7, 11), (8, 10), (9, 10), (10, 10)]:
    im.putpixel((x, y), hexc('#f4e2b0'))
im.save(out)

# cave crayfish: shrinking the AI drawing (icon_ai_input/海鮮重繪_v2) loses the pincers and legs, which are only
# one source pixel apart; hand-drawn at 16x16 after that drawing: pale blue-white shell, two black eyes,
# two open pincers held apart from the body, segmented tail and fan. Laid out from geometric parts
# (oval carapace, tapering abdomen, fan, arm + oval pincer each side), then the pincer gaps cut by hand.
CRAY = [
    '...........OOO..',
    '..........OWWBO.',
    '..........OWBBbO',
    '.........OWBPbbO',
    '........OWPBbbbO',
    '.OOOO..OPBBPbOO.',
    'OCCMMOOWBPbbO...',
    '..OMcOBBBbPO....',
    'OMMcMMBBBbO.....',
    '.OOOBBBBbO......',
    '...OBEBMOO......',
    '....OBEOCMO.....',
    '.....OOCMMO.....',
    '......OCOMO.....',
    '......OM.cO.....',
    '.......O.O......',
]
PAL = {'O': '#2a3448', 'W': '#f4f0e0', 'B': '#b8cce0', 'b': '#9aa8c8', 'P': '#8a88b0', 'E': '#141418',
       'C': '#d2def0', 'M': '#a6b6d4', 'c': '#7e8cb4'}
im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
for y, row in enumerate(CRAY):
    for x, ch in enumerate(row):
        if ch != '.':
            im.putpixel((x, y), hexc(PAL[ch]))
im.save(os.path.join(STAGE, 'cave_crayfish.png'))

# squid: the arms had merged into one blob; three separate arms with dark gaps, plus an eye
im, out = fresh('squid_tube')
for y in range(16):
    for x in range(16):
        if x - y < -4:
            im.putpixel((x, y), (0, 0, 0, 0))
ARM, ARM_TIP, GAP = hexc('#f0dcd6'), hexc('#c8a0a8'), hexc('#5a3a4e')
arms = [  # each arm is a run of edge-connected pixels fanning out from the head (lower-left)
    [(5, 10), (4, 10), (3, 10), (3, 11), (2, 11), (1, 11), (0, 11)],
    [(6, 11), (5, 11), (5, 12), (4, 12), (4, 13), (3, 13), (3, 14), (2, 14)],
    [(7, 12), (7, 13), (6, 13), (6, 14), (6, 15)],
]
for arm in arms:
    for k, (x, y) in enumerate(arm):
        im.putpixel((x, y), ARM_TIP if k == len(arm) - 1 else ARM)
for arm in arms:
    for (x, y) in arm:
        for nx, ny in ((x - 1, y), (x, y + 1), (x + 1, y), (x, y - 1)):
            if 0 <= nx < 16 and 0 <= ny < 16 and not im.getpixel((nx, ny))[3]:
                im.putpixel((nx, ny), GAP)
im.putpixel((7, 9), hexc('#2a1a24'))
im.save(out)


# jellyfish (second AI drawings, icon_ai_input/海鮮重繪_v2): the bells convert well but the thin tentacles
# vanish when shrunk, so keep the converted bell (<name>.v2.png) and draw the tentacles by hand.
def base_v2(name, keep_rows):
    im = Image.open(os.path.join(STAGE, f'{name}.v2.png')).convert('RGBA')
    for y in range(keep_rows, 16):
        for x in range(16):
            im.putpixel((x, y), (0, 0, 0, 0))
    return im


def strand(im, path, light, edge, tip):
    """A thin tentacle: light pixels along the path, a dark edge on the right where it is empty."""
    for k, (x, y) in enumerate(path):
        im.putpixel((x, y), tip if k == len(path) - 1 else light)
    for (x, y) in path:
        if x + 1 < 16 and not im.getpixel((x + 1, y))[3]:
            im.putpixel((x + 1, y), edge)


# moon jellyfish: four long thin tentacles trailing to the lower left
im = base_v2('moon_jellyfish', 11)
EDGE = hexc('#2f5c60')
for path in ([(2, 11), (2, 12), (1, 13), (1, 14), (0, 15)],
             [(5, 11), (5, 12), (4, 13), (4, 14), (3, 15)],
             [(8, 11), (8, 12), (7, 13), (7, 14), (6, 15)],
             [(11, 10), (11, 11), (10, 12), (10, 13), (9, 14)]):
    strand(im, path, hexc('#cfe0f0'), EDGE, hexc('#9cb4cc'))
im.save(os.path.join(STAGE, 'moon_jellyfish.png'))

# chorus jellyfish: pale, thick inner arms hanging down, darker purple outer tentacles curling outwards
im = base_v2('chorus_jellyfish', 9)
DK, PALE, MID, OUTER = hexc('#3a1c40'), hexc('#ecd0f4'), hexc('#c8a0d8'), hexc('#a060a8')
for x in range(3, 13):
    im.putpixel((x, 9), DK)                                # shadow under the bell
for cx, length in ((3, 5), (7, 6), (11, 5)):               # inner arms, two pixels wide, a little wavy, with gaps
    for i in range(length):
        y = 10 + i
        x = cx - (1 if i in (2, 3) else 0)
        if y > 15:
            break
        im.putpixel((x, y), PALE)
        im.putpixel((x + 1, y), MID if i < length - 1 else DK)
        im.putpixel((x + 2, y), DK)                        # shadow edge on one side; the next column stays open
for path in ([(1, 9), (0, 10), (0, 11)], [(14, 9), (15, 10), (15, 11)]):
    for (x, y) in path:                                    # outer tentacles curl out to the sides
        im.putpixel((x, y), OUTER)
    for (x, y) in path:
        for nx, ny in ((x, y + 1), (x - 1, y), (x + 1, y)):
            if 0 <= nx < 16 and 0 <= ny < 16 and not im.getpixel((nx, ny))[3]:
                im.putpixel((nx, ny), DK)
im.save(os.path.join(STAGE, 'chorus_jellyfish.png'))
print('touched up: fish_roe, flying_fish_roe, karasumi_slices, clam, cave_crayfish, squid_tube, moon_jellyfish, chorus_jellyfish')
