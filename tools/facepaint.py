"""Hand-built box models with every face painted in code: a small kit for the polished 1.5.0 models.

    sheet = Sheet()                                   # one texture, shared by any number of geometries
    g = Part(sheet, density=1)                        # texture pixels per model unit for this geometry
    g.box(lo, hi, shader)                             # an axis-aligned box; returns the cube dict (per-face UVs)
    sheet.save(png)                                   # packs the faces, paints them, writes the png (and _mer)

Every face gets its own rectangle in the texture, density x its size in pixels, so nothing is stretched. The
rectangles are packed when the sheet is saved: the UV dicts handed out by box() are filled in then, so write the
geometry after sheet.save(). Identical boxes (same corners, shader and faces) share their rectangles, as the
16 hands of the wall tide clock do.

A shader is a function shader(p, n) of a point p on the face and the face's outward normal n, both in the
part's source coordinates (see Part.to_src), returning '#rrggbb', an (r, g, b, a) tuple, None for a hole, or
(colour, (metal, emissive, rough)) to set the pixel's MER too. Texel centres are found with the same face
orientation as Bedrock (and tools/render_models.py):
    up    left x1 right x0, top z0 bottom z1        down  left x1 right x0, top z1 bottom z0
    north left x1 right x0, top y1 bottom y0        south left x0 right x1, top y1 bottom y0
    east  left z1 right z0                          west  left z0 right z1
"""
import math, os

from PIL import Image

import pbr

FACES = ('north', 'south', 'east', 'west', 'up', 'down')
NORMAL = {'north': (0, 0, -1), 'south': (0, 0, 1), 'east': (1, 0, 0), 'west': (-1, 0, 0), 'up': (0, 1, 0), 'down': (0, -1, 0)}


def rgba(c):
    if c is None:
        return None
    if isinstance(c, str):
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + ((int(c[7:9], 16),) if len(c) == 9 else (255,))
    return tuple(int(max(0, min(255, v))) for v in c[:3]) + ((int(c[3]),) if len(c) == 4 else (255,))


def mix(a, b, t):
    a, b = rgba(a), rgba(b)
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def shade(c, k):
    """Brighter (k > 1) or darker (k < 1)."""
    c = rgba(c)
    return tuple(int(max(0, min(255, v * k))) for v in c[:3]) + (c[3],)


def hash01(*v):
    """A repeatable pseudo-random number in [0, 1) for integer-ish coordinates."""
    h = 2166136261
    for x in v:
        h = ((h ^ (int(math.floor(x)) & 0xffffffff)) * 16777619) & 0xffffffff
    h ^= h >> 13
    h = (h * 1274126177) & 0xffffffff
    return (h & 0xffffff) / 0x1000000


