"""The 1.4.0 additions that are data, icons and models (see the 1.4.0 plan).

  python tools/gen_additions_1_4.py && python tools/build.py build

Safe to run again. The icons drawn here are placeholders, used only while an item has no icon file yet;
the icons in the pack now were generated with Retro Diffusion from these placeholders (see CREDITS.txt).

  cleaning()   Fish Cleaning Board: nine more fish, shrimp / crabs / jellyfish, and what they are cut into
  dishes()     five dishes from the new ingredients; small changes to older dishes
  tank()       Shrimp and Purpur Shrimp in the Fish Tank
  legends()    a keepsake and a feast for every legend, and the four tackle parts made from the keepsakes
"""
import json, os

from content import BP, RP, NS, add_item, add_guide, add_lang, guide_entry, load, save, read, write, write_json, rgba
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
                if GEO + f"{e['index']}_{stage}" in by_id:       # its own model (tools/gen_models_1_4.py) wins
                    gid = GEO + f"{e['index']}_{stage}"
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


# --------------------------------------------------------------------------- legends
BOBBER = ['................', '.......OO.......', '......OssO......', '......OssO......', '.....OOOOOO.....',
          '....OaaaaaaO....', '...OaaAAAAaaO...', '...OaAAAAAAaO...', '...OOOOOOOOOO...', '...ObbbbbbbbO...',
          '...ObbBBBBbbO...', '....ObbBBbbO....', '.....ObbbbO.....', '......OOOO......', '.......OO.......',
          '................']
T = lambda en, tw, cn: {'en_US': en, 'zh_TW': tw, 'zh_CN': cn}  # noqa: E731

