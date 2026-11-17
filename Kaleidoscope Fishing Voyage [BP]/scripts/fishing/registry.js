// ## Kaleidoscope script role: external bait / catch registration (v1.6.2, Senluo plan 第三期 ★3, F4-A).
// Other packs (first the 森羅物語：魔女手札 0.5.0 arcane baits and element fish) add baits and catches to this
// add-on through script events, in the same envelope style as Cookery's register_* API (kc/bridge.js):
//
//   kaleidoscope_fishing:api_ready      we send it 10 ticks after load and again in answer to api_ping:
//                                       {"api":1,"source":"kaleidoscope_fishing","version":"1.6.2","capabilities":["bait","catch"]}
//   kaleidoscope_fishing:api_ping       anyone -> us; message is the sender's namespace (or {"source"})
//   kaleidoscope_fishing:register_bait  {"api":1,"source":"<ns>","baits":[{"id":"<item>","biteFactor":0.7}, ...]}
//   kaleidoscope_fishing:register_catch {"api":1,"source":"<ns>","catches":[{"id":"<item>","w":6,"waters":[...],
//                                        "size":[20,60],"fight":1,"needBait":["<bait item>"],"bait":{"<bait>":1.5},
//                                        "time","off","slots","moon","moon_boost","tide","min_depth","max_depth",
//                                        "tier","tier_bonus","rain","cold","dawn_dusk","school","needs"}, ...]}
//
// Chunking: a script event message holds at most 2048 characters, so a sender splits a long list over several
// messages; every message stands on its own (replace by source + id, so re-sending is safe). Like Cookery, we keep
// registrations only for the current world session: senders register again on every world load, after api_ready.
// Rules (F4-A, balance): ids must be the sender's own (never kaleidoscope_fishing:*, never a built-in catch or
// bait, never a legend); the item must exist (ItemTypes.get) so a missing pack never lands an impossible item;
// `req` (legend conditions) is not accepted; w is 1..20 (built-in rare fish are <= 12, common 30); a bait's
// biteFactor is 0.5..1 (our best bait is 0.5). An entry with needBait bites only on one of those baits, which is
// how element fish stay behind arcane bait. Bad entries are dropped with one console warning each.
//
// 1.5.0:
//   kaleidoscope_fishing:register_price {"api":1,"source":"<ns>","prices":[{"id":"<item>","price":0.5}, ...]}
//                                       the Fish Merchant buys the item: `price` is emeralds for one medium fish
//                                       (0.05..3; our dearest fish are 3). Size and record factors apply as for
//                                       our own fish. An outside fish is never one of the day's wanted fish.
//   kaleidoscope_fishing:register_pond_feed {"api":1,"source":"<ns>","feeds":[{"id":"<item>","meals":1}, ...]}
//                                       the item feeds the fish in a pond (blocks/pond.js): `meals` 1..4 (our Fish
//                                       Meal is 4). Our own feeds stay as they are.
// api_ready also lists what api/host.js offers: "events", "state", "records", "catalog" (see that file).
import { system, ItemTypes } from "@minecraft/server";
import { ADDON_VERSION, CATCHES, LEGENDS, POND_FEEDS } from "../data/generated.js";

export const SOURCE = "kaleidoscope_fishing";
export const API = 1;
export const EV = {
  ready: `${SOURCE}:api_ready`,
  ping: `${SOURCE}:api_ping`,
  bait: `${SOURCE}:register_bait`,
  catch: `${SOURCE}:register_catch`,
  price: `${SOURCE}:register_price`,
  pond_feed: `${SOURCE}:register_pond_feed`,
};
export const CAPABILITIES = ["bait", "catch", "price", "events", "state", "records", "catalog", "sky", "pond_feed"];
const SKIES = ["meteor", "aurora"];          // world/sky.js (not imported: it imports the host, which imports this)
export const LIMITS = Object.freeze({ w: [1, 20], biteFactor: [0.5, 1], size: [1, 500], fight: [0, 3], depth: [0, 64],
  factor: [0, 3], moonBoost: [1, 2], price: [0.05, 3], meals: [1, 4], perSource: 64 });

