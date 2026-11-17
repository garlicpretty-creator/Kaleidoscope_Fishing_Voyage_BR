"""Item icons added in 1.5.0 that are drawn from icons the pack already has, so they match its style.

  python tools/icons_1_5.py

Each icon starts again from its source every run. A recolour keeps the source's shading: the pixels picked by
`pick` are sorted by brightness and mapped onto a new ramp (dark outline first, highlight last); every other
pixel is left as it is. Writes textures/items/kfv_<name>.png, its texture set and its RTX maps (tools/pbr.py).
"""
import colorsys, json, os

from PIL import Image

import pbr

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(os.path.dirname(HERE), 'Kaleidoscope Fishing Voyage [RP]', 'textures', 'items')
SRC = os.path.join(HERE, 'data', 'icon_src_1_5')


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def hsv(c):
    return colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def ramp_colour(ramp, t):
    """t in 0..1 along a list of hex colours."""
    cols = [rgb(h) for h in ramp]
    x = t * (len(cols) - 1)
    i = min(len(cols) - 2, int(x))
    f = x - i
    return tuple(round(cols[i][k] + (cols[i + 1][k] - cols[i][k]) * f) for k in range(3))


def recolour(im, pick, ramp):
    px = im.load()
    chosen = [(x, y) for y in range(im.height) for x in range(im.width) if px[x, y][3] and pick(px[x, y])]
    if not chosen:
        raise SystemExit('recolour: nothing picked')
    lo = min(lum(px[p]) for p in chosen)
    hi = max(lum(px[p]) for p in chosen)
    for p in chosen:
        t = (lum(px[p]) - lo) / (hi - lo) if hi > lo else 0.5
        px[p] = ramp_colour(ramp, t) + (255,)
    return im


def hue_between(a, b, min_s=0.25):
    return lambda c: a <= hsv(c)[0] * 360 <= b and hsv(c)[1] >= min_s


def grey(max_s=0.2, min_v=0.0):
    return lambda c: hsv(c)[1] <= max_s and hsv(c)[2] >= min_v


def source(name):
    return Image.open(os.path.join(ITEMS, f'kfv_{name}.png')).convert('RGBA')


def put(im, cells):
    for (x, y), h in cells.items():
        im.putpixel((x, y), rgb(h) + (255,) if h else (0, 0, 0, 0))
    return im


def build():
    out = {}
    # Frostlake Scale: the Dragon Scale's shape in ice
    out['frostlake_scale'] = recolour(source('dragon_scale'), lambda c: True,
                                      ['#22405f', '#3f73a6', '#6aa9d8', '#a9d8f2', '#e9f8ff'])
    # Whisker Line: the Wire Line's spool, wound with the River Lord's dark whisker
    out['whisker_line'] = recolour(source('wire_line'), grey(0.22, 0.25), ['#120d0c', '#231815', '#35241c', '#4a3425', '#6b4b33'])
    # Dragon Scale Bobber / Frost Scale Bobber: the Glow Bobber's float, in scale colours
    teal = hue_between(120, 200, 0.2)
    out['dragon_scale_bobber'] = recolour(source('glow_bobber'), teal, ['#5a1408', '#a02a0c', '#d9541a', '#f58a2a', '#ffd070'])
    out['frost_scale_bobber'] = recolour(source('glow_bobber'), teal, ['#22405f', '#3f73a6', '#6aa9d8', '#a9d8f2', '#f2fbff'])
    # Emperor Bone Hook: the Bone Hook in cold blue-white bone
    out['emperor_bone_hook'] = recolour(source('bone_hook'), lambda c: True, ['#1b2a4a', '#3d5a8c', '#8fb0d6', '#d6e6f5', '#ffffff'])
    # Emperor Tuna Fin: its own drawing (tools/data/icon_src_1_5)
    out['emperor_tuna_fin'] = Image.open(os.path.join(SRC, 'emperor_tuna_fin.png')).convert('RGBA')
    # Icons finished in the 1.4 work (outlined already): taken as they are
    for name in FINISHED:
        out[name] = Image.open(os.path.join(SRC, f'{name}.png')).convert('RGBA')
    # Retro Diffusion pictures: a pixel of margin where they touch the edge, then the pack's dark outline
    for name in GENERATED:
        im = hard(Image.open(os.path.join(SRC, f'{name}.png')).convert('RGBA'))
        if name in RAMP:                                  # recoloured so it does not read as its neighbour
            im = recolour(im, lambda c_: True, RAMP[name])
        out[name] = outline(margin(im))
    # the gutted fish: the generated picture as it is, and recoloured for skipjack (dark blue back) and flying fish (blue-silver)
    gut = lambda: hard(Image.open(os.path.join(SRC, 'gutted_fish.png')).convert('RGBA'))
    out['gutted_fish'] = outline(margin(gut()))
    out['gutted_skipjack'] = slit_open(source('skipjack'))
    out['gutted_flying_fish'] = slit_open(source('flying_fish'))
    for name, (ramp, stripes) in CUTS.items():
        im = recolour(hard(Image.open(os.path.join(SRC, f'{name}.png')).convert('RGBA')), lambda c_: True, ramp)
        px = im.load()
        solid = [(x, y) for y in range(16) for x in range(16) if px[x, y][3]]
        if stripes:                                   # fat: light diagonal lines across the slice
            for (x, y) in solid:
                if (x + y) % (6 - stripes) == 0 and 0 < x < 15:
                    px[x, y] = rgb(ramp[-1]) + (255,)
        else:                                         # bonito: a silver skin along the top edge
            for x in range(16):
                col = [y for y in range(16) if px[x, y][3]]
                if col:
                    px[x, col[0] + 1 if len(col) > 2 else col[0]] = rgb(ramp[-1]) + (255,)
        out[name] = outline(margin(im))
    return out


