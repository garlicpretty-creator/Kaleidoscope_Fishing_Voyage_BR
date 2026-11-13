# 森羅物語：漁歌 / Kaleidoscope Cookery: Fishing Voyage

森羅物語：廚房（基岩版移植）的非官方釣魚與海鮮附屬包。
An unofficial fishing and seafood add-on for the Bedrock Edition port of Kaleidoscope Cookery.

> **需要 / Requires:** 森羅物語：廚房（Kaleidoscope Cookery，基岩版移植，作者 Loyallay）1.6.1 以上。
> 本附屬包不修改森羅物語的任何檔案，只透過它公開的 Script Event API 註冊配方和手帳頁面。

## 內容

- **釣魚**：大魚上鉤時的收線小遊戲，竹、漁歌、熔岩、末影四種釣竿，可自由搭配鉤、線、浮標和餌。
- **漁獲**：淡水、海水、洞穴、下界、末地的魚與海鮮，以及四條傳說魚：河伯鯰、藍鰭皇鮪、冰湖主、熔岩龍鯉。
- **加工**：曬魚架（魚乾、鹹魚、烏魚子）、魚露甕（魚露、蝦醬）、魚案板。
- **料理與宴席**：湯、粥、飯、麵、清蒸、煎烤、炸物、壽司，以及鮪魚大體、生魚片船等宴席。
- **裝飾**：魚缸、漁燈、錨、漁獲木箱、玻璃浮球、漁網牆飾、魚乾串、魚拓等。
- **生物**：鸕鶿、鷺鷥、海鷗、漁販。
- **漁歌手帳**：圖鑑、食譜與潮汐。
- **給其他附屬包的 API**：`kaleidoscope_fishing:register_bait`、`kaleidoscope_fishing:register_catch`，可以註冊新的餌和漁獲。

## Features

- **Fishing**: a reeling minigame for big catches; four rods (bamboo, voyage, lava, ender) with interchangeable hooks, lines, bobbers and baits.
- **Catches**: freshwater, sea, cave, Nether and End fish and seafood, plus four legendary fish.
- **Processing**: drying rack (dried fish, salted fish, karasumi), fish sauce jar (fish sauce, shrimp paste), fish cleaning board.
- **Dishes and feasts**: soups, congee, rice and noodle dishes, steamed and grilled fish, sushi, and feast blocks.
- **Decor**: fish tanks, lanterns, anchor, catch crate, glass floats, net walls, fish prints and more.
- **Mobs**: cormorant, heron, seagull and the fish merchant.
- **Angler's journal**: catch log, recipes and tides.
- **Add-on API**: other add-ons can register baits and catches through script events.

## 安裝 / Installation

1. 先安裝森羅物語：廚房 1.6.1 以上。 / Install Kaleidoscope Cookery 1.6.1 or newer first.
2. 從 [Releases](../../releases) 下載 `.mcaddon`，點兩下匯入 Minecraft。 / Download the `.mcaddon` from Releases and open it.
3. 在世界設定中同時啟用森羅物語與漁歌的行為包、資源包。 / Enable both add-ons' behaviour and resource packs in the world settings.

## 從原始碼打包 / Building from source

需要 Python 3 與 Pillow。 / Requires Python 3 and Pillow.

```
python tools/build.py check   # 檢查資料與 generated.js 是否一致
python tools/build.py pack    # 產生 ../Kaleidoscope_Fishing_Voyage_v<版本>.mcaddon
python tools/validate.py .    # 交叉檢查引用
```

- 遊戲資料表在 `tools/data/*.json`，改完用 `build.py build` 重新產生 `scripts/data/generated.js`。
- `tools/ai2pixel.py` 和 `tools/touchup_*.py` 是製作物品 icon 用的工具。

## 授權 / License

- 美術素材（貼圖、模型、音效、文字）：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
- 腳本（`scripts/`）：BSD 3-Clause

詳見 `LICENSE.txt` 與 `CREDITS.txt`。

本專案與 Kaleidoscope Official Production Team、Loyallay、Mojang Studios、Microsoft 無關，也未獲其背書。
Not affiliated with or endorsed by the Kaleidoscope Official Production Team, Loyallay, Mojang Studios or Microsoft.
