"""Repaint the fish-tank creatures whose textures were flat (1-2 texels per face, a single colour each).

usage: python tools/repaint_tank_fish.py

Starts from tools/data/tank_fish_atlas_base.png and tools/data/tank_fish_base.geo.json (the 1.4.0 originals),
so it can be run again. The atlas is doubled to 512x512 (old fish are scaled pixel-for-pixel and look the same;
the geometry keeps texture_width 256), and each repainted creature gets fresh, non-overlapping regions below
the old fish with every face at full size and 2 texels per unit. Colours come from the creature's 16x16 item
icon so the tank matches the inventory. Patterns follow the species: spots, stripes, blotches, shell segments...
Writes models/entity/tank_fish.geo.json, textures/entity/kfv_tank_fish.png and its MER/height maps.
"""
import colorsys, json, math, os, random, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
BASE_ATLAS = os.path.join(ROOT, 'tools', 'data', 'tank_fish_atlas_base.png')
BASE_GEO = os.path.join(ROOT, 'tools', 'data', 'tank_fish_base.geo.json')
S = 2                    # texels per UV unit in the new atlas
START_ROW = 32           # first free row (UV units) below the kept fish

# species -> (kind, pattern)
TARGETS = {
    'sea_bass': ('fish', 'spots'), 'grey_mullet': ('fish', 'stripes'), 'loach': ('fish', 'mottle'),
    'snakehead': ('fish', 'blotch'), 'mudskipper': ('fish', 'dots'), 'flying_fish': ('fish', 'plain'),
    'cave_blindfish': ('fish', 'blind'), 'river_lord_catfish': ('fish', 'specks'),
    'emperor_tuna': ('fish', 'tuna'), 'frostlake_char': ('fish', 'char'), 'lava_dragon_koi': ('fish', 'lava'),
    'lobster': ('crust', 'segments'), 'king_crab': ('crust', 'spiky'), 'cave_crayfish': ('crust', 'segments'),
    'crab': ('crust', 'shell'), 'glow_crab': ('crust', 'glow'),
    'shrimp': ('crust', 'shrimp'), 'purpur_shrimp': ('crust', 'shrimp'),
    'octopus': ('octo', 'octo'), 'moon_jellyfish': ('jelly', 'rings'), 'chorus_jellyfish': ('jelly', 'chorus'),
}
# 1.5.0: creatures with no model of their own yet: a copy of a template's geometry (less the bones listed), then
# painted from their own icon like the rest. The Lava Fish Tank's four, and the oyster for the Fish Tank.
CLONES = {
    'blazefin': ('carp', []), 'magma_koi': ('lava_dragon_koi', []), 'lava_eel': ('eel', []),
    'basalt_crab': ('crab', []),
    'oyster': ('crab', ['legl1', 'legr1', 'legl2', 'legr2', 'legl3', 'legr3']),
    # the new waters' fish (the Meteor Marlin is too big for a tank)
    'mycelium_flounder': ('carp', []), 'spore_seahorse': ('smelt', []), 'cherry_trout': ('rainbow_trout', []),
    'creek_shrimp': ('shrimp', []), 'echo_ray': ('crab', ['legl1', 'legr1', 'legl2', 'legr2', 'legl3', 'legr3']),
    'sculk_lanternfish': ('smelt', []),
    'aurora_icefish': ('smelt', []),
}
TARGETS.update({'blazefin': ('fish', 'lava'), 'magma_koi': ('fish', 'lava'), 'lava_eel': ('fish', 'lava'),
                'basalt_crab': ('crust', 'shell'), 'oyster': ('crust', 'shell'),
                'mycelium_flounder': ('fish', 'mottle'), 'spore_seahorse': ('fish', 'dots'), 'cherry_trout': ('fish', 'spots'),
                'creek_shrimp': ('crust', 'shrimp'), 'echo_ray': ('crust', 'glow'), 'sculk_lanternfish': ('fish', 'dots'),
                'aurora_icefish': ('fish', 'dots')})
