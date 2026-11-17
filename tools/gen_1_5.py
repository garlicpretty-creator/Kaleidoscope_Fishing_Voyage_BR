"""Content added in 1.5.0, step by step as docs/PLAN_1.5.0.md lays it out. Run again any time:

  python tools/icons_1_5.py && python tools/gen_1_5.py && python tools/build.py build
"""
import content as c
import os
c.os = os

NS = c.NS + ':'


def legends():
    """Step 1: keepsakes for the two legends that had none, and tackle made from all four keepsakes."""
    # ---- keepsakes
    keep = c.data('KEEPSAKES')
    keep[NS + 'emperor_tuna'] = NS + 'emperor_tuna_fin'
    keep[NS + 'frostlake_char'] = NS + 'frostlake_scale'
    c.save('KEEPSAKES', keep)
    for key, name, text, after in [
        ('emperor_tuna_fin', ('Emperor Bluefin Dorsal Fin', '皇鮪背鰭', '皇鲔背鳍'),
         ('The tall dorsal fin of the Emperor Bluefin. A keepsake; with a Bone Hook it makes an Emperor Bone Hook.',
          '藍鰭皇鮪高聳的背鰭。紀念品；和骨鉤可以做成皇鮪骨鉤。', '蓝鳍皇鲔高耸的背鳍。纪念品；和骨钩可以做成皇鲔骨钩。'), 'dragon_scale'),
        ('frostlake_scale', ('Frostlake Scale', '冰湖霜鱗', '冰湖霜鳞'),
         ('A scale of the Frostlake Char, cold as the lake it came from. A keepsake; with a Weighted Bobber it makes a Frost Scale Bobber.',
          '冰湖主的鱗，和牠住的湖一樣冰。紀念品；和重墜浮標可以做成霜鱗浮標。', '冰湖主的鳞，和它住的湖一样冰。纪念品；和重坠浮标可以做成霜鳞浮标。'), 'emperor_tuna_fin'),
    ]:
        c.item(key)
        c.names(key, *name)
        c.icon(key)
        c.catalog(key, after)
        c.guide(key, 'tools', text, name)

    # ---- tackle: each keepsake and an ordinary part
    parts = c.data('PARTS')
    parts[NS + 'emperor_bone_hook'] = {'slot': 'hook', 'rare': 1.5, 'size': 1, 'as': NS + 'bone_hook'}
    parts[NS + 'whisker_line'] = {'slot': 'line', 'strain': 2, 'as': NS + 'wire_line'}
    parts[NS + 'dragon_scale_bobber'] = {'slot': 'bobber', 'bite': 0.85, 'window': 10, 'style': 7}
    parts[NS + 'frost_scale_bobber'] = {'slot': 'bobber', 'depth': 6, 'night': 0.75, 'style': 8}
    c.save('PARTS', parts)
    lines = c.data('LINE_STYLE')
    lines[NS + 'whisker_line'] = 'line_whisker'
    c.save('LINE_STYLE', lines)
    after = 'frostlake_scale'
    for key, made_of, name, text in [
        ('emperor_bone_hook', ('emperor_tuna_fin', 'bone_hook'), ('Emperor Bone Hook', '皇鮪骨鉤', '皇鲔骨钩'),
         ('Tackle part (hook), made from an Emperor Bluefin Dorsal Fin and a Bone Hook. Less common fish bite much more often (x1.5) and large fish are more likely, with no extra wear. Counts as a Bone Hook for the River Lord Catfish.',
          '釣具部件（鉤），用皇鮪背鰭和骨鉤做成。少見的魚上鉤多很多（×1.5），大型魚的機會更高，而且不會多磨損釣竿。釣河伯鯰時視同骨鉤。',
          '钓具部件（钩），用皇鲔背鳍和骨钩做成。少见的鱼上钩多很多（×1.5），大型鱼的机会更高，而且不会多磨损钓竿。钓河伯鲶时视同骨钩。')),
        ('whisker_line', ('river_lord_whisker', 'hemp_line'), ('River Lord Whisker Line', '河伯鬚線', '河伯须线'),
         ('Tackle part (line), made from a River Lord Whisker and a Hemp Line. Dark brown line; holds two more pulls and fish bite no slower. Counts as a Wire Line for the Lava Dragon Koi.',
          '釣具部件（線），用河伯鬚和麻線做成。深褐色的線，多撐兩次拉扯，咬鉤不會變慢。釣熔岩龍鯉時視同鋼絲線。',
          '钓具部件（线），用河伯须和麻线做成。深褐色的线，多撑两次拉扯，咬钩不会变慢。钓熔岩龙鲤时视同钢丝线。')),
        ('dragon_scale_bobber', ('dragon_scale', 'bamboo_bobber'), ('Dragon Scale Bobber', '龍鱗浮標', '龙鳞浮标'),
         ('Tackle part (bobber), made from a Dragon Scale and a Bamboo Bobber. An ember-red float: fish bite sooner (15%) and you get more time to strike.',
          '釣具部件（浮標），用龍鱗和竹節浮標做成。火紅色的浮標：咬鉤快 15%，上鉤的反應時間也更長。',
          '钓具部件（浮标），用龙鳞和竹节浮标做成。火红色的浮标：咬钩快 15%，上钩的反应时间也更长。')),
        ('frost_scale_bobber', ('frostlake_scale', 'weighted_bobber'), ('Frost Scale Bobber', '霜鱗浮標', '霜鳞浮标'),
         ('Tackle part (bobber), made from a Frostlake Scale and a Weighted Bobber. An ice-blue float: sinks the bait 6 blocks deeper, and fish bite much sooner at night.',
          '釣具部件（浮標），用冰湖霜鱗和重墜浮標做成。冰藍色的浮標：水深算多 6 格，夜晚咬鉤快很多。',
          '钓具部件（浮标），用冰湖霜鳞和重坠浮标做成。冰蓝色的浮标：水深算多 6 格，夜晚咬钩快很多。')),
    ]:
        c.item(key)
        c.names(key, *name)
        c.icon(key)
        c.catalog(key, after)
        recipe = c.shapeless(key, made_of)
        c.guide(key, 'tools', text, name, recipes=[recipe])
        for part in made_of:
            c.guide_used_by(part, key)
        after = key


