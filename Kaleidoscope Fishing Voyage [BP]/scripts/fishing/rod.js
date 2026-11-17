// ## Fishing rods (Bamboo / Voyage).
// Immersion rule: no on-screen text. Everything is read from the bobber, the line,
// splashes and sounds. Port rule: the tick loop exists only while a bobber is out.
//
// Phases: flying -> waiting -> bite -> (fight: pull <-> rest) -> landed
//   flying : projectile arc (entity group "flying"); stuck in a block = "ground".
//   waiting: bobber floats still (group "floating"); wake ripples just before a bite.
//   bite   : bobber pulled under + splash. Use the rod now to set the hook.
//   fight  : big fish alternate "pull" (thrash, bobber dragged under and away, line
//            taut) and "rest" (bobber floats, line slack). Reel during rest to bring
//            it closer; reeling during pull strains the line and can snap it.
import { EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { ICE_HOLE, analyzeWater, isRaining, isWater, moonPhase, tideState, timeSlot, weatherOf } from "./water.js";
import { BAITS, LEGEND_SET, LURE, fightLength, rollCatch, rollSize } from "./loot.js";
import { KEEPSAKES, PARTS } from "../data/generated.js";
import { getRecords } from "../journal/records.js";
import { RODS } from "../data/generated.js";
import { recordCatch } from "../journal/records.js";
import { tryStore } from "../tools/basket.js";
import { emitCaught } from "../api/host.js";
import { enchantLevel, luckFactor, luckSize, lureTicks } from "../util/enchant.js";
import { AURORA_BITE, skyAt } from "../world/sky.js";
import { BOAT_DEPTH, LANTERN_BITE, boatOf, lanternOn, stow } from "../world/boat.js";
import { classOf, loreFor } from "./size.js";
import { schoolNear } from "../world/schools.js";
import { effects, readParts } from "./parts.js";
// v1.5: the fishing minigame (Stardew-style). Pure logic in minigame.js, the world switch in minigameSwitch.js.
import { advance, hud, hudDue, newGame } from "./minigame.js";
import { charsetFor, minigameOn } from "./minigameSwitch.js";
import { MG } from "../data/minigame.js";
import { CATCH_BY_ID } from "./loot.js";
import { spawnParticle } from "../util/particles.js";

const NS = "kaleidoscope_fishing";
const BOBBER = `${NS}:bobber`;
const LINE = `${NS}:fishing_line`;
const TICK = 2;
const MAX_AGE = 2400;
const MAX_DIST = 32;

const sessions = new Map();   // playerId -> session
export const _sessionsForTests = sessions;
const lastUse = new Map();
let loop;

// ---------------------------------------------------------------------------
const sound = (dim, id, loc, pitch = 1, volume = 0.8) => { try { dim.playSound(id, loc, { pitch, volume }); } catch {} };
const particle = (dim, id, loc) => { try { spawnParticle(dim, id, loc); } catch {} };
const randInt = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
// The Lava Fishing Rod also fishes in lava: the bobber floats on it, splashes are lava pops.
const isLava = b => b?.typeId === "minecraft:lava" || b?.typeId === "minecraft:flowing_lava";
const liquidOf = rod => (rod.lava ? (b => isWater(b) || isLava(b)) : isWater);
const SPLASH = s => (s.inVoid ? "minecraft:endrod" : s.inLava ? "minecraft:lava_particle" : "minecraft:water_splash_particle");
const WAKE = s => (s.inVoid ? "minecraft:endrod" : s.inLava ? "minecraft:lava_particle" : "minecraft:water_wake_particle");
// v1.2: the Ender Fishing Rod fishes the End's void. Cast off an island's edge: once the bobber
// has dropped below the edge with nothing at all beneath it, it stops and hangs in the air.
function voidBelow(dim, x, y, z) {
  try { return !dim.getBlockFromRay({ x, y, z }, { x: 0, y: -1, z: 0 }, { maxDistance: 96 }); } catch { return false; }
}
const voidContext = (s) => ({ waters: new Set(["void"]), depth: Math.max(0, Math.floor((s.castY ?? s.voidY) - s.voidY)), cold: false, biome: "" });
function lavaContext(dim, loc) {
  const x = Math.floor(loc.x), z = Math.floor(loc.z);
  let y = Math.floor(loc.y), depth = 0;
  try { if (!isLava(dim.getBlock({ x, y, z }))) y -= 1; } catch {}
  for (let yy = y; depth < 16; yy--, depth++) { try { if (!isLava(dim.getBlock({ x, y: yy, z }))) break; } catch { break; } }
  return { waters: new Set(["lava"]), depth, cold: false, biome: "" };
}
const dist2 = (a, b) => (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2;

function mainhand(player) {
  try { return player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand); } catch { return undefined; }
}
export const KEEPSAKE_AGAIN = 0.25;       // a legend caught again drops its keepsake one time in four
/** What a part counts as when a legend asks for a hook or a line (1.5.0: the Emperor Bone Hook is a Bone Hook). */
export const partAs = id => PARTS[id]?.as ?? id;
/** The rod stack in the player's hand (for its enchantments), or undefined. */
function heldRod(player) {
  try { const slot = mainhand(player); return slot?.hasItem() && RODS[slot.typeId] ? slot.getItem() : undefined; } catch { return undefined; }
}
const isCreative = p => { try { return p.getGameMode() === GameMode.Creative; } catch { return false; } };

function findBait(player) {
  try {
    const inv = player.getComponent("minecraft:inventory")?.container;
    for (let i = 0; i < inv.size; i++) { const it = inv.getItem(i); if (it && BAITS[it.typeId]) return it.typeId; }
  } catch {}
  return undefined;
}

function hasItem(player, typeId) {
  try {
    const inv = player.getComponent("minecraft:inventory")?.container;
    for (let i = 0; i < inv.size; i++) if (inv.getItem(i)?.typeId === typeId) return true;
  } catch {}
  return false;
}

/** Takes one typeId from the inventory; false when there is none (creative: true if carried). */
function consumeOne(player, typeId) {
  if (isCreative(player)) return hasItem(player, typeId);
  try {
    const inv = player.getComponent("minecraft:inventory")?.container;
    for (let i = 0; i < inv.size; i++) {
      const it = inv.getItem(i);
      if (it?.typeId !== typeId) continue;
      if (it.amount <= 1) inv.setItem(i, undefined); else { it.amount -= 1; inv.setItem(i, it); }
      return true;
    }
  } catch {}
  return false;
}

// v1.3.3: the bait has to stay in the bag while the line is out. If it is put away, the hook carries
// the next bait in the bag (or none) and the wait for a bite starts over; returns true then.
function baitGone(s) {
  if (!s.bait || s.bait === LURE || hasItem(s.player, s.bait)) return false;
  s.bait = findBait(s.player) ?? (s.fx?.lure ? LURE : undefined);   // a lure hook takes over again
  return true;
}

function damageRod(player, amount = 1) {
  if (isCreative(player)) return;
  const slot = mainhand(player);
  if (!slot?.hasItem() || !RODS[slot.typeId]) return;
  try {
    const stack = slot.getItem();
    const dur = stack.getComponent("minecraft:durability");
    if (!dur) return;
    let unbreaking = 0;
    try { unbreaking = stack.getComponent("minecraft:enchantable")?.getEnchantment("unbreaking")?.level ?? 0; } catch {}
    for (let i = 0; i < amount; i++) {
      if (unbreaking > 0 && Math.random() >= 1 / (unbreaking + 1)) continue;
      if (dur.damage + 1 >= dur.maxDurability) { slot.setItem(undefined); sound(player.dimension, "random.break", player.location); return; }
      dur.damage += 1;
    }
    slot.setItem(stack);
  } catch {}
}

// ---------------------------------------------------------------------------
// The catch is pulled out of the water toward the angler (vanilla's arc formula).
function landCatch(player, s, from) {
  const dim = player.dimension;
  const stack = new ItemStack(s.catchId, 1);
  const rec = s.size !== undefined ? recordCatch(player, s.catchId, s.size) : recordCatch(player, s.catchId);
  // Every sized fish carries its class (◆ / ◆◆ / ◆◆◆); a record also carries its length.
  const cls = s.size !== undefined ? classOf(s.catchId, s.size) : 0;
  if (cls) { try { stack.setLore(loreFor(cls, rec.newBest ? s.size : undefined)); } catch {} }
  const start = { x: from.x, y: from.y + 0.4, z: from.z };
  const pl = player.location;
  // A carried Fish Creel takes ordinary catches straight in; record fish stay out as trophies.
  const legend = LEGEND_SET.has(s.catchId);
  if (legend) { try { stack.setLore([...(stack.getLore() ?? []), "§d✦"]); } catch {} }
  // v1.4: the first legend of its kind brings its keepsake. 1.5.0: a later one does now and then, so tackle made of it can be made again
  if (legend && KEEPSAKES[s.catchId] && (rec.first || Math.random() < KEEPSAKE_AGAIN)) { try { dim.spawnItem(new ItemStack(KEEPSAKES[s.catchId], 1), player.location); } catch {} }
  // 1.5.0: a legend goes into the creel like any catch (it comes out with its ✦); only a record stays in the hand
  let stored = !rec.newBest && tryStore(player, s.catchId, 1, cls) === 0;
  if (!stored && !rec.newBest && stow(player, stack) === undefined) stored = true;   // 1.5.0: the skiff's hold
  emitCaught(player, s.catchId, { via: "rod", size: s.size, cls, rec });       // 1.5.0: other packs hear every landed catch
  if (!stored && (s.inLava || s.inVoid)) {
    // nothing is thrown back over the lava: the catch lands at the angler's feet
    try { dim.spawnItem(stack, player.location).clearVelocity(); } catch {}
  } else if (!stored) {
    let item;
    try { item = dim.spawnItem(stack, start); } catch { return; }
    const dx = pl.x - start.x, dy = pl.y - start.y, dz = pl.z - start.z;
    const d = Math.sqrt(dx * dx + dy * dy + dz * dz);
    try { item.clearVelocity(); item.applyImpulse({ x: dx * 0.1, y: dy * 0.1 + Math.sqrt(d) * 0.08, z: dz * 0.1 }); } catch {}
    system.runTimeout(() => {
      try { if (item.isValid && player.isValid && dist2(item.location, player.location) > 9) item.teleport(player.location); } catch {}
    }, 30);
  }
  try { for (let i = 0, n = randInt(1, 3) + (s.fightTotal ? 1 : 0); i < n; i++) dim.spawnEntity("minecraft:xp_orb", player.location); } catch {}
  sound(dim, s.inLava ? "liquid.lavapop" : "random.splash", start, 1.2, 0.7);
  particle(dim, SPLASH(s), start);
  if (rec.newBest || rec.first) {
    // A quiet flourish instead of a message: sparkles around the angler.
    sound(dim, rec.newBest ? "kaleidoscope_fishing.record" : "random.orb", player.location, rec.newBest ? 1.0 : 1.2, 0.6);
    for (let i = 0; i < (rec.newBest ? 10 : 5); i++) {
      particle(dim, "minecraft:villager_happy", { x: pl.x + (Math.random() - 0.5) * 1.2, y: pl.y + 1 + Math.random(), z: pl.z + (Math.random() - 0.5) * 1.2 });
    }
  }
}

// ---------------------------------------------------------------------------
const clearHud = p => { try { p?.onScreenDisplay?.setActionBar(" "); } catch {} };
function endSession(playerId) {
  const s = sessions.get(playerId);
  if (s?.game) clearHud(s.player);
  sessions.delete(playerId);
  try { if (s?.bobber?.isValid) s.bobber.remove(); } catch {}
  if (sessions.size === 0 && loop !== undefined) { system.clearRun(loop); loop = undefined; }
}

function cast(player, rodId) {
  const rod = RODS[rodId];
  let fx = effects({}), parts = {};
  try { parts = readParts(mainhand(player)?.getItem()); fx = effects(parts); } catch {}
  const dim = player.dimension;
  const eye = player.getHeadLocation();
  const dir = player.getViewDirection();
  let bobber;
  try {
    bobber = dim.spawnEntity(BOBBER, { x: eye.x + dir.x * 0.8, y: eye.y + dir.y * 0.8 - 0.1, z: eye.z + dir.z * 0.8 });
    const v = { x: dir.x * 0.75 * rod.power, y: dir.y * 0.75 * rod.power + 0.22, z: dir.z * 0.75 * rod.power };
    const proj = bobber.getComponent("minecraft:projectile");
    if (proj) { proj.owner = player; proj.shoot(v); } else bobber.applyImpulse(v);
    if (fx.style) { try { bobber.setProperty(`${NS}:style`, fx.style); } catch {} }
  } catch (err) {
    console.warn(`[Fishing Voyage] Could not cast: ${err}`);
    return;
  }
  sound(dim, "random.bow", player.location, 1.3, 0.5);
  // v1.4: with a lure hook on the rod, an empty bait bag still fishes (the lure never runs out)
  const bait = findBait(player) ?? (fx.lure ? LURE : undefined);
  sessions.set(player.id, { player, bobber, rod, rodId, fx, parts, liquid: liquidOf(rod), phase: "flying", age: 0, bait, castY: player.location.y });
  if (loop === undefined) loop = system.runInterval(tick, TICK);
}

function hookFish(player, s) {
  const dim = s.bobber.dimension;
  // The bait is eaten as the fish takes it; only a bait that is really there counts for the catch.
  if (s.bait && s.bait !== LURE && !consumeOne(player, s.bait)) {
    s.bait = findBait(player);
    if (s.bait && !consumeOne(player, s.bait)) s.bait = undefined;
  }
  const school = !!schoolNear(dim, s.bobber.location, 6);
  const boat = !!boatOf(player);                           // 1.5.0: fishing from a boat
  const depth = (s.ctx?.depth ?? 0) + s.fx.depth + (boat ? BOAT_DEPTH : 0);   // a weighted bobber sinks the bait deeper
  const luck = enchantLevel(heldRod(player), "luck_of_the_sea");       // 1.5.0: the rod's own enchantments count
  s.catchId = rollCatch({ ...s.ctx, depth, slot: timeSlot(), raining: isRaining(dim), bait: s.bait, tier: s.rod.tier, school, rare: s.fx.rare,
    luck: luckFactor(luck),
    moon: moonPhase(), tide: tideState(), shallow: s.fx.shallow, sky: skyAt(!!s.ctx?.cold), boat,
    // v1.4: what a legend asks about: a rod, the weather, the tackle, the dimension, and whether you already have one
    rod: true, thunder: /thunder/i.test(weatherOf(dim)), hook: partAs(s.parts?.hook), line: partAs(s.parts?.line), dim: dim.id,
    caught: new Set(Object.keys(getRecords(player))) });
  // a legend on the line: the bobber turns gold so everyone around can see it
  if (LEGEND_SET.has(s.catchId)) { try { s.bobber.setProperty(`${NS}:style`, LEGEND_STYLE); } catch {} }
  s.size = LEGEND_SET.has(s.catchId) ? rollSize(s.catchId, s.rod.tier + s.fx.size)
    : luckSize(luck, () => rollSize(s.catchId, s.rod.tier + s.fx.size + (boat ? 1 : 0)));
  // v1.5: a fish with a body length plays the minigame (junk, treasure, shrimp and crabs land at once)
  const entry = CATCH_BY_ID[s.catchId];
  if (minigameOn() && entry?.size && s.size !== undefined) {
    s.game = newGame({ id: s.catchId, entry, cls: classOf(s.catchId, s.size), legend: LEGEND_SET.has(s.catchId),
                       tier: s.rod.tier, parts: s.parts ?? {}, coat: gear(player).coat });
    s.phase = "game";
    s.hud = undefined;            // v1.5.8: the last actionbar write (see hudDue)
    sound(dim, "random.splash", s.bobber.location, 0.8, 1.0);
    return;
  }
  s.fightTotal = fightLength(s.catchId, s.size);
  s.fightLeft = s.fightTotal;
  if (!s.fightTotal) return land(player, s);
  // The fight starts with the fish pulling.
  s.phase = "pull";
  s.strain = 0;
  s.idleCycles = 0;
  s.reeledThisRest = false;
  s.phaseEnd = s.age + randInt(16, 34);
  sound(dim, "random.splash", s.bobber.location, 0.8, 1.0);
}

function land(player, s) {
  landCatch(player, s, s.bobber.location);
  damageRod(player, 1 + s.fx.wear);
  sound(player.dimension, "random.bow", player.location, 0.7, 0.35);
  endSession(player.id);
}

function snapLine(player, s) {
  const b = s.bobber;
  sound(b.dimension, "random.break", player.location, 1.4, 0.8);
  particle(b.dimension, SPLASH(s), b.location);
  damageRod(player, 2);
  endSession(player.id);
}

// One use of the rod while a session is active.
function useRod(player, s) {
  const b = s.bobber;
  switch (s.phase) {
    case "game":
      return;
    case "bite":
      return hookFish(player, s);
    case "pull": {
      // Fighting a thrashing fish: the line strains. Too much and it snaps.
      s.strain += 1;
      sound(b.dimension, "kaleidoscope_fishing.strain", player.location, 0.8 + s.strain * 0.08, 0.8);
      if (s.strain > Math.max(1, s.rod.tension + s.fx.strain + (gear(player).coat ? 1 : 0))) snapLine(player, s);
      return;
    }
    case "rest": {
      // Reel in: the bobber (and fish) comes toward the angler.
      s.fightLeft -= s.rod.reel;
      s.reeledThisRest = true;
      sound(b.dimension, "kaleidoscope_fishing.reel", player.location, 0.9 + Math.random() * 0.2, 0.8);
      const pl = player.location, bl = b.location;
      const share = 1 / Math.max(1, Math.ceil(s.fightLeft / s.rod.reel) + 1);
      const nx = bl.x + (pl.x - bl.x) * share, nz = bl.z + (pl.z - bl.z) * share;
      const col = b.dimension.getBlock({ x: Math.floor(nx), y: Math.floor(bl.y - 0.3), z: Math.floor(nz) });
      const open = s.inVoid ? voidBelow(b.dimension, nx, bl.y, nz) : s.liquid(col);
      if (s.fightLeft <= 0 || !open || dist2({ x: nx, y: pl.y, z: nz }, pl) < 4) return land(player, s);
      try { b.teleport({ x: nx, y: bl.y, z: nz }); } catch {}
      particle(b.dimension, SPLASH(s), b.location);
      return;
    }
    default:
      // Reel in an empty line (flying / waiting / ground).
      sound(player.dimension, "random.bow", player.location, 0.7, 0.35);
      return endSession(player.id);
  }
}

// ---------------------------------------------------------------------------
// v1.3: the fishing line (B1 + B3).
// Before, every player saw one line that started at the head plus a fixed offset that also
// followed the head's pitch, and the side offset was subtracted, so the line began on the
// player's LEFT while the rod is held in the right hand. Now each viewer gets their own line
// (Player.spawnParticle): the angler sees it from the first-person rod tip, everyone else from
// the third-person rod tip. Offsets come from the rod model (bamboo_rod.geo.json, locator
// "line_tip" at [-6, 35, -1]; third-person hold rotates the rod 67.2 deg forward around
// [-6, 13, -1], player model scale 0.9375). All four rods share that model.
//   fp: from the eyes, along the view   { fwd, right, up }  (up = camera up)
//   tp: from the feet, along the body   { fwd, right, up }  (no pitch: the arm does not follow it)
const LINE_VIEW = 48;                       // other players farther than this see no line
const tip = { fp: { fwd: 1.0, right: 0.55, up: 0.3 }, tp: { fwd: 1.25, right: 0.35, up: 1.26 } };

function basis(p) {
  const f = p.getViewDirection();
  const h = Math.hypot(f.x, f.z) || 1;
  const fx = f.x / h, fz = f.z / h;          // level forward
  const rx = -fz, rz = fx;                   // level right (Minecraft: +x east, +z south)
  return { f, fx, fz, rx, rz };
}

function tipFirstPerson(p) {
  const eye = p.getHeadLocation(), { f, rx, rz } = basis(p), o = tip.fp;
  const h = Math.hypot(f.x, f.z) || 1;
  // camera up = right x forward
  const ux = -f.y * f.x / h, uy = h, uz = -f.y * f.z / h;
  return { x: eye.x + f.x * o.fwd + rx * o.right + ux * o.up,
           y: eye.y + f.y * o.fwd + uy * o.up,
           z: eye.z + f.z * o.fwd + rz * o.right + uz * o.up };
}

function tipThirdPerson(p) {
  const l = p.location, { fx, fz, rx, rz } = basis(p), o = tip.tp;
  const crouch = p.isSneaking ? -0.3 : 0;
  return { x: l.x + fx * o.fwd + rx * o.right, y: l.y + o.up + crouch, z: l.z + fz * o.fwd + rz * o.right };
}

function lineFor(viewer, a, e, taut, lineId) {
  const to = { x: e.x, y: e.y + 0.3, z: e.z };
  const dx = to.x - a.x, dy = to.y - a.y, dz = to.z - a.z;
  const len = Math.sqrt(dx * dx + dy * dy + dz * dz);
  const n = Math.max(6, Math.min(16, Math.round(len * 1.5)));   // was len * 3, up to 28
  const sag = taut ? 0.02 : Math.min(0.8, len * 0.06);
  for (let i = 1; i < n; i++) {
    const t = i / n;
    try { spawnParticle(viewer, lineId, { x: a.x + dx * t, y: a.y + dy * t - Math.sin(Math.PI * t) * sag, z: a.z + dz * t }); } catch {}
  }
}

function drawLine(p, b, taut, lineId = LINE) {
  const e = b.location;
  lineFor(p, tipFirstPerson(p), e, taut, lineId);
  let others = [];
  try { others = p.dimension.getPlayers({ location: p.location, maxDistance: LINE_VIEW }); } catch {}
  if (others.length < 2) return;
  const a = tipThirdPerson(p);
  for (const o of others) if (o.id !== p.id) lineFor(o, a, e, taut, lineId);
}

// Angler's gear (M4). Bamboo Hat: bites come sooner. Straw Raincoat: steadier stance
// (the line takes one more strain) and, in the rain, bites come sooner still.
function gear(player) {
  const out = { hat: false, coat: false };
  try {
    const eq = player.getComponent("minecraft:equippable");
    try { out.hat = eq.getEquipmentSlot(EquipmentSlot.Head).typeId === `${NS}:bamboo_hat`; } catch {}
    try { out.coat = eq.getEquipmentSlot(EquipmentSlot.Chest).typeId === `${NS}:straw_raincoat`; } catch {}
  } catch {}
  return out;
}

function startWaiting(s) {
  // a legend that got away: the bobber loses its gold for the next ordinary bite
  try { if (s.bobber.getProperty(`${NS}:style`) === LEGEND_STYLE) s.bobber.setProperty(`${NS}:style`, s.fx.style ?? (endPond(s) ? ENDER_STYLE : 0)); } catch {}
  const [lo, hi] = s.rod.bite;
  const rain = isRaining(s.bobber.dimension);
  const g = gear(s.player);
  // Casting into a fish school (splashes, leaping fish, gulls overhead): bites come much sooner.
  const school = !!schoolNear(s.bobber.dimension, s.bobber.location, 6);
  const factor = (s.bait ? BAITS[s.bait]?.biteFactor ?? 1 : 1) * (rain ? 0.8 : 1) *
    (g.hat ? 0.85 : 1) * (g.coat && rain ? 0.8 : 1) * (school ? 0.55 : 1) *
    s.fx.bite * (timeSlot() === "night" ? s.fx.night : 1) *
    (s.ctx?.waters?.has("ice") && skyAt(true) === "aurora" ? AURORA_BITE : 1) *  // 1.5.0: the aurora wakes the ice
    (s.fx.night === 1 && lanternOn(s.player) ? LANTERN_BITE : 1);                  // 1.5.0: the skiff's lantern, not with a Glow Bobber
  s.biteAt = s.age + lureTicks(Math.round(randInt(lo, hi) * factor), enchantLevel(heldRod(s.player), "lure"));   // 1.5.0: Lure
}

// v1.3: End ponds. A missed bite makes the bobber blink 1-3 blocks across the water.
const ENDER_STYLE = 4;
const LEGEND_STYLE = 6;
const endPond = s => !!s.ctx?.waters?.has("end_pond");
function hopBobber(s) {
  const b = s.bobber, dim = b.dimension, bl = b.location;
  for (let i = 0; i < 8; i++) {
    const a = Math.random() * Math.PI * 2, r = 1 + Math.random() * 2;
    const nx = bl.x + Math.cos(a) * r, nz = bl.z + Math.sin(a) * r;
    let ns;
    try { ns = surfaceAt(dim, nx, bl.y, nz, s.liquid); } catch {}
    if (ns === undefined) continue;
    particle(dim, "minecraft:portal_reverse_particle", bl);
    try { b.teleport({ x: nx, y: ns, z: nz }); } catch { return; }
    particle(dim, "minecraft:portal_reverse_particle", { x: nx, y: ns, z: nz });
    sound(dim, "mob.endermen.portal", { x: nx, y: ns, z: nz }, 1.6, 0.5);
    return;
  }
}

function surfaceAt(dim, x, y, z, liquid = isWater) {
  const bx = Math.floor(x), bz = Math.floor(z);
  for (const yy of [Math.floor(y), Math.floor(y - 0.4), Math.floor(y + 0.4)]) {
    const blk = dim.getBlock({ x: bx, y: yy, z: bz });
    // v1.2: a bobber resting on an Ice Hole drops into the water inside it
    if (blk?.typeId === ICE_HOLE && liquid(dim.getBlock({ x: bx, y: yy - 1, z: bz }))) return yy - 0.1;
    if (!liquid(blk)) continue;
    let top = yy;
    for (let i = 0; i < 12 && liquid(dim.getBlock({ x: bx, y: top + 1, z: bz })); i++) top++;
    return top + 0.9;
  }
  return undefined;
}

function tick() {
  for (const [pid, s] of sessions) {
    try {
      const p = s.player, b = s.bobber;
      if (!p?.isValid || !b?.isValid) { endSession(pid); continue; }
      const slot = mainhand(p);
      if (!slot?.hasItem() || slot.typeId !== s.rodId || p.dimension.id !== b.dimension.id) { endSession(pid); continue; }
      const pl = p.location, bl = b.location;
      if (dist2(pl, bl) > MAX_DIST * MAX_DIST) { ["pull", "rest", "game"].includes(s.phase) ? snapLine(p, s) : endSession(pid); continue; }   // a hooked fish snaps the line
      s.age += TICK;
      if (s.age > MAX_AGE && !["pull", "rest", "game"].includes(s.phase)) { endSession(pid); continue; }
      const dim = b.dimension;
      let surface = s.inVoid ? (voidBelow(dim, bl.x, bl.y, bl.z) ? s.voidY : undefined) : surfaceAt(dim, bl.x, bl.y, bl.z, s.liquid);
      if (!s.inVoid && surface === undefined && s.phase === "flying" && s.rod.void && dim.id === "minecraft:the_end"
          && bl.y < s.castY - 3 && voidBelow(dim, bl.x, bl.y, bl.z)) { s.voidY = bl.y; surface = bl.y; s.toVoid = true; }
      drawLine(p, b, s.phase === "bite" || s.phase === "pull" || s.phase === "game", s.fx.line ? `${NS}:${s.fx.line}` : LINE);

      if (s.phase === "flying") {
        if (surface !== undefined) {
          try { b.triggerEvent(`${NS}:float`); b.clearVelocity(); b.teleport({ x: bl.x, y: surface, z: bl.z }); } catch {}
          s.phase = "waiting";
          let here;
          try { here = dim.getBlock({ x: Math.floor(bl.x), y: Math.floor(surface - 0.9), z: Math.floor(bl.z) }); } catch {}
          s.inVoid = !!s.toVoid;
          s.inLava = !s.inVoid && isLava(here);
          s.ctx = s.inVoid ? voidContext(s) : s.inLava ? lavaContext(dim, bl) : analyzeWater(dim, { x: bl.x, y: surface, z: bl.z });
          baitGone(s);
          startWaiting(s);
          // v1.3: in an End pond a plain bobber takes the End look.
          if (endPond(s) && !s.fx.style) { try { b.setProperty(`${NS}:style`, ENDER_STYLE); } catch {} }
          sound(dim, s.inVoid ? "mob.endermen.portal" : "random.splash", bl, 1.4, 0.4);
        } else if (s.age > 40) {
          let v = { x: 0, y: 0, z: 0 };
          try { v = b.getVelocity(); } catch {}
          if (Math.abs(v.x) + Math.abs(v.y) + Math.abs(v.z) < 0.01) s.phase = "ground";
        }
        continue;
      }
      if (s.phase === "ground") continue;

      // Floating phases: keep the bobber on the surface (gentle bob), dip it when pulled.
      if (surface === undefined) { if (s.phase === "waiting") { s.phase = "flying"; } continue; }
      const bob = Math.sin(s.age * 0.15) * 0.03;

      if (s.phase === "waiting") {
        try { b.teleport({ x: bl.x, y: surface + bob, z: bl.z }); } catch {}
        if (s.age % 20 === 0 && baitGone(s)) startWaiting(s);
        if (s.biteAt - s.age < 40 && s.age % 6 === 0) {
          // A fish circles in: wake ripples closing on the bobber.
          const k = Math.max(0.3, (s.biteAt - s.age) / 20);
          const a = s.age * 0.7;
          particle(dim, WAKE(s), { x: bl.x + Math.cos(a) * k, y: surface - 0.05, z: bl.z + Math.sin(a) * k });
        }
        if (s.age >= s.biteAt) {
          s.phase = "bite";
          s.biteEnd = s.age + Math.round((s.rod.window + s.fx.window) * (endPond(s) ? 0.75 : 1));
          sound(dim, "random.splash", bl, 1.0, 0.6);
          sound(dim, "kaleidoscope_fishing.bite", bl, 0.9 + Math.random() * 0.2, 1.0);
          particle(dim, SPLASH(s), bl);
          particle(dim, SPLASH(s), { x: bl.x + 0.2, y: bl.y, z: bl.z - 0.2 });
          if (s.inLava) sound(dim, "liquid.lavapop", bl, 1.0, 0.9);
        }
      } else if (s.phase === "bite") {
        try { b.teleport({ x: bl.x, y: surface - 0.35, z: bl.z }); } catch {}
        if (s.age > s.biteEnd) { if (endPond(s)) hopBobber(s); s.phase = "waiting"; startWaiting(s); }
      } else if (s.phase === "game") {
        // v1.5 minigame: the fish runs along the track while the player holds / releases the use key
        if (!minigameOn()) { s.game = undefined; clearHud(p); land(p, s); continue; }    // switched off mid-fight: it lands
        const g = s.game;
        const state = advance(g, holding.get(pid) === true, TICK);
        // the bobber is dragged under and sideways as the fish runs (left = deep = away from the angler)
        const dx = bl.x - pl.x, dz = bl.z - pl.z, h = Math.hypot(dx, dz) || 1;
        const off = (0.5 - g.fish / MG.TRACK) * 0.08;
        const nx = bl.x + (dx / h) * off, nz = bl.z + (dz / h) * off;
        const ns = s.inVoid ? (voidBelow(dim, nx, bl.y, nz) ? s.voidY : undefined) : surfaceAt(dim, nx, bl.y, nz, s.liquid);
        try { b.teleport({ x: ns !== undefined ? nx : bl.x, y: (ns ?? surface) - 0.4, z: ns !== undefined ? nz : bl.z }); } catch {}
        if (s.age % 6 === 0) particle(dim, SPLASH(s), b.location);
        if (g.inside && s.age % 6 === 0) sound(dim, "kaleidoscope_fishing.reel", p.location, 0.9 + g.progress * 0.4, 0.5);
        if (!g.inside && s.age % 10 === 0) sound(dim, "kaleidoscope_fishing.strain", p.location, 0.9, 0.4);
        if (state === "won") { s.game = undefined; clearHud(p); land(p, s); continue; }
        if (state === "lost") {
          // the fish shakes the hook: the bobber pops up and the wait starts over
          s.game = undefined; clearHud(p);
          sound(dim, "random.splash", bl, 1.3, 0.7);
          particle(dim, SPLASH(s), bl);
          damageRod(p, 1);
          s.phase = "waiting";
          startWaiting(s);
          continue;
        }
        const text = hud(g, charsetFor(p));
        if (hudDue(s.hud, text, s.age, g.inside)) {
          // 1.4.0: each line gets a short label (reel track / catch progress) in the player's language
          const [track, bar] = text.split("\n");
          try {
            p.onScreenDisplay.setActionBar({ rawtext: [
              { text: "§7" }, { translate: "kaleidoscope_fishing.minigame.label_reel" }, { text: " " + track + "\n§7" },
              { translate: "kaleidoscope_fishing.minigame.label_progress" }, { text: " " + bar }] });
          } catch {}
          s.hud = { text, at: s.age, inside: g.inside };
        }
      } else if (s.phase === "pull") {
        // Thrashing: dragged under and away from the angler, heavy splashing.
        const dx = bl.x - pl.x, dz = bl.z - pl.z, h = Math.hypot(dx, dz) || 1;
        const jx = (Math.random() - 0.5) * 0.25, jz = (Math.random() - 0.5) * 0.25;
        const nx = bl.x + (dx / h) * 0.12 + jx, nz = bl.z + (dz / h) * 0.12 + jz;
        const ns = s.inVoid ? (voidBelow(dim, nx, bl.y, nz) ? s.voidY : undefined) : surfaceAt(dim, nx, bl.y, nz, s.liquid);
        try { b.teleport({ x: ns !== undefined ? nx : bl.x, y: (ns ?? surface) - 0.45, z: ns !== undefined ? nz : bl.z }); } catch {}
        if (s.age % 4 === 0) particle(dim, SPLASH(s), bl);
        if (s.age % 8 === 0) sound(dim, "random.splash", bl, 0.9 + Math.random() * 0.3, 0.7);
        if (s.age >= s.phaseEnd) {
          s.phase = "rest";
          s.reeledThisRest = false;
          s.phaseEnd = s.age + randInt(24, 44);
        }
      } else if (s.phase === "rest") {
        try { b.teleport({ x: bl.x, y: surface + bob, z: bl.z }); } catch {}
        if (s.age % 10 === 0) particle(dim, WAKE(s), bl);
        if (s.age >= s.phaseEnd) {
          s.strain = Math.max(0, s.strain - 1);
          s.idleCycles = s.reeledThisRest ? 0 : s.idleCycles + 1;
          if (s.idleCycles >= 4) {
            // Left alone too long: the fish shakes the hook and the bobber pops up.
            sound(dim, "random.splash", bl, 1.3, 0.6);
            s.phase = "waiting";
            startWaiting(s);
            continue;
          }
          s.phase = "pull";
          s.phaseEnd = s.age + randInt(16, 34);
          sound(dim, "random.splash", bl, 0.8, 1.0);
        }
      }
    } catch (err) {
      console.warn(`[Fishing Voyage] fishing tick: ${err}`);
      endSession(pid);
    }
  }
}

world.afterEvents.itemUse.subscribe(ev => useRodItem(ev.source, ev.itemStack));

// v1.5: whether each angler is holding the use key with a rod (the minigame's only input)
const holding = new Map();
export const _holdingForTests = holding;
world.afterEvents.itemStartUse.subscribe(ev => {
  if (!ev.source || !RODS[ev.itemStack?.typeId]) return;
  holding.set(ev.source.id, true);
  useRodItem(ev.source, ev.itemStack);
});
for (const name of ["itemStopUse", "itemReleaseUse", "itemCompleteUse"]) {
  try { world.afterEvents[name].subscribe(ev => { if (ev.source) holding.set(ev.source.id, false); }); } catch {}
}

/** Cast, strike or reel with the rod in hand. Also called when the rod is used on a block that
 *  takes the click itself (an Ice Hole), so fishing through the ice works however the game routes it. */
export function useRodItem(player, stack) {
  if (!player || !stack || !RODS[stack.typeId]) return;
  const now = system.currentTick;
  const s = sessions.get(player.id);
  const cooldown = s && (s.phase === "pull" || s.phase === "rest") ? 3 : 8;
  if (now - (lastUse.get(player.id) ?? -99) < cooldown) return;
  lastUse.set(player.id, now);
  if (s) useRod(player, s);
  else cast(player, stack.typeId);
}

world.afterEvents.playerLeave.subscribe(ev => { endSession(ev.playerId); lastUse.delete(ev.playerId); holding.delete(ev.playerId); });

// Bobbers left from a previous session (world closed mid-cast) are removed once.
system.runTimeout(() => {
  const live = new Set([...sessions.values()].map(s => s.bobber?.id));
  for (const id of ["overworld", "nether", "the_end"]) {
    try { for (const e of world.getDimension(id).getEntities({ type: BOBBER })) if (!live.has(e.id)) e.remove(); } catch {}
  }
}, 40);
