# 森羅物語：漁歌 — 對外 API（API 1）

其他附加包透過 **Script Event** 和漁歌溝通，命名空間一律是 `kaleidoscope_fishing`。做法和森羅廚房、草本、樂牧相同：`api_ping` → `api_ready`，再依 `capabilities` 決定要用哪些功能。**不要 import 漁歌行為包裡的腳本。**

這份文件對應 **1.5.0（開發中）**。標「1.4.0」的在發行版就能用；標「1.5.0」的要等 1.5.0 發行。1.5.0 還會再增加魚案板、魚缸、魚池飼料的註冊與天象條件，見 [`PLAN_1.5.0.md`](PLAN_1.5.0.md) 第 11 節；加進來時這份文件會同步更新。

Other add-ons talk to Fishing Voyage through script events in the `kaleidoscope_fishing` namespace, the same ping / ready pattern Cookery, Herbal and Ranching use. Never import Fishing Voyage's scripts.

## 通用規則

| 項目 | 規定 |
| --- | --- |
| 傳輸 | `system.sendScriptEvent(id, message)`，`message` 是一行 JSON，長度不超過 2048 字元 |
| 請求必填 | `api: 1`、`source`：你的命名空間（`[a-z0-9_.-]`，不可以是 `kaleidoscope_fishing`） |
| 回覆定址 | 回覆是廣播，帶 `to: <你的 source>`；請只處理 `to` 等於自己的訊息 |
| 對應請求 | 查詢可以帶 `req`（字串或數字，最長 32 字），回覆原樣帶回 |
| 不合格的請求 | JSON 壞掉、`api` 不是 1、`source` 不合規：查詢不回覆；註冊在內容日誌留一行 `[Fishing Voyage] Rejected …` |
| 持久性 | 漁歌不保存任何外部註冊；每次載入世界，收到 `api_ready` 之後要重送一次（重送沒有副作用） |
| 沒裝漁歌 | 不會有任何回覆；你的附加包應該照常運作 |
| 相容性 | 新功能只會**增加** capability 或事件，不會改動既有欄位的意思；有破壞性變更才會升 `api` |

## 握手

| 方向 | 事件 | 內容 |
| --- | --- | --- |
| → 漁歌 | `kaleidoscope_fishing:api_ping` | 任意字串（建議放你的 `source`） |
| ← 漁歌 | `kaleidoscope_fishing:api_ready` | `{"api":1,"source":"kaleidoscope_fishing","version":"1.5.0","capabilities":[...]}` |

漁歌在世界載入後 10 tick 會主動廣播一次 `api_ready`；比較晚載入的附加包自己送 `api_ping` 會得到同樣的回覆。

### capabilities

| 名稱 | 版本 | 意義 |
| --- | --- | --- |
| `bait` | 1.4.0 | 可以註冊餌：`register_bait` |
| `catch` | 1.4.0 | 可以註冊漁獲：`register_catch` |
| `price` | 1.5.0 | 可以註冊漁販的收購價：`register_price` |
| `events` | 1.5.0 | 會廣播 `kaleidoscope_fishing:evt` |
| `state` | 1.5.0 | 可以查詢潮汐、月相、時段：`state_request` |
| `records` | 1.5.0 | 可以查詢玩家的釣魚紀錄：`record_request` |
| `catalog` | 1.5.0 | 可以查詢漁獲與餌的清單：`catalog_request` |
| `board` | 1.5.0 | 自己的魚可以上魚案板：`register_board` |
| `tank` | 1.5.0 | 自己的生物可以進魚缸、熔岩魚缸、魚池：`register_tank` |
| `pond_feed` | 1.5.0 | 可以把物品註冊成魚池飼料：`register_pond_feed` |
| `sky` | 1.5.0 | 有天象（流星雨、極光之夜）：漁獲可以設 `sky`，`state` 回報今晚的天象，`evt` 廣播 `sky` |

用之前先確認清單裡有；1.4.0 的漁歌只有 `bait`、`catch`。

## 註冊

三種註冊的共同規則：

- 只能註冊**自己命名空間**的物品，物品必須存在。
- 一則訊息 1–32 筆；每個來源每種最多 64 筆。
- 同一個 `id` 先註冊的來源保有它；同一個來源重送是更新。
- 沒有回覆事件。被拒絕的項目各在內容日誌留一行，說明原因。

### 餌 — `register_bait`（1.4.0）

