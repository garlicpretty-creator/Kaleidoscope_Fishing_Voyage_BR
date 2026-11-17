"""Pack file tests (no game, no Node): JSON, manifests, item icons, RTX texture sets, creative catalog,
the placeable 2D-icon blocks, spawn eggs and world features.

Run through tools/run_tests.py, or: python tools/tests/test_pack.py   (exit code 1 if anything fails)
"""
import json, os, re, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [BP]')
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
NS = 'kaleidoscope_fishing:'
failed = 0


def ok(cond, msg):
    global failed
    if not cond:
        failed += 1
    print(('OK   ' if cond else 'FAIL ') + msg)


def load(p):
    return json.loads(re.sub(r'^\s*//.*$', '', open(p, encoding='utf-8').read(), flags=re.M))


# JSON
jsons, broken = {}, []
for base in (BP, RP):
    for d, _, fs in os.walk(base):
        for f in fs:
            if f.endswith('.json'):
                p = os.path.join(d, f)
                try:
                    jsons[p] = load(p)
                except Exception as e:  # noqa: BLE001
                    broken.append(f'{os.path.relpath(p, ROOT)}: {e}')
ok(not broken, f'{len(jsons)} JSON files parse' + ('' if not broken else ': ' + '; '.join(broken[:5])))

# manifests
bpm, rpm = load(os.path.join(BP, 'manifest.json')), load(os.path.join(RP, 'manifest.json'))
ok(bpm['header']['version'] == rpm['header']['version'], f"BP and RP versions match ({bpm['header']['version']})")
ok(any(d.get('uuid') == rpm['header']['uuid'] for d in bpm['dependencies'])
   and any(d.get('uuid') == bpm['header']['uuid'] for d in rpm.get('dependencies', [])), 'BP and RP depend on each other')

# item icons
item_tex = load(os.path.join(RP, 'textures', 'item_texture.json'))['texture_data']
items = {j['minecraft:item']['description']['identifier']: j['minecraft:item']
         for p, j in jsons.items() if p.startswith(os.path.join(BP, 'items')) and 'minecraft:item' in j}
missing = []
for iid, it in items.items():
    icon = it.get('components', {}).get('minecraft:icon')
    key = icon if isinstance(icon, str) else (icon or {}).get('textures', {}).get('default') if isinstance(icon, dict) else None
    tex = item_tex.get(key, {}).get('textures') if key else None
    tex = tex if isinstance(tex, str) or tex is None else tex[0]
    if not tex or not os.path.exists(os.path.join(RP, tex + '.png')):
        missing.append(iid)
ok(not missing, f'all {len(items)} items have a working icon' + ('' if not missing else ': ' + ', '.join(missing[:8])))

# RTX texture sets: every map exists, has the icon's size, and covers every pixel of the icon
bad, n = [], 0
tdir = os.path.join(RP, 'textures', 'items')
for f in sorted(os.listdir(tdir)):
    if not f.endswith('.texture_set.json'):
        continue
    n += 1
    ts = load(os.path.join(tdir, f))['minecraft:texture_set']
    color = Image.open(os.path.join(tdir, ts['color'] + '.png')).convert('RGBA') if isinstance(ts.get('color'), str) else None
    for k in ('metalness_emissive_roughness', 'normal', 'heightmap'):
        if not isinstance(ts.get(k), str):
            continue
        p = os.path.join(tdir, ts[k] + '.png')
        if not os.path.exists(p):
            bad.append(f'{f}: {k} missing'); continue
        if color is None:
            continue
        im = Image.open(p).convert('RGBA')
        if im.size != color.size:
            bad.append(f'{f}: {k} is {im.size}, icon is {color.size}')
        elif any(color.getpixel((x, y))[3] and not im.getpixel((x, y))[3] for y in range(color.height) for x in range(color.width)):
            bad.append(f'{f}: {k} does not cover the icon')
ok(not bad, f'{n} RTX texture sets complete and aligned' + ('' if not bad else ': ' + '; '.join(bad[:6])))

# creative catalog
cat = load(os.path.join(BP, 'item_catalog', 'crafting_item_catalog.json'))
listed = [e if isinstance(e, str) else e.get('name') for c in cat['minecraft:crafting_items_catalog']['categories']
          for g in c.get('groups', []) for e in g.get('items', [])]
dups = sorted({x for x in listed if listed.count(x) > 1})
ok(not dups, f'creative catalog has no duplicates ({len(listed)} entries)' + ('' if not dups else ': ' + ', '.join(dups)))
# an item's own menu group must be the catalog group it is listed in, or the game logs a warning per item
group_of = {(e if isinstance(e, str) else e.get('name')): g['group_identifier']['name']
            for c in cat['minecraft:crafting_items_catalog']['categories'] for g in c.get('groups', []) for e in g.get('items', [])}
