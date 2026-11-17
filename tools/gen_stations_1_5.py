"""Blocks added in 1.5.0: the Wooden Tub (木盆), the Salt Pan (曬鹽盤) and the Lava Fish Tank (熔岩魚缸). First-pass models made of
boxes coloured from a swatch atlas (tools/modelkit.py), for refining in Blockbench later.

  python tools/gen_stations_1_5.py

Each block is one geometry whose parts are bones; the block shows the parts its state asks for (bone_visibility):
  tub       water | brine (paler, cloudy) | clams in the brine | fish roe | fry      (state `fill`, blocks/tub.js)
  salt pan  water | half dry (white rim) | a pan full of salt                       (state `stage`, blocks/saltPan.js)
Writes models/blocks/<name>.geo.json, textures/blocks/kfv_<name>.png with its RTX maps, the terrain texture
entry, and a 128x128 guidebook picture (textures/ui/kfv_book/kfv_<name>.png) rendered from the model.
"""
import importlib.util, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modelkit import Atlas, box, write_geometries, texture_set

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
NS = 'kaleidoscope_fishing'


def bone(name, cubes):
    return {'name': name, 'parent': 'root', 'pivot': [0, 0, 0], 'cubes': cubes}


def tub():
    a = Atlas(64, 64)
    wood, dark, band = '#9a6a3c', '#6e4826', '#5b5b60'
    cubes = [box(-6, 6, 0, 1, -6, 6, wood, dark, dark, atlas=a)]                       # bottom
    for x0, x1, z0, z1 in ((-7, -6, -6, 6), (6, 7, -6, 6), (-7, 7, -7, -6), (-7, 7, 6, 7)):  # staves
        cubes.append(box(x0, x1, 0, 6, z0, z1, wood, dark, atlas=a))
    for x0, x1, z0, z1 in ((-7.2, -6.9, -6, 6), (6.9, 7.2, -6, 6), (-7, 7, -7.2, -6.9), (-7, 7, 6.9, 7.2)):  # iron hoop
        cubes.append(box(x0, x1, 2, 3, z0, z1, band, atlas=a))
    water = box(-6, 6, 1, 4.6, -6, 6, '#3f76c4', '#2f5aa0', atlas=a)
    brine = box(-6, 6, 1, 4.6, -6, 6, '#8fb4c8', '#6d90a6', atlas=a)
    clams = [box(x - 1, x + 1, 3.9, 5.0, z - 0.8, z + 0.8, '#d8cbb0', '#9e8f72', atlas=a)   # half in the brine
             for x, z in ((-3, -2), (0, 1), (3, -3), (-2, 3), (2, 3), (-4, 0.5))]
    roe = [box(x - 0.6, x + 0.6, 4.6, 5.0, z - 0.6, z + 0.6, '#f2a24a', '#c8762a', atlas=a)
           for x, z in ((-1, -1), (0, 0), (1, -1), (-1, 1), (1, 1), (0, -2), (2, 0))]
    fry = [box(x - 1, x + 1, 3.6, 4.0, z - 0.3, z + 0.3, '#c9c9b8', '#8e8e80', atlas=a) for x, z in ((-2, -2), (2, 1), (-1, 3))]
    bones = [{'name': 'root', 'pivot': [0, 0, 0]}, bone('tub', cubes), bone('water', [water]), bone('brine', [brine]),
             bone('clams', clams), bone('roe', roe), bone('fry', fry)]
    return a, bones


def salt_pan():
    a = Atlas(64, 64)
    clay, dark = '#b4704c', '#86503a'
    cubes = [box(-7, 7, 0, 1, -7, 7, clay, dark, dark, atlas=a)]
    for x0, x1, z0, z1 in ((-8, -7, -8, 8), (7, 8, -8, 8), (-7, 7, -8, -7), (-7, 7, 7, 8)):
        cubes.append(box(x0, x1, 0, 2.5, z0, z1, clay, dark, atlas=a))
    water = box(-7, 7, 1, 2, -7, 7, '#4a86c8', '#3a6aa0', atlas=a)
    rim = [box(-7, 7, 1, 2.05, -7, -6, '#f2f2ea', atlas=a), box(-7, 7, 1, 2.05, 6, 7, '#f2f2ea', atlas=a),
           box(-7, -6, 1, 2.05, -6, 6, '#f2f2ea', atlas=a), box(6, 7, 1, 2.05, -6, 6, '#f2f2ea', atlas=a),
           box(-6, 6, 1, 1.6, -6, 6, '#7aa6cc', atlas=a)]
    salt = [box(-7, 7, 1, 2.2, -7, 7, '#f6f6f2', '#dcdcd4', atlas=a)] + \
           [box(x - 1, x + 1, 2.2, 2.7, z - 1, z + 1, '#ffffff', '#e2e2dc', atlas=a) for x, z in ((-3, -2), (2, 3), (4, -4), (-4, 4))]
    bones = [{'name': 'root', 'pivot': [0, 0, 0]}, bone('pan', cubes), bone('water', [water]), bone('half', rim), bone('salt', salt)]
    return a, bones