// the vocabulary the built-in table uses; an external entry may only use these waters / needs / slots
const ID_RE = /^[a-z0-9_.-]+:[a-z0-9_./-]+$/;
const BUILTIN = new Set(CATCHES.map(c => c.id));
const LEGEND = new Set(LEGENDS ?? []);
const WATERS = new Set(CATCHES.flatMap(c => [...(c.waters ?? []), ...(c.needs ?? [])]));
const SLOTS = ["dawn", "day", "dusk", "night"];

/** registered catches: id -> entry (with .source); registered baits: id -> {biteFactor, source};
 *  registered prices: id -> {price, source} */
const catches = new Map();
const baits = new Map();
const prices = new Map();
const feeds = new Map();                     // 1.5.0: id -> {meals, source}
let itemExists = id => { try { return !!ItemTypes.get(id); } catch { return false; } };
let builtinBait = () => false;     // set by loot.js (avoids a circular import)
let onChange = () => {};           // loot.js rebuilds its lookups

/** Live views for loot.js. */
export const externalCatches = () => [...catches.values()];
export const externalBait = id => baits.get(id);
export const externalBaits = () => [...baits.values()];
/** What the Fish Merchant pays for an outside fish (emeralds for a medium one), or undefined. */
export const externalPrice = id => prices.get(id)?.price;
/** loot.js wires these at load (builtin bait test, change callback). */
export function _wire(isBuiltinBait, changed) { builtinBait = isBuiltinBait; onChange = changed; }
/** Tests only. */
export function _setItemExists(fn) { itemExists = fn; }
export function _clearRegistry() { catches.clear(); baits.clear(); prices.clear(); feeds.clear(); onChange(); }

function warn(what) { try { console.warn(`[Fishing Voyage] Rejected ${what}`); } catch {} }
const num = (v, [lo, hi]) => typeof v === "number" && Number.isFinite(v) && v >= lo && v <= hi;
const int = (v, r) => num(v, r) && Number.isInteger(v);
const strs = (v, ok) => Array.isArray(v) && v.length > 0 && v.length <= 16 && v.every(x => typeof x === "string" && ok(x));

function parse(message) {
  let m;
  try { m = JSON.parse(String(message ?? "")); } catch { return undefined; }
  if (!m || typeof m !== "object" || Number(m.api) !== API) return undefined;
  if (typeof m.source !== "string" || !/^[a-z0-9_.-]{1,48}$/.test(m.source) || m.source === SOURCE) return undefined;
  return m;
}

