"""Rebuild the fish merchant (魚販) on the vanilla villager body: model and painted texture.

usage: python tools/gen_fish_merchant.py

Bones follow geometry.villager.v2: head 8x10x8 with the villager nose (2x4x2 hanging below the chin line),
body 8x12x6 under a knee-length coat 8x18x6 (inflate 0.5), the crossed `arms` (two 4x8x4 upper arms and the
8x4x4 forearm bar, tilted like the vanilla pose) and legs 4x12x4. On top of that the merchant keeps his conical
straw hat, a beard, a rope belt and the shoulder pole with two fish baskets resting on his right upper arm.

Bone names other files rely on: `head` (animation.common.look_at_target), `body`, `leg_l`, `leg_r`, `arms`,
`pole`, `basket_f`, `basket_b` (animations/fish_merchant.animation.json). The want-sign overlay
(fish_merchant_wants.geo.json) re-declares root > body > pole with the same pivots, so `pole` keeps its pivot.

Every face gets its own texture region at 1 texture pixel per model unit (per-face UV), painted below.
"""
import json, math, os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
TW = TH = 128
ARMS_TILT = -43                       # vanilla crossed-arms pose (java xRot -0.75 rad)
PX = -7.5                             # pole centre line: over the outer edge of the right upper arm (x -8..-4)

# ------------------------------------------------------------------ palette
SKIN, SHADE, SKIN_D, CHEEK = '#d4966c', '#c07a52', '#a6623c', '#cc8462'
HAIR, HAIR_D, HAIR_L = '#322b26', '#221e1a', '#423930'
BEARD, BEARD_D, BEARD_L = '#8a6a58', '#6e5244', '#a08070'
EYE_W, EYE_G = '#f2eee6', '#2e7a3a'
NOSE_TOP, NOSE_HI, NOSE, NOSE_SIDE, NOSE_SIDE_D, NOSE_UNDER, NOSTRIL = (
    '#e4a47a', '#d98c64', '#c47450', '#a85a3a', '#8a4630', '#6e3224', '#5a281c')
J, J_D, J_L, J_HI, J_IN = '#36507e', '#283a64', '#4c6a9a', '#6a88b4', '#1c2440'
WHITE, WHITE_D, PATCH = '#e8e2d4', '#ccd4de', '#5a7ab8'
ROPE_A, ROPE_B, ROPE_L = '#86642f', '#bc9a55', '#d8c08a'
PANTS, PANTS_L, PANTS_CUFF = '#2a2c36', '#383c4a', '#646c7e'
STRAW_L, STRAW, STRAW_D, STRAW_DD, CORD = '#e4cc7a', '#d0b256', '#b6963e', '#987a2e', '#6a5222'
BAMBOO, BAMBOO_D, BAMBOO_END = '#bccb58', '#677626', '#e4dca0'
WEAVE_D, WEAVE, WEAVE_L, BASKET_IN = '#7c6424', '#9a7e30', '#d2b658', '#5e4a1a'
SILVER, SILVER_D, SILVER_L = '#c4d0dc', '#a0aebe', '#e6eef4'
ORANGE, ORANGE_D, ORANGE_L = '#f49a4a', '#e4762e', '#fcc07a'


