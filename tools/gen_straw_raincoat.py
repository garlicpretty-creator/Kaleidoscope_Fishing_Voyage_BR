"""Rebuild the straw raincoat (蓑衣): worn model, held model and texture.

usage: python tools/gen_straw_raincoat.py

Worn: four overlapping straw tiers on the body that flare outwards towards the hem, each with a ragged fringe
(transparent gaps; the attachable uses entity_alphatest), a straw collar, a rope tie at the waist, and two
shoulder flaps on each arm. Held: the coat folded into a bundle and tied with rope.
Bone names and pivots match the player rig (body / leftArm / rightArm / rightItem), as before.
"""
import json, os, random, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
TW = TH = 64

# texture regions (u0, v0, w, h)
TIER = [(0, 0, 16, 6), (16, 0, 16, 6), (32, 0, 16, 6), (48, 0, 16, 6)]   # straw panels of the body tiers
ARMT = [(0, 6, 8, 7), (8, 6, 8, 7)]                                         # arm flap panels
TOP = (16, 6, 16, 8)            # tops of tiers (straw laid flat)
UNDER = (32, 6, 16, 8)          # undersides (shadowed straw)
ROPE = (48, 6, 16, 2)
COLLAR = (48, 8, 16, 3)
ROPE_WIDE = (48, 11, 16, 4)     # rope for faces taller than 2 (held bundle ties, knot ends)
FOLD = (0, 14, 16, 6)           # folded bundle sides
CLEAR = (62, 62, 1, 1)          # left transparent: hides the thin bottom edge of straw panels
SCALE = 2                       # png is drawn at 2x the model's UV space for finer straw

RIG = [
    {'name': 'root', 'pivot': [0, 0, 0]},
    {'name': 'waist', 'parent': 'root', 'pivot': [0, 12, 0]},
    {'name': 'body', 'parent': 'waist', 'pivot': [0, 24, 0]},
    {'name': 'head', 'parent': 'body', 'pivot': [0, 24, 0]},
    {'name': 'leftArm', 'parent': 'body', 'pivot': [5, 22, 0]},
    {'name': 'rightArm', 'parent': 'body', 'pivot': [-5, 22, 0]},
    {'name': 'rightItem', 'parent': 'rightArm', 'pivot': [-6, 15, 1]},
]


def face_tile(region):
    def uv(face, size):
        w, h, d = size
        fw, fh = {'north': (w, h), 'south': (w, h), 'east': (d, h), 'west': (d, h),
                  'up': (w, d), 'down': (w, d)}[face]
        return {'uv': [region[0], region[1]], 'uv_size': [round(min(fw, region[2]), 3), round(min(fh, region[3]), 3)]}
    return uv


def cube(origin, size, sides, top=TOP, bottom=UNDER):
    return _cube(origin, size, sides, top, bottom)


def _cube(origin, size, sides, top=TOP, bottom=UNDER):
    faces = {}
    for f in ('north', 'south', 'east', 'west'):
        faces[f] = face_tile(sides)(f, size)
    faces['up'] = face_tile(top)('up', size)
    faces['down'] = face_tile(bottom)('down', size)
    return {'origin': [round(v, 3) for v in origin], 'size': [round(v, 3) for v in size], 'uv': faces}


def panel_tier(cubes, y_top, h, w, d, region, flare, back=True):
    """Four thin straw panels hinged at the top edge and tilted outwards (a skirt that flares).
    Their bottom faces map to a transparent texel so only the ragged fringe shows at the hem."""
    t = 0.5
    cube = lambda o, sz, reg: _cube(o, sz, reg, bottom=CLEAR)
    cubes.append(dict(cube([-w / 2, y_top - h, -d / 2 - t], [w, h, t], region), rotation=[-flare, 0, 0],
                      pivot=[0, y_top, -d / 2]))
    if back:
        cubes.append(dict(cube([-w / 2, y_top - h, d / 2], [w, h, t], region), rotation=[flare, 0, 0],
                          pivot=[0, y_top, d / 2]))
    cubes.append(dict(cube([w / 2, y_top - h, -d / 2 - t], [t, h, d + 2 * t], region), rotation=[0, 0, flare],
                      pivot=[w / 2, y_top, 0]))
    cubes.append(dict(cube([-w / 2 - t, y_top - h, -d / 2 - t], [t, h, d + 2 * t], region), rotation=[0, 0, -flare],
                      pivot=[-w / 2, y_top, 0]))


