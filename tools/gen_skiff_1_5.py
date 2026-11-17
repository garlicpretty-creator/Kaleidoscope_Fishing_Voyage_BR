"""The Fishing Skiff (釣魚小船, 1.5.0, plan 8): a rideable boat with a fish hold, a lantern and a trawl net.

  python tools/gen_skiff_1_5.py

The behaviour entity runs on the game's own chest boat (runtime_identifier minecraft:chest_boat): the game moves it on
the water, seats one rider and keeps the 27-slot hold (crouch and use it to open, as a chest boat). The scripts
(world/boat.js) add the rest: catches go into the hold, the trawl, the lantern at night. Writes the BP entity and
loot table, the RP client entity, geometry, texture, render controller, animations, animation controllers and the
boat particles (the item, recipe and catalog entry come from gen_1_5.py). Safe to run again.

Which way the bow points. A boat's rotation in Bedrock is 90 degrees off the way it travels (a leftover of the old
Java boat): the vanilla chest boat's seat turns its rider by rotate_rider_by -90 so they face the way it moves, and
Geyser adds 90 to a Java boat's yaw for Bedrock. The rider faces, and the boat goes, the entity's rotation - 90, i.e.
to the entity's left, which in a Bedrock model is +x (the face of a mob is -z, its left arm +x). So the skiff is drawn
with its bow towards -z (the drawing, as before) and the model is that drawing turned so the bow points to +x
(BOW = 1; BOW = -1 would turn it to -x if a game test ever shows it backwards: geometry, seat and Molang all follow).
The seat turns the rider the same way the vanilla chest boat's does (rotate_rider_by -90, lock_rider_rotation 90).

The model (polished in 1.5.0), about the size of a vanilla boat (31 long, 20 wide):
  hull     (bone `hull`) clinker planks of oiled oak, a teal sheer strake under the gunwale and red-brown bottom
           paint, a keel, a stem post and a flat transom; the sides step in towards the bow and a little towards the
           stern. Inside: five ribs, floorboards, a thwart for the rider and one forward, a small foredeck, the iron
           oarlocks. Locators `bow` (spray) and `stern` (wake).
  oars     (bones `oar_left` / `oar_right`, the rider's left and right, each with a child `oar_<side>_dip`) built
           pointing straight out of the oarlock; the bones' rest angles trail them aft with the blades in the water.
  crate    (bone `crate`) a slatted fish crate at the stern, open, full of fish on crushed ice.
  lantern  (bone `lantern`) a pole at the bow with an arm reaching forward; (bone `lamp`) the glowing lantern hanging
           from the arm, free to swing.
  net      (bone `net`, shown while the trawl is out: property kaleidoscope_fishing:trawl) the stern cleats >
           `tow` the two tow ropes, angled down from the cleats > `headline` with five orange floats, turned back level
           > `bag_a` > `bag_b` (locator `net_fish`) > `bag_c`, the tapering net bag of open mesh in three sections.
No cube is rotated: every angle is a bone's, so the animation can move it. Bone angles are written with bone_rot()
in the game's sense (it draws a model mirrored in x, so x and z angles run the other way round from y);
tools/render_models.py draws y and z angles the other way, so judge the oars and the tow from a hand-posed preview.
The texture is painted in code (tools/facepaint.py), 1 texture pixel per model unit, every face its own pixels.

The animation (client side only, Molang; animations/kfv_fishing_skiff.animation.json, nothing from the scripts):
pre_animation measures the boat from its own position and rotation every frame (speed, speed along the bow,
acceleration, turning rate), since a boat has no walk animation for q.modified_move_speed to read.
  motion   the hull bobs and rolls on the water (less on land), lifts its bow under way and leans into turns. With a
           rider, the oars row while the boat moves: each stroke swings the blade from 30 degrees forward to 50 aft
           dipped deep (the drive), then back lifted clear (the recovery), faster the faster it goes, backwards when
           backing up; turning, the outer oar rows alone (the left one to turn right). Still or empty, they ease back to
           rest. The lamp swings as a damped pendulum, lagging aft as the boat speeds up and swinging on with the swell.
  trawl    the tow ropes hang steep and slack at rest and pull shallow and taut under way, with a small tug; the
           headline rocks so the floats bob in turn; the bag sways, ripples down its three sections and billows.
  particles (animation controllers, so they run only while it makes sense) kaleidoscope_fishing:boat_wake flat foam
           behind the stern under way, boat_spray drops off the bow at speed, boat_net_fish a small fish flipping up
           in the net now and then while the trawl is out.
"""
import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facepaint import Sheet, Part, FACES, NORMAL, mix, shade, hash01

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


