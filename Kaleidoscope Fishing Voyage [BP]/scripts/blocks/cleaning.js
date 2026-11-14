// ## Fish Cleaning Board (魚案板): a whole fish is worked with a knife in three cuts.
//   1 scale  -> Fish Scales           (skipped for scaleless fish: eel, catfish, hairtail, saury,
//                                       anglerfish, octopus, pufferfish)
//   2 gut    -> Fish Offal, sometimes Fish Roe (octopus: Ink Sac)
//   3 fillet -> more fillets / sashimi than Cookery's chopping board, plus Fish Bones
// Any item tagged kaleidoscope_cookery:kitchen_knife counts as a knife. No text: the fish on
// the board changes (scales flaked off, belly opened) and each cut has its own sound.
// v1.3.3: a fish taken back before the first cut keeps its "★ N cm" (and a name tag): keep.js.
// v1.6.3 (F1): the record also keeps the fish and the cut, so a board removed in any way (player, explosion,
// piston, command: contents.js) gives back what is on it: the whole fish before the first cut, after that the
// fillets and bones the last cut would give (scales and offal were handed out by their own cuts).
// A board laid before 1.6.3 learns its fish on its next use; until then only the player-break and explosion
// paths (which still see the block) can give it back.
// v1.6.3 (F2): every refused use says why (util/hint.js).
// 1.4.0: not every catch is scaled, gutted and filleted. An entry may say where it starts (`first`: 3 = one cut,
// 2 = two cuts), what the gutting cut gives instead of Fish Offal (`gut`) and what the last cut gives besides its
// meat (`last`). Shrimp are peeled in one cut (meat + shells), crabs take two (shell and roe, then meat), a
// jellyfish is sliced in one.
import { EquipmentSlot, GameMode, ItemStack, system } from "@minecraft/server";
import { CLEANING, FISH_ALIAS } from "../data/generated.js";
import { LARGE, SMALL, applyClass, readSize } from "../fishing/size.js";
import { readFishIndex, withFishIndex } from "./fishState.js";
import { fishOut, keepKey, keepOf, stash, unstash } from "./keep.js";
import { readData, writeData } from "./blockData.js";
import { spawnParticle } from "../util/particles.js";
import { refuse } from "../util/hint.js";
import { registerRecords, registerStation, spawnAll } from "./contents.js";

const NS = "kaleidoscope_fishing";
const CUT = `${NS}:cut`, SIZE = `${NS}:size`;
// Size class of the fish on the board (0 none): a large fish gives one more fillet, a small one one less.
const yieldOf = (fish, cls) => Math.max(1, fish.out[1] + (cls === LARGE ? 1 : cls === SMALL ? -1 : 0));
const KNIFE_TAG = "kaleidoscope_cookery:kitchen_knife";
const BY_INDEX = Object.fromEntries(Object.entries(CLEANING).map(([id, c]) => [c.index, { id, ...c }]));
/** The cut a catch starts at: its own `first`, else 1 for a scaled fish and 2 for a scaleless one. */
const firstOf = fish => fish.first ?? (fish.scales ? 1 : 2);
const OFFAL = [[`${NS}:fish_offal`, 1]];

// v1.5.5: the size class lives in blockData ("cb": { size }); the size state is still written for 1.5.4 and
// read only for a board laid before 1.5.5 (copied over on its next use).
const sizeOf = (block, perm) => { const d = readData("cb", block.dimension, block); return d ? Number(d.size) || 0 : Number(perm.getState(SIZE) ?? 0); };
// v1.6.3: { size, idx, cut } - the fish and how far it is cut, for a board that is gone.
const saveBoard = (block, size, idx, cut) => writeData("cb", block.dimension, block, size === undefined ? undefined : { size, idx, cut });
const saveSize = (block, size) => saveBoard(block, size);
const creative = p => { try { const g = p.getGameMode(); return g === GameMode.Creative || g === "creative"; } catch { return false; } };
function give(player, block, id, n = 1, cls = 0, keep = undefined) {
  if (n <= 0) return;
  const stack = keep ? fishOut(new ItemStack(id, n), cls, keep) : applyClass(new ItemStack(id, n), cls);
  try {
    const left = player.getComponent("minecraft:inventory")?.container?.addItem(stack);
    if (left) block.dimension.spawnItem(left, block.center());
  } catch { try { block.dimension.spawnItem(stack, block.center()); } catch {} }
}
function wearKnife(player, slot) {
  if (creative(player)) return;
  try {
    const it = slot.getItem();
    const d = it?.getComponent("minecraft:durability");
    if (!d) return;
    if (d.damage + 1 >= d.maxDurability) {
      slot.setItem(undefined);
      try { player.playSound("random.break"); } catch {}
      return;
    }
    d.damage += 1; slot.setItem(it);
  } catch {}
}
function fx(block, sound, pitch, particle) {
  try { block.dimension.playSound(sound, block.center(), { pitch, volume: 0.8 }); } catch {}
  if (!particle) return;
  for (let i = 0; i < 5; i++) {
    try { spawnParticle(block.dimension, particle, { x: block.x + 0.3 + Math.random() * 0.4, y: block.y + 0.3, z: block.z + 0.3 + Math.random() * 0.4 }); } catch {}
  }
}

