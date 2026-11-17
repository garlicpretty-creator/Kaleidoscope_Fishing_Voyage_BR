// ## Shore blocks (Oyster Bed, Laver Rock): breaking one gives 1-3 of its catch; with
// Silk Touch the whole block comes along. Done here rather than in a loot table: Bedrock
// loot tables have no "without Silk Touch" condition, and a bad condition drops nothing.
// Component params: { item, min, max }.
// 1.5.0 (plan 7.1): they grow. The `growth` state: 0 just set down, 1 small, 2 grown. 2 is the state's default,
// so a bed or reef the world generated, or one already standing in a 1.4 world, is grown; one a player places
// starts at 0. A stage takes about a Minecraft day under water, on sand, gravel or stone, in an ocean or beach
// biome (fresh water and dry land never grow), twice as fast at low tide. Time is world time, so a bed that was
// out of reach catches up when it is loaded again (at the average rate of the tide). A grown one is harvested with
// an empty hand or a knife: 2-4 of its catch, and it goes back to small. Broken grown: 1-3 as before; not grown: 1.
import { EquipmentSlot, GameMode, ItemStack, system } from "@minecraft/server";
import { readData, writeData } from "./blockData.js";
import { now } from "../util/clock.js";
import { biomeIdAt } from "../util/biome.js";
import { isWater, tideState } from "../fishing/water.js";

const NS = "kaleidoscope_fishing";
export const GROWTH = `${NS}:growth`;
export const GROWN = 2;
export const STAGE_TICKS = 24000;                    // one stage, at the plain rate
const LOW_TIDE = 2;                                   // low tide grows twice as fast
const AVERAGE = 0.75 * LOW_TIDE + 0.25;               // the tide is low three quarters of the day
const BEDS = new Set(["minecraft:sand", "minecraft:red_sand", "minecraft:gravel", "minecraft:stone", "minecraft:cobblestone",
  "minecraft:andesite", "minecraft:diorite", "minecraft:granite", "minecraft:mossy_cobblestone", "minecraft:clay"]);
const SEA = /ocean|beach|shore/;
const KNIFE_TAG = "kaleidoscope_cookery:kitchen_knife";

function hasSilkTouch(player) {
  try {
    const item = player.getComponent("minecraft:equippable").getEquipment(EquipmentSlot.Mainhand);
    return !!item?.getComponent("minecraft:enchantable")?.getEnchantment("silk_touch");
  } catch { return false; }
}
const creative = p => { try { const g = p.getGameMode(); return g === GameMode.Creative || g === "creative"; } catch { return false; } };
const stageOf = perm => { const s = Number(perm?.getState?.(GROWTH)); return Number.isInteger(s) ? s : GROWN; };
const rollN = (min, max) => min + Math.floor(Math.random() * (max - min + 1));
function drop(block, item, n) {
  if (n <= 0) return;
  try { block.dimension.spawnItem(new ItemStack(item, n), block.center()); } catch {}
}

/** Whether a bed can grow where it is. Exported for tests. */
export function canGrow(block) {
  if (!isWater(block)) return false;
  let below;
  try { below = block.below()?.typeId; } catch {}
  if (!BEDS.has(below)) return false;
  try { return SEA.test(biomeIdAt(block.dimension, block.location)); } catch { return false; }
}

/** Growth this tick: { progress, stage } from the record and the time gone by. Exported for tests. */
export function grow(rec, stage, n, low) {
  const t = Number(rec?.t);
  if (!rec || !Number.isFinite(t) || n < t || rec.stage !== stage) return { p: 0, t: n, stage };
  const dt = n - t;
  let p = (Number(rec.p) || 0) + dt * (dt > 1200 ? AVERAGE : low ? LOW_TIDE : 1);   // a long gap: the tide's average
  while (p >= STAGE_TICKS * AVERAGE && stage < GROWN) { p -= STAGE_TICKS * AVERAGE; stage++; }
  if (stage >= GROWN) p = 0;
  return { p, t: n, stage };
}

const shoreDrop = {
  beforeOnPlayerPlace(e) {
    try { e.permutationToPlace = e.permutationToPlace.withState(GROWTH, 0); } catch {}
  },
  onTick({ block }) {
    const stage = stageOf(block.permutation);
    if (stage >= GROWN) { if (readData("sg", block.dimension, block)) writeData("sg", block.dimension, block, undefined); return; }
    const n = now();
    if (!canGrow(block)) { writeData("sg", block.dimension, block, { p: Number(readData("sg", block.dimension, block)?.p) || 0, t: n, stage }); return; }
    const r = grow(readData("sg", block.dimension, block), stage, n, tideState() === "low");
    writeData("sg", block.dimension, block, r.stage >= GROWN ? undefined : r);
    if (r.stage !== stage) { try { block.setPermutation(block.permutation.withState(GROWTH, r.stage)); } catch {} }
  },
  onPlayerInteract({ block, player }, arg) {
    if (!player || stageOf(block.permutation) < GROWN) return;
    const slot = player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
    const held = slot?.hasItem() ? slot.getItem() : undefined;
    let knife = false;
    try { knife = !!held?.hasTag(KNIFE_TAG) || held?.typeId === `${NS}:fishing_knife`; } catch {}
    if (held && !knife) return;
    const p = arg?.params ?? {};
    const [lo, hi] = Array.isArray(p.harvest) ? p.harvest : [2, 4];
    drop(block, p.item ?? `${NS}:oyster`, rollN(lo, hi));
    try { block.setPermutation(block.permutation.withState(GROWTH, 1)); } catch {}
    writeData("sg", block.dimension, block, { p: 0, t: now(), stage: 1 });
    try { block.dimension.playSound("dig.gravel", block.center(), { pitch: 1.3, volume: 0.6 }); } catch {}
  },
  onPlayerBreak({ block, brokenBlockPermutation, player }, arg) {
    writeData("sg", block.dimension, block, undefined);
    if (!player || creative(player)) return;
    const p = arg?.params ?? {};
    if (hasSilkTouch(player)) return;                    // the engine drops the block itself
    const min = p.min ?? 1, max = p.max ?? 3;
    drop(block, p.item ?? `${NS}:oyster`, stageOf(brokenBlockPermutation) >= GROWN ? rollN(min, max) : 1);
  },
};

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(`${NS}:shore_drop`, shoreDrop);
});