LEGEND_ITEMS = [
    dict(name='emperor_tuna_fin', after='dragon_scale', group='tools', category='tools', stack=16,
         names=T('Emperor Bluefin Dorsal', '皇鮪背鰭', '皇鲔背鳍'),
         mechanics=T(['The tall dorsal fin of the Emperor Bluefin. A keepsake; with a Bone Hook it makes an Emperor Bone Hook.'],
                     ['藍鰭皇鮪高聳的背鰭。紀念品；和骨鉤可以做成皇鮪骨鉤。'], ['蓝鳍皇鲔高耸的背鳍。纪念品；和骨钩可以做成皇鲔骨钩。']),
         used_by=[ID('emperor_bone_hook')],
         icon=(['................', '.........OO.....', '........OfO.....', '.......OfFO.....', '......OfFFO.....',
                '.....OfFFFO.....', '....OfFFFdO.....', '...OfFFFFdO.....', '..OfFFFFddO.....', '..OfFFFdddOO....',
                '.OfFFFFddddbO...', '.OFFFFdddbbbO...', '.ObbbbbbbbbO....', '..OOOOOOOOO.....', '................',
                '................'], {'O': '#101828', 'f': '#5a86c8', 'F': '#2f5596', 'd': '#1e3868', 'b': '#c8d2e0'})),
    dict(name='frostlake_scale', after='emperor_tuna_fin', group='tools', category='tools', stack=16,
         names=T('Frostlake Scale', '冰湖霜鱗', '冰湖霜鳞'),
         mechanics=T(['A scale of the Frostlake Char, cold as the lake it came from. A keepsake; with a Weighted Bobber it makes a Frost Scale Bobber.'],
                     ['冰湖主的鱗，和牠住的湖一樣冰。紀念品；和重墜浮標可以做成霜鱗浮標。'], ['冰湖主的鳞，和它住的湖一样冰。纪念品；和重坠浮标可以做成霜鳞浮标。']),
         used_by=[ID('frost_scale_bobber')],
         icon=(['................', '................', '.....OOOOOO.....', '...OOiiiiiiOO...', '..OiihhiiiiiiO..',
                '..OihhiiiiIIiO..', '.OiihiiiiIIIIiO.', '.OiiiiiiIIIIIiO.', '.OiiiiiIIIIIIiO.', '..OiiiIIIIIIiO..',
                '..OIiIIIIIIIIO..', '...OIIIIIIIIO...', '....OOIIIIOO....', '......OOOO......', '................',
                '................'], {'O': '#27405a', 'i': '#bfe4f4', 'I': '#86bfe0', 'h': '#ffffff'})),
    dict(name='whisker_line', after='glow_line', group='tools', category='tools', stack=16,
         names=T('River Lord Whisker Line', '河伯鬚線', '河伯须线'),
         mechanics=T(['Tackle part (line), made from a River Lord Whisker and a Hemp Line. Holds two more pulls and fish bite no slower. Counts as a Wire Line for the Lava Dragon Koi.'],
                     ['釣具部件（線），用河伯鬚和麻線做成。多撐兩次拉扯，咬鉤不會變慢。釣熔岩龍鯉時視同鋼絲線。'],
                     ['钓具部件（线），用河伯须和麻线做成。多撑两次拉扯，咬钩不会变慢。钓熔岩龙鲤时视同钢丝线。']),
         recipe=['river_lord_whisker', 'hemp_line'],
         icon=(['................', '................', '....OOOOOOOO....', '...OllLLLLllO...', '..OlLOOOOOOLlO..',
                '..OLO......OLO..', '.OlLO......OLlO.', '.OlLO......OLlO.', '.OlLO......OLlO.', '..OLO......OLO..',
                '..OlLOOOOOOLlO..', '...OllLLLLllOOO.', '....OOOOOOOOlLO.', '............OOO.', '................',
                '................'], {'O': '#1c1410', 'l': '#6e5a4a', 'L': '#4a3a2e'})),
    dict(name='emperor_bone_hook', after='lure_hook', group='tools', category='tools', stack=16,
         names=T('Emperor Bone Hook', '皇鮪骨鉤', '皇鲔骨钩'),
         mechanics=T(['Tackle part (hook), made from an Emperor Bluefin Dorsal and a Bone Hook. Less common fish bite much more often (x1.5) and large fish are more likely, with no extra wear. Counts as a Bone Hook for the River Lord Catfish.'],
                     ['釣具部件（鉤），用皇鮪背鰭和骨鉤做成。少見的魚上鉤多很多（×1.5），大型魚的機會更高，而且不會多磨損釣竿。釣河伯鯰時視同骨鉤。'],
                     ['钓具部件（钩），用皇鲔背鳍和骨钩做成。少见的鱼上钩多很多（×1.5），大型鱼的机会更高，而且不会多磨损钓竿。钓河伯鲶时视同骨钩。']),
         recipe=['emperor_tuna_fin', 'bone_hook'],
         icon=(['................', '.........OOO....', '........OhhO....', '........OhO.....', '........OhO.....',
                '........OhO.....', '........OhO.....', '........OhO.....', '..OO....OhO.....', '.OtO....OhO.....',
                '.OttO..OhhO.....', '..OthOOhhO......', '...OhhhhO.......', '....OOOO........', '................',
                '................'], {'O': '#101828', 'h': '#eae4d2', 't': '#3f6fb8'})),
    dict(name='dragon_scale_bobber', after='feather_bobber', group='tools', category='tools', stack=16,
         names=T('Dragon Scale Bobber', '龍鱗浮標', '龙鳞浮标'),
         mechanics=T(['Tackle part (bobber), made from a Dragon Scale and a Bamboo Bobber. Fish bite sooner (15%) and you get more time to strike.'],
                     ['釣具部件（浮標），用龍鱗和竹節浮標做成。咬鉤快 15%，上鉤的反應時間也更長。'],
                     ['钓具部件（浮标），用龙鳞和竹节浮标做成。咬钩快 15%，上钩的反应时间也更长。']),
         recipe=['dragon_scale', 'bamboo_bobber'],
         icon=(BOBBER, {'O': O, 's': '#c9a24a', 'a': '#f2a22c', 'A': '#f8d070', 'b': '#c8402c', 'B': '#8a2418'})),
    dict(name='frost_scale_bobber', after='dragon_scale_bobber', group='tools', category='tools', stack=16,
         names=T('Frost Scale Bobber', '霜鱗浮標', '霜鳞浮标'),
         mechanics=T(['Tackle part (bobber), made from a Frostlake Scale and a Weighted Bobber. Sinks the bait 6 blocks deeper, and fish bite much sooner at night.'],
                     ['釣具部件（浮標），用冰湖霜鱗和重墜浮標做成。水深算多 6 格，夜晚咬鉤快很多。'],
                     ['钓具部件（浮标），用冰湖霜鳞和重坠浮标做成。水深算多 6 格，夜晚咬钩快很多。']),
         recipe=['frostlake_scale', 'weighted_bobber'],
         icon=(BOBBER, {'O': '#27405a', 's': '#8a96a4', 'a': '#e6f6fc', 'A': '#ffffff', 'b': '#86bfe0', 'B': '#4f8fc0'})),
]
NEW_PARTS = {
    'whisker_line': {'slot': 'line', 'strain': 2, 'as': ID('wire_line')},
    'emperor_bone_hook': {'slot': 'hook', 'rare': 1.5, 'size': 1, 'as': ID('bone_hook')},
    'dragon_scale_bobber': {'slot': 'bobber', 'bite': 0.85, 'window': 10, 'style': 7},
    'frost_scale_bobber': {'slot': 'bobber', 'depth': 6, 'night': 0.75, 'style': 8},
}
# item, block it copies (models are borrowed for now, on a re-tinted texture), tint, feast data, recipe, effects
LEGEND_FEASTS = [
    dict(name='river_lord_casserole', after='frostlake_platter', like='oden_pot', tint='clay_pot',
         names=T('River Lord Casserole', '河伯鯰砂鍋', '河伯鲶砂锅'),
         mechanics=T(['The River Lord Catfish simmered whole in a clay pot. One block, four bites; share it for the feast bonus.'],
                     ['整條河伯鯰放進砂鍋慢燉。占一格，可以吃四口；大家一起吃有宴席加成。'], ['整条河伯鲶放进砂锅慢炖。占一格，可以吃四口；大家一起吃有宴席加成。']),
         feast={'parts': [[0, 0, 0]], 'dirs': [0, 1, 2, 3], 'bites': 4, 'nutrition': 5, 'saturation': 0.9,
                'remains': ['minecraft:cauldron'], 'face': True},
         recipe=[ID('river_lord_catfish'), 'minecraft:brown_mushroom', 'minecraft:carrot', 'kaleidoscope_cookery:lettuce', 'minecraft:cauldron'],
         effects=[{'effect': 'resistance', 'duration': 600, 'amplifier': 0}, {'effect': 'regeneration', 'duration': 300, 'amplifier': 0}],
         icon=(['................', '................', '................', '..OO........OO..', '.OccOOOOOOOOccO.',
                '.OcOssggssssOcO.', '..OsswwsssggsO..', '.OCssssswwsssCO.', '.OCCssggssssCCO.', '.OCCCCCCCCCCCCO.',
                '..OCCCCCCCCCCO..', '..OCCcCCCCcCCO..', '...OCCCCCCCCO...', '....OOOOOOOO....', '................',
                '................'], {'O': O, 'C': '#9a5a34', 'c': '#b9774a', 's': '#e9d9a8', 'g': '#6fa84a', 'w': '#f6efe0'})),
    dict(name='dragon_koi_sizzle', after='river_lord_casserole', like='grilled_fish_plank', tint='stone_slab',
         names=T('Dragon Koi Stone Grill', '龍鯉石板燒', '龙鲤石板烧'),
         mechanics=T(['The Lava Dragon Koi seared on hot stone. A 1x2 board, three bites a block; share it for the feast bonus.'],
                     ['熔岩龍鯉放在滾燙的石板上炙燒。占 1×2 格，每格三口；大家一起吃有宴席加成。'], ['熔岩龙鲤放在滚烫的石板上炙烧。占 1×2 格，每格三口；大家一起吃有宴席加成。']),
         feast={'parts': [[0, 0, 0], [1, 0, 1]], 'dirs': [0, 1, 2, 3], 'bites': 3, 'nutrition': 4, 'saturation': 0.8,
                'remains': ['minecraft:cobblestone']},
         recipe=[ID('lava_dragon_koi'), 'kaleidoscope_cookery:red_chili', 'kaleidoscope_cookery:green_chili', 'minecraft:cobblestone'],
         effects=[{'effect': 'fire_resistance', 'duration': 2400, 'amplifier': 0}, {'effect': 'strength', 'duration': 600, 'amplifier': 0}],
         icon=(['................', '................', '................', '................', '..OOOOOOOOOOOO..',
                '.OkkkkkkkkkkkkO.', 'OkkrrRRRRRrrykkO', 'OkrRRhRRRRRRrykO', 'OkkrRRRRRRRrgkkO', 'OkkkrrRRRrrkgkkO',
                '.OkkkkkkkkkkkkO.', '..OKKKKKKKKKKO..', '...OOOOOOOOOO...', '................', '................',
                '................'], {'O': O, 'k': '#6b6b72', 'K': '#4c4c54', 'r': '#c8402c', 'R': '#e8683c', 'h': '#f8b070',
                                      'y': '#f2c84a', 'g': '#6fa84a'})),
]


