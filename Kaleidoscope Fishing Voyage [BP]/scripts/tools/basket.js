// ## Fish Creel (魚簍): while it is in the inventory, landed fish and trap catches go into
// it instead of the pockets (record fish stay in the pockets as trophies). Use it to take
// fish out. Contents live on the creel itself (an ItemStack dynamic property), so it can be
// stored, dropped or traded with the fish inside.
// 1.6.0 (docs/PLAN_1.6.0.md section 8): no text. How full it is shows as five item ids with their own icons
// (empty, a little, half, most, full); putting fish in or taking them out swaps the id and carries everything
// over (contents, name, enchantments, lore, durability). Using it opens a grid of pictures: one button per kind
// of fish with only its glyph, size mark (◆ / ◆◆ / ◆◆◆) and ✦ for a legend, plus a tier glyph for how many
// there are (few 1-8, some 9-32, many 33+). Tapping one takes a stack, as before. Crouching and using it pours
// everything out at the player's feet.
// Deviation from the plan: vanilla forms cannot colour a button's background, so the three amount tiers are a
// glyph at the front of the button (tier.few / tier.some / tier.many) instead of three backgrounds. The plan's
// stage bounds (0, 1-16, 17-40, 41-63, 64) assume a 64-fish creel; the creel holds 256, so the same fractions
// of CAPACITY are used (stageOf).
import { EnchantmentTypes, ItemStack, system, world } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";
import { BASKET_ITEMS, LEGENDS } from "../data/generated.js";
import { G, fishGlyph } from "../data/glyphs.js";
import { applyClass, markOf } from "../fishing/size.js";

const NS = "kaleidoscope_fishing";
const BASKET = `${NS}:fish_basket`;
/** The five looks of the creel, empty to full. Only the first is in the creative menu. */
export const BASKET_IDS = [BASKET, `${NS}:fish_basket_few`, `${NS}:fish_basket_half`, `${NS}:fish_basket_most`, `${NS}:fish_basket_full`];
const IS_BASKET = new Set(BASKET_IDS);
/** Whether an item id is a creel, in any of its looks. */
export const isBasket = id => IS_BASKET.has(id);
const KEY = `${NS}:creel`;
export const CAPACITY = 256;
const INFO = Object.fromEntries(BASKET_ITEMS.map(b => [b.id, b]));
const LEGEND = new Set(LEGENDS ?? []);
/** A stack as it comes out of the creel: its size mark, and a legend's ✦ (the lore the rod gave it). 1.5.0: legends go in too. */
export function takeOut(id, n, cls) {
  const stack = applyClass(new ItemStack(id, n), cls);
  if (LEGEND.has(id)) { try { stack.setLore([...(stack.getLore() ?? []), "§d✦"]); } catch {} }
  return stack;
}

/** The look for n fish: 0 empty, 1 a little, 2 half, 3 most, 4 full. The plan's bounds for a 64-fish creel
 *  (1-16, 17-40, 41-63, 64) as fractions of `cap`. Exported for tests. */
export function stageOf(n, cap = CAPACITY) {
  if (!(n > 0)) return 0;
  if (n >= cap) return 4;
  const f = (n * 64) / cap;
  return f <= 16 ? 1 : f <= 40 ? 2 : 3;
}
/** How many of one kind, as a tier: 1 few (1-8), 2 some (9-32), 3 many (33+). Exported for tests. */
export const tierOf = n => (n >= 33 ? 3 : n >= 9 ? 2 : 1);
const TIER_GLYPH = ["", "tier.few", "tier.some", "tier.many"];

/** The contents of a creel stack: { "<id>" | "<id>#<cls>": count }. */
export function read(stack) {
  try { const v = JSON.parse(stack.getDynamicProperty(KEY) ?? "{}"); return v && typeof v === "object" ? v : {}; } catch { return {}; }
}
export const total = c => Object.values(c).reduce((a, b) => a + (Number(b) || 0), 0);
// up to 1.5.0 the creel's lore said "N / 256"; it goes the first time the creel is written
const OLD_COUNT = /^(§.)*\d+\s*\/\s*\d+$/;

/** The same creel as another look: every dynamic property, the name, lore (less the old count), enchantments,
 *  durability, keep-on-death and lock carried over. Returns the stack itself when the look is already right.
 *  Exported for tests. */
export function asLook(stack, id) {
  if (stack.typeId === id) return stack;
  let out;
  try { out = new ItemStack(id, 1); } catch { return stack; }
  try { for (const k of stack.getDynamicPropertyIds()) out.setDynamicProperty(k, stack.getDynamicProperty(k)); } catch {}
  try { if (stack.nameTag) out.nameTag = stack.nameTag; } catch {}
  try { const lore = (stack.getLore() ?? []).filter(l => !OLD_COUNT.test(l)); if (lore.length) out.setLore(lore); } catch {}
  try { out.keepOnDeath = stack.keepOnDeath; } catch {}
  try { if (stack.lockMode !== undefined) out.lockMode = stack.lockMode; } catch {}
  try {
    const from = stack.getComponent("minecraft:enchantable"), to = out.getComponent("minecraft:enchantable");
    if (from && to) {
      for (const e of from.getEnchantments()) {
        try { const type = typeof e.type === "string" ? EnchantmentTypes.get(e.type) : e.type; to.addEnchantment({ type, level: e.level }); } catch {}
      }
    }
  } catch {}
  try {
    const from = stack.getComponent("minecraft:durability"), to = out.getComponent("minecraft:durability");
    if (from && to) to.damage = Math.min(from.damage, to.maxDurability - 1);
  } catch {}
  return out;
}

