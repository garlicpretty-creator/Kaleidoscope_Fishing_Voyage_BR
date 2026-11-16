"""Fish Cleaning Board (魚案板): models for the nine fish added in 1.4.0, built from their item icons.

usage: python tools/gen_board_fish.py           writes the models, the texture and the block permutations
       python tools/gen_board_fish.py sprites   only saves the side-view sprites next to this script, for review

Each icon (a 16x16 fish drawn corner to corner, head lower left) is turned flat (rotated 45 degrees through an
8x nearest-neighbour upscale, then sampled back down by the most common colour) and laid on its side on the board,
head towards -x like the older 32 board fish. Every sprite pixel is a 0.5-unit column whose height follows the
distance to the outline, so the body is thick in the middle and the fins are thin. The three cuts:
  1 whole fish            (fish with scales only)
  2 scales off            body colours paler, scale flakes on the board (scaleless fish start here, unchanged)
  3 belly opened          a red slit along the belly
Models: models/blocks/fish_cleaning_board_more.geo.json. Texture: textures/blocks/kfv_board_fish.png (its own material instance on the board), 2 texture pixels per unit.
"""
import json, os, sys
from collections import Counter
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
BP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [BP]')
BOARD_GEO = os.path.join(RP, 'models', 'blocks', 'fish_cleaning_board.geo.json')
GEO = os.path.join(RP, 'models', 'blocks', 'fish_cleaning_board_more.geo.json')   # written compact: ~100 cubes per model
BLOCK = os.path.join(BP, 'blocks', 'fish_cleaning_board.json')
TEX_NAME = 'kfv_board_fish'
TEX = os.path.join(RP, 'textures', 'blocks', TEX_NAME + '.png')
TW, TH = 256, 128
PX = 0.5                      # model units per sprite pixel
NS = 'kaleidoscope_fishing'

# name: (board index, length in units, has scales, max height in units)
FISH = {
    'loach':           (35, 10.5, False, 1.0),
    'mudskipper':      (36, 9.0, False, 1.5),
    'golden_croaker':  (37, 11.5, True, 2.0),
    'chorus_carp':     (38, 10.5, True, 2.0),
    'ender_angler':    (39, 10.5, False, 2.0),
    'blazefin':        (40, 11.0, True, 1.5),
    'lava_eel':        (41, 12.5, False, 1.0),
    'magma_koi':       (42, 11.0, True, 2.0),
    'lava_dragon_koi': (43, 12.5, True, 2.0),
}


def icon(name):
    return Image.open(os.path.join(RP, 'textures', 'items', f'kfv_{name}.png')).convert('RGBA')


def keep_main(im):
    """Drop loose pixels (sparks, drips): keep 4-connected opaque groups of 4 or more."""
    px = im.load(); w, h = im.size; seen = set()
    for y in range(h):
        for x in range(w):
            if px[x, y][3] < 128 or (x, y) in seen:
                continue
            group, stack = [], [(x, y)]; seen.add((x, y))
            while stack:
                a, b = stack.pop(); group.append((a, b))
                for c, d in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                    if 0 <= c < w and 0 <= d < h and (c, d) not in seen and px[c, d][3] >= 128:
                        seen.add((c, d)); stack.append((c, d))
            if len(group) < 4:
                for a, b in group:
                    px[a, b] = (0, 0, 0, 0)
    return im


def side_sprite(name, length):
    """The icon turned to a horizontal side view, head left, length*2 pixels long."""
    k = 8
    big = keep_main(icon(name)).resize((16 * k, 16 * k), Image.NEAREST).rotate(-45, Image.NEAREST, expand=True)
    big = big.crop(big.getbbox())
    W = round(length / PX)
    s = big.width / W
    H = max(1, round(big.height / s))
    out = Image.new('RGBA', (W, H)); o = out.load(); b = big.load()
    for y in range(H):
        for x in range(W):
            cols = Counter(); tot = 0
            for yy in range(int(y * s), min(big.height, int((y + 1) * s))):
                for xx in range(int(x * s), min(big.width, int((x + 1) * s))):
                    tot += 1
                    p = b[xx, yy]
                    if p[3] >= 128:
                        cols[p[:3]] += 1
            if tot and sum(cols.values()) / tot >= 0.4:
                o[x, y] = cols.most_common(1)[0][0] + (255,)
    return keep_main(out)


