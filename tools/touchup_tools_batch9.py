"""Hand touch-ups for the ninth AI batch (2026-11-14: end maggot, knife, ice auger, basket, cormorant ring,
bamboo hat, straw raincoat), applied to the staged 16x16 icons in icon_preview/AI轉換結果.

usage: python tools/touchup_tools_batch9.py

cormorant_ring  the white inside the ring was enclosed by the ring, so the background fill never reached it;
                make it transparent.
fishing_knife   the 47-cell blade shrank to a one-pixel stick; hand-drawn after the AI design (wooden handle,
                dark guard, two-tone steel blade with a bright edge), lying corner to corner like vanilla swords.
ice_auger       the red T-handle and the spiral flights vanished when shrunk; hand-drawn after the AI design.
Safe to run again: the touched-up icons are rebuilt from the untouched copies (<name>.orig.png) or the grids.
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


def grid(rows, pal):
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        assert len(row) == 16, (y, row)
        for x, ch in enumerate(row):
            if ch != '.':
                im.putpixel((x, y), hexc(pal[ch]))
    return im


# cormorant ring: clear the enclosed white
im, out = fresh('cormorant_ring')
for y in range(16):
    for x in range(16):
        c = im.getpixel((x, y))
        if c[3] and sum(c[:3]) > 690:
            im.putpixel((x, y), (0, 0, 0, 0))
im.save(out)

# fishing knife: handle bottom-left, blade to the top-right
KNIFE = [
    '..............OO',
    '.............OWO',
    '............OWsO',
    '...........OWsO.',
    '..........OWsO..',
    '.........OWsdO..',
    '........OWsdO...',
    '.......OWsdO....',
    '...OO.OWsdO.....',
    '...OGOWsdO......',
    '....OGGdO.......',
    '...OLhGGO.......',
    '..OLhhO.OO......',
    '.OLhhO..........',
    'OLhhO...........',
    'OOOO............',
]
KPAL = {'O': '#1d2733', 'W': '#eef3f8', 's': '#b4c0cc', 'd': '#7a8a9c', 'G': '#3c4654',
        'L': '#b8763c', 'h': '#7a4220'}
knife = grid(KNIFE, KPAL)
knife.save(os.path.join(STAGE, 'fishing_knife.png'))

# ice auger: red T-handle at the top-left, shaft down to the bottom-right with spiral flights
AUGER = [
    '....OO..........',
    '...ORRO.........',
    '..ORrRO.........',
    '.ORrROO.........',
    'ORrRONMO........',
    'OrRO.OMMO.......',
    '.OO...OMSO......',
    '.......OMSO.....',
    '........OFSFO...',
    '.......OFOMSFO..',
    '........OFMSFFO.',
    '.........OFMSFO.',
    '..........OFMSFO',
    '...........OFMSO',
    '............OFFO',
    '.............OO.',
]
APAL = {'O': '#1a2230', 'R': '#d8582a', 'r': '#9a2c1c', 'N': '#26584a', 'M': '#5e6e82', 'S': '#c8d4e0',
        'F': '#8696aa'}
auger = grid(AUGER, APAL)
# spiral flights: the lower shaft is a 3-wide band along the diagonal with alternating light and dark turns
for y in range(16):
    for x in range(16):
        if y >= 8 and abs(x - y) <= 1 and x + y <= 28:
            turn = ((x + y) // 2) % 2
            edge = abs(x - y) == 1
            c = ('#e2eaf2' if turn else '#7d8da2') if not edge else ('#a8b6c6' if turn else '#5a6a7e')
            auger.putpixel((x, y), hexc(c))
for y in range(16):
    for x in range(16):
        if y >= 8 and not auger.getpixel((x, y))[3] and any(
                0 <= x + dx < 16 and 0 <= y + dy < 16 and abs((x + dx) - (y + dy)) <= 1 and (y + dy) >= 8
                and (x + dx) + (y + dy) <= 28 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            auger.putpixel((x, y), hexc(APAL['O']))
auger.putpixel((15, 15), hexc(APAL['O']))
auger.save(os.path.join(STAGE, 'ice_auger.png'))
print('touched up: cormorant_ring, fishing_knife, ice_auger')
