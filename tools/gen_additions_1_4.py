"""The 1.4.0 additions that are data, icons and models (see the 1.4.0 plan).

  python tools/gen_additions_1_4.py && python tools/build.py build

Safe to run again. The icons drawn here are placeholders in the pack's palette until the author's own art
replaces them (same file names).

  cleaning()   Fish Cleaning Board: nine more fish, shrimp / crabs / jellyfish, and what they are cut into
"""
import json, os

from content import BP, RP, NS, add_item, load, save, read, write, write_json, rgba
from PIL import Image

ID = lambda n: f'{NS}:{n}'  # noqa: E731
O = '#2e1c10'


# --------------------------------------------------------------------------- Fish Cleaning Board
SHELLFISH_ITEMS = [
    dict(name='shrimp_meat', after='fish_roe', food=(1, 0.2),
         names={'en_US': 'Shrimp Meat', 'zh_TW': '蝦肉', 'zh_CN': '虾肉'},
         mechanics={'en_US': ['Peel a shrimp, crayfish or lobster on the Fish Cleaning Board. Stands in for Shrimp in Har Gow, Shrimp Scrambled Eggs and Seafood Congee.'],
                    'zh_TW': ['在魚案板上剝蝦、螯蝦或龍蝦得到。可以代替蝦做生蝦餃、蝦仁炒蛋和海鮮粥。'],
                    'zh_CN': ['在鱼案板上剥虾、螯虾或龙虾得到。可以代替虾做生虾饺、虾仁炒蛋和海鲜粥。']},
         used_by=[ID('raw_har_gow'), ID('shrimp_scrambled_eggs'), ID('seafood_congee')],
         icon=(['................',
                '................',
                '.....OOOOO......',
                '...OOpppPPO.....',
                '..OppPPPppPO....',
                '.OpPPOOOOpPPO...',
                '.OpPO....OpPO...',
                '.OpPO.....OPO...',
                '.OpPPO....OPO...',
                '..OpPPOO..OO....',
                '...OpPPPO.......',
                '....OOpPPO......',
                '......OOPPOO....',
                '........OrrrO...',
                '.........OOO....',
                '................'], {'O': O, 'p': '#f8cdbf', 'P': '#ec9a86', 'r': '#d8543a'})),
    dict(name='shrimp_shell', after='shrimp_meat', food=None,
         names={'en_US': 'Shrimp Shells', 'zh_TW': '蝦殼', 'zh_CN': '虾壳'},
         mechanics={'en_US': ['Left over from peeling shrimp on the Fish Cleaning Board. Boil into Fish Stock.'],
                    'zh_TW': ['在魚案板上剝蝦剩下的殼。可以熬成魚高湯。'],
                    'zh_CN': ['在鱼案板上剥虾剩下的壳。可以熬成鱼高汤。']},
         used_by=[ID('fish_stock_bucket')],
         icon=(['................',
                '................',
                '..OO............',
                '.OrRO...OOO.....',
                '.ORRROOORrRO....',
                '..ORrRRRRRrO....',
                '...OORRrRRO.....',
                '.....OOOOO......',
                '.........OOOO...',
                '...OOO..ORrRRO..',
                '..ORrROORRRrRO..',
                '..ORRrRRRrRRO...',
                '...ORRRrRROO....',
                '....OOOOOO......',
                '................',
                '................'], {'O': O, 'R': '#e0683c', 'r': '#f3a070'})),
    dict(name='crab_meat', after='shrimp_shell', food=(2, 0.3),
         names={'en_US': 'Crab Meat', 'zh_TW': '蟹肉', 'zh_CN': '蟹肉'},
         mechanics={'en_US': ['Picked from a crab on the Fish Cleaning Board. Stands in for a Crab in Seafood Hot Pot.'],
                    'zh_TW': ['在魚案板上拆蟹得到。可以代替螃蟹做海鮮火鍋。'],
                    'zh_CN': ['在鱼案板上拆蟹得到。可以代替螃蟹做海鲜火锅。']},
         used_by=[ID('seafood_hot_pot')],
         icon=(['................',
                '................',
                '....OOOOOO......',
                '..OOwwwwwwOO....',
                '.OwwwrwwwwwwO...',
                '.OwwrrwwwwrwwO..',
                'OwwwwwwwwrrwwO..',
                'OwsswwwwwwwwwwO.',
                'OwwwwwrwwwwsswO.',
                '.OwwwrrwwwwwwwO.',
                '.OswwwwwwwrwwO..',
                '..OsswwwwrrwO...',
                '...OOsswwwOO....',
                '.....OOOOO......',
                '................',
                '................'], {'O': O, 'w': '#fbf3e8', 's': '#e0d2c0', 'r': '#e8765a'})),
    dict(name='crab_roe', after='crab_meat', food=(1, 0.3),
         names={'en_US': 'Crab Roe', 'zh_TW': '蟹黃', 'zh_CN': '蟹黄'},
         mechanics={'en_US': ['Sometimes found when a crab is opened on the Fish Cleaning Board. Makes a Raw Crab Roe Bun with Raw Dough.'],
                    'zh_TW': ['在魚案板上開蟹殼時有時會得到。和生麵團做成生蟹黃包。'],
                    'zh_CN': ['在鱼案板上开蟹壳时有时会得到。和生面团做成生蟹黄包。']},
         used_by=[ID('raw_crab_roe_bun')],
         icon=(['................',
                '................',
                '................',
                '.....OOOOOO.....',
                '...OOyyYYYYOO...',
                '..OyyhyYYYYYYO..',
                '.OyhhyYYYYYYdYO.',
                '.OyhyYYYYYYYddO.',
                '.OyYYYYYYYYdddO.',
                '.OYYYYYYYYdddO..',
                '..OYYYYYdddddO..',
                '...OOdddddOO....',
                '.....OOOOO......',
                '................',
                '................',
                '................'], {'O': O, 'Y': '#f2a22c', 'y': '#f8c458', 'h': '#fde6a0', 'd': '#cf7a1c'})),
    dict(name='crab_shell', after='crab_roe', food=None,
         names={'en_US': 'Crab Shell', 'zh_TW': '蟹殼', 'zh_CN': '蟹壳'},
         mechanics={'en_US': ['The shell of a crab opened on the Fish Cleaning Board. Boil into Fish Stock.'],
                    'zh_TW': ['在魚案板上開蟹剩下的殼。可以熬成魚高湯。'],
                    'zh_CN': ['在鱼案板上开蟹剩下的壳。可以熬成鱼高汤。']},
         used_by=[ID('fish_stock_bucket')],
         icon=(['................',
                '................',
                '................',
                '...OOOOOOOOOO...',
                '..ORrrRRRRRRRO..',
                '.ORrhrRRRRRRRRO.',
                'ORRrrRRdRRdRRRRO',
                'ORRRRRRRRRRRRRdO',
                'ORRRRdRRRRRRRddO',
                '.ORRRRRRRRRdddO.',
                '..ORRRRRRdddOO..',
                '...OOdddddOO....',
                '.....OOOOO......',
                '................',
                '................',
                '................'], {'O': O, 'R': '#d8452c', 'r': '#ee7a52', 'h': '#f8b890', 'd': '#a82c1e'})),
    dict(name='jellyfish_skin', after='crab_shell', food=(1, 0.1),
         names={'en_US': 'Jellyfish Strips', 'zh_TW': '海蜇皮', 'zh_CN': '海蜇皮'},
         mechanics={'en_US': ['Sliced from a jellyfish on the Fish Cleaning Board. Crunchy; eat it as it is.'],
                    'zh_TW': ['在魚案板上切水母得到。口感爽脆，可以直接吃。'],
                    'zh_CN': ['在鱼案板上切水母得到。口感爽脆，可以直接吃。']},
         used_by=[],
         icon=(['................',
                '................',
                '..OOO.....OOO...',
                '.OjjjO..OOjjjO..',
                '.OjJjjOOjjjJjO..',
                '..OjJjjjjjJjO...',
                '.OOOjJJjjJJjOO..',
                'OjjjOjjJJjjOjjO.',
                'OjJjjOOjjOOjjJjO',
                '.OjJjjjOOjjjJjO.',
                '..OjJJjjjjJJjO..',
                '...OjjJJJJjjO...',
                '....OOjjjjOO....',
                '......OOOO......',
                '................',
                '................'], {'O': '#6b5a48', 'j': '#f3ead6', 'J': '#d9c8a4'})),
]