/** A catch entry as loot.js wants it, or a reason string. */
function catchEntry(e, source) {
  if (!e || typeof e !== "object" || typeof e.id !== "string" || !ID_RE.test(e.id) || e.id.length > 96) return "bad id";
  if (e.id.startsWith(`${SOURCE}:`) || BUILTIN.has(e.id) || LEGEND.has(e.id)) return `${e.id}: built-in or legend ids are closed`;
  const have = catches.get(e.id);
  if (have && have.source !== source) return `${e.id}: already registered by ${have.source}`;
  if ("req" in e) return `${e.id}: legend conditions (req) are not open to other packs`;
  if (!itemExists(e.id)) return `${e.id}: no such item`;
  if (!int(e.w, LIMITS.w)) return `${e.id}: w must be an integer ${LIMITS.w[0]}..${LIMITS.w[1]}`;
  const out = { id: e.id, w: e.w, source };
  if (e.waters !== undefined) { if (!strs(e.waters, w => WATERS.has(w))) return `${e.id}: unknown waters`; out.waters = [...e.waters]; }
  if (e.needs !== undefined) { if (!strs(e.needs, w => WATERS.has(w))) return `${e.id}: unknown needs`; out.needs = [...e.needs]; }
  if (e.size !== undefined) {
    if (!Array.isArray(e.size) || e.size.length !== 2 || !int(e.size[0], LIMITS.size) || !int(e.size[1], LIMITS.size) || e.size[0] >= e.size[1]) return `${e.id}: size must be [lo, hi] cm`;
    out.size = [e.size[0], e.size[1]];
  }
  if (e.fight !== undefined) { if (!int(e.fight, LIMITS.fight)) return `${e.id}: fight 0..3`; out.fight = e.fight; }
  if (e.tier !== undefined) { if (!int(e.tier, [1, 3])) return `${e.id}: tier 1..3`; out.tier = e.tier; }
  for (const k of ["min_depth", "max_depth"]) if (e[k] !== undefined) { if (!int(e[k], LIMITS.depth)) return `${e.id}: ${k}`; out[k] = e[k]; }
  if (e.time !== undefined) { if (e.time !== "day" && e.time !== "night") return `${e.id}: time`; out.time = e.time; }
  if (e.off !== undefined) { if (!num(e.off, [0, 1])) return `${e.id}: off 0..1`; out.off = e.off; }
  if (e.slots !== undefined) { if (!strs(e.slots, s => SLOTS.includes(s))) return `${e.id}: slots`; out.slots = [...e.slots]; }
  if (e.moon !== undefined) {
    if (e.moon === "full") out.moon = "full";
    else if (Array.isArray(e.moon) && e.moon.length && e.moon.every(p => int(p, [0, 7]))) { out.moon = [...e.moon]; if (!num(e.moon_boost, LIMITS.moonBoost)) return `${e.id}: moon_boost 1..2`; out.moon_boost = e.moon_boost; }
    else return `${e.id}: moon`;
  }
  if (e.tide !== undefined) {
    if (!e.tide || typeof e.tide !== "object") return `${e.id}: tide`;
    out.tide = {};
    for (const k of ["high", "low"]) if (e.tide[k] !== undefined) { if (!num(e.tide[k], LIMITS.factor)) return `${e.id}: tide.${k}`; out.tide[k] = e.tide[k]; }
  }
  for (const k of ["rain", "cold", "dawn_dusk", "school", "tier_bonus"]) if (e[k] !== undefined) { if (!num(e[k], LIMITS.factor)) return `${e.id}: ${k} 0..3`; out[k] = e[k]; }
  if (e.sky !== undefined) { if (!SKIES.includes(e.sky)) return `${e.id}: sky must be "meteor" or "aurora"`; out.sky = e.sky; }
  const knownBait = id => typeof id === "string" && ID_RE.test(id) && (builtinBait(id) || baits.has(id));
  if (e.bait !== undefined) {
    if (!e.bait || typeof e.bait !== "object") return `${e.id}: bait`;
    out.bait = {};
    for (const [id, f] of Object.entries(e.bait)) { if (!knownBait(id) || !num(f, LIMITS.factor)) return `${e.id}: bait ${id}`; out.bait[id] = f; }
  }
  if (e.needBait !== undefined) { if (!strs(e.needBait, knownBait)) return `${e.id}: needBait must name registered or built-in baits`; out.needBait = [...e.needBait]; }
  return out;
}

function baitEntry(e, source) {
  if (!e || typeof e !== "object" || typeof e.id !== "string" || !ID_RE.test(e.id) || e.id.length > 96) return "bad id";
  if (e.id.startsWith(`${SOURCE}:`) || builtinBait(e.id)) return `${e.id}: built-in baits are closed`;
  const have = baits.get(e.id);
  if (have && have.source !== source) return `${e.id}: already registered by ${have.source}`;
  if (!itemExists(e.id)) return `${e.id}: no such item`;
  const f = e.biteFactor === undefined ? 0.75 : e.biteFactor;
  if (!num(f, LIMITS.biteFactor)) return `${e.id}: biteFactor ${LIMITS.biteFactor[0]}..${LIMITS.biteFactor[1]}`;
  return { id: e.id, biteFactor: f, source };
}

