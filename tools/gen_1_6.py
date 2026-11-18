"""Content for 1.6.0 steps 9 and 13 (docs/PLAN_1.6.0.md sections 11 and 14). Run again any time; every part rewrites
only what it owns, from the files already in the packs, and the output is deterministic (same input, same bytes):

  python tools/gen_1_6.py            all of it, then: python tools/build.py build
  python tools/gen_1_6.py list       the PLACEHOLDER art these parts drew, still waiting for real art

  merchant   the 1.5 fish join WANT_LIST and the carrying pole's texture set (want_a / want_b / order pick a
             texture by WANT_LIST position); a row of up to 8 wooden order tags under the order's fish (entity
             properties order_n / order_have, one bone per tag and side, shown by the render controller); the
             nod and the head shake (property gesture: main's immersive gesture animation, with a shrug added)
  rack       Salted Shrimp hang on the Drying Rack as a string of shrimp (kind 7) and dry into Dried Shell-on Shrimp
  prints     fish prints for the 8 fish of 1.5, and the fish on a print drawn at 4 sizes (block state shrink): the
             paper is plain (or sealed) and the fish is its own transparent "ink" picture on a quad in front of it,
             so one picture per fish serves every size. The inks of the older fish are cut out of their old prints.
"""
import json, os, sys
from PIL import Image

import content as c
import pbr

S = c.NS + ':'
RPT = os.path.join(c.RP, 'textures')
NEW_FISH = ['mycelium_flounder', 'spore_seahorse', 'cherry_trout', 'creek_shrimp', 'echo_ray', 'sculk_lanternfish',
            'meteor_marlin', 'aurora_icefish']
def save_png(im, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=False)


def texture_set(png, like=None):
    """Write <name>.texture_set.json (MER + heightmap, as the pack's other textures) and refresh the maps.
    `like`: an existing MER map whose average colour the new one keeps (pbr.refresh reads the old map)."""
    base = png[:-4]
    name = os.path.basename(base)
    c.write_json(base + '.texture_set.json', {'format_version': '1.16.100', 'minecraft:texture_set': {
        'color': name, 'metalness_emissive_roughness': name + '_mer', 'heightmap': name + '_height'}})
    if like and os.path.exists(like) and not os.path.exists(base + '_mer.png'):
        Image.open(like).save(base + '_mer.png')
    pbr.refresh(png)


# ------------------------------------------------------------------------------------------------ merchant
GESTURE_P = S + 'gesture'
TAGS = 8
Q = "query.property('{}')".format