# ------------------------------------------------------------------ which way the model points
# The hull is drawn with its bow towards -z (the "drawing"); the model is that drawing turned about y so the bow
# points along +x * BOW (see the docstring: a boat's travel direction is 90 degrees off its entity rotation).
BOW = 1


def to_model(p):
    """A point of the drawing (bow -z) in the model (bow +x * BOW)."""
    return [-BOW * p[2], p[1], BOW * p[0]]


def to_drawing(p):
    """A model point back in the drawing's coordinates (what the shaders were written for)."""
    return [BOW * p[2], p[1], -BOW * p[0]]


def face_to_model(f):
    n = to_model(NORMAL[f])
    return next(k for k, v in NORMAL.items() if all(abs(v[i] - n[i]) < 1e-9 for i in range(3)))


class Drawn:
    """Boxes given in the drawing's coordinates, placed in the model (turned, then moved by `shift`); the shaders
    still see the drawing's coordinates, so the paint is the same whichever way the model points."""

    def __init__(self, sheet, shift=(0, 0, 0)):
        self.shift = shift
        self.part = Part(sheet, to_src=lambda p: to_drawing([p[i] - shift[i] for i in range(3)]), to_src_n=to_drawing)

    def at(self, p):
        q = to_model(p)
        return [round(q[i] + self.shift[i], 4) for i in range(3)]

    def box(self, lo, hi, shader, faces=FACES, shaders=None):
        a, b = to_model(lo), to_model(hi)
        nlo = [min(a[i], b[i]) + self.shift[i] for i in range(3)]
        nhi = [max(a[i], b[i]) + self.shift[i] for i in range(3)]
        return self.part.box(nlo, nhi, shader, faces=tuple(face_to_model(f) for f in faces),
                             shaders={face_to_model(f): s for f, s in (shaders or {}).items()})


# ------------------------------------------------------------------ the moving parts (all angles in degrees)
OAR_PIVOT_Y, OAR_PIVOT_Z = 10, 11       # the oarlocks, either side amidships
OAR_IN, OAR_OUT, BLADE = 2.5, 13, 6     # the oar: handle inboard of the oarlock, shaft outboard, then the blade
SWEEP_REST, DIP_REST = 84, 20           # at rest the oars trail aft alongside, blades in the water
SWEEP_MID, SWEEP_AMP = 10, 40           # rowing: the oar swings between 30 forward (catch) and 50 aft (finish)
DIP_MID, DIP_AMP = 9, 16                # ... the blade deep (25) through the drive, lifted (-7) on the recovery
TOW_LEN, TOW_DROP = 8, 37               # the tow ropes: 8 long from the stern cleats, 37 down at rest
TOW_SHIFT = [round(-BOW * TOW_LEN * (1 - math.cos(math.radians(TOW_DROP))), 4),
             round(TOW_LEN * math.sin(math.radians(TOW_DROP)), 4), 0]


def bone_rot(rx=0.0, ry=0.0, rz=0.0):
    """Bone angles that turn a model point the way the game does: the game draws the model mirrored in x, so in
    model coordinates a bone's x and z angles turn the right-handed way round negated and its y angle as it is
    (checked: a positive y turns the held tide clock's hand clockwise in game; vanilla's idle arm bob, positive
    z on the right arm, swings it outwards; tools/render_models.py draws y and z the other way)."""
    def neg(v):
        return (-v if v else 0) if isinstance(v, (int, float)) else f'-({v})'
    return [neg(rx), ry, neg(rz)]


