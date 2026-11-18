// ## Wooden Tub (木盆, 1.5.0). A tub of water does two things, one at a time:
//   purging clams   water + Salt makes brine; up to 8 Clams soak in it; after half a day an empty hand takes
//                   out Purged Clams (the brine stays for the next batch)
//   hatching roe    (with the fish pond) Fertilized Roe in plain water: fry after a day, and after two an empty
//                   hand takes out 2 small farmed fish of its kind (blocks/pond.js); 1.6.0: so does the Hand Net
//                   (tools/handNet.js), at the cost of one use
// A water bucket fills it, an empty bucket drains it. The state `fill` is what shows:
//   0 empty  1 water  2 brine  3 clams soaking  4 clams purged  5 roe  6 fry
// What it holds is kept in a block record ("tb": { n, t }), so a tub removed in any way gives its clams back.
import { EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { readData, writeData } from "./blockData.js";
import { registerRecords, registerStation, spawnAll } from "./contents.js";
import { refuseAt } from "../util/hint.js";
import { ambient, burst, on } from "./stationFx.js";
import { CATCHES } from "../data/generated.js";
import { fishGlyph } from "../data/glyphs.js";
import { HAND_NET, wearNet } from "../tools/handNet.js";
const SIZED = new Set(CATCHES.filter(c => c.size).map(c => c.id));

const NS = "kaleidoscope_fishing";
const BLOCK = `${NS}:wooden_tub`, FILL = `${NS}:fill`;
const CLAM = `${NS}:clam`, PURGED = `${NS}:purged_clam`, SALT = `${NS}:sea_salt`;
export const TUB_CLAMS = 8;
export const PURGE_TICKS = 12000;                       // half a day
export const HATCH_TICKS = 48000;                       // 1.5.0: two days for roe to hatch (fry show after one)
const ROE_ITEM = `${NS}:fertilized_roe`, ROE_PROP = "kfv:roe";
const now = () => { try { return world.getAbsoluteTime(); } catch { return system.currentTick; } };
const creative = p => { try { return p.getGameMode() === GameMode.Creative; } catch { return false; } };
const snd = (block, id, pitch = 1, volume = 0.7) => { try { block.dimension.playSound(id, block.center(), { pitch, volume }); } catch {} };
const fillOf = block => Number(block.permutation.getState(FILL) ?? 0);
const setFill = (block, f) => { try { block.setPermutation(block.permutation.withState(FILL, f)); } catch {} };
const rec = block => readData("tb", block.dimension, block) ?? {};
const save = (block, v) => writeData("tb", block.dimension, block, v);
// 1.5.0 (immersive pass): what the tub is doing shows on its water (stationFx.js). The surface sits ~5/16 up.
const surface = block => on(block, 0.5, 0.32, 0.5);
const fx = (block, ...names) => burst(block.dimension, surface(block), ...names);

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
  if ((fill === 5 || fill === 6) && typeof r?.roe === "string") return [{ roe: r.roe }];
  return [];
}
function roeBack(id) {
  const s = new ItemStack(ROE_ITEM, 1);
  try { s.setDynamicProperty(ROE_PROP, id); } catch {}
  try { s.setLore([`§r${fishGlyph(id)}`]); } catch {}   // 1.6.0: the fish's picture, no words (the species is ROE_PROP)
  return s;
}
/** Two small farmed fish of a kind, hatched in the tub. */
function fry(id) {
  const s = new ItemStack(id, 2);
  try { s.setLore([...(SIZED.has(id) ? ["§7◆"] : []), "§2✿"]); } catch {}
  return s;
}
function dropTub(dim, pos, perm) {
  const fill = perm ? Number(perm.getState(FILL) ?? 0) : Number(readData("tb", dim, pos)?.fill) || 0;
  const items = tubContents(fill, readData("tb", dim, pos));
  writeData("tb", dim, pos, undefined);
  spawnAll(dim, pos, items.map(id => (typeof id === "string" ? new ItemStack(id, 1) : roeBack(id.roe))));
}