```json
{"api":1,"source":"my_pack","baits":[{"id":"my_pack:corn_bait","biteFactor":0.7}]}
```

`biteFactor` 是等待咬鉤時間的倍率，0.5–1，越小越快（漁歌自己最好的餌是 0.5）；不寫是 0.75。

### 漁獲 — `register_catch`（1.4.0）

```json
{"api":1,"source":"my_pack","catches":[{"id":"my_pack:glow_eel","w":6,"waters":["river"],"size":[30,80],"needBait":["my_pack:corn_bait"]}]}
```

| 欄位 | 意思 | 限制 |
| --- | --- | --- |
| `id` | 釣到的物品 | 必填 |
| `w` | 出現權重 | 必填，整數 1–20（漁歌的稀有魚不超過 12，常見魚是 30） |
| `waters` | 出現的水域 | 見下方清單 |
| `needs` | 另外必須符合的水域 | 同上 |
| `size` | `[最小, 最大]` 公分 | 整數 1–500 |
| `fight` | 掙扎強度 | 整數 0–3 |
| `tier`、`tier_bonus` | 需要的釣竿等級；高級釣竿的加成 | 1–3；0–3 |
| `min_depth`、`max_depth` | 水深 | 整數 0–64 |
| `time`、`off` | 只在 `"day"` 或 `"night"`；非該時段的倍率 | `off` 0–1 |
| `slots` | 時段 | `dawn`、`day`、`dusk`、`night` |
| `moon`、`moon_boost` | `"full"`，或月相編號陣列（0 滿月 … 4 新月）加倍率 | `moon_boost` 1–2 |
| `tide` | `{"high":倍率,"low":倍率}` | 各 0–3 |
| `rain`、`cold`、`dawn_dusk`、`school` | 下雨、寒冷、晨昏、魚群的倍率 | 0–3 |
| `boat` | 在船上釣的倍率（1.5.0） | 0–3 |
| `bait` | 特定餌的倍率 `{"<餌>":1.5}` | 0–3；餌必須是內建或已註冊的 |
| `needBait` | 只有用這些餌才上鉤 | 同上 |
| `sky` | 只在這種天象的夜晚上鉤（1.5.0，要有 `sky` capability） | `"meteor"`（流星雨）或 `"aurora"`（極光之夜；只在寒冷的地方算數） |

水域：`river`、`lake`、`swamp`、`mangrove`、`estuary`、`beach`、`ocean`、`warm_ocean`、`cold_ocean`、`deep_ocean`、`cave`、`ice`、`lava`、`end_pond`、`void`；1.5.0 加上 `mushroom`（蘑菇島）、`cherry`（櫻花樹林）、`deep_dark`（深暗之域，和洞穴一樣只出自己的漁獲）。

不接受：`req`（傳說魚條件）。1.4.0 的漁歌收到 `sky` 會拒絕整筆漁獲，先確認 `capabilities` 有 `sky`。

### 漁販收購價 — `register_price`（1.5.0）

```json
{"api":1,"source":"my_pack","prices":[{"id":"my_pack:glow_eel","price":0.5}]}
```

- `price`：中型一條值幾顆綠寶石，0.05–3（漁歌最貴的鮟鱇魚、熔岩錦鯉是 3）。
- 尺寸的倍率和漁歌的魚一樣：小型 ×0.6、大型 ×1.6、破紀錄 ×2.5。沒有尺寸資料的物品照中型算。
- 和漁歌的魚共用漁販的錢袋。
- 外部的魚不會成為漁販當天想收的魚。
- 不能替 `minecraft:` 或漁歌自己的物品訂價。

## 事件廣播 — `events`（1.5.0）

`kaleidoscope_fishing:evt`，一行 JSON：`{"v":1,"t":"<事件>","p":"<player.id>", ...}`。格式和草本的 `kaleidoscope_herbal:evt` 相同。

| `t` | 其他欄位 | 時機 |
| --- | --- | --- |
| `caught` | `id`、`via`、`size`?、`cls`、`legend`、`first`、`record` | 一條漁獲上岸 |
| `cleaned` | `id` | 魚案板上一條魚切完最後一刀 |
| `sold` | `id`、`n`、`paid` | 把魚賣給漁販；`n` 是他收下的數量，`paid` 是這次拿到的綠寶石 |
| `order_filled` | `id`、`n` | 玩家交齊了漁販的訂單（`n` 條 `id`），剛拿到獎勵 |
| `tide` | `state`：`high` 或 `low` | 潮汐轉換。世界事件，沒有 `p` |
| `sky` | `kind`（`meteor` 或 `aurora`）、`phase`（黃昏 `start`、清晨 `end`）、`dim` | 天象開始與結束。世界事件，沒有 `p`；格式和 A Witch Way 的 `aww:evt` `sky` 相同，草本那類已經會聽 AWW 天象的包可以共用處理 |

