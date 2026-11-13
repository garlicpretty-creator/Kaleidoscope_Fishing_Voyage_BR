"""Rebuild the whole-tuna and emperor-tuna feast blocks: geometry for all 12 states each, plus painted textures.

usage: python tools/gen_whole_tuna.py

The feast is three blocks long (part 0 head, 1 body, 2 tail) and has four eating stages
(0 whole, 1 top fillet cut away, 2 cut down to the last layer, 3 bare skeleton). The fish lies on its side
along +z: its back (dark blue) faces -x, its belly (silver) +x, and its flank faces up.
Global length L runs 0..48 along the three blocks (L = z + 8 + 16 * part).

Every face's UV follows world position (texture u from x, v from L or height), so the painted gradient,
lateral line, scales and meat stripes run continuously across cubes and across the three blocks.
Geometry identifiers are kept: geometry.kaleidoscope_fishing.<name>_<part>_<stage>.
"""
import json, math, os, random, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
TW = TH = 128

# ------------------------------------------------------------------ texture layout (u0, v0, w, h)
FLANK = (0, 0, 24, 48)       # up faces of the fish: u = x + 12, v = L
DORS = (0, 48, 48, 8)        # -x faces (back edge):   u = L, v = 8 - y
BELLY = (48, 48, 48, 8)      # +x faces (belly edge)
CROSS = (40, 0, 24, 8)       # +-z faces of skin:  u = x + 12, v = 8 - y
MEAT = (64, 0, 24, 48)       # cut surface seen from above: u = x + 12, v = L
MEATX = (88, 0, 24, 8)       # cut surface seen from the side
BONE = (112, 0, 8, 8)
WOOD = (0, 64, 16, 16)
WOODS = (16, 64, 16, 4)
LEAF = (32, 64, 16, 16)
EYE = (48, 64, 4, 4)
FIN = (56, 64, 8, 8)
FINLET = (64, 64, 4, 4)
TAIL = (72, 64, 16, 16)

# ------------------------------------------------------------------ fish shape
def H(L):
    """Back-to-belly height of the fish at L (x extent)."""
    if L < 10:
        return 4 + 7 * math.sin(min(1, max(0, L / 10)) * math.pi / 2)
    if L < 30:
        return 11
    if L < 40:
        return 11 - 8 * (L - 30) / 10
    return 3


def T(L):
    """Thickness of the fish at L (y extent above the board)."""
    if L < 10:
        return 2.5 + 3.5 * math.sin(min(1, max(0, L / 10)) * math.pi / 2)
    if L < 30:
        return 6
    if L < 40:
        return 6 - 4 * (L - 30) / 10
    return 2


BOARD_Y = 1.0
CUT = {1: 0.55, 2: 0.25}            # eating stage -> fraction of thickness left
EATEN = (10, 38)                    # L range that gets eaten; head and tail stay


# ------------------------------------------------------------------ UV helpers
def region_face(region, face, box, mu, mv):
    """UV for one face, mapping world coordinates into `region` with mu/mv (functions of the face's
    left/right and top/bottom world edges). Orientation of Bedrock faces seen from outside:
      up    left x1 right x0, top z0 bottom z1        down  left x1 right x0, top z1 bottom z0
      north left x1 right x0, top y1 bottom y0        south left x0 right x1
      east  left z1 right z0                          west  left z0 right z1"""
    (x0, y0, z0), (x1, y1, z1) = box
    edges = {'up': ((x1, x0), (z0, z1)), 'down': ((x1, x0), (z1, z0)),
             'north': ((x1, x0), (y1, y0)), 'south': ((x0, x1), (y1, y0)),
             'east': ((z1, z0), (y1, y0)), 'west': ((z0, z1), (y1, y0))}
    (ul, ur), (vt, vb) = edges[face]
    u_a, u_b = mu(ul), mu(ur); v_a, v_b = mv(vt), mv(vb)
    return {'uv': [round(region[0] + u_a, 4), round(region[1] + v_a, 4)],
            'uv_size': [round(u_b - u_a, 4), round(v_b - v_a, 4)]}


def tile(region):
    """Small tile: each face maps the start of the region at its own extent (clamped to the region)."""
    def f(face, box):
        (x0, y0, z0), (x1, y1, z1) = box
        dims = {'up': (x1 - x0, z1 - z0), 'down': (x1 - x0, z1 - z0), 'north': (x1 - x0, y1 - y0),
                'south': (x1 - x0, y1 - y0), 'east': (z1 - z0, y1 - y0), 'west': (z1 - z0, y1 - y0)}[face]
        w, h = min(dims[0], region[2]), min(dims[1], region[3])
        return {'uv': [region[0], region[1]], 'uv_size': [round(w, 4), round(h, 4)]}
    return f


