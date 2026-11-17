"""Blocks added in 1.5.0: the Wooden Tub (木盆), the Salt Pan (曬鹽盤) and the Lava Fish Tank (熔岩魚缸).

  python tools/gen_stations_1_5.py                 the three models, textures, RTX maps and guidebook pictures
  python tools/gen_stations_1_5.py --pond-feeder   also the first-pass Fish Pond Feeder (box model, tools/modelkit.py)

Hand-built geometry with a texture painted in code: every face gets its own patch of the texture at 1 texture pixel
per model unit (per-face UV, nothing stretched), painted from the face's world position, so grain, crust and
highlights run on across neighbouring cubes. Each block is one geometry whose parts are bones; the block shows the
parts its state asks for (bone_visibility in the block json):

  Wooden Tub (alpha_test)   a coopered tub: 16 staves in slightly different wood tones, two iron hoops with
                            rivets, two lug staves with a hand hole, a plank bottom. State `fill` (blocks/tub.js):
                            water | brine (cloudy, salt grains) | clams in the brine | fish roe | fry.
                            bones: tub, water, brine, clams, roe, fry
  Salt Pan (alpha_test)     a terracotta tray with a wooden rim on two wooden runners. State `stage`
                            (blocks/saltPan.js): seawater | half dry (white crust creeping in from the rim, pale
                            water in the middle) | full of salt (crystalline bed, a heap and a wooden salt rake).
                            bones: pan, water, half, salt
  Lava Fish Tank (blend)    a blackstone base, iron corner posts and rims, faintly warm glass (low alpha, a little
                            heat haze near the bottom) and molten lava only as a 2-pixel bed with basalt columns
                            and a magma rock, so the creature (the tank fish entity) stays in plain view above it.
                            bones: frame, lava

Writes models/blocks/<name>.geo.json, textures/blocks/kfv_<name>.png with its RTX maps (height from pbr.refresh,
MER painted per material so the lava and magma cracks glow), the terrain texture entry, and the 128x128 guidebook
picture textures/ui/kfv_book/kfv_<name>.png (also the item icon) rendered from the model.
"""
import importlib.util, json, math, os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
NS = 'kaleidoscope_fishing'
ALL6 = ('north', 'south', 'east', 'west', 'up', 'down')


# ================================================================== colour helpers
def hexc(h, a=255):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (a,)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3)) + (a[3] if len(a) > 3 else 255,)


def shade(c, k):
    return tuple(max(0, min(255, int(round(c[i] * k)))) for i in range(3)) + (c[3] if len(c) > 3 else 255,)


def ramp(cols, t):
    t = max(0.0, min(1.0, t)) * (len(cols) - 1)
    i = min(len(cols) - 2, int(t))
    return mix(cols[i], cols[i + 1], t - i)


def noise(*k):
    """Deterministic 0..1 hash of integers/floats."""
    h = 2166136261
    for v in k:
        h = ((h ^ (int(math.floor(v * 7.0)) & 0xffffffff)) * 16777619) & 0xffffffff
    h ^= h >> 13; h = (h * 1274126177) & 0xffffffff; h ^= h >> 16
    return (h & 0xffff) / 65535.0


# ================================================================== model with per-face painted UVs
def face_corners(lo, hi, face):
    """(top-left, top-right, bottom-left) of a face seen from outside, in texture orientation (as Bedrock maps it)."""
    x0, y0, z0 = lo; x1, y1, z1 = hi
    return {'north': ([x1, y1, z0], [x0, y1, z0], [x1, y0, z0]),
            'south': ([x0, y1, z1], [x1, y1, z1], [x0, y0, z1]),
            'east': ([x1, y1, z1], [x1, y1, z0], [x1, y0, z1]),
            'west': ([x0, y1, z0], [x0, y1, z1], [x0, y0, z0]),
            'up': ([x1, y1, z0], [x0, y1, z0], [x1, y1, z1]),
            'down': ([x1, y0, z1], [x0, y0, z1], [x1, y0, z0])}[face]


class Ctx:
    """What a material sees for one texel: the face, the texel (i, j) of (nu, nv), the face's real size (W, H),
    the fractions fx, fy across it, the world point p (before cube rotation) and the cube's own params."""
    __slots__ = ('face', 'i', 'j', 'nu', 'nv', 'W', 'H', 'fx', 'fy', 'p', 'kw')