FINISHED = ['crab_meat',
            'stir_fried_shrimp', 'crab_congee', 'shrimp_noodle_soup', 'crab_roe_rice', 'jellyfish_salad']
GENERATED = ['shrimp_head', 'shrimp_meat', 'shrimp_shell', 'crab_shell', 'crab_roe', 'jellyfish_skin', 'squid_tentacles',
             'lobster_tomalley', 'crab_leg', 'boiled_shrimp', 'steamed_crab_leg', 'grilled_crab_leg',
             'salted_shrimp', 'dried_shell_shrimp', 'xo_sauce', 'dried_shrimp_greens',
             'whole_squid', 'fried_squid_tentacles', 'grilled_squid_tentacles', 'otoro_nigiri', 'spicy_dried_fish',
             'purged_clam', 'clam_steamed_egg',
             'mycelium_flounder', 'spore_seahorse', 'cherry_trout', 'creek_shrimp', 'echo_ray', 'sculk_lanternfish',
             'mushroom_flounder_stew', 'cherry_trout_rice', 'fried_creek_shrimp', 'echo_ray_pot',
             'meteor_marlin', 'aurora_icefish', 'star_sand', 'fertilized_roe', 'fishing_skiff', 'jellyfish_radish']
# Dried Shell-on Shrimp sun-browned, so it is not taken for Salted Shrimp or Shrimp Shells
RAMP = {'dried_shell_shrimp': ['#2a140c', '#5a3018', '#8a5a30', '#b48450', '#d8b07a']}
# The three tuna cuts came out of the generator as the same red block: each is recoloured so they tell apart.
CUTS = {
    'chutoro': (['#5a1a22', '#a63a46', '#d9707a', '#f0a0a6', '#fbe0e0'], 3),   # medium pink, thin fat lines
    'otoro': (['#6a2a32', '#c56a74', '#ec9ea4', '#f8cfd0', '#ffffff'], 2),     # pale pink, white marbling
    'bonito_sashimi': (['#2a0a10', '#5a1420', '#8a2232', '#b03a48', '#d8d8dc'], 0),   # dark red, a silver skin edge
}


def hard(im):
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            px[x, y] = (r, g, b, 255) if a >= 128 else (0, 0, 0, 0)
    return im


def margin(im):
    """Clear the outermost column / row on any side the drawing touches."""
    px = im.load()
    bb = im.getbbox()
    if bb:
        for x in ([0] if bb[0] == 0 else []) + ([15] if bb[2] == 16 else []):
            for y in range(16):
                px[x, y] = (0, 0, 0, 0)
        for y in ([0] if bb[1] == 0 else []) + ([15] if bb[3] == 16 else []):
            for x in range(16):
                px[x, y] = (0, 0, 0, 0)
    return im


def outline(im):
    """Darken the silhouette's edge pixels into a warm outline, as the pack's other icons have."""
    px = im.load()
    solid = {(x, y) for y in range(16) for x in range(16) if px[x, y][3]}
    for (x, y) in solid:
        if any((x + dx, y + dy) not in solid for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            r, g, b, _ = px[x, y]
            px[x, y] = (int(r * 0.34) + 14, int(g * 0.28) + 8, int(b * 0.26) + 6, 255)
    return im


def slit_open(im):
    """A whole-fish icon (drawn corner to corner, head lower left) with its belly opened: a red cut along the lower
    side of the body's middle, edged in pale flesh, as on the Fish Cleaning Board."""
    px = im.load()
    # walk the fish's long diagonal; the lower edge is the last opaque pixel below each point of it
    cut = []
    for t in range(5, 12):
        x, y = t, 15 - t
        while y + 1 < 16 and px[x, y + 1][3]:
            y += 1
        if px[x, y][3]:
            cut.append((x, y - 1))
    for (x, y) in cut:
        if 0 <= y < 16 and px[x, y][3]:
            px[x, y] = rgb('#8a1a20') + (255,)
            if y - 1 >= 0 and px[x, y - 1][3]:
                px[x, y - 1] = rgb('#f2c4b0') + (255,)
    return im


def shrimp_head():
    """Drawn by hand: no generated picture showed a head alone. A shrimp's head shell pointing left, with its spike,
    black eye and long feelers, small legs below, and the pale cut where the body came off on the right."""
    rows = [
        '................',
        'aa..............',
        '..aa............',
        '....aa..........',
        'a.....a.........',
        '.aa....OOOOO....',
        '...aa.OppppPOO..',
        '.....OppkpPPPfO.',
        '...OOppppPPPPfO.',
        '..OspppppPPPPfO.',
        '...OOpppPPPPPfO.',
        '.....OOPPPPPOO..',
        '......l.l.l.O...',
        '.....l.l.l......',
        '................',
        '................',
    ]
    pal = {'O': '#5a1f14', 'p': '#f08a6a', 'P': '#d9603e', 'k': '#140c0a', 'f': '#f6cdb2', 's': '#c74a30',
           'a': '#c45a3c', 'l': '#a8432a'}
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != '.':
                im.putpixel((x, y), rgb(pal[ch]) + (255,))
    return im


def write(name, im):
    assert im.size == (16, 16), (name, im.size)
    path = os.path.join(ITEMS, f'kfv_{name}.png')
    im.save(path)
    ts = path[:-4] + '.texture_set.json'
    if not os.path.exists(ts):
        with open(ts, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'format_version': '1.16.100', 'minecraft:texture_set': {
                'color': f'kfv_{name}', 'metalness_emissive_roughness': f'kfv_{name}_mer', 'normal': f'kfv_{name}_normal'}}, f, indent=2)
            f.write('\n')
    pbr.refresh(path)