def merchant():
    want = c.data('WANT_LIST')
    for f in NEW_FISH:
        if S + f not in want:
            want.append(S + f)
    c.save('WANT_LIST', want)
    n = len(want)
    # ---- behaviour pack: the properties
    bp = os.path.join(c.BP, 'entities', 'fish_merchant.json')
    e = c.read_json(bp)
    props = e['minecraft:entity']['description']['properties']
    for k in ('want_a', 'want_b', 'order'):
        props[S + k]['range'] = [0, n]
    props[S + 'order_n'] = {'type': 'int', 'range': [0, TAGS], 'default': 0, 'client_sync': True}
    props[S + 'order_have'] = {'type': 'int', 'range': [0, TAGS], 'default': 0, 'client_sync': True}
    props[GESTURE_P] = {'type': 'int', 'range': [0, 2], 'default': 0, 'client_sync': True}
    c.write_json(bp, e)
    # ---- resource pack: textures, geometry, animations, render controllers
    rp = os.path.join(c.RP, 'entity', 'fish_merchant.entity.json')
    ce = c.read_json(rp)
    d = ce['minecraft:client_entity']['description']
    tex = {'default': 'textures/entity/kfv_fish_merchant'}
    for i, fid in enumerate(want, 1):
        tex[f'w{i}'] = 'textures/items/kfv_' + fid.split(':')[1]
    tex['tags'] = 'textures/entity/kfv_merchant_tags'
    d['textures'] = tex
    d['geometry']['tags'] = 'geometry.kaleidoscope_fishing.fish_merchant_tags'
    for k in ('nod', 'refuse'):                    # an early 1.6.0 draft had its own; main's "gesture" does both
        d['animations'].pop(k, None)
    d['animations'].update({'tags': 'animation.kaleidoscope_fishing.fish_merchant.tags',
                            'gesture': 'animation.kaleidoscope_fishing.fish_merchant.gesture'})
    if 'tags' not in d['scripts']['animate']:
        d['scripts']['animate'].append('tags')
    rcs = [r for r in d['render_controllers'] if not (isinstance(r, dict) and 'controller.render.kfv_merchant_tags' in r)]
    rcs.append({'controller.render.kfv_merchant_tags': f"{Q(S + 'order')} > 0 && {Q(S + 'order_n')} > 0"})
    d['render_controllers'] = rcs
    c.write_json(rp, ce)

    rcp = os.path.join(c.RP, 'render_controllers', 'kfv_merchant_wants.render_controllers.json')
    rc = c.read_json(rcp)
    arr = ['Texture.default'] + [f'Texture.w{i}' for i in range(1, n + 1)]
    for k, v in rc['render_controllers'].items():
        if 'arrays' in v:
            v['arrays']['textures']['Array.wants'] = arr
    vis = [{'*': True}]
    for i in range(1, TAGS + 1):
        vis.append({f'tag_{i}': f"{Q(S + 'order_n')} >= {i} && {Q(S + 'order_have')} < {i}"})
        vis.append({f'tag_{i}_on': f"{Q(S + 'order_n')} >= {i} && {Q(S + 'order_have')} >= {i}"})
    rc['render_controllers']['controller.render.kfv_merchant_tags'] = {
        'geometry': 'Geometry.tags', 'materials': [{'*': 'Material.default'}], 'textures': ['Texture.tags'], 'part_visibility': vis}
    c.write_json(rcp, rc)

    # tags geometry: the same root / body / pole bones as the wants geometry, so the walk animation moves them too.
    # The order's fish hangs at x -8.05, y 9..16, z -3.5..3.5; the tags hang in a row just below it.
    def face(u, v, w, h):
        return {'uv': [u, v], 'uv_size': [w, h]}
    bones = [{'name': 'root', 'pivot': [0, 0, 0]},
             {'name': 'body', 'pivot': [0, 24, 0], 'parent': 'root'},
             {'name': 'pole', 'pivot': [-6.5, 24.5, 0], 'parent': 'body'},
             {'name': 'tags', 'pivot': [-8.05, 9, 0], 'parent': 'pole'}]
    for i in range(1, TAGS + 1):
        z0 = round(-3.55 + (i - 1) * 0.9, 3)
        for side, u in (('', 0), ('_on', 4)):
            bones.append({'name': f'tag_{i}{side}', 'pivot': [-8.05, 8.6, z0 + 0.4], 'parent': 'tags', 'cubes': [
                {'origin': [-8.125, 7.2, z0], 'size': [0.15, 1.2, 0.8], 'uv': {
                    'east': face(u, 0, 4, 6), 'west': face(u + 4, 0, -4, 6),
                    **{f: face(9, 0, 1, 1) for f in ('north', 'south', 'up', 'down')}}},
                {'origin': [-8.1, 8.4, z0 + 0.35], 'size': [0, 0.6, 0.1], 'uv': {'east': face(8, 0, 1, 1), 'west': face(8, 0, 1, 1)}}]})
    c.write_json(os.path.join(c.RP, 'models', 'entity', 'fish_merchant_tags.geo.json'), {'format_version': '1.12.0', 'minecraft:geometry': [{
        'description': {'identifier': 'geometry.kaleidoscope_fishing.fish_merchant_tags', 'texture_width': 16, 'texture_height': 16,
                        'visible_bounds_width': 3, 'visible_bounds_height': 3, 'visible_bounds_offset': [0, 1.25, 0]},
        'bones': bones}]})

    # tags texture: the blank side is pale wood with grain and a string hole (u 0..3); a flipped tag shows its red
    # lacquered side with a gold fish stamped on it (u 4..7); the string (u 8); the tag's edge, darker wood (u 9)
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    px = im.load()
    WOOD, GRAIN, EDGE = (204, 168, 112, 255), (176, 138, 86, 255), (128, 92, 52, 255)
    RED, RED_DK, GOLD = (178, 44, 36, 255), (122, 28, 24, 255), (240, 196, 84, 255)
    fish = {(1, 3), (2, 3), (1, 4), (2, 4), (3, 3)}            # a fish facing left, its tail at x 3
    for y in range(6):
        for x in range(4):
            edge = x in (0, 3) or y in (0, 5)
            px[x, y] = EDGE if edge else (GRAIN if (x + 2 * y) % 5 == 0 else WOOD)
            px[x + 4, y] = RED_DK if edge else (GOLD if (x, y) in fish else RED)
    px[1, 1] = px[5, 1] = (60, 40, 24, 255)                     # the string hole
    px[8, 0] = (90, 70, 50, 255)
    px[9, 0] = EDGE
    tp = os.path.join(RPT, 'entity', 'kfv_merchant_tags.png')
    save_png(im, tp)
    texture_set(tp, like=os.path.join(RPT, 'entity', 'kfv_fish_merchant_mer.png'))

    # animations: centre the row for n tags. The nod and the head shake are main's immersive "gesture" animation
    # (Molang variables kfv_bow / kfv_no from the gesture property); 1.6.0 adds the shrug to its arms.
    ap = os.path.join(c.RP, 'animations', 'fish_merchant.animation.json')
    an = c.read_json(ap)
    A = 'animation.kaleidoscope_fishing.fish_merchant.'
    an['animations'][A + 'tags'] = {'loop': True, 'bones': {'tags': {
        'position': [0, 0, f"0.45 * ({TAGS} - {Q(S + 'order_n')})"]}}}
    arms = an['animations'][A + 'gesture']['bones']['arms']
    shrug = ' + 14 * variable.kfv_no'
    if shrug not in arms['rotation'][0]:
        arms['rotation'][0] += shrug
    arms['position'] = [0, '1.5 * variable.kfv_no', 0]
    c.write_json(ap, an)


