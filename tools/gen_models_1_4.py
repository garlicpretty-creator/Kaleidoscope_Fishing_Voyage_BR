"""First-pass 3D models for the 1.4.0 additions, built from coloured boxes (tools/modelkit.py).

  python tools/gen_models_1_4.py && python tools/gen_additions_1_4.py && python tools/build.py build

They are meant to be refined in Blockbench: every model is a plain Bedrock geometry with per-face UVs on a swatch
texture, so it opens as is and the texture can be repainted. Safe to run again (each run rebuilds what it owns).

  board_fish() the nine fish new on the Fish Cleaning Board, in their own colours
  tank_creatures() Shrimp, Purpur Shrimp and Oyster in the Fish Tank
  feasts()    River Lord Casserole (a clay pot, 5 stages) and Dragon Koi Stone Grill (1x2 stone slab, 4 stages)
"""
import os

from modelkit import Atlas, box, geometry, texture_set, write_geometries

HERE = os.path.dirname(os.path.abspath(__file__))
RP = os.path.join(os.path.dirname(HERE), 'Kaleidoscope Fishing Voyage [RP]')
NS = 'kaleidoscope_fishing'
GEO = f'geometry.{NS}.'


# --------------------------------------------------------------------------- River Lord Casserole
def casserole():
    """A round clay pot of broth with the River Lord Catfish's head and body in it. Five stages: 0 whole ... 4 empty."""
    a = Atlas(64, 64)
    CLAY, CLAY_D, CLAY_L, RIM, INSIDE = '#a8573a', '#7c3b26', '#c4724e', '#d08a62', '#5a2a1c'
    BROTH, FISH, FISH_L, BELLY, EYE, WHISKER = '#b07a3a', '#5b5a3e', '#7e7a52', '#d8cfa8', '#1a1a1a', '#3c3a28'
    CAP, STEM, CARROT, GREEN, BONE = '#6e4228', '#d9c8a4', '#e8813a', '#6fa84a', '#e8e2d0'
    B = lambda *v, top, side=None, bottom=None: box(*v, top, side, bottom, atlas=a)  # noqa: E731
    pot = [
        B(-5, 5, 0, 0.5, -5, 5, top=CLAY_D),
        B(-5.5, 5.5, 0.5, 1, -5.5, 5.5, top=INSIDE, side=CLAY),
        B(-6.5, 6.5, 1, 6, -6.5, -5.5, top=RIM, side=CLAY),          # walls
        B(-6.5, 6.5, 1, 6, 5.5, 6.5, top=RIM, side=CLAY),
        B(-6.5, -5.5, 1, 6, -5.5, 5.5, top=RIM, side=CLAY),
        B(5.5, 6.5, 1, 6, -5.5, 5.5, top=RIM, side=CLAY),
        B(-6.9, -6.5, 2, 4.5, -5, 5, top=CLAY_L),                    # the belly of the pot
        B(6.5, 6.9, 2, 4.5, -5, 5, top=CLAY_L),
        B(-5, 5, 2, 4.5, -6.9, -6.5, top=CLAY_L),
        B(-5, 5, 2, 4.5, 6.5, 6.9, top=CLAY_L),
        B(6.9, 7.8, 4, 5, -1, 1, top=CLAY_D),                        # ears
        B(-7.8, -6.9, 4, 5, -1, 1, top=CLAY_D),
    ]
    geos = []
    for s in range(5):
        cubes = list(pot)
        if s < 4:
            b = 5.0 - s * 0.8                                        # the broth goes down as it is eaten
            cubes.append(B(-5.5, 5.5, 1, b, -5.5, 5.5, top=BROTH))
            wy = max(b + 0.6, 6.05)                                  # whiskers drape over the rim
            head = [B(-4.5, -1, b - 0.5, b + 1.5, -2, 2, top=FISH), B(-5, -4.5, b, b + 0.8, -1.5, 1.5, top=BELLY),
                    B(-3.5, -3, b + 1.5, b + 1.7, -1.6, -1.1, top=EYE), B(-3.5, -3, b + 1.5, b + 1.7, 1.1, 1.6, top=EYE),
                    B(-7.6, -4.5, wy, wy + 0.25, -1.9, -1.65, top=WHISKER), B(-7.6, -4.5, wy, wy + 0.25, 1.65, 1.9, top=WHISKER),
                    B(-7.85, -7.6, wy - 2, wy + 0.25, -1.9, -1.65, top=WHISKER), B(-7.85, -7.6, wy - 2, wy + 0.25, 1.65, 1.9, top=WHISKER)]
            body = [B(-1, 3, b - 0.5, b + 1.2, -1.6, 1.6, top=FISH), B(0, 2.5, b + 1.2, b + 1.7, -0.25, 0.25, top=FISH_L)]
            tail = [B(3, 4.6, b - 0.3, b + 0.8, -1.1, 1.1, top=FISH), B(4.6, 5.4, b - 0.3, b + 1.2, -1.6, 1.6, top=FISH_L)]
            carrot = [B(-3, -1.5, b, b + 0.4, 3, 4.5, top=CARROT), B(1, 2.5, b, b + 0.4, -4.5, -3, top=CARROT)]
            greens = [B(-4.5, -2.5, b, b + 0.3, -4.6, -2.8, top=GREEN)]
            mushroom = [B(3.2, 4.4, b, b + 0.6, 2.8, 4.0, top=STEM), B(2.9, 4.7, b + 0.6, b + 1.1, 2.5, 4.3, top=CAP)]
            keep = [head + body + tail + carrot + greens + mushroom, head + body + carrot[:1] + greens + mushroom,
                    head + mushroom + carrot[:1], head][s]
            cubes += keep
        else:
            cubes.append(B(-3, 3, 1, 1.3, -0.2, 0.2, top=BONE))      # what is left: the spine
            cubes += [B(x, x + 0.25, 1, 1.25, -1.2, 1.2, top=BONE) for x in (-2, -0.5, 1, 2.5)]
        geos.append(geometry(GEO + f'river_lord_casserole_0_{s}_0', cubes, 64, 64))
    write_geometries(os.path.join(RP, 'models', 'blocks', 'river_lord_casserole.geo.json'), geos)
    tex = os.path.join(RP, 'textures', 'blocks', 'kfv_river_lord_casserole.png')
    a.save(tex)
    texture_set(tex)