class Model:
    def __init__(self, tex_w=128):
        self.tex_w = tex_w
        self.bones = []          # [(name, [cube dicts])]
        self.faces = []          # (cube uv dict, face, nu, nv, painter) waiting for a texture patch
        self.tex_h = 0
        self.img = self.mer = None

    def bone(self, name):
        self.bones.append((name, []))
        return name

    def add(self, bone, lo, hi, mat, faces=ALL6, rot=None, pivot=None, **kw):
        if any(hi[i] - lo[i] <= 1e-6 for i in range(3)):
            return
        uv = {}
        c = {'origin': [round(v, 4) for v in lo], 'size': [round(hi[i] - lo[i], 4) for i in range(3)], 'uv': uv}
        if rot:
            c['pivot'] = [round(v, 4) for v in (pivot or [0, 0, 0])]
            c['rotation'] = [round(v, 4) for v in rot]
        for f in faces:
            tl, tr, bl = face_corners(lo, hi, f)
            W = math.dist(tl, tr); H = math.dist(tl, bl)
            nu, nv = max(1, math.ceil(W - 1e-6)), max(1, math.ceil(H - 1e-6))
            uv[f] = {'uv': [0, 0], 'uv_size': [round(W, 4), round(H, 4)]}

            def painter(i, j, f=f, tl=tl, tr=tr, bl=bl, W=W, H=H, nu=nu, nv=nv):
                ctx = Ctx()
                fx = min(1.0, (i + 0.5) / W); fy = min(1.0, (j + 0.5) / H)
                ctx.face, ctx.i, ctx.j, ctx.nu, ctx.nv, ctx.W, ctx.H, ctx.fx, ctx.fy = f, i, j, nu, nv, W, H, fx, fy
                ctx.p = [tl[k] + (tr[k] - tl[k]) * fx + (bl[k] - tl[k]) * fy for k in range(3)]
                ctx.kw = kw
                return mat(ctx)
            self.faces.append((uv[f], nu, nv, painter))
        dict(self.bones)[bone].append(c)

    def finish(self):
        """Shelf-pack every face patch (tallest first), then paint colour + MER."""
        order = sorted(range(len(self.faces)), key=lambda k: (-self.faces[k][2], -self.faces[k][1]))
        x = y = row_h = 0
        spots = {}
        for k in order:
            _, nu, nv, _ = self.faces[k]
            if x + nu > self.tex_w:
                x, y, row_h = 0, y + row_h, 0
            spots[k] = (x, y); x += nu; row_h = max(row_h, nv)
        used = y + row_h
        self.tex_h = 16
        while self.tex_h < used:
            self.tex_h *= 2
        self.img = Image.new('RGBA', (self.tex_w, self.tex_h), (0, 0, 0, 0))
        self.mer = Image.new('RGBA', (self.tex_w, self.tex_h), (0, 0, 0, 0))
        px, mp = self.img.load(), self.mer.load()
        for k, (uvd, nu, nv, painter) in enumerate(self.faces):
            u0, v0 = spots[k]
            uvd['uv'] = [u0, v0]
            for j in range(nv):
                for i in range(nu):
                    out = painter(i, j)
                    if out is None:
                        continue
                    col, mer = out if isinstance(out[0], tuple) else (out, (0, 0, 220))
                    px[u0 + i, v0 + j] = col
                    if col[3]:
                        mp[u0 + i, v0 + j] = tuple(mer) + (255,)

    def geometry(self, name):
        bones = [{'name': 'root', 'pivot': [0, 0, 0]}]
        for bname, cubes in self.bones:
            if bname != 'root':
                bones.append({'name': bname, 'parent': 'root', 'pivot': [0, 0, 0], 'cubes': cubes})
        return {'description': {'identifier': f'geometry.{NS}.{name}', 'texture_width': self.tex_w,
                                'texture_height': self.tex_h, 'visible_bounds_width': 2, 'visible_bounds_height': 2,
                                'visible_bounds_offset': [0, 0.5, 0]},
                'bones': bones}


def disc(m, bone, y0, y1, r, mat, faces=('up',), **kw):
    """A round slab of radius r made of non-overlapping z bands (the sides stay inside the tub's staves)."""
    bands = (0, 2.0, 3.4, 4.5, 5.3, 5.9)
    for k in range(len(bands) - 1):
        za, zb = bands[k], bands[k + 1]
        if za >= r:
            break
        zb = min(zb, r)
        half = math.sqrt(max(0.0, r * r - ((za + zb) / 2) ** 2))
        if k == 0:
            m.add(bone, [-half, y0, -zb], [half, y1, zb], mat, faces, **kw)
        else:
            m.add(bone, [-half, y0, za], [half, y1, zb], mat, faces, **kw)
            m.add(bone, [-half, y0, -zb], [half, y1, -za], mat, faces, **kw)


# ================================================================== 木盆 Wooden Tub
TUB_R, TUB_H, LEVEL = 7.0, 6.0, 4.5
WOODS = ['#a8743e', '#9a6838', '#b27e48', '#94623a', '#a46f3c', '#8c5c34', '#ae7a44', '#9e6c3a']
IRON = hexc('#4c4c54')


def wood_mat(ctx):
    base = hexc(ctx.kw.get('tone', '#a06e3c'))
    seed = ctx.kw.get('seed', 0)
    f = ctx.face
    if f in ('up', 'down'):                                        # end grain: lighter with a dark edge
        c = mix(base, hexc('#d0a06a'), 0.35)
        if ctx.i in (0, ctx.nu - 1):
            c = shade(c, 0.8)
        return c, (0, 0, 230)
    grain = noise(seed, ctx.i, 3)
    c = shade(base, 0.92 + 0.16 * grain)
    if noise(seed, ctx.i, ctx.j, 9) < 0.12:                        # knots and streaks along the grain
        c = shade(c, 0.82)
    if ctx.i == 0 or ctx.i == ctx.nu - 1:                         # the joint between staves
        c = shade(c, 0.78)
    if f == ctx.kw.get('inner'):                                   # inside: darker, wet below the water line
        c = shade(c, 0.78)
        if ctx.p[1] < LEVEL + 0.4:
            c = shade(mix(c, hexc('#4a3420'), 0.25), 0.9)
    elif ctx.p[1] < 1.0:
        c = shade(c, 0.85)                                         # damp foot
    if f == ctx.kw.get('outer') and ctx.p[1] > TUB_H - 1:
        c = mix(c, hexc('#c4925a'), 0.18)                          # sun-faded lip
    return c, (0, 0, 225)


def iron_mat(ctx):
    c = IRON
    if ctx.face == 'up':
        c = hexc('#7a7a84')
    elif ctx.face in ('south', 'north'):
        c = shade(IRON, 1.15) if ctx.j == 0 and ctx.nv > 1 else IRON
        if noise(ctx.kw.get('seed', 0), ctx.i, ctx.j) < 0.18:
            c = hexc('#6a4a32')                                    # rust
        if ctx.i == 0:
            c = shade(c, 0.85)
    return c, (190, 0, 120)


def rivet_mat(ctx):
    return (hexc('#9a9aa4') if ctx.face in ('south', 'up') else hexc('#5c5c64')), (210, 0, 90)


