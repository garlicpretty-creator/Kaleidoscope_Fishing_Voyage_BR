"""Hand touch-ups for the seventh AI batch (2026-11-14: block items, spawn eggs, unknown fish).

fish_print         the black fish broke apart when shrunk; hand-drawn: frame, rice paper, ink fish, red seal.
dried_fish_string  the converter turned the tall string diagonal and the fish fell apart;
                   hand-drawn: two fish (tapered body, eye, forked tail) on a rope with a loop on top.
The Fish Tank, Tackle Rack and Drying Rack icons from this batch were dropped: those blocks have no item
file, so the inventory shows their 3D model.
Safe to run again.
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
KAL = os.path.dirname(os.path.dirname(HERE))
STAGE = os.path.join(KAL, 'icon_preview', 'AI轉換結果')


def hexc(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def draw(name, grid, pal):
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(grid):
        assert len(row) == 16, (name, y)
        for x, ch in enumerate(row):
            if ch != '.':
                im.putpixel((x, y), hexc(pal[ch]))
    im.save(os.path.join(STAGE, f'{name}.png'))


WOOD = {'O': '#2e1c10', 'L': '#8b5b2e', 'W': '#6b4626', 'w': '#4a2f1b', 'R': '#d8c08a',
        'F': '#d89a3c', 'f': '#a8682a', 'H': '#f4d080', 'E': '#2a1a08', 'T': '#f0b850'}
draw('dried_fish_string', [
    '......ORRO......',
    '.....OR..RO.....',
    '......ORRO......',
    '.......RO.......',
    '...OOOOROO...OO.',
    '..OHHHHRHHO.OFFO',
    '.OEFFFFRFFFOOFO.',
    '..OffffRfffO.OFO',
    '...OOOOROO...OO.',
    '.......RO.......',
    '...OOOOROO...OO.',
    '..OHHHHRHHO.OFFO',
    '.OEFFFFRFFFOOFO.',
    '..OffffRfffO.OFO',
    '...OOOOROO...OO.',
    '.......RO.......',
], WOOD)

draw('fish_print', [
    '................',
    '................',
    'OOOOOOOOOOOOOOOO',
    'OWWWWWWWWWWWWWwO',
    'OWPPPPPPPPPPPPwO',
    'OWPPPPPPPPPPPPwO',
    'OWPPPKKKKKPPKPwO',
    'OWPPKPKKKKKKKPwO',
    'OWPPKKKKKKKKKPwO',
    'OWPPPKKKKKPPKRwO',
    'OWPPPPPPPPPPPPwO',
    'OWppppppppppppwO',
    'OwwwwwwwwwwwwwwO',
    'OOOOOOOOOOOOOOOO',
    '................',
    '................',
], {'O': '#2e1c10', 'W': '#7a4a24', 'w': '#5a341a', 'P': '#efe4c8', 'p': '#d8cba8', 'K': '#1c1c1c',
    'R': '#c02020'})
print('touched up: dried_fish_string, fish_print')
