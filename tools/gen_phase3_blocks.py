"""Convenience phase 3: two new stations, the Long Drying Rack (長曬架) and the Gutting Table (殺魚台).

  python tools/gen_phase3_blocks.py           models, textures (+ RTX maps), guidebook pictures, blocks, loot,
                                              recipes, names, creative catalog, guidebook entries
  python tools/build.py build                 afterwards (the guidebook JSON goes into generated.js)

Safe to run again: everything it writes is replaced.

Long Drying Rack  kaleidoscope_fishing:long_drying_rack. The Drying Rack's batch (one kind, same timing, same
                  script: blocks/drying.js), but 9 places on three bamboo poles, three on each, filled top left
                  first. Block states kind / count (0..9) / stage as on the rack. One geometry per kind
                  (long_drying_rack_<kind>, kind 0 = the bare rack) with a bone per hanging place (s1..s9),
                  shown by `count`; the stage swaps the whole texture (kfv_long_drying_rack_<stage>): the three
                  sheets have the same layout, the frame painted the same and the goods in the stage's colours.
                  Frame 7 cubes, each hanging thing 2 (low-poly; detail is painted per face).
Gutting Table     kaleidoscope_fishing:gutting_table (blocks/guttingTable.js). A butcher's top on two trestles
                  (4 cubes). Bones: pile1..pile3 (the stack of fish on it, state `load` 1..3), knife (state
                  `knife`), done (cut goods waiting, state `done`).
Both are their own inventory item (the game shows the 3D model there, as for the other stations); the guidebook
pictures (textures/ui/kfv_book/kfv_<key>.png, 128x128) are rendered from the models like the pond feeder's.
"""
import importlib.util, json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facepaint import Sheet, Part, shade, mix, hash01  # noqa: E402
import content as c  # noqa: E402

ROOT = c.ROOT
RP, BP, NS = c.RP, c.BP, c.NS
S = NS + ':'
BLK = os.path.join(RP, 'textures', 'blocks')
M_WOOD, M_STEEL, M_FISH, M_WET = (0, 0, 215), (200, 0, 70), (0, 0, 120), (0, 0, 90)

# ------------------------------------------------------------------------------------------------ colours
BAMBOO, BAMBOO_LT, BAMBOO_DK, NODE = '#b4ad58', '#d2c878', '#8a8440', '#6e6a30'
PLANK, PLANK_LT, PLANK_DK = '#9a6a3a', '#b88450', '#5e3e20'
TWINE, TWINE_DK = '#d6c294', '#a08c60'


def bamboo(axis):
    """Bamboo: pale culm with a dark node ring every 4 units along `axis`, lighter on top, a fine vertical streak."""
    def f(p, n):
        a = p[axis]
        if abs(n[axis]) > 0.5:
            r = max(abs(p[i]) % 1 for i in range(3) if i != axis)
            return (BAMBOO_DK if r > 0.6 else '#e6dca0', M_WOOD)      # cut end: a ring and the hollow
        if (a + 64) % 4 < 0.5:
            return (NODE, M_WOOD)
        base = BAMBOO_LT if n[1] > 0.5 else BAMBOO_DK if n[1] < -0.5 else BAMBOO
        k = 0.93 + 0.12 * hash01(math.floor(a * 2), math.floor((p[0] + p[2]) * 3))
        return (shade(base, k), M_WOOD)
    return f


def plank(axis):
    def f(p, n):
        along = p[axis]
        row = math.floor((p[1] if abs(n[1]) < 0.5 else p[(axis + 2) % 3 if axis != 1 else 0]) * 2)
        c_ = shade(PLANK, 0.92 + 0.14 * hash01(row, math.floor(along / 3)))
        if n[1] > 0.5:
            c_ = shade(c_, 1.1)
        if hash01(row * 3 + 1, math.floor(along * 2)) > 0.9:
            c_ = shade(c_, 0.8)
        return (c_, M_WOOD)
    return f


def twine(p, n):
    return (TWINE if int(math.floor((p[0] + p[1] + p[2]) * 4)) % 2 else TWINE_DK, M_WOOD)


# per stage (fresh, half dry, dry)
FISH = {'back': ('#6e7c8a', '#948060', '#8e5e34'), 'belly': ('#dcded6', '#d6be96', '#c48c50'),
        'flesh': ('#e28c78', '#c8784e', '#9e5028'), 'fin': ('#8a96a0', '#a08a6a', '#7a5230')}