def bottom_mat(ctx):
    x, z = ctx.p[0], ctx.p[2]
    plank = math.floor((z + 7) / 3)
    c = shade(hexc('#8e6036'), 0.9 + 0.15 * noise(plank, 5))
    if abs((z + 7) / 3 - round((z + 7) / 3)) < 0.2:
        c = hexc('#5a3a20')
    if noise(plank, math.floor(x), 2) < 0.1:
        c = shade(c, 0.85)
    return c


def water_mat(ctx):
    x, z = ctx.p[0], ctx.p[2]
    r = math.hypot(x, z)
    c = mix(hexc('#3f84cc'), hexc('#24568f'), (r - 2) / 4)          # deeper colour towards the wall shadow
    if abs((z + 7) / 3 - round((z + 7) / 3)) < 0.2 and r < 4.5:
        c = shade(c, 0.9)                                          # the bottom planks showing through
    d = x + z
    if -3.5 < d < -1.5 and -4 < x - z < 3:
        c = mix(c, hexc('#d6ecff'), 0.85 if -3 < d < -2 else 0.45)  # sky highlight
    elif 2.5 < d < 3.5 and -1 < x - z < 2:
        c = mix(c, hexc('#a8d0f6'), 0.6)
    elif r > 5.4:
        c = mix(c, hexc('#7fb2e2'), 0.35)                          # meniscus against the staves
    return c, (0, 0, 20)


def brine_mat(ctx):
    x, z = ctx.p[0], ctx.p[2]
    r = math.hypot(x, z)
    n = noise(math.floor(x), math.floor(z), 7)
    c = mix(hexc('#b4cccc'), hexc('#8eaab0'), (r - 2) / 4)
    c = mix(c, hexc('#dfe9e4'), 0.35 * noise(math.floor(x / 2), math.floor(z / 2), 3))   # cloudy patches
    if n < 0.13:
        c = hexc('#f6f8f2')                                        # salt grains
    elif n > 0.93:
        c = hexc('#e2ebe6')
    d = x + z
    if -3 < d < -2 and -3 < x - z < 2:
        c = mix(c, hexc('#f4fbff'), 0.6)
    return c, (0, 0, 60)


def grain_mat(ctx):
    return hexc('#f8f8f2') if ctx.face == 'up' else hexc('#d8dedc')


CLAMS = [  # x, z, y rotation, palette
    (-3.0, -2.4, 22.5, 0), (0.6, 0.4, -30, 1), (3.4, -2.6, 60, 2), (-2.4, 2.8, -10, 2), (2.6, 3.0, 35, 0), (-4.0, 0.4, 80, 1)]
CLAM_PAL = [('#e4d4b2', '#b89a70', '#7a5a3a'),     # cream and brown
            ('#c8c4bc', '#8e8a84', '#5a5652'),     # grey hard clam
            ('#dcc2a8', '#a87c64', '#6e4a3c')]     # rose-brown


def clam_mat(ctx):
    light, mid, dark = (hexc(c) for c in CLAM_PAL[ctx.kw['pal']])
    part = ctx.kw['part']
    if part == 'hinge':
        return dark
    if ctx.face == 'up':
        # growth rings run across the shell, darkest at the hinge (-z), lighter towards the lip (+z)
        if part == 'cap':
            return mix(dark, mid, ctx.fy * 1.3)                    # the umbo, darkest at the hinge
        c = light if ctx.j % 2 == 0 else mid                       # growth rings
        if ctx.i in (0, ctx.nu - 1):
            c = shade(c, 0.85)
        if ctx.j == ctx.nv - 1:
            c = mix(light, hexc('#ffffff'), 0.3)                   # pale growing edge
        return c
    if part == 'base':                                             # the shell's side, banded
        return mid if ctx.i % 2 else shade(mid, 0.88)
    return shade(dark, 1.15)


def roe_mat(ctx):
    k = ctx.kw['k']
    tones = ['#f39234', '#f7a640', '#ee8228', '#f9b852', '#f29a3c']
    c = hexc(tones[k % len(tones)])
    if ctx.face == 'up':
        c = mix(c, hexc('#ffe0a0'), 0.45) if k % 3 else hexc('#c04a18')   # some eggs show the dark embryo spot
    elif ctx.face in ('north', 'west'):
        c = shade(c, 0.88)
    return c, (0, 0, 70)


def fry_mat(ctx):
    part = ctx.kw['part']
    if part == 'tail':
        return hexc('#8e9ea4')
    if ctx.face == 'up':
        return hexc('#4e5e66') if ctx.i else hexc('#3a464c')
    if ctx.face in ('east',):
        return hexc('#2a3036')                                     # snout / eyes end
    if ctx.face in ('north', 'south'):
        head = (ctx.i == ctx.nu - 1) if ctx.face == 'south' else (ctx.i == 0)
        return hexc('#1e2428') if head else hexc('#c4d0d4')       # eye spot at the head, silver flank
    return hexc('#b0bcc0')