def worn():
    body, left, right = [], [], []
    # tiers top to bottom: (top edge y, height, width, depth, flare in degrees); each hangs over the next
    tiers = [(24.2, 5.4, 9.0, 4.8, 22), (20.6, 5.6, 9.6, 5.2, 16), (16.4, 5.6, 10.2, 5.6, 13), (12.4, 5.8, 10.6, 6.0, 11)]
    for k, (y, h, w, d, fl) in enumerate(tiers):
        panel_tier(body, y, h, w, d, TIER[k], fl)
    body.append(cube([-4.6, 23.0, -2.6], [9.2, 1.4, 5.2], COLLAR, top=TOP, bottom=UNDER))     # collar
    body.append(cube([-5.6, 15.9, -3.6], [11.2, 0.7, 7.2], ROPE, top=UNDER, bottom=UNDER))          # waist rope, over the seam
    body.append(cube([-1.1, 14.2, -3.9], [0.7, 1.8, 0.3], ROPE_WIDE, top=ROPE, bottom=ROPE))           # knot ends hanging in front
    body.append(cube([0.3, 13.8, -3.9], [0.7, 2.2, 0.3], ROPE_WIDE, top=ROPE, bottom=ROPE))
    for sgn, bone in ((1, left), (-1, right)):
        # shoulder flaps: an outer panel and front/back panels over the upper arm, tilted out
        cx = 6 * sgn
        bone.append(dict(cube([cx + (2.2 if sgn > 0 else -2.7), 17.6, -2.6], [0.5, 6.6, 5.2], ARMT[0]),
                         rotation=[0, 0, 16 * sgn], pivot=[cx + 2.2 * sgn, 24.2, 0]))
        for zs in (-1, 1):
            bone.append(dict(cube([cx - 2.3, 18.6, (-2.6 if zs < 0 else 2.1)], [4.6, 5.6, 0.5], ARMT[1]),
                             rotation=[14 * zs, 0, 0], pivot=[cx, 24.2, 2.35 * zs]))
        bone.append(cube([cx - 2.4, 23.6, -2.4], [4.8, 0.6, 4.8], TOP))
    bones = [dict(b) for b in RIG]
    bones.append({'name': 'kfv_coat', 'parent': 'body', 'pivot': [0, 24, 0], 'cubes': body})
    bones.append({'name': 'kfv_coat_l', 'parent': 'leftArm', 'pivot': [5, 22, 0], 'cubes': left})
    bones.append({'name': 'kfv_coat_r', 'parent': 'rightArm', 'pivot': [-5, 22, 0], 'cubes': right})
    return bones


def held():
    cubes = [cube([-9, 10, -2], [6, 1.5, 6], FOLD, top=TOP),
             cube([-8.75, 11.5, -1.75], [5.5, 1.5, 5.5], FOLD, top=TOP),
             cube([-8.5, 13, -1.5], [5, 1.2, 5], FOLD, top=TOP),
             cube([-9.1, 10.6, 0.6], [6.2, 3.8, 0.6], ROPE_WIDE, top=ROPE, bottom=ROPE),       # rope round the bundle
             cube([-6.6, 10.6, -2.1], [0.6, 3.8, 6.2], ROPE_WIDE, top=ROPE, bottom=ROPE_WIDE)]
    bones = [dict(b) for b in RIG]
    bones.append({'name': 'kfv_held', 'parent': 'rightItem', 'pivot': [-6, 15, 1], 'cubes': cubes})
    return bones


def hexc(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


STRAW = [hexc(c) for c in ('#5a4318', '#7a5c22', '#97752e', '#b4913c', '#ccab52', '#e0c470')]


def paint():
    rnd = random.Random(7)
    im = Image.new('RGBA', (TW * SCALE, TH * SCALE), (0, 0, 0, 0))
    px = im.load()

    def strands(region, shade, hem=True):
        u0, v0, w, h = (c * SCALE for c in region)
        for u in range(w):
            base = max(1, min(5, rnd.randint(1, 5) + shade))
            hem_len = rnd.choice((0, 1, 2, 2, 3, 4)) if hem else 0
            for v in range(h):
                if hem and v >= h - hem_len:
                    continue                                   # ragged fringe
                c = base
                if v < 2:
                    c -= 1                                     # shadow under the tier above
                if (u + v * 5) % 11 == 0:
                    c -= 1                                     # knots / breaks in the straw
                if hem and v == h - hem_len - 1:
                    c -= 1                                     # strand tip
                px[u0 + u, v0 + v] = STRAW[max(0, min(5, c))]
    for k, reg in enumerate(TIER):
        strands(reg, -(k // 2))
    for reg in ARMT:
        strands(reg, 0)
    strands(FOLD, 0, hem=False)

    def fill(region, fn):
        u0, v0, w, h = (c * SCALE for c in region)
        for v in range(h):
            for u in range(w):
                px[u0 + u, v0 + v] = fn(u, v)
    fill(TOP, lambda u, v: STRAW[2 + ((u * 3 + v) % 5 == 0) + ((u + v) % 4 == 0)])
    fill(UNDER, lambda u, v: STRAW[(u + v) % 2])
    fill(ROPE, lambda u, v: hexc('#4a3a28') if (u + v) % 2 else hexc('#6e5a3e'))
    fill(ROPE_WIDE, lambda u, v: hexc('#4a3a28') if (u + v) % 2 else hexc('#6e5a3e'))
    fill(COLLAR, lambda u, v: STRAW[max(0, min(5, 4 - v // 2 + (u % 3 == 0)))])
    return im


def main():
    geos = []
    for ident, bones in (('geometry.kaleidoscope_fishing.straw_raincoat', worn()),
                         ('geometry.kaleidoscope_fishing.straw_raincoat_held', held())):
        geos.append({'description': {'identifier': ident, 'texture_width': TW, 'texture_height': TH,
                                     'visible_bounds_width': 3, 'visible_bounds_height': 3,
                                     'visible_bounds_offset': [0, 1.5, 0]}, 'bones': bones})
    with open(os.path.join(RP, 'models', 'entity', 'straw_raincoat.geo.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'format_version': '1.12.0', 'minecraft:geometry': geos}, f, indent=1)
    tex = os.path.join(RP, 'textures', 'entity', 'kfv_straw_raincoat.png')
    paint().save(tex)
    pbr.refresh(tex)
    print('worn cubes', sum(len(b.get('cubes', [])) for b in geos[0]['bones']),
          'held cubes', sum(len(b.get('cubes', [])) for b in geos[1]['bones']))


if __name__ == '__main__':
    main()
