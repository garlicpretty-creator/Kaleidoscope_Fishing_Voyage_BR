"""Content for 1.6.0 steps 9 and 13 (docs/PLAN_1.6.0.md sections 11 and 14). Run again any time; every part rewrites
only what it owns, from the files already in the packs, and the output is deterministic (same input, same bytes):

  python tools/gen_1_6.py            all of it, then: python tools/build.py build
  python tools/gen_1_6.py list       the PLACEHOLDER art these parts drew, still waiting for real art

  merchant   the 1.5 fish join WANT_LIST and the carrying pole's texture set (want_a / want_b / order pick a
             texture by WANT_LIST position); a row of up to 8 wooden order tags under the order's fish (entity
             properties order_n / order_have, one bone per tag and side, shown by the render controller); the
             nod and the head shake with a shrug (property gesture, played by an animation controller)
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
    d['animations'].update({'tags': 'animation.kaleidoscope_fishing.fish_merchant.tags',
                            'nod': 'animation.kaleidoscope_fishing.fish_merchant.nod',
                            'refuse': 'animation.kaleidoscope_fishing.fish_merchant.refuse',
                            'gesture': 'controller.animation.kaleidoscope_fishing.fish_merchant.gesture'})
    d['scripts']['animate'] = ['move', 'look_at_target', 'tags', 'gesture']
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
                {'origin': [-8.1, 7.2, z0], 'size': [0, 1.2, 0.8], 'uv': {'east': face(u, 0, 4, 6), 'west': face(u + 4, 0, -4, 6)}},
                {'origin': [-8.1, 8.4, z0 + 0.35], 'size': [0, 0.6, 0.1], 'uv': {'east': face(8, 0, 1, 1), 'west': face(8, 0, 1, 1)}}]})
    c.write_json(os.path.join(c.RP, 'models', 'entity', 'fish_merchant_tags.geo.json'), {'format_version': '1.12.0', 'minecraft:geometry': [{
        'description': {'identifier': 'geometry.kaleidoscope_fishing.fish_merchant_tags', 'texture_width': 16, 'texture_height': 16,
                        'visible_bounds_width': 3, 'visible_bounds_height': 3, 'visible_bounds_offset': [0, 1.25, 0]},
        'bones': bones}]})

    # tags texture: blank light wood (u 0..3), flipped: darker wood with a green mark (u 4..7), the string (u 8)
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    px = im.load()
    for y in range(6):
        for x in range(4):
            edge = x in (0, 3) or y in (0, 5)
            px[x, y] = (196, 160, 104, 255) if not edge else (150, 112, 66, 255)
            px[x + 4, y] = (118, 80, 44, 255) if not edge else (84, 56, 30, 255)
    for (x, y) in ((5, 2), (6, 2), (5, 3), (6, 3)):
        px[x, y] = (64, 196, 96, 255)
    px[8, 0] = (90, 70, 50, 255)
    tp = os.path.join(RPT, 'entity', 'kfv_merchant_tags.png')
    save_png(im, tp)
    texture_set(tp, like=os.path.join(RPT, 'entity', 'kfv_fish_merchant_mer.png'))

    # animations: centre the row for n tags; the nod; the head shake with a shrug
    ap = os.path.join(c.RP, 'animations', 'fish_merchant.animation.json')
    an = c.read_json(ap)
    A = 'animation.kaleidoscope_fishing.fish_merchant.'
    an['animations'][A + 'tags'] = {'loop': True, 'bones': {'tags': {
        'position': [0, 0, f"0.45 * ({TAGS} - {Q(S + 'order_n')})"]}}}
    an['animations'][A + 'nod'] = {'animation_length': 1.0, 'bones': {'head': {'rotation': {
        '0.0': [0, 0, 0], '0.2': [16, 0, 0], '0.4': [0, 0, 0], '0.6': [16, 0, 0], '0.8': [0, 0, 0]}}}}
    an['animations'][A + 'refuse'] = {'animation_length': 1.3, 'bones': {
        'head': {'rotation': {'0.0': [0, 0, 0], '0.15': [0, -22, 0], '0.35': [0, 22, 0], '0.55': [0, -22, 0], '0.75': [0, 22, 0], '0.9': [0, 0, 0]}},
        'arms': {'position': {'0.0': [0, 0, 0], '0.3': [0, 1.5, 0], '1.0': [0, 1.5, 0], '1.3': [0, 0, 0]},
                 'rotation': {'0.0': [0, 0, 0], '0.3': [12, 0, 0], '1.0': [12, 0, 0], '1.3': [0, 0, 0]}},
        'body': {'rotation': {'0.0': [0, 0, 0], '0.3': [0, 0, 3], '1.0': [0, 0, -3], '1.3': [0, 0, 0]}}}}
    c.write_json(ap, an)
    g = Q(GESTURE_P)
    c.write_json(os.path.join(c.RP, 'animation_controllers', 'fish_merchant.animation_controllers.json'), {
        'format_version': '1.10.0', 'animation_controllers': {'controller.animation.kaleidoscope_fishing.fish_merchant.gesture': {
            'initial_state': 'default',
            'states': {
                'default': {'transitions': [{'nod': f'{g} == 1'}, {'refuse': f'{g} == 2'}]},
                'nod': {'animations': ['nod'], 'transitions': [{'default': f'{g} != 1'}], 'blend_transition': 0.2},
                'refuse': {'animations': ['refuse'], 'transitions': [{'default': f'{g} != 2'}], 'blend_transition': 0.2},
            }}}})


# ------------------------------------------------------------------------------------------------ drying rack
SHRIMP_KIND = 7
# swatches painted into the rack texture's free rows (y 24..25): body and tail per stage
SWATCH = {0: ((236, 132, 104), (250, 176, 150)), 1: ((206, 100, 74), (226, 140, 110)), 2: ((162, 76, 50), (186, 104, 76))}


def rack():
    dry = c.data('DRYING')
    dry['kinds'][str(SHRIMP_KIND)] = {'name': 'shrimp', 'product': S + 'dried_shell_shrimp', 'ticks': 24000}
    dry['inputs'][S + 'salted_shrimp'] = SHRIMP_KIND
    c.save('DRYING', dry)
    # texture swatches
    tp = os.path.join(RPT, 'blocks', 'kfv_drying_rack.png')
    im = Image.open(tp).convert('RGBA')
    for st, (body, tail) in SWATCH.items():
        for dx in range(2):
            for dy in range(2):
                im.putpixel((st * 4 + dx, 24 + dy), body + (255,))
                im.putpixel((st * 4 + 2 + dx, 24 + dy), tail + (255,))
    save_png(im, tp)
    pbr.refresh(tp)
    # geometry: the bare rack, then per hanging place a string with four curled shrimp
    gp = os.path.join(c.RP, 'models', 'blocks', 'drying_rack.geo.json')
    geo = c.read_json(gp)
    gs = [x for x in geo['minecraft:geometry'] if not x['description']['identifier'].split('_rack_')[1].startswith(f'{SHRIMP_KIND}_')]
    base = next(x for x in gs if x['description']['identifier'].endswith('_0_0_0'))
    centres = {1: [0.0], 2: [-2.5, 2.5], 3: [-3.75, 0.0, 3.75]}

    def solid(u, v, size):
        return {'origin': None, 'size': size, 'uv': {f: {'uv': [u, v], 'uv_size': [1, 1]} for f in ('north', 'south', 'east', 'west', 'up', 'down')}}
    for count in (1, 2, 3):
        for stage in (0, 1, 2):
            cubes = json.loads(json.dumps(base['bones'][0]['cubes']))
            for cx in centres[count]:
                cubes.append({'origin': [cx - 0.25, 4.0, -0.25], 'size': [0.5, 10.0, 0.5], 'uv': {f: {'uv': [104, 14], 'uv_size': [0.5, 1]} for f in ('north', 'south', 'east', 'west', 'up', 'down')}})
                for k, y in enumerate((10.5, 8.5, 6.5, 4.5)):
                    s = -1 if k % 2 == 0 else 1
                    body = solid(stage * 4, 24, [1.5, 1.2, 0.8])
                    body['origin'] = [cx + (0.1 if s > 0 else -1.6), y, -0.4]
                    tail = solid(stage * 4 + 2, 24, [0.6, 0.6, 0.5])
                    tail['origin'] = [cx + (1.6 if s > 0 else -2.2), y + 0.5, -0.25]
                    cubes += [body, tail]
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
    out = [('Kaleidoscope Fishing Voyage [RP]/textures/entity/kfv_merchant_tags.png', 'the order tags (blank / flipped) under the fish merchant\'s order fish'),
           ('Kaleidoscope Fishing Voyage [RP]/models/entity/fish_merchant_tags.geo.json', 'the order tags\' shapes'),
           ('Kaleidoscope Fishing Voyage [RP]/animations/fish_merchant.animation.json', 'nod / refuse (head shake and shrug) / tags: keyframes by hand'),
           ('Kaleidoscope Fishing Voyage [RP]/textures/blocks/kfv_drying_rack.png', 'drying rack: hanging shrimp colours (x 0..11, y 24..25)'),
           ('Kaleidoscope Fishing Voyage [RP]/models/blocks/drying_rack.geo.json', 'drying rack: drying_rack_7_* (a string of four shrimp per place)'),
           ('Kaleidoscope Fishing Voyage [RP]/textures/blocks/kfv_print_paper_seal.png', 'sealed print paper (cut from the old carp print: real art, kept)')]
    out += [(f'Kaleidoscope Fishing Voyage [RP]/textures/blocks/kfv_print_ink_{f}.png', f'fish print ink of {f}: its item icon in grey ink') for f in NEW_FISH]
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