# ------------------------------------------------------------------------------------------------ drying rack
SHRIMP_KIND = 7
# per stage (salted, half dry, dry): shell, light, dark. Painted into a free part of the rack texture: one 16 x 8
# patch per stage at u 64 + 16 * stage, v 4 (segmented abdomen u+0, head with eye and feelers u+4, tail fan u+8)
SHRIMP = {0: ((236, 132, 104), (252, 184, 156), (186, 86, 62)),
          1: ((206, 100, 74), (232, 146, 116), (150, 64, 44)),
          2: ((160, 74, 48), (190, 108, 78), (106, 46, 28))}
PATCH_U, PATCH_V = 64, 4


def paint_shrimp(im):
    px = im.load()
    for y in range(24, 26):                  # the 1.6.0 first draft's swatches (x 0..11, y 24..25), no longer used
        for x in range(12):
            px[x, y] = (0, 0, 0, 0)
    for st, (shell, light, dark) in SHRIMP.items():
        u = PATCH_U + 16 * st
        for y in range(8):
            for x in range(16):
                px[u + x, PATCH_V + y] = (0, 0, 0, 0)
        for y in range(8):                   # abdomen: shell segments with a light band and a dark joint
            for x in range(4):
                px[u + x, PATCH_V + y] = (light if y % 3 == 0 else dark if y % 3 == 2 else shell) + (255,)
        for y in range(8):                   # head: darker back, an eye, feelers along the lower edge
            for x in range(4):
                c = dark if y < 2 else shell
                if (x, y) == (1, 3):
                    c = (24, 18, 16)
                if y == 7 and x % 2 == 0:
                    c = light
                px[u + 4 + x, PATCH_V + y] = c + (255,)
        for y in range(4):                   # tail fan: light with a dark tip
            for x in range(4):
                px[u + 8 + x, PATCH_V + y] = (dark if y == 3 else light if x in (1, 2) else shell) + (255,)
    return im


