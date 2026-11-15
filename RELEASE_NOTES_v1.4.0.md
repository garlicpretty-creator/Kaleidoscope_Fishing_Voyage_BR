## 森羅物語：漁歌 1.4.0 更新公告（1.3 → 1.4.0）

**需要**：森羅物語：廚房（Kaleidoscope Cookery 基岩版移植）1.6.1 以上（開發時用 1.6.6 測試）。
**不再需要**：國味（中華美食）。

### 安裝
1. 先安裝森羅物語：廚房 1.6.1 以上。
2. 下載 `Kaleidoscope_Fishing_Voyage_v1.4.0.mcaddon`，點兩下匯入 Minecraft。
3. 在世界設定裡，同時啟用森羅物語和漁歌的行為包、資源包。
4. 從 1.3 升級：先到「設定 → 儲存」刪掉舊的漁歌，再匯入新版。**建議先備份世界。**

---

### 🎣 釣魚玩法
- **收線小遊戲**：大魚上鉤後要按住使用鍵，把方框對準魚，「進度」條滿了才拉得上來。
  - 傳說魚最難。
  - 方框的大小和難度受釣竿、魚線、浮標影響。
  - 不想玩小遊戲：輸入 `/scriptevent kaleidoscope_fishing:minigame off`，就會換回原本的拉扯玩法。
- **新水域**：紅樹林、河口、洞穴。洞穴水域有專屬的洞穴漁獲。
- **天氣與月相**：雷雨天會有魚群，而且留得比較久。月相會帶來特定魚汛，例如烏魚汛。河上的魚群旁會有鷺鷥。
- **新的餌和釣具**：
  - 假餌鉤：不用掛餌也能釣；
  - 羽毛浮標：容易釣到淺水的魚；
  - 活蝦：從蝦籠取得；
  - 蚯蚓：雨天在草地挖到。

### 🐟 新魚與傳說魚
- **10 種新魚**：烏魚、鱸魚、泥鰍、彈塗魚、鱧魚、飛魚、龍蝦、帝王蟹、洞穴盲魚、洞穴螯蝦。目前共 52 種漁獲。
- **4 條傳說魚**：河伯鯰、藍鰭皇鮪、冰湖主、熔岩龍鯉。
  - 每條都有自己的出現條件，第一次釣到會得到紀念品。
  - 傳說魚上鉤時浮標會變成金色。

### 🍲 加工與料理
- **魚露甕**：先放鹽，再放 4 條小魚做成魚露，或放 4 份蝦米做成蝦醬。
  - 能用的魚：小黃魚、公魚、香魚、秋刀魚、鯖魚、泥鰍、生鱈魚。
  - 封蓋發酵約 3 分鐘後，用玻璃瓶取魚露、用碗舀蝦醬。
  - 甕裡放了什麼（鹽、魚、魚露、蝦醬）從外面看得出來。
- **烏魚子**：烏魚上魚案板取出烏魚卵，鹽漬後放上曬魚架曬三天就是烏魚子。
- **飛魚一夜干**：飛魚放上曬魚架曬一天。
- **魚案板**：目前共 41 種魚可以放上去切。每一刀外觀都會變：刮鱗、剖腹，最後片成魚片。
- **新宴席**：
  - 藍鰭皇鮪大體；
  - 冰湖主漁獲盤；
  - 龍鯉石板燒：2 格，石板會發光；
  - 河伯鯰砂鍋：開蓋的砂鍋。

  目前共 16 種可放置的宴席，名稱下方會標示紫色的「可放置食物」。
- 漁歌料理都已登錄到森羅廚房的鍋具和砧板，共 84 道配方，也都收錄在森羅廚房圖鑑的漁歌分頁。

### 🏠 工作站與裝飾
- **工作站被拆掉時會掉出內容物**：曬魚架、魚露甕、魚案板、蝦籠、冰洞不論是被玩家敲掉、被炸掉、被活塞推走或被指令移除，裡面的東西都會掉出來。
- **工作站改用世界時間計時**：蝦籠、魚露甕離開載入範圍後回來，會自動補上這段時間的進度。
- **冰洞**：魚上鉤後會一直等你來收，鈴鐺每 30 秒響一次。
- **魚缸**：
  - 可以放進更多種類，包括蝦、紫珀蝦（在缸底爬行）；
  - 魚拓也支援更多魚種。