W = ID('white_fish_fillet')
# index 33.. ; `like` = the fish whose board models the new one borrows (same cuts) until it has its own
NEW_FISH = [
    ('loach', dict(out=[W, 2], scales=False, bones=1, extra=[]), 'eel'),
    ('mudskipper', dict(out=[W, 2], scales=False, bones=1, extra=[]), 'catfish'),
    ('golden_croaker', dict(out=[W, 4], scales=True, bones=1, extra=[[ID('fish_roe'), 0.25], ['minecraft:gold_nugget', 0.25]]), 'yellow_croaker'),
    ('chorus_carp', dict(out=[ID('chorus_sashimi'), 4], scales=True, bones=1, extra=[[ID('fish_roe'), 0.25]]), 'carp'),
    ('ender_angler', dict(out=[W, 4], scales=False, bones=2, extra=[['minecraft:ender_pearl', 0.1]]), 'anglerfish'),
    ('blazefin', dict(out=[W, 3], scales=True, bones=1, extra=[]), 'sea_bream'),
    ('lava_eel', dict(out=[ID('eel_fillet'), 3], scales=False, bones=1, extra=[]), 'eel'),
    ('magma_koi', dict(out=[W, 4], scales=True, bones=1, extra=[['minecraft:magma_cream', 0.1]]), 'carp'),
    ('lava_dragon_koi', dict(out=[W, 6], scales=True, bones=2, extra=[]), 'grass_carp'),
]
MEAT, SHELL = ID('shrimp_meat'), ID('shrimp_shell')
CMEAT, CSHELL, ROE, SKIN = ID('crab_meat'), ID('crab_shell'), ID('crab_roe'), ID('jellyfish_skin')
# first = the cut a creature starts at (3: one cut; 2: two cuts); gut = what cut 2 gives instead of Fish Offal;
# last = what the final cut gives besides `out`; model = the shared board model
SHELLFISH = [
    ('shrimp', dict(first=3, scales=False, out=[MEAT, 1], bones=0, extra=[], last=[[SHELL, 1]]), 'shrimp'),
    ('purpur_shrimp', dict(first=3, scales=False, out=[MEAT, 1], bones=0, extra=[], last=[[SHELL, 1]]), 'shrimp'),
    ('cave_crayfish', dict(first=3, scales=False, out=[MEAT, 2], bones=0, extra=[], last=[[SHELL, 1]]), 'shrimp'),
    ('lobster', dict(first=3, scales=False, out=[MEAT, 3], bones=0, extra=[], last=[[SHELL, 2]]), 'shrimp'),
    ('crab', dict(first=2, scales=False, out=[CMEAT, 1], bones=0, gut=[[CSHELL, 1]], extra=[[ROE, 0.5]]), 'crab'),
    ('basalt_crab', dict(first=2, scales=False, out=[CMEAT, 1], bones=0, gut=[[CSHELL, 1]], extra=[[ROE, 0.5]]), 'crab'),
    ('glow_crab', dict(first=2, scales=False, out=[CMEAT, 2], bones=0, gut=[[CSHELL, 1], [ROE, 1]], extra=[]), 'crab'),
    ('king_crab', dict(first=2, scales=False, out=[CMEAT, 4], bones=0, gut=[[CSHELL, 2], [ROE, 1]], extra=[]), 'crab'),
    ('moon_jellyfish', dict(first=3, scales=False, out=[SKIN, 2], bones=0, extra=[]), 'jelly'),
    ('chorus_jellyfish', dict(first=3, scales=False, out=[SKIN, 2], bones=0, extra=[]), 'jelly'),
]