def tub():
    m = Model(128)
    for b in ('tub', 'water', 'brine', 'clams', 'roe', 'fry'):
        m.bone(b)
    w = 2 * TUB_R * math.tan(math.radians(11.25)) + 0.06            # stave width at the outer face
    # 16 staves = 8 rotations x a pair on opposite sides (rotations stay within +-90)
    for k in range(8):
        a = -67.5 + 22.5 * k
        for side in (1, -1):
            idx = k * 2 + (side < 0)
            zlo, zhi = (TUB_R - 1, TUB_R) if side > 0 else (-TUB_R, -TUB_R + 1)
            kw = dict(tone=WOODS[(idx * 5) % len(WOODS)], seed=idx,
                      outer='south' if side > 0 else 'north', inner='north' if side > 0 else 'south')
            m.add('tub', [-w / 2, 0, zlo], [w / 2, TUB_H, zhi], wood_mat, ('north', 'south', 'up'),
                  rot=[0, a, 0], **kw)
    # the two lug staves (at +-x: rotation 90) rise above the rim with a hand hole
    for side in (1, -1):
        zlo, zhi = (TUB_R - 1, TUB_R) if side > 0 else (-TUB_R, -TUB_R + 1)
        kw = dict(tone='#a8743e', seed=40 + side, outer='south' if side > 0 else 'north', inner='north' if side > 0 else 'south')
        for x0, x1 in ((-w / 2, -0.5), (0.5, w / 2)):
            m.add('tub', [x0, TUB_H, zlo], [x1, TUB_H + 1.5, zhi], wood_mat, ('north', 'south', 'east', 'west'),
                  rot=[0, 90, 0], **kw)
        m.add('tub', [-w / 2, TUB_H + 1.5, zlo], [w / 2, TUB_H + 2.5, zhi], wood_mat, ('north', 'south', 'up', 'down', 'east', 'west'),
              rot=[0, 90, 0], **kw)
    # iron hoops: a band round the staves, rivets on every other stave
    hw = 2 * (TUB_R + 0.3) * math.tan(math.radians(11.25)) + 0.08
    for hy in (1.0, 4.0):
        for k in range(8):
            a = -67.5 + 22.5 * k
            for side in (1, -1):
                zlo, zhi = (TUB_R, TUB_R + 0.3) if side > 0 else (-TUB_R - 0.3, -TUB_R)
                outer = 'south' if side > 0 else 'north'
                m.add('tub', [-hw / 2, hy, zlo], [hw / 2, hy + 1.0, zhi], iron_mat, (outer, 'up'), rot=[0, a, 0],
                      seed=int(hy * 10 + k * 2 + side))
                if (k + (side > 0)) % 2 == 0:
                    rz = (TUB_R + 0.3, TUB_R + 0.55) if side > 0 else (-TUB_R - 0.55, -TUB_R - 0.3)
                    m.add('tub', [-0.3, hy + 0.25, rz[0]], [0.3, hy + 0.75, rz[1]], rivet_mat, (outer, 'up', 'east', 'west'),
                          rot=[0, a, 0])
    disc(m, 'tub', 0, 1, 6.4, bottom_mat, ('up', 'down'))
    # contents (tops only: the sides are hidden in the staves)
    disc(m, 'water', 1, LEVEL, 6.4, water_mat)
    disc(m, 'brine', 1, LEVEL, 6.4, brine_mat)
    for gx, gz in ((-1.2, -0.6), (1.8, 2.2), (-3.6, 3.6), (3.8, 0.2), (0.2, -4.2)):
        m.add('brine', [gx, LEVEL, gz], [gx + 0.5, LEVEL + 0.25, gz + 0.5], grain_mat, ('up', 'north', 'south', 'east', 'west'))
    for k, (x, z, a, pal) in enumerate(CLAMS):
        piv = [x, LEVEL, z]
        y0 = LEVEL - 0.3
        kw = dict(pal=pal)
        m.add('clams', [x - 1.3, y0, z - 1.0], [x + 1.3, y0 + 1.0, z + 1.0], clam_mat, ('up', 'north', 'south', 'east', 'west'),
              rot=[0, a, 0], pivot=piv, part='base', seam=y0 + 0.55, **kw)
        m.add('clams', [x - 0.9, y0 + 1.0, z - 0.8], [x + 0.9, y0 + 1.5, z + 0.6], clam_mat, ('up', 'north', 'south', 'east', 'west'),
              rot=[0, a, 0], pivot=piv, part='cap', **kw)
        m.add('clams', [x - 0.4, y0 + 0.9, z - 1.25], [x + 0.4, y0 + 1.3, z - 0.95], clam_mat, ('up', 'north', 'east', 'west'),
              rot=[0, a, 0], pivot=piv, part='hinge', **kw)
    # fish roe: three clumps of eggs floating at the surface
    k = 0
    for cx, cz in ((-2.0, -1.5), (2.2, 1.6), (-1.0, 3.2)):
        for dx, dy, dz in ((0, 0, 0), (1, 0, 0.2), (-1, 0, -0.2), (0.2, 0, 1), (-0.2, 0, -1), (1, 0, -1), (-1, 0, 1),
                           (0.5, 0.7, 0.5), (-0.5, 0.7, -0.5), (0.5, 0.75, -0.5), (0, 1.3, 0)):
            if noise(cx, cz, dx, dz, dy) < 0.12 and dy == 0 and (dx or dz):
                continue
            x, y, z = cx + dx * 0.8, LEVEL - 0.3 + dy * 0.8, cz + dz * 0.8
            m.add('roe', [x - 0.38, y, z - 0.38], [x + 0.38, y + 0.76, z + 0.38], roe_mat, ('up', 'north', 'south', 'east', 'west'), k=k)
            k += 1
    # fry: tiny silver fish just at the surface, heading every which way
    for k, (x, z, a) in enumerate(((-3.0, -2.0, 30), (1.0, -3.4, -60), (3.4, 1.2, 75), (-1.0, 1.0, -20), (0.8, 3.8, 10),
                                   (-4.2, 1.8, 50), (2.6, -0.8, -85))):
        piv = [x, LEVEL, z]
        y0 = LEVEL - 0.2
        m.add('fry', [x - 0.8, y0, z - 0.3], [x + 0.8, y0 + 0.6, z + 0.3], fry_mat, ('up', 'north', 'south', 'east', 'west'),
              rot=[0, a, 0], pivot=piv, part='body')
        m.add('fry', [x - 1.4, y0 - 0.1, z - 0.1], [x - 0.8, y0 + 0.7, z + 0.1], fry_mat, ('north', 'south', 'up'),
              rot=[0, a, 0], pivot=piv, part='tail')
    return m


