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


def shrimp_head_stock():
    """Step 5: Shrimp Head Stock, a new stockpot base made the way Fish Stock is: three Shrimp Heads in water.
    Its bucket, the base and the two liquid layers in the pot are copies of Fish Stock's, tinted shrimp red."""
    import json, re
    from PIL import Image
    import colorsys
    import pbr
    def tint(path_in, path_out, liquid_only):
        im = Image.open(path_in).convert('RGBA'); px = im.load()
        for y in range(im.height):
            for x in range(im.width):
                r, g, b, a = px[x, y]
                if not a:
                    continue
                h, sat, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                if liquid_only and sat < 0.12:
                    continue                                  # the bucket's grey metal stays
                nr, ng, nb = colorsys.hsv_to_rgb(0.035, min(1, max(sat, 0.25) * 1.6 + 0.15), v * 0.97)
                px[x, y] = (round(nr * 255), round(ng * 255), round(nb * 255), a)
        im.save(path_out)
    def clone_json(src, dst, pairs):
        text = open(src, encoding='utf-8').read()
        for a_, b_ in pairs:
            text = text.replace(a_, b_)
        with open(dst, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    BPd, RPd = c.BP, c.RP
    swap = [('stockpot_fish_stock', 'stockpot_shrimp_stock'), ('fish_stock_bucket', 'shrimp_stock_bucket')]
    for layer in ('', '_cooking'):
        clone_json(os.path.join(BPd, 'entities', f'stockpot_fish_stock{layer}.json'), os.path.join(BPd, 'entities', f'stockpot_shrimp_stock{layer}.json'), swap)
        clone_json(os.path.join(RPd, 'entity', f'stockpot_fish_stock{layer}.entity.json'), os.path.join(RPd, 'entity', f'stockpot_shrimp_stock{layer}.entity.json'), swap)
        tex = os.path.join(RPd, 'textures', 'entity', f'kfv_stockpot_fish_stock{layer}')
        out = os.path.join(RPd, 'textures', 'entity', f'kfv_stockpot_shrimp_stock{layer}')
        tint(tex + '.png', out + '.png', False)
        clone_json(tex + '.texture_set.json', out + '.texture_set.json', swap)
        pbr.refresh(out + '.png')
    rc_path = os.path.join(RPd, 'render_controllers', 'kaleidoscope_fishing_stockpot.render_controllers.json')
    rc = c.read_json(rc_path)
    for layer in ('', '_cooking'):
        rc['render_controllers'][f'controller.render.kaleidoscope_fishing.stockpot_shrimp_stock{layer}'] = \
            rc['render_controllers'][f'controller.render.kaleidoscope_fishing.stockpot_fish_stock{layer}']
    c.write_json(rc_path, rc)
    icon = os.path.join(RPd, 'textures', 'items', 'kfv_shrimp_stock_bucket')
    tint(os.path.join(RPd, 'textures', 'items', 'kfv_fish_stock_bucket.png'), icon + '.png', True)
    clone_json(os.path.join(RPd, 'textures', 'items', 'kfv_fish_stock_bucket.texture_set.json'), icon + '.texture_set.json', swap)
    pbr.refresh(icon + '.png')
    name = ('Shrimp Head Stock Bucket', '蝦頭高湯桶', '虾头高汤桶')
    c.item('shrimp_stock_bucket', stack=1, group='ingredients')
    c.names('shrimp_stock_bucket', *name)
    c.icon('shrimp_stock_bucket')
    c.catalog('shrimp_stock_bucket', 'dashi_bucket')
    bases = [b for b in c.data('STOCKPOT_BASES') if b['base'] != NS + 'shrimp_stock']
    bases.append({'filled': NS + 'shrimp_stock_bucket', 'base': NS + 'shrimp_stock', 'empty': 'minecraft:bucket',
                  'visualBase': NS + 'stockpot_shrimp_stock', 'visualCooking': NS + 'stockpot_shrimp_stock_cooking',
                  'visualFinished': NS + 'stockpot_shrimp_stock_cooking'})
    c.save('STOCKPOT_BASES', bases)
    c._baseline(NS + 'shrimp_stock', 'generated.js')            # a stockpot base id, not an item (as fish_stock and dashi)
    c.kc_recipe('stockpot_exact', {'id': NS + 'stockpot/shrimp_stock', 'ingredients': [NS + 'shrimp_head'] * 3, 'result': NS + 'shrimp_stock_bucket',
                                   'count': 1, 'time': 300, 'base': 'minecraft:water', 'carrier': 'minecraft:bucket', 'finishedKind': 'default'})
    c.guide('shrimp_stock_bucket', 'ingredients', (
        'Three Shrimp Heads boiled in water in the stockpot. Pour it into a stockpot as a soup base; Shrimp Noodle Soup and Seafood Congee take it in place of Fish Stock.',
        '三個蝦頭在湯鍋裡加水熬成。倒進湯鍋當湯底；鮮蝦湯麵、海鮮粥可以用它代替魚高湯。',
        '三个虾头在汤锅里加水熬成。倒进汤锅当汤底；鲜虾汤面、海鲜粥可以用它代替鱼高汤。'), name, stack=1,
        recipes=[{'method': 'Stockpot', 'ingredients': [NS + 'shrimp_head'] * 3, 'count': 1, 'time': 300, 'result': NS + 'shrimp_stock_bucket'}])
    c.guide_used_by('shrimp_head', 'shrimp_stock_bucket')
    # dishes that take it in place of Fish Stock: the same recipe again on this base
    table = c.data('KC_RECIPES')
    for rid in ('stockpot/seafood_congee', 'stockpot/shrimp_noodle_soup'):
        src = next(r for r in table if r['recipe']['id'] == NS + rid)
        twin = json.loads(json.dumps(src))
        twin['recipe']['id'] = NS + rid + '_shrimp_stock'
        twin['recipe']['base'] = NS + 'shrimp_stock'
        table = [r for r in table if r['recipe']['id'] != twin['recipe']['id']] + [twin]
    c.save('KC_RECIPES', table)


def dried_shrimp():
    """Step 5: Dried Shrimp the real way, the old shortcut gone (plan 5.2, 5.3).
    salt + 3 shrimp in water -> 3 Salted Shrimp; on the bamboo tray -> Dried Shell-on Shrimp; on the Fish Cleaning
    Board one rub -> 2 Dried Shrimp and Shrimp Shells. The tray no longer dries raw shrimp; the jar's shrimp paste
    takes fresh shrimp (blocks/fishSauceJar.js)."""
    fresh = [NS + 'shrimp', NS + 'live_shrimp']
    c.dish('salted_shrimp', ('Salted Shrimp', '鹽水蝦', '盐水虾'), 3, 0.4,
           [('stockpot', ['sea_salt', fresh, fresh, fresh], {'count': 3, 'time': 200})], bowl=False, after='boiled_shrimp',
           text=('Shrimp boiled in salted water: a small dish as it is, and the first step to Dried Shrimp. Dry it on a bamboo tray.',
                 '用鹽水煮熟的蝦：本身是一道小菜，也是做蝦米的第一步。放上竹匾曬乾。',
                 '用盐水煮熟的虾：本身是一道小菜，也是做虾米的第一步。放上竹匾晒干。'))
    name = ('Dried Shell-on Shrimp', '帶殼蝦乾', '带壳虾干')
    c.item('dried_shell_shrimp', stack=64, group='ingredients')
    c.names('dried_shell_shrimp', *name)
    c.icon('dried_shell_shrimp')
    c.catalog('dried_shell_shrimp', 'dried_shrimp')
    table = [r for r in c.data('KC_RECIPES') if r['recipe']['id'] != NS + 'tray/dried_shrimp']
    c.save('KC_RECIPES', table)
    c.kc_recipe('bamboo_tray', {'id': NS + 'tray/dried_shell_shrimp', 'input': NS + 'salted_shrimp', 'result': NS + 'dried_shell_shrimp',
                                'process': 'dry', 'duration': 1200})
    c.guide('dried_shell_shrimp', 'ingredients', (
        'Salted Shrimp dried on a bamboo tray. Rub it once on the Fish Cleaning Board with a knife: the shells come off and leave 2 Dried Shrimp.',
        '鹽水蝦放竹匾曬乾而成。放上魚案板用刀搓一下，殼掉下來，留下 2 份蝦米。', '盐水虾放竹匾晒干而成。放上鱼案板用刀搓一下，壳掉下来，留下 2 份虾米。'),
        name, stack=64, recipes=[{'method': 'Bamboo Tray', 'ingredients': [NS + 'salted_shrimp'], 'count': 1, 'time': 1200, 'result': NS + 'dried_shell_shrimp'}])
    c.guide_used_by('salted_shrimp', 'dried_shell_shrimp')
    # the board: one rub
    board = c.data('CLEANING')
    board[NS + 'dried_shell_shrimp'] = {'index': 55, 'first': 3, 'cuts': [
        {'act': 'rub', 'out': [[NS + 'dried_shrimp', 2], [NS + 'shrimp_shell', 1]]}]}
    c.save('CLEANING', board)
    # the guidebook's Dried Shrimp page: the new way only
    g = c.data('GUIDEBOOK_JSON')
    for e in g['entries']:
        if e['id'] == NS + 'dried_shrimp':
            e.pop('recipes', None)                       # board and tray steps are told in words, as the drying rack's are
            e['mechanicsByLocale'] = {
                'en_US': ['Made in three steps: boil Shrimp with Salt into Salted Shrimp (stockpot), dry it on a bamboo tray, then rub the Dried Shell-on Shrimp on the Fish Cleaning Board.'],
                'zh_TW': ['分三步做：蝦加鹽在湯鍋煮成鹽水蝦，放竹匾曬成帶殼蝦乾，再放上魚案板搓掉殼。'],
                'zh_CN': ['分三步做：虾加盐在汤锅煮成盐水虾，放竹匾晒成带壳虾干，再放上鱼案板搓掉壳。']}
            e['mechanics'] = list(e['mechanicsByLocale']['en_US'])
        if e['id'] == NS + 'shrimp':
            e['usedBy'] = [u for u in e.get('usedBy', []) if u != NS + 'dried_shrimp']
    c.save('GUIDEBOOK_JSON', g)
    # the jar's own words: shrimp paste is made from fresh shrimp now
    for pack in (c.BP, c.RP):
        for code, old, new in [('en_US', '; or 4 Dried Shrimp§r', '; or 4 fresh Shrimp (shrimp paste)§r'),
                               ('zh_TW', '；或 4 份蝦米§r', '；或 4 隻新鮮的蝦（做蝦醬）§r'), ('zh_CN', '；或 4 份虾米§r', '；或 4 只新鲜的虾（做虾酱）§r')]:
            path = os.path.join(pack, 'texts', f'{code}.lang')
            text = open(path, encoding='utf-8').read()
            if old in text:
                with open(path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(text.replace(old, new))
    g = c.data('GUIDEBOOK_JSON')
    words = {
        NS + 'fish_sauce_jar': {
            'en_US': 'Rub in Salt first, then add 4 small fish (fish sauce) or 4 fresh Shrimp or Live Shrimp (shrimp paste; Dried Shrimp no longer goes in). Small fish: Yellow Croaker, Pond Smelt, Sweetfish, Pacific Saury, Mackerel, Loach, Raw Cod; they can be mixed. It seals itself and ferments for about 3 minutes; when the lid is off, draw fish sauce with glass bottles or scoop shrimp paste with bowls: 4 each.',
            'zh_TW': '先放鹽，再放 4 條小魚（做魚露）或 4 隻新鮮的蝦或活蝦（做蝦醬；蝦米不能再用）。可以用的小魚：小黃魚、公魚、香魚、秋刀魚、鯖魚、泥鰍、生鱈魚，可以混著放。甕會自己封起來發酵約 3 分鐘；蓋子打開後用玻璃瓶取魚露、用碗舀蝦醬，各 4 份。',
            'zh_CN': '先放盐，再放 4 条小鱼（做鱼露）或 4 只新鲜的虾或活虾（做虾酱；虾米不能再用）。可以用的小鱼：小黄鱼、公鱼、香鱼、秋刀鱼、鲭鱼、泥鳅、生鳕鱼，可以混着放。瓮会自己封起来发酵约 3 分钟；盖子打开后用玻璃瓶取鱼露、用碗舀虾酱，各 4 份。'},
        NS + 'shrimp_paste': {
            'en_US': 'Scooped with a bowl from a Fish Sauce Jar of fresh shrimp pounded with salt.',
            'zh_TW': '用碗從醃了新鮮蝦的魚露甕舀出。', 'zh_CN': '用碗从腌了新鲜虾的鱼露瓮舀出。'},
    }
    for e in g['entries']:
        if e['id'] in words:
            e['mechanicsByLocale'] = {k: [v] for k, v in words[e['id']].items()}
            e['mechanics'] = [words[e['id']]['en_US']]
        if e['id'] == NS + 'dried_shrimp':
            e['usedBy'] = [u for u in e.get('usedBy', []) if u != NS + 'shrimp_paste']
    c.save('GUIDEBOOK_JSON', g)
    # XO sauce and a greens dish
    name = ('XO Sauce', 'XO 醬', 'XO 酱')
    c.item('xo_sauce', stack=16, group='ingredients')
    c.names('xo_sauce', *name)
    c.icon('xo_sauce')
    c.catalog('xo_sauce', 'shrimp_paste')
    ing = ['dried_shrimp', 'karasumi_slices', 'kaleidoscope_cookery:red_chili', 'kaleidoscope_cookery:oil']
    recipe = c.shapeless('xo_sauce', ing)
    c.guide('xo_sauce', 'ingredients', (
        'A jar of chili sauce rich with Dried Shrimp and karasumi. Goes into a wok dish in place of salt or fish sauce, as in Salt and Pepper Shrimp.',
        '滿是蝦米和烏魚子的辣醬。可以代替鹽或魚露放進炒鍋料理，例如椒鹽蝦。', '满是虾米和乌鱼子的辣酱。可以代替盐或鱼露放进炒锅料理，例如椒盐虾。'),
        name, stack=16, recipes=[recipe])
    for i in ('dried_shrimp', 'karasumi_slices'):
        c.guide_used_by(i, 'xo_sauce')
    c.kc_alternative('wok/salt_pepper_shrimp', 'sea_salt', 'xo_sauce')
    c.kc_alternative('wok/salt_pepper_shrimp', 'shrimp', 'shrimp_meat')
    c.dish('dried_shrimp_greens', ('Greens with Dried Shrimp', '蝦米炒青菜', '虾米炒青菜'), 6, 0.6,
           [('wok', ['dried_shrimp', 'kaleidoscope_cookery:lettuce', 'kaleidoscope_cookery:lettuce', 'kaleidoscope_cookery:oil'], None)],
           bowl=True, after='salted_shrimp')


def squid_and_tuna():
    """Step 6: the whole squid on the board, and tuna cut by part (plan 5.6, 5.7)."""
    import json
    S = NS
    # ---- renames (ids stay)
    for key, en, tw, cn in [('squid_tube', 'Squid Tube', '魷魚筒', '鱿鱼筒'), ('tuna_sashimi', 'Akami Sashimi', '赤身刺身', '赤身刺身')]:
        c.names(key, en, tw, cn)
        c.guide_name(S + key, en, tw, cn)
    # ---- new ingredients
    for key, name, edible, text, after in [
        ('whole_squid', ('Whole Squid', '整隻魷魚', '整只鱿鱼'), None,
         ('What a squid killed with a knife leaves. On the Fish Cleaning Board: gut it, draw the cartilage, then cut it into a Squid Tube and Squid Tentacles.',
          '用刀殺魷魚得到。在魚案板上去內臟、抽軟骨，再分成魷魚筒和魷魚鬚。', '用刀杀鱿鱼得到。在鱼案板上去内脏、抽软骨，再分成鱿鱼筒和鱿鱼须。'), 'squid_tube'),
        ('squid_tentacles', ('Squid Tentacles', '魷魚鬚', '鱿鱼须'), food(1, 0.2),
         ('Cut from a Whole Squid on the Fish Cleaning Board. Fry them in the wok or grill them.', '在魚案板上從整隻魷魚切下。可以炒鍋炸或拿去烤。', '在鱼案板上从整只鱿鱼切下。可以炒锅炸或拿去烤。'), 'whole_squid'),
        ('chutoro', ('Chutoro Sashimi', '中腹刺身', '中腹刺身'), food(3, 0.7),
         ('The medium-fat belly of a tuna, from the Fish Cleaning Board. Any sushi that takes tuna takes it.', '鮪魚中段的腹肉，在魚案板上切得。用鮪魚的壽司都能用。', '鲔鱼中段的腹肉，在鱼案板上切得。用鲔鱼的寿司都能用。'), 'tuna_sashimi'),
        ('otoro', ('Otoro Sashimi', '大腹刺身', '大腹刺身'), food(4, 0.8),
         ('The fattiest belly of a tuna, from the Fish Cleaning Board. Makes Otoro Nigiri.', '鮪魚最肥的腹肉，在魚案板上切得。可以做大腹握壽司。', '鲔鱼最肥的腹肉，在鱼案板上切得。可以做大腹握寿司。'), 'chutoro'),
        ('bonito_sashimi', ('Bonito Sashimi', '鰹魚生魚片', '鲣鱼生鱼片'), food(3, 0.6),
         ('Skipjack is no tuna: on the Fish Cleaning Board it gives its own darker slices. Sushi takes them as it takes tuna.', '鰹魚不是鮪魚：在魚案板上切出顏色較深的生魚片。壽司可以用它代替鮪魚。', '鲣鱼不是鲔鱼：在鱼案板上切出颜色较深的生鱼片。寿司可以用它代替鲔鱼。'), 'otoro'),
    ]:
        c.item(key, stack=64, group='ingredients', components=edible)
        c.names(key, *name)
        c.icon(key)
        c.catalog(key, after)
        c.guide(key, 'ingredients', text, name, stack=64, food={'nutrition': edible['minecraft:food']['nutrition'],
                'saturation': edible['minecraft:food']['saturation_modifier']} if edible else None)
    # ---- the board
    board = c.data('CLEANING')
    board[S + 'whole_squid'] = {'index': 56, 'first': 1, 'cuts': [
        {'act': 'gut', 'out': [[S + 'fish_offal', 1], ['minecraft:ink_sac', 1, 0.5]]},
        {'act': 'bone', 'out': []},
        {'act': 'fillet', 'out': [[S + 'squid_tube', 1], [S + 'squid_tentacles', 1]]}]}
    def parts(akami, chu, oto):
        return [[S + 'tuna_sashimi', akami], [S + 'chutoro', chu], [S + 'otoro', oto, 1, 'sized']]
    for key, out in [('tuna', parts(4, 1, 1)), ('emperor_tuna', parts(4, 2, 2)), ('skipjack', [[S + 'bonito_sashimi', 3, 1, 'sized']])]:
        last = board[S + key]['cuts'][-1]
        bones = [r for r in last['out'] if r[0] == S + 'fish_bones']
        last['out'] = out + bones
    c.save('CLEANING', board)
    # ---- sushi takes every cut: a tag on the four, and the recipes ask for the tag
    TAG = S + 'tuna_cut'
    for key in ('tuna_sashimi', 'chutoro', 'otoro', 'bonito_sashimi'):
        path = os.path.join(c.BP, 'items', f'{key}.json')
        j = c.read_json(path)
        tags = j['minecraft:item']['components'].setdefault('minecraft:tags', {'tags': []})['tags']
        if TAG not in tags:
            tags.append(TAG)
        c.write_json(path, j)
    users = []
    for name in ('nigiri_tuna', 'maki_roll', 'temaki_stand', 'sashimi_boat', 'seafood_platter'):
        path = os.path.join(c.BP, 'recipes', 'crafting', f'{name}.json')
        j = c.read_json(path)
        r = j['minecraft:recipe_shapeless']
        r['ingredients'] = [{'tag': TAG} if i.get('item') == S + 'tuna_sashimi' else i for i in r['ingredients']]
        c.write_json(path, j)
        users.append(f'{name}.json')
    # validate.py reads a tag in a recipe as an item id (it lists the first three files it finds it in)
    c._baseline(TAG, "maki_roll.json', 'nigiri_tuna.json', 'sashimi_boat.json")
    for k in ('chutoro', 'otoro', 'bonito_sashimi'):
        for u in ('nigiri_sushi', 'maki_roll', 'temaki_stand', 'sashimi_boat', 'seafood_platter'):
            c.guide_used_by(k, u)
    # ---- dishes
    c.dish('otoro_nigiri', ('Otoro Nigiri', '大腹握壽司', '大腹握寿司'), 6, 1.0,
           [('crafting', ['kaleidoscope_cookery:cooked_rice', 'otoro'], {'count': 2})], effects=[('regeneration', 100, 0)], after='nigiri_sushi',
           text=('Rice under the fattiest tuna: more filling than any other nigiri, and it heals a little.',
                 '白飯上放最肥的大腹：比其他握壽司更有飽足感，還會回復一點生命。', '白饭上放最肥的大腹：比其他握寿司更有饱足感，还会回复一点生命。'))
    c.dish('fried_squid_tentacles', ('Fried Squid Tentacles', '炸魷魚鬚', '炸鱿鱼须'), 6, 0.6,
           [('wok', ['squid_tentacles', 'squid_tentacles', 'kaleidoscope_cookery:flour', 'kaleidoscope_cookery:oil'], None)],
           bowl=True, after='fried_calamari')
    c.dish('grilled_squid_tentacles', ('Grilled Squid Tentacles', '烤魷魚鬚', '烤鱿鱼须'), 4, 0.5,
           [('furnace', ['squid_tentacles'], None)], after='fried_squid_tentacles')


def dried_fish():
    """Step 7: small fish dry whole on the tray (Dried Small Fish); bigger fish are gutted first and hung (plan 5.8)."""
    S = NS
    c.names('dried_fish', 'Dried Small Fish', '小魚乾', '小鱼干')
    c.guide_name(S + 'dried_fish', 'Dried Small Fish', '小魚乾', '小鱼干')
    # ---- the tray: whole small fish only (smelt in, mackerel out: a mackerel is split and hung)
    table = [r for r in c.data('KC_RECIPES') if r['recipe']['id'] != S + 'tray/dried_fish_mackerel']
    c.save('KC_RECIPES', table)
    c.kc_recipe('bamboo_tray', {'id': S + 'tray/dried_fish_smelt', 'input': S + 'smelt', 'result': S + 'dried_fish', 'process': 'dry', 'duration': 1800})
    # ---- gutted fish: taken off the board after the gut, the only thing the rack hangs besides squid and roe
    after = 'air_dried_fish'
    for key, name, text in [
        ('gutted_fish', ('Gutted Fish', '剖好的魚', '剖好的鱼'),
         ('A fish scaled and gutted on the Fish Cleaning Board, taken back with an empty hand instead of being filleted. Hang it on a Drying Rack (rub Salt on it there for Salted Fish).',
          '在魚案板上去鱗、剖腹之後，不切片而空手取回的魚。掛上曬魚架曬乾（在架上抹鹽就是鹹魚）。',
          '在鱼案板上去鳞、剖腹之后，不切片而空手取回的鱼。挂上晒鱼架晒干（在架上抹盐就是咸鱼）。')),
        ('gutted_skipjack', ('Gutted Skipjack', '剖好的鰹魚', '剖好的鲣鱼'),
         ('A skipjack gutted on the Fish Cleaning Board and taken back. Three days on a Drying Rack make it Katsuobushi.',
          '在魚案板上剖好、空手取回的鰹魚。在曬魚架上曬三天就是柴魚。', '在鱼案板上剖好、空手取回的鲣鱼。在晒鱼架上晒三天就是柴鱼。')),
        ('gutted_flying_fish', ('Gutted Flying Fish', '剖好的飛魚', '剖好的飞鱼')
         , ('A flying fish gutted on the Fish Cleaning Board and taken back. A night on a Drying Rack makes it Dried Flying Fish.',
            '在魚案板上剖好、空手取回的飛魚。在曬魚架上曬一夜就是飛魚一夜干。', '在鱼案板上剖好、空手取回的飞鱼。在晒鱼架上晒一夜就是飞鱼一夜干。')),
    ]:
        c.item(key, stack=64, group='ingredients')
        c.names(key, *name)
        c.icon(key)
        c.catalog(key, after)
        c.guide(key, 'ingredients', text, name, stack=64)
        after = key
    rack_fish = ['carp', 'grass_carp', 'catfish', 'sweetfish', 'mackerel', 'yellow_croaker', 'sea_bream', 'hairtail', 'grouper', 'saury', 'cod', 'salmon']
    board = c.data('CLEANING')
    for fish in rack_fish:
        board[f'minecraft:{fish}' if fish in ('cod', 'salmon') else S + fish]['gutted'] = S + 'gutted_fish'   # cod and salmon are the game's own
    board[S + 'skipjack']['gutted'] = S + 'gutted_skipjack'
    board[S + 'flying_fish']['gutted'] = S + 'gutted_flying_fish'
    c.save('CLEANING', board)
    dry = c.data('DRYING')
    for fish in rack_fish + ['skipjack', 'flying_fish']:
        for k in (S + fish, f'minecraft:{fish}'):
            dry['inputs'].pop(k, None)
    dry['inputs'].update({S + 'gutted_fish': 1, S + 'gutted_skipjack': 4, S + 'gutted_flying_fish': 6})
    c.save('DRYING', dry)
    # ---- words
    g = c.data('GUIDEBOOK_JSON')
    words = {
        S + 'drying_rack': (
            'Hang up to 3 of one kind: Gutted Fish, Gutted Skipjack, Gutted Flying Fish (gut a fish on the Fish Cleaning Board and take it back with an empty hand), Squid Tubes or Salted Mullet Roe. Fish and squid dry in 2 days, skipjack and roe in 3, flying fish overnight; you can see them darken. Rub Salt on fresh Gutted Fish for Salted Fish. Rain on an open rack stops the drying, and gulls may take a fish when nobody is near. Use it with an empty hand to take one back, or everything once dry.',
            '一架掛一種，最多 3 條：剖好的魚、剖好的鰹魚、剖好的飛魚（在魚案板剖腹後空手取回）、魷魚筒或鹽漬烏魚卵。魚和魷魚 2 天曬好，鰹魚和烏魚卵 3 天，飛魚一夜，看得到顏色慢慢變深。剛掛上的剖好的魚拿鹽抹一下就會曬成鹹魚。下雨時沒遮蔽的曬架會停下來，沒人在旁邊時海鷗可能來叼走一條。空手使用可取回一條；曬好後一次全部收下。',
            '一架挂一种，最多 3 条：剖好的鱼、剖好的鲣鱼、剖好的飞鱼（在鱼案板剖腹后空手取回）、鱿鱼筒或盐渍乌鱼卵。鱼和鱿鱼 2 天晒好，鲣鱼和乌鱼卵 3 天，飞鱼一夜，看得到颜色慢慢变深。刚挂上的剖好的鱼拿盐抹一下就会晒成咸鱼。下雨时没遮蔽的晒架会停下来，没人在旁边时海鸥可能来叼走一条。空手使用可取回一条；晒好后一次全部收下。'),
        S + 'air_dried_fish': ('A Gutted Fish dried for 2 days on a Drying Rack. Keeps well and is good to eat as it is.', '剖好的魚在曬魚架上曬 2 天。耐放，直接吃也不錯。', '剖好的鱼在晒鱼架上晒 2 天。耐放，直接吃也不错。'),
        S + 'salted_fish': ('A Gutted Fish rubbed with Salt and dried for 2 days on a Drying Rack. Salty and filling.', '抹了鹽的剖好的魚在曬魚架上曬 2 天。鹹香耐飽。', '抹了盐的剖好的鱼在晒鱼架上晒 2 天。咸香耐饱。'),
        S + 'katsuobushi': ("A Gutted Skipjack dried for 3 days on a Drying Rack, hard as wood. Shave it on Cookery's Chopping Board for Bonito Flakes.", '剖好的鰹魚在曬魚架上曬 3 天，硬得像木頭。放到本體的砧板上削成柴魚片。', '剖好的鲣鱼在晒鱼架上晒 3 天，硬得像木头。放到本体的砧板上削成柴鱼片。'),
        S + 'dried_flying_fish': ('A Gutted Flying Fish dried overnight on a Drying Rack. Grill it.', '剖好的飛魚在曬魚架上曬一夜。拿去烤。', '剖好的飞鱼在晒鱼架上晒一夜。拿去烤。'),
        S + 'dried_fish': ('Small fish dried whole on a bamboo tray: Pond Smelt, Sweetfish or Yellow Croaker. Grind it into Fish Meal, use it as Shrimp Trap bait, or stir-fry it with chili.',
                           '小魚整條放竹匾曬乾：公魚、香魚或小黃魚。可以磨成魚粉、當蝦籠的餌，或和辣椒一起炒。', '小鱼整条放竹匾晒干：公鱼、香鱼或小黄鱼。可以磨成鱼粉、当虾笼的饵，或和辣椒一起炒。'),
    }
    for e in g['entries']:
        if e['id'] in words:
            en, tw, cn = words[e['id']]
            e['mechanicsByLocale'] = {'en_US': [en], 'zh_TW': [tw], 'zh_CN': [cn]}
            e['mechanics'] = [en]
        if e['id'] == S + 'fish_cleaning_board':
            for code, extra in {'en_US': 'After the gut, an empty hand takes the fish back whole: a Gutted Fish for the Drying Rack.',
                                'zh_TW': '剖腹之後空手取回，就是可以掛上曬魚架的「剖好的魚」。', 'zh_CN': '剖腹之后空手取回，就是可以挂上晒鱼架的「剖好的鱼」。'}.items():
                if extra not in e['mechanicsByLocale'][code]:
                    e['mechanicsByLocale'][code].append(extra)
            e['mechanics'] = list(e['mechanicsByLocale']['en_US'])
    c.save('GUIDEBOOK_JSON', g)
    c.dish('spicy_dried_fish', ('Spicy Dried Small Fish', '辣炒小魚乾', '辣炒小鱼干'), 5, 0.6,
           [('wok', ['dried_fish', 'dried_fish', 'kaleidoscope_cookery:red_chili', 'kaleidoscope_cookery:oil'], None)], bowl=True, after='dried_shrimp_greens')


def station_block(key, name, text, states, visibility, box_, recipe, after, group='cooking_stations'):
    """A block that is its own inventory item (it shows its 3D model there), with a model from
    tools/gen_stations_1_5.py whose bones show by state, and a script component of the same name."""
    S = NS
    c.write_json(os.path.join(c.BP, 'blocks', f'{key}.json'), {'format_version': '1.21.60', 'minecraft:block': {
        'description': {'identifier': S + key, 'states': states,
                        'menu_category': {'category': 'equipment', 'group': f'kaleidoscope_cookery:itemGroup.name.{group}'}},
        'components': {
            'minecraft:display_name': f'%{S}display.item.{key}'.replace(':display', '.display'),
            'minecraft:material_instances': {'*': {'texture': f'kfv_{key}', 'render_method': 'alpha_test'}},
            'minecraft:geometry': {'identifier': f'geometry.{S.replace(":", ".")}{key}'.replace('..', '.'), 'bone_visibility': visibility},
            'minecraft:light_dampening': 0, 'minecraft:movable': {'movement_type': 'popped'},
            'minecraft:collision_box': box_, 'minecraft:selection_box': box_,
            'minecraft:tick': {'interval_range': [100, 100], 'looping': True},
            'minecraft:destructible_by_mining': {'seconds_to_destroy': 0.6},
            'minecraft:loot': f'loot_tables/{c.NS}/blocks/{key}.json', S + key: {}}}})
    c.write_json(os.path.join(c.BP, 'loot_tables', c.NS, 'blocks', f'{key}.json'), {'pools': [{'rolls': 1, 'entries': [{'type': 'item', 'name': S + key}]}]})
    c.names(key, *name)
    c.catalog(key, after)
    rid, pattern, keys = recipe
    c.write_json(os.path.join(c.BP, 'recipes', 'crafting', f'{key}.json'), {'format_version': '1.20.10', 'minecraft:recipe_shaped': {
        'description': {'identifier': S + key}, 'tags': ['crafting_table'], 'pattern': pattern,
        'key': {k: ({'tag': v[4:]} if v.startswith('tag:') else {'item': v}) for k, v in keys.items()},
        'result': {'item': S + key, 'count': 1}, 'unlock': [{'item': v} for v in keys.values() if not v.startswith('tag:')][:1]}})
    shown = [keys[ch] for row in pattern for ch in row if ch != ' ']
    shown = ['minecraft:oak_planks' if i.startswith('tag:') else i for i in shown]
    g = c.data('GUIDEBOOK_JSON')
    entry = {'id': S + key, 'category': 'tools', 'kinds': ['item', 'block'], 'stack': 64, 'icon': f'textures/ui/kfv_book/kfv_{key}',
             'recipes': [{'method': 'Crafting Table', 'ingredients': shown, 'count': 1, 'time': 0, 'result': S + key}],
             'mechanicsByLocale': {'en_US': [text[0]], 'zh_TW': [text[1]], 'zh_CN': [text[2]]}, 'mechanics': [text[0]]}
    g['entries'] = [e for e in g['entries'] if e['id'] != S + key] + [entry]
    for code, t in zip(c.LANGS, name):
        g['names'][code][S + key] = t
    c.save('GUIDEBOOK_JSON', g)


def tub_and_salt_pan():
    """Step 8: the Wooden Tub (purging clams) and the Salt Pan (sea salt from the sun), plan 5.11, 5.12."""
    S = NS
    fill = S + 'fill'
    on = lambda *vals: ' || '.join(f"q.block_state('{fill}') == {v}" for v in vals)
    station_block('wooden_tub', ('Wooden Tub', '木盆', '木盆'), (
        'Fill it with a water bucket. Add Salt to make brine and soak up to 8 Clams in it: half a day later an empty hand takes out Purged Clams, and the brine stays for the next batch. An empty bucket drains it.',
        '用水桶裝水。加一份鹽變成鹽水，放進最多 8 個蛤蜊泡著：半天後空手取出吐沙蛤蜊，鹽水留著給下一批。用空桶可以把水舀掉。',
        '用水桶装水。加一份盐变成盐水，放进最多 8 个蛤蜊泡着：半天后空手取出吐沙蛤蜊，盐水留着给下一批。用空桶可以把水舀掉。'),
        {fill: list(range(7))},
        {'water': on(1, 5, 6), 'brine': on(2, 3, 4), 'clams': on(3, 4), 'roe': on(5), 'fry': on(6)},
        {'origin': [-7, 0, -7], 'size': [14, 6, 14]},
        ('wooden_tub', ['P P', 'PIP'], {'P': 'tag:minecraft:planks', 'I': 'minecraft:iron_ingot'}), 'fish_sauce_jar')
    stage = S + 'stage'
    st = lambda *vals: ' || '.join(f"q.block_state('{stage}') == {v}" for v in vals)
    station_block('salt_pan', ('Salt Pan', '曬鹽盤', '晒盐盘'), (
        'Set it by the sea (an ocean or beach) under open sky and pour in a water bucket. It dries only in daylight and without rain, a whole day of daylight in all; rain pauses it without undoing it. When the pan is white, an empty hand gathers 4 Salt.',
        '放在海邊（海洋或海灘）頭上沒有遮蔽的地方，倒入一桶水。只有白天、沒下雨時會曬，累計一整天的日照；下雨會暫停但不會歸零。整盤變白後空手收成鹽 ×4。',
        '放在海边（海洋或海滩）头上没有遮蔽的地方，倒入一桶水。只有白天、没下雨时会晒，累计一整天的日照；下雨会暂停但不会归零。整盘变白后空手收成盐 ×4。'),
        {stage: [0, 1, 2, 3]}, {'water': st(1), 'half': st(2), 'salt': st(3)},
        {'origin': [-8, 0, -8], 'size': [16, 3, 16]},
        ('salt_pan', ['TTT', 'P P'], {'T': 'minecraft:terracotta', 'P': 'tag:minecraft:planks'}), 'wooden_tub')
    c.guide_name('minecraft:terracotta', 'Terracotta', '陶瓦', '陶瓦')
    c.guide_name('minecraft:oak_planks', 'Oak Planks', '橡木材', '橡木木板')
    c.guide_name('minecraft:iron_ingot', 'Iron Ingot', '鐵錠', '铁锭')
    # planks tags in recipes read as item ids by validate.py
    c._baseline('minecraft:planks', "salt_pan.json', 'wooden_tub.json")
    # ---- purged clams, and what they are for
    name = ('Purged Clam', '吐沙蛤蜊', '吐沙蛤蜊')
    c.item('purged_clam', stack=64, group='ingredients')
    c.names('purged_clam', *name)
    c.icon('purged_clam')
    c.catalog('purged_clam', 'clam')
    c.guide('purged_clam', 'ingredients', (
        'A clam soaked half a day in brine in a Wooden Tub: no grit left. Every clam dish takes it, and Steamed Egg with Clams takes nothing else.',
        '在木盆的鹽水裡泡了半天的蛤蜊，沙都吐乾淨了。所有蛤蜊料理都能用，蛤蜊蒸蛋只收它。', '在木盆的盐水里泡了半天的蛤蜊，沙都吐干净了。所有蛤蜊料理都能用，蛤蜊蒸蛋只收它。'), name, stack=64)
    for rid in ('wok/spicy_clams', 'wok/paella', 'stockpot/seafood_hot_pot'):
        c.kc_alternative(rid, 'clam', 'purged_clam')
        c.guide_used_by('purged_clam', rid.split('/')[1])
    c.dish('clam_steamed_egg', ('Steamed Egg with Clams', '蛤蜊蒸蛋', '蛤蜊蒸蛋'), 8, 0.8,
           [('stockpot', ['purged_clam', 'purged_clam', 'minecraft:egg', 'minecraft:egg'], {'time': 200})], bowl=True,
           effects=[('regeneration', 100, 0)], after='spicy_clams',
           text=('Silky egg steamed with Purged Clams; only clams without grit will do.', '用吐沙蛤蜊蒸的滑嫩蒸蛋；一定要吐過沙的蛤蜊。', '用吐沙蛤蜊蒸的滑嫩蒸蛋；一定要吐过沙的蛤蜊。'))


def lava_tank():
    """Step 9: the Lava Fish Tank (plan 6). The block is the Fish Tank's, with its own model (tools/gen_stations_1_5.py),
    light, and the tank component told it holds lava; the four new lava creatures' tank models come from
    tools/gen_tank_1_5.py, which also adds the oyster to the ordinary tanks."""
    S = NS
    src = c.read_json(os.path.join(c.BP, 'blocks', 'fish_tank.json'))
    blk = src['minecraft:block']
    blk['description']['identifier'] = S + 'lava_fish_tank'
    comp = blk['components']
    comp['minecraft:display_name'] = f'%{c.NS}.display.item.lava_fish_tank'
    comp['minecraft:material_instances'] = {'*': {'texture': 'kfv_lava_fish_tank', 'render_method': 'blend'}}
    comp['minecraft:geometry'] = f'geometry.{c.NS}.lava_fish_tank'
    comp['minecraft:light_emission'] = 10
    comp['minecraft:map_color'] = '#C43A12'
    comp['minecraft:loot'] = f'loot_tables/{c.NS}/blocks/lava_fish_tank.json'
    comp.pop('minecraft:liquid_detection', None)
    comp[S + 'fish_tank'] = {'lava': True}
    c.write_json(os.path.join(c.BP, 'blocks', 'lava_fish_tank.json'), src)
    c.write_json(os.path.join(c.BP, 'loot_tables', c.NS, 'blocks', 'lava_fish_tank.json'), {'pools': [{'rolls': 1, 'entries': [{'type': 'item', 'name': S + 'lava_fish_tank'}]}]})
    name = ('Lava Fish Tank', '熔岩魚缸', '熔岩鱼缸')
    c.names('lava_fish_tank', *name)
    c.catalog('lava_fish_tank', 'large_fish_tank')
    keys = {'B': 'minecraft:basalt', 'G': 'minecraft:glass', 'O': 'minecraft:obsidian', 'L': 'minecraft:lava_bucket'}
    pattern = ['BGB', 'OLO', 'BGB']
    c.write_json(os.path.join(c.BP, 'recipes', 'crafting', 'lava_fish_tank.json'), {'format_version': '1.20.10', 'minecraft:recipe_shaped': {
        'description': {'identifier': S + 'lava_fish_tank'}, 'tags': ['crafting_table'], 'pattern': pattern,
        'key': {k: {'item': v} for k, v in keys.items()}, 'result': {'item': S + 'lava_fish_tank', 'count': 1},
        'unlock': [{'item': 'minecraft:lava_bucket'}]}})
    for item, names in [('minecraft:basalt', ('Basalt', '玄武岩', '玄武岩')), ('minecraft:glass', ('Glass', '玻璃', '玻璃')),
                        ('minecraft:obsidian', ('Obsidian', '黑曜石', '黑曜石')), ('minecraft:lava_bucket', ('Lava Bucket', '岩漿桶', '熔岩桶'))]:
        c.guide_name(item, *names)
    text = ('Glows like a lantern and keeps one lava creature: Blazefin, Lava Eel, Magma Koi, Basalt Crab or the Lava Dragon Koi. Use one on it to put it in, an empty hand to take it back; size marks, records and names are kept. It sets nothing alight. Water fish do not go in, and these lava creatures do not go in a water tank (the Dragon Koi goes in either).',
            '像燈一樣發光，可以養一隻熔岩生物：焰鰭魚、熔岩鰻、熔岩錦鯉、玄武岩蟹或熔岩龍鯉。拿牠對缸使用就放進去，空手取回；尺寸、紀錄和名字都會保留。不會點燃周圍。一般的魚放不進去，這幾種熔岩生物也放不進一般魚缸（熔岩龍鯉兩種都可以）。',
            '像灯一样发光，可以养一只熔岩生物：焰鳍鱼、熔岩鳗、熔岩锦鲤、玄武岩蟹或熔岩龙鲤。拿它对缸使用就放进去，空手取回；尺寸、纪录和名字都会保留。不会点燃周围。一般的鱼放不进去，这几种熔岩生物也放不进一般鱼缸（熔岩龙鲤两种都可以）。')
    g = c.data('GUIDEBOOK_JSON')
    entry = {'id': S + 'lava_fish_tank', 'category': 'tools', 'kinds': ['item', 'block'], 'stack': 64, 'icon': 'textures/ui/kfv_book/kfv_lava_fish_tank',
             'recipes': [{'method': 'Crafting Table', 'ingredients': [keys[ch] for row in pattern for ch in row], 'count': 1, 'time': 0, 'result': S + 'lava_fish_tank'}],
             'mechanicsByLocale': {'en_US': [text[0]], 'zh_TW': [text[1]], 'zh_CN': [text[2]]}, 'mechanics': [text[0]]}
    g['entries'] = [e for e in g['entries'] if e['id'] != entry['id']] + [entry]
    for code, t in zip(c.LANGS, name):
        g['names'][code][S + 'lava_fish_tank'] = t
    c.save('GUIDEBOOK_JSON', g)


NEW_FISH = {
    # key: (names en/tw/cn, habitat en/tw/cn, catch entry, journal sized?, raw food or None, fish tag?, price, board, minigame pattern)
    'mycelium_flounder': (('Mycelium Flounder', '菌褶鰈', '菌褶鲽'),
        ('Any water on a mushroom island, the commonest catch there. Flat on the bottom, the gills of a mushroom on its back.',
         '蘑菇島上的任何水域，那裡最常見的漁獲。平貼在水底，背上有像菇褶的花紋。', '蘑菇岛上的任何水域，那里最常见的渔获。平贴在水底，背上有像菇褶的花纹。'),
        {'w': 24, 'waters': ['mushroom'], 'size': [20, 50], 'fight': 1}, True, (2, 0.2), True, 0.3333,
        {'first': 1, 'cuts': 'fish', 'fillet': 3, 'bones': 1}, 'sinker'),
    'spore_seahorse': (('Spore Seahorse', '孢子海馬', '孢子海马'),
        ('Mushroom island waters, at night only. A seahorse dusted with spores: a curio for a fish tank, not for the pot; the fish merchant pays well for one.',
         '蘑菇島的水域，只在夜晚。身上沾滿孢子的海馬：養在魚缸裡觀賞，不能下鍋；漁販會出好價錢。', '蘑菇岛的水域，只在夜晚。身上沾满孢子的海马：养在鱼缸里观赏，不能下锅；渔贩会出好价钱。'),
        {'w': 6, 'waters': ['mushroom'], 'time': 'night', 'off': 0.0, 'size': None, 'fight': 0}, False, None, False, 1.5, None, None),
    'cherry_trout': (('Cherry Trout', '櫻鱒', '樱鳟'),
        ('Lakes and rivers in a cherry grove; more of them at high tide. A trout with a blossom-pink stripe.',
         '櫻花樹林裡的湖和河；漲潮時更多。身上有一條櫻花色條紋的鱒魚。', '樱花树林里的湖和河；涨潮时更多。身上有一条樱花色条纹的鳟鱼。'),
        {'w': 24, 'waters': ['cherry'], 'size': [25, 55], 'fight': 2, 'tide': {'high': 1.5}}, True, (2, 0.2), True, 0.3333,
        {'first': 1, 'cuts': 'fish', 'fillet': 3, 'bones': 1, 'roe': 0.4, 'gutted': True}, 'dash'),
    'creek_shrimp': (('Creek Shrimp', '溪蝦', '溪虾'),
        ('Cherry grove streams, by day; earthworms bring them up. Small and see-through: fry them whole, or use them as any shrimp.',
         '櫻花樹林的溪流，白天出沒；用蚯蚓比較容易。小小的、半透明：整隻炸來吃，或當一般的蝦用。', '樱花树林的溪流，白天出没；用蚯蚓比较容易。小小的、半透明：整只炸来吃，或当一般的虾用。'),
        {'w': 10, 'waters': ['cherry'], 'time': 'day', 'off': 0.0, 'bait': {NS + 'earthworm': 2}, 'size': None, 'fight': 0}, False, (1, 0.2), False, 0.2,
        {'first': 1, 'cuts': 'shrimp'}, None),
    'echo_ray': (('Echo Ray', '回音魟', '回音魟'),
        ('Water in the Deep Dark (a pool you make there with a bucket will do). Big, flat and strong. Fishing there makes a noise: crouch and stand on wool.',
         '深暗之域裡的水（用水桶自己做的水池也可以）。又大又扁、力氣很大。在那裡釣魚會發出聲音：蹲下、站在羊毛上。', '深暗之域里的水（用水桶自己做的水池也可以）。又大又扁、力气很大。在那里钓鱼会发出声音：蹲下、站在羊毛上。'),
        {'w': 20, 'waters': ['deep_dark'], 'size': [40, 120], 'fight': 2}, True, (3, 0.3), True, 0.5,
        {'first': 2, 'cuts': 'fish', 'fillet': 4, 'bones': 1}, 'sinker'),
    'sculk_lanternfish': (('Sculk Lanternfish', '幽匿燈籠魚', '幽匿灯笼鱼'),
        ('Water in the Deep Dark, and only on Glow Bait: it comes to light. Two of them make Glow Bait again.',
         '深暗之域裡的水，只咬發光餌：牠會被光引來。兩條可以再做成發光餌。', '深暗之域里的水，只咬发光饵：它会被光引来。两条可以再做成发光饵。'),
        {'w': 6, 'waters': ['deep_dark'], 'needBait': [NS + 'glow_bait'], 'size': [5, 12], 'fight': 0}, True, (1, 0.1), True, 1.0,
        {'first': 1, 'cuts': 'fish', 'fillet': 1, 'bones': 1}, 'dart'),
}


def _add_fish(table, group, after):
    """Items, names, habitat, catches, journal page, creel, price, board, guide page for each fish of a table like NEW_FISH."""
    S = NS
    catches = c.data('CATCHES')
    journal = c.data('JOURNAL_SPECIES')
    basket = c.data('BASKET_ITEMS')
    prices = c.data('MERCHANT_PRICES')
    board = c.data('CLEANING')
    next_board = max(f['index'] for f in board.values()) + 1
    for key, (name, where, entry, sized, edible, fish_tag, price, cut, pattern) in table.items():
        comp = {}
        if edible:
            comp = food(*edible)
            if fish_tag:
                comp['minecraft:tags']['tags'].append('minecraft:is_fish')
        c.item(key, stack=64, group='catches', components=comp or None)
        path = os.path.join(c.BP, 'items', f'{key}.json')
        j = c.read_json(path)                                  # catches sit in the pack's own creative group
        j['minecraft:item']['description']['menu_category']['group'] = f'{c.NS}:itemGroup.name.catches'
        c.write_json(path, j)
        c.names(key, *name)
        c.lang(f'{c.NS}.habitat.{key}', *where, packs=(c.RP,))
        c.icon(key)
        c.catalog(key, after)
        after = key
        catches = [x for x in catches if x['id'] != S + key] + [{'id': S + key, **entry}]
        journal = [x for x in journal if x['id'] != S + key] + [{'id': S + key, 'key': key, 'icon': f'textures/items/kfv_{key}', 'sized': sized, 'group': group}]
        basket = [x for x in basket if x['id'] != S + key] + [{'id': S + key, 'nameKey': f'{c.NS}.name.{key}', 'icon': f'textures/items/kfv_{key}'}]
        prices[S + key] = price
        if cut:
            idx = board.get(S + key, {}).get('index') or next_board
            if idx == next_board:
                next_board += 1
            if cut['cuts'] == 'shrimp':
                cuts = [{'act': 'head', 'out': [[S + 'shrimp_head', 1]]}, {'act': 'shell', 'out': [[S + 'shrimp_shell', 1]]},
                        {'act': 'devein', 'out': [[S + 'shrimp_meat', 1, 1, 'sized']]}]
                rec = {'index': idx, 'first': 1, 'cuts': cuts}
            else:
                cuts = ([{'act': 'scale', 'out': [[S + 'fish_scales', 1]]}] if cut['first'] == 1 else []) + \
                       [{'act': 'gut', 'out': [[S + 'fish_offal', 1]] + ([[S + 'fish_roe', 1, cut['roe']]] if cut.get('roe') else [])},
                        {'act': 'fillet', 'out': [[S + 'white_fish_fillet', cut['fillet'], 1, 'sized'], [S + 'fish_bones', cut['bones']]]}]
                rec = {'index': idx, 'first': cut['first'], 'cuts': cuts}
                if cut.get('gutted'):
                    rec['gutted'] = S + 'gutted_fish'
            board[S + key] = rec
        food_info = {'nutrition': edible[0], 'saturation': edible[1]} if edible else None
        c.guide(key, 'fish' if fish_tag else 'seafood', where, name, stack=64, food=food_info)
    c.save('CATCHES', catches); c.save('JOURNAL_SPECIES', journal); c.save('BASKET_ITEMS', basket)
    c.save('MERCHANT_PRICES', prices); c.save('CLEANING', board)
    mp = os.path.join(c.BP, 'scripts', 'data', 'minigame.js')
    js = open(mp, encoding='utf-8').read()
    for key, v in table.items():
        pat = v[8]
        if pat and f"'{S}{key}'" not in js:
            js = js.replace("export const PATTERN = {\n", f"export const PATTERN = {{\n  '{S}{key}': '{pat}',   // 1.5.0\n", 1)
    with open(mp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(js)
    cp = os.path.join(c.BP, 'entities', 'cormorant.json')
    e = c.read_json(cp)
    groups = e['minecraft:entity']['component_groups']
    fishy = [S + k for k, v in table.items() if v[5]]
    for lst in (groups[f'{c.NS}:wild']['minecraft:tameable']['tame_items'], groups[f'{c.NS}:wild']['minecraft:behavior.tempt']['items']):
        lst += [f for f in fishy if f not in lst]
    heal = groups[f'{c.NS}:tamed']['minecraft:healable']['items']
    heal += [{'item': f, 'heal_amount': 4} for f in fishy if f not in [h['item'] for h in heal]]
    c.write_json(cp, e)


def new_waters():
    """Step 10: three new waters and their six fish, a journal page for them, and four dishes (plan 8)."""
    S = NS
    J = f'{c.NS}.journal.'
    c.lang(J + 'group_secret', 'Hidden Waters', '秘境', '秘境', packs=(c.RP,))
    _add_fish(NEW_FISH, 'secret', 'cave_crayfish')
    # dishes
    for key, name, n, sat, how, bowl in [
        ('mushroom_flounder_stew', ('Mushroom and Flounder Stew', '菇菌燉鰈魚', '菇菌炖鲽鱼'), 8, 0.7,
         [('stockpot', ['white_fish_fillet', 'minecraft:brown_mushroom', 'minecraft:brown_mushroom', 'minecraft:carrot'], None)], True),
        ('cherry_trout_rice', ('Cherry Trout Rice', '櫻鱒炊飯', '樱鳟炊饭'), 9, 0.7,
         [('stockpot', ['white_fish_fillet', 'kaleidoscope_cookery:rice', 'minecraft:kelp', 'minecraft:kelp'], None)], True),
        ('fried_creek_shrimp', ('Fried Creek Shrimp', '炸溪蝦', '炸溪虾'), 6, 0.6,
         [('wok', ['creek_shrimp', 'creek_shrimp', 'kaleidoscope_cookery:flour', 'kaleidoscope_cookery:oil'], None)], True),
        ('echo_ray_pot', ('Echo Ray Pot', '回音魟魚煲', '回音魟鱼煲'), 10, 0.8,
         [('stockpot', ['white_fish_fillet', 'white_fish_fillet', 'minecraft:potato', 'kaleidoscope_cookery:red_chili'], None)], True),
    ]:
        c.dish(key, name, n, sat, how, bowl=bowl, after='blindfish_clear_soup')
    # what else takes them
    c.recipe_file('crafting', 'glow_bait_from_lanternfish', {'format_version': '1.20.10', 'minecraft:recipe_shapeless': {
        'description': {'identifier': S + 'glow_bait_from_lanternfish'}, 'tags': ['crafting_table'],
        'ingredients': [{'item': S + 'sculk_lanternfish'}, {'item': S + 'sculk_lanternfish'}],
        'result': {'item': S + 'glow_bait', 'count': 2}, 'unlock': [{'item': S + 'sculk_lanternfish'}]}})
    for rid in ('wok/salt_pepper_shrimp', 'wok/shrimp_scrambled_eggs', 'stockpot/seafood_congee', 'wok/seafood_chow_mein', 'wok/paella', 'stockpot/seafood_hot_pot'):
        c.kc_alternative(rid, 'shrimp', 'creek_shrimp')
    table = c.data('KC_RECIPES')
    for r in table:
        if r['recipe']['id'] == S + 'stockpot/salted_shrimp':
            r['recipe']['ingredients'] = [i + [S + 'creek_shrimp'] if isinstance(i, list) and S + 'shrimp' in i and S + 'creek_shrimp' not in i else i
                                          for i in r['recipe']['ingredients']]
    c.save('KC_RECIPES', table)


SKY_FISH = {
    'meteor_marlin': (('Meteor Marlin', '流星旗魚', '流星旗鱼'),
        ('Open and deep sea, only on a meteor-shower night. Huge, fast and very hard to land; specks of starlight on its back. Too big for a tank.',
         '海域與深海，只在流星雨的夜晚。巨大、快、非常難拉上來；背上有星光般的斑點。太大了，放不進魚缸。',
         '海域与深海，只在流星雨的夜晚。巨大、快、非常难拉上来；背上有星光般的斑点。太大了，放不进鱼缸。'),
        {'w': 3, 'waters': ['ocean', 'deep_ocean', 'warm_ocean'], 'sky': 'meteor', 'tier': 2, 'size': [180, 350], 'fight': 6}, True, (3, 0.3), True, 2.5,
        {'first': 1, 'cuts': 'fish', 'fillet': 8, 'bones': 2}, 'dash'),
    'aurora_icefish': (('Aurora Icefish', '極光銀魚', '极光银鱼'),
        ('Under the ice, only on an aurora night (seen from a cold biome). Small and see-through; it shows the colours of the sky. Cooked whole; it stands in for Smelt.',
         '冰面底下，只在極光之夜（在寒冷的生物群系才看得到）。小小的、半透明，映著天上的顏色。整條入菜，可以代替公魚。',
         '冰面底下，只在极光之夜（在寒冷的生物群系才看得到）。小小的、半透明，映着天上的颜色。整条入菜，可以代替公鱼。'),
        {'w': 14, 'waters': ['ice'], 'sky': 'aurora', 'size': [5, 10], 'fight': 0}, True, (1, 0.2), True, 0.6, None, None),
}


def sky_events():
    """Step 11: sky events (plan 10): the two sky fish, star sand, the glowing glass float, the journal's Sky page;
    the starfin rises into the sea under meteors, and the aurora stands in for the Frostlake Char's new moon."""
    S = NS
    J = f'{c.NS}.journal.'
    c.lang(J + 'group_sky', 'Sky', '天象', '天象', packs=(c.RP,))
    c.lang(J + 'sky_meteor', '§eTonight: a meteor shower.§r Starfins come up into the sea, the Meteor Marlin bites, and bubbling beach sand may hold Star Sand.',
           '§e今晚的天象：流星雨。§r星鰭魚浮上海面，流星旗魚會咬鉤，海灘冒泡的沙地可能挖到星砂。',
           '§e今晚的天象：流星雨。§r星鳍鱼浮上海面，流星旗鱼会咬钩，海滩冒泡的沙地可能挖到星砂。', packs=(c.RP,))
    c.lang(J + 'sky_aurora', '§bTonight: an aurora,§r seen in cold biomes. Fish under the ice bite sooner, the Aurora Icefish comes up, and the Frostlake Char does not wait for the new moon.',
           '§b今晚的天象：極光之夜§r（寒冷的生物群系看得到）。冰下的魚咬鉤比較快，極光銀魚會出現，冰湖主不必等新月。',
           '§b今晚的天象：极光之夜§r（寒冷的生物群系看得到）。冰下的鱼咬钩比较快，极光银鱼会出现，冰湖主不必等新月。', packs=(c.RP,))
    _add_fish(SKY_FISH, 'sky', 'sculk_lanternfish')
    catches = c.data('CATCHES')
    for e in catches:
        if e['id'] == S + 'starfin':
            e['sky_waters'] = {'meteor': ['ocean', 'deep_ocean', 'warm_ocean', 'cold_ocean']}
        if e['id'] == S + 'frostlake_char':
            e['req']['sky_moon'] = 'aurora'
    c.save('CATCHES', catches)
    c.lang(f'{c.NS}.habitat.starfin',
           'Rare, deep in the void (Ender Fishing Rod): the bait has to hang deep, so fit a Weighted Bobber. On a meteor-shower night it also comes up in the deep sea. A long fight. Slow falling and night vision.',
           '稀有，在虛空深處（末影釣竿）：餌要垂得夠深，得裝上重墜浮標。流星雨的夜晚也會出現在海裡較深的地方。拉扯很久。吃了緩降又有夜視。',
           '稀有，在虚空深处（末影钓竿）：饵要垂得够深，得装上重坠浮标。流星雨的夜晚也会出现在海里较深的地方。拉扯很久。吃了缓降又有夜视。', packs=(c.RP,))
    c.lang(f'{c.NS}.habitat.frostlake_char',
           'Under the ice at dawn after a new moon, or at dawn after an aurora night. A tip-up will never take it; fish for it by hand.',
           '新月後的清晨，冰面底下；極光之夜後的清晨也可以。插旗浮標釣不到，要親手釣。',
           '新月后的清晨，冰面底下；极光之夜后的清晨也可以。插旗浮标钓不到，要亲手钓。', packs=(c.RP,))
    # the icefish in smelt dishes
    for r in c.data('KC_RECIPES'):
        ing = r['recipe'].get('ingredients') or []
        if any(S + 'smelt' in (i if isinstance(i, list) else [i]) for i in ing) and r['recipe']['id'].startswith(S + 'wok/'):
            c.kc_alternative(r['recipe']['id'].split(':')[1], 'smelt', 'aurora_icefish')
    # ---- star sand
    name = ('Star Sand', '星砂', '星砂')
    c.item('star_sand', stack=64, group='ingredients')
    c.names('star_sand', *name)
    c.icon('star_sand')
    c.catalog('star_sand', 'glow_bait')
    bait = c.recipe_file('crafting', 'glow_bait_from_star_sand', {'format_version': '1.20.10', 'minecraft:recipe_shapeless': {
        'description': {'identifier': S + 'glow_bait_from_star_sand'}, 'tags': ['crafting_table'],
        'ingredients': [{'item': S + 'star_sand'}, {'item': S + 'fish_meal'}],
        'result': {'item': S + 'glow_bait', 'count': 4}, 'unlock': [{'item': S + 'star_sand'}]}})
    c.guide('star_sand', 'ingredients', (
        'Tiny star-shaped grains. On a meteor-shower night, bubbling beach sand dug with a shovel sometimes gives one as well. With Fish Meal it makes 4 Glow Bait; used on a placed Glass Float it makes the float glow.',
        '一粒粒小星星形狀的沙。流星雨的夜晚，用鏟子挖海灘冒泡的沙地，有時會多挖到一個。和魚粉做成發光餌 ×4；對放好的玻璃浮球使用，浮球會發光。',
        '一粒粒小星星形状的沙。流星雨的夜晚，用铲子挖海滩冒泡的沙地，有时会多挖到一个。和鱼粉做成发光饵 ×4；对放好的玻璃浮球使用，浮球会发光。'), name, stack=64,
        recipes=[{'method': 'Crafting Table', 'ingredients': [S + 'star_sand', S + 'fish_meal'], 'count': 4, 'time': 0, 'result': S + 'glow_bait'}])
    # ---- the glowing glass float
    src = c.read_json(os.path.join(c.BP, 'blocks', 'glass_float.json'))
    src['minecraft:block']['components'][S + 'star_float'] = {}
    c.write_json(os.path.join(c.BP, 'blocks', 'glass_float.json'), src)
    blk = c.read_json(os.path.join(c.BP, 'blocks', 'glass_float.json'))
    b = blk['minecraft:block']
    b['description']['identifier'] = S + 'glowing_glass_float'
    comp = b['components']
    comp.pop(S + 'star_float')
    comp['minecraft:display_name'] = f'%{c.NS}.display.item.glowing_glass_float'
    comp['minecraft:material_instances'] = {'*': {'texture': 'kfv_glowing_glass_float', 'render_method': 'alpha_test'}}
    comp['minecraft:light_emission'] = 12
    comp['minecraft:map_color'] = '#9FE8E0'
    comp['minecraft:loot'] = f'loot_tables/{c.NS}/blocks/glowing_glass_float.json'
    c.write_json(os.path.join(c.BP, 'blocks', 'glowing_glass_float.json'), blk)
    c.write_json(os.path.join(c.BP, 'loot_tables', c.NS, 'blocks', 'glowing_glass_float.json'),
                 {'pools': [{'rolls': 1, 'entries': [{'type': 'item', 'name': S + 'glowing_glass_float'}]}]})
    it = c.read_json(os.path.join(c.BP, 'items', 'glass_float.json'))
    d = it['minecraft:item']
    d['description']['identifier'] = S + 'glowing_glass_float'
    d['components']['minecraft:display_name'] = {'value': f'%{c.NS}.display.item.glowing_glass_float'}
    d['components']['minecraft:icon'] = 'kfv_glowing_glass_float'
    d['components']['minecraft:block_placer'] = {'block': S + 'glowing_glass_float', 'replace_block_item': True}
    c.write_json(os.path.join(c.BP, 'items', 'glowing_glass_float.json'), it)
    gname = ('Glowing Glass Float', '發光玻璃浮球', '发光玻璃浮球')
    c.names('glowing_glass_float', *gname, placeable=True)
    c.icon('glowing_glass_float')
    tp = os.path.join(c.RP, 'textures', 'terrain_texture.json')
    t = c.read_json(tp)
    t['texture_data']['kfv_glowing_glass_float'] = {'textures': 'textures/blocks/kfv_glowing_glass_float'}
    c.write_json(tp, t)
    c.catalog('glowing_glass_float', 'glass_float')
    g = c.data('GUIDEBOOK_JSON')
    text = ('A Glass Float with Star Sand rubbed in: it glows softly. Use Star Sand on a placed Glass Float to make one.',
            '抹了星砂的玻璃浮球，會發出柔和的光。拿星砂對放好的玻璃浮球使用就會變成這個。',
            '抹了星砂的玻璃浮球，会发出柔和的光。拿星砂对放好的玻璃浮球使用就会变成这个。')
    entry = {'id': S + 'glowing_glass_float', 'category': 'decor' if any(e.get('category') == 'decor' for e in g['entries']) else 'tools',
             'kinds': ['item', 'block'], 'stack': 64, 'icon': 'textures/items/kfv_glowing_glass_float',
             'recipes': [], 'mechanicsByLocale': {'en_US': [text[0]], 'zh_TW': [text[1]], 'zh_CN': [text[2]]}, 'mechanics': [text[0]]}
    g['entries'] = [e for e in g['entries'] if e['id'] != entry['id']] + [entry]
    for code, n in zip(c.LANGS, gname):
        g['names'][code][entry['id']] = n
    c.save('GUIDEBOOK_JSON', g)


def shore_growth():
    """Step 12: Oyster Beds and Laver Rocks grow (plan 7.1). A `growth` state (2 grown, the default, so beds the world
    made and 1.4 beds count as grown; 0 just set down; 1 small) shown by scaling the grown model down; a block tick
    for the script (blocks/shoreDrop.js); harvest 2-4."""
    S = NS
    rot = {'north': 0, 'east': 270, 'south': 180, 'west': 90}
    scale = {2: None, 1: [0.8, 0.65, 0.8], 0: [0.55, 0.4, 0.55]}
    texts = {
        'oyster_bed': ('Oysters', '牡蠣', '牡蛎', 'on beaches by the water', '長在海灘水邊', '长在海滩水边', 'a bed', '整塊', '整块'),
        'laver_rock': ('Laver', '紫菜', '紫菜', 'on beaches and stony shores', '長在海灘與石岸', '长在海滩与石岸', 'the rock', '整塊', '整块'),
    }
    g = c.data('GUIDEBOOK_JSON')
    for key, (en, tw, cn, en_w, tw_w, cn_w, en_b, tw_b, cn_b) in texts.items():
        path = os.path.join(c.BP, 'blocks', f'{key}.json')
        j = c.read_json(path)
        b = j['minecraft:block']
        b['description']['states'] = {S + 'growth': [2, 0, 1]}
        comp = b['components']
        comp['minecraft:tick'] = {'interval_range': [400, 600], 'looping': True}
        comp[S + 'shore_drop']['harvest'] = [2, 4]
        perms = []
        for stage in (2, 1, 0):
            for d, r in rot.items():
                t = {'rotation': [0, r, 0]}
                if scale[stage]:
                    t.update({'scale': scale[stage], 'scale_pivot': [0, -0.5, 0]})
                perms.append({'condition': f"q.block_state('minecraft:cardinal_direction') == '{d}' && q.block_state('{S}growth') == {stage}",
                              'components': {'minecraft:transformation': t}})
        b['permutations'] = perms
        c.write_json(path, j)
        text = (f'Grows {en_w}. Set down under water on sand, gravel or stone by the sea, it grows (just set down, small, grown: about a day each, twice as fast at low tide). Use a grown one with an empty hand or a knife to gather 2-4 {en}; it goes back to small. Broken grown it gives 1-3 {en}, not yet grown only 1; Silk Touch keeps {en_b}.',
                f'{tw_w}。放在海邊水裡的沙、礫石或石頭上會長大（剛放下、小、成熟，每段大約一天，退潮時快一倍）。成熟後空手或拿刀使用，採下 {tw} 2～4 個，回到「小」繼續長。成熟時打掉得 1～3 個，還沒長大只得 1 個；絲綢之觸可以{tw_b}帶走。',
                f'{cn_w}。放在海边水里的沙、砾石或石头上会长大（刚放下、小、成熟，每段大约一天，退潮时快一倍）。成熟后空手或拿刀使用，采下 {cn} 2～4 个，回到“小”继续长。成熟时打掉得 1～3 个，还没长大只得 1 个；精准采集可以{cn_b}带走。')
        for e in g['entries']:
            if e['id'] == S + key:
                e['mechanicsByLocale'] = {'en_US': [text[0]], 'zh_TW': [text[1]], 'zh_CN': [text[2]]}
                e['mechanics'] = [text[0]]
    c.save('GUIDEBOOK_JSON', g)


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
    shrimp_head_stock()
    dried_shrimp()
    squid_and_tuna()
    dried_fish()
    tub_and_salt_pan()
    lava_tank()
    new_waters()
    sky_events()
    shore_growth()
    print('1.5.0 content written; now run: python tools/build.py build')
