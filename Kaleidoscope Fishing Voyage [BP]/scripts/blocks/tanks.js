// ## Fish Tank (one block) and Large Fish Tank (two blocks, up to four fish). v1.3: the fish swim.
// The tank keeps what is in it: block states for the Fish Tank (as since v1.0), a world property for
// the Large Fish Tank. The swimming fish are display entities (tank_fish: no hitbox, no AI) standing
// at the tank's centre and posed by the resource pack's animations; this script keeps exactly one
// entity per fish. Tanks tick every 5 s and put back a missing fish (a /kill, or a tank from v1.2
// seen for the first time); a sweep every 10 s clears fish whose tank went without a player breaking
// it (a piston, an explosion, a command) and drops those fish where the tank stood.
// No text anywhere: the fish, splashes and sounds show everything.
// v1.3.3: a record fish keeps its "★ N cm" (and a name tag) while it swims here (keep.js).
import { BlockPermutation, EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { FISH_ALIAS, TANK_FISH } from "../data/generated.js";
import { FIT, LANE, TANK_KIND } from "../data/tank.js";
import { readSize } from "../fishing/size.js";
import { readFishIndex, withFishIndex } from "./fishState.js";
import { fishOut, keepKey, keepOf, stash, unstash } from "./keep.js";
import { readData, writeData } from "./blockData.js";
import { spawnParticle } from "../util/particles.js";
import { refuse } from "../util/hint.js";   // v1.6.4 (F5): a fish that does not go in says why
import { externalTank } from "../fishing/registry.js";

const NS = "kaleidoscope_fishing";
const FISH_ID = `${NS}:tank_fish`;
const SMALL_ID = `${NS}:fish_tank`;
const LARGE_BLOCK = `${NS}:large_fish_tank_block`, LARGE_ITEM = `${NS}:large_fish_tank`;
const SIZE_STATE = `${NS}:size`, PART = `${NS}:part`, DIR = `${NS}:dir`;
const CAP = 4;                                  // fish in a Large Fish Tank
const LEVELS = [0.62, 0.28, 0.9, 0.08];         // where in its height band each slot of the large tank swims
const TURN = { north: 0, east: 1, south: 2, west: 3 };   // quarter turns clockwise, as the block model is turned
const REPLACEABLE = new Set(["minecraft:air", "minecraft:short_grass", "minecraft:fern", "minecraft:snow_layer", "minecraft:leaf_litter"]);
const TAG = "kfv_tank:";                        // kfv_tank:s:x,y,z (Fish Tank) / kfv_tank:l:x,y,z (Large, anchor block)
const canon = id => FISH_ALIAS[id] ?? id;
// 1.5.0: lava creatures live in the Lava Fish Tank (blocks/lava_fish_tank.json: params {"lava": true}); the Lava
// Dragon Koi was allowed in a water tank in 1.4 and still is. Water creatures do not go in the lava tank.
export const LAVA_ONLY = new Set([`${NS}:blazefin`, `${NS}:magma_koi`, `${NS}:lava_eel`, `${NS}:basalt_crab`]);
export const LAVA_OK = new Set([...LAVA_ONLY, `${NS}:lava_dragon_koi`]);
/** The tank index of what is held, if this kind of tank takes it (0 when it does not). Exported for tests. */
export function tankIndex(id, lava = false) {
  const c = canon(id);
  if (TANK_FISH.includes(c)) {
    if (lava ? !LAVA_OK.has(c) : LAVA_ONLY.has(c)) return 0;
    return TANK_FISH.indexOf(c) + 1;
  }
  // 1.5.0 (register_tank): another pack's creature, drawn as its `like`; its item id rides along in the fish's keep
  const e = externalTank(id);
  if (!e || (e.tank !== "both" && (e.tank === "lava") !== lava)) return 0;
  return TANK_FISH.indexOf(e.like) + 1;
}
/** What a fish going in keeps: its marks and name, and for another pack's creature its id and scale. */
function keepFor(stack) {
  const k = keepOf(stack);
  const e = TANK_FISH.includes(canon(stack.typeId)) ? undefined : externalTank(stack.typeId);
  return e ? { ...(k ?? {}), ext: stack.typeId, ...(e.scale !== 1 ? { sc: e.scale } : {}) } : k;
}
const peek = key => { try { const v = world.getDynamicProperty(key); return typeof v === "string" ? JSON.parse(v) : undefined; } catch { return undefined; } };

const mainhand = p => p.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
const creative = p => { try { return p.getGameMode() === GameMode.Creative; } catch { return false; } };
function takeOne(player, slot) {
  if (creative(player)) return;
  const it = slot.getItem();
  if (!it) return;
  if (it.amount <= 1) slot.setItem(undefined); else { it.amount -= 1; slot.setItem(it); }
}
function give(player, at, stack) {
  try {
    const left = player.getComponent("minecraft:inventory")?.container?.addItem(stack);
    if (left) player.dimension.spawnItem(left, at);
  } catch { try { player.dimension.spawnItem(stack, at); } catch {} }
}
const snd = (dim, at, id, pitch = 1, volume = 0.8) => { try { dim.playSound(id, at, { pitch, volume }); } catch {} };
function splash(dim, at, n = 6) {
  for (let i = 0; i < n; i++) {
    try { spawnParticle(dim, "minecraft:water_splash_particle", { x: at.x + (Math.random() - 0.5) * 0.6, y: at.y + 0.8, z: at.z + (Math.random() - 0.5) * 0.6 }); } catch {}
  }
}
/** The item a fish comes out as: ours by index, another pack's by its keep (undefined while that item is missing). */
function fishStack(idx, cls, keep) {
  let s;
  try { s = new ItemStack(keep?.ext ?? TANK_FISH[idx - 1], 1); } catch { return undefined; }
  return fishOut(s, cls, keep);
}

// local -> world, k quarter turns (as feast.js)
function rot(x, z, k) { for (let i = 0; i < ((k % 4) + 4) % 4; i++) [x, z] = [-z, x]; return [x, z]; }
// the way the player looks -> north 0, east 1, south 2, west 3
function facingOf(yaw) {
  const a = ((yaw % 360) + 360) % 360;
  if (a >= 135 && a < 225) return 0;
  if (a >= 225 && a < 315) return 1;
  if (a >= 315 || a < 45) return 2;
  return 3;
}

// ---------------------------------------------------------------- the swimming fish
function fishEntities(dim, tag, centre) {
  try { return dim.getEntities({ type: FISH_ID, tags: [tag], location: centre, maxDistance: 2.5 }); } catch { return undefined; }
}
const remove = e => { try { e.remove(); } catch {} };
const prop = (e, k) => { try { return e.getDynamicProperty(k); } catch { return undefined; } };

function spawnFish(dim, tag, centre, turn, big, slot, [idx, cls, keep]) {
  const spec = idx - 1;
  const fits = FIT[spec]?.[big ? 1 : 0];
  if (!fits) return;
  const [scale0, span, lo, hi] = fits[cls] ?? fits[2];
  const scale = Math.min(100, Math.round(scale0 * (Number(keep?.sc) || 1)));   // 1.5.0: a registered creature's own scale
  let e;
  try { e = dim.spawnEntity(FISH_ID, centre, { initialRotation: 0 }); }
  catch { try { e = dim.spawnEntity(FISH_ID, centre); } catch { return; } }
  try { e.teleport(centre, { rotation: { x: 0, y: 0 } }); } catch {}
  const kind = TANK_KIND[spec] ?? 0;
  const props = {
    species: spec, kind, seed: Math.floor(Math.random() * 8), turn, tank: big ? 1 : 0, scale, span,
    level: Math.round(lo + (hi - lo) * (big ? LEVELS[slot] ?? 0.5 : 0.5)),
    lane: 60 + Math.round((big ? LANE[kind] ?? 0 : 0) * 10),
  };
  for (const [k, v] of Object.entries(props)) { try { e.setProperty(`${NS}:${k}`, v); } catch {} }
  try {
    e.addTag(tag);
    e.setDynamicProperty("kfv:slot", slot);
    e.setDynamicProperty("kfv:idx", idx);
    e.setDynamicProperty("kfv:cls", cls);
  } catch {}
}

/** Make the entities at a tank match its fish list [[index, class, keep?], ...] (slot = list position). */
function syncFish(dim, tag, centre, turn, big, fish) {
  const have = fishEntities(dim, tag, centre);
  if (!have) return;
  const kept = new Map();
  for (const e of have) {
    const slot = prop(e, "kfv:slot"), f = fish[slot];
    let turnNow;
    try { turnNow = e.getProperty(`${NS}:turn`); } catch {}
    if (!f || kept.has(slot) || prop(e, "kfv:idx") !== f[0] || prop(e, "kfv:cls") !== f[1] || turnNow !== turn) { remove(e); continue; }
    kept.set(slot, e);
    // a fish that was pushed or turned is put back (the model keeps its axes only at yaw 0)
    try {
      const l = e.location, r = e.getRotation();
      if (Math.abs(l.x - centre.x) + Math.abs(l.y - centre.y) + Math.abs(l.z - centre.z) > 0.05 || Math.abs(r.y) > 1)
        e.teleport(centre, { rotation: { x: 0, y: 0 } });
    } catch {}
  }
  fish.forEach((f, slot) => { if (!kept.has(slot)) spawnFish(dim, tag, centre, turn, big, slot, f); });
}

function clearFish(dim, tag, centre) {
  for (const e of fishEntities(dim, tag, centre) ?? []) remove(e);
}

// ---------------------------------------------------------------- Fish Tank (one block)
const smallTag = b => `${TAG}s:${b.x},${b.y},${b.z}`;
const smallCentre = b => ({ x: b.x + 0.5, y: b.y, z: b.z + 0.5 });
// v1.5.5: what swims here is kept in blockData ("tk": { idx, cls }); the fish / fish_bank / size states are
// still written for 1.5.4 and read only when a tank has no record yet (it is copied over on its next tick).
function smallData(block, perm = block.permutation) {
  const d = readData("tk", block.dimension, block);
  if (d) return { idx: Number(d.idx) || 0, cls: Number(d.cls) || 0, saved: true };
  return { idx: readFishIndex(perm), cls: Number(perm.getState(SIZE_STATE) ?? 0), saved: false };
}
function saveSmall(block, idx, cls) {
  writeData("tk", block.dimension, block, idx > 0 ? { idx, cls } : undefined);
}
function smallFish(block, perm) {
  const { idx, cls } = smallData(block, perm);
  return idx > 0 && idx <= TANK_FISH.length ? [[idx, cls, peek(keepKey("tk", block.dimension, block))]] : [];
}
function syncSmall(block, perm = block.permutation) {
  syncFish(block.dimension, smallTag(block), smallCentre(block), TURN[perm.getState("minecraft:cardinal_direction")] ?? 0, false, smallFish(block, perm));
}

const fishTank = {
  onPlayerInteract({ block, player }, arg) {
    if (!player) return;
    const slot = mainhand(player);
    const held = slot?.hasItem() ? slot.typeId : "";
    const now = smallData(block);
    const cur = now.idx;
    const idx = tankIndex(held, !!arg?.params?.lava);
    const at = smallCentre(block);
    if (idx > 0 && cur === 0) {
      const stack = slot.getItem();
      const cls = readSize(stack).cls;
      stash(keepKey("tk", block.dimension, block), keepFor(stack));
      takeOne(player, slot);
      saveSmall(block, idx, cls);
      const perm = withFishIndex(block.permutation, idx).withState(SIZE_STATE, cls);
      block.setPermutation(perm);
      snd(block.dimension, at, "bucket.empty_fish", 1.0);
      splash(block.dimension, at);
      syncSmall(block, perm);
      return;
    }
    if (!held && cur > 0) {
      const cls = now.cls;
      const out = fishStack(cur, cls, peek(keepKey("tk", block.dimension, block)));
      if (!out) return refuse(player, "tank_pack_gone");                 // another pack's creature, its pack gone: it stays
      unstash(keepKey("tk", block.dimension, block));
      give(player, block.center(), out);
      saveSmall(block, 0, 0);
      const perm = withFishIndex(block.permutation, 0).withState(SIZE_STATE, 0);
      block.setPermutation(perm);
      snd(block.dimension, at, "bucket.fill_fish", 1.0);
      splash(block.dimension, at, 4);
      syncSmall(block, perm);
      return;
    }
    if (held) refuse(player, idx > 0 ? "tank_occupied" : LAVA_OK.has(canon(held)) !== !!arg?.params?.lava ? "tank_wrong_kind" : "tank_not_fish");
  },
  onPlayerBreak({ block, brokenBlockPermutation, player }) {
    const { idx: cur, cls } = smallData(block, brokenBlockPermutation);
    saveSmall(block, 0, 0);
    clearFish(block.dimension, smallTag(block), smallCentre(block));
    const keep = unstash(keepKey("tk", block.dimension, block));
    const out = cur > 0 && cur <= TANK_FISH.length && !creative(player) ? fishStack(cur, cls, keep) : undefined;
    if (out) { try { block.dimension.spawnItem(out, block.center()); } catch {} }
  },
  onTick({ block }) {
    const d = smallData(block);                                  // v1.5.5: copy a 1.5.4 tank's fish into its record
    if (!d.saved && d.idx > 0) saveSmall(block, d.idx, d.cls);
    syncSmall(block);
  },
};

// ---------------------------------------------------------------- Large Fish Tank (two blocks)
// Part 0 is the anchor; part 1 stands one block along the model's +x (rot(1, 0, dir)). The front of
// the model (north, -z) faces the player who placed it; the tank reaches to that player's right.
function largeOf(loc, perm) {
  const part = Number(perm.getState(PART) ?? 0), k = Number(perm.getState(DIR) ?? 0);
  const [dx, dz] = rot(1, 0, k);
  const a = part === 0 ? { x: loc.x, y: loc.y, z: loc.z } : { x: loc.x - dx, y: loc.y, z: loc.z - dz };
  return {
    k, anchor: a, other: { x: a.x + dx, y: a.y, z: a.z + dz },
    // a hair towards the anchor, so the fish always stand in the anchor's block (and chunk)
    centre: { x: a.x + 0.5 + dx * 0.499, y: a.y, z: a.z + 0.5 + dz * 0.499 },
    tag: `${TAG}l:${a.x},${a.y},${a.z}`,
  };
}
const largeKey = (dim, a) => `${NS}:lt:${dim.id}:${a.x},${a.y},${a.z}`;
function readLarge(dim, t) {
  try {
    const v = JSON.parse(world.getDynamicProperty(largeKey(dim, t.anchor)) ?? "[]");
    return Array.isArray(v) ? v.filter(f => Array.isArray(f) && f[0] > 0 && f[0] <= TANK_FISH.length).slice(0, CAP) : [];
  } catch { return []; }
}
function writeLarge(dim, t, fish) {
  try { world.setDynamicProperty(largeKey(dim, t.anchor), fish.length ? JSON.stringify(fish) : undefined); } catch {}
}
const syncLarge = (dim, t, fish = readLarge(dim, t)) => syncFish(dim, t.tag, t.centre, t.k, true, fish);

function dropAll(dim, t, withTank) {
  const fish = readLarge(dim, t);
  writeLarge(dim, t, []);
  const at = { x: t.centre.x, y: t.centre.y + 0.5, z: t.centre.z };
  if (withTank) { try { dim.spawnItem(new ItemStack(LARGE_ITEM, 1), at); } catch {} }
  for (const [idx, cls, keep] of fish) { const out = fishStack(idx, cls, keep); if (out) { try { dim.spawnItem(out, at); } catch {} } }
}

const largeTank = {
  onPlayerInteract({ block, player }) {
    if (!player) return;
    const dim = block.dimension;
    const t = largeOf(block.location, block.permutation);
    const fish = readLarge(dim, t);
    const slot = mainhand(player);
    const held = slot?.hasItem() ? slot.typeId : "";
    const idx = tankIndex(held);
    if (idx > 0) {
      if (fish.length >= CAP) { snd(dim, t.centre, "random.click", 0.6, 0.5); return refuse(player, "tank_full", CAP); }
      const stack = slot.getItem();
      const cls = readSize(stack).cls, keep = keepFor(stack);
      takeOne(player, slot);
      fish.push(keep ? [idx, cls, keep] : [idx, cls]);
      writeLarge(dim, t, fish);
      snd(dim, t.centre, "bucket.empty_fish", 0.9 + fish.length * 0.05);
      splash(dim, t.centre, 8);
      syncLarge(dim, t, fish);
      return;
    }
    if (!held && fish.length) {
      const [i, cls, keep] = fish[fish.length - 1];
      const out = fishStack(i, cls, keep);
      if (!out) return refuse(player, "tank_pack_gone");
      fish.pop();
      writeLarge(dim, t, fish);
      give(player, block.center(), out);
      snd(dim, t.centre, "bucket.fill_fish", 1.0);
      splash(dim, t.centre, 4);
      syncLarge(dim, t, fish);
      return;
    }
    if (held) refuse(player, "tank_not_fish");
  },
  onPlayerBreak({ block, brokenBlockPermutation, player }) {
    const dim = block.dimension;
    const t = largeOf(block.location, brokenBlockPermutation);
    for (const c of [t.anchor, t.other]) {
      try { const b = dim.getBlock(c); if (b?.typeId === LARGE_BLOCK) b.setType("minecraft:air"); } catch {}
    }
    clearFish(dim, t.tag, t.centre);
    if (creative(player)) { writeLarge(dim, t, []); return; }
    dropAll(dim, t, true);
  },
  onTick({ block }) {
    if (Number(block.permutation.getState(PART) ?? 0) !== 0) return;
    const dim = block.dimension;
    const t = largeOf(block.location, block.permutation);
    // the other half went missing (a command): put it back if there is room
    try {
      const o = dim.getBlock(t.other);
      if (o && o.typeId !== LARGE_BLOCK && REPLACEABLE.has(o.typeId))
        o.setPermutation(BlockPermutation.resolve(LARGE_BLOCK, { [PART]: 1, [DIR]: t.k }));
    } catch {}
    syncLarge(dim, t);
  },
};

// ---------------------------------------------------------------- placing a Large Fish Tank
function placeLarge(player, clicked, face) {
  const off = { Up: [0, 1, 0], Down: [0, -1, 0], North: [0, 0, -1], South: [0, 0, 1], East: [1, 0, 0], West: [-1, 0, 0] }[face] ?? [0, 1, 0];
  const base = REPLACEABLE.has(clicked.typeId) && clicked.typeId !== "minecraft:air"
    ? clicked.location : { x: clicked.x + off[0], y: clicked.y + off[1], z: clicked.z + off[2] };
  const k = (facingOf(player.getRotation().y) + 2) % 4;
  const [rx, rz] = rot(-1, 0, k);                  // the player's right
  const cells = [{ part: 0, x: base.x + rx, y: base.y, z: base.z + rz }, { part: 1, ...base }];
  const dim = player.dimension;
  let ok = true, supported = false;
  for (const c of cells) {
    let b;
    try { b = dim.getBlock(c); } catch { ok = false; break; }
    if (!b || !REPLACEABLE.has(b.typeId)) { ok = false; break; }
    try { const below = b.below(); if (below && !below.isAir && !below.isLiquid) supported = true; } catch {}
  }
  const at = { x: base.x + 0.5, y: base.y + 0.5, z: base.z + 0.5 };
  if (!ok || !supported) { snd(dim, at, "random.click", 0.6, 0.5); return; }
  for (const c of cells) {
    try { dim.getBlock(c).setPermutation(BlockPermutation.resolve(LARGE_BLOCK, { [PART]: c.part, [DIR]: k })); } catch {}
  }
  // a tank placed where an old one stood starts empty
  try { writeLarge(dim, largeOf(cells[0], BlockPermutation.resolve(LARGE_BLOCK, { [PART]: 0, [DIR]: k })), []); } catch {}
  snd(dim, at, "dig.wood", 1.1);
  snd(dim, at, "bucket.empty_water", 1.0, 0.6);
  if (!creative(player)) {
    try {
      const slot = mainhand(player);
      const it = slot.getItem();
      if (it?.typeId === LARGE_ITEM) { if (it.amount <= 1) slot.setItem(undefined); else { it.amount -= 1; slot.setItem(it); } }
    } catch {}
  }
}

world.beforeEvents.playerInteractWithBlock.subscribe(ev => {
  if (ev.itemStack?.typeId !== LARGE_ITEM) return;
  ev.cancel = true;
  if (!ev.isFirstEvent) return;
  const player = ev.player, clicked = ev.block, face = ev.blockFace;
  system.run(() => { try { placeLarge(player, clicked, face); } catch {} });
});

// ---------------------------------------------------------------- fish whose tank is gone
function sweep() {
  for (const id of ["overworld", "nether", "the_end"]) {
    let dim, list = [];
    try { dim = world.getDimension(id); list = dim.getEntities({ type: FISH_ID }); } catch { continue; }
    for (const e of list) {
      const tag = e.getTags().find(t => t.startsWith(TAG));
      const m = tag && /^kfv_tank:([sl]):(-?\d+),(-?\d+),(-?\d+)$/.exec(tag);
      if (!m) { remove(e); continue; }
      const pos = { x: Number(m[2]), y: Number(m[3]), z: Number(m[4]) };
      let block;
      try { block = dim.getBlock(pos); } catch { continue; }       // not loaded: leave it alone
      if (!block) continue;
      if (m[1] === "s") {
        if (block.typeId === SMALL_ID) continue;
        const idx = prop(e, "kfv:idx"), cls = prop(e, "kfv:cls") ?? 0;
        const keep = unstash(keepKey("tk", dim, pos));
        writeData("tk", dim, pos, undefined);                      // v1.5.5: the tank's record goes too
        const out = typeof idx === "number" && idx > 0 && idx <= TANK_FISH.length ? fishStack(idx, cls, keep) : undefined;
        if (out) { try { dim.spawnItem(out, e.location); } catch {} }
        remove(e);
      } else {
        if (block.typeId === LARGE_BLOCK && Number(block.permutation.getState(PART) ?? 0) === 0) continue;
        const t = largeOf(pos, BlockPermutation.resolve(LARGE_BLOCK, { [PART]: 0, [DIR]: Number(e.getProperty(`${NS}:turn`) ?? 0) }));
        dropAll(dim, t, false);                                     // once: the list is cleared
        remove(e);
      }
    }
  }
}
system.runInterval(() => { try { sweep(); } catch {} }, 200);

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(`${NS}:fish_tank`, fishTank);
  blockComponentRegistry.registerCustomComponent(`${NS}:large_fish_tank`, largeTank);
});