# --------------------------------------------------------------------------- Dragon Koi Stone Grill
def sizzle():
    """A dark stone slab over two blocks with the Lava Dragon Koi seared on it, chilies on the side.
    Part 0 holds the head and the front of the body, part 1 the back and the tail. Stages: 0 whole ... 3 bones."""
    a = Atlas(64, 64)
    STONE, STONE_L, STONE_D = '#5e5e66', '#77777f', '#45454c'
    KOI, KOI_L, GOLD, BELLY, CHAR, EYE = '#d8452c', '#ee7a3c', '#f2c84a', '#f6e2c8', '#3a1e14', '#141414'
    RED, GREEN, BONE = '#c8281e', '#4f8f2e', '#ece6d6'
    B = lambda *v, top, side=None, bottom=None: box(*v, top, side, bottom, atlas=a)  # noqa: E731
    Y0, Y1 = 1.5, 4.0
    def slab(z0, z1):
        return [B(-6.5, 6.5, 0, Y0, z0, z1, top=STONE_L, side=STONE, bottom=STONE_D)]
    def meat(z0, z1):
        return [B(-2.5, 2.5, Y0, Y1, z0, z1, top=KOI, side=KOI_L)] + \
               [B(-2.5, 2.5, Y1, Y1 + 0.1, z, z + 0.4, top=CHAR) for z in (z0 + 0.8, (z0 + z1) / 2) if z + 0.4 < z1] + \
               [B(-0.3, 0.3, Y1, Y1 + 0.8, z0, z1, top=KOI_L), B(-1.2, 1.0, Y1, Y1 + 0.15, z0 + 0.5, min(z1, z0 + 2.5), top=GOLD)]
    spine = lambda z0, z1: [B(-0.3, 0.3, Y0, Y0 + 0.5, z0, z1, top=BONE)] + \
        [B(-1.6, 1.6, Y0, Y0 + 0.25, z, z + 0.25, top=BONE) for z in range(int(z0) + 1, int(z1), 2)]  # noqa: E731
    head = [B(-2, 2, Y0, 3.5, -6.5, -3, top=KOI, side=KOI_L), B(-1, 1, Y0, 2.7, -7.2, -6.5, top=BELLY),
            B(-2.15, -2, 2.6, 3.1, -5.5, -5, top=EYE), B(2, 2.15, 2.6, 3.1, -5.5, -5, top=EYE),
            B(-2.1, 2.1, Y0, 3.6, -3, -2.5, top=KOI_L)]
    chili0 = [B(3.5, 5.5, Y0, 2.1, -5, -4.3, top=RED), B(-5.5, -3.5, Y0, 2.1, 2, 2.7, top=GREEN), B(3.4, 5.6, Y0, 2, 4, 4.6, top=GREEN)]
    chili1 = [B(-5.6, -3.6, Y0, 2.1, -4, -3.3, top=RED), B(3.6, 5.6, Y0, 2.1, 0, 0.7, top=GREEN)]
    tail = [B(-1.5, 1.5, Y0, 3.3, 1, 3, top=KOI, side=KOI_L), B(-2.8, 2.8, Y0, 3.8, 3, 6, top=KOI_L), B(-2.8, 2.8, 3.8, 3.9, 4.5, 6, top=GOLD)]
    parts = {
        0: (slab(-7.5, 8), chili0, [meat(2.5, 8), meat(-2.5, 2.5)], head, spine(-3, 8)),
        1: (slab(-8, 7.5), chili1, [meat(-8, -3), meat(-3, 1)], tail, spine(-8, 1)),
    }
    geos = []
    for p, (base, chili, segments, end, bones) in parts.items():
        for s in range(4):
            cubes = base + chili
            if s < 3:
                for seg in segments[s:]:                             # each bite takes one segment
                    cubes += seg
                cubes += end
                if s > 0:
                    cubes += bones[:1]
            else:
                cubes += end + bones                                  # head (or tail) and the bones are left
            geos.append(geometry(GEO + f'dragon_koi_sizzle_{p}_{s}', cubes, 64, 64))
    write_geometries(os.path.join(RP, 'models', 'blocks', 'dragon_koi_sizzle.geo.json'), geos)
    tex = os.path.join(RP, 'textures', 'blocks', 'kfv_dragon_koi_sizzle.png')
    a.save(tex)
    texture_set(tex)


