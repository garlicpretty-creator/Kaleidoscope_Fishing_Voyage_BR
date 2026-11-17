// ## Wooden Tub (木盆, 1.5.0). A tub of water does two things, one at a time:
//   purging clams   water + Salt makes brine; up to 8 Clams soak in it; after half a day an empty hand takes
//                   out Purged Clams (the brine stays for the next batch)
//   hatching roe    (with the fish pond) Fertilized Roe in plain water hatches into small fish
// A water bucket fills it, an empty bucket drains it. The state `fill` is what shows:
//   0 empty  1 water  2 brine  3 clams soaking  4 clams purged  5 roe  6 fry
// What it holds is kept in a block record ("tb": { n, t }), so a tub removed in any way gives its clams back.
import { EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { readData, writeData } from "./blockData.js";
import { registerRecords, registerStation, spawnAll } from "./contents.js";
import { refuse } from "../util/hint.js";
import { spawnParticle } from "../util/particles.js";

const NS = "kaleidoscope_fishing";
const BLOCK = `${NS}:wooden_tub`, FILL = `${NS}:fill`;
const CLAM = `${NS}:clam`, PURGED = `${NS}:purged_clam`, SALT = `${NS}:sea_salt`;
export const TUB_CLAMS = 8;
export const PURGE_TICKS = 12000;                       // half a day
const now = () => { try { return world.getAbsoluteTime(); } catch { return system.currentTick; } };
const creative = p => { try { return p.getGameMode() === GameMode.Creative; } catch { return false; } };
const snd = (block, id, pitch = 1, volume = 0.7) => { try { block.dimension.playSound(id, block.center(), { pitch, volume }); } catch {} };
const fillOf = block => Number(block.permutation.getState(FILL) ?? 0);
const setFill = (block, f) => { try { block.setPermutation(block.permutation.withState(FILL, f)); } catch {} };
const rec = block => readData("tb", block.dimension, block) ?? {};
const save = (block, v) => writeData("tb", block.dimension, block, v);

function slotOf(player) {
  try { return player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand); } catch { return undefined; }
}
function takeOne(player, slot) {
  if (creative(player)) return;
  const it = slot.getItem(); if (!it) return;
  if (it.amount <= 1) slot.setItem(undefined); else { it.amount -= 1; slot.setItem(it); }
}
function swapHeld(player, slot, id) {
  if (creative(player)) return;
  const it = slot.getItem();
  if (it && it.amount > 1) {
    it.amount -= 1; slot.setItem(it);
    give(player, new ItemStack(id, 1), player.location);
  } else slot.setItem(new ItemStack(id, 1));
}
function give(player, stack, at) {
  try { const left = player.getComponent("minecraft:inventory")?.container?.addItem(stack); if (left) player.dimension.spawnItem(left, at); }
  catch { try { player.dimension.spawnItem(stack, at); } catch {} }
}

/** What a tub holds as items (for a tub that is removed). Exported for tests. */
export function tubContents(fill, r) {
  const n = Number(r?.n) || 0;
  if (fill === 3) return Array(n).fill(CLAM);
  if (fill === 4) return Array(n).fill(PURGED);
  return [];
}
function dropTub(dim, pos, perm) {
  const fill = perm ? Number(perm.getState(FILL) ?? 0) : Number(readData("tb", dim, pos)?.fill) || 0;
  const items = tubContents(fill, readData("tb", dim, pos));
  writeData("tb", dim, pos, undefined);
  spawnAll(dim, pos, items.map(id => new ItemStack(id, 1)));
}

const tub = {
  onPlayerInteract({ block, player }) {
    if (!player) return;
    const slot = slotOf(player);
    const held = slot?.hasItem() ? slot.typeId : undefined;
    const fill = fillOf(block);
    const r = rec(block);
    if (held === "minecraft:water_bucket") {
      if (fill !== 0) return refuse(player, "tub_full");
      swapHeld(player, slot, "minecraft:bucket"); setFill(block, 1); snd(block, "bucket.empty_water"); return;
    }
    if (held === "minecraft:bucket") {
      if (fill !== 1 && fill !== 2) return refuse(player, "tub_busy");
      swapHeld(player, slot, "minecraft:water_bucket"); setFill(block, 0); save(block, undefined); snd(block, "bucket.fill_water"); return;
    }
    if (held === SALT) {
      if (fill !== 1) return refuse(player, fill === 0 ? "tub_need_water" : "tub_salted");
      takeOne(player, slot); setFill(block, 2); snd(block, "dig.sand", 1.3); return;
    }
    if (held === CLAM) {
      if (fill !== 2 && fill !== 3) return refuse(player, fill === 1 ? "tub_need_salt" : "tub_need_water");
      const n = (fill === 3 ? Number(r.n) || 0 : 0) + 1;
      if (n > TUB_CLAMS) return refuse(player, "tub_clams_full", TUB_CLAMS);
      takeOne(player, slot);
      save(block, { n, t: now(), fill: 3 });                // the half day runs from the last clam in
      setFill(block, 3); snd(block, "random.splash", 1.5, 0.4); return;
    }
    if (!held && fill === 4) {
      const n = Number(r.n) || 0;
      for (let i = 0; i < n; i++) give(player, new ItemStack(PURGED, 1), block.center());
      save(block, undefined); setFill(block, 2); snd(block, "random.splash", 1.2, 0.5); return;
    }
    if (!held && fill === 3) return refuse(player, "tub_soaking");
    refuse(player, "tub_what");
  },
  onTick({ block }) {
    if (fillOf(block) !== 3) return;
    const r = rec(block);
    if (typeof r.t !== "number") { save(block, { ...r, t: now(), fill: 3 }); return; }
    if (now() - r.t >= PURGE_TICKS) { save(block, { ...r, fill: 4 }); setFill(block, 4); snd(block, "bubble.pop", 1.2, 0.4); }
    else if (Math.random() < 0.3) { try { spawnParticle(block.dimension, "minecraft:basic_bubble_particle", { x: block.x + 0.3 + Math.random() * 0.4, y: block.y + 0.35, z: block.z + 0.3 + Math.random() * 0.4 }); } catch {} }
  },
  onPlayerBreak({ block, brokenBlockPermutation, player }) {
    if (player && creative(player)) { save(block, undefined); return; }
    dropTub(block.dimension, block, brokenBlockPermutation);
  },
};

registerStation(BLOCK, dropTub);
registerRecords(`${NS}:bd:tb:`, BLOCK, (dim, pos) => dropTub(dim, pos, undefined));

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(BLOCK, tub);
});