class Part:
    def __init__(self, part):
        self.part = part; self.cubes = []

    def zl(self, L):                       # global L -> local z
        return L - 8 - 16 * self.part

    def add(self, lo, hi, faces, rotation=None, pivot=None):
        box = (lo, hi)
        uv = {f: fn(f, box) for f, fn in faces.items()}
        c = {'origin': [round(v, 4) for v in lo], 'size': [round(hi[i] - lo[i], 4) for i in range(3)], 'uv': uv}
        if rotation:
            c['rotation'] = rotation; c['pivot'] = pivot
        self.cubes.append(c)


def skin_faces(part, top_meat=False, end_meat=()):
    """Faces for a slab of fish: flank (or meat) on top, back/belly edges on the sides, cross-section ends."""
    L_of = lambda z: z + 8 + 16 * part.part
    up_region = MEAT if top_meat else FLANK
    f = {'up': lambda face, box: region_face(up_region, face, box, lambda x: x + 12, L_of),
         'west': lambda face, box: region_face(DORS, face, box, L_of, lambda y: 8 - y),
         'east': lambda face, box: region_face(BELLY, face, box, L_of, lambda y: 8 - y)}
    for face in ('north', 'south'):
        reg = MEATX if face in end_meat else CROSS
        f[face] = (lambda reg: lambda face, box: region_face(reg, face, box, lambda x: x + 12, lambda y: 8 - y))(reg)
    return f


