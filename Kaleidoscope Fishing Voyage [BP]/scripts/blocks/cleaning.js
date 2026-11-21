// ## Fish Cleaning Board (魚案板): a whole catch is worked with a knife, one cut at a time.
// 1.5.0: every catch lists its own cuts (tools/data/CLEANING.json: "first" stage and "cuts"). A fish is still
// scaled, gutted and filleted (a scaleless one starts at the gut); shrimp, crab, squid and the rest list theirs.
// The board's `cut` state is the stage on show: laid down at `first`, one stage on per cut, cleared by the last.
// Any item tagged kaleidoscope_cookery:kitchen_knife counts as a knife. No text: the fish on
// the board changes (scales flaked off, belly opened) and each cut has its own sound.
// v1.3.3: a fish taken back before the first cut keeps its "★ N cm" (and a name tag): keep.js.
// v1.6.3 (F1): the record also keeps the fish and the cut, so a board removed in any way (player, explosion,
// piston, command: contents.js) gives back what is on it: the whole fish before the first cut, after that the
// fillets and bones the last cut would give (scales and offal were handed out by their own cuts).
// A board laid before 1.6.3 learns its fish on its next use; until then only the player-break and explosion
// paths (which still see the block) can give it back.
// v1.6.3 (F2): every refused use says why (util/hint.js).
// 1.7.0 (phase 1): sneak-use with a knife runs every cut left, and more of the same catch after it (cleanAll).
// Phase 3: the Gutting Table (guttingTable.js) cuts with the same table (entryFor, cutYield, ACT_FX, isKnife).
import { EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { CLEANING, FISH_ALIAS } from "../data/generated.js";
import { LARGE, SMALL, applyClass, readSize } from "../fishing/size.js";
import { readFishIndex, withFishIndex } from "./fishState.js";
import { fishOut, keepKey, keepOf, stash, unstash } from "./keep.js";
import { readData, writeData } from "./blockData.js";
import { refuseAt } from "../util/hint.js";
import { burst, on, sound } from "./stationFx.js";
import { registerRecords, registerStation, spawnAll } from "./contents.js";
import { emit } from "../api/host.js";
import { enchantLevel, wears } from "../util/enchant.js";
import { externalBoard } from "../fishing/registry.js";

const NS = "kaleidoscope_fishing";
const CUT = `${NS}:cut`, SIZE = `${NS}:size`;
// What one cut gives. An output marked "sized" grows by one for a large catch and shrinks by one for a small one.
const countOf = (row, cls) => (row[3] === "sized" ? Math.max(1, row[1] + (cls === LARGE ? 1 : cls === SMALL ? -1 : 0)) : row[1]);
/** The stacks a cut gives: [id, n], chance outputs rolled with `rand`. Exported for tests. */
export function cutYield(cut, cls, rand = Math.random) {
  const out = [];
  for (const row of cut.out) if ((row[2] ?? 1) >= 1 || rand() < row[2]) out.push([row[0], countOf(row, cls)]);
  return out;
}
// The sound and particles of each kind of cut: [sound, pitch, [station effects], [second sound, pitch, volume]?].
// 1.5.0 (immersive pass): scales flick off silver, gutting splats red, a fillet thunks into the board with wood chips.
export const ACT_FX = {
  scale: ["mob.sheep.shear", 1.4, ["scales"], ["dig.sand", 2.0, 0.25]], gut: ["mob.slime.small", 1.2, ["gut"], ["random.splash", 1.9, 0.12]],
  fillet: ["dig.wood", 1.3, ["chips"], ["hit.wood", 1.6, 0.4]], head: ["mob.turtle.baby.step", 1.1, ["chips", "gut"], ["hit.wood", 1.2, 0.45]],
  shell: ["random.break", 1.6, ["shell"]], devein: ["mob.slime.small", 1.5, ["gut"]], open: ["random.break", 1.2, ["shell", "drip"]],
  legs: ["dig.wood", 1.6, ["shell"]], tentacle: ["mob.slime.small", 0.9, ["ink"], ["random.splash", 1.7, 0.12]], bone: ["dig.wood", 0.9, ["chips"]],
  rub: ["dig.sand", 1.4, ["shell", "salt"]],
};
const KNIFE_TAG = "kaleidoscope_cookery:kitchen_knife";
export const isKnife = it => { try { return !!it?.hasTag(KNIFE_TAG); } catch { return false; } };
const BY_INDEX = Object.fromEntries(Object.entries(CLEANING).map(([id, c]) => [c.index, { id, ...c }]));
// 1.5.0 (register_board): another pack's fish is drawn as its `like` (the board index), cut with its own outputs.
// The board record keeps its item id ("ext"); while that pack has not registered it (yet), its cuts are unknown.
/** The board entry for what lies on a board: ours by index, or another pack's by the record's ext. */
function fishOn(idx, rec) {
  const base = BY_INDEX[idx];
  if (!base || !rec?.ext) return base;
  const e = externalBoard(rec.ext);
  return { ...base, id: rec.ext, ext: rec.ext, cuts: e?.cuts, gutted: undefined };
}
/** The board entry for a held item: ours, or a registered one. Phase 3: the Gutting Table uses it too. */
export function entryFor(id) {
  const ours = CLEANING[FISH_ALIAS[id] ?? id];
  if (ours) return ours;
  const e = externalBoard(id);
  return e && CLEANING[e.like] ? { ...CLEANING[e.like], cuts: e.cuts, ext: id } : undefined;
}

// v1.5.5: the size class lives in blockData ("cb": { size }); the size state is still written for 1.5.4 and
// read only for a board laid before 1.5.5 (copied over on its next use).
const sizeOf = (block, perm) => { const d = readData("cb", block.dimension, block); return d ? Number(d.size) || 0 : Number(perm.getState(SIZE) ?? 0); };
// v1.6.3: { size, idx, cut } - the fish and how far it is cut, for a board that is gone.
const saveBoard = (block, size, idx, cut, ext) => writeData("cb", block.dimension, block, size === undefined ? undefined : { size, idx, cut, ...(ext ? { ext } : {}) });
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
    if (!wears(enchantLevel(it, "unbreaking"))) return;      // 1.5.0: Unbreaking spares the knife here as it does in a fight
    if (d.damage + 1 >= d.maxDurability) {
      slot.setItem(undefined);
      try { player.playSound("random.break"); } catch {}
      return;
    }
    d.damage += 1; slot.setItem(it);
  } catch {}
}
function fx(block, snd, pitch, effects, layer) {
  const at = on(block, 0.5, 0.3, 0.5);
  sound(block.dimension, snd, block.center(), pitch, 0.8);
  if (layer) sound(block.dimension, layer[0], at, layer[1], layer[2]);
  for (const e of effects ?? []) burst(block.dimension, { x: at.x + (Math.random() - 0.5) * 0.3, y: at.y, z: at.z + (Math.random() - 0.5) * 0.2 }, e);
}

