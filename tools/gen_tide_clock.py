"""Tide Clock (潮汐鐘): the held model, the wall model and their texture; with --icon, the 16x16 item icon too.

  python tools/gen_tide_clock.py                    model and texture
  python tools/gen_tide_clock.py --icon <picture>   also the item icon, made from the author's picture

Writes models/entity/tide_clock.geo.json, models/blocks/tide_clock.geo.json and textures/entity/kfv_tide_clock.png;
--icon writes textures/items/kfv_tide_clock.png. Each texture gets its texture set and RTX maps. Safe to run again.

The clock is a brass disc held flat in the hand, read from above with "forward" at the top:
  hand      one turn per tide (12000 ticks). It points at the blue arc while the tide is high.
  blue arc  the far rim, 45 degrees either side: high tide lasts 1500 ticks each side of its centre.
  moon      four strips in a dark window near the low mark, lit by the moon phase (0 full .. 4 new .. 7 waxing
            gibbous).
Everything that carries meaning is a cube, not a painted mark, so nothing depends on how a face's texture is
mirrored (the painted ticks and the bezel's engraving are symmetric). The turning and the moon are Molang in
animations/tide_clock.animation.json and render_controllers/kfv_tide_clock.render_controllers.json; they follow
fishing/water.js tideState(). The hand turns clockwise, which in game is a POSITIVE Y rotation in the animation
(checked in game 2026-11-17: with the old negative sign the held hand ran anticlockwise, the mirror of the wall clock;
tools/render_models.py draws Y the other way round, so do not judge the held hand by its preview).

On a wall (1.5.0) the same dial is a block, 1.5 times the size, with the blue arc at the top. A block cannot run
Molang on the time of day, so the hand is one of 16 bones, 22.5 degrees apart, and blocks/tideClock.js shows the
right one through a block state; the moon strips are bones too.

The look (polished in 1.5.0): a turned bronze back plate, a brass case with an engraved groove round its side, a
knurled bezel engraved with 16 notches, a cream dial with 16 painted ticks (the wall hand's 16 positions), the
blue high-tide arc in enamel with wave crests, a sand-coloured low-tide mark, a navy moon window with pale moon
strips, a red arrow hand with a counterweight on a brass boss, two glints on the glass, and a winding crown with
a hanging bail at the top. The dial is drawn once, in dial units (the wall clock's pixels: radius 6), and placed
twice: on the wall at 1 texture pixel per unit, in the hand at 2/3 the size with the same pixels (1.5 per unit).
The texture is painted in code (tools/facepaint.py): every face has its own pixels, nothing is stretched.
"""
import json, math, os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr
from facepaint import Sheet, Part, rgba, mix, shade, hash01

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')

CX, CZ, Y0 = -6, 1, 12          # centre of the disc and its underside, in the hand (as the held Bamboo Hat)
K = 2 / 3                       # held size per dial unit
WALL = 1.5                      # the wall dial is this many times the held one (1 dial unit = 1 block pixel)
WALL_Y, WALL_Z = 8, 8           # its centre's height, and the wall it hangs on (the block's south side)
HAND_STEPS = 16

# Dial units: a across (+a = the holder's left; model +x on the wall), b along (+b = the far rim, the top
# on the wall), h up from the back plate (towards the viewer). Heights:
H_BACK, H_BODY, H_BEZEL = 1.0, 2.0, 3.0      # tops of the back plate, the case, the bezel
H_FACE, H_MARK, H_WIN, H_MOON = 2.2, 2.35, 2.3, 2.4
H_HAND0, H_HAND1, H_PIN, H_GLASS0, H_GLASS1 = 2.5, 2.7, 2.8, 2.85, 2.95
R_CASE, R_BACK, R_FACE = 6.0, 5.5, 4.6

# ------------------------------------------------------------------ palette and shaders (on dial coordinates)
BRASS, BRASS_HI, BRASS_LO, BRASS_DK = '#d2a84e', '#f4d98a', '#9c7430', '#6a4a1c'
BRONZE, BRONZE_DK = '#8a5a2c', '#5a3818'
CREAM, CREAM_DK, INK, TICK = '#eedfba', '#d4c094', '#5a3a22', '#8a6440'
SEA, SEA_HI, SEA_DK = '#3f7fc4', '#8fc4ee', '#2a5590'
SAND, NIGHT, NIGHT_HI, MOON, MOON_DK = '#d8b874', '#1e2748', '#2e3a66', '#f6eaa6', '#d6c47a'
HAND, HAND_DK, HAND_HI = '#b02a22', '#6e1410', '#e05a44'
GLINT = '#ffffff'
M_BRASS, M_DULL, M_PAINT, M_ENAMEL, M_GLASS = (200, 0, 70), (150, 0, 120), (0, 0, 210), (0, 0, 90), (0, 0, 20)


