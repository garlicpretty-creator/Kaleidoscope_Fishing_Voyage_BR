"""Touch-ups for the 1.4.0 item icons generated with Retro Diffusion (tools/icon_candidates/).

  python tools/touchup_rd_icons.py

The generated icons have no dark outline, unlike the rest of the pack, and a few reach the edge of the 16x16
square. For each icon below this script starts again from the untouched candidate, so it can be run again:
  1. clears the outermost column / row where the drawing touches the edge (one pixel of margin, like the others)
  2. darkens the silhouette's edge pixels into an outline (warm, a little hue-shifted, as in the Cookery icons)
  3. applies the recolouring in RECOLOR and the hand fixes in FIX
and writes textures/items/kfv_<name>.png with its RTX maps. The feast icons are not here: they are 64x64 renders
of their 3D models (tools/icons_from_models.py --hires 64).
"""
import os

from PIL import Image

import pbr

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'icon_candidates')
DST = os.path.join(os.path.dirname(HERE), 'Kaleidoscope Fishing Voyage [RP]', 'textures', 'items')

ICONS = ['shrimp_meat', 'shrimp_shell', 'crab_meat', 'crab_roe', 'crab_shell', 'jellyfish_skin', 'emperor_tuna_fin',
         'frostlake_scale', 'whisker_line', 'emperor_bone_hook', 'dragon_scale_bobber', 'frost_scale_bobber',
         'stir_fried_shrimp', 'crab_congee', 'shrimp_noodle_soup', 'crab_roe_rice', 'jellyfish_salad']


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


# name -> {(x, y): colour or None (clear)}, applied after the outline
FIX = {}


def _pale_shrimp(r, g, b):
    """Stir-fried Shrimp is a light dish: its shrimp pale pink, so it does not read as the red Salt and Pepper Shrimp."""
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if (h <= 0.09 or h >= 0.95) and s > 0.4 and v > 0.5:
        return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(0.0 if h >= 0.95 else h * 0.6, s * 0.5, min(1.0, v * 1.1)))
    return (r, g, b)


# name -> function (r, g, b) -> (r, g, b), applied to the drawing before the outline
RECOLOR = {'stir_fried_shrimp': _pale_shrimp}


def outline(im):
    px = im.load()
    solid = {(x, y) for y in range(16) for x in range(16) if px[x, y][3]}
    for (x, y) in solid:
        if any((x + dx, y + dy) not in solid for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            r, g, b, _ = px[x, y]
            px[x, y] = (int(r * 0.34) + 14, int(g * 0.28) + 8, int(b * 0.26) + 6, 255)
    return im


def margin(im):
    """Clear the outermost column / row on any side the drawing touches."""
    px = im.load()
    bb = im.getbbox()
    if not bb:
        return im
    cols = ([0] if bb[0] == 0 else []) + ([15] if bb[2] == 16 else [])
    rows = ([0] if bb[1] == 0 else []) + ([15] if bb[3] == 16 else [])
    for x in cols:
        for y in range(16):
            px[x, y] = (0, 0, 0, 0)
    for y in rows:
        for x in range(16):
            px[x, y] = (0, 0, 0, 0)
    return im


def main():
    for name in ICONS:
        im = Image.open(os.path.join(SRC, name + '.png')).convert('RGBA')
        assert im.size == (16, 16), (name, im.size)
        px = im.load()
        for y in range(16):                              # hard alpha: a pixel is there or not
            for x in range(16):
                r, g, b, a = px[x, y]
                px[x, y] = (r, g, b, 255) if a >= 128 else (0, 0, 0, 0)
        if name in RECOLOR:
            for y in range(16):
                for x in range(16):
                    r, g, b, a = px[x, y]
                    if a:
                        px[x, y] = RECOLOR[name](r, g, b) + (255,)
        outline(margin(im))
        for (x, y), colour in FIX.get(name, {}).items():
            im.putpixel((x, y), rgb(colour) if colour else (0, 0, 0, 0))
        out = os.path.join(DST, f'kfv_{name}.png')
        im.save(out)
        pbr.refresh(out)
    print('touched up', len(ICONS), 'icons')


if __name__ == '__main__':
    main()