def lava_tank():
    """The Lava Fish Tank: basalt posts and rims, smoked glass, a bed of lava with a darker crust, and a glowing back.
    The fish is the tank fish entity, as in the Fish Tank; it swims in the space above the lava bed."""
    a = Atlas(64, 64)
    basalt, basalt_dark = '#4a4a50', '#2c2c32'
    cubes = [box(-7, 7, 0, 1, -5, 5, basalt, basalt_dark, atlas=a), box(-7, 7, 12, 13, -5, 5, basalt, basalt_dark, atlas=a)]
    for x in (-7, 6):
        for z in (-5, 4):
            cubes.append(box(x, x + 1, 1, 12, z, z + 1, basalt, basalt_dark, atlas=a))
    glass = '#2a1a1a60'
    cubes += [box(-6, 6, 1, 12, -4.9, -4.8, glass, atlas=a), box(-6, 6, 1, 12, 4.8, 4.9, glass, atlas=a),
              box(-6.9, -6.8, 1, 12, -4, 4, glass, atlas=a), box(6.8, 6.9, 1, 12, -4, 4, glass, atlas=a)]
    lava = [box(-6.8, 6.8, 1, 3, -4.8, 4.8, '#ff8a1e', '#e2581a', atlas=a),
            box(-6.8, 6.8, 3, 3.3, -4.8, 4.8, '#c43a12', atlas=a),
            box(-6.7, 6.7, 3.3, 11.8, 4.5, 4.75, '#7a1c0c', atlas=a)]                   # the glow at the back
    bones = [{'name': 'root', 'pivot': [0, 0, 0]}, bone('frame', cubes), bone('lava', lava)]
    return a, bones


def write(name, atlas, bones):
    geo = os.path.join(RP, 'models', 'blocks', f'{name}.geo.json')
    write_geometries(geo, [{'description': {'identifier': f'geometry.{NS}.{name}', 'texture_width': atlas.w, 'texture_height': atlas.h,
                                            'visible_bounds_width': 2, 'visible_bounds_height': 2, 'visible_bounds_offset': [0, 0.5, 0]},
                            'bones': bones}])
    png = os.path.join(RP, 'textures', 'blocks', f'kfv_{name}.png')
    atlas.save(png)
    texture_set(png)
    path = os.path.join(RP, 'textures', 'terrain_texture.json')
    t = json.load(open(path, encoding='utf-8'))
    t['texture_data'][f'kfv_{name}'] = {'textures': f'textures/blocks/kfv_{name}'}
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(t, f, indent=2, ensure_ascii=False)
    return geo, png


def book_picture(name, show):
    """The guidebook's 128x128 picture, rendered from the model with the bones in `show`."""
    spec = importlib.util.spec_from_file_location('rm', os.path.join(ROOT, 'tools', 'render_models.py'))
    rm = importlib.util.module_from_spec(spec); spec.loader.exec_module(rm)
    from PIL import Image
    g = json.load(open(os.path.join(RP, 'models', 'blocks', f'{name}.geo.json'), encoding='utf-8'))['minecraft:geometry'][0]
    g = json.loads(json.dumps(g))
    g['bones'] = [b for b in g['bones'] if b['name'] in show]
    g['description']['identifier'] = 'tmp'
    rm.GEOS['tmp'] = g
    tex = Image.open(os.path.join(RP, 'textures', 'blocks', f'kfv_{name}.png')).convert('RGBA')
    big = rm.render(rm.quads('tmp', tex), 256, 225, -30)
    bb = big.getbbox()
    side = max(bb[2] - bb[0], bb[3] - bb[1]); cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    big = big.crop((int(cx - side / 2), int(cy - side / 2), int(cx + side / 2), int(cy + side / 2))).resize((124, 124), Image.LANCZOS)
    out = Image.new('RGBA', (128, 128), (0, 0, 0, 0)); out.alpha_composite(big, (2, 2))
    out.save(os.path.join(RP, 'textures', 'ui', 'kfv_book', f'kfv_{name}.png'))


def main():
    for name, make, show in (('wooden_tub', tub, ('root', 'tub', 'brine', 'clams')), ('salt_pan', salt_pan, ('root', 'pan', 'salt')),
                             ('lava_fish_tank', lava_tank, ('root', 'frame', 'lava'))):
        atlas, bones = make()
        write(name, atlas, bones)
        book_picture(name, show)
    print('wrote the Wooden Tub and the Salt Pan')


if __name__ == '__main__':
    main()