def rack():
    dry = c.data('DRYING')
    dry['kinds'][str(SHRIMP_KIND)] = {'name': 'shrimp', 'product': S + 'dried_shell_shrimp', 'ticks': 24000}
    dry['inputs'][S + 'salted_shrimp'] = SHRIMP_KIND
    c.save('DRYING', dry)
    tp = os.path.join(RPT, 'blocks', 'kfv_drying_rack.png')
    save_png(paint_shrimp(Image.open(tp).convert('RGBA')), tp)
    pbr.refresh(tp)
    # geometry: the bare rack, then per hanging place a string with four shrimp hung by the tail, head down and
    # curled, alternately left and right of the string: tail fan, abdomen, head (three cubes, the rest painted)
    gp = os.path.join(c.RP, 'models', 'blocks', 'drying_rack.geo.json')
    geo = c.read_json(gp)
    gs = [x for x in geo['minecraft:geometry'] if not x['description']['identifier'].split('_rack_')[1].startswith(f'{SHRIMP_KIND}_')]
    base = next(x for x in gs if x['description']['identifier'].endswith('_0_0_0'))
    centres = {1: [0.0], 2: [-2.5, 2.5], 3: [-3.75, 0.0, 3.75]}
    SIDES = ('north', 'south', 'east', 'west', 'up', 'down')

    def part(stage, du, dv, w, h, size, origin):
        u = PATCH_U + 16 * stage + du
        return {'origin': origin, 'size': size, 'uv': {f: {'uv': [u, PATCH_V + dv], 'uv_size': [w, h]} for f in SIDES}}
    for count in (1, 2, 3):
        for stage in (0, 1, 2):
            cubes = json.loads(json.dumps(base['bones'][0]['cubes']))
            for cx in centres[count]:
                cubes.append({'origin': [cx - 0.25, 4.0, -0.25], 'size': [0.5, 10.0, 0.5], 'uv': {f: {'uv': [104, 14], 'uv_size': [0.5, 1]} for f in SIDES}})
                for k, y in enumerate((10.5, 8.5, 6.5, 4.5)):
                    s = 1 if k % 2 else -1

                    def x0(a, w):                # a: distance out from the string, w: width; mirrored to the left
                        return round(cx + a if s > 0 else cx - a - w, 3)
                    cubes += [part(stage, 8, 0, 4, 4, [1.2, 0.6, 0.4], [x0(0.2, 1.2), y + 1.3, -0.2]),     # tail fan
                              part(stage, 0, 0, 4, 8, [1.0, 1.5, 0.8], [x0(0.35, 1.0), y - 0.1, -0.4]),    # abdomen
                              part(stage, 4, 0, 4, 8, [1.3, 1.1, 1.0], [x0(1.05, 1.3), y - 0.7, -0.5])]    # head
            g = json.loads(json.dumps(base))
            g['description']['identifier'] = f'geometry.kaleidoscope_fishing.drying_rack_{SHRIMP_KIND}_{count}_{stage}'
            g['bones'][0]['cubes'] = cubes
            gs.append(g)
    geo['minecraft:geometry'] = gs
    c.write_json(gp, geo)
    # block: the new kind and its nine looks
    bp = os.path.join(c.BP, 'blocks', 'drying_rack.json')
    b = c.read_json(bp)
    blk = b['minecraft:block']
    blk['description']['states'][S + 'kind'] = list(range(SHRIMP_KIND + 1))
    perms = [p for p in blk['permutations'] if f"q.block_state('{S}kind') == {SHRIMP_KIND} " not in p['condition'] + ' ']
    for count in (1, 2, 3):
        for stage in (0, 1, 2):
            perms.append({'condition': f"q.block_state('{S}kind') == {SHRIMP_KIND} && q.block_state('{S}count') == {count} && q.block_state('{S}stage') == {stage}",
                          'components': {'minecraft:geometry': f'geometry.kaleidoscope_fishing.drying_rack_{SHRIMP_KIND}_{count}_{stage}'}})
    blk['permutations'] = perms
    c.write_json(bp, b)
    # the guidebook (Cookery's book keeps its words, plan 4.3)
    gb = c.data('GUIDEBOOK_JSON')
    add = {'en_US': 'Salted Shrimp hang as a string of shrimp and dry overnight into Dried Shell-on Shrimp.',
           'zh_TW': '鹽水蝦也能掛，掛成一串，曬一夜就是帶殼蝦乾。', 'zh_CN': '盐水虾也能挂，挂成一串，晒一夜就是带壳虾干。'}
    for e in gb['entries']:
        if e['id'] == S + 'drying_rack':
            for code, t in add.items():
                if t not in e['mechanicsByLocale'][code]:
                    e['mechanicsByLocale'][code].append(t)
            e['mechanics'] = list(e['mechanicsByLocale']['en_US'])
        if e['id'] == S + 'dried_shell_shrimp':
            r = {'method': 'Drying Rack', 'ingredients': [S + 'salted_shrimp'], 'count': 1, 'time': 24000, 'result': S + 'dried_shell_shrimp'}
            if r not in e['recipes']:
                e['recipes'].append(r)
    c.save('GUIDEBOOK_JSON', gb)