# --------------------------------------------------------------------------- Fish Cleaning Board
# The nine fish that came to the board in 1.4.0. Each gets its own models, shaped like a look-alike's (same cuts)
# and re-coloured: every face in the look-alike's skin takes one of the new fish's three skin colours (dark, mid,
# light, by how bright it was); flesh, guts, eyes and bones stay as they are. The colours are swatches below the
# board's atlas (from row 100).
BOARD_FISH = {   # name: (look-alike, dark, mid, light)
    'loach': ('eel', '#4a3c22', '#86703f', '#c2a868'),
    'mudskipper': ('catfish', '#433d30', '#7a6e52', '#b4a47c'),
    'golden_croaker': ('yellow_croaker', '#8a5a12', '#e8a02a', '#f8d870'),
    'chorus_carp': ('carp', '#5a2c6a', '#9a5ab0', '#e0a8e8'),
    'ender_angler': ('anglerfish', '#1e1428', '#3e2a52', '#7a5aa0'),
    'blazefin': ('sea_bream', '#7a1e10', '#d8452c', '#f2a03a'),
    'lava_eel': ('eel', '#3a0e0a', '#8a1e14', '#d8502a'),
    'magma_koi': ('carp', '#6a2a10', '#e0601e', '#f2a032'),
    'lava_dragon_koi': ('carp', '#5a0a08', '#c8281e', '#e85a2a'),
}


def _hsv(rgb):
    import colorsys
    return colorsys.rgb_to_hsv(*(c / 255 for c in rgb[:3]))


def _kind(c):
    """What a face of a fish on the board shows: 'skin', or something to keep (flesh, bone, guts, eye)."""
    h, s, v = _hsv(c)
    if not c[3] or v < 0.16:
        return 'eye'
    if v > 0.72 and s < 0.28:
        return 'flesh'
    if s > 0.62 and (h < 0.03 or h > 0.95) and v > 0.45:
        return 'guts'
    return 'skin'