# ================================================================== 曬鹽盤 Salt Pan
FLOOR, IN = 1.75, 6.5


def runner_mat(ctx):
    c = shade(hexc('#7e5430'), 0.9 + 0.2 * noise(ctx.kw['seed'], ctx.j, 1))
    if ctx.face in ('east', 'west'):
        c = mix(c, hexc('#a07040'), 0.3)
    if ctx.j == ctx.nv - 1 and ctx.face not in ('up', 'down'):
        c = shade(c, 0.8)
    return c


def clay_mat(ctx):
    x, y, z = ctx.p
    c = shade(hexc('#b4683e'), 0.92 + 0.14 * noise(math.floor(x), math.floor(y * 2), math.floor(z), 4))
    if noise(math.floor(x), math.floor(z), math.floor(y), 11) < 0.1:
        c = hexc('#9a5434')
    if ctx.face == 'up' and ctx.kw.get('floor'):
        c = shade(c, 0.88)
        if noise(math.floor(x), math.floor(z), 21) < 0.08:
            c = hexc('#8a4a2e')                                    # hairline cracks
    if ctx.kw.get('inner') == ctx.face:
        c = mix(c, hexc('#e8e0d4'), 0.35 if y > 2.0 else 0.15)       # salt stain inside the walls
    if ctx.face not in ('up', 'down') and y < 1.3:
        c = shade(c, 0.82)
    return c


def rim_mat(ctx):
    x, y, z = ctx.p
    along = x if ctx.kw['axis'] == 'x' else z
    c = shade(hexc('#b2834e'), 0.92 + 0.14 * noise(ctx.kw['seed'], math.floor(along / 2)))
    if ctx.face == 'up':
        if noise(ctx.kw['seed'], math.floor(along), 5) < 0.15:
            c = shade(c, 0.86)                                     # grain streaks
        if abs(abs(x) - 7.25) < 0.5 and abs(abs(z) - 7.25) < 0.5:
            c = hexc('#3a3a3e')                                    # nail head at each corner
    elif ctx.j == ctx.nv - 1:
        c = shade(c, 0.82)
    return c


def sea_mat(ctx):
    x, z = ctx.p[0], ctx.p[2]
    edge = IN - max(abs(x), abs(z))
    c = mix(hexc('#2f6cb4'), hexc('#4a92d6'), 0.5 + 0.5 * math.sin(x * 0.9 + z * 0.6))
    d = x - z
    if -1.2 < d < 0.4 and abs(x + z) < 7:
        c = mix(c, hexc('#e2f2ff'), 0.8 if -0.6 < d < 0.0 else 0.4)   # shine across the pan
    elif 4.5 < d < 5.4 and abs(x + z) < 4:
        c = mix(c, hexc('#bcdcf8'), 0.55)
    if edge < 0.6:
        c = mix(c, hexc('#d2e6f2'), 0.5)                           # a thin line where it meets the clay
    return c, (0, 0, 15)


def crust_edge(x, z):
    """How far the white crust reaches in from the walls at this point (ragged)."""
    return 1.6 + 1.4 * noise(math.floor(x / 1.5), math.floor(z / 1.5), 31) + 0.6 * noise(math.floor(x), math.floor(z), 32)


def half_water_mat(ctx):
    x, z = ctx.p[0], ctx.p[2]
    c = mix(hexc('#9cc4d8'), hexc('#7eaac6'), 0.5 + 0.5 * math.sin(x * 0.7 - z * 0.5))
    if noise(math.floor(x), math.floor(z), 8) < 0.1:
        c = hexc('#e6eef0')                                        # first crystals forming
    if -0.6 < x - z < 0.2 and abs(x + z) < 4:
        c = mix(c, hexc('#eef8ff'), 0.6)
    return c, (0, 0, 40)


def half_crust_mat(ctx):
    x, z = ctx.p[0], ctx.p[2]
    edge = IN - max(abs(x), abs(z))
    reach = crust_edge(x, z)
    if edge > reach:
        return (0, 0, 0, 0)                                        # open middle: the pale water shows
    c = hexc('#f4f2ea') if noise(math.floor(x), math.floor(z), 9) > 0.2 else hexc('#ffffff')
    if edge > reach - 0.8:
        c = hexc('#dfe4e0')                                        # wet, greyer edge of the crust
    return c, (0, 0, 200)


def salt_mat(ctx):
    x, y, z = ctx.p
    n = noise(math.floor(x), math.floor(y * 2), math.floor(z), 13)
    c = hexc('#f2f1ea')
    if n < 0.18:
        c = hexc('#ffffff')                                        # glints
    elif n < 0.3:
        c = hexc('#dde2e2')                                        # bluish shadow between crystals
    elif n > 0.92:
        c = hexc('#e8e2d2')
    if ctx.face in ('north', 'east', 'south', 'west'):
        c = shade(c, 0.94) if ctx.j else c
    return c, (0, 0, 170)


def rake_mat(ctx):
    part = ctx.kw['part']
    if part == 'handle':
        c = shade(hexc('#c09060'), 0.92 + 0.12 * noise(ctx.i, ctx.j, 6))
        if ctx.face == 'up':
            c = mix(c, hexc('#d8aa74'), 0.3)
        return c
    c = shade(hexc('#a87848'), 0.92 + 0.1 * noise(ctx.i, 2))
    if ctx.p[1] < 2.75 and ctx.face in ('north', 'south'):
        c = mix(c, hexc('#f0eee6'), 0.75)                          # salt caked on the blade
    return c


