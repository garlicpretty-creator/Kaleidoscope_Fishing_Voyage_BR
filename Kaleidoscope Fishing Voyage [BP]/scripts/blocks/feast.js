// ## Multi-block feasts (Sashimi Boat 1x3, Seafood Platter 3x3).
// The item is placed by this script (needs the whole footprint free); every block of the
// feast is eaten on its own, two bites each, like Cookery's placeable foods. When every
// block is empty, one more use clears the feast and returns its container. Breaking any
// block removes the whole feast (an untouched feast drops back as its item).
// No text anywhere: sounds and the model show everything.
// v1.3.3: the round and square feasts (Seafood Platter, Feast Pot, Skewer Grill, Dim Sum Steamer,
// Temaki Stand, Oden Pot; FEASTS "face") turn their front to the player who sets them down.
import { BlockPermutation, EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { FEASTS, FOOD_EFFECTS } from "../data/generated.js";
import { spawnParticle } from "../util/particles.js";

const NS = "kaleidoscope_fishing";
const PART = `${NS}:part`, STAGE = `${NS}:food_stage`, DIR = `${NS}:dir`;
const SNEAK_KEY = "kc:sneak_to_place_food";     // Cookery's own per-player setting
const ITEM_TO_BLOCK = Object.fromEntries(Object.entries(FEASTS).map(([b, d]) => [d.item, b]));
const REPLACEABLE = new Set(["minecraft:air", "minecraft:short_grass", "minecraft:fern", "minecraft:snow_layer", "minecraft:leaf_litter"]);

// local -> world, k quarter turns (must match tools/models.py rot_xz)
function rot(x, z, k) { for (let i = 0; i < ((k % 4) + 4) % 4; i++) [x, z] = [-z, x]; return [x, z]; }

// yaw: 0 south, 90 west, 180 north, -90 east -> k: north 0, east 1, south 2, west 3
function dirFromYaw(yaw) {
  const a = ((yaw % 360) + 360) % 360;
  if (a >= 135 && a < 225) return 0;
  if (a >= 225 && a < 315) return 1;
  if (a >= 315 || a < 45) return 2;
  return 3;
}

function feastCells(def, centre, k) {
  return def.parts.map(([part, lx, lz]) => {
    const [wx, wz] = rot(lx, lz, k);
    return { part, x: centre.x + wx, y: centre.y, z: centre.z + wz };
  });
}

// From any block of a feast, find the whole structure (only blocks that really belong to it).
function structureOf(dim, loc, typeId, perm) {
  const def = FEASTS[typeId];
  if (!def) return null;
  const part = Number(perm.getState(PART) ?? 0);
  const k = def.dirs.length > 1 ? Number(perm.getState(DIR) ?? 0) : 0;
  const me = def.parts.find(p => p[0] === part);
  if (!me) return null;
  const [wx, wz] = rot(me[1], me[2], k);
  const centre = { x: loc.x - wx, y: loc.y, z: loc.z - wz };
  const cells = feastCells(def, centre, k).map(c => {
    let block;
    try { block = dim.getBlock(c); } catch {}
    const ok = block && block.typeId === typeId && Number(block.permutation.getState(PART) ?? 0) === c.part &&
      (def.dirs.length <= 1 || Number(block.permutation.getState(DIR)) === k);
    return { ...c, block: ok ? block : undefined };
  });
  return { def, k, centre, cells };
}

function centreOf(s) { return { x: s.centre.x + 0.5, y: s.centre.y + 0.4, z: s.centre.z + 0.5 }; }

function drop(dim, ids, at) {
  for (const id of ids) { try { dim.spawnItem(new ItemStack(id, 1), at); } catch {} }
}

function canEat(player) {
  const gm = player.getGameMode();
  if (gm !== GameMode.Survival && gm !== GameMode.Adventure) return true;
  const h = player.getComponent("minecraft:player.hunger");
  return !!h && h.currentValue < h.effectiveMax;
}
function feed(player, nutrition, satMod) {
  const h = player.getComponent("minecraft:player.hunger");
  const s = player.getComponent("minecraft:player.saturation");
  if (h) h.setCurrentValue(Math.min(h.currentValue + nutrition, h.effectiveMax));
  if (s) s.setCurrentValue(Math.min(s.currentValue + nutrition * 2 * satMod, s.effectiveMax));
}

// ---------------------------------------------------------------- placing
function canPlace(dim, cells) {
  let supported = false;
  for (const c of cells) {
    let b;
    try { b = dim.getBlock(c); } catch { return false; }
    if (!b || !REPLACEABLE.has(b.typeId)) return false;
    try { const below = b.below(); if (below && !below.isAir && !below.isLiquid) supported = true; } catch {}
  }
  return supported;
}

function place(player, clicked, face, itemId) {
  const blockId = ITEM_TO_BLOCK[itemId];
  const def = FEASTS[blockId];
  const off = { Up: [0, 1, 0], Down: [0, -1, 0], North: [0, 0, -1], South: [0, 0, 1], East: [1, 0, 0], West: [-1, 0, 0] }[face] ?? [0, 1, 0];
  const anchor = REPLACEABLE.has(clicked.typeId) && clicked.typeId !== "minecraft:air"
    ? clicked.location
    : { x: clicked.x + off[0], y: clicked.y + off[1], z: clicked.z + off[2] };
  const look = dirFromYaw(player.getRotation().y);
  // Long feasts point away from the player; "face" feasts turn their front (model north) to the player.
  const k = def.dirs.length > 1 ? (def.face ? (look + 2) % 4 : look) : 0;
  // The boat starts at the clicked spot and reaches away from the player; the platter is centred on it.
  let centre = anchor;
  if (def.dirs.length > 1 && !def.face) {
    const [fx, fz] = rot(0, -1, k);
    centre = { x: anchor.x + fx, y: anchor.y, z: anchor.z + fz };
  }
  const cells = feastCells(def, centre, k);
  const dim = player.dimension;
  if (!canPlace(dim, cells)) {
    try { dim.playSound("random.click", { x: anchor.x + 0.5, y: anchor.y + 0.5, z: anchor.z + 0.5 }, { pitch: 0.6, volume: 0.5 }); } catch {}
    return;
  }
  for (const c of cells) {
    // one-block feasts have no part state, the boat (never eaten) no food_stage: a state needs 2+ values
    const states = {};
    if (def.parts.length > 1) states[PART] = c.part;
    if ((def.bites ?? 2) > 0) states[STAGE] = 0;
    if (def.dirs.length > 1) states[DIR] = k;
    try { dim.getBlock(c).setPermutation(BlockPermutation.resolve(blockId, states)); } catch {}
  }
  try { dim.playSound("dig.wood", { x: centre.x + 0.5, y: centre.y + 0.5, z: centre.z + 0.5 }, { pitch: 1.1 }); } catch {}
  if (player.getGameMode() !== GameMode.Creative) {
    try {
      const slot = player.getComponent("minecraft:equippable").getEquipmentSlot(EquipmentSlot.Mainhand);
      const it = slot.getItem();
      if (it?.typeId === itemId) { if (it.amount <= 1) slot.setItem(undefined); else { it.amount -= 1; slot.setItem(it); } }
    } catch {}
  }
}

world.beforeEvents.playerInteractWithBlock.subscribe(ev => {
  const id = ev.itemStack?.typeId;
  if (!id || !ITEM_TO_BLOCK[id]) return;
  ev.cancel = true;
  if (!ev.isFirstEvent) return;
  const player = ev.player;
  let sneakOnly = false;
  try { sneakOnly = player.getDynamicProperty(SNEAK_KEY) === true; } catch {}
  if (sneakOnly && !player.isSneaking) return;
  const clicked = ev.block, face = ev.blockFace;
  system.run(() => { try { place(player, clicked, face, id); } catch {} });
});

// ---------------------------------------------------------------- eating / removing
function clearAll(s) {
  for (const c of s.cells) { try { c.block?.setType("minecraft:air"); } catch {} }
}

// v1.3: eating together. Everyone who took a bite of the same feast in the last minute and still
// stands within 5 blocks of it shares a table. Two or more at a table: all of them get Health
// Boost and a little Regeneration; three or more: Haste too. Once per player every 5 minutes.
const TABLE_TIME = 1200, TABLE_RANGE = 5, SHARE_COOLDOWN = 6000;
const diners = new Map();        // feast key -> Map(player id -> tick of last bite)
const lastShare = new Map();     // player id -> tick
function shareFeast(s, player, dim) {
  const c = centreOf(s), now = system.currentTick;
  const key = `${dim.id}:${Math.floor(c.x)}:${Math.floor(c.y)}:${Math.floor(c.z)}`;
  let table = diners.get(key);
  if (!table) diners.set(key, table = new Map());
  table.set(player.id, now);
  for (const [id, at] of table) if (now - at > TABLE_TIME) table.delete(id);
  let near = [];
  try { near = dim.getPlayers({ location: c, maxDistance: TABLE_RANGE }); } catch {}
  const seated = near.filter(p => table.has(p.id));
  if (seated.length < 2) return;
  let shared = false;
  for (const p of seated) {
    if (now - (lastShare.get(p.id) ?? -SHARE_COOLDOWN) < SHARE_COOLDOWN) continue;
    lastShare.set(p.id, now);
    shared = true;
    try { p.addEffect("health_boost", 2400, { amplifier: 0 }); } catch {}
    try { p.addEffect("regeneration", 200, { amplifier: 0 }); } catch {}
    if (seated.length >= 3) { try { p.addEffect("haste", 2400, { amplifier: 0 }); } catch {} }
  }
  if (!shared) return;
  for (let i = 0; i < 6; i++) {
    try { spawnParticle(dim, `${NS}:feast_aroma`, { x: c.x + (Math.random() - 0.5) * 1.5, y: c.y + 0.8, z: c.z + (Math.random() - 0.5) * 1.5 }); } catch {}
  }
  try { dim.playSound("random.levelup", c, { pitch: 1.6, volume: 0.35 }); } catch {}
  if (diners.size > 64) for (const [k, m] of diners) if (![...m.values()].some(at => now - at <= TABLE_TIME)) diners.delete(k);
}

const feastComponent = {
  onPlayerInteract({ block, player }) {
    if (!player || player.isSneaking) return;
    const s = structureOf(block.dimension, block.location, block.typeId, block.permutation);
    if (!s || s.def.decor) return;            // the fishing boat is only for looking at
    const stage = Number(block.permutation.getState(STAGE) ?? 0);
    const dim = block.dimension;
    const MAX = s.def.bites ?? 2;
    if (stage >= MAX) {
      // empty block: once the whole feast is empty, clear it and give the container back
      if (s.cells.every(c => !c.block || Number(c.block.permutation.getState(STAGE) ?? 0) >= MAX)) {
        clearAll(s);
        drop(dim, s.def.remains, centreOf(s));
        try { dim.playSound("dig.wood", centreOf(s)); } catch {}
      }
      return;
    }
    if (!canEat(player)) return;
    try { dim.playSound("random.eat", block.center()); } catch {}
    feed(player, s.def.nutrition, s.def.saturation);
    for (const e of FOOD_EFFECTS[s.def.item] ?? []) {
      try { player.addEffect(e.effect, e.duration, { amplifier: e.amplifier ?? 0 }); } catch {}
    }
    block.setPermutation(block.permutation.withState(STAGE, stage + 1));
    try { shareFeast(s, player, dim); } catch {}
    if (stage + 1 >= MAX) { try { dim.playSound("dig.wood", block.center(), { volume: 0.5 }); } catch {} }
  },
  onPlayerBreak({ block, brokenBlockPermutation, player }) {
    const typeId = brokenBlockPermutation.type.id;
    const s = structureOf(block.dimension, block.location, typeId, brokenBlockPermutation);
    if (!s) return;
    const untouched = Number(brokenBlockPermutation.getState(STAGE) ?? 0) === 0 &&
      s.cells.every(c => !c.block || Number(c.block.permutation.getState(STAGE) ?? 0) === 0);
    clearAll(s);
    if (player?.getGameMode() === GameMode.Creative) return;
    drop(block.dimension, untouched ? [s.def.item] : s.def.remains, centreOf(s));
  },
};

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(`${NS}:feast`, feastComponent);
});
