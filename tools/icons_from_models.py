"""Render 3D models as inventory icons, to judge which models make good icons.

usage: python tools/icons_from_models.py <out_dir>            review sheet + 16x16 pixel icons
       python tools/icons_from_models.py <out_dir> --hires 64 id [id ...]
                                                           smooth renders at 64x64 (<id>_64.png) for use as icons

For every candidate it writes <out_dir>/<id>_16x16.png (a pixel icon made from the 3D render: rendered large,
reduced to 16x16, colour-quantised, dark outline added) and builds a review sheet <out_dir>/對照.png showing
  current 2D icon | 3D model at inventory size | auto 16x16 icon from the model
Candidates are grouped: blocks that already show their 3D model in the inventory (A), feast / large items that
use a 2D icon but have a 3D model (B), and worn / held items whose model only shows in hand (C).
"""
import importlib.util, json, os, sys
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
spec = importlib.util.spec_from_file_location('rm', os.path.join(ROOT, 'tools', 'render_models.py'))
rm = importlib.util.module_from_spec(spec); spec.loader.exec_module(rm)
rm.LIGHT_FLOOR = 0.72              # icons read better with softer shadows

F = 'geometry.kaleidoscope_fishing.'
# (group, item id, block-texture name or texture path, [(geometry, dx, dz)], yaw, pitch, rotate_deg)
A = [(n, f'kfv_{t}', [(F + g, 0, 0)]) for n, t, g in (
    ('anchor', 'anchor', 'anchor'), ('catch_crate', 'catch_crate', 'catch_crate'),
    ('dried_fish_string', 'dried_fish_string', 'dried_fish_string'), ('drying_rack', 'drying_rack', 'drying_rack_1_1_2'),
    ('fish_cleaning_board', 'fish_cleaning_board', 'fish_cleaning_board_1_1'), ('fish_print', 'print_frame_wood', 'fish_print'),
    ('fish_sauce_jar', 'fish_sauce_jar', 'fish_sauce_jar_lid'), ('fish_scale', 'fish_scale', 'fish_scale_0'),
    ('fish_tank', 'fish_tank', 'fish_tank'), ('fishing_lantern', 'fishing_lantern', 'fishing_lantern_1'),
    ('fishing_net', 'fishing_net', 'fishing_net_0'), ('glass_float', 'glass_float', 'glass_float'),
    ('laver_rock', 'laver_rock', 'laver_rock_0'), ('net_wall', 'net_wall', 'net_wall'),
    ('oyster_bed', 'oyster_bed', 'oyster_bed_0'), ('shrimp_trap', 'shrimp_trap', 'shrimp_trap_1_1_1'),
    ('tackle_rack', 'tackle_rack', 'tackle_rack_1_4'))]
B = [(n, f'kfv_{t}', parts) for n, t, parts in (
    ('whole_tuna', 'whole_tuna', [(F + f'whole_tuna_{p}_0', 0, 16 * p) for p in range(3)]),
    ('emperor_whole_tuna', 'emperor_whole_tuna', [(F + f'emperor_whole_tuna_{p}_0', 0, 16 * p) for p in range(3)]),
    ('sashimi_boat', 'sashimi_boat', [(F + 'sashimi_boat_0_0', 0, 0), (F + 'sashimi_boat_1_0', 0, 16), (F + 'sashimi_boat_2_0', 0, 32)]),
    ('seafood_platter', 'seafood_platter', [(F + 'seafood_platter_0_0', 0, 0)]),
    ('sushi_platter', 'sushi_platter', [(F + 'sushi_platter_0_0', 0, 0), (F + 'sushi_platter_1_0', 0, 16)]),
    ('temaki_stand', 'temaki_stand', [(F + 'temaki_stand_0_0_0', 0, 0)]),
    ('dim_sum_steamer', 'dim_sum_steamer', [(F + 'dim_sum_steamer_0_0_0', 0, 0)]),
    ('fish_skewer_grill', 'fish_skewer_grill', [(F + 'fish_skewer_grill_0_0_0', 0, 0)]),
    ('grilled_fish_plank', 'grilled_fish_plank', [(F + 'grilled_fish_plank_0_0', 0, 0), (F + 'grilled_fish_plank_1_0', 0, 16)]),
    ('oden_pot', 'oden_pot', [(F + 'oden_pot_0_0_0', 0, 0)]),
    ('seafood_feast_pot', 'seafood_feast_pot', [(F + 'seafood_feast_pot_0_0_0', 0, 0)]),
    ('ice_catch_platter', 'ice_catch_platter', [(F + 'ice_catch_platter_0_0', 0, 0), (F + 'ice_catch_platter_1_0', 0, 16)]),
    ('frostlake_platter', 'frostlake_platter', [(F + 'frostlake_platter_0_0', 0, 0), (F + 'frostlake_platter_1_0', 0, 16)]),
    ('fishing_boat', 'fishing_boat', [(F + f'fishing_boat_{p}', 0, 16 * p) for p in range(3)]),
    ('large_fish_tank', 'large_fish_tank', [(F + 'large_fish_tank_0_0', 0, 0), (F + 'large_fish_tank_1_0', 16, 0)]))]