# ------------------------------------------------------------------ build one state
def build(part_no, stage):
    p = Part(part_no)
    zmin = -7 if part_no == 0 else -8
    zmax = 7 if part_no == 2 else 8
    # board, with bamboo-leaf garnish rims along both long edges
    p.add([-7, 0, zmin], [7, BOARD_Y, zmax], {
        'up': lambda f, b: region_face(WOOD, f, b, lambda x: x + 8, lambda z: z + 8),
        'down': tile(WOOD), 'north': tile(WOODS), 'south': tile(WOODS), 'east': tile(WOODS), 'west': tile(WOODS)})
    for x0 in (-7, 5.5):
        p.add([x0, BOARD_Y, zmin], [x0 + 1.5, BOARD_Y + 0.5, zmax], {
            'up': tile(LEAF), 'north': tile(LEAF), 'south': tile(LEAF), 'east': tile(LEAF), 'west': tile(LEAF)})
    Lmin, Lmax = 16 * part_no, 16 * part_no + 16
    # body, in 2-long chunks of stacked slabs (a rounded cross-section)
    for La in range(0, 40, 2):
        Lb = La + 2
        if Lb <= Lmin or La >= Lmax:
            continue
        Lm = (La + Lb) / 2
        h, t = H(Lm), T(Lm)
        eaten = EATEN[0] <= La and Lb <= EATEN[1]
        if stage == 3 and eaten:
            continue
        top_cap = BOARD_Y + t
        if stage in CUT and eaten:
            top_cap = BOARD_Y + max(0.5, t * CUT[stage])
        # slabs: lower half full width, upper half narrowing
        layers = [(0.0, 0.5, 1.0), (0.5, 0.7, 0.92), (0.7, 0.85, 0.78), (0.85, 1.0, 0.55)]
        end_meat = ()
        if stage in (1, 2, 3):
            if La == EATEN[0] - 2:
                end_meat = ('south',)      # head chunk facing the eaten part (+z)
            if Lb == EATEN[1] + 2:
                end_meat = ('north',)
        for k, (fa, fb, wf) in enumerate(layers):
            ya, yb = BOARD_Y + t * fa, BOARD_Y + t * fb
            if ya >= top_cap - 1e-6:
                break
            cut_here = yb > top_cap + 1e-6
            yb = min(yb, top_cap)
            w = h * wf
            x0, x1 = -w / 2, w / 2
            p.add([x0, ya, p.zl(La)], [x1, yb, p.zl(Lb)], skin_faces(p, top_meat=cut_here, end_meat=end_meat))
    # skeleton for the bare stage: spine and ribs
    if stage == 3:
        a, b = max(EATEN[0], Lmin), min(EATEN[1], Lmax)
        if a < b:
            p.add([-0.75, BOARD_Y, p.zl(a)], [0.75, BOARD_Y + 1.5, p.zl(b)], {f: tile(BONE) for f in
                  ('up', 'north', 'south', 'east', 'west')})
            for L in range(11, 38, 3):
                if a <= L < b:
                    hw = H(L) / 2 - 1
                    p.add([-hw, BOARD_Y, p.zl(L)], [hw, BOARD_Y + 0.6, p.zl(L + 0.75)],
                          {f: tile(BONE) for f in ('up', 'north', 'south', 'east', 'west')})
    # head: eye on the flank, near the back
    if part_no == 0:
        ty = BOARD_Y + T(5)
        p.add([-2.6, ty - 0.1, p.zl(4)], [-0.6, ty + 0.25, p.zl(6)], {
            'up': lambda f, b: region_face(EYE, f, b, lambda x: (x + 2.6) * 2, lambda z: (z - p.zl(4)) * 2),
            'north': tile(FIN), 'south': tile(FIN), 'east': tile(FIN), 'west': tile(FIN)})
    # fins (lying flat, the fish is on its side): first and second dorsal on the back, anal on the belly,
    # a long pectoral fin on the flank, yellow finlets on both edges towards the tail. Fins inside the eaten
    # stretch go once the meat is cut; edge fins sit low enough to stay attached to what is left.
    def eaten_at(L):
        return stage >= 1 and EATEN[0] <= L < EATEN[1]

    def fin_y(L):
        t = T(L)
        if eaten_at(L) and stage in CUT:
            t = max(0.5, t * CUT[stage]) * 2
        return BOARD_Y + t * 0.5

    for (fa, fb), side, reach in (((13, 19), -1, 2.2), ((24, 27.5), -1, 3.2), ((25, 28.5), 1, 3.0)):
        La, Lb = max(fa, Lmin), min(fb, Lmax)
        if La >= Lb or (stage == 3 and eaten_at(fa)):
            continue
        edge = H((fa + fb) / 2) / 2
        y = fin_y((fa + fb) / 2)
        n = 3                                           # swept-back steps: each step reaches further, is shorter
        for k in range(n):
            ra, rb = reach * k / n, reach * (k + 1) / n
            sa = fa + (fb - fa) * 0.45 * k / n          # leading edge slopes back
            sb = fb - (fb - fa) * 0.2 * k / n
            sa, sb = max(sa, Lmin), min(sb, Lmax)
            if sa >= sb:
                continue
            x0, x1 = (-edge - rb, -edge - ra) if side < 0 else (edge + ra, edge + rb)
            p.add([x0, y - 0.25, p.zl(sa)], [x1, y + 0.25, p.zl(sb)], {f: tile(FIN) for f in
                  ('up', 'down', 'north', 'south', 'east', 'west')})
    pa, pb = max(11, Lmin), min(20, Lmax)
    if pa < pb and stage == 0:
        ty = BOARD_Y + T(15)
        p.add([-2.8, ty, p.zl(pa)], [-1.2, ty + 0.3, p.zl(pb)], {f: tile(FIN) for f in
              ('up', 'north', 'south', 'east', 'west')})
    for L in (30, 32, 34, 36, 38):
        if Lmin <= L < Lmax and not (stage == 3 and eaten_at(L)):
            edge = H(L + 0.5) / 2
            y = fin_y(L)
            for x0, x1 in ((-edge - 1, -edge), (edge, edge + 1)):
                p.add([x0, y - 0.25, p.zl(L)], [x1, y + 0.25, p.zl(L + 1)], {f: tile(FINLET) for f in
                      ('up', 'down', 'north', 'south', 'east', 'west')})
    # tail: forked crescent, two lobes swept back from the peduncle
    if part_no == 2:
        ty = BOARD_Y + 0.75
        for sgn in (-1, 1):
            p.add([-0.9, ty, p.zl(40.5)], [0.9, ty + 0.5, p.zl(40.5) + 8.2], {
                'up': tile(TAIL), 'down': tile(TAIL), 'north': tile(FIN), 'south': tile(FIN), 'east': tile(FIN), 'west': tile(FIN)},
                rotation=[0, -50 * sgn, 0], pivot=[0, ty, p.zl(40.5)])
        p.add([-1.5, BOARD_Y, p.zl(40)], [1.5, BOARD_Y + 1.5, p.zl(42)], skin_faces(p))
    return p.cubes


# ------------------------------------------------------------------ textures
def hexc(h, a=255):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (a,)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def ramp(cols, t):
    t = max(0.0, min(1.0, t)) * (len(cols) - 1)
    i = min(len(cols) - 2, int(t))
    return lerp(cols[i], cols[i + 1], t - i)


