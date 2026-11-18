"""1.6.0 icons: the Fish Creel's four fill looks and the Hand Net (docs/PLAN_1.6.0.md sections 7.1, 8).

  python tools/gen_basket_net_icons.py

The creel looks are the empty creel icon with fish painted into its mouth (LOOKS, pixel rows); the net is the
Retro Diffusion picture tools/data/item_art/hand_net.png with its mesh drawn in (plan section 17):
  textures/items/kfv_fish_basket_few.png    1-25 % full: one silver tail sticks out of the mouth
  textures/items/kfv_fish_basket_half.png   up to 62 %: a silver and a gold tail, backs showing in the mouth
  textures/items/kfv_fish_basket_most.png   up to full: two tails and a head, the mouth full
  textures/items/kfv_fish_basket_full.png   full: a heap of fish over the rim, one hanging down the side, the sides bulge
  textures/items/kfv_hand_net.png           a wooden handle, a hoop and the mesh
Each gets a texture set whose MER / normal maps come from tools/pbr.py. Deterministic: same input, same pixels.
The empty creel keeps textures/items/kfv_fish_basket.png.
"""
import json, os, sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr  # noqa: E402

STAGES = ["few", "half", "most", "full"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS = os.path.join(ROOT, "Kaleidoscope Fishing Voyage [RP]", "textures", "items")

SILVER, SILVER_LT, SILVER_DK, EYE = (176, 196, 210, 255), (222, 234, 240, 255), (96, 116, 136, 255), (20, 24, 30, 255)
GOLD, GOLD_DK = (222, 162, 51, 255), (156, 94, 22, 255)
WOOD, WOOD_DK, WOOD_LT = (140, 96, 52, 255), (92, 60, 30, 255), (184, 136, 80, 255)
MESH, MESH_DK = (226, 218, 188, 255), (170, 160, 128, 255)


# The creel's mouth is rows 0-2 of the empty creel icon; each look paints fish over it, row by row ("." keeps
# the creel's pixel). S light silver, s silver, d dark silver, e eye, G gold, g dark gold, w white glint.
INK = {"S": (222, 234, 240, 255), "s": (176, 196, 210, 255), "d": (96, 116, 136, 255), "e": (20, 24, 30, 255),
       "G": (244, 196, 84, 255), "g": (176, 108, 32, 255), "w": (255, 255, 255, 255)}
LOOKS = {
    "few": ["..........S.S...",
            "..........dsd...",
            "...........s...."],
    "half": [".....G.G..S.S...",
             ".....gGg..dsd...",
             "....dSSsgGsSs..."],
    "most": ["...S.S....G.G...",
             "...dsdwSSe.gGg..",
             "...SSsssdsGGGg..",
             "....dsdd..gg...."],
    "full": ["S.SwSSSe..GGGGe.",
             "dsdSssssdGwGggg.",
             ".SSSsssdsGGGgg..",
             "Ssdsdsdd.ggg.d..",
             "Sd..............",
             "se..............",
             "d..............."],
}


def creel(stage):
    img = Image.open(os.path.join(ITEMS, "kfv_fish_basket.png")).convert("RGBA")
    px = img.load()
    for y, row in enumerate(LOOKS[STAGES[stage - 1]]):
        for x, ch in enumerate(row[:16]):
            if ch in INK and (y < 3 or px[x, y][3] or stage == 4):   # below the rim only over the creel, but a
                                                                   # full creel has a fish hanging over the side
                px[x, y] = INK[ch]
    if stage == 4:
        for y in range(6, 13):                         # full: the sides bulge one pixel
            if px[14, y][3] and not px[15, y][3]:
                px[15, y] = (110, 64, 26, 255)
    return img


NET_ART = os.path.join(ROOT, "tools", "data", "item_art", "hand_net.png")


def hand_net():
    """The Retro Diffusion net (tools/art/rd_glyphs.py, art.hand_net) with its mesh drawn in: the pale pixels
    inside the hoop become a light / dark string check, so the net reads as a net at 16 px."""
    img = Image.open(NET_ART).convert("RGBA")
    px = img.load()
    for y in range(16):
        for x in range(16):
            r, g, b, a = px[x, y]
            if a and min(r, g, b) > 120 and max(r, g, b) - min(r, g, b) < 40:
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


if __name__ == "__main__":
    out = [save(f"kfv_fish_basket_{s}", creel(i + 1)) for i, s in enumerate(STAGES)]
    out.append(save("kfv_hand_net", hand_net()))
    print("wrote", *out, sep="\n  ")