def polar(p):
    a, b = p[0], p[1]
    return math.hypot(a, b), math.degrees(math.atan2(a, b))      # angle 0 = towards the far rim, symmetric in a


def near_step(ang, step, tol):
    d = (ang + 3600) % step
    return min(d, step - d) < tol


def s_back(p, n):
    """Bronze back plate: darker, with a turned groove round its side."""
    if n[2] < -0.5:
        return (BRONZE_DK, M_DULL)
    if abs(n[2]) < 0.5 and 0.35 < p[2] < 0.65:
        return (BRONZE_DK, M_DULL)
    return (shade(BRONZE, 0.95 + 0.1 * hash01(p[0] * 2, p[1] * 2)), M_DULL)


def s_case(p, n):
    """Brass case: polished side with one engraved line, lighter towards the top."""
    if abs(n[2]) < 0.5:
        if 1.4 < p[2] < 1.6:
            return (BRASS_DK, M_BRASS)
        return (mix(BRASS_LO, BRASS, (p[2] - 1.0)), M_BRASS)
    return (BRASS, M_BRASS)


def s_bezel(p, n):
    """Bezel: knurled side, a top engraved with 16 notches (and 4 bigger ones at the quarters), a bright inner edge."""
    r, ang = polar(p)
    if abs(n[2]) < 0.5:                                         # side: knurling, light and dark alternating
        if r > R_FACE + 0.3:                                     # outer side
            k = int(math.floor((ang + 360) / 11.25)) % 2
            return (BRASS_HI if k and p[2] > 2.5 else BRASS if k else BRASS_LO, M_BRASS)
        return (BRASS_LO, M_BRASS)                               # inner wall, in the shade of the rim
    if n[2] > 0.5:
        if r < R_FACE + 0.6:
            return (BRASS_HI, M_BRASS)                           # the polished inner edge
        if near_step(ang, 22.5, 3.5) and 5.1 < r < 5.6:
            return (BRASS_LO, M_BRASS)
        return (mix(BRASS, BRASS_HI, 0.35 * hash01(p[0] * 3, p[1] * 3)), M_BRASS)
    return (BRASS_LO, M_BRASS)


def s_face(p, n):
    """Cream dial: darker towards the rim, 16 ticks (the wall hand's 16 positions), a fine ring inside them."""
    if n[2] < 0.5:
        return (CREAM_DK, M_PAINT)
    r, ang = polar(p)
    if r > 3.9 and near_step(ang, 22.5, 6.5):
        return (TICK, M_PAINT)
    if 2.9 < r < 3.4:
        return (CREAM_DK, M_PAINT)
    return (mix(CREAM, CREAM_DK, max(0.0, r - 3.0) / 3 + 0.12 * hash01(p[0], p[1])), M_PAINT)


def s_arc(p, n):
    """Blue enamel arc: deeper blue outside, a row of pale wave crests along the middle."""
    r, ang = polar(p)
    if n[2] < 0.5:
        return (SEA_DK, M_ENAMEL)
    if 3.75 < r < 4.1 and int(math.floor((ang + 360) / 10)) % 2 == 0:
        return (SEA_HI, M_ENAMEL)
    return (mix(SEA, SEA_DK, (r - 3.4) / 1.4), M_ENAMEL)


def s_low(p, n):
    return (SAND if n[2] > 0.5 else shade(SAND, 0.8), M_ENAMEL)


def s_window(p, n):
    """The moon's window: night blue, a few stars; lighter at its rim."""
    if n[2] < 0.5:
        return (NIGHT, M_PAINT)
    if hash01(p[0] * 2 + 3, p[1] * 2) > 0.93:
        return (NIGHT_HI, M_PAINT)
    return (NIGHT, M_PAINT)


def s_moon(p, n):
    if n[2] < 0.5:
        return (shade(MOON, 0.9), M_PAINT)
    return (MOON_DK if hash01(p[0] * 2 + 7, p[1] * 2) > 0.8 else MOON, M_PAINT)


def s_hand(p, n):
    """Red hand: a bright ridge down its middle, dark edges."""
    if n[2] < 0.5:
        return (HAND_DK, M_ENAMEL)
    if abs(p[0]) < 0.15 and p[1] > -0.8:
        return (HAND_HI, M_ENAMEL)
    return (HAND, M_ENAMEL)