clash = []
for p, j in jsons.items():
    top = j.get('minecraft:item') or j.get('minecraft:block') if isinstance(j, dict) else None
    if not top or not p.startswith(BP):
        continue
    ident = top.get('description', {}).get('identifier'); g = top.get('description', {}).get('menu_category', {}).get('group')
    if g and ident in group_of and group_of[ident] != g:
        clash.append(f'{ident.split(":")[1]} ({g.split(".")[-1]} / catalog {group_of[ident].split(".")[-1]})')
ok(not clash, 'every item\'s menu group matches its catalog group' + ('' if not clash else ': ' + ', '.join(clash)))

# blocks with a 2D inventory icon: an item of the same id places the block, which faces the player
blocks = {j['minecraft:block']['description']['identifier']: j['minecraft:block']
          for p, j in jsons.items() if p.startswith(os.path.join(BP, 'blocks')) and 'minecraft:block' in j}
for n_ in ('fish_print', 'glass_float', 'laver_rock', 'oyster_bed', 'net_wall', 'dried_fish_string'):
    bid = NS + n_
    b, it = blocks.get(bid), items.get(bid)
    places = (it or {}).get('components', {}).get('minecraft:block_placer', {}).get('block')
    faces = 'minecraft:placement_direction' in (b or {}).get('description', {}).get('traits', {})
    ok(bool(b) and places == bid and faces and listed.count(bid) == 1,
       f'{n_}: item places the block, block faces the player, listed once in the catalog')

# spawn eggs
for p, j in jsons.items():
    if p.startswith(os.path.join(RP, 'entity')) and 'minecraft:client_entity' in j:
        d = j['minecraft:client_entity']['description']
        egg = d.get('spawn_egg', {}).get('texture')
        if egg:
            tex = item_tex.get(egg, {}).get('textures')
            ok(bool(tex) and os.path.exists(os.path.join(RP, tex + '.png')), f"spawn egg {d['identifier']} has its icon")

# world features: the pier is in, the 1.6.4 sea platform is out
names = [os.path.basename(p) for p in jsons] + [f for _, _, fs in os.walk(os.path.join(BP, 'structures')) for f in fs]
ok(not [f for f in names if 'platform' in f], 'the sea platform is gone (feature, rule, structure)')
ok(sum('fishing_pier' in f for f in names) >= 3, 'the fishing pier feature, rule and structure are present')

# Cookery guidebook: every item a page shows has a name in each language. Cookery falls back to English and
# then to the raw id, which is how untranslated English appeared in the Traditional Chinese book (1.4.0 playtest)
gb = load(os.path.join(ROOT, 'tools', 'data', 'GUIDEBOOK_JSON.json'))
gb_ids = set()
def gb_walk(o):
    if isinstance(o, dict):
        for v in o.values(): gb_walk(v)
    elif isinstance(o, list):
        for v in o: gb_walk(v)
    elif isinstance(o, str) and re.fullmatch(r'[a-z_]+:[a-z0-9_]+', o):
        gb_ids.add(o)
gb_walk(gb['entries']); gb_walk(gb['categories'])
for lang in ('zh_TW', 'zh_CN', 'en_US'):
    miss = sorted(i for i in gb_ids if i not in gb['names'][lang])
    ok(not miss, f'guidebook: every item shown has a {lang} name ({len(gb_ids)} items)' + ('' if not miss else ': ' + ', '.join(miss)))
latin = re.compile(r'[A-Za-z]{3,}')
for lang in ('zh_TW', 'zh_CN'):
    bad = sorted(k for k, v in list(gb['names'][lang].items()) + list(gb['text'][lang].items())
                 if isinstance(v, str) and latin.search(re.sub('§.', '', v).replace('Kaleidoscope', '').replace('Cookery', '')))
    ok(not bad, f'guidebook: no untranslated English in the {lang} names and texts' + ('' if not bad else ': ' + ', '.join(bad[:10])))

# entity component groups: a group that an event removes must not redefine a base component, because removing
# it deletes the base component as well (1.4.0: the cormorant lost gravity after its first dive and rose away)
for p, j in jsons.items():
    if not (p.startswith(os.path.join(BP, 'entities')) and 'minecraft:entity' in j):
        continue
    e = j['minecraft:entity']; base = set(e.get('components', {})); removed = set()
    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get('remove'), dict):
                removed.update(o['remove'].get('component_groups', []))
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(e.get('events', {}))
    clash = {g: sorted(base & set(v)) for g, v in e.get('component_groups', {}).items() if g in removed and base & set(v)}
    ok(not clash, f"{e['description']['identifier']}: no removable group shadows a base component"
       + ('' if not clash else f' ({clash})'))

print(f'\n{failed} pack test(s) FAILED' if failed else '\nall pack tests passed')
sys.exit(1 if failed else 0)
