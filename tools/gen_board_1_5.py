"""Fish Cleaning Board (魚案板): models for the catches that go on the board from 1.5.0 on.

  python tools/gen_board_1_5.py

Shrimp, crab and jellyfish are laid flat as their item icons show them (a view from above), not turned to a side
view like the fish (tools/gen_board_fish.py, whose column modelling this reuses). Each cut has its own look:
  shrimp     1 whole        2 head off (the head end cleared)       3 peeled (pale flesh, a little flatter)
  crab       1 whole        2 shell off (the back shows orange roe) 3 cleaned (pale meat)
  jellyfish  2 whole        3 feelers off (only the bell is left)
  dried shell-on shrimp   3 a small heap, rubbed once
  whole squid 1 whole        2 gutted (paler inside)                  3 cartilage out (paler still)
  flatfish   (flounder, ray) laid flat as the icon shows it: 1 whole, 2 scales off (paler), 3 a red gutting cut
  side       a fish whose icon is already a side view (the lanternfish): used as it is, not turned 45 degrees
  drawn      the Meteor Marlin: its icon is too small and crooked for the bill and sail to survive, so its side view
             is drawn here (bill, sail fin, crescent tail, starlight specks) in the icon's colours
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
TW, TH = 512, 256                # the atlas in pixels: twice the board's 256x128 (the block's textures must share its shape)
UV = 0.5                         # the models keep the board's 256x128 UV space, so atlas pixels are halved

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
    'dried_shell_shrimp': (55, 'pile', 16, 1.0, None),
    'whole_squid':        (56, 'squid', 22, 1.5, None),
    # 1.5.0 new fish: their board index is whatever tools/gen_1_5.py gave them (read from CLEANING.json)
    'mycelium_flounder':  (None, 'flatfish', 22, 1.5, None),
    'cherry_trout':       (None, 'fish', 11.0, 2.0, True),
    'creek_shrimp':       (None, 'shrimp', 16, 1.0, (0.0, 0.15)),
    'echo_ray':           (None, 'flatfish', 26, 1.5, None),
    'sculk_lanternfish':  (None, 'side', 16, 1.5, True),
    'meteor_marlin':      (None, 'drawn', 28, 2.0, True),      # step 11
}
_board = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'CLEANING.json'), encoding='utf-8'))
for _k, _v in list(CATCH.items()):
    if _v[0] is None:
        CATCH[_k] = (_board[f'{NS}:{_k}']['index'],) + _v[1:]
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


MARLIN = {'outline': (14, 20, 40), 'back': (26, 44, 96), 'dorsal': (48, 88, 168), 'flank': (78, 128, 196),
          'belly': (196, 204, 214), 'bar': (120, 170, 220), 'star': (246, 226, 96), 'sail': (36, 66, 140), 'bill': (34, 44, 70)}


def marlin_sprite(L=28):
    """A blue marlin side on, head left, L pixels long: a long bill, the tall sail fin, a crescent tail."""
    c = MARLIN
    H = 18
    im = Image.new('RGBA', (L, H)); px = im.load()
    mid = 10                                         # the body's centre row
    body = {}
    x0, x1 = round(L * 0.2), round(L * 0.8)
    for x in range(x0, x1 + 1):
        t = (x - x0) / (x1 - x0)
        half = 4.3 * math.sin(math.pi * min(0.5, t * 1.4) ** 0.9 / 0.5 ** 0.9 / 2) if t < 0.55 else 4.3 * (1 - (t - 0.55) / 0.45 * 0.8)
        half = max(1.0, half)
        top, bot = round(mid - half), round(mid + half)
        for y in range(top, bot + 1):
            body[x, y] = (y - top) / max(1, bot - top)
    for x in range(0, x0 + 1):                        # the bill, rising a little to the snout
        body[x, mid - 1] = 0.45
    for x, h in zip(range(x0 + 3, x0 + 13), (6, 6, 5, 5, 4, 3, 3, 2, 2, 1)):   # the sail
        top = min(y for (xx, y) in body if xx == x)
        for y in range(top - h, top):
            body[x, y] = -1
    for x in range(x0 + 4, x0 + 8):                   # pectoral fin
        for y in range(mid + 2, mid + 2 + (x0 + 8 - x)):
            body.setdefault((x, y + 1), -2)
    for x in range(x1 + 1, L):                        # crescent tail
        k = x - x1
        for y in (mid - 2 - k, mid - 1 - k, mid - k, mid + k, mid + 1 + k, mid + 2 + k):
            if 0 <= y < H:
                body[x, y] = -3
        body[x, mid] = -3 if k < 2 else None
    for (x, y), t in body.items():
        if t is None or not (0 <= x < L and 0 <= y < H):
            continue
        if t == -1:
            col = c['sail'] if (x * 3 + y) % 7 else c['star']
        elif t in (-2, -3):
            col = c['dorsal']
        elif x <= x0:
            col = c['bill']
        else:
            col = c['back'] if t < 0.2 else c['dorsal'] if t < 0.42 else c['flank'] if t < 0.62 else c['belly']
            if 0.25 < t < 0.6 and (x % 4 == 0):
                col = c['bar']                        # the pale bars down a marlin's side
            if t < 0.35 and (x * 7 + y * 3) % 11 == 0:
                col = c['star']                       # starlight specks on the back
        px[x, y] = col + (255,)
    # outline
    out = im.copy(); op = out.load()
    for y in range(H):
        for x in range(L):
            if px[x, y][3] == 0:
                continue
            edge = any(not (0 <= x + a < L and 0 <= y + b < H) or px[x + a, y + b][3] == 0
                       for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge and px[x, y][:3] not in (c['bill'],):
                op[x, y] = tuple(round(v * 0.55 + o * 0.45) for v, o in zip(px[x, y][:3], c['outline'])) + (255,)
    ex, ey = x0 + 2, mid - 1                          # eye
    op[ex, ey] = (12, 12, 16, 255); op[ex, ey - 1] = (236, 236, 240, 255)
    return out.crop(out.getbbox())


def belly_slit(sp):
    """Belly opened, for a fish with a tall fin over it: the cut follows the underside, two pixels up from it."""
    out = sp.copy(); px = out.load(); w, h = sp.size
    for x in range(round(w * 0.3), round(w * 0.62)):
        col = [y for y in range(h) if px[x, y][3]]
        if len(col) < 5:
            continue
        y = col[-1] - 2
        px[x, y] = gb.SLIT + (255,)
        px[x, y - 1] = gb.SLIT_EDGE + (255,)
    return out


def side_icon(name, size):
    """An icon that is already a side view (head left): scaled so it is `size` pixels long."""
    return flat_sprite(name, size)


def flat_cut(sp, at):
    """A gutting cut on a fish lying flat: a short red curve across the body at `at` of its length."""
    out = sp.copy(); px = out.load(); w, h = sp.size
    x = round(w * at)
    rows = [y for y in range(h) if px[x, y][3]]
    if not rows:
        return out
    top, bot = rows[0], rows[-1]
    for y in range(top + (bot - top) // 4, bot - (bot - top) // 4 + 1):
        xx = x + (1 if abs(y - (top + bot) / 2) > (bot - top) / 6 else 0)
        if px[xx, y][3]:
            px[xx, y] = gb.SLIT + (255,)
            if px[xx + 1, y][3]:
                px[xx + 1, y] = gb.SLIT_EDGE + (255,)
    return out


def stages(name):
    idx, kind, size, hmax, corner = CATCH[name]
    sp = flat_sprite(name, size) if kind not in ('fish', 'side', 'drawn') else None
    if kind in ('side', 'drawn'):
        whole = side_icon(name, size) if kind == 'side' else marlin_sprite(size)
        st = {1: whole, 2: gb.scaled_off(whole)} if corner else {2: whole}
        st[3] = gb.slit(st[2]) if kind == 'side' else belly_slit(st[2])
        return idx, hmax, st
    if kind == 'shrimp':
        off = head_off(sp, corner)
        return idx, hmax, {1: sp, 2: off, 3: peeled(off)}
    if kind == 'crab':
        return idx, hmax, {1: sp, 2: recolour_inner(sp, ROE, 0.6), 3: recolour_inner(sp, MEAT, 0.75)}
    if kind == 'fish':                              # side view, as the older board fish (scales: last field)
        whole = gb.side_sprite(name, size)
        if corner:
            st = {1: whole, 2: gb.scaled_off(whole)}
        else:
            st = {2: whole}
        st[3] = gb.slit(st[2])
        return idx, hmax, st
    if kind == 'flatfish':                          # flat on the board as the icon shows it; scaled if it has a first stage
        first = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'CLEANING.json'), encoding='utf-8'))[f'{NS}:{name}']['first']
        st = {1: sp, 2: gb.scaled_off(sp)} if first == 1 else {2: sp}
        st[3] = flat_cut(st[2], 0.3 if name == 'mycelium_flounder' else 0.5)
        return idx, hmax, st
    if kind == 'squid':                             # gutted: the inside shows pale; the cartilage out: paler still
        return idx, hmax, {1: sp, 2: recolour_inner(sp, MEAT, 0.35), 3: recolour_inner(sp, MEAT, 0.7, depth=1)}
    if kind == 'pile':
        return idx, hmax, {3: sp}                       # one rub and it is done
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
            cubes = gb.fish_cubes(sp, h, (u, v))
            for cube in cubes:
                for face in cube['uv'].values():
                    face['uv'] = [round(x * UV, 4) for x in face['uv']]
                    face['uv_size'] = [round(x * UV, 4) for x in face['uv_size']]
            cubes = [base] + cubes
            geos.append({'description': {
                'identifier': f'geometry.{NS}.fish_cleaning_board_{idx}_{cut}', 'texture_width': 256, 'texture_height': 128,
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