`caught` 的欄位：

| 欄位 | 內容 |
| --- | --- |
| `id` | 漁獲的物品 ID（也包含其他附加包註冊的漁獲） |
| `via` | `rod`（釣竿）或 `tip_up`（冰洞的插旗浮標） |
| `size` | 公分；沒有尺寸的漁獲（蝦、蟹等）沒有這個欄位 |
| `cls` | 0 沒有尺寸、1 小型、2 中型、3 大型 |
| `legend` | 是不是傳說魚 |
| `first` | 這位玩家第一次釣到這種 |
| `record` | 打破了這位玩家自己的紀錄 |

蝦籠收成、鸕鶿抓魚、挖蛤不算 `caught`。

### 魚案板 — `register_board`（1.5.0）

```json
{"api":1,"source":"my_pack","boards":[{"id":"my_pack:glow_trout","like":"kaleidoscope_fishing:carp","cuts":[
  {"act":"scale","out":[["kaleidoscope_fishing:fish_scales",1]]},
  {"act":"gut","out":[["kaleidoscope_fishing:fish_offal",1],["my_pack:glow_gland",1,0.25]]},
  {"act":"fillet","out":[["my_pack:glow_fillet",3,1,"sized"],["kaleidoscope_fishing:fish_bones",1]]}]}]}
```

- 案板上的模型沒辦法由別的包提供，所以用 `like` 指定長得最像的內建漁獲（必須是能上案板的），案板就顯示它的模型；`cuts` 的刀數要和 `like` 一樣。
- `act`：`scale`、`gut`、`fillet`、`head`、`shell`、`devein`、`open`、`legs`、`tentacle`、`bone`（決定音效與粒子）。
- `out`：每刀 1–4 種產物，`[物品, 數量 1–8, 機率 0–1（省略是 1）, "sized"]`。`"sized"` 的產物大型 +1、小型 −1，整條魚最多一個。
- 產物只能是自己命名空間的物品，或漁歌的通用產物：魚鱗、魚雜、魚骨、魚卵、白肉魚片、蝦頭、蝦殼、蝦仁、蟹殼、蟹肉、蟹腳、海蜇皮。
- 外部的魚不能取「剖好的魚」。案板記得是哪一個物品；你的包這次還沒註冊時，案板上的魚切不動、也拿不回來，註冊之後照常。

### 魚缸與魚池 — `register_tank`（1.5.0）

```json
{"api":1,"source":"my_pack","tanks":[{"id":"my_pack:glow_trout","like":"kaleidoscope_fishing:carp","scale":1.0,"tank":"water","pond":"fresh","breed":true}]}
```

| 欄位 | 意思 | 限制 |
| --- | --- | --- |
| `like` | 顯示哪一種內建生物的模型與游法 | 必須是能進魚缸的內建生物 |
| `scale` | 顯示大小的倍率 | 0.5–1.5，省略是 1 |
| `tank` | 進哪一種缸 | `water`（預設）、`lava`、`both` |
| `pond` | 能不能進魚池 | `none`（預設）、`fresh`、`salt`（海水池）、`both` |
| `breed` | 在魚池能不能繁殖 | 預設 `false` |

- 取回時是原本的物品，尺寸、★、取名都保留。魚缸記得物品和 `like`：你的包還沒註冊時照樣顯示；物品不存在（包被移除）時取不出來、留在缸裡，包裝回來就能取。
- 魚池的容量、餵食、成長、養殖標記和內建的魚相同。

### 魚池飼料 — `register_pond_feed`（1.5.0）

```json
{"api":1,"source":"my_pack","feeds":[{"id":"my_pack:corn_mash","meals":2}]}
```

- `meals`：一個物品給幾餐，整數 1–4（漁歌的魚粉是 4、魚粉餌 2、小魚乾與蚯蚓 1）。省略是 1。
- 只能註冊自己命名空間、確實存在的物品；漁歌自己的飼料不能改。
- 餵食台最多存 64 餐；每天清晨每條魚吃 1 餐。

## 查詢

### 現在的漁況 — `state_request`（1.5.0）