PALETTES = {
    'whole_tuna': {
        'skin': ['#0f1838', '#1c2c5c', '#2e4a86', '#5a7aa8', '#a9b8c8', '#dfe5ea', '#f4f6f6'],
        'lateral': '#8fb0d0', 'gill': '#0b1230', 'fin': ['#14204a', '#2a3e74', '#4a628f'],
        'finlet': ['#c99a12', '#f0c43a', '#fde58a'], 'accent': None,
        'meat': ['#7a1420', '#a81e2c', '#c8303c', '#d8505a'], 'toro': ['#e48a8e', '#f2b6b4'], 'fat': '#f6d8d0'},
    'emperor_whole_tuna': {
        'skin': ['#0a1240', '#14267a', '#2244b0', '#4a74d0', '#a8c0e4', '#e2ecf6', '#fbfcff'],
        'lateral': '#f2c94a', 'gill': '#d8a420', 'fin': ['#0e1a5a', '#2040a0', '#e0b030'],
        'finlet': ['#d49a0c', '#ffd24a', '#fff2a8'], 'accent': '#f2c94a',
        'meat': ['#86101e', '#b81a2a', '#d42c3a', '#e04c58'], 'toro': ['#ec9298', '#f8c4c0'], 'fat': '#fae2da'},
}


