"""The Fish Pond Feeder (魚池餵食台, 1.5.0): the polished model, its texture and the guidebook picture.

  python tools/gen_pond_feeder.py

It replaces the first-pass box model of the feeder (tools/gen_stations_1_5.py --pond-feeder, part of the
tools/gen_1_5.py fish-pond step), so run it AFTER those whenever they are run again. Same geometry identifier
(geometry.kaleidoscope_fishing.pond_feeder), same texture (textures/blocks/kfv_pond_feeder, terrain key
kfv_pond_feeder) and the same bones, which blocks/pond_feeder.json shows by state (blocks/pond.js sets them):
  feeder   always: a stone footing, a stout post with two braces, a plank deck, a feed trough on the deck, and a
           beam reaching out over the water with a net basket hanging from it on three ropes
  feed     state kaleidoscope_fishing:feed == 1 (there are meals left): pellets heaped in the trough, a few spilled
           on the deck, and a tied burlap feed sack beside it
  roe      state kaleidoscope_fishing:roe == 1 (the pond spawned roe): orange clumps of roe in the net basket
The basket hangs on the north side (-z). The texture is painted in code (tools/facepaint.py), 1 texture pixel per
model unit, every face its own pixels; the RTX maps are refreshed (tools/pbr.py). Also writes the 128x128 guidebook
picture textures/ui/kfv_book/kfv_pond_feeder.png, rendered from the model with every bone shown.
"""
import importlib.util, json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facepaint import Sheet, Part, shade, mix, hash01

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
NS = 'kaleidoscope_fishing'

STONE, STONE_LT, STONE_DK, MOSS = '#8c8c88', '#a8a8a2', '#5e5e5a', '#5e7a3a'
WOOD, WOOD_LT, WOOD_DK, WOOD_GAP = '#a8763e', '#c49058', '#6e4826', '#3a2614'
ROPE, ROPE_DK, NET, NET_KNOT, HOOP = '#d2bd8c', '#9a8458', '#d8d0b0', '#a89e7a', '#b89a5a'
PELLET, PELLET_DK, PELLET_LT = '#8a5a2e', '#5e3a1a', '#b07a44'
SACK, SACK_DK, SACK_LT = '#c2a46e', '#8e7444', '#d8bc86'
ROE, ROE_DK, ROE_HI = '#f2953a', '#c8661e', '#ffd08a'
WOOD_M, STONE_M = (0, 0, 210), (0, 0, 230)


def s_stone(p, n):
    """Footing: rough blocks of stone with mortar lines and a little moss low down."""
    x, y, z = p
    along = x if abs(n[2]) > 0.5 else z
    if n[1] > 0.5:
        u, v = x, z
        row = math.floor((v + 8) / 2.5)
        if (v + 8) % 2.5 < 0.5 or (u + 8 + row * 1.3) % 3.5 < 0.5:
            return (STONE_DK, STONE_M)
        return (shade(STONE_LT, 0.92 + 0.12 * hash01(math.floor(u * 2), math.floor(v * 2))), STONE_M)
    row = math.floor(y)
    if y % 1.0 < 0.01 or (along + 8 + row * 1.7) % 3.0 < 0.5:
        return (STONE_DK, STONE_M)
    if y < 0.6 and hash01(math.floor(along * 2), 9) > 0.45:
        return (MOSS, STONE_M)
    return (shade(STONE, 0.9 + 0.18 * hash01(math.floor(along), row)), STONE_M)


def grain(base, plank, along, k=0.12):
    t = 0.94 + k * hash01(plank, math.floor(along / 7 + plank * 0.41))
    c = shade(base, t)
    if hash01(plank * 7 + 3, math.floor(along)) > 0.85:
        c = shade(c, 0.86)
    return c


def s_post(p, n):
    """The post: end grain on top, otherwise grain running up, darker where it meets the footing (wet)."""
    if abs(n[1]) > 0.5:
        r = max(abs(p[0]), abs(p[2] - 2.5))
        return (WOOD_DK if r > 1.0 else WOOD_LT, WOOD_M)
    c = grain(WOOD, 5 + round(p[0] + p[2]), p[1])
    return (shade(c, 0.75) if p[1] < 4 else c, WOOD_M)


