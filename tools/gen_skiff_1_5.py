"""The Fishing Skiff (釣魚小船, 1.5.0, plan 8): a rideable boat with a fish hold, a lantern and a trawl net.

  python tools/gen_skiff_1_5.py

The behaviour entity runs on the game's own chest boat (runtime_identifier minecraft:chest_boat): the game moves it on
the water, seats one rider and keeps the 27-slot hold (crouch and use it to open, as a chest boat). The scripts
(world/boat.js) add the rest: catches go into the hold, the trawl, the lantern at night. A first-pass model of boxes
(tools/modelkit.py): a plank hull, a fish crate at the stern, a lantern on a pole at the bow; the net shows behind the
stern while the trawl is out (property kaleidoscope_fishing:trawl). Writes the BP entity, item, recipe and loot table,
the RP client entity, geometry, texture and render controller. Safe to run again.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modelkit import Atlas, box, write_geometries, texture_set

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [BP]')
RP = os.path.join(ROOT, 'Kaleidoscope Fishing Voyage [RP]')
NS = 'kaleidoscope_fishing'
ID = f'{NS}:fishing_skiff'


def bone(name, cubes, parent='root'):
    return {'name': name, 'parent': parent, 'pivot': [0, 0, 0], 'cubes': cubes}


def model():
    a = Atlas(128, 64)
    oak, oak_dark, oak_side = '#a8834e', '#6b4f2a', '#8c6a3c'
    hull = [box(-9, 9, 0, 2, -14, 14, oak, oak_dark, oak_dark, atlas=a)]                              # bottom
    hull += [box(-11, -9, 0, 8, -14, 14, oak, oak_side, atlas=a), box(9, 11, 0, 8, -14, 14, oak, oak_side, atlas=a)]
    hull += [box(-9, 9, 0, 8, -16, -14, oak, oak_side, atlas=a), box(-9, 9, 0, 8, 14, 16, oak, oak_side, atlas=a)]
    hull += [box(-9, 9, 5, 6, -2, 2, oak, oak_dark, atlas=a)]                                        # the thwart (seat)
    crate = [box(-7, 7, 2, 10, 6, 13.5, '#b58a52', '#7a5a30', atlas=a), box(-7.2, 7.2, 9.6, 10.4, 6, 13.6, '#6b4f2a', atlas=a)]
    lantern = [box(-1, 1, 2, 22, -12, -10, '#5a4128', '#3e2c18', atlas=a),                            # the pole
               box(-1, 1, 20, 22, -12, -6, '#5a4128', atlas=a),                                         # the arm
               box(-2, 2, 15, 19, -8, -4, '#ffd36a', '#f0a830', atlas=a),                                # the light
               box(-2.5, 2.5, 19, 20, -8.5, -3.5, '#3a3a40', atlas=a), box(-2.5, 2.5, 14.5, 15, -8.5, -3.5, '#3a3a40', atlas=a)]
    net = [box(-8, 8, -1, 5, 16, 30, '#b8c0a88a', '#98a0888a', atlas=a), box(-1, 1, 3, 4, 14, 17, '#d8d0b0', atlas=a)]
    bones = [{'name': 'root', 'pivot': [0, 0, 0]}, bone('hull', hull), bone('crate', crate), bone('lantern', lantern), bone('net', net)]
    return a, bones


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')


def main():
    atlas, bones = model()
    geo = os.path.join(RP, 'models', 'entity', 'fishing_skiff.geo.json')
    write_geometries(geo, [{'description': {'identifier': f'geometry.{NS}.fishing_skiff', 'texture_width': atlas.w, 'texture_height': atlas.h,
                                            'visible_bounds_width': 4, 'visible_bounds_height': 3, 'visible_bounds_offset': [0, 0.5, 0]},
                            'bones': bones}])
    png = os.path.join(RP, 'textures', 'entity', 'kfv_fishing_skiff.png')
    atlas.save(png)
    texture_set(png)
    write_json(os.path.join(RP, 'entity', 'fishing_skiff.entity.json'), {'format_version': '1.10.0', 'minecraft:client_entity': {'description': {
        'identifier': ID, 'materials': {'default': 'entity_alphatest'}, 'textures': {'default': 'textures/entity/kfv_fishing_skiff'},
        'geometry': {'default': f'geometry.{NS}.fishing_skiff'}, 'render_controllers': [f'controller.render.{NS}.fishing_skiff']}}})
    write_json(os.path.join(RP, 'render_controllers', 'kfv_fishing_skiff.render_controllers.json'), {'format_version': '1.8.0', 'render_controllers': {
        f'controller.render.{NS}.fishing_skiff': {'geometry': 'Geometry.default', 'materials': [{'*': 'Material.default'}], 'textures': ['Texture.default'],
                                                 'part_visibility': [{'*': True}, {'net': f"q.property('{NS}:trawl') == 1"}]}}})
    write_json(os.path.join(BP, 'entities', 'fishing_skiff.json'), {'format_version': '1.21.60', 'minecraft:entity': {
        'description': {'identifier': ID, 'runtime_identifier': 'minecraft:chest_boat', 'is_spawnable': False, 'is_summonable': True,
                        'properties': {f'{NS}:trawl': {'type': 'int', 'range': [0, 1], 'default': 0, 'client_sync': True}}},
        'components': {
            'minecraft:type_family': {'family': ['boat', 'inanimate', 'fishing_skiff']},
            'minecraft:collision_box': {'width': 1.4, 'height': 0.455},
            'minecraft:inventory': {'container_type': 'chest_boat', 'inventory_size': 27, 'can_be_siphoned_from': True},
            'minecraft:rideable': {'seat_count': 1, 'interact_text': 'action.interact.ride.boat', 'pull_in_entities': True,
                                   'family_types': ['player'], 'seats': [{'position': [0, -0.2, 0], 'min_rider_count': 0, 'max_rider_count': 1}]},
            'minecraft:buoyant': {'apply_gravity': True, 'base_buoyancy': 1.0, 'simulate_waves': False, 'big_wave_probability': 0.03,
                                  'big_wave_speed': 10.0, 'liquid_blocks': ['minecraft:water', 'minecraft:flowing_water']},
            'minecraft:physics': {}, 'minecraft:pushable': {'is_pushable': True, 'is_pushable_by_piston': True},
            'minecraft:leashable': {'soft_distance': 4.0, 'hard_distance': 6.0, 'max_distance': 10.0},
            'minecraft:loot': {'table': f'loot_tables/{NS}/entities/fishing_skiff.json'},
            'minecraft:is_stackable': {}}}})
    write_json(os.path.join(BP, 'loot_tables', NS, 'entities', 'fishing_skiff.json'), {'pools': [{'rolls': 1, 'entries': [{'type': 'item', 'name': ID}]}]})
    print('wrote the Fishing Skiff')


if __name__ == '__main__':
    main()
