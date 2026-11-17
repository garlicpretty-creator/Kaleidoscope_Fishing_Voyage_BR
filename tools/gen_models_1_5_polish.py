"""1.5.0 model polish: replaces the first-pass creature models that tools/gen_1_5.py (and the scripts it calls) made
by copying a similar creature. Run it AFTER gen_1_5.py / gen_tank_1_5.py, which would otherwise put the copies back:

  python tools/gen_models_1_5_polish.py            all three parts below
  python tools/gen_models_1_5_polish.py tank       only the fish-tank creatures
  python tools/gen_models_1_5_polish.py board      only the Fish Cleaning Board models
  python tools/gen_models_1_5_polish.py shore      only the Oyster Bed / Laver Rock growth stages
  (then python tools/build.py build)

tank   Twelve fish-tank creatures get their own geometry instead of a recoloured copy (CLONES in
       tools/repaint_tank_fish.py): the Lava Fish Tank's Blazefin, Magma Koi, Lava Eel and Basalt Crab; the oyster
       (a half-open oyster with a pearl, still on the bottom); the new waters' Mycelium Flounder, Spore Seahorse,
       Cherry Trout, Creek Shrimp, Echo Ray, Sculk Lanternfish; and the sky's Aurora Icefish. The geometry is written
       into tools/data/tank_fish_base.geo.json (each cube tagged with the part it is, `kfv_part`), then
       tools/repaint_tank_fish.py paints it from the item icons as it does the rest. Bone names follow
       animations/tank_fish.animation.json for each creature's kind (scripts/data/tank.js TANK_KIND): spin > fish >
       tail for the swimmers, seg1..seg5 for the eel, legl1..legr3 for the walkers; each stays inside the bounds of
       the creature its placement rows (FIT) were copied from, so the tank fit still holds.
board  runs tools/gen_board_1_5.py (the 1.5.0 catches on the board), where the Meteor Marlin is now drawn side on
       (bill, sail, crescent tail), the Sculk Lanternfish is used as the side view its icon already is, and the
       flatfish (flounder, ray) get a gutting cut instead of being tinted red all over.
shore  Oyster Bed and Laver Rock: the two young growth stages get models of their own (a few spat / sprouts on the
       bare rock, then a half-grown cluster) instead of the grown model scaled down; same rock base and textures.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
BP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [BP]')
NS = 'kaleidoscope_fishing'
BASE_GEO = os.path.join(HERE, 'data', 'tank_fish_base.geo.json')


# ------------------------------------------------------------------ tank creatures
def C(o, s, part, r=None, p=None):
    c = {'origin': [round(v, 3) for v in o], 'size': [round(v, 3) for v in s], 'kfv_part': part}
    if r:
        c['rotation'] = r
        c['pivot'] = [round(v, 3) for v in p]
    return c


def pair(o, s, part, r=None, p=None):
    """The cube and its mirror across z = 0 (rotations about x and y flip)."""
    a = C(o, s, part, r, p)
    o2 = [o[0], o[1], -(o[2] + s[2])]
    r2 = [-r[0], -r[1], r[2]] if r else None
    p2 = [p[0], p[1], -p[2]] if p else None
    return [a, C(o2, s, part, r2, p2)]


def bone(name, parent, pivot, cubes):
    b = {'name': name, 'pivot': pivot}
    if parent:
        b['parent'] = parent
    if cubes:
        b['cubes'] = cubes
    return b


def swimmer(fish, tail_pivot, tail):
    return [bone('spin', None, [0, 0, 0], []), bone('fish', 'spin', [0, 0, 0], fish), bone('tail', 'fish', tail_pivot, tail)]


def forked(x, y, w, h, part='fin', ang=25, t=0.3):
    """Two tail lobes from (x, y), raked back."""
    return [C([x, y + 0.2, -t / 2], [w, h, t], part, [0, 0, -ang], [x, y + 0.4, 0]),
            C([x, y - 0.2 - h, -t / 2], [w, h, t], part, [0, 0, ang], [x, y - 0.4, 0])]


def blazefin():
    f = [C([-5.8, -1.3, -1.1], [2.6, 2.6, 2.2], 'head'), C([-6.4, -1.0, -0.8], [0.6, 1.5, 1.6], 'lip'),
         C([-3.2, -1.9, -1.4], [4.4, 3.8, 2.8], 'body'), C([1.2, -1.4, -1.1], [2.0, 2.8, 2.2], 'body')]
    f += pair([-5.0, 0.2, -1.2], [0.6, 0.6, 0.15], 'eye')
    for x, h in ((-2.9, 1.3), (-2.0, 2.3), (-1.1, 2.9), (-0.2, 2.2), (0.7, 1.6), (1.6, 1.0)):   # a crown of flames
        f.append(C([x, 1.8, -0.15], [0.8, h, 0.3], 'flame'))
    f += [C([-1.0, -3.0, -0.15], [1.0, 1.2, 0.3], 'flame'), C([0.6, -2.7, -0.15], [1.2, 1.0, 0.3], 'flame')]
    f += pair([-3.2, -1.4, -2.2], [1.8, 1.0, 0.2], 'flame', [0, 0, 20], [-3.2, -1.0, -2.1])
    t = [C([3.2, -0.9, -0.7], [1.2, 1.8, 1.4], 'body')] + forked(4.2, 0, 2.2, 2.7, 'flame', 22)
    return swimmer(f, [3.2, 0, 0], t)


def magma_koi():
    f = [C([-4.2, -2.0, -1.5], [7.4, 4.2, 3.0], 'body'), C([-6.4, -1.5, -1.2], [2.2, 3.0, 2.4], 'head'),
         C([-7.0, -1.0, -0.7], [0.6, 1.2, 1.4], 'lip')]
    f += pair([-7.3, -1.0, -0.8], [1.0, 0.2, 0.2], 'barbel', [0, 0, 20], [-6.9, -0.9, -0.7])
    f += pair([-5.8, 0.4, -1.3], [0.6, 0.6, 0.15], 'eye')
    f += [C([-3.6, 2.2, -1.1], [1.8, 0.5, 2.2], 'crust'), C([-1.5, 2.2, -1.25], [2.1, 0.7, 2.5], 'crust'),
          C([0.8, 2.2, -1.0], [1.7, 0.45, 2.0], 'crust'), C([-2.2, 2.7, -0.15], [4.2, 1.3, 0.3], 'fin')]
    f += [C([-2.8, -0.6, -1.7], [2.2, 1.6, 0.2], 'crust'), C([0.6, 0.2, 1.5], [2.0, 1.2, 0.2], 'crust'),
          C([-0.6, -1.4, 1.5], [1.4, 0.9, 0.2], 'crust')]
    f += pair([-3.8, -1.9, -3.1], [1.9, 0.2, 1.6], 'fin', [24, 0, 0], [-3.8, -1.8, -1.5])     # broad drooping pectorals
    f += pair([-0.2, -2.4, -1.8], [1.4, 0.2, 1.0], 'fin', [30, 0, 0], [-0.2, -2.3, -1.2])
    t = [C([3.2, -1.0, -0.8], [1.4, 2.0, 1.6], 'body')] + forked(4.4, 0, 3.0, 2.8, 'fin', 25)
    return swimmer(f, [3.2, 0, 0], t)


def lava_eel():
    s1 = [C([-6.6, -0.8, -0.8], [2.4, 1.6, 1.6], 'head'), C([-7.2, -0.75, -0.55], [0.6, 1.0, 1.1], 'lip'),
          C([-5.4, 0.8, -0.15], [1.1, 0.5, 0.3], 'flame')]
    s1 += pair([-6.3, 0.15, -0.85], [0.45, 0.45, 0.1], 'eye')
    s1 += pair([-4.6, -0.6, -1.15], [0.6, 0.7, 0.15], 'fin')
    bones = [bone('spin', None, [0, 0, 0], []), bone('fish', 'spin', [0, 0, 0], []), bone('seg1', 'fish', [0, 0, 0], s1)]
    spec = [('seg2', 'seg1', -4.2, 0.85, 0.75, 0.0), ('seg3', 'seg2', -1.4, 0.8, 0.85, 0.5),
            ('seg4', 'seg3', 1.4, 0.65, 0.8, 0.5), ('seg5', 'seg4', 4.2, 0.45, 0.0, 0.0)]
    for name, parent, x, r, up, down in spec:
        cubes = [C([x, -r, -r], [2.8 if name != 'seg5' else 2.0, 2 * r, 2 * r], 'body')]
        if up:
            cubes.append(C([x, r, -0.15], [2.8, up, 0.3], 'flame'))
        if down:
            cubes.append(C([x, -r - down, -0.12], [2.8, down, 0.24], 'fin'))
        if name == 'seg5':
            cubes += [C([6.2, -0.25, -0.25], [0.8, 0.5, 0.5], 'body'), C([4.6, -1.1, -0.12], [2.6, 2.2, 0.24], 'flame')]
        bones.append(bone(name, parent, [x, 0, 0], cubes))
    return bones


def leg_bones(x_in, zs, upper, lower, y=1.5):
    out = []
    for i, z in enumerate(zs, 1):
        for side, sgn in (('l', 1), ('r', -1)):
            ux = x_in if sgn > 0 else -x_in - upper[0]
            lx = x_in + upper[0] - lower[0] if sgn > 0 else -x_in - upper[0]
            cubes = [C([ux, y - 0.3, z - upper[2] / 2], upper, 'leg'),
                     C([lx, 0.0, z - lower[2] / 2], [lower[0], y - 0.3, lower[2]], 'leg')]
            out.append(bone(f'leg{side}{i}', 'fish', [sgn * x_in, y, z], cubes))
    return out


def basalt_crab():
    f = [C([-2.6, 0.9, -2.0], [5.2, 1.6, 3.8], 'shell'), C([-2.1, 0.6, -1.6], [4.2, 0.3, 3.0], 'leg')]
    for o, s in (([-2.2, 2.5, -1.7], [1.2, 0.7, 1.2]), ([-0.6, 2.5, -1.9], [1.2, 1.0, 1.2]), ([1.0, 2.5, -1.6], [1.2, 0.6, 1.2]),
                 ([-1.5, 2.5, 0.0], [1.2, 0.5, 1.2]), ([0.2, 2.5, 0.2], [1.2, 0.85, 1.2]), ([1.5, 2.5, 0.6], [0.8, 0.4, 0.8])):
        f.append(C(o, s, 'column'))
    f += [C([-1.1, 2.3, -2.35], [0.4, 0.75, 0.4], 'eye'), C([0.7, 2.3, -2.35], [0.4, 0.75, 0.4], 'eye')]
    for sgn in (1, -1):
        ax = 2.0 if sgn > 0 else -3.2
        cx = 2.1 if sgn > 0 else -4.1
        f += [C([ax, 1.1, -2.9], [1.2, 0.8, 1.0], 'claw'), C([cx, 0.8, -4.3], [2.0, 1.5, 1.7], 'claw'),
              C([cx + (0.2 if sgn > 0 else 1.2), 1.0, -4.8], [0.6, 0.9, 0.5], 'clawtip')]
    return [bone('spin', None, [0, 0, 0], []), bone('fish', 'spin', [0, 0, 0], f)] + \
        leg_bones(2.6, (-1.3, 0.1, 1.4), [1.4, 0.5, 0.5], [0.5, 0, 0.5])


def oyster():
    lo = [C([-2.8, 0.0, -2.2], [5.6, 0.9, 3.8], 'valve_low'), C([-2.2, 0.0, -3.0], [4.4, 0.8, 0.8], 'valve_low'),
          C([-1.8, 0.0, 1.6], [3.6, 0.85, 1.2], 'valve_low'), C([-1.0, 0.0, 2.8], [2.0, 0.75, 0.7], 'valve_low')]
    rim = [C([-3.0, 0.6, -2.4], [0.4, 0.55, 3.8], 'shell_rim'), C([2.6, 0.6, -2.4], [0.4, 0.55, 3.8], 'shell_rim'),
           C([-2.2, 0.6, -3.2], [4.4, 0.5, 0.4], 'shell_rim'), C([-1.6, 0.6, 1.4], [0.4, 0.5, 1.6], 'shell_rim'),
           C([1.2, 0.6, 1.4], [0.4, 0.5, 1.6], 'shell_rim')]
    meat = [C([-2.0, 0.9, -2.5], [4.0, 0.4, 3.9], 'meat'), C([-0.5, 1.3, -1.3], [1.0, 1.0, 1.0], 'pearl')]
    up = []
    piv = [0, 0.9, 3.4]
    a = [-58, 0, 0]                                   # the top shell stands open about 60 degrees
    for o, s in (([-2.5, 0.9, -1.8], [5.0, 0.5, 3.8]), ([-1.9, 0.9, -2.5], [3.8, 0.45, 0.7]),
                 ([-1.6, 0.9, 2.0], [3.2, 0.55, 0.9]), ([-0.9, 0.9, 2.9], [1.8, 0.6, 0.5])):
        up.append(C(o, s, 'valve_up', a, piv))
    up += [C([-1.9, 1.4, -1.4], [1.5, 0.3, 1.6], 'shell_rough', a, piv),
           C([0.4, 1.4, -0.8], [1.4, 0.3, 1.8], 'shell_rough', a, piv),
           C([-0.9, 1.45, 1.0], [1.7, 0.3, 1.1], 'shell_rough', a, piv)]
    lo += [C([-2.4, 0.2, -2.6], [1.4, 0.3, 1.2], 'shell_rough'), C([1.2, 0.15, 0.2], [1.6, 0.3, 1.6], 'shell_rough')]
    return [bone('spin', None, [0, 0, 0], []), bone('fish', 'spin', [0, 0, 0], lo + rim + meat + up)]


def mycelium_flounder():
    f = [C([-4.0, -0.5, -2.4], [7.0, 1.0, 4.8], 'flat'), C([-3.2, -0.4, -3.0], [5.6, 0.8, 0.6], 'flat'),
         C([-3.2, -0.4, 2.4], [5.6, 0.8, 0.6], 'flat'), C([-4.8, -0.4, -1.6], [0.8, 0.8, 3.0], 'flat'),
         C([3.0, -0.4, -1.6], [0.8, 0.8, 3.2], 'flat'),
         C([-2.6, -0.1, -3.8], [5.6, 0.2, 0.8], 'fringe'), C([-2.6, -0.1, 3.0], [5.6, 0.2, 0.8], 'fringe'),
         C([-4.3, 0.5, -1.2], [1.8, 0.3, 2.0], 'flathead'),
         C([-4.1, 0.8, -1.0], [0.6, 0.45, 0.6], 'eye'), C([-3.6, 0.8, 0.25], [0.6, 0.45, 0.6], 'eye')]
    for o in ([-1.0, 0.5, -1.2], [0.8, 0.5, 0.6], [-2.2, 0.5, 1.0], [1.8, 0.5, -1.4]):   # little mushroom bumps
        f.append(C(o, [0.6, 0.3, 0.6], 'spore'))
    t = [C([3.8, -0.3, -0.8], [0.8, 0.6, 1.6], 'flat'), C([4.6, -0.1, -1.9], [1.8, 0.2, 3.8], 'fin')]
    return swimmer(f, [3.8, 0, 0], t)


def spore_seahorse():
    f = [C([-1.0, 2.0, -0.6], [1.6, 1.2, 1.2], 'head'), C([-2.5, 2.2, -0.35], [1.5, 0.6, 0.7], 'head'),
         C([-2.8, 2.15, -0.4], [0.3, 0.75, 0.8], 'lip'), C([-0.4, 3.2, -0.4], [0.9, 0.6, 0.8], 'crest'),
         C([-0.15, 3.8, -0.25], [0.5, 0.45, 0.5], 'spore'),
         C([-0.6, 1.0, -0.55], [1.4, 1.0, 1.1], 'body'), C([-0.9, -0.7, -0.7], [1.9, 1.7, 1.4], 'body'),
         C([-0.5, -1.7, -0.55], [1.4, 1.0, 1.1], 'body'), C([-0.1, -2.5, -0.42], [1.0, 0.8, 0.84], 'body'),
         C([-0.7, -3.1, -0.36], [1.1, 0.6, 0.72], 'body'), C([-1.3, -2.9, -0.32], [0.6, 0.8, 0.64], 'body'),
         C([-1.2, -2.3, -0.3], [0.5, 0.45, 0.6], 'body')]
    f += pair([-0.65, 2.5, -0.7], [0.45, 0.45, 0.12], 'eye')
    for o in ([0.8, 1.3, -0.2], [0.95, 0.2, -0.2], [0.85, -1.0, -0.2], [0.4, -2.0, -0.18], [0.5, 2.3, -0.2]):
        f.append(C(o, [0.35, 0.35, 0.4], 'spore'))
    f += pair([-0.9, 1.4, -0.65], [0.7, 0.5, 0.1], 'fin')
    t = [C([1.0, -0.8, -0.1], [0.9, 1.7, 0.2], 'fin')]            # the dorsal fin is the bone that flutters
    for c in f + t:                                               # centred on the swim line like the smelt it replaces
        c['origin'][1] = round(c['origin'][1] - 0.5, 3)
        if 'pivot' in c:
            c['pivot'][1] = round(c['pivot'][1] - 0.5, 3)
    return swimmer(f, [1.0, -0.7, 0], t)


def cherry_trout():
    f = [C([-6.0, -1.3, -1.0], [2.4, 2.5, 2.0], 'head'), C([-6.5, -1.0, -0.7], [0.5, 1.6, 1.4], 'lip'),
         C([-3.6, -1.7, -1.25], [4.6, 3.4, 2.5], 'body'), C([1.0, -1.3, -1.0], [2.0, 2.6, 2.0], 'body'),
         C([-1.8, 1.7, -0.15], [1.8, 1.5, 0.3], 'fin', [0, 0, -12], [-1.8, 1.7, 0]),
         C([1.6, 1.3, -0.12], [0.8, 0.6, 0.24], 'fin'),
         C([-0.6, -2.4, -0.15], [1.2, 0.8, 0.3], 'fin'), C([1.3, -2.1, -0.15], [1.0, 0.8, 0.3], 'fin')]
    f += pair([-5.2, 0.2, -1.1], [0.55, 0.55, 0.12], 'eye')
    f += pair([-3.9, -1.5, -1.6], [1.4, 0.8, 0.2], 'fin', [0, 0, 18], [-3.9, -1.2, -1.5])
    t = [C([3.0, -0.9, -0.6], [1.2, 1.8, 1.2], 'body'), C([4.2, -0.5, -0.12], [0.6, 1.0, 0.24], 'fin')] + forked(4.1, 0, 2.1, 2.6, 'fin', 14)
    return swimmer(f, [3.0, 0, 0], t)


def creek_shrimp():
    f = [C([-0.65, 1.0, -2.4], [1.3, 1.2, 2.4], 'carapace'),
         C([-0.1, 1.95, -4.0], [0.2, 0.25, 1.7], 'rostrum', [-14, 0, 0], [0, 2.0, -2.4]),
         C([-0.6, 1.0, 0.0], [1.2, 1.2, 0.9], 'seg')]
    f += pair([-0.8, 2.0, -2.65], [0.45, 0.45, 0.45], 'eye')
    # 1.4.0 playtest: long feelers poked out through the tank glass, so they stay short and swept up (as the shrimp's)
    f += pair([-0.5, 1.7, -4.8], [0.12, 0.12, 2.4], 'antenna', [-30, -14, 0], [-0.45, 1.75, -2.4])
    f += pair([-0.35, 1.55, -3.5], [0.1, 0.1, 1.1], 'antenna', [-8, -6, 0], [-0.3, 1.6, -2.4])
    t = [C([-0.55, 0.9, 0.9], [1.1, 1.1, 0.9], 'seg', [20, 0, 0], [0, 1.45, 0.9]),
         C([-0.5, 0.62, 1.7], [1.0, 1.0, 0.8], 'seg', [40, 0, 0], [0, 1.2, 1.7]),
         C([-0.42, 0.36, 2.35], [0.84, 0.85, 0.75], 'seg', [60, 0, 0], [0, 0.9, 2.35]),
         C([-0.95, 0.12, 2.9], [1.9, 0.2, 1.3], 'fan', [78, 0, 0], [0, 0.4, 2.9])]
    legs = []
    for i, z in enumerate((-2.0, -1.2, -0.4), 1):
        for side, sgn in (('l', 1), ('r', -1)):
            up = C([0.6 if sgn > 0 else -1.6, 1.05, z], [1.0, 0.15, 0.16], 'leg')
            dn = C([1.45 if sgn > 0 else -1.6, 0.0, z + 0.01], [0.15, 1.2, 0.15], 'leg')
            legs.append(bone(f'leg{side}{i}', 'fish', [sgn * 0.6, 1.2, z], [up, dn]))
    return [bone('spin', None, [0, 0, 0], []), bone('fish', 'spin', [0, 0, 0], f), bone('tail', 'fish', [0, 1.4, 0.9], t)] + legs


def echo_ray():
    f = []
    cx, half = -1.4, 4.4
    z = -half
    while z < half - 1e-6:
        zc = z + 0.4
        k = 1 - abs(zc) / (half + 0.4)
        L = 0.5 + 3.2 * k
        t = 0.3 + 0.7 * k
        f.append(C([cx - L * 1.05, 0.0, z], [L * 2.05, t, 0.8], 'disc'))
        z += 0.8
    f += [C([-4.0, 0.5, -1.1], [4.6, 0.75, 2.2], 'raybody'),
          C([-5.4, 0.15, -1.2], [0.9, 0.45, 0.5], 'raybody'), C([-5.4, 0.15, 0.7], [0.9, 0.45, 0.5], 'raybody'),
          C([-3.5, 1.15, -0.95], [0.5, 0.35, 0.5], 'eye'), C([-3.5, 1.15, 0.45], [0.5, 0.35, 0.5], 'eye'),
          C([-2.4, 0.78, -3.0], [0.8, 0.12, 0.8], 'glow'), C([-2.4, 0.78, 2.2], [0.8, 0.12, 0.8], 'glow'),
          C([-0.6, 1.2, -0.3], [0.6, 0.12, 0.6], 'glow'),
          C([1.9, 0.25, -0.35], [1.6, 0.5, 0.7], 'raybody'), C([3.5, 0.3, -0.17], [1.3, 0.3, 0.34], 'raybody'),
          C([4.8, 0.32, -0.1], [0.5, 0.2, 0.2], 'glow'), C([2.4, 0.75, -0.08], [0.8, 0.4, 0.16], 'fin')]
    return [bone('spin', None, [0, 0, 0], []), bone('fish', 'spin', [0, 0, 0], f)]


def sculk_lanternfish():
    f = [C([-5.0, -1.4, -1.1], [2.6, 2.8, 2.2], 'head'), C([-5.4, -1.3, -0.9], [0.4, 1.3, 1.8], 'lip'),
         C([-2.4, -1.5, -1.0], [3.6, 2.9, 2.0], 'body'), C([1.2, -0.9, -0.7], [1.6, 1.9, 1.4], 'body'),
         C([-1.6, 1.4, -0.12], [1.4, 1.0, 0.24], 'fin'), C([1.4, 1.0, -0.1], [0.5, 0.4, 0.2], 'fin'),
         C([0.0, -2.1, -0.12], [1.6, 0.6, 0.24], 'fin'), C([-4.1, 1.4, -0.2], [0.4, 0.3, 0.4], 'glow')]
    f += pair([-4.5, -0.1, -1.25], [1.15, 1.15, 0.2], 'bigeye')
    f += pair([-2.7, -0.7, -1.2], [1.1, 0.6, 0.15], 'fin', [0, 0, 15], [-2.7, -0.4, -1.1])
    t = [C([2.8, -0.5, -0.4], [0.8, 1.0, 0.8], 'body')] + forked(3.4, 0, 1.6, 2.0, 'fin', 25, 0.24)
    return swimmer(f, [2.8, 0, 0], t)


def aurora_icefish():
    f = [C([-5.0, -0.55, -0.5], [1.8, 1.1, 1.0], 'head'), C([-5.8, -0.4, -0.35], [0.8, 0.65, 0.7], 'lip'),
         C([-3.2, -0.7, -0.6], [4.4, 1.4, 1.2], 'body'), C([1.2, -0.5, -0.45], [1.8, 1.0, 0.9], 'body'),
         C([0.6, 0.7, -0.1], [0.9, 0.6, 0.2], 'fin'), C([2.0, 0.5, -0.08], [0.4, 0.3, 0.16], 'fin'),
         C([0.0, -1.15, -0.1], [1.6, 0.5, 0.2], 'fin')]
    f += pair([-4.6, 0.0, -0.55], [0.4, 0.4, 0.1], 'eye')
    f += pair([-3.4, -0.45, -1.2], [0.9, 0.1, 0.6], 'fin')
    t = [C([3.0, -0.3, -0.3], [0.8, 0.6, 0.6], 'body')] + forked(3.6, 0, 1.4, 1.4, 'fin', 28, 0.2)
    return swimmer(f, [3.0, 0, 0], t)


TANK = {'blazefin': blazefin, 'magma_koi': magma_koi, 'lava_eel': lava_eel, 'basalt_crab': basalt_crab,
        'oyster': oyster, 'mycelium_flounder': mycelium_flounder, 'spore_seahorse': spore_seahorse,
        'cherry_trout': cherry_trout, 'creek_shrimp': creek_shrimp, 'echo_ray': echo_ray,
        'sculk_lanternfish': sculk_lanternfish, 'aurora_icefish': aurora_icefish}


def tank():
    geo = json.load(open(BASE_GEO, encoding='utf-8'))
    gs = geo['minecraft:geometry']
    for name, fn in TANK.items():
        ident = f'geometry.{NS}.tank_fish.{name}'
        g = {'description': {'identifier': ident, 'texture_width': 256, 'texture_height': 256,
                             'visible_bounds_width': 2, 'visible_bounds_height': 2, 'visible_bounds_offset': [0, 0.5, 0]},
             'bones': fn()}
        old = [i for i, x in enumerate(gs) if x['description']['identifier'] == ident]
        if old:
            gs[old[0]] = g
        else:
            gs.append(g)
    with open(BASE_GEO, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(geo, f, indent=1)
    subprocess.run([sys.executable, os.path.join(HERE, 'repaint_tank_fish.py')], check=True)


# ------------------------------------------------------------------ cleaning board
def board():
    subprocess.run([sys.executable, os.path.join(HERE, 'gen_board_1_5.py')], check=True)


# ------------------------------------------------------------------ oyster bed / laver rock
def _cube(o, s, uv):
    """A cube whose faces read the atlas at the given corners, each face as large as the cube side it covers."""
    dims = {'north': (0, 1), 'south': (0, 1), 'east': (2, 1), 'west': (2, 1), 'up': (0, 2), 'down': (0, 2)}
    return {'origin': [round(v, 3) for v in o], 'size': [round(v, 3) for v in s],
            'uv': {f: {'uv': list(uv[f]), 'uv_size': [s[a], s[b]]} for f, (a, b) in dims.items() if f in uv}}


def _like(cube, o, s):
    """The same faces as a cube of the grown model, on a smaller cube."""
    return _cube(o, s, {f: v['uv'] for f, v in cube['uv'].items()})


def _young_oyster(grown):
    c = grown
    rock = c[0]                                                   # the bare rock slab stays as it is
    spat = c[12]                                                  # a one-unit oyster
    small = c[10]                                                 # a 2 x 1.5 x 3 oyster
    stage0 = [rock] + [_like(spat, o, s) for o, s in (
        ([-3.5, 1.5, -3.0], [0.75, 0.5, 0.75]), ([1.5, 1.5, -2.0], [1.0, 0.5, 1.0]), ([-1.0, 1.5, 2.0], [0.75, 0.5, 0.75]),
        ([3.0, 1.5, 2.5], [0.5, 0.5, 0.5]), ([-4.5, 1.5, 3.0], [0.5, 0.5, 0.5]), ([0.0, 1.5, -0.5], [0.5, 0.25, 0.5]))]
    stage1 = [rock,
              _like(c[1], [-0.5, 1.5, -3.0], [4.5, 1.0, 5.0]),          # the main cluster, low and half as wide
              _like(c[2], [-4.5, 1.5, -0.5], [3.0, 0.75, 4.5]),
              _like(c[4], [0.5, 2.5, -2.0], [2.0, 1.0, 1.5]),           # a second layer just starting
              _like(small, [-5.0, 1.5, -4.5], [1.5, 1.0, 2.0]),
              _like(small, [2.5, 1.5, 3.0], [2.0, 1.0, 1.5]),
              _like(spat, [-3.5, 2.25, 1.0], [1.0, 0.75, 1.0]), _like(spat, [-1.5, 1.5, -5.0], [1.0, 0.75, 1.0]),
              _like(spat, [4.0, 2.5, -1.0], [1.0, 0.5, 1.0]), _like(spat, [-2.0, 1.5, 4.0], [0.75, 0.5, 0.75])]
    return stage0, stage1


def _young_laver(grown):
    c = grown
    rock = [c[0], c[1], c[3], c[4], c[2]]                         # the rock lumps (and the cap stone)
    tuft, sheet, sheet2, frond, frond2 = c[11], c[5], c[7], c[6], c[8]
    stage0 = rock + [_like(tuft, o, s) for o, s in (
        ([1.5, 5.5, -2.0], [0.5, 0.5, 0.5]), ([-4.0, 3.0, 1.5], [0.5, 0.5, 0.5]), ([-3.0, 3.0, 3.0], [0.5, 0.25, 0.5]),
        ([3.0, 2.0, 3.0], [0.5, 0.5, 0.5]), ([-0.5, 4.0, -4.0], [0.5, 0.25, 0.5]))] + [
        _like(frond, [6.0, 2.5, -3.5], [0.25, 1.0, 1.0])] + [
        _like(sheet2, o, [1.0, 0.25, 1.0]) for o in ([2.0, 5.5, -2.5], [-4.5, 3.0, 2.5], [-4.5, 2.0, -5.5])]   # first blades
    stage1 = rock + [_like(sheet, [1.5, 5.5, -3.5], [2.5, 0.5, 2.5]),        # sheets half grown, flat on the top
                     _like(sheet2, [-4.5, 3.0, 0.5], [2.5, 0.5, 2.5]),
                     _like(c[10], [2.5, 2.0, 3.0], [1.5, 0.5, 1.5]),
                     _like(frond, [6.0, 2.0, -4.0], [0.4, 2.0, 2.0]),
                     _like(frond2, [-6.4, 1.5, 1.0], [1.0, 1.5, 2.0]),
                     _like(tuft, [-3.5, 2.0, -5.0], [0.5, 0.5, 0.5]), _like(tuft, [0.5, 4.0, 1.5], [0.5, 0.5, 0.5])]
    return stage0, stage1


def shore():
    """Own models for growth 0 (just set down) and 1 (small); 2 (grown) keeps the original model."""
    rot = {'north': 0, 'east': 270, 'south': 180, 'west': 90}
    for key, young in (('oyster_bed', _young_oyster), ('laver_rock', _young_laver)):
        gp = os.path.join(RP, 'models', 'blocks', f'{key}.geo.json')
        doc = json.load(open(gp, encoding='utf-8'))
        gs = doc['minecraft:geometry']
        grown = next(g for g in gs if g['description']['identifier'] == f'geometry.{NS}.{key}_0')
        stages = young(grown['bones'][0]['cubes'])
        gs[:] = [grown]
        for i, cubes in enumerate(stages):
            d = dict(grown['description'], identifier=f'geometry.{NS}.{key}_young{i}')
            gs.append({'description': d, 'bones': [{'name': 'root', 'pivot': [0, 0, 0], 'cubes': cubes}]})
        with open(gp, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(doc, f, separators=(',', ':'))
        bp = os.path.join(BP, 'blocks', f'{key}.json')
        blk = json.load(open(bp, encoding='utf-8'))
        perms = []
        for stage in (2, 1, 0):
            for d, r in rot.items():
                comp = {'minecraft:transformation': {'rotation': [0, r, 0]}}
                if stage < 2:
                    comp['minecraft:geometry'] = f'geometry.{NS}.{key}_young{stage}'
                perms.append({'condition': f"q.block_state('minecraft:cardinal_direction') == '{d}' && q.block_state('{NS}:growth') == {stage}",
                              'components': comp})
        blk['minecraft:block']['permutations'] = perms
        with open(bp, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(blk, f, indent=2, ensure_ascii=False)
    print('shore: young growth stages for the oyster bed and laver rock')


def main(argv):
    what = argv[:1] or ['tank', 'board', 'shore']
    if 'all' in what:
        what = ['tank', 'board', 'shore']
    for w in what:
        {'tank': tank, 'board': board, 'shore': shore}[w]()


if __name__ == '__main__':
    main(sys.argv[1:])