請求：`{"api":1,"source":"my_pack","req":"1"}`

回覆 `kaleidoscope_fishing:state`：

```json
{"api":1,"to":"my_pack","req":"1","ok":true,"tide":"high","moon":0,"slot":"dawn","day":12,"sky":"none"}
```

- `tide`：`high` 或 `low`。
- `moon`：0 滿月 … 4 新月 … 7。
- `slot`：`dawn`、`day`、`dusk`、`night`。
- `day`：世界的天數。
- `sky`：今晚的天象，`meteor`、`aurora` 或 `none`。只在黃昏到隔天清晨之間有值；極光不分地點都回報 `aurora`，是否在寒冷的地方由你判斷。

### 玩家的釣魚紀錄 — `record_request`（1.5.0）

查一種魚：`{"api":1,"source":"my_pack","req":"2","p":"<player.id>","id":"kaleidoscope_fishing:carp"}`

回覆 `kaleidoscope_fishing:record`：`{"api":1,"to":"my_pack","req":"2","p":"...","ok":true,"id":"kaleidoscope_fishing:carp","n":7,"best":64}`

- `n`：釣到幾次（0 表示沒釣過）。
- `best`：最大的尺寸，公分；沒有尺寸的漁獲或沒釣過就沒有這個欄位。

不帶 `id` 就查總覽：`{"ok":true,"caught":23,"total":52,"legends":1,"legendTotal":4}`。

`p` 不是線上玩家時回 `{"ok":false,"code":"NO_PLAYER"}`。

### 清單 — `catalog_request`（1.5.0）

請求：`{"api":1,"source":"my_pack","req":"3","kind":"catches"}`

回覆 `kaleidoscope_fishing:catalog`，可能分成多封；收齊 `parts` 封後依 `index` 合併 `items`：

```json
{"api":1,"to":"my_pack","req":"3","kind":"catches","ok":true,"index":0,"parts":4,"items":[...]}
```

| `kind` | `items` 每筆 |
| --- | --- |
| `catches` | `{id, waters, group?, size?, legend?, source?}`：`group` 是手帳的分頁；其他附加包註冊的漁獲帶註冊者的 `source` |
| `baits` | `{id, biteFactor, source?}` |

未知的 `kind` 回 `{"ok":false,"code":"UNKNOWN_KIND","kinds":["catches","baits"]}`。

## 標籤與指令

- **刀**：任何帶 `kaleidoscope_cookery:kitchen_knife` 標籤的物品都能在魚案板下刀，用它殺魷魚也會掉魷魚。
- **小遊戲開關**（管理員指令，不是給附加包用的）：`/scriptevent kaleidoscope_fishing:minigame on | off | status | charset block | charset ascii`

## 漁歌會主動找的附加包

漁歌載入一秒後會送出下面三個 `api_ping`。有回覆才會動作；沒裝的話什麼都不會發生，也不會在日誌留訊息。

| 附加包 | 漁歌送出 | 效果 |
| --- | --- | --- |
| 森羅物語：草本 `kaleidoscope_herbal` | `heat_register`（需要 `external_heat`） | 39 道漁歌料理有寒熱值：螃蟹、生魚片、海苔偏寒；蝦、鰻魚、炸物、辣菜、火鍋、下界料理偏熱 |
| 森羅物語：樂牧 `kaleidoscope_ranching` | `register_feed`（需要 `register_feed`） | 魚粉（混合飼料，2 份）、魚乾（穀物類，1 份）可以放進飼槽；蝦米是補鈣飼料（需要 `feed_1_1`） |
| 森羅物語：豐收 `kaleidoscope_harvest` | `api_ping`；新版豐收回 `api_ready`，1.0.0 不回應，所以也看它的物品在不在 | 有豐收時，7 道用豐收作物的漁歌料理才會登記到森羅廚房：薑絲蛤蜊湯、蔥燒魚、蒜蓉蒸蝦、檸檬魚、黃瓜拌海蜇、花生小魚乾、白蘿蔔魚丸湯 |

漁歌另外會聽：

| 事件 | 來源 | 漁歌的反應 |
| --- | --- | --- |
| `kaleidoscope_cookery:api_ready` / `guidebook_ready` | 森羅廚房 | 註冊配方與湯底；發布圖鑑的漁歌分頁 |
| `aww:evt` 的 `autofed` | A Witch Way | 背包自動餵食漁歌料理時，照樣給料理的效果 |

