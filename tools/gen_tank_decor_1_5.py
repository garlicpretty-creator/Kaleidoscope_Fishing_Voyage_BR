"""Large Fish Tank bottoms (1.5.0, plan 12): kelp, coral or sand used on a Large Fish Tank changes its bottom.

  python tools/gen_tank_decor_1_5.py

The tank's two half geometries (models/blocks/large_fish_tank.geo.json) are split into bones: `frame` (base, posts,
glass, water) and `deco0` (the stones and weeds it always had), and three bottoms are added: `deco1` water plants,
`deco2` coral, `deco3` a sand bed with shells. The block state kaleidoscope_fishing:decor (0-3) picks one
(bone_visibility); blocks/tanks.js sets it. The new colours go below the tank texture's used rows (y 32 on).
Safe to run again.
"""
import json, os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modelkit import Atlas, box

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [BP]')
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
NS = 'kaleidoscope_fishing'
GEO = os.path.join(RP, 'models', 'blocks', 'large_fish_tank.geo.json')
TEX = os.path.join(RP, 'textures', 'blocks', 'kfv_large_fish_tank.png')
FRAME = 12                       # the first 12 cubes of each half: base, posts, glass, rims, water


def bottoms(a, x0, x1):
    """The three bottoms for a half spanning x0..x1 (inside the glass, z -5..5, on the floor at y 3)."""
    w = x1 - x0
    plants = []
    for i, (fx, fz, h) in enumerate(((0.15, -3.5, 8), (0.35, 2.5, 6), (0.55, -1, 9), (0.75, 3.2, 5), (0.9, -4, 7))):
        x = x0 + w * fx
        col = ('#3f8f3a', '#2f6f2c') if i % 2 else ('#5aa845', '#3f7f30')
        plants += [box(x - 0.5, x + 0.5, 3, 3 + h, fz - 0.5, fz + 0.5, *col, atlas=a),
                   box(x - 1.2, x - 0.4, 3 + h * 0.5, 3 + h * 0.5 + 1.5, fz - 0.3, fz + 0.3, col[0], atlas=a)]
    coral = []
    for i, (fx, fz, c) in enumerate(((0.2, -3, '#e0607a'), (0.45, 2.8, '#f0a040'), (0.7, -1.5, '#d8d040'), (0.85, 3, '#7a60d0'))):
        x = x0 + w * fx
        coral += [box(x - 1, x + 1, 3, 5.5, fz - 1, fz + 1, c, atlas=a), box(x - 0.4, x + 0.4, 5.5, 7.5, fz - 0.4, fz + 0.4, c, atlas=a),
                  box(x + 0.6, x + 1.6, 4.5, 6, fz - 0.3, fz + 0.3, c, atlas=a)]
    sand = [box(x0, x1, 3, 3.6, -5.4, 5.4, '#e4d29c', '#c8b27a', atlas=a)]
    for i, (fx, fz) in enumerate(((0.25, -2), (0.6, 3), (0.8, -3.5))):
        x = x0 + w * fx
        sand.append(box(x - 0.8, x + 0.8, 3.6, 4.1, fz - 0.6, fz + 0.6, '#f4ece0' if i % 2 else '#e8b0a0', atlas=a))
    return plants, coral, sand


def main():
    j = json.load(open(GEO, encoding='utf-8'))
    a = Atlas(128, 128, start=(0, 32), base=TEX)
    for g in j['minecraft:geometry']:
        bones = {b['name']: b for b in g['bones']}
        if 'frame' in bones:
            frame, deco0 = bones['frame']['cubes'], bones['deco0']['cubes']
        else:
            cubes = bones['root']['cubes']
            frame, deco0 = cubes[:FRAME], cubes[FRAME:]
        floor = frame[0]                                    # the base: its x span is this half's inside
        x0, x1 = floor['origin'][0] + 1, floor['origin'][0] + floor['size'][0] - 1
        plants, coral, sand = bottoms(a, x0, x1)
        mk = lambda n, c: {'name': n, 'parent': 'root', 'pivot': [0, 0, 0], 'cubes': c}  # noqa: E731
        g['bones'] = [{'name': 'root', 'pivot': [0, 0, 0]}, mk('frame', frame), mk('deco0', deco0),
                      mk('deco1', plants), mk('deco2', coral), mk('deco3', sand)]
    with open(GEO, 'w', encoding='utf-8', newline='\n') as f:   # compact, as the file always was
        json.dump(j, f, separators=(',', ':'))
    a.save(TEX)
    # the new pixels take the average material of the old ones (the MER map stays as it was elsewhere)
    mer_path = TEX[:-4] + '_mer.png'
    if os.path.exists(mer_path):
        mer, col = Image.open(mer_path).convert('RGBA'), Image.open(TEX).convert('RGBA')
        old = [p for p in mer.crop((0, 0, 128, 28)).get_flattened_data() if p[3]] or [(0, 0, 200, 255)]
        avg = tuple(sum(p[i] for p in old) // len(old) for i in range(3)) + (255,)
        for y in range(32, 128):
            for x in range(128):
                if col.getpixel((x, y))[3]:
                    mer.putpixel((x, y), avg)
        mer.save(mer_path)
    # the block: a decor state, and each half's geometry shows the bottom it asks for
    bp = os.path.join(BP, 'blocks', 'large_fish_tank_block.json')
    b = json.load(open(bp, encoding='utf-8'))
    blk = b['minecraft:block']
    blk['description']['states'][f'{NS}:decor'] = [0, 1, 2, 3]
    vis = {f'deco{i}': f"q.block_state('{NS}:decor') == {i}" for i in range(4)}
    for p in blk['permutations']:
        geo = p['components'].get('minecraft:geometry')
        if geo:
            ident = geo if isinstance(geo, str) else geo['identifier']
            p['components']['minecraft:geometry'] = {'identifier': ident, 'bone_visibility': vis}
    base = blk['components']['minecraft:geometry']
    ident = base if isinstance(base, str) else base['identifier']
    blk['components']['minecraft:geometry'] = {'identifier': ident, 'bone_visibility': vis}
    with open(bp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(b, f, indent=2)
        f.write('\n')
    print('large fish tank: three bottoms added')


if __name__ == '__main__':
    main()
