"""The Fishing Skiff (釣魚小船, 1.5.0, plan 8): a rideable boat with a fish hold, a lantern and a trawl net.

  python tools/gen_skiff_1_5.py

The behaviour entity runs on the game's own chest boat (runtime_identifier minecraft:chest_boat): the game moves it on
the water, seats one rider and keeps the 27-slot hold (crouch and use it to open, as a chest boat). The scripts
(world/boat.js) add the rest: catches go into the hold, the trawl, the lantern at night. Writes the BP entity, item,
recipe and loot table, the RP client entity, geometry, texture and render controller. Safe to run again.

The model (polished in 1.5.0), about the size of a vanilla boat (31 long, 20 wide), bow towards -z like every
Bedrock entity model (the way the rider faces):
  hull     clinker planks of oiled oak, a teal sheer strake under the gunwale and red-brown bottom paint, a keel,
           a stem post and a flat transom; the sides step in towards the bow and a little towards the stern.
  inside   five ribs, floorboards, a bench seat (thwart) in the middle for the rider and a second one forward,
           a small foredeck.
  oars     two oars in iron oarlocks at the middle of the gunwale, trailing aft with their blades in the water.
  crate    (bone `crate`) a slatted fish crate at the stern, open, full of fish on crushed ice.
  lantern  (bone `lantern`) a pole at the bow with an arm reaching forward and a glowing lantern hanging from it.
  net      (bone `net`, shown while the trawl is out: property kaleidoscope_fishing:trawl) two tow ropes from the
           stern to a headline with five orange floats, and a tapering net bag of open mesh behind it.
The rotated cubes (oars, tow ropes) turn about x only, which Bedrock and tools/render_models.py agree on.
The texture is painted in code (tools/facepaint.py), 1 texture pixel per model unit, every face its own pixels.
"""
import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facepaint import Sheet, Part, mix, shade, hash01

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [BP]')
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
NS = 'kaleidoscope_fishing'
ID = f'{NS}:fishing_skiff'

# ------------------------------------------------------------------ palette
OAK, OAK_LT, OAK_DK, OAK_IN = '#a8794a', '#c3925c', '#6e4a28', '#b88a58'
TEAL, TEAL_DK, CREAM = '#2f7f7a', '#1f5552', '#e8dcb8'
RED, RED_DK = '#8a3424', '#5e2216'
IRON, IRON_DK, IRON_LT = '#4a4a50', '#2c2c32', '#7a7a82'
ROPE, ROPE_DK = '#cdb88a', '#9a8458'
GLOW, GLOW_HI, GLOW_LO = '#ffc85a', '#fff2b0', '#e8902a'
ICE, ICE_DK, FISH, FISH_DK, FISH_BELLY = '#d6ecf2', '#a8ccd8', '#8aa6b8', '#4e6a80', '#e4ecef'
FLOAT, FLOAT_DK, NET = '#f07a28', '#b8501a', '#d8cfa8'
WOOD_M, IRON_M, GLOW_M, PAINT_M = (0, 0, 200), (170, 0, 110), (0, 200, 60), (0, 0, 170)

# ------------------------------------------------------------------ hull plan: (z0, z1, outer half width W, inner I, top)
SLICES = [(-15, -13, 5.5, 2.5, 10.5), (-13, -11, 7.5, 4.5, 9.75), (-11, -9, 9, 6.5, 9.0),
          (-9, 10, 10, 8.5, 8.5), (10, 13, 9.5, 8, 8.5), (13, 15, 9, 7.5, 8.5)]
WALL_Y0 = 1.0
RIBS = (-7, -3, 1, 5, 9)


def grain(base, plank, along, k=0.12):
    """Wood: each plank a little lighter or darker, darker streaks along the grain, a butt joint every 9 units."""
    t = 0.94 + k * hash01(plank, math.floor(along / 9 + plank * 0.37))
    c = shade(base, t)
    if hash01(plank * 7 + 3, math.floor(along)) > 0.86:
        c = shade(c, 0.88)
    return c


