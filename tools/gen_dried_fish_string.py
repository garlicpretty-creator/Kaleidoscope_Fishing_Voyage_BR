"""Rebuild the string of dried fish (魚乾串): model and texture, matching its inventory icon.

usage: python tools/gen_dried_fish_string.py

Three golden dried fish threaded on one twine, head to the left, tail fork to the right, hanging from a knot at the
top of the block. Each fish is a body, a smaller head with an eye, a peduncle and a forked tail (transparent notch;
the block uses alpha_test). 1 texture pixel per model pixel, like vanilla blocks.
"""
import json, os, random, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
TW = TH = 32

# texture regions (u, v, w, h)
B_SIDE, B_TOP, B_BOT, B_END = (0, 0, 7, 3), (0, 3, 7, 2), (7, 3, 7, 2), (7, 0, 2, 3)
H_SIDE, H_TOP, H_BOT, H_NOSE = (9, 0, 2, 2), (11, 0, 2, 1), (11, 1, 2, 1), (13, 0, 1, 2)
PED = (14, 0, 1, 1)
T_SIDE, T_IN, T_OUT, T_TOP = (16, 0, 3, 4), (19, 0, 1, 4), (20, 0, 1, 4), (21, 0, 3, 1)
STRING = (24, 0, 1, 16)
TWINE = (26, 0, 4, 4)

LIGHT, MID, BELLY, DARK, EYE = '#f4d080', '#d89a3c', '#a8682a', '#7a4a1e', '#2a1a08'
TW_A, TW_B = '#d8c08a', '#b49a62'


def hexc(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def face(region, w, h, flip=False):
    u, v = region[0], region[1]
    return {'uv': [u + w, v] if flip else [u, v], 'uv_size': [-w if flip else w, h]}


def cube(origin, size, uv, inflate=0):
    c = {'origin': [round(x, 3) for x in origin], 'size': [round(x, 3) for x in size], 'uv': uv}
    if inflate:
        c['inflate'] = inflate
    return c


def box(origin, size, side, top, bottom, end_e, end_w, flip_s=True, inflate=0):
    """side: region for north/south (south mirrored so the head stays on the same end); ends for east/west."""
    w, h, d = size
    return cube(origin, size, {
        'north': face(side, w, h), 'south': face(side, w, h, flip_s),
        'east': face(end_e, d, h), 'west': face(end_w, d, h),
        'up': face(top, w, d), 'down': face(bottom, w, d)}, inflate)


def fish(x0, y0):
    """Head towards -x. x0 = left end of the body, y0 = bottom of the body."""
    return [
        box([x0, y0, -1], [7, 3, 2], B_SIDE, B_TOP, B_BOT, B_END, B_END),                       # body
        box([x0 - 2, y0 + 0.5, -0.75], [2, 2, 1.5], H_SIDE, H_TOP, H_BOT, H_NOSE, H_NOSE),      # head
        box([x0 + 7, y0 + 1, -0.5], [1, 1, 1], PED, PED, PED, PED, PED),                        # tail root
        box([x0 + 8, y0 - 0.5, -0.25], [3, 4, 0.5], T_SIDE, T_TOP, T_TOP, T_OUT, T_IN),         # forked tail
        box([-0.5, y0, -1], [1, 3, 2], TWINE, TWINE, TWINE, TWINE, TWINE, inflate=0.1),         # twine round it
    ]


def geometry():
    cubes = [box([-0.5, 0.5, -0.5], [1, 15.5, 1], STRING, TWINE, TWINE, STRING, STRING),         # the twine
             box([-1, 15, -1], [2, 1, 2], TWINE, TWINE, TWINE, TWINE, TWINE)]                     # knot at the top
    for x0, y0 in ((-4, 11), (-3, 6), (-4, 1)):
        cubes += fish(x0, y0)
    return {'format_version': '1.12.0', 'minecraft:geometry': [{
        'description': {'identifier': 'geometry.kaleidoscope_fishing.dried_fish_string', 'texture_width': TW,
                        'texture_height': TH, 'visible_bounds_width': 2, 'visible_bounds_height': 2,
                        'visible_bounds_offset': [0, 0.5, 0]},
        'bones': [{'name': 'root', 'pivot': [0, 0, 0], 'cubes': cubes}]}]}


def paint():
    rnd = random.Random(11)
    im = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
    px = im.load()

    def fill(region, fn):
        u0, v0, w, h = region
        for v in range(h):
            for u in range(w):
                c = fn(u, v)
                if c:
                    px[u0 + u, v0 + v] = hexc(c)

    def body_side(u, v):
        row = (LIGHT, MID, BELLY)[v]
        if u == 0:
            return (MID, BELLY, DARK)[v]                     # gill line next to the head
        if v == 1 and (u * 3) % 5 == 1:
            return '#c88a30'                                 # scale flecks
        if v == 0 and u % 3 == 2:
            return '#e8bc66'
        return row
    fill(B_SIDE, body_side)
    fill(B_TOP, lambda u, v: '#e0b25a' if v == 0 and u % 2 else LIGHT if v == 0 else '#e8bc66')
    fill(B_BOT, lambda u, v: BELLY if (u + v) % 3 else '#94582a')
    fill(B_END, lambda u, v: (LIGHT, MID, BELLY)[v])
    fill(H_SIDE, lambda u, v: ((EYE, '#e0b25a'), (MID, BELLY))[v][u])            # eye next to the body
    fill(H_TOP, lambda u, v: '#e0b25a')
    fill(H_BOT, lambda u, v: BELLY)
    fill(H_NOSE, lambda u, v: (MID, DARK)[v])
    fill(PED, lambda u, v: MID)
    fork = lambda u, v: (v in (1, 2), True, v in (0, 3))[u]               # narrow root, fan, two lobes with a notch
    fill(T_SIDE, lambda u, v: ('#c88a30' if u == 0 else MID if u == 1 else '#e0a848') if fork(u, v) else None)
    fill(T_IN, lambda u, v: MID if fork(0, v) else None)
    fill(T_OUT, lambda u, v: MID if fork(2, v) else None)
    fill(T_TOP, lambda u, v: MID if u else None)
    fill(STRING, lambda u, v: TW_B if v % 3 == 2 else TW_A)
    fill(TWINE, lambda u, v: TW_B if (u + v) % 3 == 0 else TW_A)
    return im


def main():
    with open(os.path.join(RP, 'models', 'blocks', 'dried_fish_string.geo.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(geometry(), f, indent=2)
    tex = os.path.join(RP, 'textures', 'blocks', 'kfv_dried_fish_string.png')
    paint().save(tex)
    print('cubes', len(geometry()['minecraft:geometry'][0]['bones'][0]['cubes']), 'wrote', pbr.refresh(tex))


if __name__ == '__main__':
    main()