def creel():
    """Step 1: the Fish Creel takes the four legends (they used to stay in the hand)."""
    items = c.data('BASKET_ITEMS')
    have = {i['id'] for i in items}
    for key in c.data('LEGENDS'):
        if key not in have:
            short = key.split(':')[1]
            items.append({'id': key, 'nameKey': f'{c.NS}.name.{short}', 'icon': f'textures/items/kfv_{short}'})
    c.save('BASKET_ITEMS', items)


def journal():
    """Step 1: the journal's settings page."""
    J = f'{c.NS}.journal.'
    for key, en, tw, cn in [
        ('settings', 'Settings', '設定', '设置'),
        ('settings_charset', 'Reeling track drawn as: %1$s', '收線軌道的樣式：%1$s', '收线轨道的样式：%1$s'),
        ('settings_use_block', 'Draw it with blocks  ▕██ ▏', '改用方塊字元 ▕██ ▏', '改用方块字符 ▕██ ▏'),
        ('settings_use_ascii', 'Draw it with plain characters  [## ]', '改用一般字元 [## ]', '改用普通字符 [## ]'),
        ('settings_minigame_on', 'Reeling minigame: on (for the whole world)', '收線小遊戲：開啟（整個世界）', '收线小游戏：开启（整个世界）'),
        ('settings_minigame_off', 'Reeling minigame: off (for the whole world)', '收線小遊戲：關閉（整個世界）', '收线小游戏：关闭（整个世界）'),
        ('settings_op_only', 'Only an operator can turn the minigame on or off.', '只有管理員可以開關小遊戲。', '只有管理员可以开关小游戏。'),
        ('settings_turn_off', 'Turn the minigame off', '關閉小遊戲', '关闭小游戏'),
        ('settings_turn_on', 'Turn the minigame on', '開啟小遊戲', '开启小游戏'),
    ]:
        c.lang(J + key, en, tw, cn, packs=(c.RP,))