# ------------------------------------------------------------------------------------------------ fish prints
SHRINK = [1.0, 0.85, 0.7, 0.55]           # block state shrink 0..3 (0 = full size, also every print placed before 1.6.0)
TIER_FRAME = {1: 'kfv_print_frame_bronze', 2: 'kfv_print_frame_silver', 3: 'kfv_print_frame_gold', 4: 'kfv_print_frame_gold'}
IDX = f"(q.block_state('{S}fish') + 16 * q.block_state('{S}fish_bank'))"
BLK = os.path.join(RPT, 'blocks')


def lum(p):
    return 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]


def ink_from_print(fish_png, paper):
    """The ink of an old print: every pixel clearly darker than the paper under it."""
    im = Image.open(fish_png).convert('RGBA')
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    for y in range(im.height):
        for x in range(im.width):
            p, q = im.getpixel((x, y)), paper.getpixel((x, y))
            if p[3] and lum(p) < lum(q) - 40:
                out.putpixel((x, y), p[:3] + (255,))
    return out


INK_ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'print_ink')


def ink_from_art(art_png):
    """The ink of a fish drawn for its print (tools/data/print_ink/<fish>.png, Retro Diffusion through
    tools/art/rd_glyphs.py: the fish lying flat, head to the left): its shading turned into the old prints' warm
    black ink, with the paper showing through in specks, centred where the old prints' fish lie (row 14)."""
    art = Image.open(art_png).convert('RGBA')
    box = art.getbbox() or (0, 0, 32, 32)
    art = art.crop(box)
    if art.width > 30 or art.height > 26:
        k = min(30 / art.width, 26 / art.height)
        art = art.resize((max(1, round(art.width * k)), max(1, round(art.height * k))), Image.NEAREST)
    out = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    ox, oy = (32 - art.width) // 2, max(0, min(32 - art.height, 14 - art.height // 2))
    solid = lambda x, y: 0 <= x < art.width and 0 <= y < art.height and art.getpixel((x, y))[3] >= 128
    ls = [lum(art.getpixel((x, y))) for y in range(art.height) for x in range(art.width) if solid(x, y)]
    lo, hi = min(ls), max(ls)
    for y in range(art.height):
        for x in range(art.width):
            if not solid(x, y):
                continue
            t = (lum(art.getpixel((x, y))) - lo) / max(1, hi - lo)      # the fish's own shading, 0..1
            v = 34 + t * 64
            if (x + 2 * y) % 4 == 0:                                     # scales: a lighter dot in a diagonal grid
                v += 15
            if (x * 73 + y * 151) % 29 == 0:                             # a speck where the ink did not take
                v += 40
            if not all(solid(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                v = min(v, 34)                                           # the ink pools at the edge
            v = int(max(22, min(120, v)))
            out.putpixel((ox + x, oy + y), (v + 6, v + 1, max(0, v - 4), 255))
    return out


def ink_from_icon(icon_png):
    """A PLACEHOLDER ink for a fish with no print yet: its item icon, scaled up, in grey-black ink."""
    icon = Image.open(icon_png).convert('RGBA')
    box = icon.getbbox() or (0, 0, icon.width, icon.height)
    icon = icon.crop(box)
    k = max(1, min(28 // icon.width, 22 // icon.height))
    icon = icon.resize((icon.width * k, icon.height * k), Image.NEAREST)
    out = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    ox, oy = (32 - icon.width) // 2, (27 - icon.height) // 2
    for y in range(icon.height):
        for x in range(icon.width):
            p = icon.getpixel((x, y))
            if p[3] >= 128:
                v = int(28 + lum(p) * 0.28)
                out.putpixel((ox + x, oy + y), (v, v, v + 4, 255))
    return out


def prints():
    extra = c.data('PRINT_EXTRA')
    for f in NEW_FISH:
        if S + f not in extra:
            extra.append(S + f)
    c.save('PRINT_EXTRA', extra)
    base_n = c.data('PRINT_BASE')
    bp = os.path.join(c.BP, 'blocks', 'fish_print.json')
    b = c.read_json(bp)
    blk = b['minecraft:block']
    # which fish each print index shows, from the permutations written so far (old textures) or the ink ones
    names = {}
    for p in blk['permutations']:
        cond = p['condition']
        if IDX in cond and 'paper' in p['components'].get('minecraft:material_instances', {}):
            i = int(cond.split(IDX + ' == ')[1].split(' ')[0])
            mi = p['components']['minecraft:material_instances']
            t = (mi.get('ink') or mi['paper'])['texture']
            names[i] = t.replace('kfv_print_ink_', '').replace('kfv_print_', '').replace('_seal', '')
    for k, f in enumerate(NEW_FISH):
        names[base_n + 1 + extra.index(S + f)] = f
    assert max(names) < 64, 'fish print indices run out at 63 (fish 16 x fish_bank 4)'
    paper = Image.open(os.path.join(BLK, 'kfv_print_paper.png')).convert('RGBA')
    tt_path = os.path.join(RPT, 'terrain_texture.json')
    tt = c.read_json(tt_path)
    td = tt['texture_data']
    # the sealed paper: the seal of the carp's sealed print on plain paper
    seal_png = os.path.join(BLK, 'kfv_print_paper_seal.png')
    if os.path.exists(os.path.join(BLK, 'kfv_print_carp_seal.png')):
        a = Image.open(os.path.join(BLK, 'kfv_print_carp.png')).convert('RGBA')
        s = Image.open(os.path.join(BLK, 'kfv_print_carp_seal.png')).convert('RGBA')
        sealed = paper.copy()
        for y in range(s.height):
            for x in range(s.width):
                if s.getpixel((x, y)) != a.getpixel((x, y)):
                    sealed.putpixel((x, y), s.getpixel((x, y)))
        save_png(sealed, seal_png)
        texture_set(seal_png, like=os.path.join(BLK, 'kfv_print_paper_mer.png'))
    td['kfv_print_paper_seal'] = {'textures': 'textures/blocks/kfv_print_paper_seal'}
    # one ink per fish
    for i, f in sorted(names.items()):
        ink_png = os.path.join(BLK, f'kfv_print_ink_{f}.png')
        old = os.path.join(BLK, f'kfv_print_{f}.png')
        if os.path.exists(old):
            ink = ink_from_print(old, paper)
            like = os.path.join(BLK, f'kfv_print_{f}_mer.png')
        elif os.path.exists(os.path.join(INK_ART, f + '.png')):
            ink = ink_from_art(os.path.join(INK_ART, f + '.png'))
            like = os.path.join(BLK, 'kfv_print_ink_carp_mer.png')
        elif os.path.exists(ink_png) and f not in NEW_FISH:
            ink, like = None, None
        else:
            ink = ink_from_icon(os.path.join(RPT, 'items', f'kfv_{f}.png'))
            like = os.path.join(BLK, 'kfv_print_ink_carp_mer.png')
        if ink is not None:
            save_png(ink, ink_png)
            texture_set(ink_png, like=like)
        td[f'kfv_print_ink_{f}'] = {'textures': f'textures/blocks/kfv_print_ink_{f}'}
        # the baked prints of 1.5.0 are replaced by paper + ink
        for name in (f'kfv_print_{f}', f'kfv_print_{f}_seal'):
            td.pop(name, None)
            for suffix in ('.png', '.texture_set.json', '_mer.png', '_height.png', '_normal.png'):
                p = os.path.join(BLK, name + suffix)
                if os.path.exists(p):
                    os.remove(p)
    c.write_json(tt_path, tt)
    # geometry: the paper as it was, and an ink quad in front of it at each size
    gp = os.path.join(c.RP, 'models', 'blocks', 'fish_print.geo.json')
    geo = c.read_json(gp)
    g = geo['minecraft:geometry'][0]
    g['bones'] = [x for x in g['bones'] if not x['name'].startswith('ink_')]
    for k, f in enumerate(SHRINK):
        w, h = round(12 * f, 3), round(10 * f, 3)
        g['bones'].append({'name': f'ink_{k}', 'pivot': [0, 8, 7], 'cubes': [{'origin': [round(-w / 2, 3), round(8 - h / 2, 3), 6.9], 'size': [w, h, 0],
                           'uv': {'north': {'uv': [0, 0], 'uv_size': [32, 27], 'material_instance': 'ink'}}}]})
    with open(gp, 'w', encoding='utf-8', newline='\n') as fh:          # the model file is one compact line
        fh.write(json.dumps(geo, separators=(',', ':')) + '\n')
    # block: the new state, the bones by state, and per fish and frame the paper and the ink
    blk['description']['states'][S + 'shrink'] = [0, 1, 2, 3]
    has_fish = f'{IDX} > 0'
    comps = blk['components']
    comps['minecraft:geometry'] = {'identifier': 'geometry.kaleidoscope_fishing.fish_print', 'bone_visibility': {
        f'ink_{k}': f"{has_fish} && q.block_state('{S}shrink') == {k}" for k in range(len(SHRINK))}}
    comps['minecraft:material_instances'] = {'*': {'texture': 'kfv_print_frame_wood', 'render_method': 'alpha_test'},
                                             'paper': {'texture': 'kfv_print_paper', 'render_method': 'alpha_test'},
                                             'ink': {'texture': 'kfv_print_paper', 'render_method': 'alpha_test'}}
    perms = [p for p in blk['permutations'] if IDX not in p['condition']]
    for i, f in sorted(names.items()):
        for tier in (1, 2, 3, 4):
            perms.append({'condition': f"{IDX} == {i} && q.block_state('{S}tier') == {tier}", 'components': {'minecraft:material_instances': {
                '*': {'texture': TIER_FRAME[tier], 'render_method': 'alpha_test'},
                'paper': {'texture': 'kfv_print_paper_seal' if tier == 4 else 'kfv_print_paper', 'render_method': 'alpha_test'},
                'ink': {'texture': f'kfv_print_ink_{f}', 'render_method': 'alpha_test'}}}})
    blk['permutations'] = perms
    c.write_json(bp, b)


def placeholders():
    """The PLACEHOLDER art these parts draw (Pillow), still waiting for real art."""
    out = [('Kaleidoscope Fishing Voyage [RP]/animations/fish_merchant.animation.json', 'tags: the row centred by hand (z sign unchecked in game); the shrug added to the gesture animation'),
           ('Kaleidoscope Fishing Voyage [RP]/textures/blocks/kfv_print_paper_seal.png', 'sealed print paper (cut from the old carp print: real art, kept)')]
    out += [(f'Kaleidoscope Fishing Voyage [RP]/textures/blocks/kfv_print_ink_{f}.png', f'fish print ink of {f}: its item icon in grey ink')
            for f in NEW_FISH if not os.path.exists(os.path.join(INK_ART, f + '.png'))]
    return out


def main():
    if sys.argv[1:] == ['list']:
        for f, what in placeholders():
            print(f'{f}\t{what}')
        return
    merchant()
    rack()
    prints()
    print('1.6.0 content written; now run: python tools/build.py build')


if __name__ == '__main__':
    main()
