// ## Recipe pages in the Angler's Journal.
// A dish is learned when you first hold it, or by reading a Fisherman's Recipe Scrap
// (found in fishermen's huts). Learned dishes show their station and ingredients.
import { system, world } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";
import { RECIPE_HINTS } from "../data/generated.js";
import { spawnParticle } from "../util/particles.js";

const NS = "kaleidoscope_fishing";
const KEY = `${NS}:recipes`;
const SCRAP = `${NS}:recipe_scrap`;
const BY_ID = Object.fromEntries(RECIPE_HINTS.map(r => [r.id, r]));
const t = (key, ...w) => w.length ? { translate: `${NS}.journal.${key}`, with: w.map(String) } : { translate: `${NS}.journal.${key}` };

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

export async function showRecipes(player, back) {
  const set = learned(player);
  const form = new ActionFormData().title(t("recipes"))
    .body(t("recipes_summary", RECIPE_HINTS.filter(r => set.has(r.id)).length, RECIPE_HINTS.length));
  for (const r of RECIPE_HINTS) form.button(set.has(r.id) ? { translate: r.nameKey } : t("unknown"), set.has(r.id) ? r.icon : "textures/items/kfv_recipe_scrap");
  form.button(t("back"));
  const res = await form.show(player);
  if (res.canceled) return;
  try { player.playSound("item.book.page_turn", { volume: 0.8 }); } catch {}
  if (res.selection === undefined || res.selection >= RECIPE_HINTS.length) return back();
  const r = RECIPE_HINTS[res.selection];
  if (!set.has(r.id)) return showRecipes(player, back);
  return showRecipe(player, r, () => showRecipes(player, back));
}

async function showRecipe(player, r, back) {
  const body = { rawtext: [t("station"), { translate: `${NS}.journal.method_${r.method}` }, { text: "\n\n" }, t("ingredients"), { text: "\n" }] };
  for (const [key, n] of r.ingredients) body.rawtext.push({ text: "  • " }, { translate: key }, { text: n > 1 ? ` ×${n}\n` : "\n" });
  if (r.count > 1) body.rawtext.push({ text: "\n" }, t("makes", r.count));
  const res = await new ActionFormData().title({ translate: r.nameKey }).body(body).button(t("back")).show(player);
  if (!res.canceled) back();
}