def merchant_order():
    """Step 1: the tide page's lines for the merchant's order."""
    J = f'{c.NS}.journal.'
    for key, en, tw, cn in [
        ('market_order', "The fish merchant's order: ", '漁販的訂單：', '渔贩的订单：'),
        ('order_medium', ' (medium ◆◆ or larger)', '（中型 ◆◆ 以上）', '（中型 ◆◆ 以上）'),
        ('order_progress', 'handed in %1$s / %2$s', '已交 %1$s / %2$s', '已交 %1$s / %2$s'),
        ('order_done', 'filled', '已完成', '已完成'),
    ]:
        c.lang(J + key, en, tw, cn, packs=(c.RP,))


def tide_clock():
    """Step 2: the Tide Clock. Its model, texture and icon come from tools/gen_tide_clock.py; the moving hand and
    the moon are Molang in the resource pack (animations/tide_clock.animation.json, the render controller)."""
    name = ('Tide Clock', '潮汐鐘', '潮汐钟')
    # 1.5.0: used on a wall it hangs there (blocks/tide_clock.json below); in the hand it is still the dial
    c.item('tide_clock', stack=1, components={'minecraft:block_placer': {'block': c.full('tide_clock'), 'replace_block_item': True}})
    c.names('tide_clock', *name)
    c.icon('tide_clock')
    c.catalog('tide_clock', 'angler_journal')
    c.guide_name('minecraft:clock', 'Clock', '時鐘', '时钟')
    recipe = {'method': 'Crafting Table', 'ingredients': ['minecraft:copper_ingot', 'minecraft:copper_ingot', 'minecraft:clock',
              'minecraft:copper_ingot', 'minecraft:copper_ingot'], 'count': 1, 'time': 0, 'result': c.full('tide_clock')}
    c.guide('tide_clock', 'tools', (
        ['Hold it and look down at the dial. The hand goes round once every tide: while it points at the blue arc on the far rim the tide is high, anywhere else it is low.',
         "The small moon near the low mark shows tonight's moon phase.",
         'It only moves while you hold it: in the inventory or in an Item Frame the picture stays still.'],
        ['拿在手上低頭看盤面。指針每一次潮汐轉一圈：指著遠端的藍色弧段時是漲潮，其他位置是退潮。', '靠近退潮記號的小月亮顯示今晚的月相。',
         '只有拿在手上時才會動：在物品欄或物品展示框裡圖案是靜止的。'],
        ['拿在手上低头看盘面。指针每一次潮汐转一圈：指着远端的蓝色弧段时是涨潮，其他位置是退潮。', '靠近退潮记号的小月亮显示今晚的月相。',
         '只有拿在手上时才会动：在物品栏或物品展示框里图案是静止的。']), name, stack=1, recipes=[recipe])