def s_pin(p, n):
    if n[2] > 0.5:
        return (BRASS_HI if abs(p[0]) < 0.3 and abs(p[1]) < 0.3 else BRASS, M_BRASS)
    return (BRASS_LO, M_BRASS)


def s_glass(p, n):
    """Clear glass (holes, the alpha test drops them) with two glints across the upper left."""
    if n[2] < 0.5:
        return None
    a, b = -p[0], p[1]                                           # the viewer's upper left on the wall
    if (abs(a + b - 4) < 0.2 and 0 < a < 4 and 0 < b < 4) or (abs(a + b - 2) < 0.2 and 0 < a < 2 and 0 < b < 2):
        return (GLINT, M_GLASS)
    return None


def s_crown(p, n):
    """Winding crown: ridged brass."""
    if abs(n[1]) > 0.5:
        return (BRASS_HI if n[1] > 0 else BRASS_LO, M_BRASS)
    k = int(math.floor(p[2] * 2 + (p[0] + 9) * 2)) % 2
    return (BRASS if k else BRASS_LO, M_BRASS)


def s_bail(p, n):
    return (BRASS_HI if n[1] > 0.5 or n[2] > 0.5 else BRASS_LO, M_BRASS)


# ------------------------------------------------------------------ the dial, in dial units
def disc(r_out, r_in=0.0, keep=None):
    """Rows of a ring on the unit grid (cells whose centre lies between r_in and r_out, and keep(a, b, r, ang)),
    each row's runs merged, and equal rows merged: [(a0, a1, b0, b1)]."""
    rows = []
    n = int(math.ceil(r_out))
    for j in range(-n, n):
        runs, start = [], None
        for i in range(-n, n + 1):
            ok = False
            if i < n:
                a, b = i + 0.5, j + 0.5
                r = math.hypot(a, b)
                ok = r_in <= r < r_out and (keep is None or keep(a, b, r, math.degrees(math.atan2(a, b))))
            if ok and start is None:
                start = i
            elif not ok and start is not None:
                runs.append((start, i))
                start = None
        rows.append((j, tuple(runs)))
    out, k = [], 0
    while k < len(rows):
        j, runs = rows[k]
        m = k
        while m + 1 < len(rows) and rows[m + 1][1] == runs:
            m += 1
        out += [(a0, a1, j, rows[m][0] + 1) for a0, a1 in runs]
        k = m + 1
    return out


def dial_case():
    """(lo, hi, shader) boxes in dial units of everything that does not move."""
    boxes = []
    for a0, a1, b0, b1 in disc(R_BACK):
        boxes.append(((a0, b0, 0), (a1, b1, H_BACK), s_back))
    for a0, a1, b0, b1 in disc(R_CASE):
        boxes.append(((a0, b0, H_BACK), (a1, b1, H_BODY), s_case))
    for a0, a1, b0, b1 in disc(R_CASE, R_FACE):
        boxes.append(((a0, b0, H_BODY), (a1, b1, H_BEZEL), s_bezel))
    for a0, a1, b0, b1 in disc(R_FACE):
        boxes.append(((a0, b0, H_BODY), (a1, b1, H_FACE), s_face))
    # the high-tide arc: 45 degrees either side of the far rim
    for a0, a1, b0, b1 in disc(R_FACE, 3.3, lambda a, b, r, ang: abs(ang) <= 46):
        boxes.append(((a0, b0, H_FACE), (a1, b1, H_MARK), s_arc))
    # the low-tide mark, nearest the holder (the bottom on a wall)
    boxes.append(((-0.5, -R_FACE + 0.1, H_FACE), (0.5, -3.7, H_MARK), s_low))
    # the moon's window, rounded at its corners
    for a0, a1, b0, b1 in ((-1.5, 1.5, -3.5, -3.0), (-2.25, 2.25, -3.0, -1.0), (-1.5, 1.5, -1.0, -0.6)):
        boxes.append(((a0, b0, H_FACE), (a1, b1, H_WIN), s_window))
    # the glass, a winding crown and a bail to hang it by, at the far rim
    boxes.append(((-3.0, -3.0, H_GLASS0), (3.0, 3.0, H_GLASS1), s_glass))
    boxes.append(((-0.5, 5.7, 0.9), (0.5, 6.3, 2.1), s_crown))
    boxes.append(((-1.0, 6.3, 0.5), (1.0, 7.3, 2.5), s_crown))
    boxes.append(((1.25, 6.4, 1.25), (1.75, 8.0, 1.75), s_bail))
    boxes.append(((-1.75, 6.4, 1.25), (-1.25, 8.0, 1.75), s_bail))
    boxes.append(((-1.75, 8.0, 1.25), (1.75, 8.5, 1.75), s_bail))
    return boxes


