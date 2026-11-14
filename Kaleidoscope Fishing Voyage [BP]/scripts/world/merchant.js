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
import { FISH_ALIAS, MERCHANT_BUDGET, MERCHANT_PRICES, WANT_LIST } from "../data/generated.js";
import { LARGE, MEDIUM, SMALL, readSize } from "../fishing/size.js";
import { spawnParticle } from "../util/particles.js";

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
  try { const m = p.dimension.spawnEntity(MERCHANT, at); setWants(m); bell(p.dimension, at, 0.8); } catch {}
}

system.runInterval(() => { try { check(); } catch (err) { console.warn(`[Fishing Voyage] merchant: ${err}`); } }, CHECK);
// his hand bell as he walks
system.runInterval(() => {
  for (const m of merchants()) if (Math.random() < 0.5) bell(m.dimension, m.location, 0.45);
}, 400);

// --------------------------------------------------------------- the day's wants (v1.4)
// Two fish from WANT_LIST, paid double. Both hang from his carrying pole for everyone to see.
const WANTS = `${NS}:wants`;
const WANT_BONUS = 2;
const pick3 = () => { const a = [...WANT_LIST]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a.slice(0, 2); };
function setWants(m) {
  const w = pick3();
  try { m.setDynamicProperty(WANTS, JSON.stringify(w)); } catch {}
  try { m.setProperty(`${NS}:want_a`, WANT_LIST.indexOf(w[0]) + 1); m.setProperty(`${NS}:want_b`, WANT_LIST.indexOf(w[1]) + 1); } catch {}
  return w;
}
function wantsOf(m) {
  try { const v = JSON.parse(m.getDynamicProperty(WANTS) ?? "null"); if (Array.isArray(v) && v.length) return v; } catch {}
  return setWants(m);                       // a merchant from 1.3.x gets his wants the first time he is asked
}
/** What the nearest merchant wants, for the journal; undefined if none is about. */
export function wantsNear(player) {
  let near;
  try { near = player.dimension.getEntities({ type: MERCHANT, location: player.location, maxDistance: 96, closest: 1 })[0]; } catch {}
  if (!near) return undefined;
  return wantsOf(near).slice(0, 2);
}

// --------------------------------------------------------------- he buys fish
const CLASS_PRICE = { 0: 1, [SMALL]: 0.6, [MEDIUM]: 1, [LARGE]: 1.6 };
const CREDIT = `${NS}:merchant_credit`, SPENT = `${NS}:spent`;
const snd = (e, id, pitch = 1, volume = 0.8) => { try { e.dimension.playSound(id, e.location, { pitch, volume }); } catch {} };

function sell(player, merchant, id) {
  const slot = player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
  const stack = slot?.hasItem() ? slot.getItem() : undefined;
  if (!stack || (FISH_ALIAS[stack.typeId] ?? stack.typeId) !== id) return;
  const { cls, record } = readSize(stack);
  const want = wantsOf(merchant).slice(0, 2).includes(id) ? WANT_BONUS : 1;
  const each = MERCHANT_PRICES[id] * (record ? 2.5 : CLASS_PRICE[cls] ?? 1) * want;
  let credit = 0, spent = 0;
  try { credit = Number(player.getDynamicProperty(CREDIT) ?? 0); } catch {}
  try { spent = Number(merchant.getDynamicProperty(SPENT) ?? 0); } catch {}
  const left = MERCHANT_BUDGET - spent;
  let n = stack.amount;
  while (n > 0 && Math.floor(credit + n * each) > left) n--;                 // only what his purse allows
  if (n <= 0) { snd(merchant, "mob.wanderingtrader.no"); return; }
  const total = credit + n * each, paid = Math.floor(total);
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
  snd(player, paid > 0 ? "random.orb" : "random.pop", 1.2, 0.5);
  for (let i = 0; i < 3; i++) {
    try { spawnParticle(merchant.dimension, "minecraft:villager_happy", { x: merchant.location.x + (Math.random() - 0.5), y: merchant.location.y + 2, z: merchant.location.z + (Math.random() - 0.5) }); } catch {}
  }
}

world.beforeEvents.playerInteractWithEntity.subscribe(ev => {
  const { player, target, itemStack } = ev;
  if (target?.typeId !== MERCHANT || !itemStack) return;
  const id = FISH_ALIAS[itemStack.typeId] ?? itemStack.typeId;
  if (MERCHANT_PRICES[id] === undefined) return;
  ev.cancel = true;                                      // no trading screen: he takes the fish
  system.run(() => { try { sell(player, target, id); } catch (err) { console.warn(`[Fishing Voyage] merchant sale: ${err}`); } });
});
