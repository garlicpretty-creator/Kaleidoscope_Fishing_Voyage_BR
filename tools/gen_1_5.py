"""Content added in 1.5.0, step by step as docs/PLAN_1.5.0.md lays it out. Run again any time:

  python tools/icons_1_5.py && python tools/gen_1_5.py && python tools/build.py build
"""
import content as c

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
    c.item('tide_clock', stack=1)
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


if __name__ == '__main__':
    legends()
    creel()
    journal()
    merchant_order()
    tide_clock()
    print('1.5.0 content written; now run: python tools/build.py build')