def model():
    sheet = Sheet()
    g = Drawn(sheet)
    hull, inside, crate, lantern, lamp, net = [], [], [], [], [], []

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

    # --- inside: ribs, floorboards, thwarts, foredeck, oarlocks
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

    # --- the oars, each in two bones at its oarlock: `oar_<side>` swings it fore and aft (y), `oar_<side>_dip`
    # lifts and dips the blade (x). Built pointing straight out from the side; the bones' rest angles trail them aft.
    # The rider's left is the model's +z side when the bow is +x (BOW = 1).
    o = Part(sheet)
    oars = []
    for side, s in (('left', BOW), ('right', -BOW)):
        def sh_shaft(p, n, s=s):
            return s_oar([0, 0, s * p[2] - OAR_PIVOT_Z], n)

        def sh_blade(p, n, s=s):
            along = s * p[2] - OAR_PIVOT_Z
            rim = abs(p[1] - OAR_PIVOT_Y) > 0.8 or along > OAR_OUT + BLADE - 0.6 or abs(n[0]) < 0.5
            return (TEAL_DK if rim else TEAL, PAINT_M)
        z_in, z_out, z_tip = (s * (OAR_PIVOT_Z + d) for d in (-OAR_IN, OAR_OUT, OAR_OUT + BLADE))
        cubes = [o.box([-0.5, OAR_PIVOT_Y - 0.5, min(z_in, z_out)], [0.5, OAR_PIVOT_Y + 0.5, max(z_in, z_out)], sh_shaft),
                 o.box([-0.25, OAR_PIVOT_Y - 1.25, min(z_out, z_tip)], [0.25, OAR_PIVOT_Y + 1.25, max(z_out, z_tip)], sh_blade)]
        piv = [0, OAR_PIVOT_Y, s * OAR_PIVOT_Z]
        oars.append({'name': f'oar_{side}', 'parent': 'root', 'pivot': piv,
                     'rotation': bone_rot(ry=-BOW * s * SWEEP_REST)})
        oars.append({'name': f'oar_{side}_dip', 'parent': f'oar_{side}', 'pivot': piv,
                     'rotation': bone_rot(rx=s * DIP_REST), 'cubes': cubes})

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

    # --- the lantern at the bow: the pole and its arm (`lantern`), the lamp hanging from the arm (`lamp`)
    lantern.append(g.box([-0.5, 1.8, -13], [0.5, 21, -12], s_pole))
    lantern.append(g.box([-0.5, 20, -18], [0.5, 21, -13], s_pole))
    lantern.append(g.box([-0.75, 19.25, -13.75], [0.75, 21.25, -12.75], s_iron))                 # the iron band
    lamp.append(g.box([-0.2, 18.5, -17], [0.2, 20, -16.5], s_iron))                              # hook
    lamp.append(g.box([-0.5, 18.0, -17.25], [0.5, 18.5, -16.25], s_iron))                         # ring
    lamp.append(g.box([-1.75, 17.25, -18.5], [1.75, 18.0, -15.0], s_iron))                        # cap
    lamp.append(g.box([-1.5, 14.0, -18.25], [1.5, 17.25, -15.25], s_lamp))                        # glass
    lamp.append(g.box([-1.75, 13.25, -18.5], [1.75, 14.0, -15.0], s_iron))                        # base

    # --- the trawl: `net` (the stern cleats) > `tow` (the two ropes, turning down from the cleats) > `headline`
    # (turned back level, with the floats) > `bag_a` > `bag_b` > `bag_c` (the net bag in three sections, so it can
    # ripple). The headline and the bag are drawn where they hang at rest and moved by TOW_SHIFT to where they sit
    # while the tow is level, so the tow's rest angle puts them back.
    for sx in (1, -1):
        net.append(g.box([sx * 7 - 0.5, 8.75, 16.25], [sx * 7 + 0.5, 9.75, 17.25], s_iron))       # the cleat
    cleat = g.at([0, 8.5, 16.5])
    tow = []
    for sx in (1, -1):
        x0, x1 = sorted((cleat[0], cleat[0] - BOW * TOW_LEN))
        z0, z1 = sorted((sx * 6.75, sx * 7.25))
        tow.append(o.box([x0, 8.25, z0], [x1, 8.75, z1], s_rope))
    h = Drawn(sheet, TOW_SHIFT)
    headline = [h.box([-7.5, 3.0, 22.5], [7.5, 3.5, 23.0], s_rope)]
    for x in (-6, -3, 0, 3, 6):
        headline.append(h.box([x - 0.75, 2.5, 22.0], [x + 0.75, 4.0, 23.5], s_float))
    open_ = ('south', 'east', 'west', 'up', 'down')
    bag = [[h.box([-7, -3.0, 23], [7, 3.0, 27.5], s_mesh, faces=open_)],
           [h.box([-5, -2.0, 27.5], [5, 2.25, 31.5], s_mesh, faces=open_)],
           [h.box([-3, -1.25, 31.5], [3, 1.5, 35], s_mesh, faces=open_),
            h.box([-1.5, -0.75, 35], [1.5, 1.0, 37], s_mesh),
            h.box([-1.75, -0.5, 36.75], [1.75, 0.75, 37.25], s_rope)]]                            # the cod-end tie

    def bone(name, cubes, parent='root', pivot=(0, 0, 0), **extra):
        b = {'name': name, 'parent': parent, 'pivot': list(pivot)}
        b.update(extra)
        if cubes:
            b['cubes'] = cubes
        return b
    bones = [{'name': 'root', 'pivot': [0, 3, 0]},
             bone('hull', hull + inside, locators={'bow': g.at([0, 3.5, -19.5]), 'stern': g.at([0, 2.0, 18])}),
             *oars,
             bone('crate', crate),
             bone('lantern', lantern, pivot=g.at([0, 1.8, -12.5])),
             bone('lamp', lamp, 'lantern', g.at([0, 20, -16.75])),
             bone('net', net, pivot=cleat),
             bone('tow', tow, 'net', cleat, rotation=bone_rot(rz=BOW * TOW_DROP)),
             bone('headline', headline, 'tow', [cleat[0] - BOW * TOW_LEN, cleat[1], 0], rotation=bone_rot(rz=-BOW * TOW_DROP)),
             bone('bag_a', bag[0], 'headline', h.at([0, 3.0, 23])),
             bone('bag_b', bag[1], 'bag_a', h.at([0, 0.1, 27.5]), locators={'net_fish': h.at([0, 1.0, 29.5])}),
             bone('bag_c', bag[2], 'bag_b', h.at([0, 0.1, 31.5]))]
    return sheet, bones