EXTRA = {   # hand-picked accents the icons cannot give
    'emperor_tuna': {'accent': (242, 194, 48)}, 'river_lord_catfish': {'accent': (216, 189, 106)},
    'frostlake_char': {'accent': (240, 140, 120)}, 'lava_dragon_koi': {'accent': (255, 190, 60)},
    'glow_crab': {'accent': (190, 255, 150)}, 'chorus_jellyfish': {'accent': (236, 140, 200)},
    'moon_jellyfish': {'accent': (178, 162, 214)},
    # the shrimp icons are pale inside; same hues, wider range
    'shrimp': {'dark': (90, 36, 24), 'dorsal': (216, 96, 62), 'flank': (240, 138, 102), 'belly': (246, 205, 176),
               'light': (255, 240, 222), 'accent': (226, 69, 42)},
    'purpur_shrimp': {'dark': (58, 26, 64), 'dorsal': (138, 74, 142), 'flank': (176, 122, 175), 'belly': (220, 188, 214),
                      'light': (242, 226, 240), 'accent': (194, 90, 192)},
}


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def palette(species):
    """dark, dorsal, flank, belly, light, accent from the item icon."""
    icon = Image.open(os.path.join(RP, 'textures', 'items', f'kfv_{species}.png')).convert('RGBA')
    ip = icon.load(); W, H = icon.size
    solid = lambda x, y: 0 <= x < W and 0 <= y < H and ip[x, y][3] > 0
    # interior pixels only: the dark outline would drag the whole palette towards black
    cols = sorted([ip[x, y][:3] for y in range(H) for x in range(W)
                   if solid(x, y) and all(solid(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))],
                  key=lum) or sorted([c[:3] for c in icon.getdata() if c[3] > 0], key=lum)
    pick = lambda q: cols[min(len(cols) - 1, int(q * (len(cols) - 1)))]
    sat = max(cols, key=lambda c: colorsys.rgb_to_hsv(*(v / 255 for v in c))[1] * (0.3 + lum(c) / 255))
    p = {'dark': pick(0.05), 'dorsal': pick(0.3), 'flank': pick(0.55), 'belly': pick(0.85), 'light': pick(0.97),
         'accent': sat}
    p.update(EXTRA.get(species, {}))
    return p


class Packer:
    """Shelf packer in texel space (512 wide), starting below the kept fish."""
    def __init__(self):
        self.x, self.y, self.row_h = 0, START_ROW * S, 0

    def take(self, w, h):
        w, h = max(1, w), max(1, h)
        if self.x + w > 256 * S:
            self.x, self.y, self.row_h = 0, self.y + self.row_h + 1, 0
        pos = (self.x, self.y)
        self.x += w + 1; self.row_h = max(self.row_h, h)
        if self.y + h > 256 * S:
            raise SystemExit('atlas full')
        return pos


FACE_DIMS = {'north': (0, 1), 'south': (0, 1), 'east': (2, 1), 'west': (2, 1), 'up': (0, 2), 'down': (0, 2)}


def info_front(body_box):
    return body_box[2] + (body_box[3] - body_box[2]) * 0.3


def classify(kind, bone, c, body_box):
    s = c['size']
    small = max(s) <= 0.8
    thin = min(s) <= 0.5
    if kind == 'fish':
        if bone == 'tail' and thin:
            return 'fin'
        if small and c['origin'][0] < body_box[0] + (body_box[1] - body_box[0]) * 0.35 \
                and c['origin'][1] + s[1] / 2 > 0.1:
            return 'eye'
        if thin:
            return 'fin'
        return 'body'
    if kind == 'crust':
        if bone.startswith('leg'):
            return 'leg'
        if small and c['origin'][1] > 1.5 and c['origin'][2] < info_front(body_box) :
            return 'eye'
        if max(s) >= 3.5 and min(s) <= 0.25:
            return 'antenna'
        return 'body'
    if kind == 'octo':
        return 'body' if bone == 'fish' else 'arm'
    if kind == 'jelly':
        return 'bell' if bone == 'bell' else 'tentacle'
    return 'body'


