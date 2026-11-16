"""Build the two legendary-fish feasts: models (every state) and painted textures.

usage: python tools/gen_legend_feasts.py

龍鯉石板燒 lava_dragon_koi_stone_grill (2 blocks, part 0 head, part 1 tail; 4 stages each)
    The Lava Dragon Koi seared on a hot stone: a basalt base with glowing ember cracks round its edge, a polished
    blackstone plate on top, the koi lying on its side (flank up, back towards -x) with grill marks, gold barbels
    sweeping back from the mouth, flame-coloured fins and a big flame tail, red chili rings and scallion on top.
    Global length L runs 0..32 along the two blocks (L = z + 8 + 16 * part). Stages: 0 whole, 1 top fillet gone
    (cooked meat shows), 2 cut down to the last layer, 3 bare spine and ribs between head and tail.
    Geometry ids: geometry.kaleidoscope_fishing.lava_dragon_koi_stone_grill_<part>_<stage>.

河伯鯰砂鍋 river_lord_catfish_clay_pot (1 block, front = north = towards the player; 5 states, 4 bites)
    A round terracotta clay pot on a straw mat, black glaze inside, its lid slid back and leaning on the rim.
    In the braising broth: the catfish head with its long whiskers draped over the front rim, catfish chunks,
    tofu and scallion. Stages: 0 full, 1-3 fewer pieces and a lower broth, 4 empty (a film of broth left).
    Geometry ids: geometry.kaleidoscope_fishing.river_lord_catfish_clay_pot_0_<stage>_0 (like oden_pot).

Every face's UV follows world position at 1 texture pixel per model unit, so textures are never stretched and
painted patterns run continuously across cubes (and across the two blocks of the grill). The block textures'
_mer map is written with emissive embers / broth highlights; the _height map comes from pbr.refresh.
"""
import json, math, os, random, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
NS = 'geometry.kaleidoscope_fishing.'


# ================================================================== shared helpers
def hexc(h, a=255):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (a,)


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def ramp(cols, t):
    t = max(0.0, min(1.0, t)) * (len(cols) - 1)
    i = min(len(cols) - 2, int(t))
    return lerp(cols[i], cols[i + 1], t - i)


def region_face(region, face, box, mu, mv):
    """UV for one face, mapping world coordinates into `region` with mu/mv (functions of the face's left/right
    and top/bottom world edges). Orientation of Bedrock faces seen from outside:
      up    left x1 right x0, top z0 bottom z1        down  left x1 right x0, top z1 bottom z0
      north left x1 right x0, top y1 bottom y0        south left x0 right x1
      east  left z1 right z0                          west  left z0 right z1"""
    (x0, y0, z0), (x1, y1, z1) = box
    edges = {'up': ((x1, x0), (z0, z1)), 'down': ((x1, x0), (z1, z0)),
             'north': ((x1, x0), (y1, y0)), 'south': ((x0, x1), (y1, y0)),
             'east': ((z1, z0), (y1, y0)), 'west': ((z0, z1), (y1, y0))}
    (ul, ur), (vt, vb) = edges[face]
    u_a, u_b = mu(ul), mu(ur)
    v_a, v_b = mv(vt), mv(vb)
    return {'uv': [round(region[0] + u_a, 4), round(region[1] + v_a, 4)],
            'uv_size': [round(u_b - u_a, 4), round(v_b - v_a, 4)]}


def tile(region):
    """Small tile: the face shows the start of the region at its own size (clamped to the region)."""
    def f(face, box):
        (x0, y0, z0), (x1, y1, z1) = box
        dims = {'up': (x1 - x0, z1 - z0), 'down': (x1 - x0, z1 - z0), 'north': (x1 - x0, y1 - y0),
                'south': (x1 - x0, y1 - y0), 'east': (z1 - z0, y1 - y0), 'west': (z1 - z0, y1 - y0)}[face]
        w, h = min(dims[0], region[2]), min(dims[1], region[3])
        return {'uv': [region[0], region[1]], 'uv_size': [round(w, 4), round(h, 4)]}
    return f


def planar(region, axis_u, off_u, axis_v, off_v, sign_v=1):
    """Face UV from world coordinates: u = coord[axis_u] + off_u, v = sign_v * coord[axis_v] + off_v."""
    return lambda face, box: region_face(region, face, box, lambda a: a + off_u, lambda b: sign_v * b + off_v)


ALL6 = ('up', 'down', 'north', 'south', 'east', 'west')


class Model:
    def __init__(self):
        self.cubes = []

    def add(self, lo, hi, faces, rotation=None, pivot=None):
        if any(hi[i] - lo[i] <= 1e-6 for i in range(3)):
            return
        box = (lo, hi)
        uv = {f: fn(f, box) for f, fn in faces.items()}
        c = {'origin': [round(v, 4) for v in lo], 'size': [round(hi[i] - lo[i], 4) for i in range(3)], 'uv': uv}
        if rotation:
            c['rotation'] = rotation
            c['pivot'] = [round(v, 4) for v in pivot]
        self.cubes.append(c)


def geo(ident, tw, th, cubes, vb=(3, 2)):
    return {'description': {'identifier': ident, 'texture_width': tw, 'texture_height': th,
                            'visible_bounds_width': vb[0], 'visible_bounds_height': vb[1],
                            'visible_bounds_offset': [0, 0.5, 0]},
            'bones': [{'name': 'root', 'pivot': [0, 0, 0], 'cubes': cubes}]}


def write_mer(color_png, emissive, rough=200, metal=0):
    """MER map: emissive(x, y, rgba) -> 0..255 per pixel; everything else plain rough non-metal."""
    col = Image.open(color_png).convert('RGBA')
    px = col.load()
    mer = Image.new('RGBA', col.size, (0, 0, 0, 0))
    mp = mer.load()
    for y in range(col.height):
        for x in range(col.width):
            c = px[x, y]
            if c[3]:
                e, r = emissive(x, y, c)
                mp[x, y] = (metal, e, r if r is not None else rough, 255)
    mer.save(color_png[:-4] + '_mer.png')


def write_texture_set(name, kind):
    base = os.path.join(RP, 'textures', kind, name)
    third = ('heightmap', name + '_height') if kind == 'blocks' else ('normal', name + '_normal')
    ts = {'format_version': '1.16.100', 'minecraft:texture_set': {
        'color': name, 'metalness_emissive_roughness': name + '_mer', third[0]: third[1]}}
    with open(base + '.texture_set.json', 'w', encoding='utf-8', newline='\n') as f:
        json.dump(ts, f, indent=2)
        f.write('\n')