BOARD_TEX = os.path.join(RP, 'textures', 'blocks', 'kfv_fish_cleaning_board.png')
BOARD_GEO = os.path.join(RP, 'models', 'blocks', 'fish_cleaning_board.geo.json')
BOARD_BLOCK = os.path.join(BP, 'blocks', 'fish_cleaning_board.json')
GEO = 'geometry.kaleidoscope_fishing.fish_cleaning_board_'
# colour swatches painted into the free rows of the board atlas (4x4 each, from x = 0, y = 96)
SWATCH = ['#ee7a52', '#d8452c', '#a82c1e', '#fbf3e8', '#e0d2c0', '#f2a22c', '#f3ead6', '#d9c8a4', '#f8cdbf', '#2e1c10']
SHRIMP, RED, DARK, WHITE, SHADE, ROE_C, JELLY, JELLY_D, PINK, EYE = range(10)


def board_cube(x0, x1, y0, y1, z0, z1, colour):
    """A box on the board (its top is y = 2), every face one swatch colour."""
    f = {'uv': [colour * 4 + 1, 97], 'uv_size': [2, 2]}
    return {'origin': [x0, 2 + y0, z0], 'size': [round(x1 - x0, 3), round(y1 - y0, 3), round(z1 - z0, 3)],
            'uv': {k: dict(f) for k in ('north', 'south', 'east', 'west', 'up', 'down')}}


