"""Check every 3D model (geometry) in the pack.

usage: python tools/check_models.py

Checks
  files       every models/**/*.geo.json parses, has minecraft:geometry, a known format_version
  ids         geometry identifiers are unique; every geometry is used; every reference points at one that exists
  bones       bone names unique per geometry; parents exist; no parent cycles; cubes have size/origin
  uv          every cube's UV (box UV or per-face) stays inside texture_width x texture_height
  textures    the texture each geometry is drawn with exists, and its pixel size has the declared aspect ratio
              (a 32x32 png on a 64x64 geometry is fine, a 64x32 png is not)
  blocks      block geometry stays inside Bedrock's 30x30x30 limit (x,z in [-15,15], y in [0,30]) and has
              at most 32 bones; collision/selection boxes stay inside the block
  anim        bones that the entity's animations move exist in that entity's geometry
  rc          render controllers only name geometry keys / texture keys the entity or attachable defines
Exit code 0 = no errors (warnings may remain).
"""
import json, os, re, sys, glob, math
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
BP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [BP]')
errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def load(path):
    with open(path, encoding='utf-8-sig') as f:
        text = f.read()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        stripped = re.sub(r'(?m)^\s*//.*$', '', text)          # Bedrock tolerates // comments
        return json.loads(stripped)


def rel(p):
    return os.path.relpath(p, ROOT).replace('\\', '/')


# ---------------------------------------------------------------- geometry files
geos = {}            # identifier -> dict(file, desc, bones)
for path in sorted(glob.glob(os.path.join(glob.escape(RP), 'models', '**', '*.json'), recursive=True)):
    try:
        data = load(path)
    except Exception as e:
        err(f'{rel(path)}: does not parse: {e}'); continue
    fv = data.get('format_version')
    if fv not in ('1.12.0', '1.16.0', '1.19.30', '1.21.0', '1.8.0', '1.10.0'):
        warn(f'{rel(path)}: unusual format_version {fv!r}')
    if 'minecraft:geometry' in data:
        items = data['minecraft:geometry']
        for g in items:
            d = g.get('description', {})
            gid = d.get('identifier')
            if not gid:
                err(f'{rel(path)}: geometry without identifier'); continue
            if gid in geos:
                err(f'{rel(path)}: identifier {gid} already defined in {geos[gid]["file"]}')
            geos[gid] = {'file': rel(path), 'desc': d, 'bones': g.get('bones', [])}
    else:
        legacy = [k for k in data if k.startswith('geometry.')]
        if legacy:
            warn(f'{rel(path)}: legacy 1.8 geometry format ({", ".join(legacy)})')
            for k in legacy:
                geos[k.split(':')[0]] = {'file': rel(path), 'desc': {'texture_width': data[k].get('texturewidth', 64),
                                         'texture_height': data[k].get('textureheight', 64)},
                                         'bones': data[k].get('bones', [])}
        else:
            err(f'{rel(path)}: no minecraft:geometry')


def cube_box(c):
    o = c.get('origin', [0, 0, 0]); s = c.get('size', [0, 0, 0]); inf = c.get('inflate', 0)
    lo = [o[i] - inf for i in range(3)]; hi = [o[i] + s[i] + inf for i in range(3)]
    return lo, hi


def rotate_point(p, pivot, rot):
    """Bedrock rotates bones/cubes X then Y then Z (degrees) around the pivot."""
    x, y, z = (p[i] - pivot[i] for i in range(3))
    rx, ry, rz = (math.radians(a) for a in rot)
    y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
    x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
    x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
    return [x + pivot[0], y + pivot[1], z + pivot[2]]


