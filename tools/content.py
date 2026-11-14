"""Helpers for adding an item everywhere it has to appear (used by tools/gen_additions_1_4.py).

add_item() writes the item file, its 16x16 icon (drawn from a character grid) with texture set and RTX maps, the
item_texture entry, the creative menu entry, the names in all six language files and the guidebook page.
Every step looks first and does nothing when the thing is already there, so the callers are safe to run again.
After a run:  python tools/build.py build  (the guidebook lives in generated.js).
"""
import json, os, re
from PIL import Image

import pbr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [BP]')
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
DATA = os.path.join(ROOT, 'tools', 'data')
NS = 'kaleidoscope_fishing'
LANGS = ('en_US', 'zh_TW', 'zh_CN')
TAG = {'en_US': 'KC: Fishing Voyage', 'zh_TW': '森羅物語：漁歌', 'zh_CN': '森罗物语：渔歌'}


def read(path):
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def load(name):
    with open(os.path.join(DATA, name + '.json'), encoding='utf-8') as f:
        return json.load(f)


def save(name, value, indent=2):
    with open(os.path.join(DATA, name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=indent)
        f.write('\n')


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')


def rgba(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def draw(grid, palette):
    """A 16x16 RGBA image from 16 rows of 16 characters; '.' is transparent."""
    assert len(grid) == 16, len(grid)
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(grid):
        assert len(row) == 16, (y, row, len(row))
        for x, ch in enumerate(row):
            if ch != '.':
                im.putpixel((x, y), rgba(palette[ch]))
    return im


def save_icon(name, image):
    """textures/items/kfv_<name>.png with its texture set (colour, MER, normal), like every other item icon."""
    path = os.path.join(RP, 'textures', 'items', f'kfv_{name}.png')
    image.save(path)
    write_json(path[:-4] + '.texture_set.json', {'format_version': '1.16.100', 'minecraft:texture_set': {
        'color': f'kfv_{name}', 'metalness_emissive_roughness': f'kfv_{name}_mer', 'normal': f'kfv_{name}_normal'}})
    pbr.refresh(path)


def _after_line(text, anchor_test, new_lines):
    """Insert new_lines after the first line anchor_test accepts; returns None when no line matches."""
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if anchor_test(line):
            cr = '\r' if line.endswith('\r') else ''
            return '\n'.join(lines[:i + 1] + [l + cr for l in new_lines] + lines[i + 1:])
    return None


def add_names(name, names, after):
    """display.item.<name> in both packs and name.<name> in the resource pack, after the lines for `after`."""
    for lang in LANGS:
        for pack in (BP, RP):
            path = os.path.join(pack, 'texts', lang + '.lang')
            text = read(path)
            if f'{NS}.display.item.{name}=' not in text:
                text = _after_line(text, lambda l: l.startswith(f'{NS}.display.item.{after}='),
                                   [f'{NS}.display.item.{name}={names[lang]}\\n§9§o{TAG[lang]}§r'])
                assert text, (path, after)
            if pack is RP and f'{NS}.name.{name}=' not in text:
                text = _after_line(text, lambda l: l.startswith(f'{NS}.name.{after}='), [f'{NS}.name.{name}={names[lang]}'])
                assert text, (path, after)
            write(path, text)


def add_lang(key, values, after_key):
    """One resource-pack key in the three languages, after the line for after_key."""
    for lang in LANGS:
        path = os.path.join(RP, 'texts', lang + '.lang')
        text = read(path)
        if f'{key}=' in text:
            continue
        text = _after_line(text, lambda l: l.startswith(after_key + '='), [f'{key}={values[lang]}'])
        assert text, (path, after_key)
        write(path, text)


def add_item_texture(name, after):
    path = os.path.join(RP, 'textures', 'item_texture.json')
    text = read(path)
    if f'"kfv_{name}"' in text:
        return
    anchor = f'    "kfv_{after}": {{\n      "textures": "textures/items/kfv_{after}"\n    }},\n'
    assert text.count(anchor) == 1, after
    write(path, text.replace(anchor, anchor + f'    "kfv_{name}": {{\n      "textures": "textures/items/kfv_{name}"\n    }},\n'))


def add_catalog(name, after):
    path = os.path.join(BP, 'item_catalog', 'crafting_item_catalog.json')
    text = read(path)
    if f'"{NS}:{name}"' in text:
        return
    m = re.search(r'\n( *)"%s:%s"(,?)\n' % (NS, after), text)
    assert m, after
    pad = m.group(1)
    new = f'\n{pad}"{NS}:{after}",\n{pad}"{NS}:{name}"{m.group(2)}\n'
    write(path, text[:m.start()] + new + text[m.end():])


def add_guide(entry, names, after):
    """A guidebook page after the page for `after`, and the item's name in the guidebook's own name tables."""
    g = load('GUIDEBOOK_JSON')
    ids = [e['id'] for e in g['entries']]
    if entry['id'] in ids:
        g['entries'][ids.index(entry['id'])] = entry
    else:
        g['entries'].insert(ids.index(f'{NS}:{after}') + 1, entry)
    for lang in LANGS:
        table = g['names'][lang]
        if entry['id'] not in table:
            out = {}
            for k, v in table.items():
                out[k] = v
                if k == f'{NS}:{after}':
                    out[entry['id']] = names[lang]
            g['names'][lang] = out
        else:
            table[entry['id']] = names[lang]
    save('GUIDEBOOK_JSON', g, indent=1)


def guide_entry(name, category, stack, mechanics, food=None, recipes=None, used_by=None, kinds=('item',), icon=None):
    e = {'id': f'{NS}:{name}', 'category': category, 'kinds': list(kinds), 'stack': stack,
         'icon': icon or f'textures/items/kfv_{name}'}
    if food:
        e['food'] = food
    if recipes:
        e['recipes'] = recipes
    if used_by is not None:
        e['usedBy'] = used_by
    e['mechanicsByLocale'] = {lang: list(mechanics[lang]) for lang in LANGS}
    e['mechanics'] = list(mechanics['en_US'])
    return e


def add_item(name, names, icon, after, group='ingredients', category='ingredients', stack=64, food=None,
             mechanics=None, recipes=None, used_by=None, components=None, texture_after=None):
    """names / mechanics: {lang: ...}; icon: (grid, palette); food: (nutrition, saturation_modifier) or None;
    after: the existing item this one follows in menus, language files and the guidebook."""
    comp = {'minecraft:display_name': {'value': f'%{NS}.display.item.{name}'}, 'minecraft:icon': f'kfv_{name}',
            'minecraft:max_stack_size': stack}
    if food:
        comp.update({'minecraft:food': {'nutrition': food[0], 'saturation_modifier': food[1], 'can_always_eat': False},
                     'minecraft:use_animation': 'eat',
                     'minecraft:use_modifiers': {'use_duration': 1.6, 'movement_modifier': 0.33},
                     'minecraft:tags': {'tags': ['minecraft:is_food']}})
    comp.update(components or {})
    write_json(os.path.join(BP, 'items', name + '.json'), {'format_version': '1.21.60', 'minecraft:item': {
        'description': {'identifier': f'{NS}:{name}', 'menu_category': {
            'category': 'equipment', 'group': f'kaleidoscope_cookery:itemGroup.name.{group}'}},
        'components': comp}})
    save_icon(name, draw(*icon))
    add_item_texture(name, texture_after or after)
    add_catalog(name, after)
    add_names(name, names, after)
    if mechanics:
        add_guide(guide_entry(name, category, stack, mechanics,
                              food={'nutrition': food[0], 'saturation': food[1]} if food else None,
                              recipes=recipes, used_by=used_by), names, after)