PIN = ((-0.6, -0.6, H_FACE), (0.6, 0.6, H_PIN), s_pin)


def dial_hand():
    """The hand pointing at the far rim: arrow head, shaft, a round counterweight behind the centre."""
    s = s_hand
    return [((-0.3, -1.0, H_HAND0), (0.3, 3.0, H_HAND1), s),
            ((-0.8, 3.0, H_HAND0), (0.8, 3.5, H_HAND1), s),
            ((-0.55, 3.5, H_HAND0), (0.55, 4.0, H_HAND1), s),
            ((-0.3, 4.0, H_HAND0), (0.3, 4.5, H_HAND1), s),
            ((-0.55, -1.7, H_HAND0), (0.55, -1.0, H_HAND1), s)]


# moon strips, from the holder's left (+a) to right: l2 l1 r1 r2; the outer two are shorter, for a round moon
STRIPS = {'moon_l2': (0.75, 1.5, -2.6, -1.4), 'moon_l1': (0.0, 0.75, -2.95, -1.05),
          'moon_r1': (-0.75, 0.0, -2.95, -1.05), 'moon_r2': (-1.5, -0.75, -2.6, -1.4)}


# ------------------------------------------------------------------ placing the dial
def held_part(sheet):
    to_src = lambda p: [(p[0] - CX) / K, -(p[2] - CZ) / K, (p[1] - Y0) / K]      # noqa: E731
    to_n = lambda n: (n[0], -n[2], n[1])                                         # noqa: E731
    part = Part(sheet, density=1 / K, to_src=to_src, to_src_n=to_n)

    def box(lo, hi, shader):
        return part.box([CX + lo[0] * K, Y0 + lo[2] * K, CZ - hi[1] * K], [CX + hi[0] * K, Y0 + hi[2] * K, CZ - lo[1] * K], shader)
    return box


def wall_part(sheet):
    to_src = lambda p: [p[0], p[1] - WALL_Y, WALL_Z - p[2]]                      # noqa: E731
    to_n = lambda n: (n[0], n[1], -n[2])                                          # noqa: E731
    part = Part(sheet, density=1, to_src=to_src, to_src_n=to_n)

    def box(lo, hi, shader):
        return part.box([lo[0], WALL_Y + lo[1], WALL_Z - hi[2]], [hi[0], WALL_Y + hi[1], WALL_Z - lo[2]], shader)
    return box


def geometry(sheet):
    box = held_part(sheet)
    skeleton = [
        {'name': 'root', 'pivot': [0, 0, 0]},
        {'name': 'waist', 'parent': 'root', 'pivot': [0, 12, 0]},
        {'name': 'body', 'parent': 'waist', 'pivot': [0, 24, 0]},
        {'name': 'rightArm', 'parent': 'body', 'pivot': [-5, 22, 0]},
        {'name': 'rightItem', 'parent': 'rightArm', 'pivot': [-6, 15, 1]},
    ]
    bones = skeleton + [
        {'name': 'tide_clock', 'parent': 'rightItem', 'pivot': [CX, Y0, CZ], 'cubes': [box(*c) for c in dial_case()]},
        {'name': 'tide_hand', 'parent': 'tide_clock', 'pivot': [CX, Y0 + 1.2, CZ], 'cubes': [box(*c) for c in dial_hand() + [PIN]]},
    ] + [{'name': n, 'parent': 'tide_clock', 'pivot': [CX, Y0 + 1.13, CZ + 1.4],
          'cubes': [box((a0, b0, H_WIN), (a1, b1, H_MOON), s_moon)]} for n, (a0, a1, b0, b1) in STRIPS.items()]
    return bones


def wall_geometry(sheet):
    box = wall_part(sheet)
    bones = [{'name': 'root', 'pivot': [0, 0, 0]},
             {'name': 'dial', 'parent': 'root', 'pivot': [0, WALL_Y, WALL_Z], 'cubes': [box(*c) for c in dial_case() + [PIN]]}]
    centre = [0, WALL_Y, round(WALL_Z - H_HAND0, 3)]
    for i in range(HAND_STEPS):
        # a positive Z rotation turns the hand clockwise for someone facing the dial
        bones.append({'name': f'hand_{i}', 'parent': 'dial', 'pivot': centre, 'rotation': [0, 0, round(i * 360 / HAND_STEPS, 3)],
                      'cubes': [box(*c) for c in dial_hand()]})
    for n, (a0, a1, b0, b1) in STRIPS.items():
        bones.append({'name': n, 'parent': 'dial', 'pivot': [0, WALL_Y, WALL_Z], 'cubes': [box((a0, b0, H_WIN), (a1, b1, H_MOON), s_moon)]})
    return bones


