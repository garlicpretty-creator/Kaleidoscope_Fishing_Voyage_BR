"""Textured isometric previews of the pack's 3D models, as contact sheets.

usage: python tools/render_models.py <out_dir>

Every texture pixel of every visible cube face becomes a small projected quad, drawn far-to-near with simple
face lighting, so the preview shows the real texture and geometry. Writes:
  blocks.png       one model per block (the state with the most cubes), two views each
  entities.png     mobs, bobber, worn/held items, stockpot layer
  tank_fish.png    every fish that can swim in the fish tank
"""
import json, os, re, sys, glob, math
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
BP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [BP]')
try:
    FONT = ImageFont.truetype(r'C:\Windows\Fonts\msjh.ttc', 15)
except OSError:                       # not on Windows: labels in the default font (only review sheets use them)
    FONT = ImageFont.load_default()


def load(path):
    with open(path, encoding='utf-8-sig') as f:
        t = f.read()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return json.loads(re.sub(r'(?m)^\s*//.*$', '', t))


def g_escape(p):
    return glob.escape(p)


GEOS = {}
for path in glob.glob(os.path.join(g_escape(RP), 'models', '**', '*.json'), recursive=True):
    for g in load(path).get('minecraft:geometry', []):
        GEOS[g['description']['identifier']] = g

ZH = {}
with open(os.path.join(RP, 'texts', 'zh_TW.lang'), encoding='utf-8') as f:
    for line in f:
        m = re.match(r'kaleidoscope_fishing\.(?:name|display\.item|block)\.([\w.]+?)(?:\.name)?=([^\\\n]*)', line)
        if m and m.group(1) not in ZH:
            ZH[m.group(1)] = m.group(2)
        m = re.match(r'entity\.kaleidoscope_fishing:(\w+)\.name=(.*)', line)
        if m:
            ZH[m.group(1)] = m.group(2).strip()


def png_for(path):
    for ext in ('.png', '.tga'):
        p = os.path.join(RP, path + ext)
        if os.path.exists(p):
            return p
    return None


# ------------------------------------------------------------------ geometry -> faces
def rot(p, pivot, r):
    x, y, z = (p[i] - pivot[i] for i in range(3))
    rx, ry, rz = (math.radians(a) for a in r)
    # Bedrock: bone rotation applied Z, then Y, then X when transforming a point outward; X/Y are negated
    rx, ry = -rx, -ry
    x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
    x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
    y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
    return [x + pivot[0], y + pivot[1], z + pivot[2]]


def box_uv(u, v, s, mirror):
    dx, dy, dz = (math.floor(abs(t)) if abs(t) >= 1 else abs(t) for t in s)
    f = {'east': ([u, v + dz], [dz, dy]), 'north': ([u + dz, v + dz], [dx, dy]),
         'west': ([u + dz + dx, v + dz], [dz, dy]), 'south': ([u + 2 * dz + dx, v + dz], [dx, dy]),
         'up': ([u + dz, v], [dx, dz]), 'down': ([u + dz + dx, v + dz], [dx, -dz])}
    if mirror:
        f['east'], f['west'] = f['west'], f['east']
        for k in f:
            (a, b), (w, h) = f[k]
            f[k] = ([a + w, b], [-w, h])
    return f


def face_corners(lo, hi, face):
    """Corners as (top-left, top-right, bottom-left) of the face seen from outside, in texture orientation."""
    x0, y0, z0 = lo; x1, y1, z1 = hi
    if face == 'north':
        return [x1, y1, z0], [x0, y1, z0], [x1, y0, z0]
    if face == 'south':
        return [x0, y1, z1], [x1, y1, z1], [x0, y0, z1]
    if face == 'east':
        return [x1, y1, z1], [x1, y1, z0], [x1, y0, z1]
    if face == 'west':
        return [x0, y1, z0], [x0, y1, z1], [x0, y0, z0]
    if face == 'up':
        return [x1, y1, z0], [x0, y1, z0], [x1, y1, z1]
    if face == 'down':
        return [x1, y0, z1], [x0, y0, z1], [x1, y0, z0]


LIGHT_FLOOR = 0.55            # darkest face shade; icon rendering raises it

NORMAL = {'north': (0, 0, -1), 'south': (0, 0, 1), 'east': (1, 0, 0), 'west': (-1, 0, 0), 'up': (0, 1, 0), 'down': (0, -1, 0)}