SALT = {'back': ('#8a96a0', '#b0a084', '#b48c5c'), 'belly': ('#eceee6', '#e6d6b8', '#d8b484'),
        'flesh': ('#ecb0a0', '#d8a07c', '#b87a4c'), 'fin': ('#a8b0b6', '#b8a68a', '#987048')}
SQUID = {'body': ('#eee2dc', '#e6cea8', '#d6a060'), 'spot': ('#c88c96', '#c09070', '#a46a38'),
         'leg': ('#e6c8c0', '#dcb890', '#c08850')}
LOIN = {'body': ('#962a2e', '#6e2e24', '#5c3a24'), 'line': ('#b84a4a', '#8a4430', '#7a5434'),
        'skin': ('#3c4250', '#3e3a36', '#3a2c20')}
ROE = {'body': ('#ec963c', '#d67828', '#b0541e'), 'hi': ('#ffc880', '#f0a050', '#d0803a'),
       'dk': ('#c86e24', '#a8561c', '#843a14')}
FLY = {'back': ('#3c64aa', '#646470', '#785a3c'), 'belly': ('#dce2e8', '#c8beaa', '#b48c5a'),
       'wing': ('#96bedc', '#a0a6aa', '#8c7458')}
SHRIMP = {'shell': ('#ec8468', '#ce644a', '#a04a30'), 'light': ('#fcb89c', '#e89274', '#be6c4e'),
          'dark': ('#ba563e', '#96402c', '#6a2e1c')}


def fish_body(pal, st, salted=False):
    """A gutted fish hung by the tail, head down: dark back along the north face top, pale belly, the opened belly
    (flesh) down the middle of the south face, an eye near the bottom, a gill line; salt specks if salted."""
    def f(p, n):
        x, y, z = p
        if n[1] < -0.5:                                   # the head end, seen from below
            return (pal['back'][st], M_FISH)
        if n[1] > 0.5:
            return (pal['fin'][st], M_FISH)
        side = x if abs(n[2]) > 0.5 else z * 2
        if abs(n[2]) > 0.5 and n[2] > 0 and abs(x) < 0.45 and -3.5 < y < -1.3:
            col = pal['flesh'][st]                         # the belly opened
        elif abs(side) > 0.85:
            col = pal['back'][st]
        else:
            col = mix(pal['belly'][st], pal['back'][st], abs(side) / 1.2)
        if abs(n[2]) > 0.5 and abs(y + 3.45) < 0.25 and abs(abs(x) - 0.6) < 0.25:
            col = '#1a1410'                                # eye
        elif -3.2 < y < -3.0 and abs(n[2]) > 0.5:
            col = shade(col, 0.75)                         # gill line
        if salted and hash01(math.floor(x * 4 + 20), math.floor(y * 4 + 40), math.floor(z * 4 + 9)) > 0.86:
            col = '#f8f8f0'
        return (shade(col, 0.95 + 0.1 * hash01(math.floor(y * 4), math.floor(x * 4))), M_FISH)
    return f


def fish_tail(pal, st):
    def f(p, n):
        if abs(n[2]) > 0.5 and p[1] > -0.35 and abs(p[0]) < 0.35:
            return None                                    # forked tail: a notch in the middle
        rays = int(math.floor((p[0] + 4) * 4)) % 2
        return (shade(pal['fin'][st], 1.1 if rays else 0.9), M_FISH)
    return f


def squid_body(st):
    def f(p, n):
        x, y = p[0], p[1]
        if abs(n[2]) > 0.5 and y > -0.8 and abs(x) > 0.5 and y - (-0.8) > (abs(x) - 0.5) * 1.6:
            return None                                    # the fin's two points at the top
        col = SQUID['body'][st]
        if hash01(math.floor(x * 4 + 30), math.floor(y * 4 + 40), int(n[2] * 3 + n[0] * 5)) > 0.8:
            col = SQUID['spot'][st]
        return (shade(col, 0.94 + 0.1 * hash01(math.floor(y * 3), 2)), M_FISH)
    return f


def squid_legs(st):
    def f(p, n):
        if abs(n[1]) < 0.5 and int(math.floor((p[0] + p[2] + 4) * 4)) % 2 and p[1] < -3.4:
            return None                                    # strands of tentacle
        return (SQUID['leg'][st], M_FISH)
    return f


def loin(st):
    def f(p, n):
        x, y, z = p
        if abs(n[2]) > 0.5 and n[2] < 0:
            return (LOIN['skin'][st], (0, 0, 80))
        if (y * 2 + abs(x) * 1.5) % 1.5 < 0.3:
            return (LOIN['line'][st], M_FISH)               # the flakes of the loin
        return (shade(LOIN['body'][st], 0.92 + 0.12 * hash01(math.floor(y * 3), math.floor(x * 3))), M_FISH)
    return f


