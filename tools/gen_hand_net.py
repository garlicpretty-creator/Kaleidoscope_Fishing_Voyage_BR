"""Hand Net (撈網, 1.6.0): the held 3D model, its texture and the attachable (docs/PLAN_1.6.0.md section 7.1).

  python tools/gen_hand_net.py

Writes, in the resource pack:
  models/entity/hand_net.geo.json           the player skeleton (as the rods) with a "net" bone in the right hand
  textures/entity/kfv_hand_net.png          32x32, painted here; texture set + RTX maps (tools/pbr.py)
  animations/hand_net.animation.json        held in first and third person: the rods' grip, the hoop up
  attachables/hand_net.json                 kaleidoscope_fishing:hand_net uses all of the above

The net: an ash handle with a cord-wrapped grip and a brass ferrule, a bent-wood hoop (an octagon of eight
pieces) and a string bag that bulges out of the hoop on one side and narrows (two boxes). The bag's faces are a
transparent diamond string mesh (entity_alphatest), so the hoop and the far side of the bag show through it.
Low-poly: 13 cubes, the detail is painted. Deterministic: same code, same files.
"""
import json, os, sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "Kaleidoscope Fishing Voyage [RP]")
NS = "kaleidoscope_fishing"
TEX = "kfv_hand_net"
W = H = 32

# cubes: name, origin, size, uv (box UV); all in the right hand, the handle along +y as the rods'
CUBES = [
    ("grip", [-7, 10, -2], [2, 4, 2], [8, 0]),
    ("handle", [-6.5, 14, -1.5], [1, 8, 1], [0, 0]),
    ("ferrule", [-7, 21, -2], [2, 1, 2], [8, 6]),
    ("hoop_bottom", [-9, 22, -1.5], [6, 1, 1], [16, 0]),
    ("hoop_top", [-9, 31, -1.5], [6, 1, 1], [16, 0]),
    ("hoop_left", [-11, 24, -1.5], [1, 6, 1], [16, 3]),
    ("hoop_right", [-3, 24, -1.5], [1, 6, 1], [16, 3]),
    ("hoop_bl", [-10, 23, -1.5], [1, 1, 1], [24, 3]),
    ("hoop_br", [-4, 23, -1.5], [1, 1, 1], [24, 3]),
    ("hoop_tl", [-10, 30, -1.5], [1, 1, 1], [24, 3]),
    ("hoop_tr", [-4, 30, -1.5], [1, 1, 1], [24, 3]),
    ("bag", [-10, 23, -0.5], [7, 8, 2], [0, 16]),
    ("bag_tip", [-9, 24, 1.5], [5, 5, 2], [18, 22]),
]

ASH, ASH_LT, ASH_DK = (176, 130, 78, 255), (206, 164, 108, 255), (128, 90, 50, 255)
CORD, CORD_DK = (70, 92, 120, 255), (44, 58, 80, 255)
BRASS, BRASS_LT = (200, 160, 70, 255), (240, 210, 120, 255)
HOOP, HOOP_LT, HOOP_DK = (150, 104, 56, 255), (186, 138, 82, 255), (104, 70, 36, 255)
STRING, STRING_DK = (238, 232, 208, 255), (196, 186, 150, 255)


def box_faces(u, v, w, h, d):
    """The rectangles of a box-UV cube at (u, v): {face: (x0, y0, x1, y1)} (exclusive ends)."""
    return {"up": (u + d, v, u + d + w, v + d), "down": (u + d + w, v, u + d + 2 * w, v + d),
            "east": (u, v + d, u + d, v + d + h), "north": (u + d, v + d, u + d + w, v + d + h),
            "west": (u + d + w, v + d, u + 2 * d + w, v + d + h), "south": (u + 2 * d + w, v + d, u + 2 * d + 2 * w, v + d + h)}