/** Save contents onto the creel in that slot, in the look that matches them. */
function write(container, slot, stack, contents) {
  try {
    stack.setDynamicProperty(KEY, JSON.stringify(contents));
    const lore = stack.getLore() ?? [];
    if (lore.some(l => OLD_COUNT.test(l))) stack.setLore(lore.filter(l => !OLD_COUNT.test(l)));
    container.setItem(slot, asLook(stack, BASKET_IDS[stageOf(total(contents))]));
  } catch {}
}

function findBasket(player) {
  try {
    const inv = player.getComponent("minecraft:inventory")?.container;
    if (!inv) return undefined;
    for (let i = 0; i < inv.size; i++) {
      const it = inv.getItem(i);
      if (it && isBasket(it.typeId) && total(read(it)) < CAPACITY) return { inv, slot: i, stack: it };
    }
  } catch {}
  return undefined;
}

// Contents are counted per fish and size class: "id" (no class) or "id#1".."id#3".
const keyOf = (typeId, cls) => (cls ? `${typeId}#${cls}` : typeId);
const splitKey = key => { const [id, c] = key.split("#"); return { id, cls: Number(c ?? 0) }; };

/** Put up to `amount` of typeId (size class cls, 0 = none) into a creel the player carries.
 *  Returns how many did not fit. */
export function tryStore(player, typeId, amount = 1, cls = 0) {
  if (!INFO[typeId]) return amount;
  const b = findBasket(player);
  if (!b) return amount;
  const c = read(b.stack);
  const room = CAPACITY - total(c);
  const n = Math.min(room, amount);
  if (n <= 0) return amount;
  const key = keyOf(typeId, cls);
  c[key] = (c[key] ?? 0) + n;
  write(b.inv, b.slot, b.stack, c);
  try { player.playSound("bundle.insert", { volume: 0.7, pitch: 0.9 + Math.random() * 0.2 }); } catch {}
  return amount - n;
}

/** The kinds shown in the grid, in a fixed order. Exported for tests. */
export const kindsOf = c => Object.keys(c).filter(k => c[k] > 0 && INFO[splitKey(k).id]).sort((a, b) => a.localeCompare(b));
/** One grid button's label: tier glyph, fish glyph, size mark, ✦ for a legend. Nothing else. Exported for tests. */
export function label(key, n) {
  const { id, cls } = splitKey(key);
  return `${G[TIER_GLYPH[tierOf(n)]] ?? ""}${fishGlyph(id)}${cls ? ` ${markOf(cls)}§r` : ""}${LEGEND.has(id) ? " §d✦§r" : ""}`;
}

async function open(player) {
  const inv = player.getComponent("minecraft:inventory")?.container;
  const slot = player.selectedSlotIndex;
  const stack = inv?.getItem(slot);
  if (!stack || !isBasket(stack.typeId)) return;
  const c = read(stack);
  const look = BASKET_IDS[stageOf(total(c))];
  if (stack.typeId !== look) write(inv, slot, stack, c);    // an old creel, or one given by command: the right look
  const ids = kindsOf(c);
  if (!ids.length) { try { player.playSound("bundle.insert_fail", { volume: 0.6 }); } catch {} return; }
  const form = new ActionFormData().title(" ");
  for (const k of ids) form.button(label(k, c[k]), INFO[splitKey(k).id].icon);
  const res = await form.show(player);
  if (res.canceled || res.selection === undefined || res.selection >= ids.length) return;
  // take one stack of the chosen fish
  const key = ids[res.selection];
  const { id, cls } = splitKey(key);
  const fresh = inv.getItem(slot);
  if (!fresh || !isBasket(fresh.typeId)) return;
  const cur = read(fresh);
  const max = new ItemStack(id, 1).maxAmount;
  const n = Math.min(cur[key] ?? 0, max);
  if (n <= 0) return;
  const left = inv.addItem(takeOut(id, n, cls));
  const given = n - (left?.amount ?? 0);
  cur[key] -= given;
  if (cur[key] <= 0) delete cur[key];
  write(inv, slot, inv.getItem(slot) ?? fresh, cur);
  try { player.playSound("bundle.remove_one", { volume: 0.8 }); } catch {}
  if (given > 0 && total(cur) > 0) system.run(() => open(player).catch(() => {}));
}

/** Crouch + use: everything in the creel falls out at the player's feet. Exported for tests. */
export function pourAll(player) {
  const inv = player.getComponent("minecraft:inventory")?.container;
  const slot = player.selectedSlotIndex;
  const stack = inv?.getItem(slot);
  if (!stack || !isBasket(stack.typeId)) return 0;
  const c = read(stack);
  let n = 0;
  for (const key of kindsOf(c)) {
    const { id, cls } = splitKey(key);
    let left = c[key];
    let max = 64;
    try { max = new ItemStack(id, 1).maxAmount; } catch { continue; }
    while (left > 0) {
      const k = Math.min(left, max);
      try { player.dimension.spawnItem(takeOut(id, k, cls), player.location); } catch { break; }
      left -= k; n += k;
    }
    if (left > 0) c[key] = left; else delete c[key];
  }
  write(inv, slot, stack, c);
  if (n > 0) { try { player.playSound("bundle.drop_contents", { volume: 0.9 }); } catch {} }
  return n;
}

world.afterEvents.itemUse.subscribe(ev => {
  if (!ev.itemStack || !isBasket(ev.itemStack.typeId) || !ev.source) return;
  const player = ev.source;
  if (player.isSneaking) { system.run(() => { try { pourAll(player); } catch {} }); return; }
  system.run(() => open(player).catch(() => {}));
});