def roe(st):
    def f(p, n):
        x, y = p[0], p[1]
        if abs(n[2]) > 0.5 and (y < -3.1 or y > -1.4) and abs(x) > 0.7:
            return None                                    # rounded ends
        h = hash01(math.floor(x * 4 + 10), math.floor(y * 4 + 40), int(n[2] * 2))
        col = ROE['hi'][st] if h > 0.85 else ROE['dk'][st] if abs(x) > 0.75 else ROE['body'][st]
        return (col, (0, 0, 60))                           # glossy
    return f


def fly_body(st):
    def f(p, n):
        x, y, z = p
        if abs(n[2]) > 0.5 and y > -1.2 and abs(x) > 0.3 and (y + 1.2) > (abs(x) - 0.3) * 1.4:
            return None                                    # tail fork
        if n[1] < -0.5:
            return (FLY['back'][st], M_FISH)
        side = x if abs(n[2]) > 0.5 else z * 1.6
        col = FLY['back'][st] if abs(side) > 0.45 else FLY['belly'][st]
        if abs(n[2]) > 0.5 and abs(y + 3.5) < 0.2 and abs(abs(x) - 0.45) < 0.2:
            col = '#141010'
        return (col, M_FISH)
    return f


def fly_wing(st):
    def f(p, n):
        x, y = p[0], p[1]
        if abs(x) > 0.75 and (y + 2.6) < (abs(x) - 0.75) * 0.6:
            return None                                    # the wing's swept-back lower edge
        rays = int(math.floor((abs(x) + y) * 3)) % 2
        return (shade(FLY['wing'][st], 1.08 if rays else 0.9), M_FISH)
    return f


def shrimp_bunch(st):
    """Three curled shrimp on the string: segments, a dark head with an eye, alternating sides."""
    def f(p, n):
        x, y = p[0], p[1]
        k = math.floor((y + 3.6) / 1.0)                    # which shrimp, bottom to top
        fy = (y + 3.6) % 1.0
        left = k % 2 == 0
        u = x if left else -x
        if abs(n[1]) < 0.5 and u > 0.9 and fy < 0.35:
            return None                                    # gaps between the curls
        if u < -0.6:
            col = SHRIMP['dark'][st]                       # heads
            if abs(n[2]) > 0.5 and abs(fy - 0.5) < 0.2 and abs(u + 0.85) < 0.2:
                col = '#1c1210'
        else:
            col = SHRIMP['light'][st] if int(math.floor((u + 2) * 3)) % 3 == 0 else SHRIMP['shell'][st]
        return (col, M_FISH)
    return f


# local shapes of one hanging thing: [(lo, hi, shader factory(stage)), ...], hung from y = 0 (the pole's underside)
GOODS = {
    1: [((-1, -1.0, -0.2), (1, 0, 0.2), lambda st: fish_tail(FISH, st)),
        ((-1.25, -4.0, -0.6), (1.25, -1.0, 0.6), lambda st: fish_body(FISH, st))],
    2: [((-1, -1.0, -0.2), (1, 0, 0.2), lambda st: fish_tail(SALT, st)),
        ((-1.25, -4.0, -0.6), (1.25, -1.0, 0.6), lambda st: fish_body(SALT, st, salted=True))],
    3: [((-1, -3.0, -0.5), (1, 0, 0.5), squid_body),
        ((-0.75, -4.0, -0.3), (0.75, -3.0, 0.3), squid_legs)],
    4: [((-0.2, -0.75, -0.2), (0.2, 0, 0.2), lambda st: twine),
        ((-1, -4.0, -0.7), (1, -0.75, 0.7), loin)],
    5: [((-0.2, -1.0, -0.2), (0.2, 0, 0.2), lambda st: twine),
        ((-1, -3.5, -0.35), (1, -1.0, 0.35), roe)],
    6: [((-0.8, -4.0, -0.5), (0.8, -0.25, 0.5), fly_body),
        ((-1.6, -2.6, -0.1), (1.6, -1.4, 0.1), fly_wing)],
    7: [((-0.2, -3.9, -0.2), (0.2, 0, 0.2), lambda st: twine),
        ((-1.2, -3.6, -0.5), (1.2, -0.6, 0.5), shrimp_bunch)],
}
POLES = (14.5, 9.5, 4.5)                     # the underside of each pole, top to bottom
COLS = (-3.75, 0.0, 3.75)
SLOTS = [(x, y) for y in POLES for x in COLS]  # s1..s9: the top pole left to right, then the next