def paint_face(px, x0, y0, w, h, face, role, p, pattern, rnd, info):
    """Paint one face region (w x h texels at x0,y0). Texture v runs top to bottom of the face."""
    dark, dorsal, flank, belly, light, acc = (p[k] for k in ('dark', 'dorsal', 'flank', 'belly', 'light', 'accent'))
    for v in range(h):
        for u in range(w):
            fv = (v + 0.5) / h; fu = (u + 0.5) / w
            if role == 'body':
                if face in ('north', 'south', 'east', 'west'):
                    c = mix(dorsal, flank, min(1, fv / 0.45)) if fv < 0.45 else mix(flank, belly, (fv - 0.45) / 0.55)
                elif face == 'up':
                    c = mix(dorsal, dark, 0.25 if abs(fv - 0.5) < 0.2 else 0)
                else:
                    c = belly
                if (u + v) % 2 == 0 and face in ('north', 'south'):
                    c = mix(c, (0, 0, 0), 0.07)                           # scales
                if face in ('north', 'south') and info.get('kind') == 'fish':
                    if pattern == 'spots' and fv < 0.5 and rnd.random() < 0.10:
                        c = dark
                    elif pattern == 'stripes' and fv < 0.65 and v % 3 == 1:
                        c = mix(c, dark, 0.45)
                    elif pattern == 'mottle' and rnd.random() < 0.28 and fv < 0.8:
                        c = mix(c, dark, 0.55)
                    elif pattern == 'blotch' and ((u // 3 + v // 2) % 3 == 0) and fv < 0.75:
                        c = mix(c, dark, 0.6)
                    elif pattern == 'dots':
                        if rnd.random() < 0.08:
                            c = light
                        elif rnd.random() < 0.10 and fv < 0.6:
                            c = dark
                    elif pattern == 'specks' and rnd.random() < 0.07:
                        c = acc
                    elif pattern == 'tuna' and abs(fv - 0.45) < 0.08:
                        c = mix(c, acc, 0.6)
                    elif pattern == 'char':
                        if fv < 0.55 and (u * 7 + v * 3) % 9 == 0:
                            c = light
                        if abs(fv - 0.62) < 0.08:
                            c = mix(c, acc, 0.6)
                    elif pattern == 'lava':
                        if (u * 5 + v * 3) % 7 == 0 or rnd.random() < 0.12:
                            c = mix(dark, (40, 10, 10), 0.3)
                        elif (u + 2 * v) % 9 == 0:
                            c = acc                                          # glowing cracks
                if info.get('kind') == 'crust':
                    if face == 'up':
                        c = mix(dorsal, light, 0.25) if fv < 0.3 else dorsal
                        if pattern in ('segments',) and v % 3 == 2:
                            c = mix(c, dark, 0.5)                         # shell segments
                        if pattern == 'spiky' and (u + v) % 4 == 0:
                            c = light                                      # spines
                        if pattern == 'glow' and (u * 3 + v) % 5 == 0:
                            c = acc
                        if pattern == 'shell' and (fu < 0.12 or fu > 0.88):
                            c = mix(c, dark, 0.35)
                    elif face == 'down':
                        c = belly
                    else:
                        c = mix(dorsal, dark, 0.3 * fv)
                if info.get('kind') == 'octo':
                    c = mix(dorsal, flank, fv) if face != 'up' else mix(flank, light, 0.2)
                    if rnd.random() < 0.12:
                        c = mix(c, dark, 0.5)
                    if rnd.random() < 0.06:
                        c = light
            elif role in ('fin', 'leg', 'antenna', 'arm', 'tentacle'):
                base = mix(dorsal, flank, 0.4) if role == 'fin' else dorsal
                if role == 'fin':
                    c = base if u % 2 == 0 else mix(base, light, 0.25)    # fin rays
                    if fv > 0.8:
                        c = mix(c, light, 0.35)                            # pale edge
                    if info.get('species') == 'emperor_tuna' and (u + v) % 3 == 0:
                        c = acc
                elif role == 'leg':
                    c = base if (v + u) % 3 else mix(base, dark, 0.4)     # joints
                    if fv > 0.75:
                        c = mix(base, light, 0.3)
                elif role == 'antenna':
                    c = mix(base, light, 0.2) if v % 2 else base
                elif role == 'arm':
                    c = mix(dorsal, flank, fv)
                    if face == 'down' or (face in ('north', 'south', 'east', 'west') and u % 2 == 0 and v % 2 == 1
                                          and fv > 0.3):
                        c = mix(light, flank, 0.3)                         # suckers
                else:
                    c = light if v % 3 else mix(flank, light, 0.5)        # jellyfish tentacles
            elif role == 'bell':
                if face == 'up':
                    d = math.hypot(fu - 0.5, fv - 0.5)
                    c = mix(light, flank, min(1, d * 1.6))
                    if pattern == 'rings' and abs(d - 0.22) < 0.07 and (u + v) % 2 == 0:
                        c = acc
                    if pattern == 'chorus' and (abs(fu - 0.5) < 0.08 or abs(fv - 0.5) < 0.08) and d < 0.3:
                        c = acc
                elif face == 'down':
                    c = mix(flank, dark, 0.3)
                else:
                    c = mix(light, flank, fv)
                    if fv > 0.75:
                        c = mix(c, acc, 0.4)                               # rim
            elif role == 'eye':
                c = (14, 12, 16)
                if (u == 0 and v == 0) and w > 1:
                    c = (250, 250, 250)
                if info.get('species') == 'cave_blindfish':
                    c = mix(flank, light, 0.4)
                if info.get('species') in ('lava_dragon_koi',):
                    c = (255, 200, 60) if (u + v) % 2 else (40, 10, 0)
            else:
                c = flank
            px[x0 + u, y0 + v] = c + (255,)


DENSITY = {'shrimp': 2, 'purpur_shrimp': 2}     # extra texel density for small, detailed creatures


def shrimp_part(bone, c):
    s = c['size']
    if bone.startswith('leg'):
        return 'leg'
    if max(s) >= 2.5 and min(s) <= 0.2:
        return 'antenna'
    if bone == 'tail' and s[1] <= 0.25:
        return 'fan'
    if max(s) <= 0.45:
        return 'eye'
    if s[0] <= 0.35:
        return 'rostrum'
    if s[2] >= 2:
        return 'carapace'
    return 'seg'


def paint_shrimp(px, x0, y0, w, h, face, part, p, rnd):
    """Shrimp: see-through looking shell with a dark back line, segment seams, a banded fan tail."""
    dark, dorsal, flank, belly, light, acc = (p[k] for k in ('dark', 'dorsal', 'flank', 'belly', 'light', 'accent'))
    side = face in ('north', 'south', 'east', 'west')
    for v in range(h):
        for u in range(w):
            fv = (v + 0.5) / h; fu = (u + 0.5) / w
            if part in ('carapace', 'seg'):
                if face == 'up':
                    c = mix(flank, light, 0.25)
                    if abs(fu - 0.5) < 0.18:
                        c = mix(dorsal, dark, 0.6)                         # line down the back
                    elif abs(fu - 0.5) < 0.3:
                        c = mix(dorsal, acc, 0.4)
                    if part == 'seg' and fv < 0.2:
                        c = mix(c, dark, 0.7)                              # seam to the segment in front
                elif face == 'down':
                    c = mix(belly, light, 0.3)
                    if part == 'seg' and u % 2 == 0 and fv > 0.5:
                        c = mix(belly, acc, 0.35)                          # swimmerets
                else:
                    c = mix(mix(dorsal, acc, 0.45), flank, fv / 0.4) if fv < 0.4 else mix(flank, belly, (fv - 0.4) / 0.6)
                    if abs(fv - 0.55) < 0.09:
                        c = mix(c, light, 0.6)                             # glassy band
                    if part == 'carapace' and face in ('north', 'south') and abs(fu - 0.6) < 0.06 and 0.2 < fv < 0.75:
                        c = mix(c, dark, 0.55)                             # cervical groove
                    if part == 'seg':
                        if face in ('east', 'west') and u == 0 or face in ('north', 'south') and fu < 0.12:
                            c = mix(c, dark, 0.6)
                        if fv > 0.85 and u % 2:
                            c = mix(c, dark, 0.3)                          # scalloped plate edge
                    if fv < 0.15:
                        c = mix(c, dark, 0.4)
                if rnd.random() < 0.1:
                    c = mix(acc, dark, 0.35)                               # pigment specks
            elif part == 'fan':
                c = mix(flank, acc, 0.5 + 0.5 * fv)
                if u % 2:
                    c = mix(c, light, 0.25)                                # rays
                if abs(fu - 0.5) < 0.12:
                    c = mix(dorsal, light, 0.2)                            # telson
                if fv > 0.78:
                    c = mix(acc, dark, 0.65)                               # dark tip band
                if not side and fv < 0.15:
                    c = mix(c, dark, 0.3)
            elif part == 'rostrum':
                c = mix(dorsal, flank, 0.3)
                if face == 'up' and v % 2 == 0:
                    c = mix(c, light, 0.5)                                 # teeth
            elif part == 'leg':
                c = mix(flank, light, 0.45)
                if v % 3 == 2 or (face in ('up', 'down') and u % 3 == 2):
                    c = mix(acc, flank, 0.3)                               # joint bands
            elif part == 'antenna':
                c = mix(acc, flank, 0.25) if (u + v) // 2 % 2 else mix(flank, light, 0.3)
            else:                                                          # eye on a stalk
                c = (14, 12, 16)
                if u == 0 and v == 0:
                    c = (235, 235, 240)
            px[x0 + u, y0 + v] = c + (255,)


def paint_eye_on_head(px, regions, p, species):
    """Fish without eye cubes: paint an eye near the front-top of the head cube's two side faces."""
    if species == 'cave_blindfish':
        return
    for face, (x0, y0, w, h) in regions.items():
        if face not in ('north', 'south') or w < 3 or h < 3:
            continue
        ex = x0 + w - 3 if face == 'north' else x0 + 1      # north: texture right = front (-x); south: left
        ey = y0 + max(0, h // 3 - 1)
        for (du, dv), col in (((0, 0), (250, 250, 250)), ((1, 0), (14, 12, 16)), ((0, 1), (14, 12, 16)),
                              ((1, 1), (14, 12, 16))):
            if ex + du < x0 + w and ey + dv < y0 + h:
                px[ex + du, ey + dv] = col + (255,)


def main():
    geo = json.load(open(BASE_GEO, encoding='utf-8'))
    byid = {g['description']['identifier'].split('tank_fish.')[-1]: g for g in geo['minecraft:geometry']}
    for new, (tpl, drop) in CLONES.items():
        g = json.loads(json.dumps(byid[tpl]))
        g['description']['identifier'] = f'geometry.kaleidoscope_fishing.tank_fish.{new}'
        g['bones'] = [b for b in g['bones'] if b['name'] not in drop]
        geo['minecraft:geometry'].append(g)
    base = Image.open(BASE_ATLAS).convert('RGBA')
    atlas = base.resize((base.width * S, base.height * S), Image.NEAREST)
    # clear everything below the kept fish (the old flat strips of the repainted species)
    for y in range(START_ROW * S, atlas.height):
        for x in range(atlas.width):
            atlas.putpixel((x, y), (0, 0, 0, 0))
    px = atlas.load()
    packer = Packer()
    done = []
    for g in geo['minecraft:geometry']:
        species = g['description']['identifier'].split('tank_fish.')[-1]
        if species not in TARGETS:
            continue
        kind, pattern = TARGETS[species]
        p = palette(species)
        rnd = random.Random(species)
        xs = [c['origin'][0] for b in g['bones'] for c in b.get('cubes', [])] + \
             [c['origin'][0] + c['size'][0] for b in g['bones'] for c in b.get('cubes', [])]
        zs = [c['origin'][2] for b in g['bones'] for c in b.get('cubes', []) if not b['name'].startswith('leg')] +              [c['origin'][2] + c['size'][2] for b in g['bones'] for c in b.get('cubes', []) if not b['name'].startswith('leg')]
        body_box = (min(xs), max(xs), min(zs), max(zs))
        head = None
        if kind == 'fish':
            bodies = [(b['name'], c) for b in g['bones'] for c in b.get('cubes', [])
                      if classify(kind, b['name'], c, body_box) == 'body']
            head = min(bodies, key=lambda bc: bc[1]['origin'][0])[1] if bodies else None
        has_eye_cubes = any(classify(kind, b['name'], c, body_box) == 'eye' for b in g['bones'] for c in b.get('cubes', []))
        for b in g['bones']:
            for c in b.get('cubes', []):
                role = classify(kind, b['name'], c, body_box)
                s = c['size']
                newuv, regions = {}, {}
                for face in ('north', 'south', 'east', 'west', 'up', 'down'):
                    if isinstance(c.get('uv'), dict) and face not in c['uv']:
                        continue
                    a, bdim = FACE_DIMS[face]
                    fw, fh = abs(s[a]), abs(s[bdim])
                    k = S * DENSITY.get(species, 1)
                    tw, th = max(1, math.ceil(fw * k - 1e-6)), max(1, math.ceil(fh * k - 1e-6))
                    x0, y0 = packer.take(tw, th)
                    if pattern == 'shrimp':
                        paint_shrimp(px, x0, y0, tw, th, face, shrimp_part(b['name'], c), p, rnd)
                    else:
                        paint_face(px, x0, y0, tw, th, face, role, p, pattern, rnd, {'kind': kind, 'species': species})
                    regions[face] = (x0, y0, tw, th)
                    newuv[face] = {'uv': [x0 / S, y0 / S], 'uv_size': [round(tw / S, 4), round(th / S, 4)]}
                if c is head and not has_eye_cubes:
                    paint_eye_on_head(px, regions, p, species)
                c['uv'] = newuv
        done.append(species)
    out_geo = os.path.join(RP, 'models', 'entity', 'tank_fish.geo.json')
    with open(out_geo, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(geo, f, indent=1)
    tex = os.path.join(RP, 'textures', 'entity', 'kfv_tank_fish.png')
    atlas.save(tex)
    pbr.refresh(tex)
    print('repainted', len(done), 'creatures; atlas', atlas.size, 'used down to row', (packer.y + packer.row_h) // S)


if __name__ == '__main__':
    main()