def s_hull_side(p, n):
    """Outside of a side plank (clinker): 2-unit strakes, each one's top row in the shade of the strake above;
    the top strake teal with a cream line, the bottom one red-brown."""
    y, along = p[1], p[2]
    top = next((s[4] for s in SLICES if s[0] <= along <= s[1]), 8.5)
    if n[1] < -0.5:
        return (RED_DK, PAINT_M)
    d = top - y
    if d < 1:
        return (TEAL_DK if hash01(math.floor(along), 5) > 0.8 else TEAL, PAINT_M)
    if d < 2:
        return (shade(TEAL, 0.9), PAINT_M)
    if d < 3:
        return (CREAM, PAINT_M)
    if y < 2.25:
        return (RED if y > 1.5 else RED_DK, PAINT_M)
    k = math.floor((y - 2.25) / 2)
    v = (y - 2.25) - 2 * k
    c = grain(OAK, k, along)
    return (shade(c, 0.72) if v > 1.5 else shade(c, 1.06) if v < 0.5 else c, WOOD_M)


def s_hull_in(p, n):
    """Inside of the hull and the transom: smooth planks with dark seams."""
    y, along = p[1], p[2] if abs(n[0]) > 0.5 else p[0]
    k = math.floor((y - WALL_Y0) / 2)
    v = (y - WALL_Y0) - 2 * k
    c = grain(OAK_IN, k + 20, along)
    return (shade(c, 0.8) if v > 1.6 else c, WOOD_M)


def s_bottom(p, n):
    if n[1] > 0.5:
        k = math.floor(p[0] / 2.5)
        c = grain(OAK_IN, k + 40, p[2])
        return (shade(c, 0.8) if (p[0] / 2.5) % 1 > 0.8 else shade(c, 0.85), WOOD_M)
    return (RED_DK if n[1] < -0.5 else RED, PAINT_M)


def s_gunwale(p, n):
    along = p[2] if abs(p[0]) > 3 else p[0]
    c = grain(OAK_DK, 60, along, 0.2)
    return (shade(c, 1.15) if n[1] > 0.5 else c, WOOD_M)


def s_wood(base, k=0.14):
    def f(p, n):
        along = p[0] if abs(n[2]) > 0.5 or abs(n[1]) > 0.5 else p[2]
        c = grain(base, round(p[1] * 3) + round(p[2] / 4) * 5, along, k)
        return (shade(c, 1.08) if n[1] > 0.5 else shade(c, 0.85) if n[1] < -0.5 else c, WOOD_M)
    return f


def s_floor(p, n):
    k = math.floor(p[0] / 2)
    c = grain(OAK_LT, k + 80, p[2])
    if n[1] > 0.5 and (p[0] / 2) % 1 > 0.75:
        c = shade(c, 0.75)
    return (c, WOOD_M)


def s_iron(p, n):
    return (IRON_LT if n[1] > 0.5 else IRON if abs(n[1]) < 0.5 else IRON_DK, IRON_M)


def s_oar(p, n):
    """Oar shaft: pale ash, a dark leather sleeve where it sits in the oarlock, a worn grip."""
    z = p[2]
    if -1.2 < z < 1.2:
        return ('#5a3a22', WOOD_M)
    if z < -1.5:
        return (shade('#d2b48a', 0.85), WOOD_M)
    return (shade('#d2b48a', 0.95 + 0.08 * hash01(z * 2, 3)), WOOD_M)


def s_blade(p, n):
    if abs(n[1]) > 0.5:
        edge = abs(abs(p[0]) - 11) > 0.9
        return (TEAL if not edge else TEAL_DK, PAINT_M)
    return (TEAL_DK, PAINT_M)