def rack_sheet(st):
    """One stage's texture and the geometries (identical layout for every stage)."""
    sheet = Sheet()
    frame_part = Part(sheet, density=2)
    goods_part = Part(sheet, density=4)
    frame = [frame_part.box([-8, 0, -2.5], [-5, 1, 2.5], plank(2)), frame_part.box([5, 0, -2.5], [8, 1, 2.5], plank(2)),
             frame_part.box([-7.5, 1, -1], [-5.5, 16, 1], bamboo(1)), frame_part.box([5.5, 1, -1], [7.5, 16, 1], bamboo(1))]
    for y in POLES:
        frame.append(frame_part.box([-8, y, -0.75], [8, y + 1.25, 0.75], bamboo(0)))
    local = {k: [goods_part.box(lo, hi, mk(st)) for lo, hi, mk in shapes] for k, shapes in GOODS.items()}
    return sheet, frame, local


def rack_geometries(frame, local, tw, th):
    geos = []
    for kind in range(8):
        bones = [{'name': 'root', 'pivot': [0, 0, 0]}, {'name': 'rack', 'parent': 'root', 'pivot': [0, 0, 0], 'cubes': frame}]
        if kind:
            for i, (sx, sy) in enumerate(SLOTS, 1):
                # the face dicts are shared with the local cube, so every place shows the same painted thing
                cubes = [{'origin': [round(cb['origin'][0] + sx, 4), round(cb['origin'][1] + sy, 4), cb['origin'][2]],
                          'size': cb['size'], 'uv': cb['uv']} for cb in local[kind]]
                bones.append({'name': f's{i}', 'parent': 'root', 'pivot': [sx, sy, 0], 'cubes': cubes})
        geos.append({'description': {'identifier': f'geometry.{NS}.long_drying_rack_{kind}', 'texture_width': tw, 'texture_height': th,
                                     'visible_bounds_width': 2, 'visible_bounds_height': 2, 'visible_bounds_offset': [0, 0.5, 0]},
                     'bones': bones})
    return geos


def texture_set(png):
    name = os.path.basename(png)[:-4]
    with open(png[:-4] + '.texture_set.json', 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'format_version': '1.16.100', 'minecraft:texture_set': {
            'color': name, 'metalness_emissive_roughness': name + '_mer', 'heightmap': name + '_height'}}, f, indent=2)
        f.write('\n')


def write_geo(path, geos):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'format_version': '1.16.0', 'minecraft:geometry': geos}, f, indent=2)
        f.write('\n')


def long_rack_model():
    out = None
    for st in range(3):
        sheet, frame, local = rack_sheet(st)
        png = os.path.join(BLK, f'kfv_long_drying_rack_{st}.png')
        texture_set(png)
        sheet.save(png)
        geos = rack_geometries(frame, local, *sheet.size)
        if out is None:
            out = geos
        else:
            assert json.dumps(geos) == json.dumps(out), 'the stage sheets must share one layout'
    path = os.path.join(RP, 'models', 'blocks', 'long_drying_rack.geo.json')
    write_geo(path, out)
    return path


# ------------------------------------------------------------------------------------------------ gutting table
TOP, TOP_LT, TOP_DK, STAIN = '#a87a4a', '#c49462', '#6a4a2a', '#7a3a2e'
STEEL, STEEL_LT, STEEL_DK = '#b8bec4', '#e2e6ea', '#7c848c'
SILVER, SILVER_BACK, SILVER_BELLY = '#aab8c2', '#5a7488', '#e6eaec'
FILLET, FILLET_FAT = '#f08a6a', '#fcd2c0'


def s_top(p, n):
    """Butcher's top: end-grain blocks on top (a checker of light and dark squares), scored by the knife and stained
    dark red at the fish end; planks round the sides."""
    x, y, z = p
    if n[1] > 0.5:
        bx, bz = math.floor((x + 7) / 2.0), math.floor((z + 4.5) / 1.5)
        col = shade(TOP_LT if (bx + bz) % 2 else TOP, 0.94 + 0.1 * hash01(bx, bz))
        if (x + 7) % 2.0 < 0.2 or (z + 4.5) % 1.5 < 0.15:
            col = TOP_DK
        if hash01(math.floor(x * 4 + 40), math.floor(z * 4 + 40)) > 0.93:
            col = shade(col, 0.78)                         # knife scores
        if x < -0.5 and hash01(math.floor(x * 2 + 40), math.floor(z * 2 + 40), 7) > 0.72:
            col = mix(col, STAIN, 0.55)
        return (col, M_WET if x < 0 else M_WOOD)
    if n[1] < -0.5:
        return (TOP_DK, M_WOOD)
    row = math.floor((y - 9.5) * 2)
    col = shade(TOP, 0.88 + 0.14 * hash01(row, math.floor((x + z) / 3)))
    if y < 9.75:
        col = shade(col, 0.8)
    return (col, M_WOOD)