def shellfish_models():
    legs = [board_cube(x, x + 0.5, 0, 0.5, z0, z1, DARK) for x in (-2.2, -0.8, 0.6, 1.9) for z0, z1 in ((-3.4, -2.0), (2.0, 3.4))]
    claws = [board_cube(-4.2, -2.6, 0, 0.9, z, z + 1.2, RED) for z in (-2.6, 1.4)]
    return {
        # a peeled-to-be shrimp lying on its side: head, three body segments, tail fan
        'shrimp_3': [board_cube(-3.4, -1.8, 0, 1.4, -1.0, 0.6, SHRIMP), board_cube(-3.9, -3.4, 0.5, 0.9, -0.5, -0.1, EYE),
                     board_cube(-1.8, 0.0, 0, 1.3, -0.9, 0.5, PINK), board_cube(0.0, 1.6, 0, 1.1, -0.7, 0.4, SHRIMP),
                     board_cube(1.6, 2.8, 0, 0.8, -0.5, 0.3, PINK), board_cube(2.8, 3.8, 0, 0.4, -1.0, 0.8, RED)],
        # a whole crab, then the same crab with the shell lifted off and the white meat showing
        'crab_2': [board_cube(-2.6, 2.6, 0, 1.6, -2.0, 2.0, RED), board_cube(-2.0, 2.0, 1.6, 1.9, -1.4, 1.4, DARK),
                   board_cube(-3.0, -2.6, 0.9, 1.3, -1.0, -0.6, EYE), board_cube(-3.0, -2.6, 0.9, 1.3, 0.6, 1.0, EYE)] + legs + claws,
        'crab_3': [board_cube(-2.6, 2.6, 0, 0.7, -2.0, 2.0, RED), board_cube(-2.2, 2.2, 0.7, 1.2, -1.6, 1.6, WHITE),
                   board_cube(-1.2, 0.2, 1.2, 1.4, -0.8, 0.6, SHADE), board_cube(0.6, 1.6, 1.2, 1.5, -0.4, 0.8, ROE_C)] + legs + claws,
        # a jellyfish bell with its arms laid out to one side
        'jelly_3': [board_cube(-3.2, 0.6, 0, 1.4, -2.0, 2.0, JELLY), board_cube(-2.6, 0.0, 1.4, 1.8, -1.4, 1.4, JELLY_D)] +
                   [board_cube(0.6, 4.4, 0, 0.4, z, z + 0.6, JELLY_D if i % 2 else JELLY) for i, z in enumerate((-1.8, -0.9, 0.0, 0.9))],
    }