def paint(name):
    pal = PALETTES[name]
    rnd = random.Random(name)
    im = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
    px = im.load()
    skin = [hexc(c) for c in pal['skin']]

    def skin_at(x, L, scales=True):
        h = H(L)
        rel = max(0.0, min(1.0, (x + h / 2) / h))  # 0 back .. 1 belly
        c = ramp(skin, rel ** 0.9)
        if scales and (int(L) + int((x + 12) // 1)) % 2 == 0 and 0.15 < rel < 0.85:
            c = lerp(c, (0, 0, 0), 0.08)
        if abs(rel - 0.42) < 0.05 and L > 9:       # lateral line
            c = lerp(c, hexc(pal['lateral']), 0.55)
        return c

    # flank: back->belly gradient, lateral line, scale dither, gill line and snout on the head
    u0, v0, w, h = FLANK
    for v in range(h):
        L = v + 0.5
        for u in range(w):
            x = u - 12 + 0.5
            if abs(x) > H(L) / 2 + 0.6:
                continue
            c = skin_at(x, L)
            gl = 8.5 + 1.2 * (1 - abs((x / (H(L) / 2 + 1e-6))) ** 2)
            if abs(L - gl) < 0.6:
                c = lerp(c, hexc(pal['gill']), 0.75)
            if L < 1.5:
                c = lerp(c, hexc(pal['gill']), 0.5)
            if 3 < L < 8 and abs(x - 1.5) < 0.6:    # mouth line along the lower jaw
                c = lerp(c, hexc(pal['gill']), 0.4)
            px[u0 + u, v0 + v] = c
    # back and belly edges (u along L wrapped to 8, v height): dark back, silver belly
    for (u0, v0, w, hh), cols in ((DORS, [skin[1], skin[0], skin[0]]), (BELLY, [skin[6], skin[5], skin[4]])):
        for v in range(hh):
            for u in range(w):
                c = ramp(cols, v / (hh - 1))
                if (u + v) % 3 == 0:
                    c = lerp(c, (0, 0, 0), 0.07)
                px[u0 + u, v0 + v] = c
    # cross-section ends of skin slabs
    u0, v0, w, hh = CROSS
    for v in range(hh):
        for u in range(w):
            px[u0 + u, v0 + v] = ramp(skin, u / (w - 1))
    # meat from above: red akami, pink toro towards the belly, pale fat lines (myosepta), skin rim
    meat = [hexc(c) for c in pal['meat']]; toro = [hexc(c) for c in pal['toro']]
    u0, v0, w, h = MEAT
    for v in range(h):
        L = v + 0.5
        for u in range(w):
            x = u - 12 + 0.5
            hh_ = H(L) / 2
            if abs(x) > hh_ + 0.6:
                continue
            rel = (x + hh_) / (2 * hh_)
            if rel < 0.08:
                c = skin[1]
            elif rel > 0.92:
                c = skin[5]
            else:
                c = ramp(meat, 0.4 + 0.5 * abs(rel - 0.45) * 2 * 0.5 + rnd.random() * 0.25)
                if rel > 0.62:
                    c = lerp(c, ramp(toro, (rel - 0.62) / 0.3), 0.75)
                ph = (L + 3.0 * abs(rel - 0.45) * 2) % 4.0     # chevron-shaped fat lines
                if ph < 0.7:
                    c = lerp(c, hexc(pal['fat']), 0.55)
                if abs(rel - 0.45) < 0.04:
                    c = lerp(c, meat[0], 0.5)                  # dark blood line down the middle
            px[u0 + u, v0 + v] = c
    u0, v0, w, hh = MEATX
    for v in range(hh):
        for u in range(w):
            rel = u / (w - 1)
            c = ramp(meat, 0.5 + rnd.random() * 0.3)
            if rel > 0.62:
                c = lerp(c, ramp(toro, (rel - 0.62) / 0.3), 0.7)
            if v % 3 == 0:
                c = lerp(c, hexc(pal['fat']), 0.35)
            px[u0 + u, v0 + v] = c
    # bone
    u0, v0, w, hh = BONE
    for v in range(hh):
        for u in range(w):
            c = hexc('#f2ead6') if (u + v) % 4 else hexc('#ddd2b8')
            if v == hh - 1 or u == w - 1:
                c = hexc('#c8bc9e')
            px[u0 + u, v0 + v] = c
    # wood board: planks along the fish
    u0, v0, w, hh = WOOD
    plank = [hexc('#7a4a24'), hexc('#8e5a2c'), hexc('#a46c36'), hexc('#b67d42')]
    for v in range(hh):
        for u in range(w):
            c = plank[(u // 4 + (1 if (v * 7 + u // 4 * 3) % 11 == 0 else 0)) % 4]
            if u % 4 == 0:
                c = lerp(c, (0, 0, 0), 0.3)
            if (v + u * 5) % 9 == 0:
                c = lerp(c, (0, 0, 0), 0.12)
            px[u0 + u, v0 + v] = c
    u0, v0, w, hh = WOODS
    for v in range(hh):
        for u in range(w):
            px[u0 + u, v0 + v] = lerp(plank[1], (0, 0, 0), 0.15 + 0.1 * (v == hh - 1))
    # bamboo leaf garnish
    u0, v0, w, hh = LEAF
    greens = [hexc('#2f5a1c'), hexc('#3f7a24'), hexc('#5a9a32'), hexc('#7cba4a')]
    for v in range(hh):
        for u in range(w):
            c = greens[1 + (u % 4 == 1) + (u % 4 == 2) * 0]
            if u % 4 == 0:
                c = greens[0]
            if u % 4 == 2 and v % 5 == 0:
                c = greens[3]
            px[u0 + u, v0 + v] = c
    # eye: pale ring, dark pupil, highlight
    u0, v0, w, hh = EYE
    ring = hexc('#d8dee4') if pal['accent'] is None else hexc(pal['accent'])
    for v in range(4):
        for u in range(4):
            px[u0 + u, v0 + v] = ring
    for (u, v) in ((1, 1), (2, 1), (1, 2), (2, 2)):
        px[u0 + u, v0 + v] = hexc('#0a0a10')
    px[u0 + 1, v0 + 1] = hexc('#ffffff')
    # fins with rays
    fin = [hexc(c) for c in pal['fin']]
    u0, v0, w, hh = FIN
    for v in range(hh):
        for u in range(w):
            c = fin[0] if u % 2 == 0 else fin[1]
            if v == 0:
                c = fin[2]
            px[u0 + u, v0 + v] = c
    u0, v0, w, hh = FINLET
    fl = [hexc(c) for c in pal['finlet']]
    for v in range(hh):
        for u in range(w):
            px[u0 + u, v0 + v] = fl[1] if (u + v) % 3 else fl[0]
    px[u0, v0] = fl[2]
    # tail fin: dark with rays and a pale trailing edge
    u0, v0, w, hh = TAIL
    for v in range(hh):
        for u in range(w):
            c = fin[0] if u % 2 else fin[1]
            if v >= hh - 2:
                c = fin[2]
            px[u0 + u, v0 + v] = c
    return im


def main():
    for name in ('whole_tuna', 'emperor_whole_tuna'):
        geos = []
        for part in range(3):
            for stage in range(4):
                geos.append({'description': {'identifier': f'geometry.kaleidoscope_fishing.{name}_{part}_{stage}',
                                             'texture_width': TW, 'texture_height': TH,
                                             'visible_bounds_width': 3, 'visible_bounds_height': 2,
                                             'visible_bounds_offset': [0, 0.5, 0]},
                             'bones': [{'name': 'root', 'pivot': [0, 0, 0], 'cubes': build(part, stage)}]})
        path = os.path.join(RP, 'models', 'blocks', f'{name}.geo.json')
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'format_version': '1.12.0', 'minecraft:geometry': geos}, f, indent=1)
        tex = os.path.join(RP, 'textures', 'blocks', f'kfv_{name}.png')
        paint(name).save(tex)
        pbr.refresh(tex)
        print(name, 'cubes per state:', [len(g['bones'][0]['cubes']) for g in geos])


if __name__ == '__main__':
    main()