/** Lay `held` (taken from where `put` writes back) on an empty board. False if it is not a catch the board takes. */
function layFish(block, player, held, put) {
  const c = entryFor(held.typeId);
  if (!c) return false;
  const p = block.permutation;
  const size = readSize(held).cls;
  stash(keepKey("cb", block.dimension, block), keepOf(held));
  if (!creative(player)) { if (held.amount <= 1) put(undefined); else { held.amount -= 1; put(held); } }
  saveBoard(block, size, c.index, c.first, c.ext);
  block.setPermutation(withFishIndex(p, c.index).withState(CUT, c.first).withState(SIZE, size));
  fx(block, "mob.fish.flop", 1.0, ["drip"]);
  return true;
}

/** One use of the board. Returns "laid", "cut" (a cut, more to come), "done" (the last cut) or undefined. */
function useBoard(block, player) {
  const slot = player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
  const held = slot?.hasItem() ? slot.getItem() : undefined;
  const p = block.permutation;
  const idx = readFishIndex(p), cut = Number(p.getState(CUT) ?? 0), cls = sizeOf(block, p);
  const key = keepKey("cb", block.dimension, block);
  const rec = readData("cb", block.dimension, block);
  const fish = fishOn(idx, rec);
  if (fish && (!rec || rec.idx !== idx || rec.cut !== cut)) saveBoard(block, cls, idx, cut, rec?.ext);   // 1.5.4 / pre-1.6.3 boards: fill the record

  if (!fish) {                                         // empty board: lay a fish down
    if (!held) return refuseAt(player, "board_need_fish", block);
    if (layFish(block, player, held, s => slot.setItem(s))) return "laid";
    return refuseAt(player, isKnife(held) ? "board_need_fish" : "board_cannot_clean", block);
  }
  const first = fish.first;
  if (!held) {                                         // changed your mind before the first cut
    if (cut === first) {
      try { new ItemStack(fish.id, 1); } catch { return refuseAt(player, "board_pack_gone", block); }   // another pack's fish, its pack gone
      give(player, block, fish.id, 1, cls, unstash(key)); saveSize(block, undefined); block.setPermutation(withFishIndex(p, 0).withState(CUT, 0).withState(SIZE, 0));
    }
    else if (fish.gutted && cut === guttedStage(fish)) {   // 1.5.0: gutted and not yet filleted, it goes to the drying rack
      give(player, block, fish.gutted);
      saveSize(block, undefined);
      block.setPermutation(withFishIndex(p, 0).withState(CUT, 0).withState(SIZE, 0));
      fx(block, "mob.fish.flop", 1.2);
    }
    else refuseAt(player, "board_finish_knife", block);
    return;
  }
  if (!isKnife(held)) return refuseAt(player, "board_need_knife", block);
  if (!fish.cuts) return refuseAt(player, "board_pack_gone", block);   // another pack's fish whose pack has not registered it
  wearKnife(player, slot);
  if (cut === first) stash(key, undefined);            // once the knife is in, the fish is food: its record is let go
  const step = Math.max(0, Math.min(fish.cuts.length - 1, cut - first));   // a board from before 1.5.0 carries on where it was
  const this_ = fish.cuts[step];
  for (const [id, n] of cutYield(this_, cls)) give(player, block, id, n);
  fx(block, ...(ACT_FX[this_.act] ?? ACT_FX.fillet));
  if (step < fish.cuts.length - 1) {
    saveBoard(block, cls, idx, first + step + 1, fish.ext);
    block.setPermutation(p.withState(CUT, first + step + 1));
    return "cut";
  }
  saveSize(block, undefined);
  block.setPermutation(withFishIndex(p, 0).withState(CUT, 0).withState(SIZE, 0));
  emit("cleaned", player, { id: fish.id });
  return "done";
}