def s_crate(p, n):
    """Crate sides: three slats with dark gaps; the top: crushed ice with three fish laid head to tail."""
    if n[1] > 0.5:
        x, z = p[0], p[2]
        for fx, fz, d in ((-1.5, 8.5, 1), (1.0, 10.5, -1), (-1.0, 12.0, 1)):
            u = (x - fx) * d                                      # along the fish, head at +u
            w = abs(z - fz)
            if -3.0 < u < 3.0 and w < 1.0:
                if u > 2.0 and w < 0.5:
                    return ('#1a1a1a' if u < 2.6 else FISH_DK, PAINT_M)   # the eye, the snout
                return (FISH_DK if z < fz else FISH, PAINT_M)            # dark back, silver side
            if -4.0 < u <= -3.0 and w < 1.0:
                return (FISH_DK, PAINT_M)                              # the tail
        return (ICE_DK if hash01(x * 2, z * 2) > 0.8 else ICE, (0, 0, 60))
    if n[1] < -0.5:
        return (OAK_DK, WOOD_M)
    y = p[1]
    along = p[0] if abs(n[2]) > 0.5 else p[2]
    band = (y - 1.75) % 2.0
    if band > 1.5:
        return ('#3a2a18', WOOD_M)
    return (grain('#b58a52', math.floor((y - 1.75) / 2) + 90, along), WOOD_M)


def s_post(p, n):
    return (shade(OAK_DK, 1.1 if n[1] > 0.5 else 1.0), WOOD_M)


def s_pole(p, n):
    return (grain('#6b4a2c', 120, p[1] if abs(n[1]) < 0.5 else p[2], 0.15), WOOD_M)


def s_lamp(p, n):
    """Lantern glass: an iron frame round each face, a warm glow brighter towards the flame."""
    if abs(n[1]) > 0.5:
        return (IRON_DK, IRON_M)
    if abs(n[0]) > 0.5:
        u = p[2] + 16.75
    else:
        u = p[0]
    v = p[1] - 15.75
    if abs(u) > 1.0 or abs(v) > 1.25:
        return (IRON, IRON_M)
    if abs(u) < 0.4 and -1.0 < v < 0.3:
        return (GLOW_HI, (0, 255, 40))
    return (GLOW if abs(u) < 0.6 else GLOW_LO, GLOW_M)


def s_rope(p, n):
    t = p[0] + p[1] + p[2]
    return (ROPE if int(math.floor(t * 1.5)) % 2 else ROPE_DK, WOOD_M)


def s_float(p, n):
    if abs(n[1]) < 0.5 and abs(p[1] - 3.25) < 0.3:
        return (CREAM, PAINT_M)
    return (FLOAT if n[1] >= 0 else FLOAT_DK, PAINT_M)


def s_mesh(p, n):
    """Open netting: a line every third unit both ways (the holes are cut out by the alpha test)."""
    if abs(n[0]) > 0.5:
        u, v = p[2], p[1]
    elif abs(n[1]) > 0.5:
        u, v = p[0], p[2]
    else:
        u, v = p[0], p[1]
    on_u = (math.floor(u + 99) % 3) == 0
    on_v = (math.floor(v + 99) % 3) == 0
    if on_u and on_v:
        return ('#b8ae86', WOOD_M)                                   # the knots
    if on_u or on_v:
        return (NET, WOOD_M)
    return None


