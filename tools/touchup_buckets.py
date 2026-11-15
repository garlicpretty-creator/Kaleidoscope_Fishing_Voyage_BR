"""Tell the three buckets apart (Salt Bucket, Fish Stock Bucket, Dashi Bucket).

  python tools/touchup_buckets.py

The three icons are the same bucket and differed only in the colour of a 6x3 patch: white, cream and amber, and the
first two were easy to mix up. Now the salt is heaped above the rim and speckled, the fish stock is a milky white
broth with green onion, and the dashi stays amber. Every pixel is set to a fixed colour, so it is safe to run again.
"""
import os

from PIL import Image

import pbr

ITEMS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'Kaleidoscope Fishing Voyage [RP]', 'textures', 'items')
OUT, W, w, s = '#383635', '#ffffff', '#eff0e8', '#cccec5'

PIXELS = {
    'salt_bucket': {
        # a heap of salt rising over the far rim
        (6, 0): OUT, (7, 0): OUT, (8, 0): OUT, (9, 0): OUT,
        (6, 1): W, (7, 1): W, (8, 1): w, (9, 1): w,
        (5, 2): s, (6, 2): W, (7, 2): w, (8, 2): w, (9, 2): w, (10, 2): s,
        (8, 3): s, (6, 4): s, (9, 4): s,                # grains
    },
    'fish_stock_bucket': {
        # milky broth with green onion
        (4, 3): '#d9d3c4', (5, 3): W, (6, 3): W, (7, 3): '#efeae0', (8, 3): '#efeae0', (9, 3): '#6fa84a', (10, 3): '#efeae0',
        (11, 3): '#d9d3c4',
        (4, 4): '#d9d3c4', (5, 4): '#efeae0', (6, 4): '#6fa84a', (7, 4): '#efeae0', (8, 4): '#efeae0', (9, 4): '#efeae0',
        (10, 4): '#efeae0', (11, 4): '#d9d3c4',
        (5, 5): '#d9d3c4', (6, 5): '#d9d3c4', (7, 5): '#d9d3c4', (8, 5): '#d9d3c4', (9, 5): '#d9d3c4', (10, 5): '#d9d3c4',
    },
}


def rgba(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def main():
    for name, pixels in PIXELS.items():
        path = os.path.join(ITEMS, f'kfv_{name}.png')
        im = Image.open(path).convert('RGBA')
        for xy, colour in pixels.items():
            im.putpixel(xy, rgba(colour))
        im.save(path)
        pbr.refresh(path)
    print('touched up', ', '.join(PIXELS))


if __name__ == '__main__':
    main()