# ------------------------------------------------------------------ the animation (client side, all Molang)
# Every frame, pre_animation works out from the boat's own position and rotation: v.spd its speed (blocks a
# second, smoothed), v.vf the same along the bow (negative backing up), v.acc its acceleration, v.turn how fast it
# turns (degrees a second, positive turning right), v.wl / v.wr how hard each oar rows (0 rest .. 1), v.phase the
# rowing stroke (degrees), v.la the lamp's swing (degrees, positive aft), v.tow the tow ropes' angle, v.wet 1 afloat.
# The game rotates a boat 90 degrees off its travel: the bow's heading is the entity's rotation - 90 * BOW.
def scripts():
    B = BOW
    init = ['v.px = q.position(0); v.pz = q.position(2); v.yaw = q.body_y_rotation;',
            'v.spd = 0; v.vf = 0; v.vfp = 0; v.acc = 0; v.turn = 0; v.wl = 0; v.wr = 0; v.phase = 0;',
            'v.la = 0; v.lv = 0; v.go = 0; v.wet = 1; v.tow = 46;']
    pre = [
        'v.dt = math.clamp(q.delta_time, 0, 0.1);',
        'v.dx = q.position(0) - v.px; v.dz = q.position(2) - v.pz; v.px = q.position(0); v.pz = q.position(2);',
        # a jump of more than 2 blocks in a frame is a teleport, not sailing
        'v.inv = (v.dt > 0 && (v.dx * v.dx + v.dz * v.dz) < 4) ? 1 / v.dt : 0;',
        'v.dyaw = q.body_y_rotation - v.yaw; v.dyaw = v.dyaw - 360 * math.round(v.dyaw / 360); v.yaw = q.body_y_rotation;',
        'v.k = math.min(1, v.dt * 3);',
        f'v.vf = v.vf + (math.clamp({B} * (v.dx * math.cos(v.yaw) + v.dz * math.sin(v.yaw)) * v.inv, -12, 12) - v.vf) * v.k;',
        'v.spd = v.spd + (math.min(math.sqrt(v.dx * v.dx + v.dz * v.dz) * v.inv, 12) - v.spd) * v.k;',
        'v.acc = v.dt > 0 ? v.acc + ((v.vf - v.vfp) / v.dt - v.acc) * math.min(1, v.dt * 5) : v.acc; v.vfp = v.vf;',
        'v.turn = v.turn + (math.clamp(v.dyaw * v.inv, -360, 360) - v.turn) * math.min(1, v.dt * 4);',
        'v.go = math.clamp((v.spd - 0.4) / 2, 0, 1);',
        'v.wet = (q.is_in_water || !q.is_on_ground) ? 1 : 0.3;',
        # the left oar pulls to turn right, the right oar to turn left, both to go ahead; nobody rows an empty boat
        'v.ride = q.has_rider ? 1 : 0;',
        'v.wl = v.wl + (v.ride * math.clamp(v.go + math.max(0, v.turn) / 50, 0, 1) - v.wl) * v.k;',
        'v.wr = v.wr + (v.ride * math.clamp(v.go + math.max(0, -v.turn) / 50, 0, 1) - v.wr) * v.k;',
        'v.phase = math.mod(v.phase + 360 + v.dt * (v.vf < -0.3 ? -1 : 1) * (math.max(v.wl, v.wr) > 0.01 ? 160 + 30 * math.min(v.spd, 8) : 0), 360);',
        # the lamp: a damped pendulum pushed by the boat's acceleration (it lags aft as the boat speeds up)
        'v.lv = v.lv + (40 * (math.clamp(v.acc, -3, 3) * 9 - v.la) - 3.2 * v.lv) * v.dt;',
        'v.la = math.clamp(v.la + v.lv * v.dt, -28, 28);',
        # the tow ropes: slack and steep with the net sinking at rest, taut and shallow under way, tugging
        'v.tow = 46 - 20 * v.go + 1.5 * v.go * math.sin(q.life_time * 290);',
    ]
    return init, pre


