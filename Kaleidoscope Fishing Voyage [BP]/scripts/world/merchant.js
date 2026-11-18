// ## Wandering Fish Merchant (流浪漁販, v1.2). Now and then, in the daytime, a fish seller
// with a carrying pole turns up near a player who is by the water. He trades through the
// game's own trading screen (entity file + trading/kfv_fish_merchant.json) and moves on after
// two Minecraft days (the entity's timer). One at a time in the world. No text: you hear his
// hand bell before you see him.
// He buys fish when you use one on him: the whole stack in your hand, sizes mixed or not, and
// big fish fetch more (small x0.6, large x1.6, a record x2.5). The trading screen only matched
// identical stacks, so the buying moved here (v1.2-pre7); the screen keeps what he sells.
import { EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { isWater } from "../fishing/water.js";
import { FISH_ALIAS, MERCHANT_BUDGET, MERCHANT_PRICES } from "../data/generated.js";
import { LARGE, MEDIUM, SMALL, isFarmed, rangeOf, readSize } from "../fishing/size.js";
import { WANT_LIST } from "../data/generated.js";
import { spawnParticle } from "../util/particles.js";
import { externalPrice } from "../fishing/registry.js";
import { emit } from "../api/host.js";

const NS = "kaleidoscope_fishing";
const MERCHANT = `${NS}:fish_merchant`;
const CHECK = 6000;          // every 5 minutes
const CHANCE = 0.2;          // per check, when someone is by the water in the day
const randInt = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
const bell = (dim, loc, volume = 0.5) => { try { dim.playSound("block.bell.hit", loc, { pitch: 1.9, volume }); } catch {} };

function merchants() {
  try { return world.getDimension("overworld").getEntities({ type: MERCHANT }); } catch { return []; }
}

function nearWater(p) {
  const dim = p.dimension, b = p.location;
  for (let i = 0; i < 24; i++) {
    const x = Math.floor(b.x) + randInt(-10, 10), z = Math.floor(b.z) + randInt(-10, 10);
    for (let y = Math.floor(b.y); y >= Math.floor(b.y) - 3; y--) {
      try { if (isWater(dim.getBlock({ x, y, z }))) return true; } catch { break; }
    }
  }
  return false;
}

/** Dry ground 16-24 blocks from the player, with room to stand. */
function spawnSpot(p) {
  const dim = p.dimension, b = p.location;
  for (let i = 0; i < 12; i++) {
    const a = Math.random() * Math.PI * 2, r = randInt(16, 24);
    const x = Math.floor(b.x + Math.cos(a) * r), z = Math.floor(b.z + Math.sin(a) * r);
    try {
      const top = dim.getTopmostBlock({ x, z });
      if (!top || isWater(top) || /leaves|water|lava|ice/.test(top.typeId)) continue;
      if (Math.abs(top.y - b.y) > 8) continue;
      const head = dim.getBlock({ x, y: top.y + 2, z });
      if (head && head.typeId !== "minecraft:air") continue;
      return { x: x + 0.5, y: top.y + 1, z: z + 0.5 };
    } catch {}
  }
  return undefined;
}

function check() {
  const t = world.getTimeOfDay?.() ?? 6000;
  if (t < 1000 || t > 10000) return;                       // daytime only
  if (merchants().length) return;
  if (Math.random() > CHANCE) return;
  const players = world.getAllPlayers().filter(p => p.dimension.id === "minecraft:overworld");
  const p = players[Math.floor(Math.random() * players.length)];
  if (!p || !nearWater(p)) return;
  const at = spawnSpot(p);
  if (!at) return;
  try { const m = p.dimension.spawnEntity(MERCHANT, at); setWants(m); orderOf(m); bell(p.dimension, at, 0.8); } catch {}
}

system.runInterval(() => { try { for (const m of merchants()) wantsOf(m); check(); } catch (err) { console.warn(`[Fishing Voyage] merchant: ${err}`); } }, CHECK);
// his hand bell as he walks
system.runInterval(() => {
  for (const m of merchants()) if (Math.random() < 0.5) bell(m.dimension, m.location, 0.45);
}, 400);

// --------------------------------------------------------------- the day's wants (v1.4)
// Two fish from WANT_LIST, paid double. Both hang from his carrying pole for everyone to see.
const WANTS = `${NS}:wants`;
const WANT_BONUS = 2;
const WANTS_DAY = `${NS}:wants_day`;             // a merchant who stays a second day wants new fish that day
const today = () => { try { return world.getDay(); } catch { return 0; } };
const pickWants = (not) => { const a = WANT_LIST.filter(id => id !== not); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a.slice(0, 2); };
function setWants(m) {
  let ordered;                                   // 1.5.0: the day's wanted fish are never the fish of his order
  try { ordered = JSON.parse(m.getDynamicProperty(`${NS}:order`) ?? "null")?.id; } catch {}
  const w = pickWants(ordered);
  try { m.setDynamicProperty(WANTS, JSON.stringify(w)); m.setDynamicProperty(WANTS_DAY, today()); } catch {}
  try { m.setProperty(`${NS}:want_a`, WANT_LIST.indexOf(w[0]) + 1); m.setProperty(`${NS}:want_b`, WANT_LIST.indexOf(w[1]) + 1); } catch {}
  return w;
}
function wantsOf(m) {
  try {
    const v = JSON.parse(m.getDynamicProperty(WANTS) ?? "null");
    if (Array.isArray(v) && v.length && (m.getDynamicProperty(WANTS_DAY) ?? today()) === today()) return v;
  } catch {}
  return setWants(m);                       // a merchant from 1.3.x gets his wants the first time he is asked
}
/** What the nearest merchant wants, for the journal; undefined if none is about. */
export function wantsNear(player) {
  let near;
  try { near = player.dimension.getEntities({ type: MERCHANT, location: player.location, maxDistance: 96, closest: 1 })[0]; } catch {}
  if (!near) return undefined;
  return wantsOf(near).slice(0, 2);
}

// --------------------------------------------------------------- his order (1.5.0)
// Besides the two fish of the day, a merchant carries one order for his whole visit: so many of one fish, now and
// then of medium size or better. Fish sold to him count toward it, each player on their own; a filled order
// brings a reward. The order's fish hangs low on his pole, and the journal's tide page tells the count.
const ORDER = `${NS}:order`, ORDER_DONE = `${NS}:order_done`;
const ORDER_SIZED_CHANCE = 0.3;
// cheap fish: six of them; middling: four; dear: two
const orderCount = id => (MERCHANT_PRICES[id] <= 0.25 ? 6 : MERCHANT_PRICES[id] <= 0.5 ? 4 : 2);
export const ORDER_REWARDS = [
  { w: 30, give: () => [new ItemStack(`${NS}:recipe_scrap`, 1)] },
  { w: 30, give: () => [new ItemStack([`${NS}:copper_hook`, `${NS}:hemp_line`, `${NS}:bamboo_bobber`][randInt(0, 2)], 1)] },
  { w: 25, give: () => [new ItemStack(Math.random() < 0.5 ? `${NS}:fish_meal_bait` : `${NS}:glow_bait`, 8)] },
  { w: 8, give: () => [new ItemStack(`${NS}:wooden_tub`, 1)] },         // 1.5.0: the tub and the pond feeder
  { w: 8, give: () => [new ItemStack(`${NS}:pond_feeder`, 1)] },
  { w: 15, give: () => [new ItemStack("minecraft:emerald", 6)] },
];
function setOrder(m) {
  let wants = [];
  try { wants = JSON.parse(m.getDynamicProperty(WANTS) ?? "[]") ?? []; } catch {}
  const pool = WANT_LIST.filter(id => !wants.includes(id) && MERCHANT_PRICES[id] !== undefined);
  const id = pool[randInt(0, pool.length - 1)];
  if (!id) return undefined;
  const o = { id, n: orderCount(id), min: rangeOf(id) && Math.random() < ORDER_SIZED_CHANCE ? MEDIUM : 0 };
  try { m.setDynamicProperty(ORDER, JSON.stringify(o)); m.setDynamicProperty(ORDER_DONE, "{}"); } catch {}
  try { m.setProperty(ORDER, WANT_LIST.indexOf(id) + 1); } catch {}
  return o;
}
/** The merchant's order { id, n, min }. One who came before 1.5.0 gets his the first time he is asked. */
export function orderOf(m) {
  try { const v = JSON.parse(m.getDynamicProperty(ORDER) ?? "null"); if (v && typeof v.id === "string" && v.n > 0) return v; } catch {}
  wantsOf(m);
  return setOrder(m);
}
function progressOf(m) {
  try { const v = JSON.parse(m.getDynamicProperty(ORDER_DONE) ?? "{}"); return v && typeof v === "object" ? v : {}; } catch { return {}; }
}
/** How many more fish of this kind and size (a record counts as large) the player may hand in for the order. */
function orderRoom(m, player, id, cls, record) {
  const o = orderOf(m);
  if (!o || o.id !== id) return 0;
  if (o.min && !record && (cls || MEDIUM) < o.min) return 0;      // a fish with no mark counts as medium (size.js)
  return Math.max(0, o.n - (progressOf(m)[player.id] ?? 0));
}
/** Count n fish toward the player's order; hands over the reward when it is filled. */
function fillOrder(m, player, n) {
  const o = orderOf(m);
  if (!o || n <= 0) return;
  const done = progressOf(m);
  const before = done[player.id] ?? 0;
  if (before >= o.n) return;
  done[player.id] = Math.min(o.n, before + n);
  try { m.setDynamicProperty(ORDER_DONE, JSON.stringify(done)); } catch {}
  if (done[player.id] < o.n) return;
  let roll = Math.random() * ORDER_REWARDS.reduce((a, r) => a + r.w, 0);
  const reward = ORDER_REWARDS.find(r => (roll -= r.w) <= 0) ?? ORDER_REWARDS[0];
  for (const stack of reward.give()) {
    try { const rest = player.getComponent("minecraft:inventory")?.container?.addItem(stack); if (rest) player.dimension.spawnItem(rest, player.location); }
    catch { try { player.dimension.spawnItem(stack, player.location); } catch {} }
  }
  bell(m.dimension, m.location, 0.9);
  system.runTimeout(() => { try { bell(m.dimension, m.location, 0.9); } catch {} }, 6);
  try { player.playSound("random.levelup", { pitch: 1.4, volume: 0.5 }); } catch {}
  emit("order_filled", player, { id: o.id, n: o.n });
}
/** The nearest merchant's order for the journal: { id, n, min, have }; undefined if none is about. */
export function orderNear(player) {
  let near;
  try { near = player.dimension.getEntities({ type: MERCHANT, location: player.location, maxDistance: 96, closest: 1 })[0]; } catch {}
  const o = near && orderOf(near);
  return o ? { ...o, have: Math.min(o.n, progressOf(near)[player.id] ?? 0) } : undefined;
}

// --------------------------------------------------------------- he buys fish
export const FARMED_PRICE = 0.6;
const CLASS_PRICE = { 0: 1, [SMALL]: 0.6, [MEDIUM]: 1, [LARGE]: 1.6 };
/** Emeralds for one medium fish: our own table first, then what another pack registered (1.5.0 register_price). */
export const priceOf = id => MERCHANT_PRICES[id] ?? externalPrice(id);
const CREDIT = `${NS}:merchant_credit`, SPENT = `${NS}:spent`;
const snd = (e, id, pitch = 1, volume = 0.8) => { try { e.dimension.playSound(id, e.location, { pitch, volume }); } catch {} };
// 1.5.0 (immersive motion): a gesture the resource pack plays for about 1.5 s: 1 a little bow and nod (a sale, or the
// trading screen opening), 2 a shake of the head (he will not buy).
const gestureAt = new Map();
function gesture(m, kind) {
  const tick = system.currentTick;
  gestureAt.set(m.id, tick);
  try { m.setProperty(`${NS}:gesture`, kind); } catch {}
  system.runTimeout(() => {
    if (gestureAt.get(m.id) !== tick) return;
    gestureAt.delete(m.id);
    try { if (m.isValid) m.setProperty(`${NS}:gesture`, 0); } catch {}
  }, 30);
}

function sell(player, merchant, id) {
  const slot = player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
  const stack = slot?.hasItem() ? slot.getItem() : undefined;
  if (!stack || (FISH_ALIAS[stack.typeId] ?? stack.typeId) !== id) return;
  const { cls, record } = readSize(stack);
  const farmed = isFarmed(stack);                         // 1.5.0: pond fish: 60%, and never the day's double
  const want = !farmed && wantsOf(merchant).slice(0, 2).includes(id) ? WANT_BONUS : 1;
  const each = priceOf(id) * (record ? 2.5 : CLASS_PRICE[cls] ?? 1) * want * (farmed ? FARMED_PRICE : 1);
  let credit = 0, spent = 0;
  try { credit = Number(player.getDynamicProperty(CREDIT) ?? 0); } catch {}
  try { spent = Number(merchant.getDynamicProperty(SPENT) ?? 0); } catch {}
  const left = MERCHANT_BUDGET - spent;
  let n = stack.amount;
  while (n > 0 && Math.floor(credit + n * each) > left) n--;                 // only what his purse allows
  const room = orderRoom(merchant, player, id, cls, record);
  // a short purse does not stop his order: the fish it still asks for are taken as well, unpaid
  const bought = n;
  n = Math.max(bought, Math.min(stack.amount, room));
  if (n <= 0) { snd(merchant, "mob.wanderingtrader.no"); gesture(merchant, 2); return; }
  const total = credit + bought * each, paid = Math.floor(total);
  try { player.setDynamicProperty(CREDIT, Math.round((total - paid) * 1000) / 1000); } catch {}
  try { merchant.setDynamicProperty(SPENT, spent + paid); } catch {}
  let creative = false;
  try { creative = player.getGameMode() === GameMode.Creative; } catch {}
  if (!creative) { if (n >= stack.amount) slot.setItem(undefined); else { stack.amount -= n; slot.setItem(stack); } }
  if (paid > 0) {
    const em = new ItemStack("minecraft:emerald", paid);
    try { const rest = player.getComponent("minecraft:inventory")?.container?.addItem(em); if (rest) player.dimension.spawnItem(rest, player.location); }
    catch { try { player.dimension.spawnItem(em, player.location); } catch {} }
  }
  snd(merchant, "mob.wanderingtrader.yes");
  gesture(merchant, 1);
  emit("sold", player, { id, n, paid });
  fillOrder(merchant, player, Math.min(n, room));
  snd(player, paid > 0 ? "random.orb" : "random.pop", 1.2, 0.5);
  for (let i = 0; i < 3; i++) {
    try { spawnParticle(merchant.dimension, "minecraft:villager_happy", { x: merchant.location.x + (Math.random() - 0.5), y: merchant.location.y + 2, z: merchant.location.z + (Math.random() - 0.5) }); } catch {}
  }
}

world.beforeEvents.playerInteractWithEntity.subscribe(ev => {
  const { player, target, itemStack } = ev;
  if (target?.typeId !== MERCHANT || !itemStack) return;
  const id = FISH_ALIAS[itemStack.typeId] ?? itemStack.typeId;
  if (priceOf(id) === undefined) return;
  ev.cancel = true;                                      // no trading screen: he takes the fish
  system.run(() => { try { sell(player, target, id); } catch (err) { console.warn(`[Fishing Voyage] merchant sale: ${err}`); } });
});

// Opening his trading screen earns a bow as well.
try {
  world.afterEvents.playerInteractWithEntity.subscribe(ev => {
    if (ev.target?.typeId !== MERCHANT) return;
    try { gesture(ev.target, 1); } catch {}
  });
} catch {}