// 1.7.0 (phase 1): sneak-use with a knife does it all. Every cut left on the fish on the board follows, one every
// SNEAK_GAP ticks, each with its own sound and bits; then, while the player carries more of the same catch (off-hand
// first, then the pockets), the next one is laid down and cut up too, up to SNEAK_MAX fish per use. A fish that
// carries more than its size mark (a record "★", a name) is never picked up this way: it stays in the pockets.
// The engine does not run a block's own interaction for a sneaking player with an item in hand, so the
// before-event takes it (and cancels it, so a plain use cannot also happen on the same click).
export const SNEAK_GAP = 5, SNEAK_MAX = 8;
const busy = new Set();
/** Same catch as the board's: our id (or an old alias of it), or another pack's registered item. */
const sameCatch = (fish, id) => (fish.ext ? id === fish.ext : (FISH_ALIAS[id] ?? id) === fish.id);
/** The next stack of the same catch the player carries: [stack, put] (off-hand, then pockets), or undefined. */
function nextOfSame(player, fish) {
  const ok = it => it && sameCatch(fish, it.typeId) && !keepOf(it);
  try {
    const off = player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Offhand);
    const it = off?.hasItem() ? off.getItem() : undefined;
    if (ok(it)) return [it, s => off.setItem(s)];
  } catch {}
  try {
    const inv = player.getComponent("minecraft:inventory")?.container;
    for (let i = 0; i < (inv?.size ?? 0); i++) {
      if (i === player.selectedSlotIndex) continue;
      const it = inv.getItem(i);
      if (ok(it)) return [it, s => inv.setItem(i, s)];
    }
  } catch {}
  return undefined;
}
const heldKnife = player => {
  try { const s = player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand); return isKnife(s?.hasItem() ? s.getItem() : undefined); }
  catch { return false; }
};
/** Run the whole board for a sneaking player with a knife (steps SNEAK_GAP ticks apart). Exported for tests. */
export function cleanAll(block, player) {
  const dim = block.dimension, at = { x: block.x, y: block.y, z: block.z };
  const key = `${dim.id}:${at.x},${at.y},${at.z}`;
  if (busy.has(key)) return;                           // already running: the button held down does not start another
  busy.add(key);
  let done = 0, fish;
  const stop = () => { busy.delete(key); };
  const step = () => {
    try {
      const b = dim.getBlock(at);
      if (!player?.isValid || b?.typeId !== `${NS}:fish_cleaning_board` || !heldKnife(player)) return stop();   // gone, or the knife broke / was put away
      if (!readFishIndex(b.permutation)) {               // board empty
        if (!fish) { useBoard(b, player); return stop(); }   // nothing was on it: the usual refusal
        const next = done < SNEAK_MAX ? nextOfSame(player, fish) : undefined;
        if (!next || !layFish(b, player, next[0], next[1])) return stop();
        system.runTimeout(step, SNEAK_GAP);
        return;
      }
      fish ??= fishOn(readFishIndex(b.permutation), readData("cb", dim, b));
      const r = useBoard(b, player);
      if (r === "done") done++;
      if (r !== "cut" && r !== "done") return stop();
      system.runTimeout(step, SNEAK_GAP);
    } catch { stop(); }
  };
  step();
}