def s_trestle(p, n):
    """A trestle board with an arch cut out of the bottom (a hole in the paint, so the cube stays one box)."""
    x, y, z = p
    if abs(n[0]) > 0.5 and abs(z) < 2.5 and y < 3.5 + 2.0 * math.sqrt(max(0.0, 1 - (z / 2.5) ** 2)):
        return None                                        # a round-topped arch between the two feet
    if n[1] < -0.5 and abs(z) < 2.5:
        return None
    col = shade(PLANK, 0.9 + 0.15 * hash01(math.floor(z * 2 + 20), math.floor(y / 3)))
    if y < 0.75:
        col = shade(col, 0.72)                             # wet foot
    return (col, M_WOOD)


def s_bar(p, n):
    return (shade(PLANK_DK, 0.95 + 0.1 * hash01(math.floor(p[0]), 3)), M_WOOD)


def s_fish(p, n, span):
    """A fish lying along x, head at +x: dark back up the middle of the top, silver sides, pale belly, an eye
    each side near the head, a gill line, the tail fan at -x. `span` is where this fish lies."""
    x, y, z = p
    lo, hi = span['x']
    t = (x - lo) / (hi - lo)                              # 0 tail .. 1 head
    if abs(n[0]) > 0.5:
        return (SILVER_BACK if n[0] > 0 else shade(SILVER, 1.1), M_FISH)
    if t < 0.16:                                          # tail fan
        return (shade(SILVER, 1.12 if int(math.floor(z * 4 + 40)) % 2 else 0.95), M_FISH)
    if n[1] > 0.5:
        w = span['w']
        rel = abs((z - span['zc']) / w)
        if (t < 0.27 and rel > 0.45) or (t > 0.9 and rel > 1 - (t - 0.9) * 4):
            return None                                    # the tail narrows to its fan, the snout comes to a point
        col = SILVER_BACK if rel < 0.15 else mix(SILVER, SILVER_BACK, 0.3) if rel < 0.3 else SILVER
        if t > 0.8 and abs(rel - 0.45) < 0.12 and abs(t - 0.86) < 0.03:
            col = '#141414'                               # eyes
        elif abs(t - 0.78) < 0.02:
            col = shade(col, 0.7)                         # gill
        if hash01(math.floor(x * 4 + 50), math.floor(z * 4 + 50)) > 0.9:
            col = shade(col, 1.15)                        # scales catching the light
        return (col, M_FISH)
    if n[1] < -0.5:
        return (SILVER_BELLY, M_FISH)
    rel = (y - span['y0']) / 1.2
    col = SILVER_BACK if rel > 0.75 else SILVER if rel > 0.35 else SILVER_BELLY
    if t > 0.84 and abs(rel - 0.62) < 0.15:
        col = '#141414'
    return (col, M_FISH)


def fish_cube(g, lo, hi):
    """Each fish gets its own shader closure (the span it is painted in)."""
    span = {'x': (lo[0], hi[0]), 'w': (hi[2] - lo[2]) / 2, 'zc': (lo[2] + hi[2]) / 2, 'y0': lo[1]}

    return g.box(lo, hi, lambda p, n: s_fish(p, n, span))


def s_blade(p, n):
    x = p[0]
    if n[1] > 0.5:
        if p[2] > 2.3 + (x + 0.5) * 1.4:
            return None                                    # the point: the back of the blade sweeps down to it
        return (STEEL_LT if p[2] < 2.55 else STEEL, M_STEEL)   # the honed edge catches the light
    return (STEEL_DK if n[1] < -0.5 else STEEL, M_STEEL)


def s_handle(p, n):
    col = '#5a3a22' if int(math.floor(p[0] * 2)) % 3 else '#c8b070'   # brass rivets in the dark wood
    return (col, M_WOOD)


def s_fillet(p, n):
    x, y, z = p
    if n[1] > 0.5 or abs(n[2]) > 0.5:
        col = FILLET_FAT if (x * 1.6 + z * 0.8) % 1.2 < 0.22 else FILLET
        return (shade(col, 0.95 + 0.1 * hash01(math.floor(x * 3), math.floor(z * 3))), M_FISH)
    return (shade(FILLET, 0.85), M_FISH)