def salt_pan():
    m = Model(64)
    for b in ('pan', 'water', 'half', 'salt'):
        m.bone(b)
    for k, z0 in enumerate((-6.5, 4.5)):                           # two runners under the tray
        m.add('pan', [-8, 0, z0], [8, 1, z0 + 2], runner_mat, ('north', 'south', 'east', 'west', 'up'), seed=k)
    m.add('pan', [-7.5, 1, -7.5], [7.5, FLOOR, 7.5], clay_mat, ('up', 'down', 'north', 'south', 'east', 'west'), floor=True)
    for lo, hi, inner in (([-7.5, FLOOR, -7.5], [7.5, 2.5, -IN], 'south'), ([-7.5, FLOOR, IN], [7.5, 2.5, 7.5], 'north'),
                          ([-7.5, FLOOR, -IN], [-IN, 2.5, IN], 'east'), ([IN, FLOOR, -IN], [7.5, 2.5, IN], 'west')):
        m.add('pan', lo, hi, clay_mat, ('north', 'south', 'east', 'west'), inner=inner)
    for k, (lo, hi, axis) in enumerate(((([-8, 2.5, -8], [8, 3, -6.5], 'x')), ([-8, 2.5, 6.5], [8, 3, 8], 'x'),
                                        ([-8, 2.5, -6.5], [-6.5, 3, 6.5], 'z'), ([6.5, 2.5, -6.5], [8, 3, 6.5], 'z'))):
        m.add('pan', lo, hi, rim_mat, ('up', 'down', 'north', 'south', 'east', 'west'), axis=axis, seed=k)
    m.add('water', [-IN, FLOOR, -IN], [IN, 2.2, IN], sea_mat, ('up',))
    m.add('half', [-IN, FLOOR, -IN], [IN, 1.95, IN], half_water_mat, ('up',))
    m.add('half', [-IN, FLOOR, -IN], [IN, 2.15, IN], half_crust_mat, ('up',))
    m.add('salt', [-IN, FLOOR, -IN], [IN, 2.4, IN], salt_mat, ('up',))
    for lo, hi in (([-4.5, 2.4, -3.0], [1.5, 3.1, 2.0]), ([-3.5, 3.1, -2.2], [0.5, 3.7, 1.2]), ([-2.5, 3.7, -1.4], [-0.5, 4.2, 0.4])):
        m.add('salt', lo, hi, salt_mat, ('up', 'north', 'south', 'east', 'west'))
    # the salt rake: blade standing in the salt, handle resting across the rim
    piv = [2.5, 3.0, 7.25]
    m.add('salt', [0.0, 2.2, 1.6], [5.0, 3.4, 2.0], rake_mat, ('up', 'north', 'south', 'east', 'west'), rot=[0, -20, 0], pivot=piv,
          part='blade')
    m.add('salt', [2.2, 3.0, 2.0], [2.8, 3.6, 9.5], rake_mat, ('up', 'down', 'north', 'south', 'east', 'west'), rot=[0, -20, 0],
          pivot=piv, part='handle')
    return m


# ================================================================== 熔岩魚缸 Lava Fish Tank
LAVA_TOP = 3.0
LAVA_COLS = [hexc('#2a120c'), hexc('#6e1e0c'), hexc('#c8400e'), hexc('#f2741a'), hexc('#ffb030'), hexc('#ffe27a')]


def lava_heat(x, z, y=0.0):
    """0..1 how molten the lava is here: crust plates drift on a bright flow."""
    v = (0.55 + 0.28 * math.sin(x * 0.8 + z * 0.5) + 0.22 * math.sin(z * 1.2 - x * 0.45 + 1.0)
         + 0.12 * (noise(math.floor(x), math.floor(z), math.floor(y), 41) - 0.5))
    return max(0.0, min(1.0, v))


def lava_mat(ctx):
    x, y, z = ctx.p
    if ctx.face == 'up':
        t = lava_heat(x, z)
        t = 0.15 + t * 0.85 if t > 0.32 else t * 0.6                 # crust islands stay dark
    else:                                                           # sides seen through the glass: hotter on top
        t = 0.45 + 0.4 * (y - 1.0) / (LAVA_TOP - 1.0) + 0.2 * (noise(math.floor(x + z), math.floor(y * 2), 42) - 0.5)
    c = ramp(LAVA_COLS, t)
    return c, (0, int(max(0, min(255, (t - 0.25) * 340))), 180)


def blackstone_mat(ctx):
    x, y, z = ctx.p
    c = shade(hexc('#2e2a30'), 0.9 + 0.22 * noise(math.floor(x), math.floor(y * 2), math.floor(z), 51))
    if ctx.face not in ('up', 'down'):
        row = math.floor(y * 2)
        u = x if ctx.face in ('north', 'south') else z
        if (y * 2) % 1 < 0.01 or abs(((u + (row % 2) * 2) % 4)) < 0.5:
            c = hexc('#1c1a1e')                                    # brick joints
        if ctx.j == 0:
            c = mix(c, hexc('#4a4450'), 0.4)
    else:
        if noise(math.floor(x), math.floor(z), 52) < 0.08:
            c = hexc('#3e1a14')                                    # scorch
    return c, (0, 0, 210)


def frame_iron_mat(ctx):
    c = hexc('#38363c')
    if ctx.face == 'up':
        c = hexc('#56535c')
    elif ctx.i == 0 and ctx.nu > 0:
        c = hexc('#4a4850')                                        # lit edge
    if ctx.face not in ('up', 'down') and ctx.nv > 3 and ctx.j in (0, ctx.nv - 1):
        c = hexc('#62606a')                                        # rivet at each end of a post
    if noise(ctx.i, ctx.j, math.floor(ctx.p[1]), 61) < 0.07:
        c = hexc('#4a2e24')                                        # heat tarnish
    return c, (200, 0, 110)


