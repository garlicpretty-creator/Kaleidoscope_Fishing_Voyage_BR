// ## Salt Pan (曬鹽盤, 1.5.0). Sea salt dried by the sun. Fill it with a water bucket where the sea is (an ocean
// or beach biome) under open sky; it dries only in daylight and without rain, a full day of daylight (12000
// ticks) in all, and rain pauses it without undoing it. Half way a white rim shows; then the pan is all salt and
// an empty hand gathers 4 Salt. The state `stage` is 0 empty, 1 water, 2 half dry, 3 salt; the daylight counted
// so far is kept in a block record ("sp": { p, t }), and a pan that was unloaded counts only the daylight it saw.
import { EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { readData, writeData } from "./blockData.js";
import { registerRecords, registerStation, spawnAll } from "./contents.js";
import { isRaining } from "../fishing/water.js";
import { refuse } from "../util/hint.js";

const NS = "kaleidoscope_fishing";
const BLOCK = `${NS}:salt_pan`, STAGE = `${NS}:stage`, SALT = `${NS}:sea_salt`;
export const DRY_TICKS = 12000, SALT_YIELD = 4;
const now = () => { try { return world.getAbsoluteTime(); } catch { return system.currentTick; } };
const creative = p => { try { return p.getGameMode() === GameMode.Creative; } catch { return false; } };
const stageOf = block => Number(block.permutation.getState(STAGE) ?? 0);
const setStage = (block, s) => { try { block.setPermutation(block.permutation.withState(STAGE, s)); } catch {} };
const snd = (block, id, pitch = 1, volume = 0.7) => { try { block.dimension.playSound(id, block.center(), { pitch, volume }); } catch {} };

/** By the sea: an ocean or beach biome (where the game can tell). Exported for tests. */
export function bySea(block) {
  let id = "";
  try { id = String(block.dimension.getBiome?.(block.location)?.id ?? ""); } catch {}
  return /ocean|beach|shore/.test(id);
}
/** Nothing above it but air: open to the sun. */
export function openSky(block) {
  try { const top = block.dimension.getTopmostBlock({ x: block.x, z: block.z }); return !top || top.y <= block.y; } catch { return true; }
}
const daylight = () => { const t = world.getTimeOfDay?.() ?? 6000; return t < 12000; };
const stageFor = p => (p >= DRY_TICKS ? 3 : p >= DRY_TICKS / 2 ? 2 : 1);

function dropPan(dim, pos, perm) {
  const stage = perm ? Number(perm.getState(STAGE) ?? 0) : Number(readData("sp", dim, pos)?.stage) || 0;
  writeData("sp", dim, pos, undefined);
  if (stage === 3) spawnAll(dim, pos, [new ItemStack(SALT, SALT_YIELD)]);
}

const pan = {
  onPlayerInteract({ block, player }) {
    if (!player) return;
    let slot;
    try { slot = player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand); } catch {}
    const held = slot?.hasItem() ? slot.typeId : undefined;
    const stage = stageOf(block);
    if (held === "minecraft:water_bucket" && stage === 0) {
      if (!bySea(block) || !openSky(block)) return refuse(player, "salt_pan_place");
      if (!creative(player)) slot.setItem(new ItemStack("minecraft:bucket", 1));
      writeData("sp", block.dimension, block, { p: 0, t: now(), stage: 1 });
      setStage(block, 1); snd(block, "bucket.empty_water"); return;
    }
    if (!held && stage === 3) {
      const stack = new ItemStack(SALT, SALT_YIELD);
      try { const left = player.getComponent("minecraft:inventory")?.container?.addItem(stack); if (left) block.dimension.spawnItem(left, block.center()); }
      catch { try { block.dimension.spawnItem(stack, block.center()); } catch {} }
      writeData("sp", block.dimension, block, undefined);
      setStage(block, 0); snd(block, "dig.sand", 1.2); return;
    }
    refuse(player, stage === 0 ? "salt_pan_need_water" : "salt_pan_drying");
  },
  onTick({ block }) {
    const stage = stageOf(block);
    if (stage !== 1 && stage !== 2) return;
    const r = readData("sp", block.dimension, block) ?? { p: 0, t: now() };
    const n = now(), dt = Math.max(0, Math.min(200, n - (Number(r.t) || n)));   // a pan out of reach counts nothing
    const sunny = daylight() && !isRaining(block.dimension) && openSky(block);
    const p = (Number(r.p) || 0) + (sunny ? dt : 0);
    const next = stageFor(p);
    writeData("sp", block.dimension, block, { p, t: n, stage: next });
    if (next !== stage) { setStage(block, next); if (next === 3) snd(block, "random.pop", 0.9, 0.5); }
  },
  onPlayerBreak({ block, brokenBlockPermutation, player }) {
    if (player && creative(player)) { writeData("sp", block.dimension, block, undefined); return; }
    dropPan(block.dimension, block, brokenBlockPermutation);
  },
};

registerStation(BLOCK, dropPan);
registerRecords(`${NS}:bd:sp:`, BLOCK, (dim, pos) => dropPan(dim, pos, undefined));

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(BLOCK, pan);
});