def table_model():
    sheet = Sheet()
    g = Part(sheet, density=2)
    base = [g.box([-7, 9.5, -4.5], [7, 11, 4.5], s_top),
            g.box([-6, 0, -4], [-4.5, 9.5, 4], s_trestle),
            g.box([4.5, 0, -4], [6, 9.5, 4], s_trestle),
            g.box([-4.5, 2, -0.75], [4.5, 3, 0.75], s_bar)]
    gf = Part(sheet, density=3)
    pile1 = [fish_cube(gf, [-6.0, 11, -2.8], [-0.5, 12.2, -0.6])]
    pile2 = [fish_cube(gf, [-6.3, 11, -0.2], [-0.8, 12.2, 2.0]), fish_cube(gf, [-5.8, 12.2, -1.6], [-0.3, 13.4, 0.6])]
    pile3 = [fish_cube(gf, [-6.1, 12.2, 1.0], [-0.6, 13.4, 3.2]), fish_cube(gf, [-6.0, 13.4, -0.5], [-0.5, 14.6, 1.7])]
    knife = [gf.box([-0.5, 11, 2.3], [4.5, 11.3, 3.3], s_blade), gf.box([4.5, 11, 2.4], [6.6, 11.6, 3.2], s_handle)]
    done = [gf.box([1.0, 11, -3.9], [5.5, 11.6, -1.5], s_fillet), gf.box([1.6, 11.6, -3.5], [5.0, 12.2, -1.9], s_fillet)]
    png = os.path.join(BLK, 'kfv_gutting_table.png')
    texture_set(png)
    sheet.save(png)
    tw, th = sheet.size
    bones = [{'name': 'root', 'pivot': [0, 0, 0]}]
    for name, cubes in (('table', base), ('pile1', pile1), ('pile2', pile2), ('pile3', pile3), ('knife', knife), ('done', done)):
        bones.append({'name': name, 'parent': 'root', 'pivot': [0, 0, 0], 'cubes': cubes})
    path = os.path.join(RP, 'models', 'blocks', 'gutting_table.geo.json')
    write_geo(path, [{'description': {'identifier': f'geometry.{NS}.gutting_table', 'texture_width': tw, 'texture_height': th,
                                      'visible_bounds_width': 2, 'visible_bounds_height': 2, 'visible_bounds_offset': [0, 0.5, 0]},
                      'bones': bones}])
    return path


# ------------------------------------------------------------------------------------------------ guidebook pictures
def book_picture(geo_path, gid, png, key):
    spec = importlib.util.spec_from_file_location('rm', os.path.join(ROOT, 'tools', 'render_models.py'))
    rm = importlib.util.module_from_spec(spec); spec.loader.exec_module(rm)
    from PIL import Image
    g = next(x for x in json.load(open(geo_path, encoding='utf-8'))['minecraft:geometry'] if x['description']['identifier'] == gid)
    g = json.loads(json.dumps(g))
    g['description']['identifier'] = 'tmp'
    rm.GEOS['tmp'] = g
    big = rm.render(rm.quads('tmp', Image.open(png).convert('RGBA')), 256, 225, -30)
    bb = big.getbbox()
    side = max(bb[2] - bb[0], bb[3] - bb[1]); cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    big = big.crop((int(cx - side / 2), int(cy - side / 2), int(cx + side / 2), int(cy + side / 2))).resize((124, 124), Image.LANCZOS)
    out = Image.new('RGBA', (128, 128), (0, 0, 0, 0)); out.alpha_composite(big, (2, 2))
    path = os.path.join(RP, 'textures', 'ui', 'kfv_book', f'kfv_{key}.png')
    out.save(path)
    return path


# ------------------------------------------------------------------------------------------------ blocks and content
ROT = [('north', 0), ('east', 270), ('south', 180), ('west', 90)]