### 姊妹包註冊進漁歌的東西

| 附加包 | 用的事件 | 內容 |
| --- | --- | --- |
| 樂牧 | `register_bait` | 雞胗、豬肝（0.75）、豬／牛／羊絞肉（0.8）、乳酪片（0.85） |
| 豐收 | `register_bait`、`register_pond_feed` | 玉米種子（0.7）、大豆（0.8）當餌；豆渣（2 餐）、玉米種子（1 餐）當魚池飼料 |
| 草本 | `register_pond_feed` | 苦藥渣、焦糊藥渣，各 1 餐 |

草本 1.1.0 之後也會聽漁歌 `evt` 的 `sky`：流星雨、極光之夜草本作物生長兩倍。

## 給草本、樂牧、豐收的對照

| 你想做的事 | 用什麼 |
| --- | --- |
| 讓自己的物品能當魚餌 | `register_bait`（樂牧已經在用） |
| 加自己的魚 | `register_catch`，可以搭配 `needBait` 限定要用自己的餌 |
| 讓漁販收自己的魚 | `register_price` |
| 玩家釣到魚、釣到傳說魚、破紀錄時做反應 | 聽 `evt` 的 `caught`，看 `legend`、`first`、`record` |
| 依潮汐或月相改變自己的內容 | `state_request`，並聽 `evt` 的 `tide` |
| 天象之夜給自己的東西加成（作物、藥草、動物） | 聽 `evt` 的 `sky`（`start` 到 `end` 之間），或在 `state` 看 `sky` |
| 任務或成就要知道玩家釣過什麼 | `record_request` |
| 列出漁歌有哪些魚（做手冊頁、掉落表） | `catalog_request` |

### 最小範例

```js
import { system } from "@minecraft/server";

const ME = "my_pack";
let fishing;                                   // 漁歌的 api_ready；沒裝漁歌就一直是 undefined

system.afterEvents.scriptEventReceive.subscribe(ev => {
  let m;
  try { m = JSON.parse(ev.message); } catch { return; }
  if (ev.id === "kaleidoscope_fishing:api_ready" && m.api === 1) {
    fishing = m;
    if (m.capabilities.includes("bait"))
      system.sendScriptEvent("kaleidoscope_fishing:register_bait",
        JSON.stringify({ api: 1, source: ME, baits: [{ id: `${ME}:corn_bait`, biteFactor: 0.7 }] }));
  } else if (ev.id === "kaleidoscope_fishing:evt" && m.v === 1) {
    if (m.t === "caught" && m.legend) { /* 玩家 m.p 釣到傳說魚 m.id */ }
    if (m.t === "tide") { /* 潮汐變成 m.state */ }
  } else if (ev.id === "kaleidoscope_fishing:state" && m.to === ME) {
    /* m.tide, m.moon, m.slot */
  }
}, { namespaces: ["kaleidoscope_fishing"] });

system.runTimeout(() => system.sendScriptEvent("kaleidoscope_fishing:api_ping", ME), 20);
```
## 和 burnt-tea-dev 的包握手（下單了、煙火）

這兩個包沒有自己的 `api_ping`，但收註冊。我們載入 20 tick 後主動送，沒裝就沒人聽、什麼都不發生。程式在 `api/burntTea.js`，要送的清單 `data/burntTeaCatalog.js` 由 `tools/gen_burnt_tea.mjs` 從本包的物品、燻爐配方與 zh_TW 語言檔產生（不要手改；測試會檢查它是否過期）。

| 對方 | 送出 | 效果 |
| --- | --- | --- |
| 下單了 Order To Cook | `ordertocook:food_catalog_v1`（收到 `food_catalog_request_v1` 時重送） | 料理用中文名上餐廳菜單；杯裝、瓶裝的算飲品。生食材、漁獲、食材分類、飢餓值不到 3 的不上菜單 |
| 同上 | `ordertocook:smoking_recipes_v1`（回應 `request_smoking_recipes_v1`） | 本包的燻爐配方可以在下單了的爐子上做；目錄名用 `main`，會取代下單了發行時替我們內建的那份 |
| 煙火 Grilling | `kaleidoscope_grilling:register_smoking`，一組一則 | 神秘烤串上的生肉、生魚烤好後變成熟的那一樣，和 Java 版煙火查燻製配方一樣 |

當兩個倉庫放在本倉庫旁邊時，測試會直接用下單了與煙火自己的程式碼驗證我們的訊息都被接受。
