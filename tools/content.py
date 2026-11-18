"""Helpers for adding content to both packs (1.5.0). Every function can be run again: it replaces what it wrote.

  item(key, ...)            items/<key>.json
  names(key, en, tw, cn)    display name in both packs' lang files, and the plain name in the resource pack
  icon(key)                 the item_texture.json entry (the PNG and its RTX maps come from an icon tool)
  catalog(key, after)       the creative inventory list, right after an item that is already there
  guide(key, ...)           the Cookery guidebook entry and its three names (tools/data/GUIDEBOOK_JSON.json)
  shapeless(key, ...)       recipes/crafting/<key>.json, and its id in the validate baseline
  data(name) / save(...)    tools/data/<NAME>.json
Run tools/build.py build afterwards.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [BP]')
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
NS = 'kaleidoscope_fishing'
PACK_TAG = {'en_US': 'KC: Fishing Voyage', 'zh_TW': '森羅物語：漁歌', 'zh_CN': '森罗物语：渔歌'}
PLACEABLE = {'en_US': 'Placeable Food', 'zh_TW': '可放置的食物', 'zh_CN': '可放置的食物'}
LANGS = ('en_US', 'zh_TW', 'zh_CN')


def full(key):
    return key if ':' in key else f'{NS}:{key}'


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def write_json(path, value, indent=2):
    """Keeps whether the file ended in a newline, so a rewrite changes only what was meant."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    newline = True
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            newline = f.read().endswith('\n')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=indent, ensure_ascii=False)
        if newline:
            f.write('\n')


def data(name):
    return read_json(os.path.join(HERE, 'data', f'{name}.json'))


def save(name, value, indent=None):
    """Writes with the indent the file already has (the data files do not all use the same)."""
    path = os.path.join(HERE, 'data', f'{name}.json')
    if indent is None:
        indent = 1
        if os.path.exists(path):
            m = re.search(r'\n( +)\S', open(path, encoding='utf-8').read(2000))
            indent = len(m.group(1)) if m else 1
    write_json(path, value, indent)


def item(key, stack=16, group='tools', category='equipment', components=None):
    comp = {'minecraft:display_name': {'value': f'%{NS}.display.item.{key}'}, 'minecraft:icon': f'kfv_{key}',
            'minecraft:max_stack_size': stack}
    comp.update(components or {})
    write_json(os.path.join(BP, 'items', f'{key}.json'), {'format_version': '1.21.60', 'minecraft:item': {
        'description': {'identifier': full(key), 'menu_category': {'category': category, 'group': f'kaleidoscope_cookery:itemGroup.name.{group}'}},
        'components': comp}})


def _set_lang(path, key, value):
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    line = f'{key}={value}'
    for i, l in enumerate(lines):
        if l.startswith(key + '='):
            lines[i] = line
            break
    else:
        while lines and lines[-1] == '':
            lines.pop()
        lines += [line, '']
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines))


def lang(key, en, tw, cn, packs=(BP, RP)):
    """A plain lang key (the same text in the given packs)."""
    for pack in packs:
        for code, text in zip(LANGS, (en, tw, cn)):
            _set_lang(os.path.join(pack, 'texts', f'{code}.lang'), key, text)


def names(key, en, tw, cn, kind='item', placeable=False):
    for code, text in zip(LANGS, (en, tw, cn)):
        shown = f'{text}\\n§9§o{PACK_TAG[code]}§r' + (f'\\n§5{PLACEABLE[code]}§r' if placeable else '')
        for pack in (BP, RP):
            _set_lang(os.path.join(pack, 'texts', f'{code}.lang'), f'{NS}.display.{kind}.{key}', shown)
        _set_lang(os.path.join(RP, 'texts', f'{code}.lang'), f'{NS}.name.{key}', text)


def icon(key):
    path = os.path.join(RP, 'textures', 'item_texture.json')
    j = read_json(path)
    j['texture_data'][f'kfv_{key}'] = {'textures': f'textures/items/kfv_{key}'}
    write_json(path, j)


def catalog(key, after):
    path = os.path.join(BP, 'item_catalog', 'crafting_item_catalog.json')
    raw = open(path, encoding='utf-8').read()
    j = json.loads(raw)
    done = []

    def walk(o):
        if isinstance(o, list):
            if full(key) in o:
                o.remove(full(key))
            if full(after) in o and all(isinstance(x, str) for x in o):
                o.insert(o.index(full(after)) + 1, full(key))
                done.append(1)
            for x in o:
                walk(x)
        elif isinstance(o, dict):
            for x in o.values():
                walk(x)
    walk(j)
    if not done:
        raise SystemExit(f'catalog: {after} is not in the creative catalog')
    indent = len(re.search(r'\n( +)"', raw).group(1))
    write_json(path, j, indent)


