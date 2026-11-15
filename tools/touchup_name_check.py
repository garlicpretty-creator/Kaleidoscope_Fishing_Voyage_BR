"""Icons fixed in the 1.4.0 name check, where an icon did not look like the thing it is named after.

  python tools/touchup_name_check.py

  live_shrimp          looked like a grey fish. Now the Shrimp icon in the grey, see-through colours of a living
                       shrimp (shrimp only turn pink when cooked).
  dried_shrimp         showed one big shrimp, while dried shrimp are tiny. Now a small handful of little curled
                       dried shrimp, drawn by hand.
  seasoned_*           Seasoned Sea Bass, Grouper and Sea Bream looked the same as the raw fish. Now they carry
                       slivers of ginger and green onion, ready for the steamer.
Each icon is rebuilt from a fixed source (the Shrimp icon; the raw fish's icon as committed before this script),
so it is safe to run again. (Cave Crayfish and Crab Meat were regenerated: touchup_rd_icons.py. The Fishing Boat
icon is a render of its 3D model: icons_from_models.py --hires 64.)
"""
import colorsys
import os
import subprocess

from PIL import Image

import pbr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ITEMS = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]', 'textures', 'items')
GINGER, ONION = (232, 200, 96, 255), (111, 168, 74, 255)
# the seasoned fish icons as they were before they got their garnish (the commit that added this script's parent)
SOURCE_REV = '8d3c664'


def live_shrimp():
    im = Image.open(os.path.join(ITEMS, 'kfv_shrimp.png')).convert('RGBA')
    px = im.load()
    for y in range(16):
        for x in range(16):
            r, g, b, a = px[x, y]
            if not a:
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if v < 0.3:                                  # outline: a cool dark grey instead of brown
                px[x, y] = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(0.55, 0.25, max(v, 0.18))) + (255,)
            else:                                        # body: grey-green, a little see-through looking
                px[x, y] = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(0.42, min(s, 0.6) * 0.3, min(1.0, v * 0.95))) + (255,)
    return im


DRIED = {'l': '#fcc896', 'o': '#f0904e', 'd': '#cc6234', 'e': '#3a1a0a'}
TINY = ['.lo..',          # one little dried shrimp: head with an eye, the body curling down to the tail
        'leoo.',
        'ooodo',
        '.oddd',
        '..dd.']
HANDFUL = [(2, 8, False), (6, 10, True), (10, 8, True), (5, 4, False), (8, 3, True)]   # x, y, mirrored


def _rgba(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def dried_shrimp():
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for ox, oy, flip in HANDFUL:
        for y, row in enumerate(TINY):
            for x, ch in enumerate(row):
                if ch != '.':
                    im.putpixel((ox + (4 - x if flip else x), oy + y), _rgba(DRIED[ch]))
    # outline only where the handful meets the outside (holes between the shrimp stay light)
    px = im.load()
    outside, todo = set(), [(x, y) for x in range(16) for y in range(16) if (x in (0, 15) or y in (0, 15))]
    while todo:
        x, y = todo.pop()
        if (x, y) in outside or not (0 <= x < 16 and 0 <= y < 16) or px[x, y][3]:
            continue
        outside.add((x, y))
        todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    edge = [(x, y) for y in range(16) for x in range(16) if px[x, y][3] and any(
        (x + dx, y + dy) in outside or not (0 <= x + dx < 16 and 0 <= y + dy < 16) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for xy in edge:
        im.putpixel(xy, _rgba('#5a2a14'))
    return im


def garnish(name):
    raw = subprocess.run(['git', 'show', f'{SOURCE_REV}:Kaleidoscope Fishing Voyage [RP]/textures/items/kfv_{name}.png'],
                         cwd=ROOT, capture_output=True, check=True).stdout
    import io
    im = Image.open(io.BytesIO(raw)).convert('RGBA')
    px = im.load()
    solid = {(x, y) for y in range(16) for x in range(16) if px[x, y][3]}
    inner = sorted((x, y) for (x, y) in solid
                   if all((x + dx, y + dy) in solid for dx in (-1, 0, 1) for dy in (-1, 0, 1)))
    xs = [x for x, _ in inner]
    lo, hi = min(xs) + (max(xs) - min(xs)) * 0.25, min(xs) + (max(xs) - min(xs)) * 0.8   # the body, not head or tail
    k = 0
    for (x, y) in inner:
        if lo <= x <= hi and (x + y) % 4 == 0:           # slivers laid across the fish
            px[x, y] = GINGER if k % 2 else ONION
            k += 1
    return im


def save(name, im):
    path = os.path.join(ITEMS, f'kfv_{name}.png')
    im.save(path)
    pbr.refresh(path)


def main():
    save('live_shrimp', live_shrimp())
    save('dried_shrimp', dried_shrimp())
    for name in ('seasoned_sea_bass', 'seasoned_grouper', 'seasoned_sea_bream'):
        save(name, garnish(name))
    print('fixed live_shrimp, dried_shrimp and the three seasoned fish')


if __name__ == '__main__':
    main()