def model():
    sheet = Sheet()
    g = Part(sheet)
    hull, inside, crate, lantern, net = [], [], [], [], []

    # --- hull: stem, side planks per slice, bottom, transom, keel
    hull.append(g.box([-3.5, 0.5, -17], [3.5, 10.75, -15], s_hull_side, shaders={'up': s_gunwale, 'south': s_hull_in}))
    hull.append(g.box([-1, 1.5, -18.5], [1, 12, -16.5], s_post, shaders={'south': s_post}))        # stem post
    widths = [3.5] + [s[2] for s in SLICES] + [9]
    for k, (z0, z1, W, I, top) in enumerate(SLICES):
        # the ends of a side plank: outside paint where it steps out past its neighbour, plain planks inside
        ends = {f: (lambda p, n, w=w: s_hull_side(p, n) if abs(p[0]) > w - 0.01 else s_hull_in(p, n))
                for f, w in (('north', widths[k]), ('south', widths[k + 2]))}
        for sx in (1, -1):
            lo, hi = sorted((sx * I, sx * W))
            out, inn = ('east', 'west') if sx > 0 else ('west', 'east')
            hull.append(g.box([lo, WALL_Y0, z0], [hi, top, z1], s_hull_side,
                              shaders={inn: s_hull_in, 'up': s_gunwale, **ends}))
            clo, chi = sorted((sx * (I - 0.25), sx * (W + 0.5)))
            hull.append(g.box([clo, top, z0], [chi, top + 0.75, z1], s_gunwale))                     # gunwale cap
        hull.append(g.box([-(W - 0.75), 0, z0], [W - 0.75, 1.5, z1], s_bottom))
    hull.append(g.box([-9, WALL_Y0, 15], [9, 9.0, 16.5], s_hull_side, shaders={'north': s_hull_in, 'up': s_gunwale}))  # transom
    hull.append(g.box([-9.5, 9.0, 14.75], [9.5, 9.75, 16.75], s_gunwale))
    hull.append(g.box([-8.25, 0, 15], [8.25, 1.5, 16.5], s_bottom))
    hull.append(g.box([-0.75, -0.75, -17], [0.75, 0, 16], s_post))                                # keel
    hull.append(g.box([-0.5, 1.5, 16.5], [0.5, 4.0, 17.25], s_post))                              # rudder post stub

    # --- inside: ribs, floorboards, thwarts, foredeck, oarlocks and oars
    for zr in RIBS:
        I = next(s[3] for s in SLICES if s[0] <= zr < s[1])
        top = next(s[4] for s in SLICES if s[0] <= zr < s[1])
        for sx in (1, -1):
            lo, hi = sorted((sx * (I - 0.6), sx * I))
            inside.append(g.box([lo, 1.5, zr], [hi, top - 0.25, zr + 1], s_wood(OAK_DK)))
        inside.append(g.box([-(I - 0.6), 1.5, zr], [I - 0.6, 2.3, zr + 1], s_wood(OAK_DK)))
    inside.append(g.box([-4, 1.5, -10], [4, 1.8, 14.5], s_floor))
    inside.append(g.box([-8.5, 5.0, -2], [8.5, 6.0, 1.5], s_wood('#b98c56')))                    # the rider's thwart
    inside.append(g.box([-8.5, 6.0, -8.5], [8.5, 7.0, -6.5], s_wood('#b98c56')))                 # forward thwart
    inside.append(g.box([-1, 1.8, -1.5], [1, 5.0, 1], s_wood(OAK_DK)))                            # its post
    inside.append(g.box([-4.5, 8.75, -15], [4.5, 9.5, -11], s_wood('#9c7044', 0.1)))              # foredeck
    inside.append(g.box([-6.5, 8.25, -11], [6.5, 8.75, -9.5], s_wood('#9c7044', 0.1)))            # its beam
    for sx in (1, -1):
        for a, b in ((10.25, 10.5), (11.5, 11.75)):
            lo, hi = sorted((sx * a, sx * b))
            inside.append(g.box([lo, 9.25, -0.5], [hi, 10.75, 0.5], s_iron))
        lo, hi = sorted((sx * 10.25, sx * 11.75))
        inside.append(g.box([lo, 9.0, -0.75], [hi, 9.25, 0.75], s_iron))
        lo, hi = sorted((sx * 10.5, sx * 11.5))
        piv = [sx * 11, 10, 0]
        inside.append(g.box([lo, 9.5, -2.5], [hi, 10.5, 13], s_oar, rotation=[-24, 0, 0], pivot=piv))
        blo, bhi = sorted((sx * 9.75, sx * 12.25))
        inside.append(g.box([blo, 9.75, 13], [bhi, 10.25, 19], s_blade, rotation=[-24, 0, 0], pivot=piv))

    # --- the fish crate at the stern
    crate.append(g.box([-6, 1.75, 7], [6, 7.5, 13], s_crate))
    for x0, x1 in ((-6.5, -5.5), (5.5, 6.5)):
        for z0, z1 in ((6.5, 7.5), (12.5, 13.5)):
            crate.append(g.box([x0, 1.75, z0], [x1, 8.0, z1], s_post))
    crate.append(g.box([-5.5, 7.5, 6.6], [5.5, 8.0, 7.4], s_post))
    crate.append(g.box([-5.5, 7.5, 12.6], [5.5, 8.0, 13.4], s_post))
    crate.append(g.box([-6.4, 7.5, 7.5], [-5.6, 8.0, 12.5], s_post))
    crate.append(g.box([5.6, 7.5, 7.5], [6.4, 8.0, 12.5], s_post))
    crate.append(g.box([-1.5, 5.0, 13.4], [1.5, 6.0, 13.9], s_rope))                             # a rope handle

    # --- the lantern at the bow
    lantern.append(g.box([-0.5, 1.8, -13], [0.5, 21, -12], s_pole))
    lantern.append(g.box([-0.5, 20, -18], [0.5, 21, -13], s_pole))
    lantern.append(g.box([-0.75, 19.25, -13.75], [0.75, 21.25, -12.75], s_iron))                 # the iron band
    lantern.append(g.box([-0.2, 18.5, -17], [0.2, 20, -16.5], s_iron))                           # hook
    lantern.append(g.box([-0.5, 18.0, -17.25], [0.5, 18.5, -16.25], s_iron))                      # ring
    lantern.append(g.box([-1.75, 17.25, -18.5], [1.75, 18.0, -15.0], s_iron))                     # cap
    lantern.append(g.box([-1.5, 14.0, -18.25], [1.5, 17.25, -15.25], s_lamp))                     # glass
    lantern.append(g.box([-1.75, 13.25, -18.5], [1.75, 14.0, -15.0], s_iron))                     # base

    # --- the trawl: ropes, headline with floats, the net bag
    for sx in (1, -1):
        lo, hi = sorted((sx * 6.75, sx * 7.25))
        net.append(g.box([lo, 8.25, 16.5], [hi, 8.75, 24.5], s_rope, rotation=[-37, 0, 0], pivot=[sx * 7, 8.5, 16.5]))
        net.append(g.box([sx * 7 - 0.5, 8.75, 16.25], [sx * 7 + 0.5, 9.75, 17.25], s_iron))       # the cleat it is tied to
    net.append(g.box([-7.5, 3.0, 22.5], [7.5, 3.5, 23.0], s_rope))                                 # headline
    for x in (-6, -3, 0, 3, 6):
        net.append(g.box([x - 0.75, 2.5, 22.0], [x + 0.75, 4.0, 23.5], s_float))
    for (w, y0, y1, z0, z1) in ((7, -3.0, 3.0, 23, 27.5), (5, -2.0, 2.25, 27.5, 31.5), (3, -1.25, 1.5, 31.5, 35)):
        net.append(g.box([-w, y0, z0], [w, y1, z1], s_mesh, faces=('south', 'east', 'west', 'up', 'down')))
    net.append(g.box([-1.5, -0.75, 35], [1.5, 1.0, 37], s_mesh))
    net.append(g.box([-1.75, -0.5, 36.75], [1.75, 0.75, 37.25], s_rope))                          # the cod-end tie

    def bone(name, cubes):
        return {'name': name, 'parent': 'root', 'pivot': [0, 0, 0], 'cubes': cubes}
    bones = [{'name': 'root', 'pivot': [0, 0, 0]}, bone('hull', hull + inside), bone('crate', crate),
             bone('lantern', lantern), bone('net', net)]
    return sheet, bones


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')


