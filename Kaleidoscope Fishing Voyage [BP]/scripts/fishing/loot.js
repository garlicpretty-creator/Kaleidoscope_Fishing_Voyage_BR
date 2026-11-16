// ## Fishing: catch roll. The catch table itself lives in tools/data.py (CATCHES).
import { CATCHES, LEGENDS } from "../data/generated.js";
import { externalCatches, externalBaits, _wire } from "./registry.js";   // v1.6.2: baits / catches other packs register
export const LEGEND_SET = new Set(LEGENDS ?? []);
const LEGEND_REPEAT = 0.25;            // decision #3: a legend you already caught is four times rarer

/** v1.4 legends: every condition in entry.req must hold, and only a rod (ctx.rod) can hook one. */
export function reqOk(e, ctx) {
  const r = e.req;
  if (!r) return true;
  if (!ctx.rod) return false;
  if (r.tier && (ctx.tier ?? 1) < r.tier) return false;
  if (r.weather === "thunder" && !ctx.thunder) return false;
  if (r.weather === "rain" && !ctx.raining) return false;
  if (r.hook && ctx.hook !== r.hook) return false;
  if (r.line && ctx.line !== r.line) return false;
  if (r.bait && ctx.bait !== r.bait) return false;
  if (r.nobait && ctx.bait && ctx.bait !== LURE) return false;
  if (r.moon && !r.moon.includes(ctx.moon)) return false;
  if (r.tide && ctx.tide !== r.tide) return false;
  if (r.slots && !r.slots.includes(ctx.slot)) return false;
  if (r.dim && ctx.dim !== r.dim) return false;
  return true;
}

export const JUNK = [
  { id: "minecraft:kelp", w: 4 }, { id: "minecraft:stick", w: 3 }, { id: "minecraft:string", w: 2 },
  { id: "minecraft:bowl", w: 2 }, { id: "minecraft:waterlily", w: 3, waters: ["swamp", "lake", "river"] },
  { id: "minecraft:magma_cream", w: 3, waters: ["lava"] }, { id: "minecraft:gold_nugget", w: 3, waters: ["lava"] },
  { id: "minecraft:quartz", w: 2, waters: ["lava"] },
  { id: "minecraft:chorus_fruit", w: 4, waters: ["end_pond"] }, { id: "minecraft:popped_chorus_fruit", w: 2, waters: ["end_pond"] },
];
export const TREASURE = [
  { id: "minecraft:nautilus_shell", w: 3, waters: ["ocean", "warm_ocean", "deep_ocean", "cold_ocean"] },
  { id: "minecraft:name_tag", w: 2 }, { id: "minecraft:saddle", w: 1 },
  { id: "minecraft:gold_ingot", w: 2, waters: ["lava"] }, { id: "minecraft:netherite_scrap", w: 1, waters: ["lava"] },
  { id: "minecraft:ender_pearl", w: 3, waters: ["end_pond"] }, { id: "minecraft:experience_bottle", w: 2, waters: ["end_pond"] },
  { id: "minecraft:shulker_shell", w: 1, waters: ["end_pond"] },
];
export const JUNK_CHANCE = 0.07;
export const TREASURE_CHANCE = 0.015;

/** The lure hook's stand-in bait id: not an item, so it is never consumed or searched for. */
export const LURE = "kaleidoscope_fishing:lure";
export const BAITS = {
  "kaleidoscope_cookery:caterpillar": { biteFactor: 0.6 },
  "kaleidoscope_fishing:shrimp": { biteFactor: 0.8 },
  "kaleidoscope_fishing:fish_meal_bait": { biteFactor: 0.5 },
  "kaleidoscope_fishing:glow_bait": { biteFactor: 0.75 },
  "kaleidoscope_fishing:fish_offal": { biteFactor: 0.65 },
  "kaleidoscope_fishing:end_maggot": { biteFactor: 0.7 },     // v1.3, for End ponds
  "kaleidoscope_fishing:live_shrimp": { biteFactor: 0.7 },    // v1.4, from the shrimp trap
  "kaleidoscope_fishing:earthworm": { biteFactor: 0.75 },     // v1.4, dug from wet grass
  [LURE]: { biteFactor: 0.9 },                                // v1.4: the lure hook, never consumed
};

export const CATCH_BY_ID = Object.fromEntries(CATCHES.map(c => [c.id, c]));

// v1.6.2: entries registered by other packs (fishing/registry.js) join the pool; CATCH_BY_ID and BAITS are
// kept in step so rollSize / fightLength / the rod's bait search see them too. Built-in entries are never replaced.
const BUILTIN_BAITS = new Set(Object.keys(BAITS));
let EXTERNAL = [];
function syncExternal() {
  for (const k of Object.keys(CATCH_BY_ID)) if (CATCH_BY_ID[k].source) delete CATCH_BY_ID[k];
  for (const k of Object.keys(BAITS)) if (!BUILTIN_BAITS.has(k)) delete BAITS[k];
  EXTERNAL = externalCatches();
  for (const e of EXTERNAL) CATCH_BY_ID[e.id] = e;
  for (const b of externalBaits()) BAITS[b.id] = { biteFactor: b.biteFactor, source: b.source };
}
_wire(id => BUILTIN_BAITS.has(id), syncExternal);
/** All catches that can be rolled now: built-in plus registered. */
export const allCatches = () => (EXTERNAL.length ? CATCHES.concat(EXTERNAL) : CATCHES);

