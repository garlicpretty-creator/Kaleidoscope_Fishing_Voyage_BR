// ## Fish Creel (魚簍): while it is in the inventory, landed fish and trap catches go into
// it instead of the pockets (record fish stay in the pockets as trophies). Use it to take
// fish out. Contents live on the creel itself (an ItemStack dynamic property), so it can be
// stored, dropped or traded with the fish inside.
import { ItemStack, system, world } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";
import { BASKET_ITEMS, LEGENDS } from "../data/generated.js";
import { applyClass, markOf } from "../fishing/size.js";

const NS = "kaleidoscope_fishing";
const BASKET = `${NS}:fish_basket`;
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

function read(stack) {
  try { const v = JSON.parse(stack.getDynamicProperty(KEY) ?? "{}"); return v && typeof v === "object" ? v : {}; } catch { return {}; }
}
const total = c => Object.values(c).reduce((a, b) => a + b, 0);
function write(container, slot, stack, contents) {
  try {
    stack.setDynamicProperty(KEY, JSON.stringify(contents));
    stack.setLore([`§7${total(contents)} / ${CAPACITY}`]);
    container.setItem(slot, stack);
  } catch {}
}

function findBasket(player) {
  try {
    const inv = player.getComponent("minecraft:inventory")?.container;
    if (!inv) return undefined;
    for (let i = 0; i < inv.size; i++) {
      const it = inv.getItem(i);
      if (it?.typeId === BASKET && total(read(it)) < CAPACITY) return { inv, slot: i, stack: it };
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

const tr = key => ({ translate: `${NS}.journal.${key}` });

async function open(player) {
  const inv = player.getComponent("minecraft:inventory")?.container;
  const slot = player.selectedSlotIndex;
  const stack = inv?.getItem(slot);
  if (stack?.typeId !== BASKET) return;
  const c = read(stack);
  const ids = Object.keys(c).filter(k => c[k] > 0 && INFO[splitKey(k).id])
    .sort((a, b) => a.localeCompare(b));
  const form = new ActionFormData().title(tr("basket_title"))
    .body({ translate: `${NS}.journal.basket_summary`, with: [String(total(c)), String(CAPACITY)] });
  for (const k of ids) {
    const { id, cls } = splitKey(k);
    form.button({ rawtext: [{ translate: INFO[id].nameKey }, { text: `${cls ? " " + markOf(cls) + "§r" : ""} ×${c[k]}` }] }, INFO[id].icon);
  }
  form.button(tr("close"));
  const res = await form.show(player);
  if (res.canceled || res.selection === undefined || res.selection >= ids.length) return;
  // take one stack of the chosen fish
  const key = ids[res.selection];
  const { id, cls } = splitKey(key);
  const fresh = inv.getItem(slot);
  if (fresh?.typeId !== BASKET) return;
  const cur = read(fresh);
  const max = new ItemStack(id, 1).maxAmount;
  const n = Math.min(cur[key] ?? 0, max);
  if (n <= 0) return;
  const left = inv.addItem(takeOut(id, n, cls));
  const given = n - (left?.amount ?? 0);
  cur[key] -= given;
  if (cur[key] <= 0) delete cur[key];
  write(inv, slot, fresh, cur);
  try { player.playSound("bundle.remove_one", { volume: 0.8 }); } catch {}
  if (given > 0) system.run(() => open(player).catch(() => {}));
}

world.afterEvents.itemUse.subscribe(ev => {
  if (ev.itemStack?.typeId !== BASKET || !ev.source) return;
  const player = ev.source;
  system.run(() => open(player).catch(() => {}));
});