# ---------------------------------------------------------------- bones and UVs
for gid, g in geos.items():
    tw = g['desc'].get('texture_width', 64); th = g['desc'].get('texture_height', 64)
    names = [b.get('name') for b in g['bones']]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        err(f'{gid}: duplicate bone names {sorted(dup)}')
    byname = {b.get('name'): b for b in g['bones']}
    for b in g['bones']:
        p = b.get('parent')
        if p and p not in byname:
            err(f'{gid}: bone {b.get("name")} has missing parent {p}')
        seen, cur = set(), b
        while cur and cur.get('parent'):
            if cur['name'] in seen:
                err(f'{gid}: parent cycle at bone {b.get("name")}'); break
            seen.add(cur['name']); cur = byname.get(cur['parent'])
        for i, c in enumerate(b.get('cubes', [])):
            where = f'{gid} bone {b.get("name")} cube {i}'
            if 'size' not in c or 'origin' not in c:
                err(f'{where}: missing origin/size'); continue
            s = c['size']
            if any(v < 0 for v in s):
                warn(f'{where}: negative size {s}')
            if all(v == 0 for v in s):
                warn(f'{where}: zero-size cube')
            uv = c.get('uv')
            if uv is None:
                continue
            if isinstance(uv, list):                       # box UV
                u, v = uv
                dx, dy, dz = (math.floor(abs(t)) if abs(t) >= 1 else abs(t) for t in s)
                w, h = 2 * (dx + dz), dz + dy
                if u < 0 or v < 0 or u + w > tw + 0.01 or v + h > th + 0.01:
                    err(f'{where}: box UV {uv} size {s} needs {u + w:g}x{v + h:g}, texture is {tw}x{th}')
            elif isinstance(uv, dict):
                for face, fd in uv.items():
                    if not isinstance(fd, dict) or 'uv' not in fd:
                        continue
                    u, v = fd['uv']; us = fd.get('uv_size', [0, 0])
                    xs = sorted([u, u + us[0]]); ys = sorted([v, v + us[1]])
                    if xs[0] < -0.01 or ys[0] < -0.01 or xs[1] > tw + 0.01 or ys[1] > th + 0.01:
                        err(f'{where} face {face}: UV {fd["uv"]}+{us} outside {tw}x{th}')

# ---------------------------------------------------------------- who uses which geometry
used = {}            # gid -> list of (user, texture path or None)
terrain = load(os.path.join(RP, 'textures', 'terrain_texture.json')).get('texture_data', {})


def terrain_png(name):
    t = terrain.get(name, {}).get('textures')
    if isinstance(t, list):
        t = t[0]
    if isinstance(t, dict):
        t = t.get('path')
    return t


def find_png(path):
    if not path:
        return None
    for ext in ('.png', '.tga'):
        p = os.path.join(RP, path + ext)
        if os.path.exists(p):
            return p
    return None


def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


block_geos = {}      # gid -> block file
for path in sorted(glob.glob(os.path.join(glob.escape(BP), 'blocks', '*.json'))):
    data = load(path)
    blk = data.get('minecraft:block', {})
    comps = [blk.get('components', {})] + [p.get('components', {}) for p in blk.get('permutations', [])]
    tex_names = set()
    for comp in comps:
        mi = comp.get('minecraft:material_instances', {})
        for k, v in mi.items():
            if isinstance(v, dict) and 'texture' in v:
                tex_names.add(v['texture'])
    for comp in comps:
        geo = comp.get('minecraft:geometry')
        if isinstance(geo, dict):
            geo = geo.get('identifier')
        if geo and geo.startswith('geometry.') and geo not in ('minecraft:geometry.full_block',):
            block_geos[geo] = rel(path)
            for t in tex_names:
                used.setdefault(geo, []).append((rel(path), find_png(terrain_png(t)), f'terrain {t}'))
            if not tex_names:
                used.setdefault(geo, []).append((rel(path), None, None))
        for box in ('minecraft:collision_box', 'minecraft:selection_box'):
            bx = comp.get(box)
            if isinstance(bx, dict):
                o, s = bx.get('origin', [-8, 0, -8]), bx.get('size', [16, 16, 16])
                if o[0] < -8 or o[2] < -8 or o[1] < 0 or o[0] + s[0] > 8 or o[2] + s[2] > 8 or o[1] + s[1] > 16:
                    err(f'{rel(path)}: {box} {o}+{s} leaves the 16x16x16 block')
    for t in tex_names:
        if t not in terrain:
            err(f'{rel(path)}: material texture {t} missing from terrain_texture.json')
        elif not find_png(terrain_png(t)):
            err(f'{rel(path)}: texture file for {t} ({terrain_png(t)}) missing')


RCS = {}
for _p in glob.glob(os.path.join(glob.escape(RP), 'render_controllers', '*.json')):
    for _rid, _r in load(_p).get('render_controllers', {}).items():
        RCS[_rid] = _r