- **新裝飾**：錨、漁獲木箱、玻璃浮球、漁網牆飾（可放在水裡）、魚乾串。
- **碼頭**：會在海岸、河岸自然生成，`/locate` 找不到。

### 🐦 生物
- **新生物鷺鷥**：出現在河邊、沼澤、海灘，人靠近會飛走。
- **鸕鶿**：
  - 所有模組魚都能拿來馴服（傳說魚除外）；
  - 馴服後會潛水幫主人抓魚，戴上頸環才會把魚交給你；
  - 有晾翅膀、理毛等待機動作。
- **漁販**：
  - 改成村民體型；
  - 每天收購 2 種魚，價格加倍；
  - 頭上會顯示當天想要的魚。
- 海鷗、鷺鷥、鸕鶿、漁販的走路和待機動作都更自然。

### 📖 介面與其他
- **漁歌手帳**：依水域分頁，還沒釣到的魚顯示為黑色剪影。
- **物品 icon**：全部重新繪製；食物 icon 的輪廓更清楚、更有立體感。
- **光影**：支援 Vibrant Visuals / RTX 的材質，包括法線貼圖與發光。
- **創造模式物品欄**：照森羅廚房的分類重新分組。
- **繁中、簡中**：圖鑑裡不再出現沒翻譯的英文。
- **給附屬包作者**：新增 `register_bait`、`register_catch` API，可以註冊自己的餌和漁獲。

### 🔧 修正
- 假餌鉤：拋竿後把餌收起來，現在會由假餌接手。
- 傳說魚跑掉後，浮標不再一直維持金色。
- 小遊戲進行中走太遠，線會斷，也會扣釣竿耐久。
- 挖蛤的冒泡點不會超過上限。
- 漁販加倍收購的魚會跟著日期更換。
- 用絲綢之觸挖紫菜礁、牡蠣床，只會掉 1 個方塊。
- 碼頭和漁屋等結構上不再有看不見的方塊；碼頭的生成機率降低。
- 鸕鶿不會在潛水後往天上飄；多人遊戲時不會認錯主人。

### ⚠️ 注意
- **玩過 1.5～1.6 測試版的世界**，請不要直接換成 1.4.0。1.4.0 的版號比較低，測試版裡有些內容沒有收錄，舊世界裡的那些物品會變成未知物品。請用新世界。

---

## Kaleidoscope Cookery: Fishing Voyage 1.4.0 (1.3 → 1.4.0)

**Requires** Kaleidoscope Cookery (Bedrock port) 1.6.1 or newer (tested with 1.6.6). Kaleidoscope Chinese Food is no longer needed. Remove the old Fishing Voyage before importing the new `.mcaddon`, and back up your world first.

**Highlights**
- A reeling minigame for big catches. Turn it off with `/scriptevent kaleidoscope_fishing:minigame off`.
- Three new waters: mangrove, estuary and cave. Storm schools, moon-phase runs, new baits and tackle.
- Ten new species, for 52 catches in all.
- Four legendary fish: River Lord Catfish, Emperor Tuna, Frostlake Char and Lava Dragon Koi.
- Processing:
  - the Fish Sauce Jar, for fish sauce and shrimp paste;
  - karasumi;
  - dried flying fish;
  - 41 fish on the Fish Cleaning Board.
- 16 placeable feasts, including two new legendary ones: the Dragon Koi Hot Stone Grill and the River Lord Catfish Clay Pot.
- 84 recipes in Cookery's cooking stations and guidebook.
- Stations drop their contents however they are removed, and run on world time.
- New decor, the fishing pier, and shrimp in fish tanks.
- Creatures: the heron is new. Cormorants dive and fish for you, and any mod fish tames them. The fish merchant now has a villager build.
- Livelier animations.
- Redrawn icons, Vibrant Visuals/RTX materials, Cookery-style creative groups, and full Chinese guidebook names.
- `register_bait` / `register_catch` API for other add-ons.

**Note:** worlds that ran the 1.5–1.6 test builds should not be loaded with 1.4.0. Its version is lower and some test-build content is not included. Use a new world.