def animations():
    B = BOW
    t = 'q.life_time'
    roll = f'v.wet * (1.4 * math.sin({t} * 61) + 0.6 * math.sin({t} * 103 + 70))'
    bones = {
        # the whole boat bobs and rolls on the water, lifts its bow under way and leans into a turn
        'root': {'position': [0, f'v.wet * (0.45 * math.sin({t} * 95) + 0.25 * math.sin({t} * 151 + 40)) + 0.2 * v.go * math.sin(v.phase * 2)', 0],
                 'rotation': bone_rot(rx=f'{roll} + math.clamp(v.turn / 12, -3, 3)',
                                      rz=f'{B} * (v.wet * 0.8 * math.sin({t} * 77 + 20) + 1.6 * v.go + 0.25 * math.clamp(v.acc, -4, 4))')},
        'lantern': {'rotation': bone_rot(rx=f'0.5 * {roll}')},
        'lamp': {'rotation': bone_rot(rx=f'v.wet * 3.5 * math.sin({t} * 61 - 60) + math.clamp(v.turn / 6, -10, 10)',
                                      rz=f'-{B} * (v.la + v.wet * 2.5 * math.sin({t} * 77 - 40))')},
    }
    for side, s, w in (('left', B, 'v.wl'), ('right', -B, 'v.wr')):
        sweep = f'(({SWEEP_MID} - {SWEEP_AMP} * math.cos(v.phase)) - {SWEEP_REST}) * {w}'
        dip = f'(({DIP_MID} + {DIP_AMP} * math.sin(v.phase)) - {DIP_REST}) * {w}'
        bones[f'oar_{side}'] = {'rotation': bone_rot(ry=f'{-B * s} * {sweep}')}
        bones[f'oar_{side}_dip'] = {'rotation': bone_rot(rx=f'{s} * {dip}')}
    trawl = {
        'tow': {'rotation': bone_rot(ry=f'math.clamp(v.turn / 4, -10, 10)', rz=f'{B} * (v.tow - {TOW_DROP})')},
        'headline': {'position': [0, f'0.35 * math.sin({t} * 130)', 0],
                     'rotation': bone_rot(rx=f'4 * math.sin({t} * 110)', rz=f'-{B} * (v.tow - {TOW_DROP})')},
    }
    for k, (name, lag) in enumerate((('bag_a', 0), ('bag_b', 50), ('bag_c', 100))):
        trawl[name] = {
            'rotation': bone_rot(ry=f'({2.5 + k} + {3 + k} * v.go) * math.sin({t} * 70 - {lag}) - math.clamp(v.turn / {8 - 2 * k}, -8, 8)',
                                 rz=f'{B} * ({9 - 2.5 * k} * (1 - v.go) + {2 + k} * math.sin({t} * 90 - {lag + 10}))'),
            'scale': [1, f'1 + (0.05 + 0.07 * v.go) * math.sin({t} * 160 - {lag * 1.4})',
                      f'1 + (0.05 + 0.07 * v.go) * math.sin({t} * 160 - {lag * 1.4 + 40})']}

    def a(name, body):
        return f'animation.{NS}.fishing_skiff.{name}', body
    return dict([
        a('motion', {'loop': True, 'bones': bones}),
        a('trawl', {'loop': True, 'bones': trawl}),
        a('wake', {'loop': True, 'animation_length': 0.2, 'particle_effects': {'0.0': {'effect': 'wake', 'locator': 'stern'}}}),
        a('spray', {'loop': True, 'animation_length': 0.25, 'particle_effects': {'0.0': {'effect': 'spray', 'locator': 'bow'}}}),
        a('net_fish', {'loop': True, 'animation_length': 1.7, 'particle_effects': {
            '0.35': {'effect': 'net_fish', 'locator': 'net_fish'}, '1.2': {'effect': 'net_fish', 'locator': 'net_fish'}}}),
    ])