def board_fish():
    import json
    from PIL import Image
    data = json.load(open(os.path.join(os.path.dirname(HERE), 'tools', 'data', 'CLEANING.json'), encoding='utf-8'))
    geo_path = os.path.join(RP, 'models', 'blocks', 'fish_cleaning_board.geo.json')
    tex_path = os.path.join(RP, 'textures', 'blocks', 'kfv_fish_cleaning_board.png')
    geo = json.load(open(geo_path, encoding='utf-8'))
    by_id = {g['description']['identifier']: g for g in geo['minecraft:geometry']}
    base = Image.open(tex_path).convert('RGBA')
    a = Atlas(256, 128, start=(0, 100), base=tex_path)
    pfx = GEO + 'fish_cleaning_board_'

    def colour_of(face):
        (u, v), (w, h) = face['uv'], face['uv_size']
        x, y = int(u + min(w, 0) + abs(w) / 2), int(v + min(h, 0) + abs(h) / 2)
        return base.getpixel((min(255, max(0, x)), min(127, max(0, y))))

    for name, (like, *palette) in BOARD_FISH.items():
        e, src = data[f'{NS}:{name}'], data[f'{NS}:{like}']
        stages = range(e.get('first', 1 if e['scales'] else 2), 4)
        sources = [json.loads(json.dumps(by_id[pfx + f"{src['index']}_{s}"])) for s in stages]
        values = [_hsv(colour_of(f))[2] for g in sources for cube in g['bones'][0]['cubes'][1:]
                  for f in cube['uv'].values() if _kind(colour_of(f)) == 'skin']
        lo, hi = (min(values), max(values)) if values else (0, 1)
        cells = [a.add(c, noise=4) for c in palette]
        for stage, g in zip(stages, sources):
            g['description']['identifier'] = pfx + f"{e['index']}_{stage}"
            for cube in g['bones'][0]['cubes'][1:]:                  # the first cube is the board itself
                for face in cube['uv'].values():
                    c = colour_of(face)
                    if _kind(c) != 'skin':
                        continue
                    rel = (_hsv(c)[2] - lo) / max(hi - lo, 1e-6)
                    face['uv'], face['uv_size'] = list(cells[0 if rel < 0.34 else 1 if rel < 0.7 else 2]), [2, 2]
            by_id[g['description']['identifier']] = g
    geo['minecraft:geometry'] = list(by_id.values())
    write_geometries(geo_path, geo['minecraft:geometry'])
    a.save(tex_path)
    # the atlas keeps its own MER and height maps; the new cells get the board's usual material
    mer_p, hgt_p = tex_path[:-4] + '_mer.png', tex_path[:-4] + '_height.png'
    mer, hgt = Image.open(mer_p), Image.open(hgt_p)
    common = max(mer.getcolors(256 * 128), key=lambda cv: cv[0])[1]
    for (cu, cv) in a.cells.values():
        for y in range(cv - 1, cv + 3):
            for x in range(cu - 1, cu + 3):
                r, g, b, _ = a.image.getpixel((x, y))
                mer.putpixel((x, y), common)
                hgt.putpixel((x, y), int(96 + (0.299 * r + 0.587 * g + 0.114 * b) * 0.5))
    mer.save(mer_p)
    hgt.save(hgt_p)


# --------------------------------------------------------------------------- Fish Tank
# Shrimp and Purpur Shrimp walk the tank floor like the Cave Crayfish (its shape, their own colours); the Oyster
# sits on the floor, half open, with a pearl. Run after tools/repaint_tank_fish.py, which rebuilds the tank models.
TANK_RECOLOUR = {'shrimp': ('cave_crayfish', '#a8442a', '#e0764a', '#f8b89a'),
                 'purpur_shrimp': ('cave_crayfish', '#5a3a6a', '#a070b8', '#d8b0e8')}