def tinted(src, dst, tint):
    """A copy of a texture (and of its texture set, MER and height maps) with its colours changed: tint is an
    (r, g, b) multiplier, or a function (r, g, b) -> (r, g, b)."""
    im = Image.open(src + '.png').convert('RGBA')
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if callable(tint):
                px[x, y] = tuple(max(0, min(255, int(v))) for v in tint(r, g, b)) + (a,)
            else:
                px[x, y] = (min(255, int(r * tint[0])), min(255, int(g * tint[1])), min(255, int(b * tint[2])), a)
    im.save(dst + '.png')
    s, d = os.path.basename(src), os.path.basename(dst)
    if os.path.exists(src + '.texture_set.json'):
        write(dst + '.texture_set.json', read(src + '.texture_set.json').replace(s, d))
        for extra in ('_mer.png', '_height.png', '_normal.png'):
            if os.path.exists(src + extra):
                Image.open(src + extra).save(dst + extra)


def _hsv(r, g, b):
    import colorsys
    return colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)


def _rgb(h, s, v):
    import colorsys
    return tuple(c * 255 for c in colorsys.hsv_to_rgb(h, s, v))


def clay_pot(r, g, b):
    """The Oden Pot's grey metal becomes a terracotta clay pot; the broth turns a deeper, browner gold."""
    h, s, v = _hsv(r, g, b)
    if s < 0.15:
        return _rgb(0.045, 0.58, min(1.0, v * 1.05))
    return _rgb(h * 0.85, min(1.0, s * 1.05), v * 0.85)