function matchWater(entry, ctx) {
  if (entry.needs && !entry.needs.every(t => ctx.waters.has(t))) return false;  // v1.4: e.g. needs ["lush"]
  if (ctx.waters.has("lava")) return !!entry.waters?.includes("lava");     // lava has its own catches only
  if (ctx.waters.has("void")) return !!entry.waters?.includes("void");     // so has the End's void (v1.2)
  if (ctx.waters.has("end_pond")) return !!entry.waters?.includes("end_pond"); // and End ponds (v1.3)
  if (ctx.waters.has("cave")) return !!entry.waters?.includes("cave");         // and cave water (v1.4)
  return !entry.waters || entry.waters.some(w => ctx.waters.has(w));
}

function pickWeighted(list, weightOf, rand) {
  let total = 0;
  const ws = list.map(e => { const w = Math.max(0, weightOf(e)); total += w; return w; });
  if (total <= 0) return undefined;
  let r = rand() * total;
  for (let i = 0; i < list.length; i++) { r -= ws[i]; if (r <= 0) return list[i]; }
  return list[list.length - 1];
}

/** ctx: {waters:Set, depth, cold, slot, raining, bait, tier, moon, tide} -> item id
 *  v1.3 entry fields: slots (only in these time slots), moon: "full" (only on a full-moon
 *  night), tide: { high, low } (weight multiplier at that tide). */
export function rollCatch(ctx, rand = Math.random) {
  const roll = rand();
  if (roll < TREASURE_CHANCE) {
    const t = pickWeighted(TREASURE.filter(e => matchWater(e, ctx)), e => e.w, rand);
    if (t) return t.id;
  } else if (!ctx.school && roll < TREASURE_CHANCE + JUNK_CHANCE) {   // no junk out of a fish school
    const j = pickWeighted(JUNK.filter(e => matchWater(e, ctx)), e => e.w, rand);
    if (j) return j.id;
  }
  const tier = ctx.tier ?? 1;
  const isDay = ctx.slot === "day" || ctx.slot === "dawn" || ctx.slot === "dusk";
  const pool = allCatches().filter(e => matchWater(e, ctx)
    && (e.tier === undefined || tier >= e.tier)
    && (e.min_depth === undefined || ctx.depth >= e.min_depth)
    && (e.max_depth === undefined || ctx.depth <= e.max_depth)
    && reqOk(e, ctx)
    && (!e.needBait || (!!ctx.bait && e.needBait.includes(ctx.bait))));   // v1.6.2: e.g. element fish only on arcane bait
  const pick = pickWeighted(pool, e => {
    let w = e.w;
    if (e.time === "day" && !isDay) w *= e.off ?? 0.3;
    if (e.time === "night" && isDay) w *= e.off ?? 0.3;
    if (e.slots && !e.slots.includes(ctx.slot)) return 0;
    if (e.req && ctx.caught?.has?.(e.id)) w *= LEGEND_REPEAT;
    if (e.moon === "full" && ctx.moon !== 0) return 0;
    // v1.4: moon as a list of phases is a boost, not a gate (0 full ... 4 new): the mullet run, the flying-fish season.
    if (Array.isArray(e.moon) && e.moon_boost && e.moon.includes(ctx.moon)) w *= e.moon_boost;
    if (e.tide && ctx.tide && e.tide[ctx.tide]) w *= e.tide[ctx.tide];
    if (e.dawn_dusk && (ctx.slot === "dawn" || ctx.slot === "dusk")) w *= e.dawn_dusk;
    if (e.rain && ctx.raining) w *= e.rain;
    if (e.cold && ctx.cold) w *= e.cold;
    if (e.bait && ctx.bait && e.bait[ctx.bait]) w *= e.bait[ctx.bait];
    if (e.tier_bonus && tier >= 2) w *= e.tier_bonus;
    if (ctx.school) w *= e.school ?? ((e.size && e.w <= 12) ? 1.8 : 1);   // a school draws the less common fish up (v1.4: or the entry's own factor)
    if (e.size && e.w <= 12) w *= ctx.rare || 1;                       // copper / gold hooks
    if (e.size && e.w <= 12 && !e.req) w *= ctx.luck || 1;             // 1.5.0: Luck of the Sea on the rod; never a legend
    if (ctx.shallow && ctx.shallow !== 1 && e.max_depth !== undefined && e.max_depth <= 6) w *= ctx.shallow;   // v1.4 feather bobber
    return w;
  }, rand);
  return pick?.id ?? "minecraft:cod";
}

/** Body length in cm, skewed small. Better rods pull bigger fish. */
export function rollSize(id, tier = 1, rand = Math.random) {
  const c = CATCH_BY_ID[id];
  if (!c?.size) return undefined;
  const [lo, hi] = c.size;
  const t = Math.pow(rand(), tier >= 3 ? 1.0 : tier >= 2 ? 1.25 : 1.6);   // tier 3 = voyage rod + bone hook
  return Math.round(lo + (hi - lo) * t);
}

/** How many successful reels a hooked fish needs (0 = lands at once). */
export function fightLength(id, size) {
  const c = CATCH_BY_ID[id];
  if (!c || !c.fight) return 0;
  let n = c.fight * 2;
  if (size !== undefined && c.size) {
    const p = (size - c.size[0]) / Math.max(1, c.size[1] - c.size[0]);
    if (p > 0.75) n += 2;
  }
  return n;
}
