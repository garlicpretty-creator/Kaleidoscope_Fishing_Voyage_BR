"""Hand touch-ups for the seventh AI batch (2026-11-14: block items, spawn eggs, unknown fish).

fish_tank          reconverted with a fixed 28 px cell: the goldfish and the water plant show.
tackle_rack        hand-drawn in the same frame as the drying rack: a coil of line, a hook, a bamboo rod.
fish_print         the black fish broke apart when shrunk; hand-drawn: frame, rice paper, ink fish, red seal.
drying_rack        at 16 px the three hanging fish were one pixel wide and vanished into the frame;
                   hand-drawn: thinner posts so three 2 px fish fit between them.
dried_fish_string  the converter turned the tall string diagonal and the fish fell apart;
                   hand-drawn: two fish (tapered body, eye, forked tail) on a rope with a loop on top.
Safe to run again.
"""
import os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ai2pixel as A  # noqa: E402

KAL = os.path.dirname(os.path.dirname(HERE))
STAGE = os.path.join(KAL, 'icon_preview', 'AI轉換結果')
INPUT = os.path.join(KAL, 'icon_ai_input')
DONE = os.path.join(INPUT, '已完成', '第七批')


def hexc(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def source(name):
    for d in (INPUT, DONE):
        p = os.path.join(d, f'{name}.png')
        if os.path.exists(p):
            return p
    raise FileNotFoundError(name)


def reconvert(name, cell):
    tmp = os.path.join(STAGE, '_raw', f'_{name}_cell{cell}')
    A.convert(source(name), tmp, cell=cell, diagonal=False)
    f = [g for g in os.listdir(tmp) if g.endswith('_16x16.png')][0]
    Image.open(os.path.join(tmp, f)).save(os.path.join(STAGE, f'{name}.png'))


def draw(name, grid, pal):
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(grid):
        assert len(row) == 16, (name, y)
        for x, ch in enumerate(row):
            if ch != '.':
                im.putpixel((x, y), hexc(pal[ch]))
    im.save(os.path.join(STAGE, f'{name}.png'))


reconvert('fish_tank', 28)

WOOD = {'O': '#2e1c10', 'L': '#8b5b2e', 'W': '#6b4626', 'w': '#4a2f1b', 'R': '#d8c08a',
        'F': '#d89a3c', 'f': '#a8682a', 'H': '#f4d080', 'E': '#2a1a08', 'T': '#f0b850'}
draw('drying_rack', [
    '................',
    'OOOOOOOOOOOOOOOO',
    'OLLLLLLLLLLLLLwO',
    'OLwOROOROOROOLwO',
    'OLwOTT.TT.TTOLwO',
    'OLwOFf.Ff.FfOLwO',
    'OLwOHF.HF.HFOLwO',
    'OLwOHF.HF.HFOLwO',
    'OLwOFf.Ff.FfOLwO',
    'OLwOEf.Ef.EfOLwO',
    'OLwO........OLwO',
    'OLwOOOOOOOOOOLwO',
    'OLLLLLLLLLLLLLwO',
    'OLwOOOOOOOOOOLwO',
    'OLLwO......OLLwO',
    'OOOOO......OOOOO',
], WOOD)

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

WOOD.update({'H': '#b8bcc4', 'B': '#c8b050'})
TACKLE = dict(WOOD, H='#b8bcc4')
draw('tackle_rack', [
    '................',
    'OOOOOOOOOOOOOOOO',
    'OLLLLLLLLLLLLLwO',
    'OLwO' + 'ROOOOROO' + 'OLwO',
    'OLwO' + 'RRR..H..' + 'OLwO',
    'OLwO' + 'R.R..H..' + 'OLwO',
    'OLwO' + 'RRRH.H..' + 'OLwO',
    'OLwO' + '...HHH.B' + 'OLwO',
    'OLwO' + '.....BB.' + 'OLwO',
    'OLwO' + '...BB...' + 'OLwO',
    'OLwO' + '.BB.....' + 'OLwO',
    'OLwOOOOOOOOOOLwO',
    'OLLLLLLLLLLLLLwO',
    'OLwOOOOOOOOOOLwO',
    'OLLwO......OLLwO',
    'OOOOO......OOOOO',
], TACKLE)

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
print('touched up: fish_tank, tackle_rack, drying_rack, dried_fish_string, fish_print')