def tank_creatures():
    import json
    from PIL import Image
    geo_path = os.path.join(RP, 'models', 'entity', 'tank_fish.geo.json')
    tex_path = os.path.join(RP, 'textures', 'entity', 'kfv_tank_fish.png')
    geo = json.load(open(geo_path, encoding='utf-8'))
    by_id = {g['description']['identifier']: g for g in geo['minecraft:geometry']}
    big = Image.open(tex_path).convert('RGBA')                    # 512x512; the geometry counts 256 (2 texels a unit)
    k = big.width // 256
    a = Atlas(256, 256, start=(0, 112))                          # in UV units, below the fish (they end at row 108)
    pfx = GEO + 'tank_fish.'

    def colour_of(face):
        (u, v), (w, h) = face['uv'], face['uv_size']
        return big.getpixel((int((u + w / 2) * k), int((v + h / 2) * k)))

    for name, (like, *palette) in TANK_RECOLOUR.items():
        g = json.loads(json.dumps(by_id[pfx + like]))
        g['description']['identifier'] = pfx + name
        faces = [f for b in g['bones'] for c in b.get('cubes', []) for f in c['uv'].values()]
        vals = [_hsv(colour_of(f))[2] for f in faces if _hsv(colour_of(f))[2] >= 0.16]
        lo, hi = min(vals), max(vals)
        cells = [a.add(c, noise=4) for c in palette]
        for f in faces:
            v = _hsv(colour_of(f))[2]
            if v < 0.16:                                         # eyes stay
                continue
            rel = (v - lo) / max(hi - lo, 1e-6)
            f['uv'], f['uv_size'] = list(cells[0 if rel < 0.34 else 1 if rel < 0.7 else 2]), [2, 2]
        by_id[pfx + name] = g

    SHELL, SHELL_D, SHELL_L, NACRE, FLESH, PEARL = '#8a8270', '#6e6858', '#9a9280', '#e8e2d4', '#d8cfb8', '#ffffff'
    B = lambda *v, top, side=None: box(*v, top, side, atlas=a)  # noqa: E731
    oyster = [B(-2, 2, 0, 0.7, -1.6, 1.6, top=SHELL, side=SHELL_D), B(-1.8, 1.8, 0.7, 0.9, -1.4, 1.4, top=NACRE),
              B(-1.2, 1.2, 0.9, 1.2, -1, 1, top=FLESH), B(-0.3, 0.3, 1.2, 1.6, 0.3, 0.9, top=PEARL),
              B(-2, 2, 1.3, 1.8, -1.6, 0.0, top=SHELL_L, side=SHELL_D), B(-1.8, 1.8, 0.9, 1.3, -1.6, -1.2, top=SHELL_D)]
    by_id[pfx + 'oyster'] = {
        'description': {'identifier': pfx + 'oyster', 'texture_width': 256, 'texture_height': 256,
                        'visible_bounds_width': 2, 'visible_bounds_height': 2, 'visible_bounds_offset': [0, 0.5, 0]},
        'bones': [{'name': 'spin', 'pivot': [0, 0, 0]}, {'name': 'fish', 'parent': 'spin', 'pivot': [0, 0, 0], 'cubes': oyster}]}

    geo['minecraft:geometry'] = list(by_id.values())
    write_geometries(geo_path, geo['minecraft:geometry'])
    cells = a.image.resize((512, 512), Image.NEAREST)
    big.alpha_composite(cells)
    big.save(tex_path)
    for suffix in ('_mer.png', '_height.png'):                    # the new cells in the RTX maps too
        p = tex_path[:-4] + suffix
        if not os.path.exists(p):
            continue
        m = Image.open(p)
        mode = m.mode
        m = m.convert('RGBA')
        common = max(m.crop((0, 0, 512, 216)).getcolors(512 * 216), key=lambda cv: cv[0])[1]
        for (cu, cv) in a.cells.values():
            for y in range((cv - 1) * k, (cv + 3) * k):
                for x in range((cu - 1) * k, (cu + 3) * k):
                    if suffix == '_mer.png':
                        m.putpixel((x, y), common)
                    else:
                        r, g, b, _ = big.getpixel((x, y))
                        l = int(96 + (0.299 * r + 0.587 * g + 0.114 * b) * 0.5)
                        m.putpixel((x, y), (l, l, l, 255))
        m.convert(mode).save(p)


def feasts():
    casserole()
    sizzle()


if __name__ == '__main__':
    feasts()
    board_fish()
    tank_creatures()
    print('done; now run: python tools/gen_additions_1_4.py && python tools/build.py build')
