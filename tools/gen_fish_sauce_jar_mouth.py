"""Fish Sauce Jar (魚露甕): an open mouth you can see into (1.4.0 playtest: "the jar will not open").

usage: python tools/gen_fish_sauce_jar_mouth.py

The neck was one solid 8x2x8 cube, so its top face covered the mouth: an empty jar looked closed, and the fish
sauce surface (y 12.25-12.75) sat under the neck's top (y 13) and never showed, so a jar that was ready still
looked sealed. Here the neck of every model except the sealed one ("lid") becomes a ring of four 1-thick walls
with a dark inside, and the inside shows what the jar holds:
  empty   a dark jar floor
  salted  a layer of white salt (new model; the block shows it at stage 0 once salted)
  sauce   an amber surface with a highlight
Run again safely: models are rebuilt from their solid-neck form if needed, and the painted regions are redrawn.
"""
import copy, json, os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
BP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [BP]')
GEO = os.path.join(RP, 'models', 'blocks', 'fish_sauce_jar.geo.json')
TEX = os.path.join(RP, 'textures', 'blocks', 'kfv_fish_sauce_jar.png')
BLOCK = os.path.join(BP, 'blocks', 'fish_sauce_jar.json')
NS = 'kaleidoscope_fishing'
ID = f'geometry.{NS}.fish_sauce_jar_'

INNER = (0, 42)      # 8x2 dark inner wall
FLOOR = (0, 46)      # 6x6 dark jar floor
SALT = (8, 46)       # 6x6 salt
SAUCE_UP = (24, 34)  # 6x6, the existing fish sauce surface region (repainted)


def f(u, v, w, h):
    return {'uv': [float(u), float(v)], 'uv_size': [float(w), float(h)]}


def ring():
    """Four walls replacing the solid neck [-4,11,-4] 8x2x8 (outer faces keep the neck's texture)."""
    iu, iv = INNER
    return [
        {'origin': [-4.0, 11.0, -4.0], 'size': [8.0, 2.0, 1.0],
         'uv': {'north': f(40, 0, 8, 2), 'south': f(iu, iv, 8, 2), 'east': f(48, 0, 1, 2), 'west': f(48, 0, 1, 2), 'up': f(56, 0, 8, 1)}},
        {'origin': [-4.0, 11.0, 3.0], 'size': [8.0, 2.0, 1.0],
         'uv': {'south': f(40, 0, 8, 2), 'north': f(iu, iv, 8, 2), 'east': f(48, 0, 1, 2), 'west': f(48, 0, 1, 2), 'up': f(56, 7, 8, 1)}},
        {'origin': [-4.0, 11.0, -3.0], 'size': [1.0, 2.0, 6.0],
         'uv': {'west': f(48, 0, 6, 2), 'east': f(iu, iv, 6, 2), 'up': f(56, 1, 1, 6)}},
        {'origin': [3.0, 11.0, -3.0], 'size': [1.0, 2.0, 6.0],
         'uv': {'east': f(48, 0, 6, 2), 'west': f(iu, iv, 6, 2), 'up': f(63, 1, 1, 6)}},
    ]


def is_neck(c):
    return c['origin'] == [-4.0, 11.0, -4.0] and c['size'] == [8.0, 2.0, 8.0]


def is_ring(c):
    return c['origin'][1] == 11.0 and c['size'][1] == 2.0 and 1.0 in (c['size'][0], c['size'][2])


def floor_cube(region):
    return {'origin': [-3.0, 11.0, -3.0], 'size': [6.0, 0.1, 6.0], 'uv': {'up': f(*region, 6, 6)}}


def paint(im):
    px = im.load()
    def put(x, y, c): px[x, y] = c + (255,)
    for x in range(8):                                    # inner wall: dark glaze, lighter at the lip
        put(INNER[0] + x, INNER[1], (74, 44, 28)); put(INNER[0] + x, INNER[1] + 1, (46, 27, 17))
    for y in range(6):
        for x in range(6):
            edge = x in (0, 5) or y in (0, 5)
            put(FLOOR[0] + x, FLOOR[1] + y, (40, 24, 15) if edge else ((30, 18, 11) if (x + y) % 3 else (36, 22, 14)))
            put(SALT[0] + x, SALT[1] + y, (226, 222, 212) if (x * 2 + y) % 5 else (250, 250, 246))
            if edge and (x + y) % 2:
                put(SALT[0] + x, SALT[1] + y, (206, 200, 188))
            # fish sauce: deep amber, a lighter ring at the edge, a two-pixel highlight top left
            c = (122, 54, 16) if not edge else (150, 74, 24)
            if (x, y) in ((1, 1), (2, 1), (1, 2)):
                c = (226, 150, 70)
            elif (x + 2 * y) % 7 == 0 and not edge:
                c = (138, 64, 20)
            put(SAUCE_UP[0] + x, SAUCE_UP[1] + y, c)
    return im


def main():
    doc = json.load(open(GEO, encoding='utf-8'))
    gs = doc['minecraft:geometry']
    by = {g['description']['identifier']: g for g in gs}
    for gid, g in list(by.items()):
        name = gid[len(ID):]
        if name in ('lid', 'salted'):
            continue
        cubes = g['bones'][0]['cubes']
        if any(is_neck(c) for c in cubes):
            i = next(i for i, c in enumerate(cubes) if is_neck(c))
            cubes[i:i + 1] = ring()
        if name == 'empty':                             # the old hidden inner cube -> a visible dark floor
            cubes[:] = [c for c in cubes if not (c['origin'][1] in (10.5, 11.0) and c['size'] in ([6.0, 0.5, 6.0], [6.0, 0.1, 6.0]))]
            cubes.append(floor_cube(FLOOR))
    salted = copy.deepcopy(by[ID + 'empty'])
    salted['description']['identifier'] = ID + 'salted'
    sc = salted['bones'][0]['cubes']
    sc[-1] = {'origin': [-3.0, 11.0, -3.0], 'size': [6.0, 0.6, 6.0],
              'uv': {'up': f(*SALT, 6, 6), 'north': f(SALT[0], SALT[1], 6, 0.6), 'south': f(SALT[0], SALT[1], 6, 0.6),
                     'east': f(SALT[0], SALT[1], 6, 0.6), 'west': f(SALT[0], SALT[1], 6, 0.6)}}
    doc['minecraft:geometry'] = [g for g in gs if g['description']['identifier'] != ID + 'salted'] + [salted]
    with open(GEO, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(doc, fh, indent=2)

    im = paint(Image.open(TEX).convert('RGBA'))
    im.save(TEX)
    pbr.refresh(TEX)

    blk = json.load(open(BLOCK, encoding='utf-8'))
    perms = blk['minecraft:block']['permutations']
    cond = f"q.block_state('{NS}:stage') == 0 && q.block_state('{NS}:salted') == 1"
    if not any(p['condition'] == cond for p in perms):
        # after the plain stage-0 permutation, so a salted empty jar shows the salt
        i = next(i for i, p in enumerate(perms) if p['condition'] == f"q.block_state('{NS}:stage') == 0")
        perms.insert(i + 1, {'condition': cond, 'components': {'minecraft:geometry': ID + 'salted'}})
        with open(BLOCK, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(blk, fh, indent=2, ensure_ascii=False)
    print('jar models:', [g['description']['identifier'][len(ID):] for g in doc['minecraft:geometry']])


if __name__ == '__main__':
    main()
