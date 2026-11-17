"""Fish Cleaning Board (魚案板): models for the catches that go on the board from 1.5.0 on.

  python tools/gen_board_1_5.py

Shrimp, crab and jellyfish are laid flat as their item icons show them (a view from above), not turned to a side
view like the fish (tools/gen_board_fish.py, whose column modelling this reuses). Each cut has its own look:
  shrimp     1 whole        2 head off (the head end cleared)       3 peeled (pale flesh, a little flatter)
  crab       1 whole        2 shell off (the back shows orange roe) 3 cleaned (pale meat)
  jellyfish  2 whole        3 feelers off (only the bell is left)
Writes models/blocks/fish_cleaning_board_1_5.geo.json, textures/blocks/kfv_board_shell.png (its own material
instance on the board) and the block permutations. Safe to run again.
"""
import json, math, os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr
import gen_board_fish as gb

RP, BP, NS = gb.RP, gb.BP, gb.NS
GEO = os.path.join(RP, 'models', 'blocks', 'fish_cleaning_board_1_5.geo.json')
TEX_NAME = 'kfv_board_shell'
TEX = os.path.join(RP, 'textures', 'blocks', TEX_NAME + '.png')
TW, TH = 256, 128

# name: (board index, kind, size in sprite pixels (0.5 units each), max height, head corner as fractions (x, y))
CATCH = {
    'shrimp':           (44, 'shrimp', 18, 1.5, (0.0, 0.15)),
    'live_shrimp':      (45, 'shrimp', 18, 1.5, (1.0, 0.1)),
    'purpur_shrimp':    (46, 'shrimp', 18, 1.5, (0.0, 0.15)),
    'cave_crayfish':    (47, 'shrimp', 20, 1.5, (0.0, 1.0)),
    'lobster':          (48, 'shrimp', 24, 2.0, (1.0, 0.0)),
    'crab':             (49, 'crab', 20, 2.0, None),
    'basalt_crab':      (50, 'crab', 20, 2.0, None),
    'glow_crab':        (51, 'crab', 20, 2.0, None),
    'king_crab':        (52, 'crab', 24, 2.0, None),
    'moon_jellyfish':   (53, 'jelly', 20, 1.5, None),
    'chorus_jellyfish': (54, 'jelly', 20, 1.5, None),
}
FLESH = (244, 214, 196)
ROE = (236, 140, 40)
MEAT = (246, 236, 224)


def flat_sprite(name, size):
    """The icon, its loose pixels dropped, scaled (nearest) so its longer side is `size` pixels."""
    im = gb.keep_main(gb.icon(name))
    im = im.crop(im.getbbox())
    f = size / max(im.size)
    return im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), Image.NEAREST)


def inner(sp, depth):
    """Pixels at least `depth` steps inside the outline."""
    px = sp.load(); w, h = sp.size
    solid = {(x, y) for y in range(h) for x in range(w) if px[x, y][3]}
    keep = set(solid)
    for _ in range(depth):
        keep = {(x, y) for (x, y) in keep if all((x + a, y + b) in keep for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    return keep


def tint(c, to, t):
    return tuple(round(a + (b - a) * t) for a, b in zip(c[:3], to)) + (255,)


def head_off(sp, corner):
    """Clear everything within 38% of the sprite's diagonal of its head corner; drop what is left loose."""
    out = sp.copy(); px = out.load(); w, h = sp.size
    cx, cy = corner[0] * (w - 1), corner[1] * (h - 1)
    r = 0.38 * math.hypot(w, h)
    for y in range(h):
        for x in range(w):
            if math.hypot(x - cx, y - cy) < r:
                px[x, y] = (0, 0, 0, 0)
    return gb.keep_main(out)


def peeled(sp):
    out = sp.copy(); px = out.load()
    for y in range(sp.height):
        for x in range(sp.width):
            if px[x, y][3]:
                px[x, y] = tint(px[x, y], FLESH, 0.65)
    return out


def recolour_inner(sp, colour, t, depth=2):
    out = sp.copy(); px = out.load()
    for (x, y) in inner(sp, depth):
        px[x, y] = tint(px[x, y], colour, t)
    return out


def bell_only(sp):
    """A jellyfish's bell: the rows down to where the body is widest (and one more)."""
    out = sp.copy(); px = out.load(); w, h = sp.size
    widths = [sum(1 for x in range(w) if px[x, y][3]) for y in range(h)]
    cut = max(range(h // 2 + 1), key=lambda y: widths[y]) + 2
    for y in range(cut, h):
        for x in range(w):
            px[x, y] = (0, 0, 0, 0)
    return out


def stages(name):
    idx, kind, size, hmax, corner = CATCH[name]
    sp = flat_sprite(name, size)
    if kind == 'shrimp':
        off = head_off(sp, corner)
        return idx, hmax, {1: sp, 2: off, 3: peeled(off)}
    if kind == 'crab':
        return idx, hmax, {1: sp, 2: recolour_inner(sp, ROE, 0.6), 3: recolour_inner(sp, MEAT, 0.75)}
    return idx, hmax, {2: sp, 3: bell_only(sp)}


def build():
    atlas = Image.new('RGBA', (TW, TH))
    geos = []
    u = v = row_h = 0
    base = gb.board_cube()
    for name in CATCH:
        idx, hmax, st = stages(name)
        for cut, sp in st.items():
            need = sp.width + sp.height
            if u + need > TW:
                u = 0; v += row_h; row_h = 0
            if v + max(sp.width, sp.height) > TH:
                raise SystemExit('board shell atlas is full')
            atlas.alpha_composite(sp, (u, v))
            atlas.alpha_composite(sp.transpose(Image.TRANSPOSE), (u + sp.width, v))
            gb.TEX_NAME = TEX_NAME                      # fish_cubes names the material instance after this
            h = hmax * (0.7 if cut == 3 and CATCH[name][1] == 'shrimp' else 1)
            cubes = [base] + gb.fish_cubes(sp, h, (u, v))
            geos.append({'description': {
                'identifier': f'geometry.{NS}.fish_cleaning_board_{idx}_{cut}', 'texture_width': TW, 'texture_height': TH,
                'visible_bounds_width': 3, 'visible_bounds_height': 3, 'visible_bounds_offset': [0, 0.75, 0]},
                'bones': [{'name': 'root', 'pivot': [0, 0, 0], 'cubes': cubes}]})
            u += need; row_h = max(row_h, sp.width, sp.height)
    return atlas, geos


def main():
    atlas, geos = build()
    atlas.save(TEX)
    with open(GEO, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'format_version': '1.16.0', 'minecraft:geometry': geos}, f, separators=(',', ':'))
    gb.TEX_NAME = TEX_NAME
    gb.write_block(geos)
    gb.write_terrain()
    ts = TEX[:-4] + '.texture_set.json'
    if not os.path.exists(ts):
        with open(ts, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'format_version': '1.16.100', 'minecraft:texture_set': {
                'color': TEX_NAME, 'metalness_emissive_roughness': TEX_NAME + '_mer', 'heightmap': TEX_NAME + '_height'}}, f, indent=2)
            f.write('\n')
    pbr.refresh(TEX)
    print(len(geos), 'board models,', max(len(g['bones'][0]['cubes']) for g in geos), 'cubes at most')


if __name__ == '__main__':
    main()