def block(key, states, geometry, materials, box, tick, component, perms, seconds):
    rot = [{'condition': f"q.block_state('minecraft:cardinal_direction') == '{d}'",
            'components': {'minecraft:transformation': {'rotation': [0, r, 0]}}} for d, r in ROT]
    c.write_json(os.path.join(BP, 'blocks', f'{key}.json'), {'format_version': '1.21.60', 'minecraft:block': {
        'description': {'identifier': S + key, 'states': states,
                        'menu_category': {'category': 'equipment', 'group': 'kaleidoscope_cookery:itemGroup.name.cooking_stations'},
                        'traits': {'minecraft:placement_direction': {'enabled_states': ['minecraft:cardinal_direction'], 'y_rotation_offset': 180.0}}},
        'components': {
            'minecraft:display_name': f'%{NS}.display.item.{key}',
            'minecraft:material_instances': materials,
            'minecraft:geometry': geometry,
            'minecraft:light_dampening': 0, 'minecraft:movable': {'movement_type': 'popped'},
            'minecraft:collision_box': box, 'minecraft:selection_box': box,
            'minecraft:tick': {'interval_range': [tick, tick], 'looping': True},
            'minecraft:destructible_by_mining': {'seconds_to_destroy': seconds},
            'minecraft:map_color': '#8F6A40',
            'minecraft:loot': f'loot_tables/{NS}/blocks/{key}.json', component: {}},
        'permutations': rot + perms}})
    c.write_json(os.path.join(BP, 'loot_tables', NS, 'blocks', f'{key}.json'), {'pools': [{'rolls': 1, 'entries': [{'type': 'item', 'name': S + key}]}]})


def recipe(key, pattern, keys):
    c.write_json(os.path.join(BP, 'recipes', 'crafting', f'{key}.json'), {'format_version': '1.20.10', 'minecraft:recipe_shaped': {
        'description': {'identifier': S + key}, 'tags': ['crafting_table'], 'pattern': pattern,
        'key': {k: ({'tag': v[4:]} if v.startswith('tag:') else {'item': v}) for k, v in keys.items()},
        'result': {'item': S + key, 'count': 1}, 'unlock': [{'item': v} for v in keys.values() if not v.startswith('tag:')][:2]}})
    shown = [keys[ch] for row in pattern for ch in row if ch != ' ']
    return [{'method': 'Crafting Table', 'ingredients': ['minecraft:oak_planks' if i.startswith('tag:') else i for i in shown],
             'count': 1, 'time': 0, 'result': S + key}]


def guide(key, name, text, recipes):
    g = c.data('GUIDEBOOK_JSON')
    entry = {'id': S + key, 'category': 'tools', 'kinds': ['item', 'block'], 'stack': 64, 'icon': f'textures/ui/kfv_book/kfv_{key}',
             'recipes': recipes, 'mechanicsByLocale': {code: [t] for code, t in zip(c.LANGS, text)}, 'mechanics': [text[0]]}
    old = [i for i, e in enumerate(g['entries']) if e['id'] == S + key]
    if old:
        g['entries'][old[0]] = entry
    else:
        g['entries'].append(entry)
    for code, t in zip(c.LANGS, name):
        g['names'][code][S + key] = t
    c.save('GUIDEBOOK_JSON', g)


def terrain(*names):
    path = os.path.join(RP, 'textures', 'terrain_texture.json')
    j = c.read_json(path)
    for n in names:
        j['texture_data'][n] = {'textures': f'textures/blocks/{n}'}
    c.write_json(path, j)


def long_rack_content():
    k = S + 'kind'
    cnt = f"q.block_state('{S}count')"
    perms = [{'condition': f"q.block_state('{k}') == {kind}",
              'components': {'minecraft:geometry': {'identifier': f'geometry.{NS}.long_drying_rack_{kind}',
                                                    'bone_visibility': {f's{i}': f'{cnt} >= {i}' for i in range(1, 10)}}}}
             for kind in range(1, 8)]
    perms += [{'condition': f"q.block_state('{S}stage') == {st}",
               'components': {'minecraft:material_instances': {'*': {'texture': f'kfv_long_drying_rack_{st}', 'render_method': 'alpha_test'}}}}
              for st in (1, 2)]
    block('long_drying_rack', {k: list(range(8)), S + 'count': list(range(10)), S + 'stage': [0, 1, 2]},
          f'geometry.{NS}.long_drying_rack_0', {'*': {'texture': 'kfv_long_drying_rack_0', 'render_method': 'alpha_test'}},
          {'origin': [-8, 0, -3], 'size': [16, 16, 6]}, 200, S + 'drying_rack', perms, 0.6)
    terrain('kfv_long_drying_rack_0', 'kfv_long_drying_rack_1', 'kfv_long_drying_rack_2')
    name = ('Long Drying Rack', '長曬架', '长晒架')
    c.names('long_drying_rack', *name)
    c.catalog('long_drying_rack', 'drying_rack')
    rec = recipe('long_drying_rack', ['BBB', 'RRR'], {'B': 'minecraft:bamboo', 'R': S + 'drying_rack'})
    guide('long_drying_rack', name, (
        'A Drying Rack with three poles: it takes up to 9 of one kind (Gutted Fish, Gutted Skipjack, Gutted Flying Fish, Squid Tubes, Salted Mullet Roe or Salted Shrimp) and dries them in the same time as the small rack. Rub Salt on fresh Gutted Fish for Salted Fish. Rain on an open rack stops the drying. With a chest or barrel right below it, a dry batch drops into it by itself; otherwise an empty hand takes it all.',
        '三層竹竿的曬魚架：一次最多掛 9 個同一種（剖好的魚、剖好的鰹魚、剖好的飛魚、魷魚筒、鹽漬烏魚卵或鹽水蝦），曬好的時間和小曬魚架一樣。剛掛上的剖好的魚抹鹽就曬成鹹魚。下雨時沒遮蔽會停下來。正下方放箱子或木桶，曬好會自己掉進去；不然空手一次全部收下。',
        '三层竹竿的晒鱼架：一次最多挂 9 个同一种（剖好的鱼、剖好的鲣鱼、剖好的飞鱼、鱿鱼筒、盐渍乌鱼卵或盐水虾），晒好的时间和小晒鱼架一样。刚挂上的剖好的鱼抹盐就晒成咸鱼。下雨时没遮蔽会停下来。正下方放箱子或木桶，晒好会自己掉进去；不然空手一次全部收下。'), rec)