def main():
    sheet, bones = model()
    png = os.path.join(RP, 'textures', 'entity', 'kfv_fishing_skiff.png')
    write_json(png[:-4] + '.texture_set.json', {'format_version': '1.16.100', 'minecraft:texture_set': {
        'color': 'kfv_fishing_skiff', 'metalness_emissive_roughness': 'kfv_fishing_skiff_mer', 'heightmap': 'kfv_fishing_skiff_height'}})
    sheet.save(png)                                   # fills in the UVs, writes the colour, height and MER maps
    tw, th = sheet.size
    geo = os.path.join(RP, 'models', 'entity', 'fishing_skiff.geo.json')
    write_json(geo, {'format_version': '1.16.0', 'minecraft:geometry': [{
        'description': {'identifier': f'geometry.{NS}.fishing_skiff', 'texture_width': tw, 'texture_height': th,
                        'visible_bounds_width': 5, 'visible_bounds_height': 3, 'visible_bounds_offset': [0, 0.5, 0]},
        'bones': bones}]})
    write_json(os.path.join(RP, 'entity', 'fishing_skiff.entity.json'), {'format_version': '1.10.0', 'minecraft:client_entity': {'description': {
        'identifier': ID, 'materials': {'default': 'entity_alphatest'}, 'textures': {'default': 'textures/entity/kfv_fishing_skiff'},
        'geometry': {'default': f'geometry.{NS}.fishing_skiff'}, 'render_controllers': [f'controller.render.{NS}.fishing_skiff']}}})
    write_json(os.path.join(RP, 'render_controllers', 'kfv_fishing_skiff.render_controllers.json'), {'format_version': '1.8.0', 'render_controllers': {
        f'controller.render.{NS}.fishing_skiff': {'geometry': 'Geometry.default', 'materials': [{'*': 'Material.default'}], 'textures': ['Texture.default'],
                                                 'part_visibility': [{'*': True}, {'net': f"q.property('{NS}:trawl') == 1"}]}}})
    write_json(os.path.join(BP, 'entities', 'fishing_skiff.json'), {'format_version': '1.21.60', 'minecraft:entity': {
        'description': {'identifier': ID, 'runtime_identifier': 'minecraft:chest_boat', 'is_spawnable': False, 'is_summonable': True,
                        'properties': {f'{NS}:trawl': {'type': 'int', 'range': [0, 1], 'default': 0, 'client_sync': True}}},
        'components': {
            'minecraft:type_family': {'family': ['boat', 'inanimate', 'fishing_skiff']},
            'minecraft:collision_box': {'width': 1.4, 'height': 0.455},
            'minecraft:inventory': {'container_type': 'chest_boat', 'inventory_size': 27, 'can_be_siphoned_from': True},
            'minecraft:rideable': {'seat_count': 1, 'interact_text': 'action.interact.ride.boat', 'pull_in_entities': True,
                                   'family_types': ['player'], 'seats': [{'position': [0, -0.2, 0], 'min_rider_count': 0, 'max_rider_count': 1}]},
            'minecraft:buoyant': {'apply_gravity': True, 'base_buoyancy': 1.0, 'simulate_waves': False, 'big_wave_probability': 0.03,
                                  'big_wave_speed': 10.0, 'liquid_blocks': ['minecraft:water', 'minecraft:flowing_water']},
            'minecraft:physics': {}, 'minecraft:pushable': {'is_pushable': True, 'is_pushable_by_piston': True},
            'minecraft:leashable': {'soft_distance': 4.0, 'hard_distance': 6.0, 'max_distance': 10.0},
            'minecraft:loot': {'table': f'loot_tables/{NS}/entities/fishing_skiff.json'},
            'minecraft:is_stackable': {}}}})
    write_json(os.path.join(BP, 'loot_tables', NS, 'entities', 'fishing_skiff.json'), {'pools': [{'rolls': 1, 'entries': [{'type': 'item', 'name': ID}]}]})
    print(f'wrote the Fishing Skiff ({tw}x{th} texture)')


if __name__ == '__main__':
    main()
