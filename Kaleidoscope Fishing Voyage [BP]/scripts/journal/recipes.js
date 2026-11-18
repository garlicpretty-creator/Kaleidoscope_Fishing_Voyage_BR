// ## Recipe pages in the Angler's Journal.
// A dish is learned when you first hold it, or by reading a Fisherman's Recipe Scrap
// (found in fishermen's huts). Learned dishes show their station and ingredients.
import { system, world } from "@minecraft/server";
import { RECIPE_HINTS } from "../data/generated.js";
import { G, itemGlyph, stationGlyph } from "../data/glyphs.js";
import { spawnParticle } from "../util/particles.js";
import { showPaged, showPlain } from "./book.js";

const NS = "kaleidoscope_fishing";
const KEY = `${NS}:recipes`;
const SCRAP = `${NS}:recipe_scrap`;
const BY_ID = Object.fromEntries(RECIPE_HINTS.map(r => [r.id, r]));
const SCRAP_ICON = "textures/items/kfv_recipe_scrap";

export function learned(player) {
  try { const v = JSON.parse(player.getDynamicProperty(KEY) ?? "[]"); return new Set(Array.isArray(v) ? v : []); } catch { return new Set(); }
}
function save(player, set) { try { player.setDynamicProperty(KEY, JSON.stringify([...set])); } catch {} }

export function learn(player, id) {
  if (!BY_ID[id]) return false;
  const set = learned(player);
  if (set.has(id)) return false;
  set.add(id); save(player, set);
  return true;
}

function flourish(player) {
  try { player.playSound("random.orb", { volume: 0.6, pitch: 1.3 }); } catch {}
  const l = player.location;
  for (let i = 0; i < 6; i++) {
    try { spawnParticle(player.dimension, "minecraft:villager_happy", { x: l.x + (Math.random() - 0.5), y: l.y + 1.2 + Math.random() * 0.6, z: l.z + (Math.random() - 0.5) }); } catch {}
  }
}

// Holding a dish for the first time teaches it.
world.afterEvents.playerInventoryItemChange.subscribe(ev => {
  const id = ev.itemStack?.typeId;
  if (!id || !BY_ID[id]) return;
  const player = ev.player;
  system.run(() => { if (learn(player, id)) flourish(player); });
});

// Reading a scrap teaches one dish you do not know yet.
world.afterEvents.itemUse.subscribe(ev => {
  if (ev.itemStack?.typeId !== SCRAP || !ev.source) return;
  const player = ev.source;
  system.run(() => {
    const set = learned(player);
    const open = RECIPE_HINTS.filter(r => !set.has(r.id));
    try { player.playSound("item.book.page_turn", { volume: 0.9 }); } catch {}
    if (!open.length) return;
    const pick = open[Math.floor(Math.random() * open.length)];
    learn(player, pick.id);
    flourish(player);
    try {
      const inv = player.getComponent("minecraft:inventory").container;
      const i = player.selectedSlotIndex, it = inv.getItem(i);
      if (it?.typeId === SCRAP && player.getGameMode() !== "Creative" && player.getGameMode() !== "creative") {
        if (it.amount <= 1) inv.setItem(i, undefined); else { it.amount -= 1; inv.setItem(i, it); }
      }
    } catch {}
    system.run(() => showRecipe(player, pick, () => {}).catch(() => {}));
  });
});

// 1.6.0 (docs/PLAN_1.6.0.md 6.4): glyphs only. The list is the dishes' glyphs (one not learned yet: the recipe
// scrap), PAGE to a page; a recipe is one line: station ┃ each ingredient (dots for more than one) → the dish
// (dots for more than one serving).
const NEED = n => (n > 1 ? G["dot.full"].repeat(n) : "");
/** A recipe's line: station, bar, ingredients with their counts, arrow, the dish and how many it makes. */
export function recipeLine(r) {
  const ings = r.ingredients.map(([key, n]) => itemGlyph(key) + NEED(n)).join(" ");
  return `${stationGlyph(r.method)} ${G["mark.sep"]} ${ings} ${G["arrow.right"]} ${itemGlyph(r.id)}${NEED(r.count)}`;
}

export async function showRecipes(player, back, page = 0) {
  const set = learned(player);
  const items = RECIPE_HINTS.map(r => (set.has(r.id) ? { text: itemGlyph(r.id), icon: r.icon } : { text: G["ui.recipe_scrap"], icon: SCRAP_ICON }));
  const res = await showPaged(player, { items, page });
  if (!res) return;
  if (res.back) return back();
  const r = RECIPE_HINTS[res.pick];
  if (!set.has(r.id)) return showRecipes(player, back, res.page);
  return showRecipe(player, r, () => showRecipes(player, back, res.page));
}

async function showRecipe(player, r, back) {
  if (await showPlain(player, recipeLine(r))) return back();
}