def paint():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()

    def fill(rect, fn):
        x0, y0, x1, y1 = rect
        for y in range(y0, y1):
            for x in range(x0, x1):
                px[x, y] = fn(x - x0, y - y0)

    done = set()
    for name, _, size, uv in CUBES:
        if tuple(uv) in done:
            continue
        done.add(tuple(uv))
        w, h, d = size
        for face, rect in box_faces(uv[0], uv[1], w, h, d).items():
            if name == "handle":
                fill(rect, lambda x, y: ASH_DK if y % 5 == 2 else (ASH_LT if x == 0 and face != "east" else ASH))
            elif name == "grip":
                fill(rect, lambda x, y: CORD_DK if y % 2 else CORD)
            elif name == "ferrule":
                fill(rect, lambda x, y: BRASS_LT if (x == 0 and face in ("north", "up")) else BRASS)
            elif name.startswith("hoop"):
                fill(rect, lambda x, y: HOOP_DK if face == "down" else (HOOP_LT if face == "up" or (x + y) % 4 == 0 else HOOP))
            elif name.startswith("bag"):        # a string diamond check: knots every 3 px, the rest open
                fill(rect, lambda x, y: (STRING if (x + y) % 3 == 0 else STRING_DK)
                     if ((x + y) % 3 == 0 or (x - y) % 3 == 0) else (0, 0, 0, 0))
    return img


def geometry():
    skeleton = [
        {"name": "root", "pivot": [0, 0, 0]},
        {"name": "waist", "parent": "root", "pivot": [0, 12, 0]},
        {"name": "body", "parent": "waist", "pivot": [0, 24, 0]},
        {"name": "head", "parent": "body", "pivot": [0, 24, 0]},
        {"name": "leftArm", "parent": "body", "pivot": [5, 22, 0]},
        {"name": "leftItem", "parent": "leftArm", "pivot": [6, 15, 1]},
        {"name": "rightArm", "parent": "body", "pivot": [-5, 22, 0]},
        {"name": "rightItem", "parent": "rightArm", "pivot": [-6, 15, 1]},
        {"name": "net", "parent": "rightItem", "pivot": [-6, 13, -1],
         "cubes": [{"origin": o, "size": s, "uv": uv} for _, o, s, uv in CUBES]},
    ]
    return {"format_version": "1.12.0", "minecraft:geometry": [{
        "description": {"identifier": f"geometry.{NS}.hand_net", "texture_width": W, "texture_height": H,
                        "visible_bounds_width": 4, "visible_bounds_height": 4, "visible_bounds_offset": [0, 1.5, 0]},
        "bones": skeleton}]}


def animations():
    a = f"animation.{NS}.hand_net"
    return {"format_version": "1.8.0", "animations": {
        f"{a}.hold_first_person": {"loop": True, "bones": {"net": {"rotation": [-80.9, -77.1, -79.9]}}},
        f"{a}.hold_third_person": {"loop": True, "bones": {"net": {"rotation": [67.2, 0.0, 0.0]}}},
    }}


def attachable():
    a = f"animation.{NS}.hand_net"
    return {"format_version": "1.10.0", "minecraft:attachable": {"description": {
        "identifier": f"{NS}:hand_net",
        "materials": {"default": "entity_alphatest", "enchanted": "entity_alphatest_glint"},
        "textures": {"default": f"textures/entity/{TEX}", "enchanted": "textures/misc/enchanted_item_glint"},
        "geometry": {"default": f"geometry.{NS}.hand_net"},
        "animations": {"hold_first_person": f"{a}.hold_first_person", "hold_third_person": f"{a}.hold_third_person"},
        "scripts": {"animate": [{"hold_first_person": "c.is_first_person"}, {"hold_third_person": "!c.is_first_person"}]},
        "render_controllers": ["controller.render.item_default"]}}}


def write_json(rel, obj):
    p = os.path.join(RP, rel)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")
    return p


if __name__ == "__main__":
    out = [write_json("models/entity/hand_net.geo.json", geometry()),
           write_json("animations/hand_net.animation.json", animations()),
           write_json("attachables/hand_net.json", attachable())]
    png = os.path.join(RP, "textures", "entity", TEX + ".png")
    paint().save(png, optimize=False, compress_level=9)
    write_json(f"textures/entity/{TEX}.texture_set.json", {"format_version": "1.16.100", "minecraft:texture_set": {
        "color": TEX, "metalness_emissive_roughness": TEX + "_mer", "heightmap": TEX + "_height"}})
    mer = os.path.join(RP, "textures", "entity", TEX + "_mer.png")
    if not os.path.exists(mer):                        # wood and string: not metal, not lit, rough
        Image.new("RGBA", (W, H), (0, 0, 210, 255)).save(mer)
    pbr.refresh(png)
    print("wrote", *out, png, sep="\n  ")