def table_content():
    st = lambda n: f"q.block_state('{S}{n}')"  # noqa: E731
    geometry = {'identifier': f'geometry.{NS}.gutting_table', 'bone_visibility': {
        'pile1': f'{st("load")} >= 1', 'pile2': f'{st("load")} >= 2', 'pile3': f'{st("load")} >= 3',
        'knife': f'{st("knife")} == 1', 'done': f'{st("done")} == 1'}}
    block('gutting_table', {S + 'load': [0, 1, 2, 3], S + 'knife': [0, 1], S + 'done': [0, 1]}, geometry,
          {'*': {'texture': 'kfv_gutting_table', 'render_method': 'alpha_test'}},
          {'origin': [-7, 0, -4.5], 'size': [14, 11, 9]}, 20, S + 'gutting_table', [], 1.0)
    terrain('kfv_gutting_table')
    name = ('Gutting Table', '殺魚台', '杀鱼台')
    c.names('gutting_table', *name)
    c.catalog('gutting_table', 'fish_cleaning_board')
    rec = recipe('gutting_table', ['IBI', 'P P'], {'I': 'minecraft:iron_ingot', 'B': S + 'fish_cleaning_board', 'P': 'tag:minecraft:planks'})
    guide('gutting_table', name, (
        'Use a stack of one kind of catch on it to lay the whole stack down (up to 64; more of the same can follow). Then lay a knife on it (Fishing Knife or any Cookery kitchen knife): it works through the fish on its own, one a second, scaling, gutting and filleting each as the Fish Cleaning Board does, and wears the knife the same. What it cuts drops into a chest or barrel right below it, or waits on the table. An empty hand takes the cut goods, then the knife, then the fish left. Record fish and named fish are not laid here: clean those on the board.',
        '拿一整組同一種漁獲對它使用，整組放上去（最多 64 個，同一種可以再加）。再把刀放上去（漁刀或森羅任何菜刀）：它會自己一條一條處理，每秒一條，和魚案板一樣去鱗、剖腹、切片，刀也一樣會磨損。切好的東西會掉進正下方的箱子或木桶，沒有就留在台上。空手依序取回切好的東西、刀、剩下的魚。紀錄魚和取了名字的魚不能放這裡，請用魚案板。',
        '拿一整组同一种渔获对它使用，整组放上去（最多 64 个，同一种可以再加）。再把刀放上去（渔刀或森罗任何菜刀）：它会自己一条一条处理，每秒一条，和鱼案板一样去鳞、剖腹、切片，刀也一样会磨损。切好的东西会掉进正下方的箱子或木桶，没有就留在台上。空手依序取回切好的东西、刀、剩下的鱼。纪录鱼和取了名字的鱼不能放这里，请用鱼案板。'), rec)


def main():
    geo = long_rack_model()
    pics = [book_picture(geo, f'geometry.{NS}.long_drying_rack_1', os.path.join(BLK, 'kfv_long_drying_rack_0.png'), 'long_drying_rack')]
    geo2 = table_model()
    pics.append(book_picture(geo2, f'geometry.{NS}.gutting_table', os.path.join(BLK, 'kfv_gutting_table.png'), 'gutting_table'))
    long_rack_content()
    table_content()
    print('wrote', geo, geo2, *pics, sep='\n  ')


if __name__ == '__main__':
    main()