def glass_mat(ctx):
    x, y, z = ctx.p
    u = x if ctx.face in ('north', 'south') else z
    edge = min(ctx.i, ctx.nu - 1 - ctx.i, ctx.j, ctx.nv - 1 - ctx.j) if ctx.face not in ('up', 'down') else 3
    a = 34
    col = (255, 226, 190)
    if y < 4.5:                                                     # heat haze just above the lava
        t = (4.5 - y) / 3.0
        col = mix(col + (255,), (255, 150, 80, 255), t)[:3]
        a = int(34 + 30 * t)
    if edge == 0:
        a += 26                                                     # the pane looks thicker at its edges
    d = u + y * 0.7
    if ctx.face not in ('up', 'down') and (abs(d - 6.2) < 0.45 or abs(d - 8.0) < 0.35):
        col, a = (255, 248, 236), 112                               # two diagonal glints
    return (col[0], col[1], col[2], a), (0, 0, 10)


def basalt_mat(ctx):
    x, y, z = ctx.p
    if ctx.face == 'up':
        ring = ctx.i in (0, ctx.nu - 1) or ctx.j in (0, ctx.nv - 1)
        c = hexc('#5a5a62') if ring else hexc('#46464e')
    else:
        c = hexc('#4a4a52') if ctx.i % 2 == 0 else hexc('#3a3a42')    # columnar ridges
        if y < LAVA_TOP + 0.6:
            c = mix(c, hexc('#8a2a10'), 0.5)                        # glow on the foot
        if noise(ctx.i, math.floor(y), math.floor(x + z), 71) < 0.1:
            c = shade(c, 0.8)
    return c, (0, 0, 200)


def magma_mat(ctx):
    x, y, z = ctx.p
    n = noise(math.floor(x), math.floor(y), math.floor(z), ctx.face == 'up', 81)
    crack = n < 0.33
    if crack:
        c = hexc('#ff8a22') if n < 0.18 else hexc('#d24a12')
        return c, (0, 230 if n < 0.18 else 150, 180)
    return hexc('#4a2018') if n > 0.7 else hexc('#3a1a14'), (0, 0, 200)


def lava_tank():
    m = Model(128)
    for b in ('frame', 'lava'):
        m.bone(b)
    # opaque parts first, the glass last
    m.add('frame', [-7, 0, -5], [7, 1, 5], blackstone_mat, ALL6)
    for x in (-7, 6):
        for z in (-5, 4):
            m.add('frame', [x, 1, z], [x + 1, 13, z + 1], frame_iron_mat, ('north', 'south', 'east', 'west', 'up'))
    for y0, y1 in ((1, 1.5), (12, 13)):                              # bottom and top rims between the posts
        m.add('frame', [-6, y0, -5], [6, y1, -4.4], frame_iron_mat, ('north', 'south', 'up', 'down'))
        m.add('frame', [-6, y0, 4.4], [6, y1, 5], frame_iron_mat, ('north', 'south', 'up', 'down'))
        m.add('frame', [-7, y0, -4], [-6.4, y1, 4], frame_iron_mat, ('east', 'west', 'up', 'down'))
        m.add('frame', [6.4, y0, -4], [7, y1, 4], frame_iron_mat, ('east', 'west', 'up', 'down'))
    # lava bed (2 pixels deep) with basalt columns at the back and a magma rock at the front
    m.add('lava', [-6.4, 1, -4.4], [6.4, LAVA_TOP, 4.4], lava_mat, ('up', 'north', 'south', 'east', 'west'))
    for lo, hi in (([-6.2, 1, 2.0], [-4.2, 6.0, 4.2]), ([-4.2, 1, 2.8], [-3.0, 4.4, 4.2]), ([-6.2, 1, 0.6], [-5.0, 3.8, 2.0]),
                   ([4.0, 1, 2.6], [6.2, 4.8, 4.2]), ([3.0, 1, 3.2], [4.0, 3.6, 4.2])):
        m.add('lava', lo, hi, basalt_mat, ('up', 'north', 'south', 'east', 'west'))
    m.add('lava', [2.6, 1, -3.8], [4.6, 3.8, -2.2], magma_mat, ('up', 'north', 'south', 'east', 'west'))
    m.add('lava', [-1.6, 1, -3.4], [-0.6, 3.4, -2.6], magma_mat, ('up', 'north', 'south', 'east', 'west'))
    # glass: faint warm panes
    m.add('frame', [-6, 1.5, -5], [6, 12, -4.55], glass_mat, ('north', 'south'))
    m.add('frame', [-6, 1.5, 4.55], [6, 12, 5], glass_mat, ('north', 'south'))
    m.add('frame', [-7, 1.5, -4], [-6.55, 12, 4], glass_mat, ('east', 'west'))
    m.add('frame', [6.55, 1.5, -4], [7, 12, 4], glass_mat, ('east', 'west'))
    return m