const tub = {
  onPlayerInteract({ block, player }) {
    if (!player) return;
    const slot = slotOf(player);
    const held = slot?.hasItem() ? slot.typeId : undefined;
    const fill = fillOf(block);
    const r = rec(block);
    if (held === "minecraft:water_bucket") {
      if (fill !== 0) return refuseAt(player, "tub_full", block);
      swapHeld(player, slot, "minecraft:bucket"); setFill(block, 1); snd(block, "bucket.empty_water"); snd(block, "random.splash", 1.6, 0.25); fx(block, "spray", "bubbles"); return;
    }
    if (held === "minecraft:bucket") {
      if (fill !== 1 && fill !== 2) return refuseAt(player, "tub_busy", block);
      swapHeld(player, slot, "minecraft:water_bucket"); setFill(block, 0); save(block, undefined); snd(block, "bucket.fill_water"); fx(block, "drip"); return;
    }
    if (held === SALT) {
      if (fill !== 1) return refuseAt(player, fill === 0 ? "tub_need_water" : "tub_salted", block);
      takeOne(player, slot); setFill(block, 2); snd(block, "dig.sand", 1.3); snd(block, "random.swim", 1.6, 0.25); fx(block, "salt", "stir"); return;
    }
    if (held === CLAM) {
      if (fill !== 2 && fill !== 3) return refuseAt(player, fill === 1 ? "tub_need_salt" : "tub_need_water", block);
      const n = (fill === 3 ? Number(r.n) || 0 : 0) + 1;
      if (n > TUB_CLAMS) return refuseAt(player, "tub_clams_full", block, TUB_CLAMS);
      takeOne(player, slot);
      save(block, { n, t: now(), fill: 3 });                // the half day runs from the last clam in
      setFill(block, 3); snd(block, "random.splash", 1.5, 0.4); fx(block, "bubbles"); return;
    }
    if (!held && fill === 4) {
      const n = Number(r.n) || 0;
      for (let i = 0; i < n; i++) give(player, new ItemStack(PURGED, 1), block.center());
      save(block, undefined); setFill(block, 2); snd(block, "random.splash", 1.2, 0.5); fx(block, "drip", "spray"); return;
    }
    if (held === ROE_ITEM) {                              // 1.5.0: fertilized roe hatches in plain water
      if (fill !== 1) return refuseAt(player, fill === 0 ? "tub_need_water" : "tub_busy", block);
      let id;
      try { id = slot.getItem().getDynamicProperty(ROE_PROP); } catch {}
      if (typeof id !== "string") return refuseAt(player, "tub_what", block);
      takeOne(player, slot);
      save(block, { roe: id, t: now(), fill: 5 });
      setFill(block, 5); snd(block, "random.splash", 1.6, 0.4); fx(block, "fry"); return;
    }
    if ((!held || held === HAND_NET) && (fill === 5 || fill === 6)) {
      if (now() - (Number(r.t) || now()) < HATCH_TICKS || typeof r.roe !== "string") return refuseAt(player, "tub_hatching", block);
      give(player, fry(r.roe), block.center());
      save(block, undefined); setFill(block, 1); snd(block, "random.splash", 1.2, 0.6); fx(block, "spray", "drip");
      if (held === HAND_NET) wearNet(player);
      return;
    }
    if (!held && fill === 3) return refuseAt(player, "tub_soaking", block);
    refuseAt(player, "tub_what", block);
  },
  onTick({ block }) {
    if (fillOf(block) === 5) {                            // the roe turns to fry halfway
      const r = rec(block);
      if (typeof r.t === "number" && now() - r.t >= HATCH_TICKS / 2) { save(block, { ...r, fill: 6 }); setFill(block, 6); }
      ambient(block, "tub", 90, surface(block), () => fx(block, "fry"));   // tiny bubbles off the roe
      return;
    }
    if (fillOf(block) === 6) {                            // fry darting: bubbles and now and then a flick at the top
      ambient(block, "tub", 90, surface(block), () => { fx(block, "fry"); if (Math.random() < 0.35) { fx(block, "drip"); snd(block, "random.swim", 1.9, 0.15); } });
      return;
    }
    if (fillOf(block) !== 3) return;
    const r = rec(block);
    if (typeof r.t !== "number") { save(block, { ...r, t: now(), fill: 3 }); return; }
    if (now() - r.t >= PURGE_TICKS) { save(block, { ...r, fill: 4 }); setFill(block, 4); snd(block, "bubble.pop", 1.2, 0.4); fx(block, "bubbles"); }
    else ambient(block, "tub", 90, surface(block), () => {   // the clams breathing: bubbles, and puffs of sand spat out
      fx(block, "purge", "sand");
      if (Math.random() < 0.25) snd(block, "bubble.pop", 1.5, 0.2);
    });
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