FLESH = (236, 196, 176)
SLIT, SLIT_EDGE = (122, 20, 24), (196, 84, 84)


def heights(sp, hmax):
    """Column height per pixel: 0.5 at the outline, rising by 0.5 per pixel inwards, up to hmax."""
    px = sp.load(); w, h = sp.size
    out = {}
    for y in range(h):
        for x in range(w):
            if px[x, y][3] < 128:
                continue
            d = 1
            while d < 8:
                ring = [(x + a, y + b) for a in range(-d, d + 1) for b in range(-d, d + 1) if max(abs(a), abs(b)) == d]
                if any(not (0 <= c < w and 0 <= e < h) or px[c, e][3] < 128 for c, e in ring):
                    break
                d += 1
            out[x, y] = min(hmax, PX * d)
    return out


def scaled_off(sp):
    """Scales scraped off: every body colour moves a third of the way to pale flesh; the outline stays."""
    out = sp.copy(); px = out.load()
    for y in range(sp.height):
        for x in range(sp.width):
            r, g, b, a = px[x, y]
            if a and (r + g + b) > 120:
                px[x, y] = tuple(round(c + (f - c) * 0.35) for c, f in zip((r, g, b), FLESH)) + (255,)
    return out


def slit(sp):
    """Belly opened: a red cut along the lower body, over the middle 45% of the fish."""
    out = sp.copy(); px = out.load(); w, h = sp.size
    for x in range(round(w * 0.22), round(w * 0.62)):
        col = [y for y in range(h) if px[x, y][3]]
        if len(col) < 4:
            continue
        top, bot = col[0], col[-1]
        y = bot - max(1, (bot - top) // 3)
        px[x, y] = SLIT + (255,)
        if px[x, y - 1][3]:
            px[x, y - 1] = SLIT_EDGE + (255,)
    return out


# the scale flakes the older board fish leave after the first cut (main board texture)
FLAKES = [[5.5, 2.0, -4.0], [4.5, 2.0, 3.5], [-6.0, 2.0, -4.2], [-6.5, 2.0, 3.8], [3.0, 2.0, 4.2], [-3.0, 2.0, -4.5],
          [-4.5, 2.0, 4.2]]


def flake(o):
    f = {'uv': [88.0, 39.0], 'uv_size': [0.5, 0.15]}
    return {'origin': o, 'size': [0.5, 0.15, 0.5],
            'uv': {k: dict(f, uv_size=[0.5, 0.5] if k in ('up', 'down') else [0.5, 0.15]) for k in
                   ('north', 'south', 'east', 'west', 'up', 'down')}}


def fish_cubes(sp, hmax, slot):
    """Columns for each sprite pixel, merged down each sprite column while the height is the same.
    slot: (u, v) of this sprite in the atlas; the transposed copy sits right of it for the east/west faces."""
    su, sv = slot
    hs = heights(sp, hmax)
    w, h = sp.size
    x0 = -w * PX / 2; z0 = -h * PX / 2
    tu = su + w                                          # transposed copy: pixel (x, y) at (tu + y, sv + x)
    M = TEX_NAME
    cubes = []
    for x in range(w):
        y = 0
        while y < h:
            if (x, y) not in hs:
                y += 1; continue
            y1 = y
            while (x, y1 + 1) in hs and hs[x, y1 + 1] == hs[x, y]:
                y1 += 1
            n = y1 - y + 1; ht = hs[x, y]
            face = lambda u, v, us, vs: {'uv': [u, v], 'uv_size': [us, vs], 'material_instance': M}
            covered = lambda cells: all(hs.get(c, 0) >= ht for c in cells)   # a neighbour at least as tall hides it
            uv = {'up': face(su + x, sv + y, 1, n)}
            if not covered([(x, y - 1)]):
                uv['north'] = face(su + x, sv + y, 1, 1)
            if not covered([(x, y1 + 1)]):
                uv['south'] = face(su + x, sv + y1, 1, 1)
            if not covered([(x - 1, yy) for yy in range(y, y1 + 1)]):
                uv['west'] = face(tu + y, sv + x, n, 1)
            if not covered([(x + 1, yy) for yy in range(y, y1 + 1)]):
                uv['east'] = face(tu + y, sv + x, n, 1)
            cubes.append({
                'origin': [round(x0 + x * PX, 3), 2.0, round(z0 + y * PX, 3)],
                'size': [PX, ht, round(n * PX, 3)],
                'uv': uv})
            y = y1 + 1
    return cubes


def board_cube():
    gs = json.load(open(BOARD_GEO, encoding='utf-8'))['minecraft:geometry']
    return next(g for g in gs if g['description']['identifier'].endswith('_0_0'))['bones'][0]['cubes'][0]


def build():
    atlas = Image.new('RGBA', (TW, TH))
    geos = []
    u = v = 0; row_h = 0
    base = board_cube()
    for name, (idx, L, scales, hmax) in FISH.items():
        whole = side_sprite(name, L)
        stages = {}
        if scales:
            stages[1] = whole
            stages[2] = scaled_off(whole)
        else:
            stages[2] = whole
        stages[3] = slit(stages[2])
        for cut, sp in stages.items():
            need = sp.width + sp.height
            if u + need > TW:
                u = 0; v += row_h; row_h = 0
            if v + max(sp.width, sp.height) > TH:
                raise SystemExit('board fish atlas is full')
            atlas.alpha_composite(sp, (u, v))
            atlas.alpha_composite(sp.transpose(Image.TRANSPOSE), (u + sp.width, v))
            cubes = [base] + fish_cubes(sp, hmax, (u, v))
            if scales and cut >= 2:
                cubes += [flake(o) for o in FLAKES]
            geos.append({'description': {
                'identifier': f'geometry.{NS}.fish_cleaning_board_{idx}_{cut}', 'texture_width': TW, 'texture_height': TH,
                'visible_bounds_width': 3, 'visible_bounds_height': 3, 'visible_bounds_offset': [0, 0.75, 0]},
                'bones': [{'name': 'root', 'pivot': [0, 0, 0], 'cubes': cubes}]})
            u += need; row_h = max(row_h, sp.width, sp.height)
    return atlas, geos


def write_geo(new):
    with open(GEO, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'format_version': '1.16.0', 'minecraft:geometry': new}, f, separators=(',', ':'))


