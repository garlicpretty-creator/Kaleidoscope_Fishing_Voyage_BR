"""A small kit for first-pass block and entity models: boxes coloured from a swatch atlas.

Each colour gets a 4x4 cell in the texture (with a little deterministic noise so faces are not flat); every face
of a box maps 2x2 texels from the middle of its colour's cell. The result is a plain Bedrock geometry with per-face
UVs, so Blockbench opens it as is, and the texture can be repainted there later.

    atlas = Atlas(width, height, start=(0, 0))       # cells are placed from `start`, row by row
    c = atlas.add('#9a5a34')                          # -> a colour id
    box(x0, x1, y0, y1, z0, z1, c, side=c2, bottom=c3)  # block units, origin bottom-centre, y up
    atlas.save(path)                                  # writes the texture (keeps what is outside the cells)
"""
import json
import os
import random

from PIL import Image


def rgba(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


class Atlas:
    def __init__(self, width, height, start=(0, 0), base=None, cell=4):
        self.w, self.h, self.cell = width, height, cell
        self.image = Image.open(base).convert('RGBA') if base else Image.new('RGBA', (width, height), (0, 0, 0, 0))
        assert self.image.size == (width, height), (self.image.size, width, height)
        self.x0, self.y0 = start
        self.cells = {}

    def add(self, colour, noise=6):
        if colour in self.cells:
            return self.cells[colour]
        n = len(self.cells)
        per_row = (self.w - self.x0) // self.cell
        cx, cy = self.x0 + (n % per_row) * self.cell, self.y0 + (n // per_row) * self.cell
        assert cy + self.cell <= self.h, 'atlas is full'
        r, g, b, _ = rgba(colour)
        rnd = random.Random(colour)
        for y in range(cy, cy + self.cell):
            for x in range(cx, cx + self.cell):
                d = rnd.randint(-noise, noise)
                self.image.putpixel((x, y), (max(0, min(255, r + d)), max(0, min(255, g + d)), max(0, min(255, b + d)), 255))
        self.cells[colour] = (cx + 1, cy + 1)
        return self.cells[colour]

    def save(self, path):
        self.image.save(path)


def box(x0, x1, y0, y1, z0, z1, top, side=None, bottom=None, atlas=None):
    """A box between the given bounds; colours are atlas cells (or hex strings when `atlas` is given)."""
    if atlas:
        top, side, bottom = (atlas.add(c) if isinstance(c, str) else c for c in (top, side or top, bottom or side or top))
    side, bottom = side or top, bottom or side or top
    face = lambda c: {'uv': list(c), 'uv_size': [2, 2]}  # noqa: E731
    return {'origin': [round(x0, 3), round(y0, 3), round(z0, 3)],
            'size': [round(x1 - x0, 3), round(y1 - y0, 3), round(z1 - z0, 3)],
            'uv': {'north': face(side), 'south': face(side), 'east': face(side), 'west': face(side),
                   'up': face(top), 'down': face(bottom)}}


def geometry(identifier, cubes, tex_w, tex_h, bone='root'):
    return {'description': {'identifier': identifier, 'texture_width': tex_w, 'texture_height': tex_h,
                            'visible_bounds_width': 3, 'visible_bounds_height': 3, 'visible_bounds_offset': [0, 0.75, 0]},
            'bones': [{'name': bone, 'pivot': [0, 0, 0], 'cubes': cubes}]}


def write_geometries(path, geos):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'format_version': '1.16.0', 'minecraft:geometry': geos}, f, indent=2)
        f.write('\n')


def texture_set(png, kind='heightmap'):
    """A texture set beside a block or entity texture (colour, MER, height), as the pack's other textures have."""
    import pbr
    name = os.path.basename(png)[:-4]
    with open(png[:-4] + '.texture_set.json', 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'format_version': '1.16.100', 'minecraft:texture_set': {
            'color': name, 'metalness_emissive_roughness': name + '_mer', kind: name + ('_height' if kind == 'heightmap' else '_normal')}}, f, indent=2)
        f.write('\n')
    pbr.refresh(png)