def s_beam(axis):
    def f(p, n):
        along = p[axis]
        plank = round(p[1] * 2) + 30
        c = grain(WOOD, plank, along, 0.16)
        if abs(n[axis]) > 0.5:
            return (WOOD_LT if n[1] >= 0 else WOOD_DK, WOOD_M)        # end grain
        return (shade(c, 1.08) if n[1] > 0.5 else shade(c, 0.85) if n[1] < -0.5 else c, WOOD_M)
    return f


def s_deck(p, n):
    """Deck: planks 3 wide running along z with dark gaps, nail heads over the two bearers."""
    x, z = p[0], p[2]
    k = math.floor((x + 6.5) / 3)
    if n[1] > 0.5:
        if (x + 6.5) % 3 > 2:
            return (WOOD_DK, WOOD_M)
        if (abs(z - 1.5) < 0.5 or abs(z - 3.5) < 0.5) and (x + 6.5) % 3 < 1 and hash01(k, math.floor(z)) > 0.4:
            return ('#5a4a3a', WOOD_M)                                 # a nail head
        return (grain(WOOD_LT, k, z), WOOD_M)
    if abs(n[2]) > 0.5:
        return (shade(WOOD, 0.8 if (x + 6.5) % 3 > 2 else 0.95), WOOD_M)
    return (grain(WOOD_DK, k + 60, z), WOOD_M)


def s_trough(p, n):
    """Trough: weathered boards, a darker stain inside where the feed sits."""
    x, y, z = p
    if n[1] > 0.5 and y < 11.8:
        return (shade(WOOD_DK, 0.9 + 0.15 * hash01(math.floor(x * 2), math.floor(z * 2))), WOOD_M)
    along = x if abs(n[2]) > 0.5 or abs(n[1]) > 0.5 else z
    c = grain('#9a6a38', math.floor(y) + 70, along, 0.15)
    if n[1] > 0.5:
        return (shade(c, 1.12), WOOD_M)
    if abs(y - 12.25) < 0.25 and abs(n[1]) < 0.5:
        return ('#4a4a50', (150, 0, 120))                          # an iron band round it
    return (c, WOOD_M)


def s_rope(p, n):
    return (ROPE if int(math.floor((p[0] + p[1] + p[2]) * 1.5)) % 2 else ROPE_DK, WOOD_M)


def s_hoop(p, n):
    """Bamboo hoop of the basket: pale with a dark node every 2 units."""
    along = p[0] if abs(n[0]) < 0.5 and abs(p[2] + 6) > 1.5 else p[2]
    return (WOOD_DK if (along + 8) % 2 < 0.4 else HOOP if n[1] <= 0.5 else shade(HOOP, 1.12), WOOD_M)


def s_mesh(p, n):
    """Net of the basket: a cord every second unit, knots where they cross; holes between."""
    if abs(n[0]) > 0.5:
        u, v = p[2], p[1]
    elif abs(n[1]) > 0.5:
        u, v = p[0], p[2]
    else:
        u, v = p[0], p[1]
    a = math.floor(u * 2 + 40) % 3 == 0
    b = math.floor(v * 2 + 40) % 3 == 0
    if a and b:
        return (NET_KNOT, WOOD_M)
    if a or b:
        return (NET, WOOD_M)
    return None


def s_pellets(p, n):
    """Feed pellets: round brown pellets, light tops, dark gaps."""
    h = hash01(math.floor(p[0] * 2 + 50), math.floor(p[2] * 2 + 50), math.floor(p[1] * 2))
    if h > 0.82:
        return (PELLET_DK, WOOD_M)
    return (PELLET_LT if h < 0.3 else PELLET, WOOD_M)


def s_sack(p, n):
    """Burlap sack: a woven check, a darker stitched seam down the middle, a printed fish on its front."""
    x, y, z = p
    if n[1] > 0.5:
        return (SACK_DK, WOOD_M)
    u = z if abs(n[0]) > 0.5 else x
    if abs(n[0]) > 0.5 and n[0] < 0 and 12.0 < y < 13.5 and 1.6 < z < 4.4:
        fish = (abs(y - 12.75) < 0.5 and 2.0 < z < 3.9) or (abs(y - 12.75) < 0.75 and 3.9 <= z < 4.4)
        if fish:
            return ('#3e5a78', WOOD_M)
    if (math.floor(u * 2) + math.floor(y * 2)) % 2:
        return (SACK, WOOD_M)
    return (SACK_LT if hash01(math.floor(u), math.floor(y)) > 0.5 else shade(SACK, 0.94), WOOD_M)