def guide(key, category, mechanics, name, stack=16, recipes=None, food=None, used_by=None, kinds=('item',)):
    """mechanics and name are (en, tw, cn)."""
    g = data('GUIDEBOOK_JSON')
    entry = {'id': full(key), 'category': category, 'kinds': list(kinds), 'stack': stack, 'icon': f'textures/items/kfv_{key}'}
    if food:
        entry['food'] = food
    if recipes:
        entry['recipes'] = recipes
    if mechanics:
        lines = [m if isinstance(m, (list, tuple)) else [m] for m in mechanics]     # one paragraph, or several
        entry['mechanicsByLocale'] = {code: list(text) for code, text in zip(LANGS, lines)}
        entry['mechanics'] = list(lines[0])
    if used_by:
        entry['usedBy'] = [full(u) for u in used_by]
    g['entries'] = [e for e in g['entries'] if e['id'] != full(key)] + [entry]
    for code, text in zip(LANGS, name):
        g['names'][code][full(key)] = text
    save('GUIDEBOOK_JSON', g)


def guide_name(item_id, en, tw, cn):
    """A name for an item another pack owns (a vanilla ingredient) that one of our guidebook pages shows."""
    g = data('GUIDEBOOK_JSON')
    for code, text in zip(LANGS, (en, tw, cn)):
        g['names'][code][full(item_id)] = text
    save('GUIDEBOOK_JSON', g)


def guide_used_by(key, user):
    g = data('GUIDEBOOK_JSON')
    for e in g['entries']:
        if e['id'] == full(key):
            e.setdefault('usedBy', [])
            if full(user) not in e['usedBy']:
                e['usedBy'].append(full(user))
    save('GUIDEBOOK_JSON', g)


def _baseline(recipe_id, file_name):
    path = os.path.join(HERE, 'tests', 'validate_baseline.txt')
    line = f"UNDEFINED_ID {recipe_id} ['{file_name}']"
    lines = open(path, encoding='utf-8').read().split('\n')
    if line in lines:
        return
    head = [l for l in lines if l.startswith('#')]
    body = sorted([l for l in lines if l and not l.startswith('#')] + [line])
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(head + body) + '\n')


def shapeless(key, ingredients, count=1):
    ing = [{'item': full(i)} for i in ingredients]
    write_json(os.path.join(BP, 'recipes', 'crafting', f'{key}.json'), {'format_version': '1.20.10', 'minecraft:recipe_shapeless': {
        'description': {'identifier': full(key)}, 'tags': ['crafting_table'], 'ingredients': ing,
        'result': {'item': full(key), 'count': count}, 'unlock': ing}})
    # validate.py reads a recipe id as an item id; an item of the same name makes it real, otherwise it is listed
    if not os.path.exists(os.path.join(BP, 'items', f'{key}.json')):
        _baseline(full(key), f'{key}.json')
    return {'method': 'Crafting Table', 'ingredients': [full(i) for i in ingredients], 'count': count, 'time': 0, 'result': full(key)}


# ------------------------------------------------------------------------------------------------ dishes
METHOD = {'wok': 'Wok', 'stockpot': 'Stockpot', 'steamer': 'Steamer', 'furnace': 'Furnace', 'crafting': 'Crafting Table'}
BUCKET = {f'{NS}:fish_stock': f'{NS}:fish_stock_bucket', f'{NS}:dashi': f'{NS}:dashi_bucket'}


def hint_key(item):
    ns, name = item.split(':')
    return f'{NS}.name.{name}' if ns == NS else f'{NS}.ing.{ns}.{name}'


def kc_recipe(kind, recipe):
    """Add or replace one of our recipes in Cookery's stations (KC_RECIPES.json)."""
    table = data('KC_RECIPES')
    table = [r for r in table if r['recipe']['id'] != recipe['id']] + [{'kind': kind, 'recipe': recipe}]
    save('KC_RECIPES', table)


def kc_alternative(recipe_id, plain, *alternatives):
    """Let a slot of one of our Cookery recipes also take other items: every slot holding `plain` becomes a list."""
    table = data('KC_RECIPES')
    for r in table:
        if r['recipe']['id'] != full(recipe_id):
            continue
        ing = r['recipe']['ingredients']
        for i, slot in enumerate(ing):
            items = slot if isinstance(slot, list) else [slot]
            if full(plain) in items:
                ing[i] = items + [full(a) for a in alternatives if full(a) not in items]
    save('KC_RECIPES', table)


def recipe_file(folder, name, body):
    write_json(os.path.join(BP, 'recipes', folder, f'{name}.json'), body)
    if not os.path.exists(os.path.join(BP, 'items', f'{name}.json')):
        _baseline(full(name), f'{name}.json')


