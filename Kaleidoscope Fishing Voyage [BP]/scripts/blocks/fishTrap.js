// ## Shrimp Trap block (custom component "kaleidoscope_fishing:fish_trap").
// Baited and underwater, it slowly fills: v1.6.4 (F3) one try every TRAP_STEP ticks of world time from baiting
// (record "t"), counted on the block tick, so a trap that was unloaded catches up when it loads again (still 3 at
// most, and the bait may be eaten on the way). Until 1.6.3: random ticks, only while loaded. A trap baited before
// 1.6.4 starts its clock on its first tick after the update.
// The catch is visible through the bamboo; use it with an empty hand to empty it.
// v1.6.3 (F1): the catch and the bait (which one went in) are mirrored in a world record (blockData "ft"), so a
// trap removed in any way (player, explosion, piston, command: contents.js) gives back its shrimp, crab and
// unused bait. A trap baited before 1.6.3 does not know its bait; it gives back the catch only.
// v1.6.3 (F2): refused uses say why (util/hint.js).
import { EquipmentSlot, GameMode, ItemStack, system } from "@minecraft/server";
import { TRAP_BAITS } from "../data/generated.js";
import { analyzeWater, isWater } from "../fishing/water.js";
import { tryStore } from "../tools/basket.js";
import { spawnParticle } from "../util/particles.js";
import { refuse } from "../util/hint.js";
import { burst, on } from "./stationFx.js";
import { now, steps } from "../util/clock.js";
import { readData, writeData } from "./blockData.js";
import { registerRecords, registerStation, spawnAll } from "./contents.js";

const NS = "kaleidoscope_fishing";
const CATCH = `${NS}:catch`, BAIT = `${NS}:bait`, CRAB = `${NS}:crab`;
export const TRAP_STEP = 2400; // v1.6.4: one try every 2 minutes of world time while baited and under water
const FILL_CHANCE = 0.9;       // per try (1.6.3: 0.5 per random tick, about one catch in 2.3 minutes on average)
const LIVE_CHANCE = 0.35;      // v1.4: a shrimp taken out of the trap is still alive this often (Live Shrimp bait)
const BAIT_USE_CHANCE = 0.35;  // bait eaten when something crawls in
const SEA = new Set(["ocean", "warm_ocean", "cold_ocean", "deep_ocean", "beach", "swamp"]);

function underwater(block) {
  try { if (block.isWaterlogged) return true; } catch {}
  try { return isWater(block.above()); } catch { return false; }
}

// Decided when something crawls in, so what you see in the cage is what you get.
function crabCrawlsIn(block) {
  let sea = false;
  try { sea = [...analyzeWater(block.dimension, block.location).waters].some(w => SEA.has(w)); } catch {}
  return Math.random() < (sea ? 0.45 : 0.15);
}
function contents(perm) { return catchOf(Number(perm.getState(CATCH) ?? 0), Number(perm.getState(CRAB) ?? 0)); }
const catchOf = (c, k) => { k = c > 0 ? Math.min(k, c) : 0; return [...Array(k).fill(`${NS}:crab`), ...Array(Math.max(0, c - k)).fill(`${NS}:shrimp`)]; };

// v1.6.3: the record { c, k, bait } follows every change of the block, so a trap that is gone still knows.
const stOf = p => ({ c: Number(p.getState(CATCH) ?? 0), k: Number(p.getState(CRAB) ?? 0), b: Number(p.getState(BAIT) ?? 0) });
function mirror(block, perm, bait, t) {
  const s = stOf(perm), d = readData("ft", block.dimension, block);
  const baitId = s.b === 1 ? (bait ?? d?.bait) : undefined;
  const clock = s.b === 1 ? (t ?? d?.t) : undefined;            // v1.6.4: the fill clock runs while baited
  const want = s.c > 0 || s.b === 1 ? { c: s.c, k: s.k, ...(baitId ? { bait: baitId } : {}), ...(typeof clock === "number" ? { t: clock } : {}) } : undefined;
  if (JSON.stringify(want) !== JSON.stringify(d)) writeData("ft", block.dimension, block, want);
}
function setTrap(block, perm, bait, t) {
  block.setPermutation(perm);
  mirror(block, perm, bait, t);
}
/** What a trap holds, as item ids (catch, then the bait if it is known and not yet eaten). Exported for tests. */
export function trapContents(c, k, baited, baitId) {
  const out = catchOf(c, k);
  if (baited && baitId && TRAP_BAITS.includes(baitId)) out.push(baitId);
  return out;
}
function dropTrap(dim, pos, perm) {
  const d = readData("ft", dim, pos);
  writeData("ft", dim, pos, undefined);
  const s = perm ? stOf(perm) : { c: Number(d?.c) || 0, k: Number(d?.k) || 0, b: d?.bait ? 1 : 0 };
  spawnAll(dim, pos, trapContents(s.c, s.k, s.b === 1, d?.bait).map(id => new ItemStack(id, 1)));
}

// --- visual cues (no text): bubbles you can spot from a boat ---------------------------
const BUBBLE = "minecraft:basic_bubble_particle";
function puff(block, n, spread = 0.35) {
  const c = block.center();
  for (let i = 0; i < n; i++) {
    try {
      spawnParticle(block.dimension, BUBBLE, { x: c.x + (Math.random() - 0.5) * spread * 2, y: c.y - 0.1 + Math.random() * 0.4, z: c.z + (Math.random() - 0.5) * spread * 2 });
    } catch {}
  }
}
// A thin trail of bubbles from the trap up to the surface, so a full trap can be found from above.
function trail(block, strands) {
  const c = block.center();
  let top = block.y;
  try {
    for (let i = 1; i <= 24; i++) { const b = block.above(i); if (!b || !isWater(b)) break; top = block.y + i; }
  } catch {}
  for (let s = 0; s < strands; s++) {
    const ox = (Math.random() - 0.5) * 0.6, oz = (Math.random() - 0.5) * 0.6;
    for (let y = block.y + 0.6; y <= top + 0.9; y += 0.55 + Math.random() * 0.4) {
      try { spawnParticle(block.dimension, BUBBLE, { x: c.x + ox, y, z: c.z + oz }); } catch {}
    }
  }
}

