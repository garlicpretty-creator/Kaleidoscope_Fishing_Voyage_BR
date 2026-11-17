// ## Kaleidoscope script role: Addon -> Cookery registration bridge.
// Registers station recipes and the Fish Stock base container through Cookery's
// public API (documentation/KC_EXTENSION_API.md, KC_STOCKPOT_BASE_API.md).
// Cookery keeps registrations only for the current world session, so this runs
// every time the world loads. Re-sending is safe: Cookery replaces by kind+source+id.
import { ItemTypes, system } from "@minecraft/server";
import { KC_RECIPES, STOCKPOT_BASES } from "../data/generated.js";

export const SOURCE = "kaleidoscope_fishing";
const API = 1;
const EV = {
  ready: "kaleidoscope_cookery:api_ready",
  ping: "kaleidoscope_cookery:api_ping",
  recipe: "kaleidoscope_cookery:register_recipe",
  base: "kaleidoscope_cookery:register_stockpot_base",
};

let registered = false;

// 1.5.0: some recipes use another pack's ingredients (森羅物語：豐收's ginger, scallion, garlic ...). A recipe is sent
// only when every ingredient it needs exists in this world; a slot that takes any of several items keeps the ones
// that exist. Our own items, Cookery's and vanilla ones are always there.
const ALWAYS = /^(minecraft|kaleidoscope_cookery|kaleidoscope_fishing):/;
let itemExists = id => { try { return !!ItemTypes.get(id); } catch { return false; } };
/** Tests only. */
export function _setItemExists(fn) { itemExists = fn; }
/** Tests only: register again on the next api_ready. */
export function _resetBridge() { registered = false; }
const have = id => typeof id !== "string" || ALWAYS.test(id) || itemExists(id);
/** The recipe as it can be sent here, or undefined when an ingredient is missing. Exported for tests. */
export function usable(recipe) {
  const out = { ...recipe };
  if (Array.isArray(recipe.ingredients)) {
    const ing = [];
    for (const slot of recipe.ingredients) {
      if (Array.isArray(slot)) {
        const left = slot.filter(have);
        if (!left.length) return undefined;
        ing.push(left.length === 1 ? left[0] : left);
      } else if (!have(slot)) return undefined;
      else ing.push(slot);
    }
    out.ingredients = ing;
  }
  for (const k of ["input", "base"]) if (recipe[k] !== undefined && !have(recipe[k])) return undefined;
  return out;
}

function send(id, payload) {
  try { system.sendScriptEvent(id, JSON.stringify(payload)); } catch (err) {
    console.warn(`[Fishing Voyage] Could not send ${id}: ${err}`);
  }
}

function registerAll(capabilities) {
  if (registered) return;
  registered = true;
  // Older Cookery builds may answer without a capability list; Wok/Stockpot are the v1 baseline.
  const caps = new Set(Array.isArray(capabilities) && capabilities.length ? capabilities : ["wok", "stockpot_exact"]);
  let sent = 0, skipped = 0, absent = 0;
  for (const r of KC_RECIPES) {
    if (!caps.has(r.kind)) { skipped++; continue; }
    const recipe = usable(r.recipe);
    if (!recipe) { absent++; continue; }                 // another pack's ingredient is not installed
    send(EV.recipe, { api: API, kind: r.kind, source: SOURCE, recipe });
    sent++;
  }
  if (caps.has("stockpot_base_containers")) {
    for (const b of STOCKPOT_BASES) {
      const payload = { api: API, source: SOURCE, filled: b.filled, base: b.base, empty: b.empty,
        emptySound: "bucket.empty_water", fillSound: "bucket.fill_water" };
      // Liquid-surface visuals are a newer, separate capability; older builds just show water.
      if (caps.has("stockpot_base_visuals")) Object.assign(payload, { visualBase: b.visualBase, visualCooking: b.visualCooking, visualFinished: b.visualFinished });
      send(EV.base, payload);
    }
  } else skipped += STOCKPOT_BASES.length;
  console.info(`[Fishing Voyage] Registered ${sent} Cookery recipes${skipped ? `, skipped ${skipped} (Cookery build lacks the feature)` : ""}${absent ? `, ${absent} wait for another pack's ingredients` : ""}.`);
}

system.afterEvents.scriptEventReceive.subscribe(ev => {
  if (ev.id !== EV.ready) return;
  try {
    const info = JSON.parse(String(ev.message ?? "{}"));
    if (Number(info.api) === API) registerAll(info.capabilities);
  } catch {}
});

// Ask Cookery to announce itself in case it finished its own startup broadcast first.
system.runTimeout(() => send(EV.ping, { source: SOURCE }), 10);
// If Cookery is missing nothing answers, and the add-on's own items still work.
system.runTimeout(() => {
  if (!registered) console.warn("[Fishing Voyage] Kaleidoscope Cookery did not answer. Station recipes are unavailable; install Kaleidoscope Cookery 1.6.1+.");
}, 200);