def quads(gid, tex, hidden=()):
    g = GEOS[gid]
    tw = g['description'].get('texture_width', 64); th = g['description'].get('texture_height', 64)
    texmap = tex if isinstance(tex, dict) else {'*': tex}
    loaded = {k: (v, v.load(), v.width / tw, v.height / th) for k, v in texmap.items()}
    bones = {b['name']: b for b in g.get('bones', [])}

    def chain(b):
        out = []
        while b:
            out.append(b); b = bones.get(b.get('parent'))
        return out
    out = []
    for b in g.get('bones', []):
        if any(bb['name'] in hidden for bb in chain(b)):
            continue
        for c in b.get('cubes', []):
            s = c['size']; o = c['origin']; inf = c.get('inflate', 0)
            lo = [o[i] - inf for i in range(3)]; hi = [o[i] + s[i] + inf for i in range(3)]
            uv = c.get('uv', [0, 0])
            if isinstance(uv, list):
                faces = {k: (a, b_, '*') for k, (a, b_) in
                         box_uv(uv[0], uv[1], s, c.get('mirror', b.get('mirror', False))).items()}
            else:
                faces = {k: (v['uv'], v.get('uv_size', [0, 0]), v.get('material_instance', '*'))
                         for k, v in uv.items() if isinstance(v, dict) and 'uv' in v}
            for face, (fuv, fus, mat) in faces.items():
                tex_, px, sx, sy = loaded.get(mat) or loaded['*']
                if face not in NORMAL:
                    continue
                tl, tr, bl = face_corners(lo, hi, face)
                nu = max(1, math.ceil(abs(fus[0]) * sx - 1e-6)); nv = max(1, math.ceil(abs(fus[1]) * sy - 1e-6))
                ex = [(tr[i] - tl[i]) / nu for i in range(3)]; ey = [(bl[i] - tl[i]) / nv for i in range(3)]
                n = list(NORMAL[face])
                for i in range(nu):
                    for j in range(nv):
                        tu = (fuv[0] + (i + 0.5) / nu * fus[0]) * sx; tv = (fuv[1] + (j + 0.5) / nv * fus[1]) * sy
                        col = px[min(tex_.width - 1, max(0, int(tu))), min(tex_.height - 1, max(0, int(tv)))]
                        if len(col) == 4 and col[3] < 100:
                            continue
                        p0 = [tl[k] + ex[k] * i + ey[k] * j for k in range(3)]
                        pts = [p0, [p0[k] + ex[k] for k in range(3)], [p0[k] + ex[k] + ey[k] for k in range(3)],
                               [p0[k] + ey[k] for k in range(3)]]
                        nn = n[:]
                        if c.get('rotation'):
                            pts = [rot(p, c.get('pivot', [0, 0, 0]), c['rotation']) for p in pts]
                            nn = [a - b for a, b in zip(rot(n, [0, 0, 0], c['rotation']), [0, 0, 0])]
                        for bb in chain(b):
                            if bb.get('rotation'):
                                pts = [rot(p, bb.get('pivot', [0, 0, 0]), bb['rotation']) for p in pts]
                                nn = rot(nn, [0, 0, 0], bb['rotation'])
                        out.append((pts, nn, col[:3]))
    return out