def rc_pairs(entries, gmap, tmap):
    """(geometry key, texture key) pairs a client actually draws, read from its render controllers.
    Vanilla controllers (controller.render.default / item_default) draw Geometry.default with Texture.default."""
    pairs = set()
    for entry in entries:
        rid = entry if isinstance(entry, str) else next(iter(entry))
        r = RCS.get(rid)
        if r is None:
            pairs.add(('default', 'default')); continue
        arrays = {}
        for kind in ('geometries', 'textures'):
            for name, vals in r.get('arrays', {}).get(kind, {}).items():
                arrays[name] = [v.split('.', 1)[1] for v in vals]
        def keys(expr, prefix):
            expr = expr if isinstance(expr, str) else ''
            m = re.match(prefix + r'\.(\w+)$', expr)
            if m:
                return [m.group(1)]
            m = re.match(r'(Array\.\w+)\[', expr)
            return arrays.get(m.group(1), []) if m else []
        gkeys = keys(r.get('geometry', ''), 'Geometry')
        tkeys = [k for t in r.get('textures', []) for k in keys(t, 'Texture')]
        for g in gkeys:
            for t in tkeys or [None]:
                pairs.add((g, t))
    return pairs

clients = {}         # identifier -> dict(file, geometry map, textures map, animations)
for kind, folder in (('minecraft:client_entity', 'entity'), ('minecraft:attachable', 'attachables')):
    for path in sorted(glob.glob(os.path.join(glob.escape(RP), folder, '*.json'))):
        data = load(path)
        d = data.get(kind, {}).get('description', {})
        gmap = d.get('geometry', {}); tmap = d.get('textures', {})
        clients[d.get('identifier', rel(path))] = {'file': rel(path), 'geometry': gmap, 'textures': tmap,
                                                    'animations': d.get('animations', {}),
                                                    'render_controllers': d.get('render_controllers', [])}
        for tkey, tpath in tmap.items():
            if tpath and not find_png(tpath) and 'enchanted_item_glint' not in tpath:
                err(f'{rel(path)}: texture {tpath} missing')
        pairs = rc_pairs(d.get('render_controllers', []), gmap, tmap)
        for gkey, tkey in pairs:
            gid = gmap.get(gkey); tpath = tmap.get(tkey)
            if not gid or (tpath and 'enchanted_item_glint' in tpath):
                continue
            used.setdefault(gid, []).append((rel(path) + f' [{gkey}/{tkey}]', find_png(tpath), tpath))
        for gkey, gid in gmap.items():                   # geometry not reached by any controller still counts as used
            used.setdefault(gid, [])

COOKERY = set()
for _z in glob.glob(os.path.join(glob.escape(os.path.dirname(ROOT)), 'Kaleidoscope-Cookery-*.mcaddon')):
    import zipfile
    with zipfile.ZipFile(_z) as _zf:
        for _n in _zf.namelist():
            if '/models/' in _n and _n.endswith('.json'):
                try:
                    _d = json.loads(re.sub(r'(?m)^\s*//.*$', '', _zf.read(_n).decode('utf-8-sig')))
                except Exception:
                    continue
                for _g in _d.get('minecraft:geometry', []):
                    COOKERY.add(_g.get('description', {}).get('identifier'))
borrowed = []
for gid, users in used.items():
    if gid not in geos:
        if gid.startswith('geometry.kaleidoscope_cookery.'):
            if COOKERY and gid not in COOKERY:
                err(f'{gid} (borrowed from Kaleidoscope Cookery) is not in the Cookery pack; used by '
                    f'{", ".join(sorted({u[0] for u in users}))}')
            else:
                borrowed.append(gid)
            continue
        if gid.startswith('geometry.') and not gid.startswith('geometry.kaleidoscope'):
            continue                                      # vanilla geometry
        err(f'missing geometry {gid} used by {", ".join(sorted({u[0] for u in users}))}')
for gid in geos:
    if gid not in used:
        warn(f'{gid} ({geos[gid]["file"]}) is never used by a block, entity or attachable')