def s_tie(p, n):
    return (ROPE_DK if int(p[1] * 2) % 2 else ROPE, WOOD_M)


def s_roe(p, n):
    """Roe: orange eggs, each with a bright highlight and a darker eye spot."""
    a = math.floor(p[0] * 2 + 40) if abs(n[0]) < 0.5 else math.floor(p[2] * 2 + 40)
    b = math.floor(p[2] * 2 + 40) if abs(n[1]) > 0.5 else math.floor(p[1] * 2 + 40)
    h = hash01(a, b, 3)
    if (a + b) % 2 == 0:
        return (ROE_HI if h > 0.6 else ROE, WOOD_M)
    return (ROE_DK if h > 0.75 else '#e07a2a', WOOD_M)


def model():
    sheet = Sheet()
    g = Part(sheet)
    feeder, feed, roe = [], [], []
    # footing and post
    feeder.append(g.box([-4, 0, -1.5], [4, 2, 6.5], s_stone))
    feeder.append(g.box([-3, 2, -0.5], [3, 2.5, 5.5], s_stone))
    feeder.append(g.box([-1.5, 2.5, 1], [1.5, 10, 4], s_post))
    # braces under the deck, front and back (turned about x only)
    feeder.append(g.box([-0.75, 6.5, -3], [0.75, 7.5, 1], s_beam(2), rotation=[-45, 0, 0], pivot=[0, 7, 1]))
    feeder.append(g.box([-0.75, 6.5, 4], [0.75, 7.5, 8], s_beam(2), rotation=[45, 0, 0], pivot=[0, 7, 4]))
    # the deck on two bearers
    feeder.append(g.box([-6, 9.25, 1], [6, 10, 2], s_beam(0)))
    feeder.append(g.box([-6, 9.25, 3], [6, 10, 4], s_beam(0)))
    feeder.append(g.box([-6.5, 10, -3.5], [6.5, 11, 6.5], s_deck))
    # the feed trough: floor, two long sides, two ends
    feeder.append(g.box([-6, 11, 0.5], [1, 11.5, 5], s_trough))
    feeder.append(g.box([-6, 11.5, 0.5], [1, 13.25, 1.25], s_trough))
    feeder.append(g.box([-6, 11.5, 4.25], [1, 13.25, 5], s_trough))
    feeder.append(g.box([-6, 11.5, 1.25], [-5.25, 13.25, 4.25], s_trough))
    feeder.append(g.box([0.25, 11.5, 1.25], [1, 13.25, 4.25], s_trough))
    # the beam out over the water, its post and the basket on three ropes
    feeder.append(g.box([-0.75, 11, -3], [0.75, 14, -1.5], s_post))
    feeder.append(g.box([-0.75, 14, -8], [0.75, 15.25, -1.5], s_beam(2)))
    feeder.append(g.box([-0.25, 14.25, -7.5], [0.25, 14.75, -7.0], s_rope, inflate=0.1))
    for x, z in ((-1.75, -7.25), (1.75, -7.25), (0, -4.25)):
        feeder.append(g.box([x - 0.2, 6, z - 0.2], [x + 0.2, 14, z + 0.2], s_rope))
    # basket: bamboo hoop on top, net round the sides and under it
    feeder.append(g.box([-2.25, 5.5, -8.25], [2.25, 6.25, -7.5], s_hoop))
    feeder.append(g.box([-2.25, 5.5, -4.5], [2.25, 6.25, -3.75], s_hoop))
    feeder.append(g.box([-2.25, 5.5, -7.5], [-1.5, 6.25, -4.5], s_hoop))
    feeder.append(g.box([1.5, 5.5, -7.5], [2.25, 6.25, -4.5], s_hoop))
    feeder.append(g.box([-2, 2, -8], [2, 5.5, -4], s_mesh, faces=('north', 'south', 'east', 'west', 'down')))
    # feed: pellets in the trough and on the deck, the sack
    feed.append(g.box([-5.25, 11.5, 1.25], [0.25, 12.75, 4.25], s_pellets))
    feed.append(g.box([-4, 12.75, 2], [-1, 13.25, 3.5], s_pellets))
    for x, z in ((1.75, 0.0), (-2.5, -1.5), (2.5, 5.5), (-6.0, 5.8)):
        feed.append(g.box([x - 0.3, 11, z - 0.3], [x + 0.3, 11.5, z + 0.3], s_pellets))
    feed.append(g.box([2.5, 11, 1.25], [6, 14.5, 4.75], s_sack))
    feed.append(g.box([3, 14.5, 1.75], [5.5, 15.25, 4.25], s_sack))
    feed.append(g.box([3.75, 15.25, 2.5], [4.75, 16.25, 3.5], s_tie))
    feed.append(g.box([3.5, 15.25, 2.25], [5, 15.75, 3.75], s_tie))
    # roe: clumps on the basket floor
    for x0, x1, z0, z1, top in ((-1.75, 0.25, -7.75, -5.75, 3.75), (0.0, 1.75, -6.5, -4.25, 3.25),
                                (-1.5, 0.5, -5.5, -4.25, 2.75), (0.75, 1.75, -7.75, -6.5, 2.75)):
        roe.append(g.box([x0, 2.05, z0], [x1, top, z1], s_roe))
    bones = [{'name': 'root', 'pivot': [0, 0, 0]}]
    for name, cubes in (('feeder', feeder), ('feed', feed), ('roe', roe)):
        bones.append({'name': name, 'parent': 'root', 'pivot': [0, 0, 0], 'cubes': cubes})
    return sheet, bones