def stone_slab(r, g, b):
    """The Grilled Fish Plank's brown wood becomes dark grey stone; the pale fish becomes a red-gold koi."""
    h, s, v = _hsv(r, g, b)
    if s >= 0.5 and 0.02 <= h <= 0.12:                  # wood
        return _rgb(0.6, 0.06, min(1.0, v * 0.95 + 0.06))
    if s < 0.2 and v > 0.6:                             # the fish
        return _rgb(0.03 + 0.06 * (1 - v), 0.72, min(1.0, v * 0.92))
    return (r, g, b)


def shapeless(rid, ingredients, result):
    ing = [{'item': i} for i in ingredients]
    write_json(os.path.join(BP, 'recipes', 'crafting', rid + '.json'), {'format_version': '1.20.10', 'minecraft:recipe_shapeless': {
        'description': {'identifier': ID(rid)}, 'tags': ['crafting_table'], 'ingredients': ing,
        'result': {'item': ID(result), 'count': 1}, 'unlock': ing[:1]}})


def guide_recipe(ingredients, result):
    return [{'method': 'Crafting Table', 'ingredients': list(ingredients), 'count': 1, 'time': 0, 'result': ID(result)}]


def ing_key(i):
    ns, name = i.split(':')
    return f'{NS}.name.{name}' if ns == NS else f'{NS}.ing.{ns}.{name}'


