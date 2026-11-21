// ## Gutting Table (殺魚台, convenience phase 3). A whole stack of one catch is laid on the table; once a knife lies
// beside it, the table works through the stack on its own block tick, one fish a second: every cut the Fish
// Cleaning Board would make (tools/data/CLEANING.json via cleaning.js), each with the board's own sound and bits.
// The knife wears as it does on the board (a point per cut, Unbreaking honoured) and breaks the same way.
// What the cuts give drops into a chest or barrel right below (nextContainer.js); what does not fit waits on the
// table (the `done` bone shows it). No text: refusals go through util/hint.js.
//   use a stack of one catch  -> the whole stack goes on (same catch and size mark only, up to TABLE_MAX)
//   use a knife               -> it is laid on the table (taken from the hand, kept with its wear and enchantments)
//   use with an empty hand    -> the cut goods; then the knife; then the fish left
// A fish carrying more than its size mark (a record "★", a name) is refused: those go on the board, by hand.
// State: load 0..3 (how big the pile looks), knife 0/1, done 0/1. Everything else lives in one block record
// (blockData "gt": { id, n, cls, knife, out, p }), so the table gives it all back however it is removed
// (contents.js). Cost: a block tick every 20 ticks that reads two states and returns when there is no work.
import { EnchantmentTypes, EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { FISH_ALIAS } from "../data/generated.js";
import { applyClass, readSize } from "../fishing/size.js";
import { keepOf } from "./keep.js";
import { readData, writeData } from "./blockData.js";
import { refuseAt } from "../util/hint.js";
import { burst, on, sound } from "./stationFx.js";
import { registerRecords, registerStation, spawnAll } from "./contents.js";
import { emit } from "../api/host.js";
import { wears } from "../util/enchant.js";
import { ACT_FX, cutYield, entryFor, isKnife } from "./cleaning.js";
import { containerNext, putWhole } from "./nextContainer.js";

const NS = "kaleidoscope_fishing";
const TABLE = `${NS}:gutting_table`;
const LOAD = `${NS}:load`, KNIFE = `${NS}:knife`, DONE = `${NS}:done`;
/** Fish one table holds; ticks between the cuts of one fish (the sounds only: a fish a block tick). */
export const TABLE_MAX = 64, CUT_GAP = 5;

const creative = p => { try { const g = p.getGameMode(); return g === GameMode.Creative || g === "creative"; } catch { return false; } };
const mainhand = p => p.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
/** The table's record (a copy), never undefined. */
function load(block) {
  const r = readData("gt", block.dimension, block);
  const v = r ? JSON.parse(JSON.stringify(r)) : {};
  v.n = Number(v.n) || 0;
  v.out = v.out && typeof v.out === "object" ? v.out : {};
  return v;
}
const hasOut = r => Object.values(r.out ?? {}).some(n => n > 0);
function save(block, r) {
  writeData("gt", block.dimension, block, r.n > 0 || r.knife || hasOut(r) ? r : undefined);
}
/** How big the pile looks: 1 for a few fish, 2 up to 16, 3 beyond. Exported for tests. */
export const loadOf = n => (n <= 0 ? 0 : n <= 4 ? 1 : n <= 16 ? 2 : 3);
function show(block, r) {
  try {
    const p = block.permutation;
    const l = loadOf(r.n), k = r.knife ? 1 : 0, d = hasOut(r) ? 1 : 0;
    if (p.getState(LOAD) === l && p.getState(KNIFE) === k && p.getState(DONE) === d) return;
    block.setPermutation(p.withState(LOAD, l).withState(KNIFE, k).withState(DONE, d));
  } catch {}
}

// ------------------------------------------------------------------ the knife, kept in the record
/** What a knife item is: id, wear, enchantments, name and lore. */
function packKnife(it, cr) {
  const k = { id: it.typeId };
  try { const d = it.getComponent("minecraft:durability"); if (d) { k.dmg = d.damage; k.max = d.maxDurability; } } catch {}
  try {
    const e = it.getComponent("minecraft:enchantable")?.getEnchantments() ?? [];
    if (e.length) k.ench = e.map(x => [String(x.type?.id ?? x.type), Number(x.level) || 1]);
  } catch {}
  try { if (it.nameTag) k.name = String(it.nameTag); } catch {}
  try { const l = it.getLore(); if (l?.length) k.lore = l; } catch {}
  if (cr) k.cr = true;                                   // laid by a creative player: it does not wear
  return k;
}
function unpackKnife(k) {
  let s;
  try { s = new ItemStack(k.id, 1); } catch { return undefined; }   // a knife from a pack that is gone
  try { const d = s.getComponent("minecraft:durability"); if (d && k.dmg > 0) d.damage = Math.min(k.dmg, d.maxDurability - 1); } catch {}
  try {
    const en = s.getComponent("minecraft:enchantable");
    for (const [id, level] of k.ench ?? []) { try { en?.addEnchantment({ type: EnchantmentTypes.get(id), level }); } catch {} }
  } catch {}
  try { if (k.name) s.nameTag = k.name; } catch {}
  try { if (k.lore?.length) s.setLore(k.lore); } catch {}
  return s;
}
const unbreaking = k => (k.ench ?? []).reduce((a, [id, lvl]) => (String(id).replace(/^minecraft:/, "") === "unbreaking" ? lvl : a), 0);
/** Wear the knife for `cuts` cuts, as the board does (a point per cut, Unbreaking may spare it). True if it broke. */
export function wearTableKnife(k, cuts, rand = Math.random) {
  if (!k || k.cr || !(k.max > 0)) return false;
  const lvl = unbreaking(k);
  for (let i = 0; i < cuts; i++) if (wears(lvl, rand)) k.dmg = (k.dmg ?? 0) + 1;
  return k.dmg >= k.max;
}

// ------------------------------------------------------------------ giving things out
/** Stacks of `n` of an item, at most a full stack each; `cls` marks fish with their size. */
function stacksOf(id, n, cls = 0) {
  const out = [];
  let max = 64;
  try { max = new ItemStack(id, 1).maxAmount || 64; } catch { return out; }
  for (let left = n; left > 0; left -= max) {
    const s = new ItemStack(id, Math.min(max, left));
    out.push(cls ? applyClass(s, cls) : s);
  }
  return out;
}
function give(player, block, stacks) {
  for (const s of stacks) {
    if (!s) continue;
    try {
      const left = player.getComponent("minecraft:inventory")?.container?.addItem(s);
      if (left) block.dimension.spawnItem(left, block.center());
    } catch { try { block.dimension.spawnItem(s, block.center()); } catch {} }
  }
}
/** Everything a record holds, as item stacks (cut goods, knife, fish). */
function contents(r) {
  const out = [];
  for (const [id, n] of Object.entries(r.out ?? {})) if (n > 0) out.push(...stacksOf(id, n));
  if (r.knife) out.push(unpackKnife(r.knife));
  if (r.n > 0 && r.id) out.push(...stacksOf(r.id, r.n, r.cls));
  return out.filter(Boolean);
}

// ------------------------------------------------------------------ effects
const top = block => on(block, 0.5, 0.75, 0.5);
function cutFx(dim, at, act) {
  const [snd, pitch, effects, layer] = ACT_FX[act] ?? ACT_FX.fillet;
  sound(dim, snd, at, pitch, 0.8);
  if (layer) sound(dim, layer[0], at, layer[1], layer[2]);
  for (const e of effects ?? []) burst(dim, { x: at.x + (Math.random() - 0.5) * 0.4, y: at.y, z: at.z + (Math.random() - 0.5) * 0.3 }, e);
}

// ------------------------------------------------------------------ one fish
/** Cut the next fish on the table: its outputs below or onto the table, the knife worn. True if a fish was cut. */
export function cutOne(block) {
  const r = load(block);
  if (!(r.n > 0) || !r.knife) { show(block, r); return false; }
  const fish = entryFor(r.id);
  if (!fish?.cuts?.length) return false;                // another pack's catch whose pack is not loaded (yet)
  const id = r.id;
  const box = containerNext(block, ["below"]);
  const yields = [];
  for (const cut of fish.cuts) yields.push(...cutYield(cut, r.cls ?? 0));
  r.n -= 1;
  for (const [out, n] of yields) {
    let into = false;
    try { into = !!box && putWhole(box, new ItemStack(out, n)); } catch { continue; }   // an output whose pack is gone
    if (!into) r.out[out] = (r.out[out] ?? 0) + n;
  }
  const broke = wearTableKnife(r.knife, fish.cuts.length);
  if (broke) r.knife = undefined;
  if (r.n <= 0) { delete r.id; delete r.cls; r.n = 0; }
  save(block, r);
  show(block, r);
  const dim = block.dimension, at = top(block);
  fish.cuts.forEach((cut, i) => {
    if (!i) cutFx(dim, at, cut.act);
    else system.runTimeout(() => { try { cutFx(dim, at, cut.act); } catch {} }, i * CUT_GAP);
  });
  if (broke) sound(dim, "random.break", at, 1.0, 0.8);
  let player;
  try { player = r.p ? world.getEntity(r.p) : undefined; } catch {}
  emit("cleaned", player, { id });
  return true;
}

/** Cut goods waiting on the table go into the container below once it has room. */
function flushOut(block) {
  const r = load(block);
  if (!hasOut(r)) return;
  const box = containerNext(block, ["below"]);
  if (!box) return;
  let moved = false;
  for (const [id, n] of Object.entries(r.out)) {
    if (!(n > 0)) { delete r.out[id]; continue; }
    const stacks = stacksOf(id, n);
    let left = n;
    for (const s of stacks) { if (!putWhole(box, s)) break; left -= s.amount; moved = true; }
    if (left > 0) r.out[id] = left; else delete r.out[id];
  }
  if (!moved) return;
  save(block, r);
  show(block, r);
  sound(block.dimension, "random.pop", top(block), 0.8, 0.3);
}

// ------------------------------------------------------------------ the component
const gutting = {
  onPlayerInteract({ block, player }) {
    if (!player) return;
    const slot = mainhand(player);
    const held = slot?.hasItem() ? slot.getItem() : undefined;
    const r = load(block);
    const dim = block.dimension, at = top(block);

    if (held && isKnife(held)) {                          // lay the knife down
      if (r.knife) return refuseAt(player, "table_has_knife", block);
      r.knife = packKnife(held, creative(player));
      try { r.p = player.id; } catch {}
      slot.setItem(undefined);
      save(block, r); show(block, r);
      sound(dim, "armor.equip_iron", at, 1.5, 0.7);
      sound(dim, "hit.wood", at, 1.6, 0.4);
      return;
    }
    if (held) {                                           // lay a stack of fish down
      const fish = entryFor(held.typeId);
      if (!fish) return refuseAt(player, "board_cannot_clean", block);
      if (!fish.cuts?.length) return refuseAt(player, "board_pack_gone", block);
      if (keepOf(held)) return refuseAt(player, "table_trophy", block);
      const id = fish.ext ? held.typeId : (FISH_ALIAS[held.typeId] ?? held.typeId);
      const cls = readSize(held).cls;
      if (r.n > 0 && (r.id !== id || (r.cls ?? 0) !== cls)) return refuseAt(player, "table_other_catch", block);
      const take = Math.min(TABLE_MAX - r.n, held.amount);
      if (take <= 0) return refuseAt(player, "table_full", block);
      if (!creative(player)) {
        if (take >= held.amount) slot.setItem(undefined);
        else { held.amount -= take; slot.setItem(held); }
      }
      r.id = id; r.cls = cls; r.n += take;
      try { r.p = r.p ?? player.id; } catch {}
      save(block, r); show(block, r);
      sound(dim, "mob.fish.flop", at, 1.0, 0.8);
      if (take > 8) sound(dim, "mob.fish.flop", at, 0.8, 0.6);
      burst(dim, at, "drip");
      return;
    }
    // an empty hand: the cut goods, then the knife, then the fish
    if (hasOut(r)) {
      give(player, block, Object.entries(r.out).flatMap(([id, n]) => (n > 0 ? stacksOf(id, n) : [])));
      r.out = {};
      save(block, r); show(block, r);
      sound(dim, "random.pop", at, 0.9, 0.7);
      return;
    }
    if (r.knife) {
      give(player, block, [unpackKnife(r.knife)]);
      r.knife = undefined;
      save(block, r); show(block, r);
      sound(dim, "armor.equip_iron", at, 1.1, 0.6);
      return;
    }
    if (r.n > 0) {
      give(player, block, stacksOf(r.id, r.n, r.cls));
      r.n = 0; delete r.id; delete r.cls;
      save(block, r); show(block, r);
      sound(dim, "mob.fish.flop", at, 1.2, 0.7);
      return;
    }
    refuseAt(player, "board_need_fish", block);
  },

  onTick({ block }) {
    const p = block.permutation;
    if (p.getState(DONE)) flushOut(block);
    if (!p.getState(LOAD) || !p.getState(KNIFE)) return;
    cutOne(block);
  },

  onPlayerBreak({ block, brokenBlockPermutation, player }) {
    if (player && creative(player)) { writeData("gt", block.dimension, block, undefined); return; }
    dropTable(block.dimension, block, brokenBlockPermutation);
  },
};

function dropTable(dim, pos) {
  const r = readData("gt", dim, pos);
  writeData("gt", dim, pos, undefined);
  if (r) spawnAll(dim, pos, contents({ ...r, n: Number(r.n) || 0 }));
}
registerStation(TABLE, dropTable);
registerRecords(`${NS}:bd:gt:`, TABLE, (dim, pos) => dropTable(dim, pos));

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(TABLE, gutting);
});