# ================================================================== the first-pass Fish Pond Feeder (only with --pond-feeder)
def pond_feeder():
    """The Fish Pond Feeder (魚池餵食台): a short post with a feed trough on top and a small net basket hanging in front,
    where the pond's roe shows. Bones: feeder | feed (pellets in the trough) | roe (an orange clump in the basket)."""
    from modelkit import Atlas, box
    a = Atlas(64, 64)
    wood, dark, net = '#a8743e', '#6e4826', '#d8d0b0'
    cubes = [box(-2, 2, 0, 9, -2, 2, wood, dark, atlas=a),                                   # the post
             box(-6, 6, 9, 10, -4, 4, wood, dark, dark, atlas=a),                             # the trough floor
             box(-6, 6, 10, 12, -4, -3, wood, dark, atlas=a), box(-6, 6, 10, 12, 3, 4, wood, dark, atlas=a),
             box(-6, -5, 10, 12, -3, 3, wood, dark, atlas=a), box(5, 6, 10, 12, -3, 3, wood, dark, atlas=a),
             box(-1, 1, 4, 9, -6, -2, wood, dark, atlas=a),                                   # the arm to the basket
             box(-3, 3, 1, 1.5, -9, -5, net, atlas=a), box(-3, 3, 1.5, 4, -9.1, -9, net, atlas=a),   # the basket
             box(-3, 3, 1.5, 4, -5, -4.9, net, atlas=a), box(-3.1, -3, 1.5, 4, -9, -5, net, atlas=a),
             box(3, 3.1, 1.5, 4, -9, -5, net, atlas=a)]
    feed = [box(-5, 5, 10, 11.2, -3, 3, '#b08a52', '#8a6838', atlas=a)] + \
           [box(x - 0.6, x + 0.6, 11.2, 11.8, z - 0.6, z + 0.6, '#c49a5e', atlas=a) for x, z in ((-3, -1), (0, 1.5), (3, -1.5), (1.5, 0))]
    roe = [box(x - 0.8, x + 0.8, 1.5, 3.2, z - 0.8, z + 0.8, '#f2a24a', '#c8762a', atlas=a)
           for x, z in ((-1.5, -7.5), (0, -6.5), (1.5, -7.5), (-0.5, -8), (0.8, -6))]
    bone = lambda name, cs: {'name': name, 'parent': 'root', 'pivot': [0, 0, 0], 'cubes': cs}
    bones = [{'name': 'root', 'pivot': [0, 0, 0]}, bone('feeder', cubes), bone('feed', feed), bone('roe', roe)]
    return a, bones


def write_pond_feeder():
    from modelkit import write_geometries, texture_set
    atlas, bones = pond_feeder()
    write_geometries(os.path.join(RP, 'models', 'blocks', 'pond_feeder.geo.json'), [{'description': {
        'identifier': f'geometry.{NS}.pond_feeder', 'texture_width': atlas.w, 'texture_height': atlas.h,
        'visible_bounds_width': 2, 'visible_bounds_height': 2, 'visible_bounds_offset': [0, 0.5, 0]}, 'bones': bones}])
    png = os.path.join(RP, 'textures', 'blocks', 'kfv_pond_feeder.png')
    atlas.save(png)
    texture_set(png)
    book_picture('pond_feeder', ('root', 'feeder', 'feed', 'roe'))


# ================================================================== writing
def write(name, m):
    m.finish()
    path = os.path.join(RP, 'models', 'blocks', f'{name}.geo.json')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'format_version': '1.16.0', 'minecraft:geometry': [m.geometry(name)]}, f, indent=1)
        f.write('\n')
    png = os.path.join(RP, 'textures', 'blocks', f'kfv_{name}.png')
    m.img.save(png)
    ts = {'format_version': '1.16.100', 'minecraft:texture_set': {
        'color': f'kfv_{name}', 'metalness_emissive_roughness': f'kfv_{name}_mer', 'heightmap': f'kfv_{name}_height'}}
    with open(png[:-4] + '.texture_set.json', 'w', encoding='utf-8', newline='\n') as f:
        json.dump(ts, f, indent=2)
        f.write('\n')
    pbr.refresh(png)                     # height map from the new colours
    m.mer.save(png[:-4] + '_mer.png')    # then the painted MER (pbr.refresh would flatten the lava's glow)
    tpath = os.path.join(RP, 'textures', 'terrain_texture.json')
    t = json.load(open(tpath, encoding='utf-8'))
    if t['texture_data'].get(f'kfv_{name}') != {'textures': f'textures/blocks/kfv_{name}'}:
        t['texture_data'][f'kfv_{name}'] = {'textures': f'textures/blocks/kfv_{name}'}
        with open(tpath, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(t, f, indent=2, ensure_ascii=False)
    cubes = sum(len(c) for _, c in m.bones)
    print(f'{name}: {cubes} cubes, texture {m.tex_w}x{m.tex_h}')


def book_picture(name, show):
    """The guidebook's 128x128 picture (also the item icon), rendered from the model with the bones in `show`."""
    spec = importlib.util.spec_from_file_location('rm', os.path.join(ROOT, 'tools', 'render_models.py'))
    rm = importlib.util.module_from_spec(spec); spec.loader.exec_module(rm)
    g = json.load(open(os.path.join(RP, 'models', 'blocks', f'{name}.geo.json'), encoding='utf-8'))['minecraft:geometry'][0]
    g = json.loads(json.dumps(g))
    g['bones'] = [b for b in g['bones'] if b['name'] in show]
    g['description']['identifier'] = 'tmp'
    rm.GEOS['tmp'] = g
    tex = Image.open(os.path.join(RP, 'textures', 'blocks', f'kfv_{name}.png')).convert('RGBA')
    big = rm.render(rm.quads('tmp', tex), 256, 225, -30)
    bb = big.getbbox()
    side = max(bb[2] - bb[0], bb[3] - bb[1]); cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    big = big.crop((int(cx - side / 2), int(cy - side / 2), int(cx + side / 2), int(cy + side / 2))).resize((124, 124), Image.LANCZOS)
    out = Image.new('RGBA', (128, 128), (0, 0, 0, 0)); out.alpha_composite(big, (2, 2))
    out.save(os.path.join(RP, 'textures', 'ui', 'kfv_book', f'kfv_{name}.png'))


def main():
    for name, make, show in (('wooden_tub', tub, ('root', 'tub', 'brine', 'clams')),
                             ('salt_pan', salt_pan, ('root', 'pan', 'salt')),
                             ('lava_fish_tank', lava_tank, ('root', 'frame', 'lava'))):
        write(name, make())
        book_picture(name, show)
    if '--pond-feeder' in sys.argv:
        write_pond_feeder()


if __name__ == '__main__':
    main()