C = [('bamboo_fishing_rod', 'textures/entity/kfv_bamboo_rod', [(F + 'bamboo_rod', 0, 0)], 'rod'),
     ('bamboo_hat', 'textures/entity/kfv_bamboo_hat', [(F + 'bamboo_hat', 0, 0)], 'hat'),
     ('straw_raincoat', 'textures/entity/kfv_straw_raincoat', [(F + 'straw_raincoat', 0, 0)], 'coat')]


def terrain_png(name):
    td = json.load(open(os.path.join(RP, 'textures', 'terrain_texture.json'), encoding='utf-8'))['texture_data']
    t = td.get(name, {}).get('textures')
    t = t[0] if isinstance(t, list) else t
    t = t.get('path') if isinstance(t, dict) else t
    return rm.png_for(t) if t else None


def joined(parts):
    cubes = []
    tw = th = None
    for gid, dx, dz in parts:
        g = rm.GEOS.get(gid)
        if not g:
            continue
        tw, th = g['description'].get('texture_width', 64), g['description'].get('texture_height', 64)
        byname = {b['name']: b for b in g['bones']}
        for b in g['bones']:
            for c in b.get('cubes', []):
                c = json.loads(json.dumps(c))
                c['origin'] = [c['origin'][0] + dx, c['origin'][1], c['origin'][2] + dz]
                if 'pivot' in c:
                    c['pivot'] = [c['pivot'][0] + dx, c['pivot'][1], c['pivot'][2] + dz]
                # flatten bone rotations: none of these block models rotate bones
                cubes.append(c)
    return {'description': {'identifier': 'tmp', 'texture_width': tw, 'texture_height': th},
            'bones': [{'name': 'root', 'pivot': [0, 0, 0], 'cubes': cubes}]}