def icon_from(source):
    """The item icon from a large picture: reduced to 16x16 by nearest neighbour (no smoothing), then the
    near-white background that touches the border is made transparent (the dial's own white stays).
    TOUCH_UP is then painted over it."""
    im = Image.open(source).convert('RGB').resize((16, 16), Image.NEAREST).convert('RGBA')
    px = im.load()
    seen, todo = set(), [(x, y) for x in range(16) for y in range(16) if x in (0, 15) or y in (0, 15)]
    while todo:
        x, y = todo.pop()
        if (x, y) in seen or not (0 <= x < 16 and 0 <= y < 16) or min(px[x, y][:3]) < 235:
            continue
        seen.add((x, y))
        todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    for x, y in seen:
        px[x, y] = (0, 0, 0, 0)
    for y, row in TOUCH_UP.items():
        for x, ch in enumerate(row):
            if ch != '.':
                px[x, y] = rgba(TOUCH_PAL[ch])
    return im


# Hand touch-ups on the reduced icon ('.' keeps the pixel). At 16x16 the blue arc came out as three separate
# dots, the hand was three pixels long and the moon window showed two yellow dots. Now: the arc runs across
# the top of the dial and down its right side, the hand reaches the centre, and the window shows three moons on
# dark blue (the picture's dark brown window was lost against the brass rim below it).
TOUCH_UP = {
    4:  '.....BBBBBB.....',
    5:  '...........B....',
    7:  '...........b....',
    8:  '.......r........',
    10: '....DyDMMDyD....',
    11: '.....DDDDDD.....',
}
TOUCH_PAL = {'B': '#4471c6', 'b': '#355590', 'r': '#7f181c', 'D': '#1e2748', 'M': '#fff4a5', 'y': '#c9b45e'}


def texture_set(path, third):
    """third: ('normal' | 'heightmap', suffix): items carry a normal map, entity textures a height map."""
    name = os.path.basename(path)[:-4]
    ts = {'format_version': '1.16.100', 'minecraft:texture_set': {
        'color': name, 'metalness_emissive_roughness': name + '_mer', third[0]: name + third[1]}}
    with open(path[:-4] + '.texture_set.json', 'w', encoding='utf-8', newline='\n') as f:
        json.dump(ts, f, indent=2)
        f.write('\n')
    pbr.refresh(path)


def write_json(path, value):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2)
        f.write('\n')


def main():
    sheet = Sheet()
    held, wall = geometry(sheet), wall_geometry(sheet)
    tex = os.path.join(RP, 'textures', 'entity', 'kfv_tide_clock.png')
    sheet.save(tex)                               # fills in the UVs; the texture set (colour, MER, height) is kept
    tw, th = sheet.size
    geo = os.path.join(RP, 'models', 'entity', 'tide_clock.geo.json')
    write_json(geo, {'format_version': '1.16.0', 'minecraft:geometry': [{
        'description': {'identifier': 'geometry.kaleidoscope_fishing.tide_clock', 'texture_width': tw,
                        'texture_height': th, 'visible_bounds_width': 3, 'visible_bounds_height': 3,
                        'visible_bounds_offset': [0, 1.5, 0]},
        'bones': held}]})
    wall_geo = os.path.join(RP, 'models', 'blocks', 'tide_clock.geo.json')
    write_json(wall_geo, {'format_version': '1.12.0', 'minecraft:geometry': [{
        'description': {'identifier': 'geometry.kaleidoscope_fishing.wall_tide_clock', 'texture_width': tw, 'texture_height': th,
                        'visible_bounds_width': 2, 'visible_bounds_height': 2, 'visible_bounds_offset': [0, 0.5, 0]},
        'bones': wall}]})
    print('wrote', geo, wall_geo, f'{tex} ({tw}x{th})', sep='\n  ')
    if len(sys.argv) == 3 and sys.argv[1] == '--icon':
        ico = os.path.join(RP, 'textures', 'items', 'kfv_tide_clock.png')
        icon_from(sys.argv[2]).save(ico)
        texture_set(ico, ('normal', '_normal'))
        print('  ' + ico)


if __name__ == '__main__':
    main()