def controllers():
    """Particles only while they make sense: the wake under way, the bow spray at speed, the fish in the net."""
    def ctl(name, anim, on, off):
        return f'controller.animation.{NS}.fishing_skiff.{name}', {'initial_state': 'default', 'states': {
            'default': {'transitions': [{'on': on}]},
            'on': {'animations': [anim], 'transitions': [{'default': off}]}}}
    trawl = f"q.property('{NS}:trawl') == 1"
    return dict([ctl('wake', 'wake', 'v.spd > 1.2 && v.wet > 0.5', 'v.spd < 0.8 || v.wet < 0.5'),
                 ctl('spray', 'spray', 'v.spd > 5 && v.wet > 0.5', 'v.spd < 4 || v.wet < 0.5'),
                 ctl('net_fish', 'net_fish', trawl, f'!({trawl})')])


def particle(name, texture, material, components):
    return {'format_version': '1.10.0', 'particle_effect': {
        'description': {'identifier': f'{NS}:boat_{name}', 'basic_render_parameters': {'material': material, 'texture': texture}},
        'components': components}}


def particles():
    sheet = 'textures/particle/particles'
    wake = particle('wake', sheet, 'particles_blend', {
        # flat foam left on the water behind the stern, spreading and fading
        'minecraft:emitter_rate_instant': {'num_particles': 'math.random_integer(1, 3)'},
        'minecraft:emitter_lifetime_once': {'active_time': 0.05},
        'minecraft:emitter_shape_disc': {'radius': 0.3, 'plane_normal': [0, 1, 0], 'surface_only': False, 'direction': 'outwards'},
        'minecraft:particle_initial_speed': 'math.random(0.2, 0.5)',
        'minecraft:particle_lifetime_expression': {'max_lifetime': 'math.random(1.0, 1.6)'},
        'minecraft:particle_motion_dynamic': {'linear_drag_coefficient': 1.5},
        'minecraft:particle_initial_spin': {'rotation': 'math.random(0, 360)'},
        'minecraft:particle_appearance_billboard': {
            'size': ['0.12 + 0.22 * v.particle_age / v.particle_lifetime', '0.12 + 0.22 * v.particle_age / v.particle_lifetime'],
            'facing_camera_mode': 'emitter_transform_xz',
            'uv': {'texture_width': 128, 'texture_height': 128,
                   'flipbook': {'base_UV': [56, 0], 'size_UV': [8, 8], 'step_UV': [-8, 0], 'frames_per_second': 6, 'max_frame': 8, 'stretch_to_lifetime': True, 'loop': False}}},
        'minecraft:particle_appearance_tinting': {'color': [0.93, 0.97, 1.0, '0.75 * (1 - v.particle_age / v.particle_lifetime)']},
        'minecraft:particle_appearance_lighting': {}})
    spray = particle('spray', sheet, 'particles_alpha', {
        # a few drops thrown up off the bow at speed
        'minecraft:emitter_rate_instant': {'num_particles': 'math.random_integer(3, 6)'},
        'minecraft:emitter_lifetime_once': {'active_time': 0.05},
        'minecraft:emitter_shape_point': {'direction': ['math.random(-1, 1)', 'math.random(0.9, 1.6)', 'math.random(-1, 1)']},
        'minecraft:particle_initial_speed': 'math.random(1.8, 3.2)',
        'minecraft:particle_lifetime_expression': {'max_lifetime': 'math.random(0.35, 0.6)'},
        'minecraft:particle_motion_dynamic': {'linear_acceleration': [0, -12, 0]},
        'minecraft:particle_appearance_billboard': {
            'size': ['0.05 + 0.04 * v.particle_random_1', '0.05 + 0.04 * v.particle_random_1'], 'facing_camera_mode': 'rotate_xyz',
            'uv': {'texture_width': 128, 'texture_height': 128, 'uv': ['24 + math.floor(v.particle_random_2 * 4) * 8', 8], 'uv_size': [8, 8]}},
        'minecraft:particle_appearance_tinting': {'color': [0.8, 0.92, 1.0, 0.9]},
        'minecraft:particle_appearance_lighting': {}})
    fish = particle('net_fish', 'textures/particle/kfv_fish_jump', 'particles_alpha', {
        # now and then a small fish flips up in the net, a silver flash
        'minecraft:emitter_rate_instant': {'num_particles': 'math.random(0, 1) < 0.55 ? 1 : 0'},
        'minecraft:emitter_lifetime_once': {'active_time': 0.05},
        'minecraft:emitter_shape_box': {'half_dimensions': [0.25, 0.05, 0.25], 'surface_only': False,
                                        'direction': ['math.random(-0.3, 0.3)', 1, 'math.random(-0.3, 0.3)']},
        'minecraft:particle_initial_speed': 'math.random(1.6, 2.6)',
        'minecraft:particle_lifetime_expression': {'max_lifetime': 0.4},
        'minecraft:particle_motion_dynamic': {'linear_acceleration': [0, -14, 0]},
        'minecraft:particle_initial_spin': {'rotation': 'math.random(-30, 30)', 'rotation_rate': 'math.random(-600, 600)'},
        'minecraft:particle_appearance_billboard': {
            'size': [0.18, 0.09], 'facing_camera_mode': 'rotate_xyz',
            'uv': {'texture_width': 8, 'texture_height': 4, 'uv': [0, 0], 'uv_size': [8, 4]}},
        'minecraft:particle_appearance_tinting': {'color': ['0.85 + 0.15 * math.sin(v.particle_age * 1800)', '0.9 + 0.1 * math.sin(v.particle_age * 1800)', 1.0, 1.0]},
        'minecraft:particle_appearance_lighting': {}})
    return {'wake': wake, 'spray': spray, 'net_fish': fish}


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
                        'visible_bounds_width': 6, 'visible_bounds_height': 3, 'visible_bounds_offset': [0, 0.5, 0]},
        'bones': bones}]})
    init, pre = scripts()
    anims, ctls, parts = animations(), controllers(), particles()
    trawl = f"q.property('{NS}:trawl') == 1"
    write_json(os.path.join(RP, 'entity', 'fishing_skiff.entity.json'), {'format_version': '1.10.0', 'minecraft:client_entity': {'description': {
        'identifier': ID, 'materials': {'default': 'entity_alphatest'}, 'textures': {'default': 'textures/entity/kfv_fishing_skiff'},
        'geometry': {'default': f'geometry.{NS}.fishing_skiff'},
        'animations': {**{k.split('.')[-1]: k for k in anims}, **{k.split('.')[-1] + '_ctrl': k for k in ctls}},
        'particle_effects': {k: v['particle_effect']['description']['identifier'] for k, v in parts.items()},
        'scripts': {'initialize': init, 'pre_animation': pre,
                    'animate': ['motion', {'trawl': trawl}, 'wake_ctrl', 'spray_ctrl', 'net_fish_ctrl']},
        'render_controllers': [f'controller.render.{NS}.fishing_skiff']}}})
    write_json(os.path.join(RP, 'animations', 'kfv_fishing_skiff.animation.json'), {'format_version': '1.8.0', 'animations': anims})
    write_json(os.path.join(RP, 'animation_controllers', 'kfv_fishing_skiff.animation_controllers.json'),
               {'format_version': '1.10.0', 'animation_controllers': ctls})
    for k, v in parts.items():
        write_json(os.path.join(RP, 'particles', f'kfv_boat_{k}.json'), v)
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
                                   'family_types': ['player'], 'seats': [{'position': [0, -0.2, 0], 'min_rider_count': 0, 'max_rider_count': 1,
                                              'lock_rider_rotation': 90, 'rotate_rider_by': -90 * BOW}]},
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