def cleaning():
    for it in SHELLFISH_ITEMS:
        add_item(**it)

    # --- data: indices continue after the current highest
    c = load('CLEANING')
    nxt = max(v['index'] for v in c.values()) + 1
    for name, entry, _ in NEW_FISH + SHELLFISH:
        if ID(name) not in c:
            c[ID(name)] = dict(index=nxt, **entry)
            nxt += 1
        else:
            c[ID(name)].update(entry)
    save('CLEANING', c)
    assert nxt <= 64, 'the board has two states for the fish index: 16 x 4'

    # --- atlas swatches for the shared shellfish models
    im = Image.open(BOARD_TEX).convert('RGBA')
    for i, colour in enumerate(SWATCH):
        for y in range(96, 100):
            for x in range(i * 4, i * 4 + 4):
                im.putpixel((x, y), rgba(colour))
    im.save(BOARD_TEX)
    # the atlas keeps its own MER and height maps; only the swatch cells are added to them
    # (pbr.refresh would flatten the whole MER map to one value)
    mer_path, height_path = BOARD_TEX[:-4] + '_mer.png', BOARD_TEX[:-4] + '_height.png'
    mer, height = Image.open(mer_path), Image.open(height_path)        # RGB and greyscale: kept as they are
    assert (mer.mode, height.mode) == ('RGB', 'L'), (mer.mode, height.mode)
    common = max(mer.getcolors(256 * 128), key=lambda cv: cv[0])[1]    # the board's usual material
    for i, colour in enumerate(SWATCH):
        r, g, b, _ = rgba(colour)
        v = int(96 + (0.299 * r + 0.587 * g + 0.114 * b) * 0.5)
        for y in range(96, 100):
            for x in range(i * 4, i * 4 + 4):
                mer.putpixel((x, y), common)
                height.putpixel((x, y), v)
    mer.save(mer_path)
    height.save(height_path)

    # --- models: the shared shellfish geometries on top of the empty board
    geo = json.loads(read(BOARD_GEO))
    by_id = {g['description']['identifier']: g for g in geo['minecraft:geometry']}
    empty = by_id[GEO + '0_0']
    for key, cubes in shellfish_models().items():
        g = json.loads(json.dumps(empty))
        g['description']['identifier'] = GEO + key
        g['bones'][0]['cubes'] += cubes
        by_id[GEO + key] = g
    # --- block: every (fish, cut) picks its geometry; a new fish borrows its look-alike's
    block = json.loads(read(BOARD_BLOCK))
    perms = [p for p in block['minecraft:block']['permutations'] if 'minecraft:geometry' not in p['components']]
    idx = "(q.block_state('kaleidoscope_fishing:fish') + 16 * q.block_state('kaleidoscope_fishing:fish_bank'))"
    cut = "q.block_state('kaleidoscope_fishing:cut')"
    perms.append({'condition': f'{idx} == 0 && {cut} == 0', 'components': {'minecraft:geometry': GEO + '0_0'}})
    like = {n: l for n, _, l in NEW_FISH}
    shared = {n: m for n, _, m in SHELLFISH}
    used = {GEO + '0_0'}
    for fid, e in sorted(c.items(), key=lambda kv: kv[1]['index']):
        name = fid.split(':')[1]
        first = e.get('first', 1 if e['scales'] else 2)
        for stage in range(first, 4):
            if name in shared:
                gid = GEO + f'{shared[name]}_{stage}'
            else:
                src = c[ID(like[name])] if name in like else e
                assert src.get('first', 1 if src['scales'] else 2) == first, (name, 'look-alike has other cuts')
                gid = GEO + f"{src['index']}_{stage}"
            assert gid in by_id, gid
            used.add(gid)
            perms.append({'condition': f"{idx} == {e['index']} && {cut} == {stage}", 'components': {'minecraft:geometry': gid}})
    block['minecraft:block']['permutations'] = perms
    write_json(BOARD_BLOCK, block)
    geo['minecraft:geometry'] = [g for i, g in by_id.items() if i in used]      # drops models no fish uses
    write_json(BOARD_GEO, geo)

    # --- recipes: shells into Fish Stock; Shrimp Meat / Crab Meat / Crab Roe as stand-ins
    kc = load('KC_RECIPES')
    def alt(rid, old, new):
        r = next(x['recipe'] for x in kc if x['recipe']['id'] == ID(rid))
        ing = r['ingredients']
        for i, slot in enumerate(ing):
            if slot == old:
                ing[i] = [old, new]
            elif isinstance(slot, list) and old in slot and new not in slot:
                slot.append(new)
    for shell in (SHELL, CSHELL):
        alt('stockpot/fish_stock', ID('fish_bones'), shell)
    alt('wok/shrimp_scrambled_eggs', ID('shrimp'), MEAT)
    alt('stockpot/seafood_congee', ID('shrimp'), MEAT)
    alt('stockpot/seafood_hot_pot', ID('crab'), CMEAT)
    save('KC_RECIPES', kc)
    for rid, dough_with, result in (('raw_har_gow_from_shrimp_meat', MEAT, 'raw_har_gow'),
                                    ('raw_crab_roe_bun_from_crab_roe', ROE, 'raw_crab_roe_bun')):
        ing = [{'item': 'kaleidoscope_cookery:raw_dough'}, {'item': dough_with}]
        write_json(os.path.join(BP, 'recipes', 'crafting', rid + '.json'), {'format_version': '1.20.10', 'minecraft:recipe_shapeless': {
            'description': {'identifier': ID(rid)}, 'tags': ['crafting_table'], 'ingredients': ing,
            'result': {'item': ID(result), 'count': 1}, 'unlock': ing}})

    # --- guidebook: the board's own page
    g = load('GUIDEBOOK_JSON')
    page = next(e for e in g['entries'] if e['id'] == ID('fish_cleaning_board'))
    more = {
        'en_US': 'Shrimp, crayfish and lobster are peeled in one cut into Shrimp Meat and Shrimp Shells. Crabs take two cuts: the first lifts the shell (Crab Shell, sometimes Crab Roe), the second picks the Crab Meat. A jellyfish is sliced into Jellyfish Strips. Oysters and clams do not go on the board.',
        'zh_TW': '蝦、螯蝦和龍蝦一刀剝開，得到蝦肉和蝦殼。螃蟹要兩刀：第一刀開殼（蟹殼，有時有蟹黃），第二刀取蟹肉。水母切成海蜇皮。牡蠣和蛤蜊不能放上魚案板。',
        'zh_CN': '虾、螯虾和龙虾一刀剥开，得到虾肉和虾壳。螃蟹要两刀：第一刀开壳（蟹壳，有时有蟹黄），第二刀取蟹肉。水母切成海蜇皮。牡蛎和蛤蜊不能放上鱼案板。',
    }
    fix = {'en_US': ('Every fish works. ', 'Every fish you catch works. '), 'zh_TW': ('所有魚都能處理。', '釣得到的魚都能處理。'),
           'zh_CN': ('所有鱼都能处理。', '钓得到的鱼都能处理。')}
    for lang, lines in page['mechanicsByLocale'].items():
        lines[0] = lines[0].replace(*fix[lang])
        if more[lang] not in lines:
            lines.append(more[lang])
    page['mechanics'] = list(page['mechanicsByLocale']['en_US'])
    save('GUIDEBOOK_JSON', g, indent=1)


if __name__ == '__main__':
    cleaning()
    print('done; now run: python tools/build.py build')