def pixel_icon(big):
    """Big RGBA render -> 16x16 pixel icon: each pixel takes the most common colour of its 16x16 block (so
    edges stay crisp instead of averaging into mud), a pixel is kept if the block is at least 40% covered,
    colours are quantised to 20 and the silhouette edge is darkened a little, vanilla style."""
    from collections import Counter
    k = big.width // 16
    src = big.load()
    out = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    solid = set()
    for ty in range(16):
        for tx in range(16):
            cols = [src[tx * k + i, ty * k + j] for j in range(k) for i in range(k)]
            op = [c[:3] for c in cols if c[3] > 128]
            if len(op) < 0.4 * len(cols):
                continue
            q = Counter((c[0] // 12, c[1] // 12, c[2] // 12) for c in op).most_common(1)[0][0]
            pick = [c for c in op if (c[0] // 12, c[1] // 12, c[2] // 12) == q]
            out.putpixel((tx, ty), tuple(sum(c[i] for c in pick) // len(pick) for i in range(3)) + (255,))
            solid.add((tx, ty))
    if not solid:
        return out
    pts = sorted(solid)
    rgb = Image.new('RGB', (len(pts), 1))
    for i, pt in enumerate(pts):
        rgb.putpixel((i, 0), out.getpixel(pt)[:3])
    q = rgb.quantize(20, method=Image.Quantize.MEDIANCUT).convert('RGB')
    for i, pt in enumerate(pts):
        out.putpixel(pt, q.getpixel((i, 0)) + (255,))
    for (x, y) in pts:
        if any((x + dx, y + dy) not in solid for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            r, g, b, _ = out.getpixel((x, y))
            out.putpixel((x, y), (int(r * 0.72), int(g * 0.72), int(b * 0.72), 255))
    return out


def render_candidate(parts, tex, kind):
    rm.GEOS['tmp'] = joined(parts)
    qs = rm.quads('tmp', tex)
    if kind == 'rod':
        big = rm.render(qs, 256, 90, 0).rotate(-45, resample=Image.NEAREST, expand=False)
    elif kind == 'coat':
        big = rm.render(qs, 256, 200, -12)
    elif kind == 'hat':
        big = rm.render(qs, 256, 225, -35)
    else:
        big = rm.render(qs, 256, 225, -30)
    bb = big.getbbox()
    if bb:                                               # fill the icon square
        side = max(bb[2] - bb[0], bb[3] - bb[1])
        cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        big = big.crop((int(cx - side / 2), int(cy - side / 2), int(cx + side / 2), int(cy + side / 2))).resize((256, 256), Image.LANCZOS)
    return big


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for group, items in (('A', A), ('B', B), ('C', C)):
        for entry in items:
            if group == 'C':
                iid, tpath, parts, kind = entry
                tex = Image.open(rm.png_for(tpath)).convert('RGBA')
            else:
                iid, tname, parts = entry; kind = 'block'
                tex = Image.open(terrain_png(tname)).convert('RGBA')
            big = render_candidate(parts, tex, kind)
            icon = pixel_icon(big)
            icon.save(os.path.join(out_dir, f'{iid}_16x16.png'))
            cur = os.path.join(RP, 'textures', 'items', f'kfv_{iid}.png')
            if not os.path.exists(cur):
                cur = os.path.join(RP, 'textures', 'items', f'kfv_{iid.replace("_fishing_rod", "_rod")}.png')
            rows.append((group, iid, Image.open(cur).convert('RGBA') if os.path.exists(cur) else None, big, icon))
    # sheet
    cell = 64; cols = 3
    W = cols * (cell * 3 + 40) + 20
    per_row = []
    sheet_h = 50 + ((len(rows) + cols - 1) // cols) * (cell + 34)
    sheet = Image.new('RGB', (W, sheet_h), (232, 230, 222))
    d = ImageDraw.Draw(sheet)
    d.text((12, 10), '每格：現在的 2D icon ｜ 3D 模型在背包大小 ｜ 由模型自動轉成的 16×16　A=方塊（背包已顯示 3D）B=宴席/大型物品 C=穿戴/手持',
           font=rm.FONT, fill=(40, 40, 40))
    zh = rm.ZH
    for i, (group, iid, cur, big, icon) in enumerate(rows):
        x = 12 + (i % cols) * (cell * 3 + 40); y = 40 + (i // cols) * (cell + 34)
        for k, im in enumerate((cur, big, icon)):
            bg = Image.new('RGBA', (cell, cell), (139, 139, 139, 255))
            if im is not None:
                bg.alpha_composite(im.resize((cell, cell), Image.NEAREST if im.width <= 32 else Image.LANCZOS))
            sheet.paste(bg.convert('RGB'), (x + k * (cell + 4), y))
        d.text((x, y + cell + 4), f'{group}  {zh.get(iid, iid)}', font=rm.FONT, fill=(40, 40, 40))
    sheet.save(os.path.join(out_dir, '對照.png'))
    print('wrote', len(rows), 'candidates to', out_dir)


def hires(out_dir, size, ids):
    """Smooth icon straight from the 3D render (no pixelisation), size x size, transparent background."""
    os.makedirs(out_dir, exist_ok=True)
    table = {e[0]: ('block', e) for e in A + B}
    table.update({e[0]: ('worn', e) for e in C})
    for iid in ids:
        kind, e = table[iid]
        if kind == 'worn':
            _, tpath, parts, k = e
            tex = Image.open(rm.png_for(tpath)).convert('RGBA')
        else:
            _, tname, parts = e; k = 'block'
            tex = Image.open(terrain_png(tname)).convert('RGBA')
        big = render_candidate(parts, tex, k)
        pad = max(1, size // 32)                       # a hair of margin so edges are not clipped
        icon = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        icon.alpha_composite(big.resize((size - 2 * pad, size - 2 * pad), Image.LANCZOS), (pad, pad))
        icon.save(os.path.join(out_dir, f'{iid}_{size}.png'))
    print('wrote', len(ids), f'{size}x{size} icons to', out_dir)


if __name__ == '__main__':
    if '--hires' in sys.argv:
        i = sys.argv.index('--hires')
        hires(sys.argv[1], int(sys.argv[i + 1]), sys.argv[i + 2:])
    else:
        main(sys.argv[1])