def dish(key, name, nutrition, saturation, how, bowl=False, stack=64, effects=None, text=None, after=None):
    """A dish: its item, names, icon, catalog place, its recipe(s), food effects, hint and guidebook page.
    how: [(method, ingredients, extra)] with method wok | stockpot | steamer | furnace | crafting;
         ingredients are item ids (or lists of ids for a slot that takes any of them); a crafting slot may be
         {'tag': ...}; extra: {'base': ..., 'time': ..., 'count': ..., 'id': ...}."""
    comp = {'minecraft:food': {'nutrition': nutrition, 'saturation_modifier': saturation, 'can_always_eat': False},
            'minecraft:use_animation': 'eat', 'minecraft:use_modifiers': {'use_duration': 1.6, 'movement_modifier': 0.33},
            'minecraft:tags': {'tags': ['minecraft:is_food']}}
    if bowl:
        comp['minecraft:food']['using_converts_to'] = 'minecraft:bowl'
    item(key, stack=stack, group='foods', components=comp)
    names(key, *name)
    icon(key)
    if after:
        catalog(key, after)
    guide_recipes, hint = [], None
    for n, (method, ingredients, extra) in enumerate(how):
        extra = extra or {}
        rid = extra.get('id', f'{key}' if n == 0 else f'{key}_{n + 1}')
        ing = [i if isinstance(i, (list, dict)) else full(i) for i in ingredients]
        shown = [i[0] if isinstance(i, list) else i.get('shown', i.get('tag')) if isinstance(i, dict) else i for i in ing]
        count = extra.get('count', 1)
        time = extra.get('time', {'wok': 200, 'stockpot': 300, 'steamer': 300}.get(method, 0))
        if method == 'wok':
            kc_recipe('wok', {'id': f'{NS}:wok/{rid}', 'ingredients': ing, 'result': full(key), 'count': count,
                              'carrier': 'minecraft:bowl', 'time': time})
        elif method == 'stockpot':
            base = extra.get('base', 'minecraft:water')
            kc_recipe('stockpot_exact', {'id': f'{NS}:stockpot/{rid}', 'ingredients': ing, 'result': full(key), 'count': count,
                                         'time': time, 'base': base, 'carrier': 'minecraft:bowl', 'finishedKind': 'default'})
            if base in BUCKET:
                shown = [BUCKET[base]] + shown
        elif method == 'steamer':
            kc_recipe('steamer', {'id': f'{NS}:steamer/{rid}', 'input': ing[0], 'result': full(key), 'count': count, 'time': time})
        elif method == 'furnace':
            recipe_file('furnace', rid, {'format_version': '1.20.10', 'minecraft:recipe_furnace': {
                'description': {'identifier': full(rid)}, 'tags': ['furnace', 'smoker', 'campfire', 'soul_campfire'],
                'input': ing[0], 'output': full(key)}})
        elif method == 'crafting':
            slots = [{'tag': i['tag']} if isinstance(i, dict) else {'item': i} for i in ing]
            recipe_file('crafting', rid, {'format_version': '1.20.10', 'minecraft:recipe_shapeless': {
                'description': {'identifier': full(rid)}, 'tags': ['crafting_table'], 'ingredients': slots,
                'result': {'item': full(key), 'count': count}, 'unlock': [s for s in slots if 'item' in s][:1] or slots[:1]}})
        guide_recipes.append({'method': METHOD[method], 'ingredients': shown, 'count': count, 'time': time, 'result': full(key)})
        if hint is None:
            counted = {}
            for i in shown:
                counted[i] = counted.get(i, 0) + 1
            hint = {'id': full(key), 'nameKey': f'{NS}.name.{key}', 'icon': f'textures/items/kfv_{key}', 'method': method,
                    'count': count, 'ingredients': [[hint_key(i), n_] for i, n_ in counted.items()]}
    hints = [h for h in data('RECIPE_HINTS') if h['id'] != full(key)] + [hint]
    save('RECIPE_HINTS', hints)
    fx = data('FOOD_EFFECTS')
    if effects:
        fx[full(key)] = [{'effect': e, 'duration': d, 'amplifier': a} for e, d, a in effects]
    else:
        fx.pop(full(key), None)
    save('FOOD_EFFECTS', fx)
    food = {'nutrition': nutrition, 'saturation': saturation}
    if bowl:
        food['returns'] = 'minecraft:bowl'
    guide(key, 'dishes', text, name, stack=stack,
          recipes=guide_recipes, food=food)
    for r in guide_recipes:
        for i in r['ingredients']:
            if i.startswith(NS + ':'):
                guide_used_by(i, key)