def hexc(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def noise(u, v, seed):
    n = (u * 374761393 + v * 668265263 + seed * 2246822519) & 0xffffffff
    n = ((n ^ (n >> 13)) * 1274126177) & 0xffffffff
    return (n ^ (n >> 16)) % 1000 / 1000


def grid(rows, legend):
    """Painter from a list of strings (one char per pixel)."""
    return lambda u, v, w, h: legend.get(rows[v][u])


# ------------------------------------------------------------------ cubes and texture regions
FACE_DIMS = {'north': (0, 1), 'south': (0, 1), 'east': (2, 1), 'west': (2, 1), 'up': (0, 2), 'down': (0, 2)}
regions = {}          # key -> [w, h, painter, (u, v) once packed]


def cube(origin, size, faces, inflate=0, rotation=None, pivot=None):
    """faces: {face: (key, painter)}; a face left out is not drawn (hidden inside the model)."""
    uv = {}
    for face, (key, fn) in faces.items():
        a, b = FACE_DIMS[face]
        w, h = size[a], size[b]
        rw, rh = max(1, math.ceil(w - 1e-6)), max(1, math.ceil(h - 1e-6))
        if key in regions:
            assert regions[key][:2] == [rw, rh], key
        else:
            regions[key] = [rw, rh, fn, None]
        uv[face] = (key, w, h)
    c = {'origin': [round(x, 3) for x in origin], 'size': [round(x, 3) for x in size], 'uv': uv}
    if inflate:
        c['inflate'] = inflate
    if rotation:
        c['rotation'] = rotation; c['pivot'] = pivot
    return c


def same(key, fn, faces=('north', 'south', 'east', 'west', 'up', 'down')):
    """All listed faces painted by one painter, each face its own region (key.face)."""
    return {f: (f'{key}.{f}', fn) for f in faces}


def pack():
    """Shelf-pack every region, tallest first."""
    x = y = shelf = 0
    for key in sorted(regions, key=lambda k: (-regions[k][1], -regions[k][0], k)):
        w, h = regions[key][:2]
        if x + w > TW:
            x, y, shelf = 0, y + shelf, 0
        regions[key][3] = (x, y)
        x += w; shelf = max(shelf, h)
    assert y + shelf <= TH, f'texture full: {y + shelf} > {TH}'


def resolve(bones):
    for b in bones:
        for c in b.get('cubes', []):
            c['uv'] = {f: {'uv': list(regions[k][3]), 'uv_size': [round(w, 3), round(h, 3)]}
                       for f, (k, w, h) in c['uv'].items()}


# ------------------------------------------------------------------ painters
def coat(seed, front=False, back=False, side=False):
    def fn(u, v, w, h):
        r = noise(u, v, seed)
        c = J_D if r < 0.16 else J_L if r > 0.88 else J
        if r > 0.985:
            c = J_HI
        if side and u == w // 2 and v > 1:
            c = J_D                                            # side seam
        if v >= 12 and u in (1, w - 2):
            c = J_D                                            # folds of the coat skirt
        if v == 11:
            c = J_L if u % 2 else J                            # under the rope belt: gathered cloth
        if v == h - 2:
            c = J_L                                            # hem stitch
        if v == h - 1:
            c = J_D                                            # hem
        if front:
            if v == 0:
                c = (J, J, WHITE_D, WHITE, WHITE, WHITE_D, J, J)[u]          # standing collar
            elif v == 1:
                c = (J, J_D, WHITE_D, J_IN, J_IN, WHITE_D, J_D, J)[u]
            elif u == 3:
                c = J_D                                        # front opening
            elif u == 4 and v not in (11,):
                c = J_L if v < h - 2 else c
            if v in (3, 6, 9, 13) and u in (3, 4):
                c = (WHITE, WHITE_D)[u - 3]                    # frog buttons
        if back and 13 <= v <= 15 and 4 <= u <= 6:
            c = PATCH if (u, v) not in ((4, 13), (6, 15)) else WHITE   # a darned patch
        if back and v == 0:
            c = J_D
        return c
    return fn


def jacket_top(u, v, w, h):
    return J_D if u in (0, w - 1) or v in (0, h - 1) else (J_L if noise(u, v, 5) > 0.8 else J)


def rope(u, v, w, h):
    t = (u + v) % 3
    return (ROPE_A, ROPE_B, ROPE_L)[t] if noise(u, v, 9) > 0.15 else ROPE_A


def sleeve(seed):
    def fn(u, v, w, h):
        r = noise(u, v, seed)
        return J_D if r < 0.2 else J_L if r > 0.85 else J
    return fn


def upper_arm(u, v, w, h):
    if v == 0:
        return J_L                                             # shoulder seam
    if v >= 6:
        return J_D if v == 7 else J                            # elbow fold under the forearm bar
    return sleeve(21)(u, v, w, h)


def forearm_front(u, v, w, h):
    # two hands gripping the opposite elbows at the ends, cuffs, sleeves crossing in the middle
    if u in (0, 7) and v >= 1:
        return SHADE if v == 3 else SKIN
    if u in (1, 6) and v >= 1:
        return SKIN_D if v == 2 else SKIN
    if u in (2, 5):
        return WHITE_D if v in (1, 2) else J_L                 # cuffs
    if v == 0:
        return J_L
    if (u, v) in ((3, 3), (4, 1)):
        return J_D                                             # where the sleeves cross
    return J if (u + v) % 3 else J_D


def forearm_under(u, v, w, h):
    if u in (0, 1, 6, 7):
        return SHADE
    return J_D if u in (2, 5) else J


def pants(u, v, w, h):
    if v <= 8:
        return PANTS_L if noise(u, v, 31) > 0.7 else PANTS
    if v == 9:
        return PANTS_CUFF
    if v == 10:
        return STRAW_D if u in (1, 2) else SKIN                # sandal strap over the bare foot
    return STRAW if (u + v) % 2 else STRAW_D                   # straw sole


def sole(u, v, w, h):
    return STRAW_D if (u + v) % 2 else STRAW_DD


def straw_up(u, v, w, h):
    ring = min(u, v, w - 1 - u, h - 1 - v)
    if ring == 0 and w > 4:
        return STRAW_D if (u + v) % 2 else STRAW
    r = noise(u, v, w)
    if r < 0.14:
        return STRAW_D
    return STRAW_L if (ring + (u * v) % 2) % 2 else STRAW


def straw_side(u, v, w, h):
    return STRAW if (u // 2) % 2 else STRAW_D


def straw_under(u, v, w, h):
    ring = min(u, v, w - 1 - u, h - 1 - v)
    return STRAW_DD if (ring + u) % 3 == 0 else STRAW_D


def bamboo_long(u, v, w, h):                                   # along the pole (u or v is the length)
    i = max(u, v) if w > 1 and h > 1 else (u if w > 1 else v)
    return BAMBOO_D if i % 7 == 3 else BAMBOO


def weave(u, v, w, h):
    if v == 0:
        return WEAVE_L
    if v == h - 1:
        return WEAVE_D
    return WEAVE if ((u // 2) + v) % 2 else WEAVE_L


def basket_top(u, v, w, h):
    if min(u, v, w - 1 - u, h - 1 - v) == 0:
        return WEAVE_L if (u + v) % 2 else STRAW_D
    pick = noise(u, v, 77)
    return SILVER if pick < 0.35 else ORANGE if pick < 0.55 else BASKET_IN


def fish_side(kind):
    a, b, c = (SILVER_D, SILVER, SILVER_L) if kind == 's' else (ORANGE_D, ORANGE, ORANGE_L)

    def fn(u, v, w, h):
        if v == 0:
            return a                                           # tail fin
        if v == 1 and u == 0 and h > 2:
            return '#1e2228'                                   # eye
        return c if u == 0 and v > 1 else b
    return fn


def fish_end(kind):
    return lambda u, v, w, h: SILVER_D if kind == 's' else ORANGE_D


HEAD_FRONT = grid([
    'HhHHHHhH',
    'HHHhHHHH',
    'SSSSSSSS',
    'SEESSEES',
    'SWGSSGWS',
    'SsSSSSsS',
    'SrSSSSrS',
    'sBBnnBBs',
    'BBBnnBBB',
    'bBBBBBBb',
], {'H': HAIR, 'h': HAIR_D, 'S': SKIN, 's': SHADE, 'E': HAIR, 'W': EYE_W, 'G': EYE_G, 'r': CHEEK,
    'B': BEARD, 'b': BEARD_D, 'n': SKIN_D})

HEAD_SIDE_ROWS = [
    'HHHHHHHH',
    'SSHHHHHH',
    'SSSSHHHH',
    'SSSSsHHH',
    'SSSSssHH',
    'SSSSssHH',
    'SSSBBHHH',
    'SSBBBhHH',
    'BBBBbhHH',
    'BBBbhHHH',
]
HEAD_LEGEND = {'H': HAIR, 'h': HAIR_D, 'S': SKIN, 's': SHADE, 'B': BEARD, 'b': BEARD_D}


def head_side(mirror):
    """d = distance from the face; west faces run front->back, east faces back->front."""
    return lambda u, v, w, h: HEAD_LEGEND[HEAD_SIDE_ROWS[v][w - 1 - u if mirror else u]]


def head_back(u, v, w, h):
    r = noise(u, v, 41)
    return HAIR_D if r < 0.25 else HAIR_L if r > 0.85 else HAIR


def head_down(u, v, w, h):                                     # v runs back -> front
    return HAIR if v < 3 else SHADE if v < 6 else BEARD_D


def beard_front(u, v, w, h):
    if v == h - 1 and u in (0, w - 1):
        return None                                            # rounded tip
    r = noise(u, v, 51)
    if v == 0:
        return BEARD_D if u in (2, 3) else BEARD               # shadow under the nose
    return BEARD_D if r < 0.25 else BEARD_L if r > 0.8 else BEARD


def beard_plain(u, v, w, h):
    return BEARD_D if (u + v) % 2 else BEARD


# nose: clearly redder and darker than the face, lit top, dark sides and underside
NOSE_FRONT = grid(['tt', 'NN', 'NN', 'xx'], {'t': NOSE_HI, 'N': NOSE, 'x': NOSTRIL})


def nose_side(mirror):
    def fn(u, v, w, h):
        d = w - 1 - u if mirror else u                         # 0 = tip end
        if v == h - 1:
            return NOSE_SIDE_D
        return NOSE if d == 0 and v == 0 else NOSE_SIDE
    return fn


# ------------------------------------------------------------------ model
def rot_x(p, pivot, deg):
    """Bedrock bone rotation about x (render_models.rot convention: x is negated)."""
    a = math.radians(-deg)
    y, z = p[1] - pivot[1], p[2] - pivot[2]
    return [p[0], y * math.cos(a) - z * math.sin(a) + pivot[1], y * math.sin(a) + z * math.cos(a) + pivot[2]]


def geometry():
    regions.clear()
    head = [
        cube([-4, 24, -4], [8, 10, 8], {
            'north': ('head.n', HEAD_FRONT), 'south': ('head.s', head_back),
            'west': ('head.w', head_side(False)), 'east': ('head.e', head_side(True)),
            'up': ('head.u', head_back), 'down': ('head.d', head_down)}),
        # beard hanging below the chin, in front of the coat collar
        cube([-3, 22, -4.75], [6, 3, 1], {
            'north': ('beard.n', beard_front), 'east': ('beard.e', beard_plain), 'west': ('beard.w', beard_plain),
            'down': ('beard.d', beard_plain), 'up': ('beard.u', beard_plain)}),
        # conical straw hat (same shape as before)
        cube([-8, 33, -8], [16, 1, 16], {**same('hat0', straw_side, ('north', 'south', 'east', 'west')),
                                         'up': ('hat0.u', straw_up), 'down': ('hat0.d', straw_under)}),
        cube([-6, 34, -6], [12, 1, 12], {**same('hat1', straw_side, ('north', 'south', 'east', 'west')),
                                         'up': ('hat1.u', straw_up)}),
        cube([-4.5, 35, -4.5], [9, 1, 9], {**same('hat2', straw_side, ('north', 'south', 'east', 'west')),
                                           'up': ('hat2.u', straw_up)}),
        cube([-3, 36, -3], [6, 1, 6], {**same('hat3', straw_side, ('north', 'south', 'east', 'west')),
                                       'up': ('hat3.u', straw_up)}),
        cube([-1.5, 37, -1.5], [3, 1, 3], {**same('hat4', straw_side, ('north', 'south', 'east', 'west')),
                                           'up': ('hat4.u', straw_up)}),
        cube([-0.5, 38, -0.5], [1, 0.75, 1], same('hat5', lambda u, v, w, h: STRAW_D)),
        cube([-4.25, 32.5, -4.25], [8.5, 0.5, 8.5], same('band', lambda u, v, w, h: CORD,
                                                         ('north', 'south', 'east', 'west'))),
    ]
    nose = [cube([-1, 23, -6], [2, 4, 2], {
        'north': ('nose.n', NOSE_FRONT), 'west': ('nose.w', nose_side(False)), 'east': ('nose.e', nose_side(True)),
        'up': ('nose.u', lambda u, v, w, h: NOSE_TOP), 'down': ('nose.d', lambda u, v, w, h: NOSE_UNDER)})]
    body = [
        cube([-4, 12, -3], [8, 12, 6], {'up': ('torso.u', jacket_top)}),           # under the coat
        cube([-4, 6, -3], [8, 18, 6], {
            'north': ('coat.n', coat(1, front=True)), 'south': ('coat.s', coat(2, back=True)),
            'west': ('coat.w', coat(3, side=True)), 'east': ('coat.e', coat(4, side=True)),
            'up': ('coat.u', jacket_top), 'down': ('coat.d', lambda u, v, w, h: J_IN)}, inflate=0.5),
        cube([-4, 13.2, -3], [8, 0.6, 6], same('belt', rope), inflate=0.75),            # rope belt
        cube([1, 12.6, -4.45], [1.5, 1.5, 0.8], same('knot', rope)),                # knot
        cube([1.4, 10.4, -4.25], [0.7, 2.4, 0.6], same('rope_end', rope)),          # loose end
    ]
    arms = [
        cube([-4, 16, -2], [8, 4, 4], {'north': ('fore.n', forearm_front), 'up': ('fore.u', sleeve(11)),
                                       'down': ('fore.d', forearm_under), 'south': ('fore.s', sleeve(12))}),
        cube([-8, 16, -2], [4, 8, 4], same('arm_r', upper_arm)),
        cube([4, 16, -2], [4, 8, 4], same('arm_l', upper_arm)),
    ]
    leg = {**same('leg', pants, ('north', 'south', 'east', 'west')), 'up': ('leg.u', pants), 'down': ('leg.d', sole)}

    # the pole rests on the top edge of the right upper arm, flush with its outer face
    arm_top = max(rot_x([x, y, z], [0, 22, 0], ARMS_TILT)[1] for x in (-8, -4) for y in (16, 24) for z in (-2, 2))
    py = round(math.ceil(arm_top * 20) / 20, 2)
    pole = [cube([-8, py, -14.5], [1, 1, 29], {
        'east': ('pole.e', bamboo_long), 'west': ('pole.w', bamboo_long), 'up': ('pole.u', bamboo_long),
        'down': ('pole.d', bamboo_long), 'north': ('pole.end', lambda u, v, w, h: BAMBOO_END),
        'south': ('pole.end', lambda u, v, w, h: BAMBOO_END)})]

    def basket(zc, fishes):
        rl = py - 17
        cubes = [
            cube([PX - 0.25, 17, zc - 0.25], [0.5, rl, 0.5], same('cord', lambda u, v, w, h: ROPE_B if v % 2 else ROPE_A,
                                                               ('north', 'south', 'east', 'west'))),
            cube([PX - 3, 12, zc - 3], [6, 5, 6], {**same('basket', weave, ('north', 'south', 'east', 'west')),
                                                 'up': ('basket.u', basket_top),
                                                 'down': ('basket.d', lambda u, v, w, h: WEAVE_D)}),
        ]
        for (x, z, w, hgt, kind) in fishes:
            cubes.append(cube([x + PX + 6.5, 17, z], [w, hgt, w], {
                **{f: (f'fish{kind}{w}{hgt}.{f}', fish_side(kind)) for f in ('north', 'south', 'east', 'west')},
                'up': (f'fish{kind}{w}.u', fish_end(kind))}))
        return cubes

    bones = [
        {'name': 'root', 'pivot': [0, 0, 0]},
        {'name': 'body', 'parent': 'root', 'pivot': [0, 24, 0], 'cubes': body},
        {'name': 'head', 'parent': 'body', 'pivot': [0, 24, 0], 'cubes': head},
        {'name': 'nose', 'parent': 'head', 'pivot': [0, 26, 0], 'cubes': nose},
        {'name': 'arms', 'parent': 'body', 'pivot': [0, 22, 0], 'rotation': [ARMS_TILT, 0, 0], 'cubes': arms},
        {'name': 'leg_r', 'parent': 'root', 'pivot': [-2, 12, 0], 'cubes': [cube([-4, 0, -2], [4, 12, 4], leg)]},
        {'name': 'leg_l', 'parent': 'root', 'pivot': [2, 12, 0], 'cubes': [cube([0, 0, -2], [4, 12, 4], leg)]},
        {'name': 'pole', 'parent': 'body', 'pivot': [-6.5, 24.5, 0], 'cubes': pole},
        {'name': 'basket_f', 'parent': 'pole', 'pivot': [PX, py, -12.5],
         'cubes': basket(-12.5, [(-6, -14, 1.5, 3, 's'), (-8.5, -12.5, 1.5, 2.5, 'o'), (-6.5, -11.5, 1, 1.5, 's')])},
        {'name': 'basket_b', 'parent': 'pole', 'pivot': [PX, py, 12.5],
         'cubes': basket(12.5, [(-8.5, 12.5, 1.5, 3, 's'), (-6, 10.5, 1.5, 2, 'o'), (-8.5, 10.5, 1, 1.5, 'o')])},
    ]
    pack()
    resolve(bones)
    return {'format_version': '1.16.0', 'minecraft:geometry': [{
        'description': {'identifier': 'geometry.kaleidoscope_fishing.fish_merchant', 'texture_width': TW,
                        'texture_height': TH, 'visible_bounds_width': 3, 'visible_bounds_height': 3,
                        'visible_bounds_offset': [0, 1.25, 0]},
        'bones': bones}]}


def paint():
    im = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
    px = im.load()
    for key, (w, h, fn, (u0, v0)) in regions.items():
        for v in range(h):
            for u in range(w):
                c = fn(u, v, w, h)
                if c:
                    px[u0 + u, v0 + v] = hexc(c)
    return im


def main():
    geo = geometry()
    path = os.path.join(RP, 'models', 'entity', 'fish_merchant.geo.json')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(geo, f, indent=2)
    tex = os.path.join(RP, 'textures', 'entity', 'kfv_fish_merchant.png')
    paint().save(tex)
    n = sum(len(b.get('cubes', [])) for b in geo['minecraft:geometry'][0]['bones'])
    print('cubes', n, 'regions', len(regions), 'wrote', path, tex, *pbr.refresh(tex))


if __name__ == '__main__':
    main()
