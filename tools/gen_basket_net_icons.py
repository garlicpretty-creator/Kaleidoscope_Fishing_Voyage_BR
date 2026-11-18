"""1.6.0 placeholder icons: the Fish Creel's four fill looks and the Hand Net (docs/PLAN_1.6.0.md sections 7.1, 8).

  python tools/gen_basket_net_icons.py

PLACEHOLDERS, drawn here with Pillow until art is made (plan section 17: the creel looks are the creel icon with
fish tails and heads heaped on it; the net is to be generated and touched up):
  textures/items/kfv_fish_basket_few.png    1-25 % full: one tail sticks out of the mouth
  textures/items/kfv_fish_basket_half.png   up to 62 %: two tails
  textures/items/kfv_fish_basket_most.png   up to full: tails and a head
  textures/items/kfv_fish_basket_full.png   full: a heap of fish over the rim, the sides bulge
  textures/items/kfv_hand_net.png           a wooden handle, a hoop and the mesh
Each gets a texture set whose MER / normal maps come from tools/pbr.py. Deterministic: same input, same pixels.
The empty creel keeps textures/items/kfv_fish_basket.png.
"""
import json, os, sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS = os.path.join(ROOT, "Kaleidoscope Fishing Voyage [RP]", "textures", "items")

SILVER, SILVER_LT, SILVER_DK, EYE = (176, 196, 210, 255), (222, 234, 240, 255), (96, 116, 136, 255), (20, 24, 30, 255)
GOLD, GOLD_DK = (222, 162, 51, 255), (156, 94, 22, 255)
WOOD, WOOD_DK, WOOD_LT = (140, 96, 52, 255), (92, 60, 30, 255), (184, 136, 80, 255)
MESH, MESH_DK = (226, 218, 188, 255), (170, 160, 128, 255)


def tail(px, x, y, c=SILVER, d=SILVER_DK):
    """A forked tail standing up out of the creel, its fork at row y (3 px wide, 3 tall)."""
    for dx, dy, col in ((0, 0, c), (2, 0, c), (0, 1, d), (1, 1, c), (2, 1, d), (1, 2, c)):
        px[x + dx, y + dy] = col


def head(px, x, y):
    """A fish head peeking over the rim, looking left: 4 px wide, 3 tall, with an eye."""
    for dx in range(4):
        for dy in range(3):
            if (dx, dy) in ((0, 0), (0, 2)):
                continue
            px[x + dx, y + dy] = SILVER_LT if dy == 0 else (SILVER if dy == 1 else SILVER_DK)
    px[x + 1, y + 1] = EYE


def creel(stage):
    img = Image.open(os.path.join(ITEMS, "kfv_fish_basket.png")).convert("RGBA")
    px = img.load()
    if stage >= 1:
        tail(px, 9, 0)
    if stage >= 2:
        tail(px, 4, 0, GOLD, GOLD_DK)
    if stage >= 3:
        head(px, 6, 1)
    if stage >= 4:
        tail(px, 12, 1)
        head(px, 1, 2)
        for y in range(6, 13):                         # the sides bulge one pixel
            if px[14, y][3] and not px[15, y][3]:
                px[15, y] = (110, 64, 26, 255)
    return img


def hand_net():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for i in range(8):                                 # the handle, bottom left to the hoop
        x, y = 1 + i, 14 - i
        px[x, y] = WOOD
        if x + 1 < 16:
            px[x + 1, y] = WOOD_DK
    px[1, 14] = WOOD_LT
    ring = [(9, 2), (10, 1), (11, 1), (12, 1), (13, 2), (14, 3), (14, 4), (14, 5), (13, 6), (12, 7), (11, 7), (10, 7),
            (9, 6), (8, 5), (8, 4), (8, 3)]
    for x, y in ring:
        px[x, y] = WOOD_LT
    for y in range(2, 7):                              # the mesh inside the hoop
        for x in range(9, 14):
            if px[x, y][3] == 0:
                px[x, y] = MESH if (x + y) % 2 == 0 else MESH_DK
    return img


def save(name, img):
    png = os.path.join(ITEMS, name + ".png")
    img.save(png, optimize=False, compress_level=9)
    with open(os.path.join(ITEMS, name + ".texture_set.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"format_version": "1.16.100", "minecraft:texture_set": {
            "color": name, "metalness_emissive_roughness": name + "_mer", "normal": name + "_normal"}}, f, indent=2)
        f.write("\n")
    # MER: the creel's own material (pbr keeps the average of an existing map); a new one starts from the base creel
    mer = os.path.join(ITEMS, name + "_mer.png")
    if not os.path.exists(mer):
        Image.open(os.path.join(ITEMS, "kfv_fish_basket_mer.png")).save(mer)
    pbr.refresh(png)
    return png


STAGES = ["few", "half", "most", "full"]

if __name__ == "__main__":
    out = [save(f"kfv_fish_basket_{s}", creel(i + 1)) for i, s in enumerate(STAGES)]
    out.append(save("kfv_hand_net", hand_net()))
    print("wrote", *out, sep="\n  ")