def wall_tide_clock():
    """Step 2: the Tide Clock as a block on a wall. Model: tools/gen_tide_clock.py; hand and moon: blocks/tideClock.js."""
    import os
    ns = c.NS
    hand, moon = f'{ns}:hand', f'{ns}:moon'
    visible = {f'hand_{i}': f"q.block_state('{hand}') == {i}" for i in range(16)}
    visible.update({                         # as the held clock's render controller: 0 full .. 4 new .. 7 waxing gibbous
        'moon_l2': f"q.block_state('{moon}') <= 3",
        'moon_l1': f"q.block_state('{moon}') <= 2 || q.block_state('{moon}') == 7",
        'moon_r1': f"q.block_state('{moon}') <= 1 || q.block_state('{moon}') >= 6",
        'moon_r2': f"q.block_state('{moon}') == 0 || q.block_state('{moon}') >= 5",
    })
    box = {'origin': [-6, 2, 6], 'size': [12, 12, 2]}
    turn = {'north': 0, 'east': 270, 'south': 180, 'west': 90}
    c.write_json(os.path.join(c.BP, 'blocks', 'tide_clock.json'), {'format_version': '1.21.60', 'minecraft:block': {
        'description': {'identifier': c.full('tide_clock'), 'states': {hand: list(range(16)), moon: list(range(8))},
                        'traits': {'minecraft:placement_direction': {'enabled_states': ['minecraft:cardinal_direction'], 'y_rotation_offset': 180.0}}},
        'components': {
            'minecraft:display_name': f'%{ns}.display.item.tide_clock',
            'minecraft:material_instances': {'*': {'texture': 'kfv_tide_clock', 'render_method': 'alpha_test'}},
            'minecraft:geometry': {'identifier': 'geometry.kaleidoscope_fishing.wall_tide_clock', 'bone_visibility': visible},
            'minecraft:light_dampening': 0, 'minecraft:collision_box': box, 'minecraft:selection_box': box,
            'minecraft:destructible_by_mining': {'seconds_to_destroy': 0.4}, 'minecraft:map_color': '#C9A24A',
            'minecraft:loot': f'loot_tables/{ns}/blocks/tide_clock.json',
            f'{ns}:wall_decor': {}, f'{ns}:tide_clock': {},
            'minecraft:tick': {'interval_range': [100, 100], 'looping': True}},
        'permutations': [{'condition': f"q.block_state('minecraft:cardinal_direction') == '{d}'",
                          'components': {'minecraft:transformation': {'rotation': [0, r, 0]}}} for d, r in turn.items()]}})
    c.write_json(os.path.join(c.BP, 'loot_tables', ns, 'blocks', 'tide_clock.json'),
                 {'pools': [{'rolls': 1, 'entries': [{'type': 'item', 'name': c.full('tide_clock')}]}]})
    path = os.path.join(c.RP, 'textures', 'terrain_texture.json')
    t = c.read_json(path)
    t['texture_data']['kfv_tide_clock'] = {'textures': 'textures/entity/kfv_tide_clock'}
    c.write_json(path, t)
    g = c.data('GUIDEBOOK_JSON')
    for e in g['entries']:
        if e['id'] == c.full('tide_clock'):
            extra = {'en_US': 'Use it on a wall to hang it there; the hand and the moon keep moving. Break it to take it back.',
                     'zh_TW': '對牆面使用就掛上去，指針和月相照樣會動。打掉就拿回來。', 'zh_CN': '对墙面使用就挂上去，指针和月相照样会动。打掉就拿回来。'}
            for code, text in extra.items():
                if text not in e['mechanicsByLocale'][code]:
                    e['mechanicsByLocale'][code].append(text)
            e['mechanics'] = list(e['mechanicsByLocale']['en_US'])
            e['kinds'] = ['item', 'block']
    c.save('GUIDEBOOK_JSON', g)


def cleaning_format():
    """Step 3: every catch on the Fish Cleaning Board lists its own cuts. 1.4's fixed three cuts (scale, gut,
    fillet) are rewritten in the new form with the same result; tools/tests/cleaning_1_4.json keeps the old table
    and tools/tests/test_scripts.mjs checks the two agree for every fish.

      "first": the board's stage when the fish is laid down (1 whole; 2 for a fish with nothing to scale)
      "cuts":  [{"act": what the knife does (sound and particles), "out": [[item, count, chance?, "sized"?], ...]}]
               "sized": the count goes up by one for a large fish and down by one for a small one (never under 1)
    Each cut moves the board on one stage; the last one clears it."""
    table = c.data('CLEANING')
    for fish in table.values():
        if 'cuts' in fish:
            continue
        cuts = []
        if fish['scales']:
            cuts.append({'act': 'scale', 'out': [[NS + 'fish_scales', 1]]})
        cuts.append({'act': 'gut', 'out': [[NS + 'fish_offal', 1]] + [[i, 1, ch] for i, ch in fish['extra']]})
        last = [[fish['out'][0], fish['out'][1], 1, 'sized']]
        if fish['bones']:
            last.append([NS + 'fish_bones', fish['bones']])
        cuts.append({'act': 'fillet', 'out': last})
        for k in ('out', 'scales', 'bones', 'extra'):
            del fish[k]
        fish['first'] = 4 - len(cuts)
        fish['cuts'] = cuts
    c.save('CLEANING', table)