def entity_textures():
    """The bobber on the water for the two scale bobbers (styles 7 and 8), and the whisker line's colour."""
    ent = os.path.join(os.path.dirname(ITEMS), 'entity')
    glow = Image.open(os.path.join(ent, 'kfv_bobber_glow.png')).convert('RGBA')
    teal = hue_between(120, 200, 0.2)
    for name, ramp in (('dragon', ['#5a1408', '#a02a0c', '#d9541a', '#f58a2a', '#ffd070']),
                       ('frost', ['#22405f', '#3f73a6', '#6aa9d8', '#a9d8f2', '#f2fbff'])):
        path = os.path.join(ent, f'kfv_bobber_{name}.png')
        recolour(glow.copy(), teal, ramp).save(path)
        ts = path[:-4] + '.texture_set.json'
        with open(ts, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'format_version': '1.16.100', 'minecraft:texture_set': {
                'color': f'kfv_bobber_{name}', 'metalness_emissive_roughness': f'kfv_bobber_{name}_mer', 'heightmap': f'kfv_bobber_{name}_height'}}, f, indent=2)
            f.write('\n')
        pbr.refresh(path)
    Image.new('RGBA', (4, 4), rgb('#3a261c') + (255,)).save(os.path.join(os.path.dirname(ITEMS), 'particle', 'kfv_line_whisker.png'))


def glowing_float():
    """1.5.0: the Glowing Glass Float, the Glass Float's block texture and icon brightened to a starlit teal with a few
    gold specks; its MER map glows (emissive) wherever the glass is."""
    import random
    rnd = random.Random(11)
    for folder in ('blocks', 'items'):
        d = os.path.join(os.path.dirname(ITEMS), folder)
        src = Image.open(os.path.join(d, 'kfv_glass_float.png')).convert('RGBA')
        im = src.copy()
        px = im.load()
        glassy = []
        for y in range(im.height):
            for x in range(im.width):
                r, g, b, a = px[x, y]
                if not a:
                    continue
                if g > r + 10 and g >= b - 30:                # the green glass
                    l = (r + g + b) / 3
                    px[x, y] = (int(min(255, 60 + l * 0.6)), int(min(255, 150 + l * 0.5)), int(min(255, 150 + l * 0.5)), a)
                    glassy.append((x, y))
        for x, y in rnd.sample(glassy, max(1, len(glassy) // 18)):
            px[x, y] = (255, 236, 150, px[x, y][3])
        path = os.path.join(d, 'kfv_glowing_glass_float.png')
        im.save(path)
        ts = path[:-4] + '.texture_set.json'
        with open(ts, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'format_version': '1.16.100', 'minecraft:texture_set': {
                'color': 'kfv_glowing_glass_float', 'metalness_emissive_roughness': 'kfv_glowing_glass_float_mer',
                **({'heightmap': 'kfv_glowing_glass_float_height'} if folder == 'blocks' else {'normal': 'kfv_glowing_glass_float_normal'})}}, f, indent=2)
            f.write('\n')
        mer_src = os.path.join(d, 'kfv_glass_float_mer.png')
        if os.path.exists(mer_src):
            Image.open(mer_src).save(path[:-4] + '_mer.png')
        pbr.refresh(path)
        mer = Image.open(path[:-4] + '_mer.png').convert('RGBA')
        mp = mer.load()
        for x, y in glassy:                                   # the glass glows
            m = mp[x, y]
            mp[x, y] = (m[0], 200, m[2], 255)
        mer.save(path[:-4] + '_mer.png')


if __name__ == '__main__':
    icons = build()
    for name, im in icons.items():
        write(name, im)
    entity_textures()
    glowing_float()
    print('wrote', len(icons), 'icons:', ', '.join(icons), '+ 2 bobber skins and the whisker line')