# ---------------------------------------------------------------- texture sizes
for gid, users in used.items():
    g = geos.get(gid)
    if not g:
        continue
    tw = g['desc'].get('texture_width', 64); th = g['desc'].get('texture_height', 64)
    for user, png, label in users:
        if not png:
            continue
        w, h = Image.open(png).size
        if abs(w / h - tw / th) > 1e-6 and not (h % w == 0 and h // w > 1 and tw == th and 'textures/blocks' in png and False):
            err(f'{gid}: texture {rel(png)} is {w}x{h}, geometry expects {tw}x{th} (aspect differs) [{user}]')
        elif w < tw or w % tw and tw % w:
            warn(f'{gid}: texture {rel(png)} is {w}x{h}, geometry declares {tw}x{th} [{user}]')

# ---------------------------------------------------------------- block limits
for gid, bfile in block_geos.items():
    g = geos.get(gid)
    if not g:
        continue
    if len(g['bones']) > 32:
        err(f'{gid}: {len(g["bones"])} bones, blocks allow 32')
    lo_all, hi_all = [1e9] * 3, [-1e9] * 3
    byname = {b['name']: b for b in g['bones']}

    def chain(b):
        out = []
        while b:
            out.append(b); b = byname.get(b.get('parent'))
        return out
    for b in g['bones']:
        for c in b.get('cubes', []):
            lo, hi = cube_box(c)
            pts = [[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
            if c.get('rotation'):
                pts = [rotate_point(p, c.get('pivot', [0, 0, 0]), c['rotation']) for p in pts]
            for bb in chain(b):
                if bb.get('rotation'):
                    pts = [rotate_point(p, bb.get('pivot', [0, 0, 0]), bb['rotation']) for p in pts]
            for p in pts:
                for i in range(3):
                    lo_all[i] = min(lo_all[i], p[i]); hi_all[i] = max(hi_all[i], p[i])
    if lo_all[0] < 1e8:
        bad = lo_all[0] < -15.01 or lo_all[2] < -15.01 or hi_all[0] > 15.01 or hi_all[2] > 15.01 \
            or lo_all[1] < -0.01 or hi_all[1] > 30.01
        msg = (f'{gid} ({bfile}): extent x {lo_all[0]:.1f}..{hi_all[0]:.1f}, '
               f'y {lo_all[1]:.1f}..{hi_all[1]:.1f}, z {lo_all[2]:.1f}..{hi_all[2]:.1f}')
        if bad:
            err(msg + ' is outside the 30x30x30 block geometry limit')

# ---------------------------------------------------------------- animations -> bones
anims = {}
for path in glob.glob(os.path.join(glob.escape(RP), 'animations', '*.json')):
    for aid, a in load(path).get('animations', {}).items():
        anims[aid] = (rel(path), set(a.get('bones', {}).keys()))
for cid, c in clients.items():
    bones = set()
    for gid in c['geometry'].values():
        bones |= {b.get('name') for b in geos.get(gid, {}).get('bones', [])}
    for short, aid in c['animations'].items():
        if aid.startswith('controller.'):
            continue
        if aid not in anims:
            if aid.startswith('animation.kaleidoscope') or aid.startswith('animation.kfv'):
                err(f'{c["file"]}: animation {aid} ({short}) not found')
            continue
        missing = anims[aid][1] - bones
        if missing and bones:
            warn(f'{c["file"]}: animation {aid} moves bones not in its geometry: {sorted(missing)}')

# ---------------------------------------------------------------- render controllers
rcs = {}
for path in glob.glob(os.path.join(glob.escape(RP), 'render_controllers', '*.json')):
    for rid, r in load(path).get('render_controllers', {}).items():
        rcs[rid] = (rel(path), json.dumps(r))
for cid, c in clients.items():
    for entry in c['render_controllers']:
        rid = entry if isinstance(entry, str) else next(iter(entry))
        if rid not in rcs:
            if not rid.startswith(('controller.render.default', 'controller.render.item_default')):
                err(f'{c["file"]}: render controller {rid} not found')
            continue
        text = rcs[rid][1]
        for key in set(re.findall(r'Geometry\.(\w+)', text)):
            if key not in c['geometry']:
                # array-based controllers may list keys for other entities sharing the controller
                if not re.search(r'Array\.', text):
                    err(f'{c["file"]}: {rid} uses Geometry.{key}, which it does not define')
        for key in set(re.findall(r'Texture\.(\w+)', text)):
            if key not in c['textures'] and not re.search(r'Array\.', text):
                err(f'{c["file"]}: {rid} uses Texture.{key}, which it does not define')

# ---------------------------------------------------------------- report
print(f'{len(geos)} geometries in {len({g["file"] for g in geos.values()})} files; '
      f'{len(block_geos)} used by blocks, {sum(1 for g in used if g in geos) - len(block_geos)} by entities/attachables')
for e in errors:
    print('ERROR  ', e)
for w in warnings:
    print('warning', w)
print(f'{len(borrowed)} geometries borrowed from Kaleidoscope Cookery' + (' (verified in the Cookery pack)' if COOKERY else ' (Cookery pack not found, not verified)'))
print(f'{len(errors)} error(s), {len(warnings)} warning(s)')
sys.exit(1 if errors else 0)