const cleaningBoard = {
  onPlayerInteract({ block, player }) {
    if (!player) return;
    const slot = player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
    const held = slot?.hasItem() ? slot.getItem() : undefined;
    const p = block.permutation;
    const idx = readFishIndex(p), cut = Number(p.getState(CUT) ?? 0), cls = sizeOf(block, p);
    const fish = BY_INDEX[idx];
    const key = keepKey("cb", block.dimension, block);
    const rec = readData("cb", block.dimension, block);
    if (fish && (!rec || rec.idx !== idx || rec.cut !== cut)) saveBoard(block, cls, idx, cut);   // 1.5.4 / pre-1.6.3 boards: fill the record

    if (!fish) {                                         // empty board: lay a fish down
      if (!held) return refuse(player, "board_need_fish");
      const c = CLEANING[FISH_ALIAS[held.typeId] ?? held.typeId];
      if (!c) {
        let knifeHeld = false;
        try { knifeHeld = held.hasTag(KNIFE_TAG); } catch {}
        return refuse(player, knifeHeld ? "board_need_fish" : "board_cannot_clean");
      }
      const size = readSize(held).cls;
      stash(key, keepOf(held));
      if (!creative(player)) { if (held.amount <= 1) slot.setItem(undefined); else { held.amount -= 1; slot.setItem(held); } }
      saveBoard(block, size, c.index, firstOf(c));
      block.setPermutation(withFishIndex(p, c.index).withState(CUT, firstOf(c)).withState(SIZE, size));
      fx(block, "mob.fish.flop", 1.0);
      return;
    }
    const first = firstOf(fish);
    if (!held) {                                         // changed your mind before the first cut
      if (cut === first) { give(player, block, fish.id, 1, cls, unstash(key)); saveSize(block, undefined); block.setPermutation(withFishIndex(p, 0).withState(CUT, 0).withState(SIZE, 0)); }
      else refuse(player, "board_finish_knife");
      return;
    }
    let knife = false;
    try { knife = held.hasTag(KNIFE_TAG); } catch {}
    if (!knife) return refuse(player, "board_need_knife");
    wearKnife(player, slot);
    if (cut === first) stash(key, undefined);            // once the knife is in, the fish is food: its record is let go
    if (cut === 1) {                                     // scale
      give(player, block, `${NS}:fish_scales`);
      saveBoard(block, cls, idx, 2);
      block.setPermutation(p.withState(CUT, 2));
      fx(block, "mob.sheep.shear", 1.4, "minecraft:basic_crit_particle");
    } else if (cut === 2) {                              // gut
      for (const [id, n] of fish.gut ?? OFFAL) give(player, block, id, n);
      for (const [id, chance] of fish.extra) if (Math.random() < chance) give(player, block, id);
      saveBoard(block, cls, idx, 3);
      block.setPermutation(p.withState(CUT, 3));
      fx(block, "mob.slime.small", 1.2);
    } else {                                             // fillet
      give(player, block, fish.out[0], yieldOf(fish, cls));
      give(player, block, `${NS}:fish_bones`, fish.bones);
      for (const [id, n] of fish.last ?? []) give(player, block, id, n);
      saveSize(block, undefined);
      block.setPermutation(withFishIndex(p, 0).withState(CUT, 0).withState(SIZE, 0));
      fx(block, "dig.wood", 1.3, "minecraft:basic_crit_particle");
    }
  },
  onPlayerBreak({ block, brokenBlockPermutation, player }) {
    if (creative(player)) { unstash(keepKey("cb", block.dimension, block)); saveSize(block, undefined); return; }
    dropBoard(block.dimension, block, brokenBlockPermutation);
  },
};

/** What a board holds: [id, n, cls, keep?] stacks to make. Exported for tests. */
export function boardContents(idx, cut, cls, keep) {
  const fish = BY_INDEX[idx];
  if (!fish) return [];
  if (cut === firstOf(fish) || !cut) return [[fish.id, 1, cls, keep]];
  return [[fish.out[0], yieldOf(fish, cls), 0], [`${NS}:fish_bones`, fish.bones, 0], ...(fish.last ?? []).map(([id, n]) => [id, n, 0])];
}
function dropBoard(dim, pos, perm) {
  const rec = readData("cb", dim, pos);
  const keep = unstash(keepKey("cb", dim, pos));
  writeData("cb", dim, pos, undefined);
  const idx = perm ? readFishIndex(perm) : Number(rec?.idx) || 0;
  const cut = perm ? Number(perm.getState(CUT) ?? 0) : Number(rec?.cut) || 0;
  const cls = Number(rec?.size ?? (perm ? perm.getState(SIZE) : 0) ?? 0) || 0;
  const stacks = [];
  for (const [id, n, c, k] of boardContents(idx, cut, cls, keep)) {
    if (n <= 0) continue;
    stacks.push(k ? fishOut(new ItemStack(id, n), c, k) : applyClass(new ItemStack(id, n), c));
  }
  spawnAll(dim, pos, stacks);
}
registerStation(`${NS}:fish_cleaning_board`, dropBoard);
registerRecords(`${NS}:bd:cb:`, `${NS}:fish_cleaning_board`, (dim, pos) => dropBoard(dim, pos, undefined));

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(`${NS}:fish_cleaning`, cleaningBoard);
});
