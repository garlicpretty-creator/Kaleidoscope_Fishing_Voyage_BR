"""Fish Tank species added in 1.5.0: the four lava creatures for the Lava Fish Tank, and the oyster.

  python tools/gen_tank_1_5.py        (then python tools/build.py build)

Adds each to tools/data/TANK_FISH.json (its index there is its `species` on the tank entity), copies the tank
placement rows of a creature of the same build in scripts/data/tank.js (TANK_KIND, FIT), lists its geometry in
the tank fish's client entity and render controller, and runs tools/repaint_tank_fish.py, which builds the models
(CLONES there) and paints them from the icons. Safe to run again.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [BP]')
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
NS = 'kaleidoscope_fishing'
# new species: (placed like this one, keep still)
NEW = {'blazefin': ('carp', False), 'magma_koi': ('lava_dragon_koi', False), 'lava_eel': ('eel', False),
       'basalt_crab': ('crab', False), 'oyster': ('crab', True)}
LAVA = ['blazefin', 'magma_koi', 'lava_eel', 'basalt_crab', 'lava_dragon_koi']


def main():
    path = os.path.join(HERE, 'data', 'TANK_FISH.json')
    tank = json.load(open(path, encoding='utf-8'))
    for k in NEW:
        if f'{NS}:{k}' not in tank:
            tank.append(f'{NS}:{k}')
    raw = open(path, encoding='utf-8').read()
    ind = re.search(r'\n( +)"', raw)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(tank, f, indent=len(ind.group(1)) if ind else 1)
        f.write('\n' if raw.endswith('\n') else '')
    short = [t.split(':')[1] for t in tank]
    # placement rows
    tp = os.path.join(BP, 'scripts', 'data', 'tank.js')
    js = open(tp, encoding='utf-8').read()
    kind = json.loads(re.search(r'TANK_KIND = (\[.*?\]);', js).group(1))
    fit = json.loads(re.search(r'FIT = (\[.*?\]);\n', js, re.S).group(1))
    for i, name in enumerate(short):
        if i < len(kind):
            continue
        like, still = NEW[name]
        j = short.index(like)
        kind.append(kind[j])
        rows = json.loads(json.dumps(fit[j]))
        if still:                                        # an oyster stays where it is put
            for tank_rows in rows:
                for r in tank_rows:
                    r[1] = 0
        fit.append(rows)
    js = re.sub(r'TANK_KIND = \[.*?\];', 'TANK_KIND = ' + json.dumps(kind) + ';', js, count=1)
    js = re.sub(r'FIT = \[.*?\];\n', 'FIT = ' + json.dumps(fit, separators=(',', ':')) + ';\n', js, count=1, flags=re.S)
    if '1.5.0: the lava creatures' not in js:
        js = js.replace('// kind: 0 fish,', '// 1.5.0: the lava creatures (for the Lava Fish Tank) and the oyster (still) follow, by tools/gen_tank_1_5.py.\n// kind: 0 fish,', 1)
    with open(tp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(js)
    # client entity and render controller
    ep = os.path.join(RP, 'entity', 'tank_fish.entity.json')
    ent = json.load(open(ep, encoding='utf-8'))
    geos = ent['minecraft:client_entity']['description']['geometry']
    for name in short:
        geos.setdefault(name, f'geometry.{NS}.tank_fish.{name}')
    with open(ep, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(ent, f, indent=2, ensure_ascii=False)
    rp = os.path.join(RP, 'render_controllers', 'kfv_tank_fish.render_controllers.json')
    rc = json.load(open(rp, encoding='utf-8'))
    rc['render_controllers'][f'controller.render.{NS}.tank_fish']['arrays']['geometries']['Array.geos'] = [f'Geometry.{n}' for n in short]
    with open(rp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rc, f, indent=2)
    subprocess.run([sys.executable, os.path.join(HERE, 'repaint_tank_fish.py')], check=True)


if __name__ == '__main__':
    main()