function give(player, block, id) {
  if (tryStore(player, id, 1) === 0) return;
  const stack = new ItemStack(id, 1);
  try {
    const left = player.getComponent("minecraft:inventory")?.container?.addItem(stack);
    if (left) block.dimension.spawnItem(left, block.center());
  } catch { try { block.dimension.spawnItem(stack, block.center()); } catch {} }
}

// v1.6.4 (F3): the tries due since the clock last moved.
function fill(block) {
  const p = block.permutation;
  if (p.getState(BAIT) !== 1) return;
  const d = readData("ft", block.dimension, block);
  if (typeof d?.t !== "number") { mirror(block, p, undefined, now()); return; }   // baited before 1.6.4: start now
  const { k, t } = steps(d.t, now(), TRAP_STEP, 3);
  if (!k) { if (t !== d.t) mirror(block, p, undefined, t); return; }
  let next = p, caught = 0;
  const wet = underwater(block);
  for (let i = 0; i < k && wet; i++) {
    const c = Number(next.getState(CATCH) ?? 0);
    if (c >= 3 || next.getState(BAIT) !== 1) break;
    if (Math.random() >= FILL_CHANCE) continue;
    next = next.withState(CATCH, c + 1);
    if (Number(next.getState(CRAB) ?? 0) === 0 && crabCrawlsIn(block)) next = next.withState(CRAB, 1);
    if (Math.random() < BAIT_USE_CHANCE) next = next.withState(BAIT, 0);
    caught++;
  }
  setTrap(block, next, undefined, t);
  if (!caught) return;
  // something just pushed in through the funnel: a burst of bubbles and a soft pop
  puff(block, 10, 0.4);
  trail(block, 2);
  try { block.dimension.playSound("kaleidoscope_fishing.trap_catch", block.center(), { pitch: 0.9 + Math.random() * 0.3, volume: 0.9 }); } catch {}
}

const fishTrap = {
  // Engine-driven per-block tick (50-110 game ticks); only does anything underwater.
  onTick({ block }) {
    mirror(block, block.permutation);  // pre-1.6.3 traps: their catch gets a record
    fill(block);
    const p = block.permutation;
    if (!underwater(block)) return;
    const c = Number(p.getState(CATCH) ?? 0);
    if (c > 0) {
      puff(block, 1 + c, 0.3);
      trail(block, c);                 // more catch = more bubble strings reaching the surface
      if (Math.random() < 0.25) {
        try { block.dimension.playSound("bubble.up", block.center(), { pitch: 1.2, volume: 0.35 }); } catch {}
      }
    } else if (p.getState(BAIT) === 1 && Math.random() < 0.5) {
      puff(block, 1, 0.15);            // baited and waiting: the odd lone bubble
    }
  },
  onPlayerInteract({ block, player }) {
    if (!player) return;
    const slot = player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
    const held = slot?.hasItem() ? slot.typeId : "";
    const p = block.permutation;
    const c = Number(p.getState(CATCH) ?? 0);
    if (held && TRAP_BAITS.includes(held)) {
      if (p.getState(BAIT) === 1) return refuse(player, "trap_baited");
      if (player.getGameMode() !== GameMode.Creative) {
        const it = slot.getItem();
        if (it.amount <= 1) slot.setItem(undefined); else { it.amount -= 1; slot.setItem(it); }
      }
      setTrap(block, p.withState(BAIT, 1), held, now());
      try { block.dimension.playSound("dig.grass", block.center(), { pitch: 1.3, volume: 0.7 }); } catch {}
      if (underwater(block)) puff(block, 6, 0.25);
      return;
    }
    if (held) return refuse(player, c > 0 ? "trap_empty_hand" : "trap_not_bait");
    if (c <= 0) return refuse(player, p.getState(BAIT) !== 1 ? "trap_need_bait" : underwater(block) ? "trap_waiting" : "trap_underwater");
    for (const id of contents(p)) give(player, block, id === `${NS}:shrimp` && Math.random() < LIVE_CHANCE ? `${NS}:live_shrimp` : id);
    setTrap(block, p.withState(CATCH, 0).withState(CRAB, 0));
    try {
      block.dimension.playSound("random.splash", block.center(), { pitch: 1.4, volume: 0.6 });
      spawnParticle(block.dimension, "minecraft:water_splash_particle", block.center());
    } catch {}
    // 1.5.0 (immersive pass): the cage comes up streaming water, the catch kicking
    burst(block.dimension, on(block, 0.5, 0.6, 0.5), "spray", "drip");
    if (!underwater(block)) { try { block.dimension.playSound("mob.fish.flop", block.center(), { pitch: 1.1, volume: 0.5 }); } catch {} }
  },
  onPlayerBreak({ block, brokenBlockPermutation, player }) {
    if (player?.getGameMode() === GameMode.Creative) { writeData("ft", block.dimension, block, undefined); return; }
    dropTrap(block.dimension, block, brokenBlockPermutation);
  },
};

registerStation(`${NS}:shrimp_trap`, dropTrap);
registerRecords(`${NS}:bd:ft:`, `${NS}:shrimp_trap`, (dim, pos) => dropTrap(dim, pos, undefined));

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(`${NS}:fish_trap`, fishTrap);
});
