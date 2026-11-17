"""Tide Clock (潮汐鐘): the held model, the wall model and their texture; with --icon, the 16x16 item icon too.

  python tools/gen_tide_clock.py                    model and texture
  python tools/gen_tide_clock.py --icon <picture>   also the item icon, made from the author's picture

Writes models/entity/tide_clock.geo.json, models/blocks/tide_clock.geo.json and textures/entity/kfv_tide_clock.png;
--icon writes textures/items/kfv_tide_clock.png. Each texture gets its texture set and RTX maps. Safe to run again.

The clock is a brass disc held flat in the hand, read from above with "forward" at the top:
  hand      one turn per tide (12000 ticks). It points at the blue arc while the tide is high.
  blue arc  the far rim, 45 degrees either side: high tide lasts 1500 ticks each side of its centre.
  moon      four strips near the low mark, lit by the moon phase (0 full .. 4 new .. 7 waxing gibbous).
Everything that carries meaning is a cube, not a painted mark, so nothing depends on how a face's texture is
mirrored. The turning and the moon are Molang in animations/tide_clock.animation.json and
render_controllers/kfv_tide_clock.render_controllers.json; they follow fishing/water.js tideState().
The hand turns clockwise (a negative Y rotation: Bedrock's Y angle runs the other way round).

On a wall (1.5.0) the same dial is a block, 1.5 times the size, with the blue arc at the top. A block cannot run
Molang on the time of day, so the hand is one of 16 bones, 22.5 degrees apart, and blocks/tideClock.js shows the
right one through a block state; the moon strips are bones too.
"""
import json, os, sys
from PIL import Image

import pbr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')

# 4x4 colour swatches on a 16x16 sheet: name -> (column, row, colour)
SWATCH = {
    'brass': (0, 0, '#c9a24a'), 'brass_dark': (1, 0, '#8a6a2a'), 'face': (2, 0, '#efe4c8'), 'high': (3, 0, '#3f7fc4'),
    'low': (0, 1, '#d8c08a'), 'hand': (1, 1, '#b02a22'), 'night': (2, 1, '#1e2748'), 'moon': (3, 1, '#f6eaa6'),
    'pin': (0, 2, '#2e1c10'),
}
CX, CZ, Y0 = -6, 1, 12          # centre of the disc and its underside, in the hand (as the held Bamboo Hat)


