// ## Kaleidoscope script role: Addon -> Cookery registration bridge.
// Registers station recipes and the Fish Stock base container through Cookery's
// public API (documentation/KC_EXTENSION_API.md, KC_STOCKPOT_BASE_API.md).
// Cookery keeps registrations only for the current world session, so this runs
// every time the world loads. Re-sending is safe: Cookery replaces by kind+source+id.
import { system } from "@minecraft/server";
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
  let sent = 0, skipped = 0;
  for (const r of KC_RECIPES) {
    if (!caps.has(r.kind)) { skipped++; continue; }
    send(EV.recipe, { api: API, kind: r.kind, source: SOURCE, recipe: r.recipe });
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
  console.info(`[Fishing Voyage] Registered ${sent} Cookery recipes${skipped ? `, skipped ${skipped} (Cookery build lacks the feature)` : ""}.`);
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
