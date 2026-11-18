// ## Fishing-village blocks: Fish Scale, Tackle Rack and Fish Print (the tanks: tanks.js).
// No text: the needle, the hung rods and the print show everything.
import { EnchantmentTypes, EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { CATCHES, FISH_ALIAS, RODS, TANK_FISH } from "../data/generated.js";
import { LARGE, MEDIUM, SMALL, applyClass, readSize, upgradeStack } from "../fishing/size.js";
import { isPart, readParts, slotOf, writeParts } from "../fishing/parts.js";
import { readFishIndex, withFishIndex } from "./fishState.js";
import { PRINTABLE, printIndex } from "../data/tank.js";
import { spawnParticle } from "../util/particles.js";

const NS = "kaleidoscope_fishing";
const SIZE = Object.fromEntries(CATCHES.filter(c => c.size).map(c => [c.id, c.size]));
const canon = id => FISH_ALIAS[id] ?? id;

const mainhand = p => p.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
const creative = p => { try { return p.getGameMode() === GameMode.Creative; } catch { return false; } };
function takeOne(player, slot) {
  if (creative(player)) return;
  const it = slot.getItem();
  if (!it) return;
  if (it.amount <= 1) slot.setItem(undefined); else { it.amount -= 1; slot.setItem(it); }
}
function give(player, block, stack) {
  try {
    const left = player.getComponent("minecraft:inventory")?.container?.addItem(stack);
    if (left) block.dimension.spawnItem(left, block.center());
  } catch { try { block.dimension.spawnItem(stack, block.center()); } catch {} }
}
const snd = (block, id, pitch = 1, volume = 0.8) => { try { block.dimension.playSound(id, block.center(), { pitch, volume }); } catch {} };

// ---------------------------------------------------------------- Fish Scale
const NEEDLE = `${NS}:needle`;
// The needle shows the fish's size class (small / medium / large) on the green-to-red band.
// A record fish (★ N cm) is weighed exactly. A fish that carries no mark counts as medium.
const CLASS_NEEDLE = { [SMALL]: 1, [MEDIUM]: 4, [LARGE]: 6 };
const fishScale = {
  onPlayerInteract({ block, player }) {
    if (!player) return;
    const slot = mainhand(player);
    const stack = slot?.hasItem() ? slot.getItem() : undefined;
    if (!stack || !SIZE[canon(stack.typeId)]) {
      if (!stack) block.setPermutation(block.permutation.withState(NEEDLE, 0));
      return;
    }
    const [lo, hi] = SIZE[canon(stack.typeId)];
    const { cls, cm, record } = readSize(stack);
    if (upgradeStack(stack)) { try { slot.setItem(stack); } catch {} }   // 1.6.0: an old "★ N cm" becomes the new ★
    const exact = record && cm !== undefined;
    const target = exact ? Math.max(0, Math.min(7, Math.round((cm - lo) / Math.max(1, hi - lo) * 7))) : CLASS_NEEDLE[cls || MEDIUM];
    // the needle overshoots to the end, then settles on the fish's mark
    const path = [7, 6, 7, ...Array.from({ length: Math.max(0, 7 - target) }, (_, i) => 6 - i).filter(v => v >= target)];
    if (path[path.length - 1] !== target) path.push(target);
    path.forEach((v, i) => system.runTimeout(() => {
      try {
        if (!block.isValid || block.typeId !== `${NS}:fish_scale`) return;
        block.setPermutation(block.permutation.withState(NEEDLE, v));
        snd(block, "random.click", 1.6 - v * 0.05, 0.35);
        if (i === path.length - 1 && exact) {
          snd(block, "random.orb", 0.7 + target * 0.08, 0.7);
          for (let k = 0; k < 6; k++) spawnParticle(block.dimension, "minecraft:villager_happy",
            { x: block.x + 0.2 + Math.random() * 0.6, y: block.y + 1.1 + Math.random() * 0.3, z: block.z + 0.2 + Math.random() * 0.6 });
        }
      } catch {}
    }, 2 + i * 3));
  },
};

// ---------------------------------------------------------------- Tackle Rack
// v1.2: the Lava and Ender rods hang here too; an Eye of Ender turns a hung Voyage rod into an Ender rod.
const ROD_KIND = { [`${NS}:bamboo_fishing_rod`]: 1, [`${NS}:voyage_fishing_rod`]: 2, [`${NS}:lava_fishing_rod`]: 3, [`${NS}:ender_fishing_rod`]: 4 };
const ROD_BY_KIND = { 1: `${NS}:bamboo_fishing_rod`, 2: `${NS}:voyage_fishing_rod`, 3: `${NS}:lava_fishing_rod`, 4: `${NS}:ender_fishing_rod` };
const RACK_SLOTS = [`${NS}:rod_a`, `${NS}:rod_b`];
const rackKey = (block, i) => `${NS}:rack:${block.dimension.id}:${block.x},${block.y},${block.z}:${i}`;
function saveRod(block, i, stack) {
  const data = { damage: 0, ench: [] };
  try { data.damage = stack.getComponent("minecraft:durability")?.damage ?? 0; } catch {}
  try { data.ench = stack.getComponent("minecraft:enchantable")?.getEnchantments().map(e => [e.type.id, e.level]) ?? []; } catch {}
  try { if (stack.nameTag) data.name = stack.nameTag; } catch {}
  data.parts = readParts(stack);
  try { world.setDynamicProperty(rackKey(block, i), JSON.stringify(data)); } catch {}
  try { world.setDynamicProperty(rackKey(block, "last"), i); } catch {}
}
function loadRod(block, i, kind) {
  const stack = new ItemStack(ROD_BY_KIND[kind], 1);
  let data = {};
  try { data = JSON.parse(world.getDynamicProperty(rackKey(block, i)) ?? "{}"); } catch {}
  try { world.setDynamicProperty(rackKey(block, i), undefined); } catch {}
  try { const d = stack.getComponent("minecraft:durability"); if (d && data.damage) d.damage = Math.min(data.damage, d.maxDurability - 1); } catch {}
  // addEnchantment needs an EnchantmentType, not its id (a plain id silently lost the enchantments)
  let enchantable;
  try { enchantable = stack.getComponent("minecraft:enchantable"); } catch {}
  for (const [id, level] of data.ench ?? []) {
    try { const type = EnchantmentTypes.get(id); if (type && enchantable) enchantable.addEnchantment({ type, level }); }
    catch (err) { console.warn(`[Fishing Voyage] could not restore rod enchantment ${id}: ${err}`); }
  }
  try { if (data.name) stack.nameTag = data.name; } catch {}
  if (data.parts && Object.keys(data.parts).length) writeParts(stack, data.parts);
  return stack;
}
// Tackle parts are fitted to the rod hung on the rack last.
function lastRod(block, kinds) {
  let i;
  try { i = world.getDynamicProperty(rackKey(block, "last")); } catch {}
  if (typeof i === "number" && kinds[i]) return i;
  const any = kinds.findIndex(k => k);
  return any >= 0 ? any : undefined;
}
function rodData(block, i) {
  try { return JSON.parse(world.getDynamicProperty(rackKey(block, i)) ?? "{}"); } catch { return {}; }
}
const tackleRack = {
  onPlayerInteract({ block, player }) {
    if (!player) return;
    const slot = mainhand(player);
    const held = slot?.hasItem() ? slot.typeId : "";
    const p = block.permutation;
    const kinds = RACK_SLOTS.map(s => Number(p.getState(s) ?? 0));
    if (ROD_KIND[held]) {
      const i = kinds.indexOf(0);
      if (i < 0) return;
      saveRod(block, i, slot.getItem());
      block.setPermutation(p.withState(RACK_SLOTS[i], ROD_KIND[held]));
      if (!creative(player)) slot.setItem(undefined);
      snd(block, "random.wood_click", 1.1);
      return;
    }
    if (isPart(held) || held === "minecraft:shears") {
      const i = lastRod(block, kinds);
      if (i === undefined) return;
      const data = rodData(block, i);
      data.parts = data.parts ?? {};
      if (held === "minecraft:shears") {
        const off = Object.values(data.parts);
        if (!off.length) return;
        for (const id of off) give(player, block, new ItemStack(id, 1));
        data.parts = {};
        snd(block, "mob.sheep.shear", 1.2);
      } else {
        const slot = slotOf(held), old = data.parts[slot];
        if (old === held) return;
        data.parts[slot] = held;
        takeOne(player, mainhand(player));
        if (old) give(player, block, new ItemStack(old, 1));
        snd(block, "armor.equip_chain", 1.4, 0.7);
        snd(block, "random.click", 1.8, 0.4);
      }
      try { world.setDynamicProperty(rackKey(block, i), JSON.stringify(data)); } catch {}
      return;
    }
    if (held === "minecraft:ender_eye") {
      const i = kinds.lastIndexOf(2);
      if (i < 0) return;
      block.setPermutation(p.withState(RACK_SLOTS[i], 4));     // the saved wear, enchantments and parts stay with it
      takeOne(player, mainhand(player));
      snd(block, "mob.endermen.portal", 1.1, 0.8);
      for (let k = 0; k < 10; k++) {
        try { spawnParticle(block.dimension, "minecraft:endrod", { x: block.x + 0.2 + Math.random() * 0.6, y: block.y + 0.3 + Math.random() * 0.7, z: block.z + 0.5 }); } catch {}
      }
      return;
    }
    if (held) return;
    for (let i = RACK_SLOTS.length - 1; i >= 0; i--) {
      if (!kinds[i]) continue;
      give(player, block, loadRod(block, i, kinds[i]));
      block.setPermutation(p.withState(RACK_SLOTS[i], 0));
      snd(block, "random.wood_click", 0.9);
      return;
    }
  },
  onPlayerBreak({ block, brokenBlockPermutation }) {
    RACK_SLOTS.forEach((s, i) => {
      const k = Number(brokenBlockPermutation.getState(s) ?? 0);
      if (k) { try { block.dimension.spawnItem(loadRod(block, i, k), block.center()); } catch {} }
    });
  },
};

// ---------------------------------------------------------------- Fish Print (魚拓)
// A blank frame on the wall; use any fish on it to ink the fish onto the paper (the fish is
// kept). The frame shows how big it was: 1 bronze (small), 2 silver (medium), 3 gold (large),
// 4 gold with a red seal (record fish). Breaking it gives the blank frame back.
const PRINT_TIER = `${NS}:tier`;
// 1.6.0 (plan 14.1): the fish on the print is drawn at one of 4 sizes (state shrink: 0 full .. 3 smallest), by where
// its length falls in the species' range: the longer the record, the bigger the fish. Without a length (not a
// record) the size class decides; a species with no sizes (crabs, shrimp) is drawn full. Prints from before 1.6.0
// have shrink 0, the full size they always had.
const PRINT_SHRINK = `${NS}:shrink`;
/** The print's shrink state (0..3) for a fish id and what its stack says ({ cls, cm } from readSize). */
export function printShrink(id, { cls = 0, cm } = {}) {
  const r = SIZE[id];
  if (!r) return 0;
  if (typeof cm === "number" && Number.isFinite(cm)) {
    const p = Math.max(0, Math.min(1, (cm - r[0]) / Math.max(1, r[1] - r[0])));
    return p >= 0.75 ? 0 : p >= 0.5 ? 1 : p >= 0.25 ? 2 : 3;
  }
  return cls === LARGE ? 0 : cls === SMALL ? 2 : 1;
}
const WALL_FACES = { North: "north", South: "south", East: "east", West: "west" };
const fishPrint = {
  // Hangs on walls only: turned to the face that was clicked, never placed on a floor or ceiling.
  beforeOnPlayerPlace(e) {
    const dir = WALL_FACES[String(e.face)] ?? WALL_FACES[String(e.face).replace(/^./, c => c.toUpperCase())];
    if (!dir) { e.cancel = true; return; }
    try { e.permutationToPlace = e.permutationToPlace.withState("minecraft:cardinal_direction", dir); } catch {}
  },
  onPlayerInteract({ block, player }) {
    if (!player) return;
    if (readFishIndex(block.permutation) !== 0) return;
    const slot = mainhand(player);
    const stack = slot?.hasItem() ? slot.getItem() : undefined;
    const idx = stack ? printIndex(canon(stack.typeId)) : 0;
    if (idx <= 0) return;                             // v1.3's new tank species have no print (1.4's do)
    const { cls, cm, record } = readSize(stack);
    if (upgradeStack(stack)) { try { slot.setItem(stack); } catch {} }   // 1.6.0: an old "★ N cm" becomes the new ★
    const tier = record ? 4 : (cls || MEDIUM);
    let perm = withFishIndex(block.permutation, idx).withState(PRINT_TIER, tier);
    try { perm = perm.withState(PRINT_SHRINK, printShrink(canon(stack.typeId), { cls, cm })); } catch {}
    block.setPermutation(perm);
    snd(block, "item.book.page_turn", 0.8, 0.9);
    snd(block, "mob.squid.ink_squirt", 1.2, 0.5);
    for (let k = 0; k < 6; k++) {
      try { spawnParticle(block.dimension, "minecraft:basic_smoke_particle",
        { x: block.x + 0.2 + Math.random() * 0.6, y: block.y + 0.3 + Math.random() * 0.5, z: block.z + 0.2 + Math.random() * 0.6 }); } catch {}
    }
    if (tier === 4) snd(block, "random.orb", 0.8, 0.6);
  },
};

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(`${NS}:fish_print`, fishPrint);
  blockComponentRegistry.registerCustomComponent(`${NS}:fish_scale`, fishScale);
  blockComponentRegistry.registerCustomComponent(`${NS}:tackle_rack`, tackleRack);
});