def render(qs, size, yaw, pitch=-30):
    if not qs:
        return Image.new('RGBA', (size, size))
    cy, sy_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))

    def view(p):
        x = p[0] * cy - p[2] * sy_; z = p[0] * sy_ + p[2] * cy; y = p[1]
        y2 = y * cp - z * sp; z2 = y * sp + z * cp
        return x, y2, z2
    light = (-0.45, 0.85, -0.3)
    items = []
    for pts, n, col in qs:
        vn = view(n)
        if vn[2] > 1e-6:          # facing away from the camera (camera looks along +z in view space)
            continue
        v = [view(p) for p in pts]
        depth = sum(p[2] for p in v) / 4
        lam = LIGHT_FLOOR + (1 - LIGHT_FLOOR) * max(0, (n[0] * light[0] + n[1] * light[1] + n[2] * light[2]) /
                                 max(1e-6, math.sqrt(sum(a * a for a in n))))
        items.append((depth, v, tuple(min(255, int(c * lam)) for c in col)))
    xs = [p[0] for _, v, _ in items for p in v]; ys = [p[1] for _, v, _ in items for p in v]
    if not xs:
        return Image.new('RGBA', (size, size))
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1e-6)
    k = (size - 8) / span; cx = (max(xs) + min(xs)) / 2; cyy = (max(ys) + min(ys)) / 2
    ss = 2                                                   # supersample for cleaner edges
    im = Image.new('RGBA', (size * ss, size * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for depth, v, col in sorted(items, key=lambda t: -t[0]):
        poly = [((p[0] - cx) * k * ss + size * ss / 2, -(p[1] - cyy) * k * ss + size * ss / 2) for p in v]
        d.polygon(poly, fill=col + (255,), outline=col + (255,))
    return im.resize((size, size), Image.LANCZOS)


# ------------------------------------------------------------------ what to render
def block_models():
    terrain = load(os.path.join(RP, 'textures', 'terrain_texture.json'))['texture_data']
    by_file = {}
    for path in sorted(glob.glob(os.path.join(g_escape(BP), 'blocks', '*.json'))):
        blk = load(path).get('minecraft:block', {})
        bid = blk.get('description', {}).get('identifier', '').split(':')[-1]
        comps = [blk.get('components', {})] + [p.get('components', {}) for p in blk.get('permutations', [])]
        mats = {}
        for comp in comps[:1]:
            for k, v in comp.get('minecraft:material_instances', {}).items():
                if isinstance(v, dict) and v.get('texture'):
                    mats[k] = v['texture']
        for comp in comps[1:]:                          # first permutation that swaps a named material, e.g. the print
            mi = comp.get('minecraft:material_instances', {})
            extra = {k: v['texture'] for k, v in mi.items() if isinstance(v, dict) and v.get('texture') and k != '*'
                     and v['texture'] != mats.get(k)}
            if extra:
                mats.update(extra); break
        geos = []
        for comp in comps:
            gg = comp.get('minecraft:geometry')
            gg = gg.get('identifier') if isinstance(gg, dict) else gg
            if gg in GEOS:
                geos.append(gg)
        if not geos or '*' not in mats:
            continue

        def tpath(name):
            tp = terrain.get(name, {}).get('textures')
            tp = tp[0] if isinstance(tp, list) else tp
            return png_for(tp.get('path') if isinstance(tp, dict) else tp)
        best = max(set(geos), key=lambda g: (sum(len(b.get('cubes', [])) for b in GEOS[g]['bones']), g))
        by_file[bid] = (best, {k: tpath(v) for k, v in mats.items() if tpath(v)}, len(set(geos)))
    return by_file


def client_models():
    out = []
    for folder, kind in (('entity', 'minecraft:client_entity'), ('attachables', 'minecraft:attachable')):
        for path in sorted(glob.glob(os.path.join(g_escape(RP), folder, '*.json'))):
            d = load(path)[kind]['description']
            ident = d['identifier'].split(':')[-1]
            if ident == 'tank_fish':
                continue
            for gkey, gid in d.get('geometry', {}).items():
                if gkey == 'wants' or gid not in GEOS:
                    continue
                tpath = d.get('textures', {}).get('default') or next(iter(d.get('textures', {}).values()), None)
                if not tpath:
                    continue
                key = (gid, tpath)
                if key not in [(o[1], o[2]) for o in out]:
                    out.append((ident + ('' if gkey == 'default' else f' ({gkey})'), gid, tpath))
    return out


def sheet(entries, cell, cols, title, out_path, views=(225,)):
    rows = (len(entries) + cols - 1) // cols
    W = cols * (cell * len(views) + 12) + 12
    im = Image.new('RGB', (W, rows * (cell + 28) + 44), (232, 230, 222))
    d = ImageDraw.Draw(im)
    d.text((12, 10), title, font=FONT, fill=(40, 40, 40))
    for i, (label, qs) in enumerate(entries):
        x = 12 + (i % cols) * (cell * len(views) + 12); y = 38 + (i // cols) * (cell + 28)
        for k, yaw in enumerate(views):
            bg = Image.new('RGBA', (cell, cell), (196, 200, 206, 255))
            bg.alpha_composite(render(qs, cell, yaw))
            im.paste(bg.convert('RGB'), (x + k * cell, y))
        d.text((x, y + cell + 4), label, font=FONT, fill=(40, 40, 40))
    im.save(out_path)


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    entries = []
    for bid, (gid, tps, n) in sorted(block_models().items()):
        tex = {k: Image.open(v).convert('RGBA') for k, v in tps.items()}
        name = ZH.get(bid) or ZH.get(bid.replace('_block', '')) or bid
        cubes = sum(len(b.get('cubes', [])) for b in GEOS[gid]['bones'])
        entries.append((f'{name}  {cubes}塊' + (f'・{n}態' if n > 1 else ''), quads(gid, tex)))
    sheet(entries, 150, 4, f'方塊模型 {len(entries)} 個（每個取方塊最多的狀態，左右是兩個角度；「N塊」= 方塊數）',
          os.path.join(out_dir, 'blocks.png'), views=(225, 45))
    entries = []
    for label, gid, tpath in client_models():
        p = png_for(tpath)
        if not p:
            continue
        cubes = sum(len(b.get('cubes', [])) for b in GEOS[gid]['bones'])
        entries.append((f'{ZH.get(label.split(" ")[0], label)}{label[len(label.split(" ")[0]):]}  {cubes}塊',
                        quads(gid, Image.open(p).convert('RGBA'))))
    sheet(entries, 170, 4, f'生物、穿戴與手持模型 {len(entries)} 個（左右是兩個角度）',
          os.path.join(out_dir, 'entities.png'), views=(225, 45))
    d = load(os.path.join(RP, 'entity', 'tank_fish.entity.json'))['minecraft:client_entity']['description']
    tex = Image.open(png_for(d['textures']['default'])).convert('RGBA')
    entries = []
    for key, gid in d['geometry'].items():
        cubes = sum(len(b.get('cubes', [])) for b in GEOS[gid]['bones'])
        entries.append((f'{ZH.get(key, key)}  {cubes}塊', quads(gid, tex)))
    sheet(entries, 130, 6, f'魚缸裡的魚 {len(entries)} 種（側面略偏上的角度）',
          os.path.join(out_dir, 'tank_fish.png'), views=(240,))
    print('wrote', out_dir)


if __name__ == '__main__':
    main(sys.argv[1])