def legends():
    add_lang(f'{NS}.ing.minecraft.cobblestone', T('Cobblestone', '鵝卵石', '圆石'), f'{NS}.ing.minecraft.cauldron')
    # keepsakes and the parts made from them
    for it in LEGEND_ITEMS:
        it = dict(it)
        recipe = it.pop('recipe', None)
        if recipe:
            ids = [ID(r) for r in recipe]
            shapeless(it['name'], ids, it['name'])
            it['recipes'] = guide_recipe(ids, it['name'])
        add_item(**it)
    keep = load('KEEPSAKES')
    keep[ID('emperor_tuna')] = ID('emperor_tuna_fin')
    keep[ID('frostlake_char')] = ID('frostlake_scale')
    save('KEEPSAKES', keep)
    parts = load('PARTS')
    for name, p in NEW_PARTS.items():
        parts[ID(name)] = p
    save('PARTS', parts)
    styles = load('LINE_STYLE')
    styles[ID('whisker_line')] = 'line_whisker'
    save('LINE_STYLE', styles)

    # the whisker line's colour on the water, and the two new bobber looks (styles 7 and 8)
    tinted(os.path.join(RP, 'textures', 'particle', 'kfv_line_wire'), os.path.join(RP, 'textures', 'particle', 'kfv_line_whisker'), (0.5, 0.42, 0.36))
    write(os.path.join(RP, 'particles', 'line_whisker.json'), read(os.path.join(RP, 'particles', 'line_wire.json')).replace('line_wire', 'line_whisker'))
    ent = os.path.join(RP, 'textures', 'entity')
    tinted(os.path.join(ent, 'kfv_bobber_legend'), os.path.join(ent, 'kfv_bobber_dragon'), (1.0, 0.62, 0.42))
    tinted(os.path.join(ent, 'kfv_bobber_weighted'), os.path.join(ent, 'kfv_bobber_frost'), (0.78, 1.0, 1.25))
    path = os.path.join(RP, 'entity', 'bobber.entity.json')
    client = json.loads(read(path))
    tex = client['minecraft:client_entity']['description']['textures']
    tex['dragon'], tex['frost'] = 'textures/entity/kfv_bobber_dragon', 'textures/entity/kfv_bobber_frost'
    write_json(path, client)
    path = os.path.join(RP, 'render_controllers', 'kfv_bobber.render_controllers.json')
    rc = json.loads(read(path))
    skins = rc['render_controllers']['controller.render.kfv_bobber']['arrays']['textures']['Array.skins']
    for s in ('Texture.dragon', 'Texture.frost'):
        if s not in skins:
            skins.append(s)
    assert skins.index('Texture.dragon') == 7 and skins.index('Texture.frost') == 8
    write_json(path, rc)
    path = os.path.join(BP, 'entities', 'bobber.json')
    server = json.loads(read(path))
    server['minecraft:entity']['description']['properties'][f'{NS}:style']['range'] = [0, 8]
    write_json(path, server)

    # the two feasts
    feasts, effects, hints = load('FEASTS'), load('FOOD_EFFECTS'), load('RECIPE_HINTS')
    terrain_path = os.path.join(RP, 'textures', 'terrain_texture.json')
    terrain = json.loads(read(terrain_path))
    for f in LEGEND_FEASTS:
        name, like = f['name'], f['like']
        shapeless(name, f['recipe'], name)
        add_item(name=name, names=f['names'], icon=f['icon'], after=f['after'], group='placeable_foods', stack=16,
                 components={'minecraft:tags': {'tags': ['kaleidoscope_cookery:placeable_food']}})
        entry = guide_entry(name, 'dishes', 16, f['mechanics'], recipes=guide_recipe(f['recipe'], name), kinds=('item', 'block'))
        add_guide(entry, f['names'], f['after'])
        blocks = os.path.join(RP, 'textures', 'blocks')
        # its own model and texture come from tools/gen_models_1_4.py; until then a re-coloured copy of the borrowed one
        if not os.path.exists(os.path.join(RP, 'models', 'blocks', f'{name}.geo.json')):
            tinted(os.path.join(blocks, f'kfv_{like}'), os.path.join(blocks, f'kfv_{name}'),
                   globals()[f['tint']] if isinstance(f['tint'], str) else f['tint'])
        terrain['texture_data'][f'kfv_{name}'] = {'textures': f'textures/blocks/kfv_{name}'}
        block = read(os.path.join(BP, 'blocks', f'{like}_block.json'))
        block = block.replace(f'{NS}:{like}_block', f'{NS}:{name}_block').replace(f'display.item.{like}', f'display.item.{name}') \
                     .replace(f'"kfv_{like}"', f'"kfv_{name}"')
        if os.path.exists(os.path.join(RP, 'models', 'blocks', f'{name}.geo.json')):
            block = block.replace(f'geometry.{NS}.{like}_', f'geometry.{NS}.{name}_')
        write(os.path.join(BP, 'blocks', f'{name}_block.json'), block)
        feasts[ID(name + '_block')] = dict(item=ID(name), **f['feast'])
        effects[ID(name)] = f['effects']
        if not any(h['id'] == ID(name) for h in hints):
            counts = {}
            for i in f['recipe']:
                counts[i] = counts.get(i, 0) + 1
            hints.append({'id': ID(name), 'nameKey': f'{NS}.name.{name}', 'icon': f'textures/items/kfv_{name}', 'method': 'crafting',
                          'count': 1, 'ingredients': [[ing_key(i), n] for i, n in counts.items()]})
    write_json(terrain_path, terrain)
    save('FEASTS', feasts)
    save('FOOD_EFFECTS', effects)
    save('RECIPE_HINTS', hints)

    # the two older keepsakes say what they are for now
    g = load('GUIDEBOOK_JSON')
    more = {'river_lord_whisker': (T(' With a Hemp Line it makes a River Lord Whisker Line.', '和麻線可以做成河伯鬚線。', '和麻线可以做成河伯须线。'), 'whisker_line'),
            'dragon_scale': (T(' With a Bamboo Bobber it makes a Dragon Scale Bobber.', '和竹節浮標可以做成龍鱗浮標。', '和竹节浮标可以做成龙鳞浮标。'), 'dragon_scale_bobber')}
    for e in g['entries']:
        name = e['id'].split(':')[1]
        if name in more:
            text, part = more[name]
            for lang, lines in e['mechanicsByLocale'].items():
                if not lines[0].endswith(text[lang]):
                    lines[0] += text[lang]
            e['mechanics'] = list(e['mechanicsByLocale']['en_US'])
            e['usedBy'] = [ID(part)]
    save('GUIDEBOOK_JSON', g, indent=1)


# --------------------------------------------------------------------------- guidebook text for script features
def journal_page():
    """The Angler's Journal page says what 1.4.0 added to the journal (the features themselves are scripts)."""
    more = T(["A water whose every species you have caught is marked, and gives a reward the first time you open its page.",
              "The tide page also shows the fish merchant's order: sell him the fish it names and he hands over a reward when it is filled. The order's fish hangs low on his pole.",
              "Settings: the look of the reeling minigame's bar (each player's own); operators can also turn the minigame off for the world."],
             ["某個水域的魚全部釣過後，該頁會打勾，第一次翻開時還會給一份獎勵。",
              "潮汐頁也會顯示漁販的訂單：把訂單上的魚賣給他，交齊後他會給一份獎勵。訂單的魚掛在他扁擔的下方。",
              "設定：收線小遊戲軌道的字元樣式（每位玩家各自設定）；管理員還可以替整個世界關閉小遊戲。"],
             ["某个水域的鱼全部钓过后，该页会打勾，第一次翻开时还会给一份奖励。",
              "潮汐页也会显示渔贩的订单：把订单上的鱼卖给他，交齐后他会给一份奖励。订单的鱼挂在他扁担的下方。",
              "设置：收线小游戏轨道的字符样式（每位玩家各自设置）；管理员还可以替整个世界关闭小游戏。"])
    g = load('GUIDEBOOK_JSON')
    page = next(e for e in g['entries'] if e['id'] == ID('angler_journal'))
    for lang, lines in page['mechanicsByLocale'].items():
        for line in more[lang]:
            if line not in lines:
                lines.append(line)
    page['mechanics'] = list(page['mechanicsByLocale']['en_US'])
    basket = next(e for e in g['entries'] if e['id'] == ID('fish_basket'))
    note = T('Legends go in too; a record fish (★) stays in your pockets.', '傳說魚也會進魚簍；破紀錄的魚（★）會留在背包。', '传说鱼也会进鱼篓；破纪录的鱼（★）会留在背包。')
    for lang, lines in basket['mechanicsByLocale'].items():
        if note[lang] not in lines:
            lines.append(note[lang])
    basket['mechanics'] = list(basket['mechanicsByLocale']['en_US'])
    save('GUIDEBOOK_JSON', g, indent=1)