# ================================================================== 龍鯉石板燒 (stone grill)
G_TW = G_TH = 128
# atlas regions (u0, v0, w, h)
G_TOP = (0, 0, 16, 32)      # fish seen from above, u = x + 8, v = L: flank, fins, tail, barbels (alpha outside)
G_MEAT = (16, 0, 16, 32)    # cut surface from above
G_DORS = (32, 0, 32, 4)     # -x faces of the body (back): u = L, v = 6.5 - y
G_BELLY = (32, 4, 32, 4)    # +x faces (belly)
G_CROSS = (64, 0, 16, 4)    # +-z faces of skin: u = x + 8, v = 6.5 - y
G_MEATX = (64, 4, 16, 4)    # cut cross-section from the side
G_FINE = (80, 0, 8, 1)      # thin edges of fins / barbels / tail
G_BONE = (88, 0, 8, 8)
G_EYE = (96, 0, 4, 4)
G_CHILI = (100, 0, 4, 4)
G_CHILIS = (104, 0, 4, 1)
G_SCAL = (100, 4, 4, 4)
G_SCALS = (104, 1, 4, 1)
G_EMBER = (108, 0, 4, 4)
G_STONE = (0, 32, 16, 32)   # basalt base, top: u = x + 8, v = L
G_STONES = (16, 32, 32, 2)  # base +-x sides: u = L, v = 1.5 - y
G_STONEE = (48, 32, 16, 2)  # base +-z ends: u = x + 8
G_PLATE = (64, 32, 16, 32)  # blackstone plate top: u = x + 8, v = L
G_PLATES = (80, 32, 32, 1)  # plate sides: u = L, v = 2.5 - y
G_PLATEE = (112, 32, 16, 1)
G_UNDER = (16, 40, 16, 16)  # underside of the base (tiled)

BASE_Y, PLATE_Y = 1.5, 2.5          # top of the basalt base / top of the plate (the fish lies on it)
FISH_L = (2, 26)                    # snout .. peduncle; tail fan 26 .. 31
EATEN = (8, 22)                     # this stretch is eaten; head and tail stay
CUT = {1: 0.55, 2: 0.25}


def k_w(L):
    """Half-width (back..belly, x) of the koi at L."""
    if L < 2:
        return 0
    if L < 8:
        return 1.4 + 2.6 * math.sin((L - 2) / 6 * math.pi / 2)
    if L < 19:
        return 4.0
    if L < 26:
        return 4.0 - 2.9 * (L - 19) / 7
    return 0


def k_t(L):
    """Thickness of the koi at L (y above the plate)."""
    if L < 8:
        return 1.6 + 1.6 * math.sin(max(0, (L - 2)) / 6 * math.pi / 2)
    if L < 19:
        return 3.4
    if L < 26:
        return 3.4 - 2.4 * (L - 19) / 7
    return 0


# fin and decoration masks in (x, L) top-view coordinates
def fin_kind(x, L):
    """Which flat appendage covers (x, L) on the plate, or None. Back is -x, belly +x."""
    w = k_w(L)
    # tail fan: flame tongues spreading from the peduncle
    if 25.5 <= L < 31.5:
        t = (L - 25.5) / 6
        spread = 1.2 + 4.6 * t ** 0.8
        notch = 1.4 * t if abs(x) < 1.4 * t else 0   # forked middle
        flame = 0.6 * math.sin(x * 2.1 + L * 0.9)
        if abs(x) <= spread and L < 31.5 - notch - (0.0 if abs(x) > 1.4 * t else 0) + flame * t:
            return 'tail'
    # dorsal fin along the back (-x), long and flame-edged
    if 8.5 <= L < 21 and x < -w and x > -w - (1.6 + 0.9 * math.sin((L - 8.5) / 12.5 * math.pi) + 0.5 * math.sin(L * 1.7)):
        return 'fin'
    # pectoral fin by the head (+x), anal fin near the tail (+x)
    if 8 <= L < 11.5 and w < x < w + 1.6 + (L - 8) * 0.5:
        return 'fin'
    if 17.5 <= L < 22 and w < x < w + 1.4 + 0.5 * math.sin((L - 17.5) / 4.5 * math.pi):
        return 'fin'
    # barbels: two gold strands from the mouth curling back along the head
    for sgn in (-1, 1):
        if 1.0 <= L < 7.5:
            cx = sgn * (1.2 + 3.0 * math.sin((L - 1.0) / 6.5 * math.pi * 0.85) + 1.0 * ((L - 1) / 6.5) ** 2)
            if abs(x - cx) < 0.5 and abs(x) > w - 0.2:
                return 'barbel'
    return None