def food(nutrition, saturation):
    """The components that make an ingredient edible raw, as the pack's other raw seafood."""
    return {'minecraft:food': {'nutrition': nutrition, 'saturation_modifier': saturation, 'can_always_eat': False},
            'minecraft:use_animation': 'eat', 'minecraft:use_modifiers': {'use_duration': 1.6, 'movement_modifier': 0.33},
            'minecraft:tags': {'tags': ['minecraft:is_food']}}


def shellfish_board():
    """Step 4: shrimp, crab and jellyfish on the Fish Cleaning Board, and what they give.
    Board models: tools/gen_board_1_5.py (indices 44-54 there and here)."""
    # ---- what the cuts give
    G = lambda en, tw, cn: (en, tw, cn)
    products = [
        ('shrimp_head', G('Shrimp Head', '蝦頭', '虾头'), None,
         G('Taken off a shrimp, crayfish or lobster with the first cut on the Fish Cleaning Board. Boil three into Shrimp Head Stock; a bait in the Shrimp Trap.',
           '在魚案板上替蝦、螯蝦或龍蝦去頭得到。三個可以熬成蝦頭高湯；也能放進蝦籠當餌。', '在鱼案板上替虾、螯虾或龙虾去头得到。三个可以熬成虾头高汤；也能放进虾笼当饵。')),
        ('lobster_tomalley', G('Lobster Tomalley', '龍蝦膏', '龙虾膏'), None,
         G('Sometimes found in a lobster\'s head. Stands in for Crab Roe.', '有時在龍蝦頭裡找到。可以代替蟹黃。', '有时在龙虾头里找到。可以代替蟹黄。')),
        ('shrimp_shell', G('Shrimp Shells', '蝦殼', '虾壳'), None,
         G('Peeled off a shrimp on the Fish Cleaning Board. Boil into Fish Stock in place of Fish Bones.', '在魚案板上剝蝦剩下的殼。可以代替魚骨熬魚高湯。', '在鱼案板上剥虾剩下的壳。可以代替鱼骨熬鱼高汤。')),
        ('shrimp_meat', G('Peeled Shrimp', '蝦仁', '虾仁'), food(1, 0.2),
         G('A shrimp with its head, shell and vein taken off on the Fish Cleaning Board. Stands in for Shrimp in the pack\'s shrimp dishes.',
           '在魚案板上去頭、剝殼、挑掉腸泥的蝦。可以代替蝦做各種蝦料理。', '在鱼案板上去头、剥壳、挑掉肠泥的虾。可以代替虾做各种虾料理。')),
        ('crab_shell', G('Crab Shell', '蟹殼', '蟹壳'), None,
         G('Lifted off a crab with the first cut on the Fish Cleaning Board. Boil into Fish Stock in place of Fish Bones.', '在魚案板上開蟹掀下的殼。可以代替魚骨熬魚高湯。', '在鱼案板上开蟹掀下的壳。可以代替鱼骨熬鱼高汤。')),
        ('crab_roe', G('Crab Roe', '蟹黃', '蟹黄'), food(1, 0.3),
         G('Found under a crab\'s shell, in one crab of two (always in a Glow Crab or a King Crab).', '開蟹殼時找到，一半的螃蟹有（夜光蟹和帝王蟹一定有）。', '开蟹壳时找到，一半的螃蟹有（夜光蟹和帝王蟹一定有）。')),
        ('crab_meat', G('Crab Meat', '蟹肉', '蟹肉'), food(2, 0.3),
         G('Picked from a crab with the last cut on the Fish Cleaning Board. Stands in for a Crab in Seafood Hot Pot.', '在魚案板上拆蟹最後一刀取出的肉。可以代替螃蟹做海鮮火鍋。', '在鱼案板上拆蟹最后一刀取出的肉。可以代替螃蟹做海鲜火锅。')),
        ('crab_leg', G('Crab Leg', '蟹腳', '蟹脚'), None,
         G('Taken off a crab with the last cut on the Fish Cleaning Board; a King Crab gives four.', '在魚案板上拆蟹時拆下的腳；帝王蟹有四隻。', '在鱼案板上拆蟹时拆下的脚；帝王蟹有四只。')),
        ('jellyfish_skin', G('Jellyfish Strips', '海蜇皮', '海蜇皮'), food(1, 0.1),
         G('Sliced from a jellyfish\'s bell on the Fish Cleaning Board. Crunchy; eat it as it is or dress it as a salad.', '在魚案板上把水母的傘切成片。口感爽脆，可以直接吃或做成涼拌菜。', '在鱼案板上把水母的伞切成片。口感爽脆，可以直接吃或做成凉拌菜。')),
    ]
    after = 'fish_bones'
    for key, name, edible, text in products:
        c.item(key, stack=64, group='ingredients', components=edible)
        c.names(key, *name)
        c.icon(key)
        c.catalog(key, after)
        c.guide(key, 'ingredients', text, name, stack=64, food={'nutrition': edible['minecraft:food']['nutrition'],
                'saturation': edible['minecraft:food']['saturation_modifier']} if edible else None)
        after = key
    # ---- the cuts
    S, O = NS, NS + 'fish_offal'
    def shrimp(heads, shells, meat, tomalley=0):
        head = [[S + 'shrimp_head', heads]] + ([[S + 'lobster_tomalley', 1, tomalley]] if tomalley else [])
        return [{'act': 'head', 'out': head}, {'act': 'shell', 'out': [[S + 'shrimp_shell', shells]]},
                {'act': 'devein', 'out': [[S + 'shrimp_meat', meat, 1, 'sized']]}]
    def crab(shells, roe, meat, legs):
        return [{'act': 'open', 'out': [[S + 'crab_shell', shells], [S + 'crab_roe', 1, roe]]},
                {'act': 'gut', 'out': [[O, 1]]},
                {'act': 'legs', 'out': [[S + 'crab_meat', meat, 1, 'sized'], [S + 'crab_leg', legs]]}]
    jelly = [{'act': 'tentacle', 'out': [[O, 1]]}, {'act': 'fillet', 'out': [[S + 'jellyfish_skin', 2, 1, 'sized']]}]
    table = c.data('CLEANING')
    for key, idx, first, cuts in [
        ('shrimp', 44, 1, shrimp(1, 1, 1)), ('live_shrimp', 45, 1, shrimp(1, 1, 1)), ('purpur_shrimp', 46, 1, shrimp(1, 1, 1)),
        ('cave_crayfish', 47, 1, shrimp(1, 1, 2)), ('lobster', 48, 1, shrimp(2, 2, 3, 0.5)),
        ('crab', 49, 1, crab(1, 0.5, 1, 2)), ('basalt_crab', 50, 1, crab(1, 0.5, 1, 2)),
        ('glow_crab', 51, 1, crab(1, 1, 2, 2)), ('king_crab', 52, 1, crab(2, 1, 2, 4)),
        ('moon_jellyfish', 53, 2, jelly), ('chorus_jellyfish', 54, 2, jelly),
    ]:
        table[S + key] = {'index': idx, 'first': first, 'cuts': cuts}
    c.save('CLEANING', table)