# --------------------------------------------------------------------------- dishes
def bowl(rows, palette):
    """A 16x16 bowl icon: `rows` are the three rows of food showing over the rim (12, 14 and 12 pixels wide)."""
    assert [len(r) for r in rows] == [8, 12, 12], rows
    grid = ['................'] * 3 + ['....' + rows[0].replace(rows[0], 'OOOOOOOO') + '....',
                                       '..OO' + rows[0] + 'OO..', '.O' + rows[1] + 'O.', '.Ob' + rows[2][1:-1] + 'bO.',
                                       '.OBbbbbbbbbbbBO.', '..OBBBBBBBBBBO..', '..OBBBBBBBBBBO..', '...OBBBBBBBBO...',
                                       '....OOBBBBOO....', '......OOOO......'] + ['................'] * 3
    pal = {'O': O, 'B': '#b9774a', 'b': '#d79a66'}
    pal.update(palette)
    return grid, pal


RICE, CR, FS = 'kaleidoscope_cookery:rice', 'kaleidoscope_cookery:cooked_rice', ID('fish_stock')
# name, names, food (nutrition, saturation), station ('wok' | 'stockpot' | 'crafting'), ingredients, time, base, effects, icon
NEW_DISHES = [
    dict(name='stir_fried_shrimp', names=T('Stir-fried Shrimp', '清炒蝦仁', '清炒虾仁'), food=(8, 0.7), station='wok', time=200,
         ingredients=[ID('shrimp_meat'), ID('shrimp_meat'), 'kaleidoscope_cookery:green_chili', 'minecraft:carrot'], effects=[],
         icon=bowl(['pPgppPcp', 'ppPppcpPgppP', 'PpgpPppPpcpP'], {'p': '#f8cdbf', 'P': '#ec9a86', 'g': '#6fa84a', 'c': '#f09030'})),
    dict(name='crab_congee', names=T('Crab Congee', '蟹肉粥', '蟹肉粥'), food=(9, 0.8), station='stockpot', time=300, base=FS,
         ingredients=[RICE, ID('crab_meat'), 'minecraft:carrot'],
         effects=[{'effect': 'regeneration', 'duration': 100, 'amplifier': 0}],
         icon=bowl(['wwrwwwcw', 'wwwwrwwwwwcw', 'wcwwwwrwwwww'], {'w': '#f6efe0', 'r': '#e8765a', 'c': '#f09030'})),
    dict(name='shrimp_noodle_soup', names=T('Shrimp Noodle Soup', '鮮蝦湯麵', '鲜虾汤面'), food=(9, 0.8), station='stockpot', time=300,
         base='minecraft:water', ingredients=['kaleidoscope_cookery:raw_noodles', ID('shrimp_meat'), ID('shrimp_shell')], effects=[],
         icon=bowl(['nsnPpsng', 'snnsPpPnsnns', 'nsnnsnnPpnsn'], {'n': '#f2dc9a', 's': '#e8b860', 'p': '#f8cdbf', 'P': '#ec9a86', 'g': '#6fa84a'})),
    dict(name='crab_roe_rice', names=T('Crab Roe Rice Bowl', '蟹黃蓋飯', '蟹黄盖饭'), food=(10, 0.8), station='crafting', time=0,
         ingredients=[CR, ID('crab_roe'), ID('crab_roe'), ID('nori'), 'minecraft:bowl'],
         effects=[{'effect': 'absorption', 'duration': 600, 'amplifier': 0}],
         icon=bowl(['wyYYYywk', 'wwyYYhYYywkw', 'wwwyYYYywwww'], {'w': '#fbf3e8', 'Y': '#f2a22c', 'y': '#f8c458', 'h': '#fde6a0', 'k': '#2c3a2a'})),
    dict(name='jellyfish_salad', names=T('Jellyfish Salad', '涼拌海蜇皮', '凉拌海蜇皮'), food=(6, 0.6), station='crafting', time=0,
         ingredients=[ID('jellyfish_skin'), ID('jellyfish_skin'), 'kaleidoscope_cookery:lettuce', 'kaleidoscope_cookery:red_chili', 'minecraft:bowl'],
         effects=[{'effect': 'water_breathing', 'duration': 600, 'amplifier': 0}],
         icon=bowl(['jJjgjJrj', 'jjJjjgJjjrJj', 'JjjgjJjjJjgj'], {'j': '#f3ead6', 'J': '#d9c8a4', 'g': '#6fa84a', 'r': '#d8452c'})),
]
METHOD = {'wok': 'Wok', 'stockpot': 'Stockpot', 'crafting': 'Crafting Table'}
BASE_ITEM = {FS: ID('fish_stock_bucket'), ID('dashi'): ID('dashi_bucket')}       # what the journal and guidebook list for a base
# small changes to dishes that were already there
MORE_STAND_INS = [('wok/seafood_chow_mein', 'shrimp', 'shrimp_meat'), ('wok/paella', 'shrimp', 'shrimp_meat'),
                  ('stockpot/seafood_hot_pot', 'shrimp', 'shrimp_meat')]
