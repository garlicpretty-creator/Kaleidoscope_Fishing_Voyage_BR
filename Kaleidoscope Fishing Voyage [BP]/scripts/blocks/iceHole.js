// ## Ice fishing (冰釣, v1.2).
// Ice Auger: used on Ice / Packed Ice / Blue Ice with water underneath, it drills an Ice Hole
// (a block of ice with a shaft through it; it never freezes over).
// Ice Hole: fish through it with any rod, or set a Tip-up in it. A tip-up fishes on its own,
// slowly, while the hole is loaded: on a bite the red flag springs up and a bell rings; use the
// hole to take the fish (v1.6.4: it waits on the line until taken). Small and medium fish only.
// The flag, the bell and the splash say everything.
// v1.6.3 (F1): a hole with a tip-up removed in any way (player, explosion, command: contents.js) gives the
// tip-up back (the owner record says one was set). F2: refused uses say why (util/hint.js).
// v1.6.4 (F3): a hooked fish no longer gets away. The flag stays up until someone takes the fish, and the bell
// rings again every RING_STEPS steps (30 s), but only when a player is within HEAR blocks. No new bite while one
// is hooked. Until 1.6.3 the fish escaped after 30 s.
import { EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { RODS, TIP_UP_LIMIT } from "../data/generated.js";
import { useRodItem } from "../fishing/rod.js";
import { rollCatch, rollSize } from "../fishing/loot.js";
import { ICE_HOLE, analyzeWater, isRaining, isWater, timeSlot } from "../fishing/water.js";
import { LARGE, MEDIUM, classOf, loreFor, rangeOf } from "../fishing/size.js";
import { recordCatch } from "../journal/records.js";
import { tryStore } from "../tools/basket.js";
import { spawnParticle } from "../util/particles.js";
import { refuse } from "../util/hint.js";
import { registerRecords, registerStation, spawnAll } from "./contents.js";

const NS = "kaleidoscope_fishing";
const AUGER = `${NS}:ice_auger`, TIP_UP = `${NS}:tip_up`;
const TIP = `${NS}:tipup`, AGE = `${NS}:age`;
const OWNED = `${NS}:tipups`;              // player property: keys of the holes they set tip-ups in
const OWNER = `${NS}:tipown:`;             // v1.3.3, world property per hole: id of the player whose tip-up is in it ("" none)
const DRILLABLE = new Set(["minecraft:ice", "minecraft:packed_ice", "minecraft:blue_ice"]);
const BITE_CHANCE = 0.04;                  // per 100-tick step: about one bite in two minutes
const RING_STEPS = 6;                      // v1.6.4: the bell again every 6 steps (30 s) while a fish is hooked
const HEAR = 32;                           // ... and only with a player this close
const someoneNear = (dim, at) => { try { return dim.getPlayers({ location: at, maxDistance: HEAR }).length > 0; } catch { return false; } };

const mainhand = p => p.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
const creative = p => { try { return p.getGameMode() === GameMode.Creative; } catch { return false; } };
const keyOf = b => `${b.dimension.id}:${b.x}:${b.y}:${b.z}`;
const snd = (dim, id, loc, pitch = 1, volume = 0.7) => { try { dim.playSound(id, loc, { pitch, volume }); } catch {} };
const fx = (dim, id, loc, n = 4, spread = 0.4) => {
  for (let i = 0; i < n; i++) {
    try { spawnParticle(dim, id, { x: loc.x + (Math.random() - 0.5) * spread, y: loc.y, z: loc.z + (Math.random() - 0.5) * spread }); } catch {}
  }
};
const top = b => ({ x: b.x + 0.5, y: b.y + 1.05, z: b.z + 0.5 });
const tipOf = b => Number(b.permutation.getState(TIP) ?? 0);
function setTip(block, tip, age = 0) {
  try { block.setPermutation(block.permutation.withState(TIP, tip).withState(AGE, age)); } catch {}
}
function takeOne(player, slot) {
  if (creative(player)) return;
  const it = slot.getItem();
  if (!it) return;
  if (it.amount <= 1) slot.setItem(undefined); else { it.amount -= 1; slot.setItem(it); }
}
function give(player, stack) {
  try {
    const left = player.getComponent("minecraft:inventory")?.container?.addItem(stack);
    if (left) player.dimension.spawnItem(left, player.location);
  } catch { try { player.dimension.spawnItem(stack, player.location); } catch {} }
}

// --------------------------------------------------------------- tip-ups a player has set
// A tip-up counts against the limit of the player who set it, and only while it is still theirs:
// once anyone takes it back (or sets their own in that hole), it leaves the old owner's count.
const ownerOf = k => { try { return world.getDynamicProperty(OWNER + k); } catch { return undefined; } };
const setOwner = (k, id) => { try { world.setDynamicProperty(OWNER + k, id); } catch {} };
function owned(player) {
  try { const v = JSON.parse(player.getDynamicProperty(OWNED) ?? "[]"); return Array.isArray(v) ? v : []; } catch { return []; }
}
function setOwned(player, list) { try { player.setDynamicProperty(OWNED, JSON.stringify(list)); } catch {} }
/** Keep only the holes that still hold this player's tip-up (unloaded ones: by the hole's owner
 *  record; holes set before v1.3.3 have none and are kept while unloaded, as before). */
function liveOwned(player) {
  const out = [];
  for (const k of owned(player)) {
    const who = ownerOf(k);
    if (who !== undefined && who !== player.id) continue;
    const [dimId, x, y, z] = k.split(/:(?=-?\d)/);
    let b;
    try { b = world.getDimension(dimId).getBlock({ x: Number(x), y: Number(y), z: Number(z) }); } catch {}
    if (b === undefined || (b.typeId === ICE_HOLE && tipOf(b) > 0)) out.push(k);
  }
  return out;
}

// --------------------------------------------------------------- landing a tip-up fish
function landTipUp(player, block) {
  const dim = block.dimension;
  const ctx = analyzeWater(dim, { x: block.x + 0.5, y: block.y - 0.1, z: block.z + 0.5 });
  const id = rollCatch({ ...ctx, slot: timeSlot(), raining: isRaining(dim), tier: 1, school: false, rare: 1 });
  let cm = rollSize(id, 1);
  let cls = cm !== undefined ? classOf(id, cm) : 0;
  if (cls === LARGE) {                     // a tip-up's light line never holds a big one
    const r = rangeOf(id);
    cm = Math.round(r[0] + (r[1] - r[0]) * 0.6);
    cls = MEDIUM;
  }
  const rec = cm !== undefined ? recordCatch(player, id, cm) : recordCatch(player, id);
  const stack = new ItemStack(id, 1);
  if (cls) { try { stack.setLore(loreFor(cls, rec.newBest ? cm : undefined)); } catch {} }
  if (rec.newBest || tryStore(player, id, 1, cls) !== 0) give(player, stack);
  const at = top(block);
  snd(dim, "random.splash", at, 1.2, 0.6);
  fx(dim, "minecraft:water_splash_particle", at, 6);
  if (rec.newBest || rec.first) snd(dim, rec.newBest ? `${NS}.record` : "random.orb", player.location, rec.newBest ? 1.0 : 1.2, 0.6);
  try { dim.spawnEntity("minecraft:xp_orb", player.location); } catch {}
}

const iceHole = {
  onPlayerInteract({ block, player }) {
    if (!player) return;
    const slot = mainhand(player);
    const held = slot?.hasItem() ? slot.getItem() : undefined;
    const tip = tipOf(block);
    const dim = block.dimension, at = top(block);
    if (tip === 2) {                                                       // a bite: take the fish
      landTipUp(player, block);
      setTip(block, 1);
      return;
    }
    if (held && RODS[held.typeId]) { useRodItem(player, held); return; }   // fish through the hole
    if (tip === 0 && held?.typeId === TIP_UP) {                            // set a tip-up
      const list = liveOwned(player);
      if (list.length >= TIP_UP_LIMIT) { snd(dim, "dig.wood", at, 0.6, 0.5); setOwned(player, list); return refuse(player, "tipup_limit", TIP_UP_LIMIT); }
      takeOne(player, slot);
      if (!list.includes(keyOf(block))) list.push(keyOf(block));
      setOwned(player, list);
      setOwner(keyOf(block), player.id);
      setTip(block, 1);
      snd(dim, "dig.wood", at, 1.2);
      fx(dim, "minecraft:water_splash_particle", at, 3);
      return;
    }
    if (tip === 1 && !held) {                                              // take the tip-up back
      setTip(block, 0);
      give(player, new ItemStack(TIP_UP, 1));
      setOwned(player, owned(player).filter(k => k !== keyOf(block)));
      setOwner(keyOf(block), "");
      snd(dim, "dig.wood", at, 0.9);
      return;
    }
    if (tip === 1) return refuse(player, held?.typeId === TIP_UP ? "tipup_set" : "tipup_empty_hand");
    return refuse(player, "icehole_use");
  },

  onPlayerBreak({ block, brokenBlockPermutation, player }) {
    if (player && creative(player)) { if (Number(brokenBlockPermutation.getState(TIP) ?? 0) > 0) setOwner(keyOf(block), ""); return; }
    dropHole(block.dimension, block, brokenBlockPermutation);
  },

  onTick({ block }) {
    const tip = tipOf(block);
    if (!tip) return;
    const dim = block.dimension, at = top(block);
    if (!isWater(dim.getBlock({ x: block.x, y: block.y - 1, z: block.z }))) return;
    if (tip === 1) {
      if (Math.random() < BITE_CHANCE) {
        setTip(block, 2, 0);
        if (someoneNear(dim, at)) snd(dim, "block.bell.hit", at, 1.7, 0.7);
        fx(dim, "minecraft:water_splash_particle", { x: at.x, y: block.y, z: at.z }, 5);
      }
      return;
    }
    const age = (Number(block.permutation.getState(AGE) ?? 0) + 1) % RING_STEPS;   // a hooked fish stays (v1.6.4)
    setTip(block, 2, age);
    if (age === 0 && someoneNear(dim, at)) snd(dim, "block.bell.hit", at, 1.7, 0.5);   // the flag still waving
  },
};

// --------------------------------------------------------------- the auger
const lastDrill = new Map();
world.beforeEvents.playerInteractWithBlock.subscribe(ev => {
  const { player, block, itemStack } = ev;
  if (itemStack?.typeId !== AUGER || !DRILLABLE.has(block?.typeId)) return;
  ev.cancel = true;
  const now = system.currentTick;
  if (now - (lastDrill.get(player.id) ?? -99) < 10) return;
  lastDrill.set(player.id, now);
  const loc = { x: block.x, y: block.y, z: block.z }, dim = block.dimension;
  system.run(() => {
    try {
      if (!isWater(dim.getBlock({ x: loc.x, y: loc.y - 1, z: loc.z }))) { snd(dim, "dig.glass", loc, 0.6, 0.5); refuse(player, "auger_no_water"); return; }
      dim.getBlock(loc)?.setType(ICE_HOLE);
      const c = { x: loc.x + 0.5, y: loc.y + 1, z: loc.z + 0.5 };
      snd(dim, "dig.glass", c, 1.3);
      snd(dim, "random.splash", c, 1.4, 0.4);
      fx(dim, "minecraft:snowflake_particle", c, 8, 0.8);
      wearAuger(player);
    } catch {}
  });
});

function wearAuger(player) {
  if (creative(player)) return;
  const slot = mainhand(player);
  if (!slot?.hasItem() || slot.typeId !== AUGER) return;
  try {
    const stack = slot.getItem();
    const dur = stack.getComponent("minecraft:durability");
    if (!dur) return;
    if (dur.damage + 1 >= dur.maxDurability) { slot.setItem(undefined); snd(player.dimension, "random.break", player.location); return; }
    dur.damage += 1;
    slot.setItem(stack);
  } catch {}
}

world.afterEvents.playerLeave.subscribe(ev => lastDrill.delete(ev.playerId));

// v1.6.3 (F1): the tip-up comes back however the hole goes. perm undefined = only the owner record is left.
function dropHole(dim, pos, perm) {
  const k = `${dim.id}:${pos.x}:${pos.y}:${pos.z}`;
  const who = ownerOf(k);
  const had = perm ? Number(perm.getState(TIP) ?? 0) > 0 : typeof who === "string" && who !== "";
  if (who !== undefined) { try { world.setDynamicProperty(OWNER + k, undefined); } catch {} }
  if (had) spawnAll(dim, pos, [new ItemStack(TIP_UP, 1)]);
}
registerStation(ICE_HOLE, dropHole);
registerRecords(OWNER, ICE_HOLE, (dim, pos) => dropHole(dim, pos, undefined));

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(`${NS}:ice_hole`, iceHole);
});