def rgba(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def cube(x0, x1, y0, y1, z0, z1, top, side=None):
    """A box given by its bounds relative to the disc centre; x grows to the holder's left, z toward them."""
    def face(name):
        c, r, _ = SWATCH[name]
        return {'uv': [c * 4 + 1, r * 4 + 1], 'uv_size': [2, 2]}
    side = side or top
    return {'origin': [round(CX + x0, 3), round(Y0 + y0, 3), round(CZ + z0, 3)],
            'size': [round(x1 - x0, 3), round(y1 - y0, 3), round(z1 - z0, 3)],
            'uv': {'up': face(top), 'down': face(side), 'north': face(side), 'south': face(side),
                   'east': face(side), 'west': face(side)}}


def geometry():
    skeleton = [
        {'name': 'root', 'pivot': [0, 0, 0]},
        {'name': 'waist', 'parent': 'root', 'pivot': [0, 12, 0]},
        {'name': 'body', 'parent': 'waist', 'pivot': [0, 24, 0]},
        {'name': 'rightArm', 'parent': 'body', 'pivot': [-5, 22, 0]},
        {'name': 'rightItem', 'parent': 'rightArm', 'pivot': [-6, 15, 1]},
    ]
    case = [
        cube(-3.5, 3.5, 0, 1.0, -3.5, 3.5, 'brass', 'brass_dark'),          # body
        cube(-4.0, 4.0, 0, 0.9, -2.5, 2.5, 'brass', 'brass_dark'),          # rounded out left and right
        cube(-2.5, 2.5, 0, 0.9, -4.0, 4.0, 'brass', 'brass_dark'),          # and front and back
        cube(-3.0, 3.0, 1.0, 1.1, -3.0, 3.0, 'face'),
        # high-tide arc on the far rim: 45 degrees either side of straight ahead
        cube(-1.5, 1.5, 1.1, 1.16, -3.0, -2.4, 'high'),
        cube(1.5, 2.4, 1.1, 1.16, -2.7, -2.0, 'high'),
        cube(-2.4, -1.5, 1.1, 1.16, -2.7, -2.0, 'high'),
        cube(-0.4, 0.4, 1.1, 1.16, 2.5, 3.0, 'low'),                        # low-tide mark, nearest the holder
        cube(-1.0, 1.0, 1.1, 1.13, 0.6, 2.2, 'night'),                      # the moon's window
    ]
    hand = [cube(-0.2, 0.2, 1.2, 1.28, -2.5, 0.3, 'hand'), cube(-0.35, 0.35, 1.2, 1.32, -0.35, 0.35, 'pin')]
    # moon strips, from the holder's left (+x) to right: l2 l1 r1 r2; the outer two are shorter, for a round moon
    strips = {'moon_l2': (0.5, 1.0, 0.9, 1.9), 'moon_l1': (0.0, 0.5, 0.6, 2.2),
              'moon_r1': (-0.5, 0.0, 0.6, 2.2), 'moon_r2': (-1.0, -0.5, 0.9, 1.9)}
    bones = skeleton + [
        {'name': 'tide_clock', 'parent': 'rightItem', 'pivot': [CX, Y0, CZ], 'cubes': case},
        {'name': 'tide_hand', 'parent': 'tide_clock', 'pivot': [CX, Y0 + 1.2, CZ], 'cubes': hand},
    ] + [{'name': n, 'parent': 'tide_clock', 'pivot': [CX, Y0 + 1.13, CZ + 1.4],
          'cubes': [cube(x0, x1, 1.13, 1.17, z0, z1, 'moon')]} for n, (x0, x1, z0, z1) in strips.items()]
    return {'format_version': '1.16.0', 'minecraft:geometry': [{
        'description': {'identifier': 'geometry.kaleidoscope_fishing.tide_clock', 'texture_width': 16,
                        'texture_height': 16, 'visible_bounds_width': 3, 'visible_bounds_height': 3,
                        'visible_bounds_offset': [0, 1.5, 0]},
        'bones': bones}]}


WALL = 1.5                      # the wall dial is this many times the held one
WALL_Y, WALL_Z = 8, 8           # its centre's height, and the wall it hangs on (the block's south side)


def wall_cube(x0, x1, y0, y1, z0, z1, top, side=None):
    """The held dial's box, stood up against the wall: its far rim is the top, its upper side faces the room
    (north), and the holder's left is still on the viewer's left."""
    def face(name):
        c, r, _ = SWATCH[name]
        return {'uv': [c * 4 + 1, r * 4 + 1], 'uv_size': [2, 2]}
    side = side or top
    X0, X1 = x0 * WALL, x1 * WALL
    Y0_, Y1_ = WALL_Y - z1 * WALL, WALL_Y - z0 * WALL
    Z0, Z1 = WALL_Z - y1 * WALL, WALL_Z - y0 * WALL
    return {'origin': [round(X0, 3), round(Y0_, 3), round(Z0, 3)], 'size': [round(X1 - X0, 3), round(Y1_ - Y0_, 3), round(Z1 - Z0, 3)],
            'uv': {'north': face(top), 'south': face(side), 'up': face(side), 'down': face(side), 'east': face(side), 'west': face(side)}}


HAND_STEPS = 16


def wall_geometry():
    case = [
        wall_cube(-3.5, 3.5, 0, 1.0, -3.5, 3.5, 'brass', 'brass_dark'),
        wall_cube(-4.0, 4.0, 0, 0.9, -2.5, 2.5, 'brass', 'brass_dark'),
        wall_cube(-2.5, 2.5, 0, 0.9, -4.0, 4.0, 'brass', 'brass_dark'),
        wall_cube(-3.0, 3.0, 1.0, 1.1, -3.0, 3.0, 'face'),
        wall_cube(-1.5, 1.5, 1.1, 1.16, -3.0, -2.4, 'high'),
        wall_cube(1.5, 2.4, 1.1, 1.16, -2.7, -2.0, 'high'),
        wall_cube(-2.4, -1.5, 1.1, 1.16, -2.7, -2.0, 'high'),
        wall_cube(-0.4, 0.4, 1.1, 1.16, 2.5, 3.0, 'low'),
        wall_cube(-1.0, 1.0, 1.1, 1.13, 0.6, 2.2, 'night'),
        wall_cube(-0.35, 0.35, 1.2, 1.32, -0.35, 0.35, 'pin'),
    ]
    centre = [0, WALL_Y, round(WALL_Z - 1.2 * WALL, 3)]
    bones = [{'name': 'root', 'pivot': [0, 0, 0]}, {'name': 'dial', 'parent': 'root', 'pivot': [0, WALL_Y, WALL_Z], 'cubes': case}]
    for i in range(HAND_STEPS):
        # a positive Z rotation turns the hand clockwise for someone facing the dial
        bones.append({'name': f'hand_{i}', 'parent': 'dial', 'pivot': centre, 'rotation': [0, 0, round(i * 360 / HAND_STEPS, 3)],
                      'cubes': [wall_cube(-0.2, 0.2, 1.2, 1.28, -2.5, 0.3, 'hand')]})
    strips = {'moon_l2': (0.5, 1.0, 0.9, 1.9), 'moon_l1': (0.0, 0.5, 0.6, 2.2),
              'moon_r1': (-0.5, 0.0, 0.6, 2.2), 'moon_r2': (-1.0, -0.5, 0.9, 1.9)}
    for n, (x0, x1, z0, z1) in strips.items():
        bones.append({'name': n, 'parent': 'dial', 'pivot': [0, WALL_Y, WALL_Z], 'cubes': [wall_cube(x0, x1, 1.13, 1.17, z0, z1, 'moon')]})
    return {'format_version': '1.12.0', 'minecraft:geometry': [{
        'description': {'identifier': 'geometry.kaleidoscope_fishing.wall_tide_clock', 'texture_width': 16, 'texture_height': 16,
                        'visible_bounds_width': 2, 'visible_bounds_height': 2, 'visible_bounds_offset': [0, 0.5, 0]},
        'bones': bones}]}


def sheet():
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for c, r, colour in SWATCH.values():
        for y in range(4):
            for x in range(4):
                im.putpixel((c * 4 + x, r * 4 + y), rgba(colour))
    return im


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


def main():
    geo = os.path.join(RP, 'models', 'entity', 'tide_clock.geo.json')
    with open(geo, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(geometry(), f, indent=2)
        f.write('\n')
    tex = os.path.join(RP, 'textures', 'entity', 'kfv_tide_clock.png')
    sheet().save(tex)
    texture_set(tex, ('heightmap', '_height'))
    wall = os.path.join(RP, 'models', 'blocks', 'tide_clock.geo.json')
    with open(wall, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(wall_geometry(), f, indent=2)
        f.write('\n')
    print('wrote', geo, wall, tex, sep='\n  ')
    if len(sys.argv) == 3 and sys.argv[1] == '--icon':
        ico = os.path.join(RP, 'textures', 'items', 'kfv_tide_clock.png')
        icon_from(sys.argv[2]).save(ico)
        texture_set(ico, ('normal', '_normal'))
        print('  ' + ico)


if __name__ == '__main__':
    main()