def corners(lo, hi, face):
    """(top-left, top-right, bottom-left) of a face seen from outside, in texture orientation."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    return {'north': ([x1, y1, z0], [x0, y1, z0], [x1, y0, z0]), 'south': ([x0, y1, z1], [x1, y1, z1], [x0, y0, z1]),
            'east': ([x1, y1, z1], [x1, y1, z0], [x1, y0, z1]), 'west': ([x0, y1, z0], [x0, y1, z1], [x0, y0, z0]),
            'up': ([x1, y1, z0], [x0, y1, z0], [x1, y1, z1]), 'down': ([x1, y0, z1], [x0, y0, z1], [x1, y0, z0])}[face]


class Sheet:
    def __init__(self, width=None):
        self.width = width
        self.requests = []            # [w, h, [uv dicts to fill], paint job]
        self.shared = {}
        self.size = None

    def request(self, key, w, h, uvd, job):
        if key in self.shared:
            self.shared[key][2].append(uvd)
            return
        r = [w, h, [uvd], job]
        self.shared[key] = r
        self.requests.append(r)

    def pack(self):
        area = sum(max(1, r[0]) * max(1, r[1]) for r in self.requests)
        widest = max(r[0] for r in self.requests)
        W = self.width or max(32, 1 << math.ceil(math.log2(max(widest, math.sqrt(area * 1.25)))))
        x = y = shelf = 0
        place = {}
        for r in sorted(self.requests, key=lambda r: (-r[1], -r[0])):
            w, h = max(1, r[0]), max(1, r[1])
            if x + w > W:
                x, y, shelf = 0, y + shelf, 0
            place[id(r)] = (x, y)
            x += w
            shelf = max(shelf, h)
        H = 1 << math.ceil(math.log2(max(16, y + shelf)))
        if H > 2 * W:
            self.width = W * 2
            return self.pack()
        self.size = (W, H)
        return place

    def save(self, png, mer=True):
        place = self.pack()
        W, H = self.size
        im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        mer_im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        px, mp = im.load(), mer_im.load()
        any_mer = False
        for r in self.requests:
            u0, v0 = place[id(r)]
            w, h, uvds, job = r
            for d in uvds:
                d['uv'] = [u0, v0]
            for i in range(max(1, w)):
                for j in range(max(1, h)):
                    out = job(i, j)
                    if isinstance(out, tuple) and len(out) == 2 and isinstance(out[1], tuple):
                        col, m = out
                        if col is not None:
                            mp[u0 + i, v0 + j] = tuple(m) + (255,)
                            any_mer = True
                    else:
                        col = out
                    col = rgba(col)
                    if col is not None and col[3] > 0:
                        px[u0 + i, v0 + j] = col
        im.save(png)
        written = pbr.refresh(png)
        if mer and any_mer:
            path = png[:-4] + '_mer.png'
            base = Image.open(path).convert('RGBA') if os.path.exists(path) else Image.new('RGBA', (W, H))
            bp = base.load()
            cp = im.load()
            for y in range(H):
                for x in range(W):
                    if cp[x, y][3] and mp[x, y][3]:
                        bp[x, y] = mp[x, y]
            base.save(path)
        return written


class Part:
    """The boxes of one geometry. to_src(p) maps a model point to the coordinates the shaders use (and
    to_src_n a normal); the default is the identity."""

    def __init__(self, sheet, density=1.0, to_src=None, to_src_n=None):
        self.sheet, self.density = sheet, density
        self.to_src = to_src or (lambda p: p)
        self.to_src_n = to_src_n or (lambda n: n)

    def box(self, lo, hi, shader, faces=FACES, rotation=None, pivot=None, inflate=None, shaders=None):
        """shaders: optional {face: shader} overriding `shader` for some faces."""
        lo = [round(v, 4) for v in lo]
        hi = [round(v, 4) for v in hi]
        assert all(hi[i] > lo[i] for i in range(3)), (lo, hi)
        uv = {}
        for f in faces:
            sh = (shaders or {}).get(f, shader)
            if sh is None:
                continue
            tl, tr, bl = corners(lo, hi, f)
            lu = math.dist(tl, tr) * self.density
            lv = math.dist(tl, bl) * self.density
            w, h = max(1, math.ceil(lu - 1e-6)), max(1, math.ceil(lv - 1e-6))
            d = {'uv': [0, 0], 'uv_size': [round(lu, 4), round(lv, 4)]}
            uv[f] = d
            n = self.to_src_n(NORMAL[f])

            def job(i, j, tl=tl, tr=tr, bl=bl, lu=lu, lv=lv, sh=sh, n=n):
                fu = (i + min(i + 1, lu)) / 2 / lu if lu > 0 else 0.5
                fv = (j + min(j + 1, lv)) / 2 / lv if lv > 0 else 0.5
                p = [tl[k] + (tr[k] - tl[k]) * fu + (bl[k] - tl[k]) * fv for k in range(3)]
                return sh(self.to_src(p), n)
            key = (id(self), id(sh), tuple(lo), tuple(hi), f)
            self.sheet.request(key, w, h, d, job)
        c = {'origin': lo, 'size': [round(hi[i] - lo[i], 4) for i in range(3)], 'uv': uv}
        if rotation:
            c['rotation'] = rotation
            c['pivot'] = [round(v, 4) for v in (pivot or [0, 0, 0])]
        if inflate:
            c['inflate'] = inflate
        return c