def write_block(new):
    with open(BLOCK, encoding='utf-8') as f:
        doc = json.load(f)
    blk = doc['minecraft:block']
    mats = blk['components']['minecraft:material_instances']
    mats[TEX_NAME] = {'texture': TEX_NAME, 'render_method': 'alpha_test'}
    perms = blk['permutations']
    want = []
    for g in new:
        idx, cut = map(int, g['description']['identifier'].rsplit('_', 2)[1:])
        want.append({'condition': f"(q.block_state('{NS}:fish') + 16 * q.block_state('{NS}:fish_bank')) == {idx} && "
                                  f"q.block_state('{NS}:cut') == {cut}",
                     'components': {'minecraft:geometry': g['description']['identifier']}})
    have = {p['condition'] for p in perms}
    perms += [p for p in want if p['condition'] not in have]
    with open(BLOCK, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)


def write_terrain():
    path = os.path.join(RP, 'textures', 'terrain_texture.json')
    with open(path, encoding='utf-8') as f:
        doc = json.load(f)
    if TEX_NAME not in doc['texture_data']:
        doc['texture_data'][TEX_NAME] = {'textures': 'textures/blocks/' + TEX_NAME}
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)


def main(argv):
    if argv[:1] == ['sprites']:
        here = os.path.dirname(os.path.abspath(__file__))
        sheet = Image.new('RGBA', (9 * 30 * 8, 16 * 8), (139, 139, 139, 255))
        for i, (n, (idx, L, sc, hmax)) in enumerate(FISH.items()):
            sp = side_sprite(n, L)
            sheet.alpha_composite(sp.resize((sp.width * 8, sp.height * 8), Image.NEAREST), (i * 240, 4))
        sheet.save(argv[1] if len(argv) > 1 else os.path.join(here, 'board_fish_sprites.png'))
        return
    atlas, geos = build()
    atlas.save(TEX)
    write_geo(geos)
    write_block(geos)
    write_terrain()
    print(len(geos), 'board models,', max(len(g['bones'][0]['cubes']) for g in geos), 'cubes at most; wrote', pbr.refresh(TEX))


if __name__ == '__main__':
    main(sys.argv[1:])