def book_picture(geo_path, png):
    """The guidebook's 128x128 picture, rendered from the model with every bone shown (as gen_stations_1_5.py does)."""
    spec = importlib.util.spec_from_file_location('rm', os.path.join(ROOT, 'tools', 'render_models.py'))
    rm = importlib.util.module_from_spec(spec); spec.loader.exec_module(rm)
    from PIL import Image
    g = json.load(open(geo_path, encoding='utf-8'))['minecraft:geometry'][0]
    g = json.loads(json.dumps(g))
    g['description']['identifier'] = 'tmp'
    rm.GEOS['tmp'] = g
    tex = Image.open(png).convert('RGBA')
    big = rm.render(rm.quads('tmp', tex), 256, 225, -30)
    bb = big.getbbox()
    side = max(bb[2] - bb[0], bb[3] - bb[1]); cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    big = big.crop((int(cx - side / 2), int(cy - side / 2), int(cx + side / 2), int(cy + side / 2))).resize((124, 124), Image.LANCZOS)
    out = Image.new('RGBA', (128, 128), (0, 0, 0, 0)); out.alpha_composite(big, (2, 2))
    path = os.path.join(RP, 'textures', 'ui', 'kfv_book', 'kfv_pond_feeder.png')
    out.save(path)
    return path


def main():
    sheet, bones = model()
    png = os.path.join(RP, 'textures', 'blocks', 'kfv_pond_feeder.png')
    ts = png[:-4] + '.texture_set.json'
    with open(ts, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'format_version': '1.16.100', 'minecraft:texture_set': {
            'color': 'kfv_pond_feeder', 'metalness_emissive_roughness': 'kfv_pond_feeder_mer', 'heightmap': 'kfv_pond_feeder_height'}}, f, indent=2)
        f.write('\n')
    sheet.save(png)                                   # fills in the UVs; colour, height and MER maps
    tw, th = sheet.size
    geo = os.path.join(RP, 'models', 'blocks', 'pond_feeder.geo.json')
    with open(geo, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'format_version': '1.16.0', 'minecraft:geometry': [{
            'description': {'identifier': f'geometry.{NS}.pond_feeder', 'texture_width': tw, 'texture_height': th,
                            'visible_bounds_width': 2, 'visible_bounds_height': 2, 'visible_bounds_offset': [0, 0.5, 0]},
            'bones': bones}]}, f, indent=2)
        f.write('\n')
    book = book_picture(geo, png)
    print('wrote', geo, f'{png} ({tw}x{th})', book, sep='\n  ')


if __name__ == '__main__':
    main()