def shellfish_dishes():
    """Step 4: dishes from what the board now gives, and the old dishes taking it too."""
    S = NS
    roe = {'tag': S + 'roe_paste', 'shown': S + 'crab_roe'}            # crab roe, or lobster tomalley in its place
    for key in ('crab_roe', 'lobster_tomalley'):
        path = c.os.path.join(c.BP, 'items', f'{key}.json')
        j = c.read_json(path)
        tags = j['minecraft:item']['components'].setdefault('minecraft:tags', {'tags': []})['tags']
        if S + 'roe_paste' not in tags:
            tags.append(S + 'roe_paste')
        c.write_json(path, j)
    after = 'crab_leg_hot_pot'
    for key, name, n, sat, how, bowl, fx in [
        ('stir_fried_shrimp', ('Stir-fried Shrimp', '清炒蝦仁', '清炒虾仁'), 8, 0.7,
         [('wok', ['shrimp_meat', 'shrimp_meat', 'kaleidoscope_cookery:green_chili', 'minecraft:carrot'], None)], True, None),
        ('crab_congee', ('Crab Congee', '蟹肉粥', '蟹肉粥'), 9, 0.8,
         [('stockpot', ['kaleidoscope_cookery:rice', 'crab_meat', 'minecraft:carrot'], {'base': S + 'fish_stock'})], True, [('regeneration', 100, 0)]),
        ('shrimp_noodle_soup', ('Shrimp Noodle Soup', '鮮蝦湯麵', '鲜虾汤面'), 9, 0.8,
         [('stockpot', ['kaleidoscope_cookery:raw_noodles', 'shrimp_meat', 'shrimp_shell'], None)], True, None),
        ('crab_roe_rice', ('Crab Roe Rice Bowl', '蟹黃蓋飯', '蟹黄盖饭'), 10, 0.8,
         [('crafting', ['kaleidoscope_cookery:cooked_rice', roe, roe, 'nori', 'minecraft:bowl'], None)], False, [('absorption', 600, 0)]),
        ('jellyfish_salad', ('Jellyfish Salad', '涼拌海蜇皮', '凉拌海蜇皮'), 6, 0.6,
         [('crafting', ['jellyfish_skin', 'jellyfish_skin', 'kaleidoscope_cookery:lettuce', 'kaleidoscope_cookery:red_chili', 'minecraft:bowl'], None)], False, [('water_breathing', 600, 0)]),
        ('boiled_shrimp', ('Boiled Shrimp', '白灼蝦', '白灼虾'), 7, 0.6,
         [('stockpot', ['live_shrimp', 'live_shrimp', 'live_shrimp', 'live_shrimp'], {'time': 200})], True, None),
        ('steamed_crab_leg', ('Steamed Crab Legs', '清蒸蟹腳', '清蒸蟹脚'), 4, 0.6, [('steamer', ['crab_leg'], None)], False, None),
        ('grilled_crab_leg', ('Grilled Crab Legs', '炭烤蟹腳', '炭烤蟹脚'), 4, 0.5, [('furnace', ['crab_leg'], None)], False, None),
    ]:
        # a crafted dish in a bowl gives the bowl back when eaten, like the stockpot and wok dishes
        c.dish(key, name, n, sat, how, bowl=bowl or any(m == 'crafting' and 'minecraft:bowl' in i for m, i, _ in how),
               effects=fx, after=after)
        after = key
    # ---- the old dishes take the board's products
    for rid, plain, alt in [('wok/shrimp_scrambled_eggs', 'shrimp', 'shrimp_meat'), ('stockpot/seafood_congee', 'shrimp', 'shrimp_meat'),
                            ('wok/seafood_chow_mein', 'shrimp', 'shrimp_meat'), ('wok/paella', 'shrimp', 'shrimp_meat'),
                            ('stockpot/seafood_hot_pot', 'shrimp', 'shrimp_meat'), ('stockpot/seafood_hot_pot', 'crab', 'crab_meat'),
                            ('stockpot/fish_stock', 'fish_bones', 'shrimp_shell'), ('stockpot/fish_stock', 'fish_bones', 'crab_shell')]:
        c.kc_alternative(rid, plain, alt)
    c.kc_recipe('stockpot_exact', {'id': S + 'stockpot/crab_leg_hot_pot_from_legs', 'ingredients': [S + 'crab_leg'] * 3 + ['kaleidoscope_cookery:lettuce', 'minecraft:carrot'],
                                   'result': S + 'crab_leg_hot_pot', 'count': 1, 'time': 400, 'base': S + 'dashi', 'carrier': 'minecraft:bowl', 'finishedKind': 'default'})
    c.recipe_file('crafting', 'raw_har_gow_from_shrimp_meat', {'format_version': '1.20.10', 'minecraft:recipe_shapeless': {
        'description': {'identifier': S + 'raw_har_gow_from_shrimp_meat'}, 'tags': ['crafting_table'],
        'ingredients': [{'item': 'kaleidoscope_cookery:raw_dough'}, {'item': S + 'shrimp_meat'}],
        'result': {'item': S + 'raw_har_gow', 'count': 2}, 'unlock': [{'item': S + 'shrimp_meat'}]}})
    c.recipe_file('crafting', 'raw_crab_roe_bun_from_roe', {'format_version': '1.20.10', 'minecraft:recipe_shapeless': {
        'description': {'identifier': S + 'raw_crab_roe_bun_from_roe'}, 'tags': ['crafting_table'],
        'ingredients': [{'item': 'kaleidoscope_cookery:raw_dough'}, {'tag': S + 'roe_paste'}],
        'result': {'item': S + 'raw_crab_roe_bun', 'count': 2}, 'unlock': [{'item': S + 'crab_roe'}]}})
    # validate.py reads an item tag in a recipe as an item id
    c._baseline(S + 'roe_paste', "crab_roe_rice.json', 'raw_crab_roe_bun_from_roe.json")
    # the guidebook shows the new ways
    g = c.data('GUIDEBOOK_JSON')
    extra = {S + 'raw_har_gow': {'method': 'Crafting Table', 'ingredients': ['kaleidoscope_cookery:raw_dough', S + 'shrimp_meat'], 'count': 2, 'time': 0, 'result': S + 'raw_har_gow'},
             S + 'raw_crab_roe_bun': {'method': 'Crafting Table', 'ingredients': ['kaleidoscope_cookery:raw_dough', S + 'crab_roe'], 'count': 2, 'time': 0, 'result': S + 'raw_crab_roe_bun'},
             S + 'crab_leg_hot_pot': {'method': 'Stockpot', 'ingredients': [S + 'dashi_bucket', S + 'crab_leg', S + 'crab_leg', S + 'crab_leg', 'kaleidoscope_cookery:lettuce', 'minecraft:carrot'], 'count': 1, 'time': 400, 'result': S + 'crab_leg_hot_pot'},
             S + 'fish_stock_bucket': None}
    for e in g['entries']:
        r = extra.get(e['id'])
        if r and r not in e.setdefault('recipes', []):
            e['recipes'].append(r)
    c.save('GUIDEBOOK_JSON', g)
    for item, user in [('shrimp_meat', 'raw_har_gow'), ('crab_roe', 'raw_crab_roe_bun'), ('crab_leg', 'crab_leg_hot_pot'),
                       ('shrimp_shell', 'fish_stock_bucket'), ('crab_shell', 'fish_stock_bucket'), ('shrimp_meat', 'shrimp_scrambled_eggs'),
                       ('shrimp_meat', 'seafood_congee'), ('shrimp_meat', 'seafood_chow_mein'), ('shrimp_meat', 'paella'),
                       ('shrimp_meat', 'seafood_hot_pot'), ('crab_meat', 'seafood_hot_pot'), ('lobster_tomalley', 'crab_roe_rice'),
                       ('lobster_tomalley', 'raw_crab_roe_bun')]:
        c.guide_used_by(item, user)


if __name__ == '__main__':
    legends()
    creel()
    journal()
    merchant_order()
    tide_clock()
    wall_tide_clock()
    cleaning_format()
    shellfish_board()
    shellfish_dishes()
    print('1.5.0 content written; now run: python tools/build.py build')