MORE_EFFECTS = {      # well-earned dishes that gave nothing but hunger
    'steamed_king_crab': [{'effect': 'absorption', 'duration': 1200, 'amplifier': 0}],
    'steamed_lobster': [{'effect': 'regeneration', 'duration': 100, 'amplifier': 0}],
    'karasumi_fried_rice': [{'effect': 'haste', 'duration': 600, 'amplifier': 0}],
    'crab_roe_bun': [{'effect': 'regeneration', 'duration': 60, 'amplifier': 0}],
}


def dishes():
    kc, effects, hints = load('KC_RECIPES'), load('FOOD_EFFECTS'), load('RECIPE_HINTS')
    after = 'shrimp_paste_fried_rice'
    for d in NEW_DISHES:
        name, n, s = d['name'], d['food'][0], d['food'][1]
        add_item(name=name, names=d['names'], icon=d['icon'], after=after, group='foods', food=d['food'],
                 components={'minecraft:food': {'nutrition': n, 'saturation_modifier': s, 'can_always_eat': False,
                                                'using_converts_to': 'minecraft:bowl'}})
        base = d.get('base')
        shown = ([BASE_ITEM[base]] if base in BASE_ITEM else []) + [i for i in d['ingredients']]
        entry = {'id': ID(name), 'category': 'dishes', 'kinds': ['item'], 'stack': 64, 'icon': f'textures/items/kfv_{name}',
                 'food': {'nutrition': n, 'saturation': s, 'returns': 'minecraft:bowl'},
                 'recipes': [{'method': METHOD[d['station']], 'ingredients': shown, 'count': 1, 'time': d['time'], 'result': ID(name)}]}
        add_guide(entry, d['names'], after)
        if d['station'] == 'crafting':
            shapeless(name, d['ingredients'], name)
        else:
            rid = ID(f"{d['station']}/{name}")
            recipe = {'id': rid, 'ingredients': d['ingredients'], 'result': ID(name), 'count': 1}
            if d['station'] == 'wok':
                recipe.update(carrier='minecraft:bowl', time=d['time'])
                kind = 'wok'
            else:
                recipe.update(time=d['time'], base=base, carrier='minecraft:bowl', finishedKind='default')
                kind = 'stockpot_exact'
            kc = [r for r in kc if r['recipe']['id'] != rid] + [{'kind': kind, 'recipe': recipe}]
        if d['effects']:
            effects[ID(name)] = d['effects']
        counts = {}
        for i in shown:
            counts[i] = counts.get(i, 0) + 1
        hints = [h for h in hints if h['id'] != ID(name)] + [{
            'id': ID(name), 'nameKey': f'{NS}.name.{name}', 'icon': f'textures/items/kfv_{name}', 'method': d['station'],
            'count': 1, 'ingredients': [[ing_key(i), c] for i, c in counts.items()]}]
        after = name
    for rid, old, new in MORE_STAND_INS:
        ing = next(r['recipe'] for r in kc if r['recipe']['id'] == ID(rid))['ingredients']
        for i, slot in enumerate(ing):
            if slot == ID(old):
                ing[i] = [ID(old), ID(new)]
    for name, fx in MORE_EFFECTS.items():
        effects.setdefault(ID(name), fx)
    save('KC_RECIPES', kc)
    save('FOOD_EFFECTS', effects)
    save('RECIPE_HINTS', hints)
    # the new ingredients' pages list the dishes that use them
    g = load('GUIDEBOOK_JSON')
    uses = {'shrimp_meat': ['stir_fried_shrimp', 'shrimp_noodle_soup', 'seafood_chow_mein', 'paella', 'seafood_hot_pot'],
            'shrimp_shell': ['shrimp_noodle_soup'], 'crab_meat': ['crab_congee'], 'crab_roe': ['crab_roe_rice'],
            'jellyfish_skin': ['jellyfish_salad']}
    text = {'jellyfish_skin': T(['Sliced from a jellyfish on the Fish Cleaning Board. Crunchy; eat it as it is or toss it into a Jellyfish Salad.'],
                                ['在魚案板上切水母得到。口感爽脆，可以直接吃，或做成涼拌海蜇皮。'], ['在鱼案板上切水母得到。口感爽脆，可以直接吃，或做成凉拌海蜇皮。'])}
    for e in g['entries']:
        name = e['id'].split(':')[1]
        for dish in uses.get(name, []):
            if ID(dish) not in e.setdefault('usedBy', []):
                e['usedBy'].append(ID(dish))
        if name in text:
            e['mechanicsByLocale'] = {k: list(v) for k, v in text[name].items()}
            e['mechanics'] = list(text[name]['en_US'])
    save('GUIDEBOOK_JSON', g, indent=1)


