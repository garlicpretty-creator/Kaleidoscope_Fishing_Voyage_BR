"""Regenerate the RTX companion maps for a repainted texture.

pbr.refresh(color_png): rewrites <name>_mer.png and <name>_height.png / <name>_normal.png next to it, whichever
the existing texture_set.json names. MER keeps the average colour of the old MER map (the material stays the
same); height comes from the new colour's brightness; normal is a Sobel of that brightness.
"""
import json, os
from PIL import Image


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def refresh(color_png):
    base = color_png[:-4]
    ts_path = base + '.texture_set.json'
    if not os.path.exists(ts_path):
        return []
    ts = json.load(open(ts_path, encoding='utf-8'))['minecraft:texture_set']
    col = Image.open(color_png).convert('RGBA')
    w, h = col.size
    px = col.load()
    written = []
    mer_name = ts.get('metalness_emissive_roughness')
    if isinstance(mer_name, str):
        mp = os.path.join(os.path.dirname(color_png), mer_name + '.png')
        avg = (0, 0, 200)
        if os.path.exists(mp):
            old = Image.open(mp).convert('RGBA')
            pts = [c for c in old.getdata() if c[3] > 0] or [(0, 0, 200, 255)]
            avg = tuple(sum(c[i] for c in pts) // len(pts) for i in range(3))
        mer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        for y in range(h):
            for x in range(w):
                if px[x, y][3]:
                    mer.putpixel((x, y), avg + (255,))
        mer.save(mp); written.append(mp)
    lum = [[_lum(px[x, y]) if px[x, y][3] else 0 for x in range(w)] for y in range(h)]
    hname = ts.get('heightmap')
    if isinstance(hname, str):
        hp = os.path.join(os.path.dirname(color_png), hname + '.png')
        hm = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        for y in range(h):
            for x in range(w):
                if px[x, y][3]:
                    v = int(96 + lum[y][x] * 0.5)
                    hm.putpixel((x, y), (v, v, v, 255))
        hm.save(hp); written.append(hp)
    nname = ts.get('normal')
    if isinstance(nname, str):
        np_ = os.path.join(os.path.dirname(color_png), nname + '.png')
        nm = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        L = lambda x, y: lum[min(h - 1, max(0, y))][min(w - 1, max(0, x))]
        for y in range(h):
            for x in range(w):
                if px[x, y][3]:
                    dx = (L(x + 1, y) - L(x - 1, y)) / 255; dy = (L(x, y + 1) - L(x, y - 1)) / 255
                    nx, ny, nz = -dx * 1.5, -dy * 1.5, 1.0
                    n = (nx * nx + ny * ny + nz * nz) ** 0.5
                    nm.putpixel((x, y), (int((nx / n * 0.5 + 0.5) * 255), int((ny / n * 0.5 + 0.5) * 255),
                                         int((nz / n * 0.5 + 0.5) * 255), 255))
        nm.save(np_); written.append(np_)
    return written