def grill_build(part, stage):
    m = Model()
    Lmin, Lmax = 16 * part, 16 * part + 16
    zl = lambda L: L - 8 - 16 * part
    Lz = lambda z: z + 8 + 16 * part
    top_faces = lambda region: {'up': lambda f, b: region_face(region, f, b, lambda x: x + 8, Lz)}

    # ---- basalt base with ember cracks, blackstone plate on it
    la, lb = max(0.5, Lmin), min(31.5, Lmax)
    m.add([-7.5, 0, zl(la)], [7.5, BASE_Y, zl(lb)], {
        'up': lambda f, b: region_face(G_STONE, f, b, lambda x: x + 8, Lz),
        'down': tile(G_UNDER),
        'east': lambda f, b: region_face(G_STONES, f, b, Lz, lambda y: BASE_Y - y),
        'west': lambda f, b: region_face(G_STONES, f, b, Lz, lambda y: BASE_Y - y),
        'north': lambda f, b: region_face(G_STONEE, f, b, lambda x: x + 8, lambda y: BASE_Y - y),
        'south': lambda f, b: region_face(G_STONEE, f, b, lambda x: x + 8, lambda y: BASE_Y - y)})
    pa, pb = max(1.5, Lmin), min(30.5, Lmax)
    m.add([-6.5, BASE_Y, zl(pa)], [6.5, PLATE_Y, zl(pb)], {
        'up': lambda f, b: region_face(G_PLATE, f, b, lambda x: x + 8, Lz),
        'east': lambda f, b: region_face(G_PLATES, f, b, Lz, lambda y: PLATE_Y - y),
        'west': lambda f, b: region_face(G_PLATES, f, b, Lz, lambda y: PLATE_Y - y),
        'north': lambda f, b: region_face(G_PLATEE, f, b, lambda x: x + 8, lambda y: PLATE_Y - y),
        'south': lambda f, b: region_face(G_PLATEE, f, b, lambda x: x + 8, lambda y: PLATE_Y - y)})
    # glowing coals at the four corners of the base rim
    for x, L in ((-6.9, 0.9), (6.1, 0.9), (-6.9, 30.3), (6.1, 30.3)):
        if Lmin <= L < Lmax:
            m.add([x, BASE_Y, zl(L)], [x + 0.8, BASE_Y + 0.5, zl(L + 0.8)], {f: tile(G_EMBER) for f in ALL6})

    def eaten(La, Lb):
        return EATEN[0] <= La and Lb <= EATEN[1]

    # ---- body, in 2-long chunks of stacked slabs (rounded cross-section)
    layers = [(0.0, 0.45, 1.0), (0.45, 0.75, 0.88), (0.75, 1.0, 0.62)]
    for La in range(FISH_L[0], FISH_L[1], 2):
        Lb = La + 2
        if Lb <= Lmin or La >= Lmax:
            continue
        w, t = k_w(La + 1), k_t(La + 1)
        if La == FISH_L[0]:                           # snout: narrower and lower
            w, t = 1.6, 1.8
        is_eaten = eaten(La, Lb) and stage >= 1
        if stage == 3 and is_eaten:
            continue
        top_cap = PLATE_Y + t
        if is_eaten:
            top_cap = PLATE_Y + max(0.5, t * CUT[stage])
        end_meat = ()
        if stage >= 1 and La == EATEN[0] - 2:
            end_meat = ('south',)
        if stage >= 1 and Lb == EATEN[1] + 2:
            end_meat = ('north',)
        for fa, fb, wf in layers:
            ya, yb = PLATE_Y + t * fa, PLATE_Y + t * fb
            if ya >= top_cap - 1e-6:
                break
            cut = yb > top_cap + 1e-6
            yb = min(yb, top_cap)
            hw = w * wf
            faces = {
                'up': lambda f, b, r=(G_MEAT if cut else G_TOP): region_face(r, f, b, lambda x: x + 8, Lz),
                'west': lambda f, b: region_face(G_DORS, f, b, Lz, lambda y: 6.5 - y),
                'east': lambda f, b: region_face(G_BELLY, f, b, Lz, lambda y: 6.5 - y)}
            for fc in ('north', 'south'):
                reg = G_MEATX if fc in end_meat else G_CROSS
                faces[fc] = (lambda reg: lambda f, b: region_face(reg, f, b, lambda x: x + 8, lambda y: 6.5 - y))(reg)
            m.add([-hw, ya, zl(La)], [hw, yb, zl(Lb)], faces)

    # ---- eye (gold ring) on the flank near the back, head part
    if part == 0:
        ty = PLATE_Y + k_t(5)
        m.add([-2.2, ty - 0.2, zl(4.5)], [-0.7, ty + 0.2, zl(6)], {
            'up': lambda f, b: region_face(G_EYE, f, b, lambda x: (x + 2.2) * 4 / 1.5, lambda z: (z - zl(4.5)) * 4 / 1.5),
            'north': tile(G_FINE), 'south': tile(G_FINE), 'east': tile(G_FINE), 'west': tile(G_FINE)})

    # ---- flat appendages: one thin slab per 1-long row, cut to the painted shape by alpha
    for L in range(0, 32):
        if not (Lmin <= L < Lmax):
            continue
        xs = [x / 4 for x in range(-28, 29)]
        for kind in ('fin', 'tail', 'barbel'):
            hits = [x for x in xs if any(fin_kind(x, L + dl) == kind for dl in (0.1, 0.5, 0.9))]
            if not hits:
                continue
            if kind == 'fin' and stage >= 2 and EATEN[0] <= L < EATEN[1]:
                continue
            # split into runs on each side of the body
            runs, cur = [], [hits[0]]
            for x in hits[1:]:
                if x - cur[-1] > 0.3:
                    runs.append(cur); cur = [x]
                else:
                    cur.append(x)
            runs.append(cur)
            y0 = PLATE_Y + (0.0 if kind != 'barbel' else 0.05)
            th = 0.5 if kind != 'barbel' else 0.4
            for r in runs:
                x0, x1 = math.floor(r[0] * 2) / 2 - 0.25, math.ceil(r[-1] * 2) / 2 + 0.25
                x0, x1 = max(x0, -7.0), min(x1, 7.0)
                m.add([x0, y0, zl(L)], [x1, y0 + th, zl(L + 1)], {
                    'up': lambda f, b: region_face(G_TOP, f, b, lambda x: x + 8, Lz),
                    'down': lambda f, b: region_face(G_TOP, f, b, lambda x: x + 8, Lz),
                    'north': tile(G_FINE), 'south': tile(G_FINE), 'east': tile(G_FINE), 'west': tile(G_FINE)})

    # ---- skeleton where the fish has been eaten
    if stage == 3:
        a, b = max(EATEN[0], Lmin), min(EATEN[1], Lmax)
        if a < b:
            m.add([-0.6, PLATE_Y, zl(a)], [0.6, PLATE_Y + 1.2, zl(b)], {f: tile(G_BONE) for f in ALL6 if f != 'down'})
            for L in range(EATEN[0] + 1, EATEN[1], 2):
                if a <= L < b:
                    hw = k_w(L) - 0.7
                    m.add([-hw, PLATE_Y, zl(L)], [hw, PLATE_Y + 0.5, zl(L + 0.6)],
                          {f: tile(G_BONE) for f in ALL6 if f != 'down'})

    # ---- garnish: chili rings and scallion on the fish (eaten with it), more on the plate
    on_fish = [((-1.5, 10.5), 'c'), ((1.0, 12.5), 's'), ((-0.5, 14.5), 'c'), ((1.6, 16.5), 'c'),
               ((-1.8, 17.5), 's'), ((0.2, 19.5), 'c'), ((-1.0, 21.0), 's')]
    on_plate = [((4.8, 13.2), 'c', 2), ((5.0, 15.0), 's', 1), ((-5.6, 22.2), 'c', 2), ((-5.4, 24.0), 's', 1),
                ((5.2, 3.0), 's', 2), ((4.6, 23.2), 's', 0)]
    for (x, L), kind in on_fish:
        if not (Lmin <= L < Lmax) or stage >= 1:
            continue
        ty = PLATE_Y + k_t(L)
        add_garnish(m, x, ty, zl(L), kind)
    for (x, L), kind, last in on_plate:
        if Lmin <= L < Lmax and stage <= last:
            add_garnish(m, x, PLATE_Y, zl(L), kind)
    return m.cubes


def add_garnish(m, x, y, z, kind):
    if kind == 'c':       # chili ring
        m.add([x - 0.6, y, z - 0.6], [x + 0.6, y + 0.4, z + 0.6], {
            'up': lambda f, b: {'uv': [G_CHILI[0], G_CHILI[1]], 'uv_size': [4, 4]},
            'north': tile(G_CHILIS), 'south': tile(G_CHILIS), 'east': tile(G_CHILIS), 'west': tile(G_CHILIS)})
    else:                 # scallion shreds
        m.add([x - 0.7, y, z - 0.4], [x + 0.7, y + 0.35, z + 0.4], {
            'up': lambda f, b: {'uv': [G_SCAL[0], G_SCAL[1]], 'uv_size': [4, 2]},
            'north': tile(G_SCALS), 'south': tile(G_SCALS), 'east': tile(G_SCALS), 'west': tile(G_SCALS)})