# --------------------------------------------------------------------------- fish tanks
TANK_MORE = [('shrimp', 'cave_crayfish'), ('purpur_shrimp', 'cave_crayfish'), ('oyster', 'cave_crayfish')]   # new species, whose fit it borrows


def tank():
    """Shrimp, Purpur Shrimp and Oysters can live in the Fish Tank (lava creatures wait for the lava tank)."""
    import re
    fish = load('TANK_FISH')
    path = os.path.join(BP, 'scripts', 'data', 'tank.js')
    js = read(path)
    kind = json.loads(re.search(r'export const TANK_KIND = (\[.*?\]);', js).group(1))
    fit = json.loads(re.search(r'export const FIT = (\[.*\]);', js).group(1))
    client_path = os.path.join(RP, 'entity', 'tank_fish.entity.json')
    client = json.loads(read(client_path))
    geos = client['minecraft:client_entity']['description']['geometry']
    rc_path = os.path.join(RP, 'render_controllers', 'kfv_tank_fish.render_controllers.json')
    rc = json.loads(read(rc_path))
    array = next(iter(rc['render_controllers'].values()))['arrays']['geometries']['Array.geos']
    for name, like in TANK_MORE:
        if ID(name) not in fish:
            fish.append(ID(name))
        i, src = fish.index(ID(name)), fish.index(ID(like))
        for table in (kind, fit):                       # tables are indexed by species (TANK_FISH position)
            while len(table) <= i:
                table.append(None)
            table[i] = json.loads(json.dumps(table[src]))
        own = f'geometry.{NS}.tank_fish.{name}'                 # its own model (tools/gen_models_1_4.py), else the look-alike's
        geos[name] = own if own in read(os.path.join(RP, 'models', 'entity', 'tank_fish.geo.json')) else geos[like]
        if name == 'oyster':                            # it sits still: no stroll along the floor
            fit[i] = [[[scale, 0, lo, hi] for scale, _, lo, hi in tank] for tank in fit[i]]
        while len(array) <= i:
            array.append(None)
        array[i] = f'Geometry.{name}'
    assert None not in array and len(array) == len(fish), (len(array), len(fish))
    assert len(fish) <= 63, 'the tank has two states for the fish index: 16 x 4'
    save('TANK_FISH', fish)
    js = re.sub(r'export const TANK_KIND = \[.*?\];', lambda m: 'export const TANK_KIND = ' + json.dumps(kind[:len(fish)]) + ';', js)
    js = re.sub(r'export const FIT = \[.*\];', lambda m: 'export const FIT = ' + json.dumps(fit[:len(fish)], separators=(',', ':')) + ';', js)
    write(path, js)
    write_json(client_path, client)
    write_json(rc_path, rc)
    g = load('GUIDEBOOK_JSON')
    note = T('Shrimp and oysters can live in it too. Anything fished from lava cannot.', '蝦和牡蠣也可以養。岩漿裡釣到的漁獲不能放。', '虾和牡蛎也可以养。岩浆里钓到的渔获不能放。')
    old = T('Shrimp can live in it too. Oysters and anything fished from lava cannot.', '蝦也可以養。牡蠣和岩漿裡釣到的漁獲不能放。', '虾也可以养。牡蛎和岩浆里钓到的渔获不能放。')
    page = next(e for e in g['entries'] if e['id'] == ID('fish_tank'))
    for lang, lines in page['mechanicsByLocale'].items():
        if old[lang] in lines:
            lines.remove(old[lang])
        if note[lang] not in lines:
            lines.append(note[lang])
    page['mechanics'] = list(page['mechanicsByLocale']['en_US'])
    save('GUIDEBOOK_JSON', g, indent=1)


if __name__ == '__main__':
    cleaning()
    legends()
    journal_page()
    dishes()
    tank()
    print('done; now run: python tools/build.py build')