function priceEntry(e, source) {
  if (!e || typeof e !== "object" || typeof e.id !== "string" || !ID_RE.test(e.id) || e.id.length > 96) return "bad id";
  if (e.id.startsWith(`${SOURCE}:`) || e.id.startsWith("minecraft:") || BUILTIN.has(e.id)) return `${e.id}: built-in prices are closed`;
  const have = prices.get(e.id);
  if (have && have.source !== source) return `${e.id}: already registered by ${have.source}`;
  if (!itemExists(e.id)) return `${e.id}: no such item`;
  if (!num(e.price, LIMITS.price)) return `${e.id}: price ${LIMITS.price[0]}..${LIMITS.price[1]}`;
  return { id: e.id, price: e.price, source };
}

function feedEntry(e, source) {
  if (!e || typeof e !== "object" || typeof e.id !== "string" || !ID_RE.test(e.id) || e.id.length > 96) return "bad id";
  if (e.id.startsWith(`${SOURCE}:`) || POND_FEEDS[e.id] !== undefined) return `${e.id}: built-in feeds are closed`;
  const have = feeds.get(e.id);
  if (have && have.source !== source) return `${e.id}: already registered by ${have.source}`;
  if (!itemExists(e.id)) return `${e.id}: no such item`;
  const meals = e.meals === undefined ? 1 : e.meals;
  if (!int(meals, LIMITS.meals)) return `${e.id}: meals ${LIMITS.meals[0]}..${LIMITS.meals[1]}`;
  return { id: e.id, meals, source };
}
/** Meals one item of a registered pond feed gives (undefined when it is not one). */
export const externalFeed = id => feeds.get(id)?.meals;

function count(map, source) { let n = 0; for (const v of map.values()) if (v.source === source) n++; return n; }

const KIND = {
  bait: { many: "baits", one: "bait", map: baits, make: baitEntry, label: "bait(s)" },
  catch: { many: "catches", one: "catch", map: catches, make: catchEntry, label: "catch(es)" },
  price: { many: "prices", one: "price", map: prices, make: priceEntry, label: "price(s)" },
  pond_feed: { many: "feeds", one: "feed", map: feeds, make: feedEntry, label: "pond feed(s)" },
};

/** Handle one register_* / api_ping event; returns how many entries were accepted (0 for anything else). */
export function onRegister(ev) {
  const id = ev?.id;
  if (id === EV.ping) { sendReady(); return 0; }
  const kind = id === EV.bait ? KIND.bait : id === EV.catch ? KIND.catch : id === EV.price ? KIND.price : id === EV.pond_feed ? KIND.pond_feed : undefined;
  if (!kind) return 0;
  const m = parse(ev.message);
  if (!m) { warn(`${id}: bad envelope (api ${API}, source required)`); return 0; }
  const list = m[kind.many] ?? (m[kind.one] ? [m[kind.one]] : undefined);
  if (!Array.isArray(list) || !list.length || list.length > 32) { warn(`${id} from ${m.source}: 1..32 entries per message`); return 0; }
  const { map, make } = kind;
  let ok = 0;
  for (const raw of list) {
    const e = make(raw, m.source);
    if (typeof e === "string") { warn(`${id} from ${m.source}: ${e}`); continue; }
    if (!map.has(e.id) && count(map, m.source) >= LIMITS.perSource) { warn(`${id} from ${m.source}: more than ${LIMITS.perSource} entries`); continue; }
    map.set(e.id, e);
    ok++;
  }
  if (ok) {
    onChange();
    try { console.info(`[Fishing Voyage] ${m.source} registered ${ok} ${kind.label} (${count(map, m.source)} in all)`); } catch {}
  }
  return ok;
}

function sendReady() {
  try { system.sendScriptEvent(EV.ready, JSON.stringify({ api: API, source: SOURCE, version: ADDON_VERSION, capabilities: CAPABILITIES })); } catch {}
}

system.afterEvents.scriptEventReceive.subscribe(ev => { try { onRegister(ev); } catch (err) { warn(`${ev?.id}: ${err}`); } }, { namespaces: [SOURCE] });
system.runTimeout(sendReady, 10);