world.beforeEvents.playerInteractWithBlock.subscribe(ev => {
  if (ev.block?.typeId !== `${NS}:fish_cleaning_board` || !ev.player?.isSneaking || !isKnife(ev.itemStack)) return;
  ev.cancel = true;
  if (!ev.isFirstEvent) return;
  const { block, player } = ev;
  system.run(() => { try { cleanAll(block, player); } catch {} });
});

const cleaningBoard = {
  onPlayerInteract({ block, player }) {
    if (!player) return;
    if (player.isSneaking && heldKnife(player)) return;    // the before-event has it
    useBoard(block, player);
  },
  onPlayerBreak({ block, brokenBlockPermutation, player }) {
    if (creative(player)) { unstash(keepKey("cb", block.dimension, block)); saveSize(block, undefined); return; }
    dropBoard(block.dimension, block, brokenBlockPermutation);
  },
};

/** The stage a fish is on once its gut cut is done (where an empty hand takes it back gutted). Exported for tests. */
export function guttedStage(fish) {
  const g = fish.cuts.findIndex(c => c.act === "gut");
  return g < 0 ? -1 : fish.first + g + 1;
}

/** What a board holds: [id, n, cls, keep?] stacks to make. Before the first cut, the whole catch; after it, what
 *  the last cut would give (its sure outputs; what earlier cuts gave was handed out with them). Exported for tests. */
export function boardContents(idx, cut, cls, keep, ext) {
  const fish = fishOn(idx, ext ? { ext } : undefined);
  if (!fish) return [];
  if (fish.ext && cut !== fish.first && cut && !fish.cuts) return [];
  if (cut === fish.first || !cut) return [[fish.id, 1, cls, keep]];
  return fish.cuts[fish.cuts.length - 1].out.filter(row => (row[2] ?? 1) >= 1).map(row => [row[0], countOf(row, cls), 0]);
}
function dropBoard(dim, pos, perm) {
  const rec = readData("cb", dim, pos);
  const keep = unstash(keepKey("cb", dim, pos));
  writeData("cb", dim, pos, undefined);
  const idx = perm ? readFishIndex(perm) : Number(rec?.idx) || 0;
  const cut = perm ? Number(perm.getState(CUT) ?? 0) : Number(rec?.cut) || 0;
  const cls = Number(rec?.size ?? (perm ? perm.getState(SIZE) : 0) ?? 0) || 0;
  const stacks = [];
  for (const [id, n, c, k] of boardContents(idx, cut, cls, keep, rec?.ext)) {
    if (n <= 0) continue;
    try { stacks.push(k ? fishOut(new ItemStack(id, n), c, k) : applyClass(new ItemStack(id, n), c)); } catch {}   // a pack that is gone
  }
  spawnAll(dim, pos, stacks);
}
registerStation(`${NS}:fish_cleaning_board`, dropBoard);
registerRecords(`${NS}:bd:cb:`, `${NS}:fish_cleaning_board`, (dim, pos) => dropBoard(dim, pos, undefined));

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(`${NS}:fish_cleaning`, cleaningBoard);
});