def grill_paint():
    rnd = random.Random('lava_dragon_koi_stone_grill')
    im = Image.new('RGBA', (G_TW, G_TH), (0, 0, 0, 0))
    px = im.load()
    body = [hexc(c) for c in ('#3a0710', '#6a0c18', '#9a1420', '#c42a1c', '#e2541c', '#f08a2a')]
    glow = [hexc(c) for c in ('#ff9a2a', '#ffc640', '#ffe890')]
    char = hexc('#1e0c08')
    gold = [hexc(c) for c in ('#9a5a10', '#d89a20', '#ffd650', '#fff0a0')]
    flame = [hexc(c) for c in ('#7a0c10', '#c4201a', '#ee5a1a', '#ff9a2a', '#ffd04a')]

    def koi_flank(x, L):
        w = max(0.5, k_w(L))
        rel = max(0.0, min(1.0, (x + w) / (2 * w)))           # 0 back .. 1 belly
        c = ramp(body, 0.15 + 0.75 * (1 - abs(rel - 0.55) * 1.5) if rel < 0.55 else 0.55 + 0.45 * rel)
        # glowing scales: each 2x2 scale gets a bright rim on its tail side
        sx, sl = int(math.floor(x + 8)), int(math.floor(L))
        if 0.12 < rel < 0.9 and L > 8:
            ph = (sl + (sx // 2) % 2) % 2
            if ph == 0 and (sx % 2 == 0):
                c = lerp(c, ramp(glow, rnd.random() * 0.6), 0.55)
            elif rnd.random() < 0.12:
                c = lerp(c, glow[2], 0.35)
        if rel < 0.12:                                        # dark ridge of the back
            c = lerp(c, body[0], 0.5)
        # grill marks: diagonal charred bars across the body
        if L > 4 and (L + x * 0.75) % 4.0 < 0.9:
            c = lerp(c, char, 0.78)
        # gill plate and mouth on the head
        if 6.6 < L < 7.6 + 0.6 * (1 - abs(x) / 4) and L < 8.2:
            c = lerp(c, body[0], 0.6)
        if L < 3.2:
            c = lerp(c, body[1], 0.5)
        return c

    # ---- top view atlas: body flank + fins + tail + barbels, transparent elsewhere
    u0, v0, w_, h_ = G_TOP
    for v in range(h_):
        L = v + 0.5
        for u in range(w_):
            x = u - 8 + 0.5
            if FISH_L[0] <= L < FISH_L[1] and abs(x) <= k_w(L) + 0.5:
                px[u0 + u, v0 + v] = koi_flank(x, L)
                continue
            kind = fin_kind(x, L)
            if kind == 'barbel':
                px[u0 + u, v0 + v] = gold[2] if (u + v) % 3 else gold[3]
            elif kind == 'fin':
                d = abs(x) - k_w(L)                            # distance out from the body edge
                c = ramp(flame, 0.2 + d / 2.8)
                if (v + (u if x > 0 else -u)) % 2 == 0:       # fin rays
                    c = lerp(c, flame[0], 0.25)
                px[u0 + u, v0 + v] = c
            elif kind == 'tail':
                t = (L - 25.5) / 6
                c = ramp(flame, 0.15 + 0.85 * t + 0.1 * math.sin(x * 2))
                if u % 2 == 0:
                    c = lerp(c, flame[1], 0.3)
                px[u0 + u, v0 + v] = c
    # ---- cooked meat from above: white flakes, orange-tinted near the skin, darker centre line
    meat = [hexc(c) for c in ('#e8d8c4', '#f4e8d8', '#fbf4ea')]
    u0, v0, w_, h_ = G_MEAT
    for v in range(h_):
        L = v + 0.5
        for u in range(w_):
            x = u - 8 + 0.5
            ww = max(0.5, k_w(L))
            if abs(x) > ww + 0.6:
                continue
            rel = abs(x) / ww
            c = ramp(meat, rnd.random() * 0.8 + 0.2)
            if (L + abs(x) * 1.2) % 3.0 < 0.6:                  # flake lines (myosepta)
                c = lerp(c, hexc('#cbb49a'), 0.6)
            if rel > 0.8:
                c = lerp(c, body[3], 0.55)                     # skin rim
            if abs(x) < 0.5:
                c = lerp(c, hexc('#b88a70'), 0.4)
            px[u0 + u, v0 + v] = c
    # ---- back and belly edges (u = L, v down the side)
    for reg, cols in ((G_DORS, [body[1], body[0], body[0], char]), (G_BELLY, [body[4], body[3], body[2], char])):
        u0, v0, w_, h_ = reg
        for v in range(h_):
            for u in range(w_):
                c = ramp(cols, v / (h_ - 1))
                if (u + v) % 3 == 0:
                    c = lerp(c, glow[0], 0.25)
                if (u + 2) % 4 == 0 and v < 3:
                    c = lerp(c, char, 0.5)                     # grill marks wrap the edge
                px[u0 + u, v0 + v] = c
    u0, v0, w_, h_ = G_CROSS
    for v in range(h_):
        for u in range(w_):
            px[u0 + u, v0 + v] = ramp(body, 0.2 + 0.7 * u / (w_ - 1))
    u0, v0, w_, h_ = G_MEATX
    for v in range(h_):
        for u in range(w_):
            c = ramp(meat, 0.3 + rnd.random() * 0.6)
            if v == 0:
                c = lerp(c, body[3], 0.7)
            if v % 2 == 1 and u % 3 == 0:
                c = lerp(c, hexc('#cbb49a'), 0.5)
            px[u0 + u, v0 + v] = c
    u0, v0, w_, h_ = G_FINE
    for u in range(w_):
        px[u0 + u, v0] = flame[2] if u % 2 else flame[3]
    u0, v0, w_, h_ = G_BONE
    for v in range(h_):
        for u in range(w_):
            c = hexc('#efe4cc') if (u + v) % 4 else hexc('#d8caa8')
            if (u * 3 + v) % 7 == 0:
                c = lerp(c, char, 0.35)                        # a little char from the stone
            px[u0 + u, v0 + v] = c
    u0, v0 = G_EYE[:2]
    for v in range(4):
        for u in range(4):
            px[u0 + u, v0 + v] = gold[2] if (u in (0, 3) or v in (0, 3)) else hexc('#120404')
    px[u0 + 1, v0 + 1] = hexc('#fff6d0')
    # chili ring (red with pale seeds), scallion (green with white bits)
    u0, v0 = G_CHILI[:2]
    for v in range(4):
        for u in range(4):
            ring = u in (0, 3) or v in (0, 3)
            px[u0 + u, v0 + v] = hexc('#c8141a') if ring else (hexc('#f4e0a0') if (u + v) % 2 else hexc('#e84a2a'))
    for u in range(4):
        px[G_CHILIS[0] + u, G_CHILIS[1]] = hexc('#a80e14')
    u0, v0 = G_SCAL[:2]
    for v in range(4):
        for u in range(4):
            px[u0 + u, v0 + v] = (hexc('#5aa82a'), hexc('#8ad04a'), hexc('#e8f0c0'), hexc('#3a8a1e'))[(u + v * 2) % 4]
    for u in range(4):
        px[G_SCALS[0] + u, G_SCALS[1]] = hexc('#4a9a24')
    u0, v0 = G_EMBER[:2]
    for v in range(4):
        for u in range(4):
            px[u0 + u, v0 + v] = ramp(glow + [hexc('#c43a10')], ((u * 7 + v * 5) % 5) / 4)

    # ---- basalt base: grey-black, with orange ember cracks round the rim and down the sides
    basalt = [hexc(c) for c in ('#1c1a1e', '#2a272c', '#38343a', '#4a454c')]
    lava = [hexc(c) for c in ('#8a1a08', '#e0501a', '#ff9a2a', '#ffd060')]

    def crack(a, b, seed):
        """Branching crack pattern value at (a, b): 0 none .. 1 bright core."""
        r = random.Random(f'{seed}:{int(a)}:{int(b)}')
        n = math.sin(a * 0.9 + seed) * 1.3 + math.sin(b * 1.3 + a * 0.4 + seed * 2) + math.sin((a - b) * 0.7)
        return max(0.0, 1 - abs(n) * 2.2) * (0.7 + 0.3 * r.random())

    u0, v0, w_, h_ = G_STONE
    for v in range(h_):
        L = v + 0.5
        for u in range(w_):
            x = u - 8 + 0.5
            c = basalt[(u * 3 + v * 7 + (u * v) % 5) % 4 if (u + v) % 2 else 1]
            edge = min(7.5 - abs(x), L - 0.5, 31.5 - L)           # distance to the outer edge
            if edge < 1.2:
                k = crack(x * 2, L, 3)
                if k > 0.15:
                    c = ramp(lava, 0.3 + 0.7 * k)
            px[u0 + u, v0 + v] = c
    u0, v0, w_, h_ = G_STONES
    for v in range(h_):
        for u in range(w_):
            c = basalt[(u * 5 + v * 3) % 4 if (u + v) % 3 else 0]
            k = crack(u, v * 3 + 1, 7)
            if k > 0.25:
                c = ramp(lava, 0.2 + 0.8 * k)
            px[u0 + u, v0 + v] = c
    u0, v0, w_, h_ = G_STONEE
    for v in range(h_):
        for u in range(w_):
            c = basalt[(u * 5 + v * 3 + 1) % 4 if (u + v) % 3 else 0]
            k = crack(u + 40, v * 3 + 1, 7)
            if k > 0.25:
                c = ramp(lava, 0.2 + 0.8 * k)
            px[u0 + u, v0 + v] = c
    u0, v0, w_, h_ = G_UNDER
    for v in range(h_):
        for u in range(w_):
            px[u0 + u, v0 + v] = basalt[(u + v * 3) % 3]
    # ---- polished blackstone plate: near-black with a faint grid of polish lines and oil sheen
    pb = [hexc(c) for c in ('#141116', '#1e1a20', '#29242b', '#3a3238')]
    u0, v0, w_, h_ = G_PLATE
    for v in range(h_):
        L = v + 0.5
        for u in range(w_):
            x = u - 8 + 0.5
            c = pb[1] if (u + v) % 2 else pb[0]
            if rnd.random() < 0.1:
                c = pb[2]
            if abs(x) > 6.0 or L < 2 or L > 30:                 # bevelled edge catches the glow
                c = lerp(pb[3], lava[1], 0.25)
            if rnd.random() < 0.04:
                c = hexc('#5a4a3a')                            # spatters of seared oil
            px[u0 + u, v0 + v] = c
    for reg in (G_PLATES, G_PLATEE):
        u0, v0, w_, h_ = reg
        for u in range(w_):
            px[u0 + u, v0] = pb[3] if u % 3 else pb[2]
    return im


def grill_emissive(x, y, c):
    r, g, b, _ = c
    hot = r > 200 and g > 60 and b < 120 and r - b > 120
    # embers and lava cracks glow; the koi's bright scales a little
    if hot and y >= 32:
        return 200, 120
    if (G_EMBER[0] <= x < G_EMBER[0] + 4 and G_EMBER[1] <= y < G_EMBER[1] + 4):
        return 255, 120
    if hot and x < 16 and y < 32 and g > 150:
        return 70, None
    return 0, None


# ================================================================== 河伯鯰砂鍋 (clay pot)
P_TW = P_TH = 64
P_SIDE = (0, 0, 16, 9)       # outside of the pot: u = x+8 (n/s) or z+8 (e/w), v = 9 - y
P_IN = (16, 0, 16, 9)        # black glaze inside
P_TOP = (0, 9, 16, 16)       # rim top: u = x + 8, v = z + 8
P_BROTH = (16, 9, 16, 16)
P_MAT = (32, 9, 16, 16)      # straw mat top
P_MATS = (32, 0, 16, 1)
P_LID = (0, 25, 16, 16)      # lid top, in lid-local x/z
P_LIDS = (16, 25, 16, 1)
P_LIDB = (16, 26, 16, 16)    # lid underside
P_SKIN = (48, 0, 8, 8)       # catfish skin, chunk tops (braised, glossy)
P_CSIDE = (48, 8, 8, 3)      # chunk sides: skin then meat
P_CEND = (56, 8, 8, 3)       # chunk cut ends: white meat, skin rim
P_HEAD = (32, 25, 8, 8)      # head top (eyes painted)
P_HEADF = (40, 25, 8, 3)     # head front (wide mouth)
P_HEADS = (40, 28, 8, 3)     # head sides
P_WHISK = (48, 16, 8, 1)
P_TOFU = (48, 20, 4, 4)
P_TOFUT = (52, 20, 4, 4)
P_SCAL = (56, 20, 4, 4)
P_KNOB = (48, 24, 4, 4)
P_BONE = (52, 24, 4, 4)
P_HANDLE = (56, 24, 4, 4)

R_OUT, R_IN = 7.0, 5.6       # pot body radius / inner radius
Y_MAT, Y_FOOT, Y_RIM = 0.5, 1.0, 7.0
LID_ROT = -95
BROTH_Y = {0: 5.8, 1: 5.3, 2: 4.8, 3: 4.2, 4: 2.2}


def circle_rows(r, step=1.0):
    """Rows (z0, z1, half-width) approximating a disc of radius r, rows `step` deep."""
    rows = []
    n = int(math.ceil(r / step))
    for i in range(-n, n):
        z0, z1 = i * step, (i + 1) * step
        zc = min(abs(z0), abs(z1))
        if zc >= r:
            continue
        hw = math.sqrt(max(0.0, r * r - (zc + step * 0.5) ** 2))
        hw = round(hw * 2) / 2
        if hw > 0:
            rows.append((max(z0, -r), min(z1, r), hw))
    return rows


def side_uv(region_out, region_in, ytop, mid=0.0):
    """Faces of a pot wall box: faces that look away from the pot's axis and lie in the outer half of the wall
    (further than `mid` from the axis) get the outside texture, the others the glaze."""
    def make(face):
        def f(fc, box):
            (x0, y0, z0), (x1, y1, z1) = box
            cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
            nrm = {'north': (0, -1), 'south': (0, 1), 'east': (1, 0), 'west': (-1, 0)}[fc]
            fx, fz = {'north': (cx, z0), 'south': (cx, z1), 'east': (x1, cz), 'west': (x0, cz)}[fc]
            outward = nrm[0] * fx + nrm[1] * fz > 0 and math.hypot(fx, fz) >= mid
            reg = region_out if outward else region_in
            if fc in ('north', 'south'):
                return region_face(reg, fc, box, lambda x: x + 8, lambda y: ytop - y)
            return region_face(reg, fc, box, lambda z: z + 8, lambda y: ytop - y)
        return f
    return {fc: make(fc) for fc in ('north', 'south', 'east', 'west')}


def ring(m, r_out, r_in, y0, y1, top=None):
    """A round wall from y0 to y1 between r_in and r_out, rows 1 deep."""
    faces = side_uv(P_SIDE, P_IN, 9, (r_out + r_in) / 2)
    if top:
        faces['up'] = planar(top, 0, 8, 2, 8)
    for z0, z1, hw in circle_rows(r_out):
        zc = min(abs(z0), abs(z1))
        if zc + 0.5 < r_in:
            hi = round(math.sqrt(max(0.0, r_in * r_in - (zc + 0.5) ** 2)) * 2) / 2
            if hi > 0 and hi < hw:
                m.add([-hw, y0, z0], [-hi, y1, z1], faces)
                m.add([hi, y0, z0], [hw, y1, z1], faces)
                continue
        m.add([-hw, y0, z0], [hw, y1, z1], faces)


def disc(m, r, y0, y1, faces):
    for z0, z1, hw in circle_rows(r):
        m.add([-hw, y0, z0], [hw, y1, z1], faces)


def pot_build(stage):
    m = Model()
    # straw mat
    disc(m, 7.5, 0, Y_MAT, {'up': planar(P_MAT, 0, 8, 2, 8), 'down': tile(P_MAT),
                           'north': tile(P_MATS), 'south': tile(P_MATS), 'east': tile(P_MATS), 'west': tile(P_MATS)})
    # foot, floor of the pot, the bulging body and the glazed rim
    side = side_uv(P_SIDE, P_IN, 9)
    disc(m, 5.6, Y_MAT, Y_FOOT + 0.5, dict(side, up=tile(P_IN)))
    ring(m, 6.5, R_IN, Y_FOOT, 2.0)
    ring(m, R_OUT, R_IN, 2.0, 5.5)
    ring(m, 6.6, R_IN - 0.2, 5.5, Y_RIM, top=P_TOP)
    # ear handles on both sides
    for sx in (-1, 1):
        x0 = 6.6 if sx > 0 else -8.0
        m.add([x0, 5.0, -1.5], [x0 + 1.4, 6.0, 1.5], {f: tile(P_HANDLE) for f in ALL6})
    # broth
    by = BROTH_Y[stage]
    disc(m, R_IN - 0.2, Y_FOOT + 0.5, by, {'up': planar(P_BROTH, 0, 8, 2, 8)})

    # ---- food, in the order it is eaten (last item is eaten first)
    def chunk(x, z, wx, wz, h, rot_y=0):
        y0 = by - h * 0.55
        faces = {'up': tile(P_SKIN), 'east': tile(P_CSIDE), 'west': tile(P_CSIDE),
                 'north': tile(P_CEND), 'south': tile(P_CEND)}
        if rot_y:
            m.add([x - wx / 2, y0, z - wz / 2], [x + wx / 2, y0 + h, z + wz / 2], faces, [0, rot_y, 0], [x, y0, z])
        else:
            m.add([x - wx / 2, y0, z - wz / 2], [x + wx / 2, y0 + h, z + wz / 2], faces)

    def tofu(x, z, rot_y=0):
        y0 = by - 1.0
        faces = {'up': tile(P_TOFUT), 'north': tile(P_TOFU), 'south': tile(P_TOFU), 'east': tile(P_TOFU), 'west': tile(P_TOFU)}
        m.add([x - 1, y0, z - 1], [x + 1, y0 + 1.8, z + 1], faces, [0, rot_y, 0] if rot_y else None, [x, y0, z])

    def scallion(x, z, rot_y=0):
        m.add([x - 0.8, by, z - 0.35], [x + 0.8, by + 0.3, z + 0.35],
              {f: tile(P_SCAL) for f in ('up', 'north', 'south', 'east', 'west')}, [0, rot_y, 0] if rot_y else None, [x, by, z])

    def head():
        y0 = by - 1.4
        # wide flat catfish head facing the front (north), its mouth by the front rim
        m.add([-2.6, y0, -5.2], [2.6, y0 + 2.8, -1.0], {
            'up': lambda f, b: region_face(P_HEAD, f, b, lambda x: (x + 2.6) * 8 / 5.2 * 0.75 + 1, lambda z: (z + 5.2) * 8 / 4.2 * 0.95),
            'north': lambda f, b: region_face(P_HEADF, f, b, lambda x: (x + 2.6) * 8 / 5.2, lambda y: (y0 + 2.8 - y)),
            'east': lambda f, b: region_face(P_HEADS, f, b, lambda z: (z + 5.2) * 8 / 4.2, lambda y: (y0 + 2.8 - y)),
            'west': lambda f, b: region_face(P_HEADS, f, b, lambda z: (z + 5.2) * 8 / 4.2, lambda y: (y0 + 2.8 - y)),
            'south': tile(P_CEND)})
        # long whiskers: two over the front rim drooping outside, two shorter curling sideways
        wy = y0 + 1.6
        wfaces = {f: (lambda f_, b: {'uv': [P_WHISK[0], P_WHISK[1]], 'uv_size': [1, 1]}) for f in ALL6}
        for sx in (-1, 1):
            # out over the rim and down the outside of the pot
            m.add([sx * 1.6 - 0.25, wy, -7.6], [sx * 1.6 + 0.25, wy + 0.5, -5.0], wfaces, [-(-10), 0, 0], [sx * 1.6, wy, -5.0])
            m.add([sx * 1.6 - 0.25, 2.5, -7.6], [sx * 1.6 + 0.25, wy + 0.4, -7.1], wfaces)
            # sideways, lying on the broth
            m.add([sx * 2.6 - (0 if sx > 0 else 3.2), by + 0.05, -4.4], [sx * 2.6 + (3.2 if sx > 0 else 0), by + 0.45, -3.9],
                  wfaces, [0, -25 * sx, 0], [sx * 2.6, by, -4.1])

    def bones():
        m.add([-0.4, by - 0.2, -3.0], [0.4, by + 0.4, 3.0], {f: tile(P_BONE) for f in ('up', 'north', 'south', 'east', 'west')},
              [0, 30, 0], [0, by, 0])
        for k in range(-2, 3):
            m.add([-1.6, by - 0.1, k * 1.1 - 0.2], [1.6, by + 0.25, k * 1.1 + 0.2],
                  {f: tile(P_BONE) for f in ('up', 'north', 'south', 'east', 'west')}, [0, 30, 0], [0, by, 0])

    food = {
        0: [lambda: scallion(-2.6, 1.0, 30), lambda: chunk(-2.4, 3.2, 3.2, 2.6, 2.0, 12), lambda: tofu(3.4, 3.0, -15),
            lambda: scallion(0.8, 4.2, -20)],
        1: [lambda: chunk(2.6, 0.6, 3.0, 2.6, 2.0, -18), lambda: tofu(-3.6, -0.2, 20), lambda: scallion(3.6, -2.0, 60)],
        2: [lambda: chunk(0.0, 2.2, 3.4, 2.8, 2.2, 5), lambda: tofu(-0.8, 4.4, 8), lambda: scallion(-3.4, 3.6, -40)],
        3: [lambda: head()],
    }
    for s in range(stage, 4):
        for fn in food[s]:
            fn()
    if stage == 3:
        bones()

    # ---- lid: tipped open on the back rim, standing behind the pot so the food shows from the front
    lid_pivot = [0, Y_RIM - 0.3, 6.6]
    rot = [LID_ROT, 0, 0]
    lid = {'up': planar(P_LID, 0, 8, 2, 8), 'down': planar(P_LIDB, 0, 8, 2, 8),
           'north': tile(P_LIDS), 'south': tile(P_LIDS), 'east': tile(P_LIDS), 'west': tile(P_LIDS)}
    off_z = 6.6 - 6.0
    ly = Y_RIM - 0.3
    for z0, z1, hw in circle_rows(6.0):
        m.add([-hw, ly, z0 + off_z], [hw, ly + 0.8, z1 + off_z], lid, rot, lid_pivot)
    m.add([-1.0, ly + 0.8, -1.0 + off_z], [1.0, ly + 1.8, 1.0 + off_z], {f: tile(P_KNOB) for f in ALL6}, rot, lid_pivot)
    return m.cubes


def pot_paint():
    rnd = random.Random('river_lord_catfish_clay_pot')
    im = Image.new('RGBA', (P_TW, P_TH), (0, 0, 0, 0))
    px = im.load()
    clay = [hexc(c) for c in ('#7a3a1e', '#9a4c26', '#b4602e', '#c87a42')]
    glaze = [hexc(c) for c in ('#140e0c', '#22180f', '#33241a', '#4a3424')]
    # outside: dark glazed rim band, terracotta body with speckles and a pale incised ring, darker foot
    u0, v0, w, h = P_SIDE
    for v in range(h):
        y = 9 - v - 0.5
        for u in range(w):
            c = clay[1 + (rnd.random() < 0.35) + (rnd.random() < 0.15)]
            if rnd.random() < 0.07:
                c = hexc('#d8a070')
            if y > 5.6:
                c = glaze[2 + ((u + v) % 3 == 0)]
            elif y > 5.0:
                c = lerp(clay[0], glaze[2], 0.5)
            elif 3.0 < y < 3.8:
                c = lerp(c, hexc('#e0b48a'), 0.45) if u % 2 == 0 else c   # incised ring
            elif y < 2.0:
                c = lerp(c, clay[0], 0.55)
            px[u0 + u, v0 + v] = c
    u0, v0, w, h = P_IN
    for v in range(h):
        for u in range(w):
            px[u0 + u, v0 + v] = glaze[(u * 3 + v) % 3]
    u0, v0, w, h = P_TOP
    for v in range(h):
        for u in range(w):
            px[u0 + u, v0 + v] = glaze[2 + ((u + v) % 4 == 0)]
    # braising broth: deep red-brown soy, oil beads and a few chili-oil glints
    u0, v0, w, h = P_BROTH
    broth = [hexc(c) for c in ('#4a1a0c', '#6a2810', '#843614', '#a0481c')]
    for v in range(h):
        for u in range(w):
            c = broth[1 + int(1.5 + math.sin(u * 0.8 + v * 0.5) + 0.6 * rnd.random()) % 3]
            if rnd.random() < 0.06:
                c = hexc('#e09a40')                       # oil bead
            elif rnd.random() < 0.05:
                c = broth[0]
            px[u0 + u, v0 + v] = c
    # straw mat: concentric woven rings
    u0, v0, w, h = P_MAT
    straw = [hexc(c) for c in ('#9a7a3a', '#b8964a', '#d4b464', '#e6cc80')]
    for v in range(h):
        for u in range(w):
            d = math.hypot(u - 7.5, v - 7.5)
            c = straw[1 + (int(d) % 2) + (1 if (int(math.atan2(v - 7.5, u - 7.5) * 4) + int(d)) % 2 else 0) * 0]
            if int(d) % 2 == 0 and (u + v) % 2 == 0:
                c = straw[0]
            px[u0 + u, v0 + v] = c
    for u in range(16):
        px[P_MATS[0] + u, P_MATS[1]] = straw[0] if u % 2 else straw[1]
    # lid: terracotta, glazed rim ring, pale ring round the knob, steam vent
    u0, v0, w, h = P_LID
    for v in range(h):
        for u in range(w):
            d = math.hypot(u - 7.5, v - 7.5)
            c = clay[2 + (rnd.random() < 0.3)]
            if d > 5.8:
                c = glaze[2]
            elif 2.2 < d < 3.0:
                c = lerp(c, hexc('#e0b48a'), 0.5)
            if (u, v) in ((10, 5), (10, 6)):
                c = glaze[0]
            px[u0 + u, v0 + v] = c
    for u in range(16):
        px[P_LIDS[0] + u, P_LIDS[1]] = glaze[2] if u % 3 else glaze[3]
    u0, v0, w, h = P_LIDB
    for v in range(h):
        for u in range(w):
            d = math.hypot(u - 7.5, v - 7.5)
            c = clay[1] if (u * 3 + v) % 4 else clay[0]                     # unglazed underside
            if d > 5.0:
                c = glaze[2]
            elif rnd.random() < 0.08:
                c = hexc('#d8b090')                                         # condensation beads
            px[u0 + u, v0 + v] = c
    # catfish: dark olive-slate skin, braised glossy, pale belly, white meat
    skin = [hexc(c) for c in ('#1e2a28', '#2c3c38', '#3e524a', '#5a6e60')]
    u0, v0, w, h = P_SKIN
    for v in range(h):
        for u in range(w):
            c = skin[1 + (rnd.random() < 0.4)]
            if rnd.random() < 0.15:
                c = skin[0]
            c = lerp(c, broth[2], 0.35)                    # soaked in the braise
            if (u + v * 3) % 7 == 0:
                c = lerp(c, hexc('#e8a050'), 0.5)          # glossy highlight
            px[u0 + u, v0 + v] = c
    meat = [hexc(c) for c in ('#e6d6c0', '#f2e6d4', '#fbf4e8')]
    u0, v0, w, h = P_CSIDE
    for v in range(h):
        for u in range(w):
            px[u0 + u, v0 + v] = lerp(skin[1], broth[2], 0.35) if v == 0 else lerp(ramp(meat, rnd.random()), broth[3], 0.25 * (v == 2))
    u0, v0, w, h = P_CEND
    for v in range(h):
        for u in range(w):
            c = ramp(meat, 0.3 + rnd.random() * 0.7)
            if v == 0 or u in (0, w - 1):
                c = lerp(skin[1], broth[2], 0.3)
            if u == 3 and v == 1:
                c = hexc('#d8ccb8')
            px[u0 + u, v0 + v] = c
    # head top: mottled, two small eyes set wide, pale lips at the front
    u0, v0, w, h = P_HEAD
    for v in range(h):
        for u in range(w):
            c = skin[1 + (rnd.random() < 0.35)]
            if rnd.random() < 0.18:
                c = skin[0]
            c = lerp(c, broth[2], 0.2)
            if v == 0:
                c = hexc('#cfc2a4')
            px[u0 + u, v0 + v] = c
    for (u, v) in ((1, 2), (6, 2)):
        px[u0 + u, v0 + v] = hexc('#e8d890')
        px[u0 + u, v0 + v + 1] = hexc('#101010')
    u0, v0, w, h = P_HEADF
    for v in range(h):
        for u in range(w):
            c = skin[2]
            if v == 1:
                c = hexc('#2a1410') if 0 < u < w - 1 else hexc('#cfc2a4')   # wide mouth
            if v == 2:
                c = hexc('#d8ccb0')
            px[u0 + u, v0 + v] = c
    u0, v0, w, h = P_HEADS
    for v in range(h):
        for u in range(w):
            px[u0 + u, v0 + v] = skin[1 + (v == 0)] if v < 2 else hexc('#c8bea4')
    for u in range(8):
        px[P_WHISK[0] + u, P_WHISK[1]] = hexc('#d8b860') if u % 2 else hexc('#c09a48')
    u0, v0 = P_TOFU[:2]
    for v in range(4):
        for u in range(4):
            px[u0 + u, v0 + v] = hexc('#f0e6c8') if (u + v) % 3 else hexc('#e2d2a8')
    u0, v0 = P_TOFUT[:2]
    for v in range(4):
        for u in range(4):
            px[u0 + u, v0 + v] = lerp(hexc('#f0e0b8'), broth[2], 0.45 if (u + v) % 2 else 0.3)
    u0, v0 = P_SCAL[:2]
    for v in range(4):
        for u in range(4):
            px[u0 + u, v0 + v] = (hexc('#4a9a24'), hexc('#7cc844'), hexc('#e4f0c4'), hexc('#3a7a1a'))[(u + v) % 4]
    for v in range(4):
        for u in range(4):
            px[P_KNOB[0] + u, P_KNOB[1] + v] = glaze[2 + ((u + v) % 2)]
            px[P_BONE[0] + u, P_BONE[1] + v] = hexc('#efe4cc') if (u + v) % 3 else hexc('#d6c8a6')
            px[P_HANDLE[0] + u, P_HANDLE[1] + v] = clay[1 + (u + v) % 2]
    return im


def pot_emissive(x, y, c):
    # oil beads on the broth catch the light (slightly smoother), nothing glows
    if P_BROTH[0] <= x < P_BROTH[0] + 16 and P_BROTH[1] <= y < P_BROTH[1] + 16:
        return 0, 90
    if P_IN[0] <= x < P_IN[0] + 16 and y < 9 or P_TOP[1] <= y < P_TOP[1] + 16 and x < 16:
        return 0, 110                                   # glaze
    return 0, None


# ================================================================== main
def save_block_texture(name, im, emissive):
    tex = os.path.join(RP, 'textures', 'blocks', f'kfv_{name}.png')
    im.save(tex)
    write_texture_set(f'kfv_{name}', 'blocks')
    pbr.refresh(tex)
    write_mer(tex, emissive)


def main():
    out = {}
    name = 'lava_dragon_koi_stone_grill'
    geos = [geo(f'{NS}{name}_{p}_{s}', G_TW, G_TH, grill_build(p, s)) for p in range(2) for s in range(4)]
    out[name] = geos
    save_block_texture(name, grill_paint(), grill_emissive)
    name = 'river_lord_catfish_clay_pot'
    geos = [geo(f'{NS}{name}_0_{s}_0', P_TW, P_TH, pot_build(s), vb=(2, 2)) for s in range(5)]
    out[name] = geos
    save_block_texture(name, pot_paint(), pot_emissive)
    for name, geos in out.items():
        path = os.path.join(RP, 'models', 'blocks', f'{name}.geo.json')
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'format_version': '1.12.0', 'minecraft:geometry': geos}, f, indent=1)
        print(name, 'cubes per state:', [len(g['bones'][0]['cubes']) for g in geos])


if __name__ == '__main__':
    main()
