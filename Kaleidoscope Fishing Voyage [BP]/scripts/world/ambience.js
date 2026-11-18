// ## Harbour sounds (漁港的聲音, 1.6.0, docs/PLAN_1.6.0.md section 13). Quiet sounds that tell where you are,
// heard only by the player they are for (player.playSound, never the whole world), each player on their own timers:
//
//   pier      planks creak, a rope rubs, a wave slaps the piles   standing on or within 8 blocks of a pier, every 10-30 s
//   gulls     far-off gulls (our gull call, quiet)                a beach biome by day, no seagull within 32 blocks
//   skiff     the hull creaks; now and then a fish slaps the hold  riding the Fishing Skiff; the slap only with fish aboard
//   lantern   a very faint hum                                    at night, within 4 blocks of a Fishing Lantern (or the
//                                                                 skiff's own lantern)
//   trawl     the net dragging through the water                  the skiff's trawl is out
//
// Vanilla sounds and the pack's own only (section 22.2 item 7: new recordings only if these do not sound right).
// Cheap: one look every CHECK ticks; the pier and lantern searches are cached per player for a few seconds.
// Piers: the generated pier (structures/kaleidoscope_fishing/fishing_pier) is spruce planks on spruce posts and carries
// no tag or marker a script could ask for, so a "pier" here is planks with water right under them (one or two
// blocks down): the generated pier, and any wooden jetty a player builds over water.
import * as mc from "@minecraft/server";
import { system, world } from "@minecraft/server";
import { isWater, timeSlot } from "../fishing/water.js";
import { boatOf, SKIFF } from "./boat.js";
import { CATCHES, FISH_ALIAS } from "../data/generated.js";

const NS = "kaleidoscope_fishing";
export const CHECK = 30;                             // ticks between looks
const PIER_R = 8, LANTERN_R = 4;
const PIER_CACHE = 200, LANTERN_CACHE = 100;         // ticks a search result is kept
const GULL = `${NS}:seagull`, LANTERN = `${NS}:fishing_lantern`, TRAWL = `${NS}:trawl`;
const CATCH_IDS = new Set(CATCHES.map(c => c.id));
const PLANK = /(_planks|_slab)$/;

/** Each scene: its sounds (one is picked) and the gap until it may play again, in ticks [min, max]. */
export const SCENES = {
  pier: { gap: [200, 600], sounds: [
    { id: "random.wood_click", pitch: [0.45, 0.6], volume: 0.35 },       // a plank creaks
    { id: "dig.cloth", pitch: [0.55, 0.7], volume: 0.25 },               // a rope rubs on a post
    { id: "random.splash", pitch: [0.5, 0.6], volume: 0.15 },            // a wave slaps the piles
  ] },
  gulls: { gap: [300, 800], sounds: [{ id: `${NS}.gull`, pitch: [0.85, 1.1], volume: 0.2 }] },
  skiff: { gap: [120, 280], sounds: [
    { id: "random.wood_click", pitch: [0.5, 0.65], volume: 0.3 },
    { id: "step.wood", pitch: [0.5, 0.6], volume: 0.2 },
  ] },
  slap: { gap: [400, 1000], sounds: [{ id: "mob.fish.flop", pitch: [0.9, 1.2], volume: 0.35 }] },
  lantern: { gap: [80, 160], sounds: [{ id: "beacon.ambient", pitch: [1.7, 1.9], volume: 0.08 }] },
  trawl: { gap: [60, 100], sounds: [
    { id: "random.swim", pitch: [0.5, 0.6], volume: 0.25 },
    { id: "liquid.water", pitch: [0.8, 0.9], volume: 0.2 },
  ] },
};

/** Which scenes apply to what a player has around them right now. Exported for tests. */
export function scenesFor(ctx) {
  const out = [];
  if (ctx.pier) out.push("pier");
  if (ctx.beach && ctx.day && !ctx.gullNear) out.push("gulls");
  if (ctx.skiff) { out.push("skiff"); if (ctx.holdFish) out.push("slap"); }
  if (ctx.night && ctx.lantern) out.push("lantern");
  if (ctx.trawl) out.push("trawl");
  return out;
}

const lerp = (r, t) => r[0] + (r[1] - r[0]) * t;
/**
 * The sounds due now for one player, given their timers (scene -> the tick it may next play; changed in place).
 * A scene seen for the first time waits a random part of its gap first, so they never all start at once.
 * Exported for tests.
 */
export function due(ctx, timers, now, rand = Math.random) {
  const play = [];
  const active = new Set(scenesFor(ctx));
  for (const name of Object.keys(timers)) if (!active.has(name)) delete timers[name];      // left the scene: start over next time
  for (const name of active) {
    const sc = SCENES[name];
    if (timers[name] === undefined) { timers[name] = now + Math.round(lerp(sc.gap, rand()) * rand()); continue; }
    if (now < timers[name]) continue;
    const s = sc.sounds[Math.min(sc.sounds.length - 1, Math.floor(rand() * sc.sounds.length))];
    play.push({ scene: name, id: s.id, pitch: Math.round(lerp(s.pitch, rand()) * 100) / 100, volume: s.volume });
    timers[name] = now + Math.round(lerp(sc.gap, rand()));
  }
  return play;
}

// ------------------------------------------------------------------------------------------------ what is around
/** Planks or a wooden slab with water one or two blocks under them. */
export function isPierBlock(b) {
  try {
    if (!b || !PLANK.test(b.typeId) || !/wood|oak|spruce|birch|jungle|acacia|dark_oak|mangrove|cherry|bamboo|crimson|warped|planks/.test(b.typeId)) return false;
    return isWater(b.below?.(1)) || isWater(b.below?.(2));
  } catch { return false; }
}
/** Standing on or within PIER_R blocks of a pier: the block underfoot, then a coarse ring of samples. */
export function nearPier(dim, loc) {
  const x0 = Math.floor(loc.x), y0 = Math.floor(loc.y), z0 = Math.floor(loc.z);
  try { if (isPierBlock(dim.getBlock({ x: x0, y: y0 - 1, z: z0 }))) return true; } catch {}
  for (let dx = -PIER_R; dx <= PIER_R; dx += 2) {
    for (let dz = -PIER_R; dz <= PIER_R; dz += 2) {
      if (dx * dx + dz * dz > PIER_R * PIER_R) continue;
      for (const dy of [-1, -2, 0]) {
        try { if (isPierBlock(dim.getBlock({ x: x0 + dx, y: y0 + dy, z: z0 + dz }))) return true; } catch {}
      }
    }
  }
  return false;
}
/** A Fishing Lantern within LANTERN_R blocks: the engine's block search when it has one, else a scan. */
export function nearLantern(dim, loc) {
  const x0 = Math.floor(loc.x), y0 = Math.floor(loc.y), z0 = Math.floor(loc.z);
  const from = { x: x0 - LANTERN_R, y: y0 - 1, z: z0 - LANTERN_R }, to = { x: x0 + LANTERN_R, y: y0 + 3, z: z0 + LANTERN_R };
  try {
    if (typeof dim.getBlocks === "function" && typeof mc.BlockVolume === "function") {
      const list = dim.getBlocks(new mc.BlockVolume(from, to), { includeTypes: [LANTERN] }, false);
      for (const _ of list.getBlockLocationIterator()) return true;     // eslint-disable-line no-unused-vars
      return false;
    }
  } catch {}
  for (let x = from.x; x <= to.x; x++) {
    for (let z = from.z; z <= to.z; z++) {
      for (let y = from.y; y <= to.y; y++) {
        try { if (dim.getBlock({ x, y, z })?.typeId === LANTERN) return true; } catch {}
      }
    }
  }
  return false;
}
function biomeOf(dim, loc) {
  try { return String(dim.getBiome?.(loc)?.id ?? ""); } catch { return ""; }
}
function holdHasFish(boat) {
  try {
    const c = boat.getComponent("minecraft:inventory")?.container;
    if (!c) return false;
    for (let i = 0; i < c.size; i++) {
      const it = c.getItem(i);
      if (it && CATCH_IDS.has(FISH_ALIAS[it.typeId] ?? it.typeId)) return true;
    }
  } catch {}
  return false;
}

const state = new Map();            // player id -> { timers, pier: {t, v}, lantern: {t, v} }
const cached = (slot, now, every, look) => {
  if (slot.t === undefined || now - slot.t >= every) { slot.t = now; slot.v = look(); }
  return slot.v;
};

/** What is around one player now. Exported for tests. */
export function contextOf(player, now, st) {
  const dim = player.dimension, loc = player.location;
  const slot = timeSlot();
  const day = slot === "day", night = slot === "night";
  const boat = boatOf(player);
  const skiff = boat?.typeId === SKIFF;
  let trawl = false;
  if (skiff) { try { trawl = !!boat.getProperty(TRAWL); } catch {} }
  const beach = day && /beach/.test(biomeOf(dim, loc));
  let gullNear = false;
  if (beach) { try { gullNear = dim.getEntities({ type: GULL, location: loc, maxDistance: 32 }).length > 0; } catch {} }
  return {
    pier: !skiff && cached(st.pier, now, PIER_CACHE, () => nearPier(dim, loc)),
    beach, day, gullNear, night, skiff, trawl,
    holdFish: skiff && holdHasFish(boat),
    lantern: night && (skiff || cached(st.lantern, now, LANTERN_CACHE, () => nearLantern(dim, loc))),
  };
}

/** One look for every player in the overworld. Exported for tests. */
export function tick(now = system.currentTick, rand = Math.random) {
  for (const p of world.getAllPlayers()) {
    try {
      if (p.dimension.id !== "minecraft:overworld") { state.delete(p.id); continue; }
      let st = state.get(p.id);
      if (!st) state.set(p.id, (st = { timers: {}, pier: {}, lantern: {} }));
      for (const s of due(contextOf(p, now, st), st.timers, now, rand)) {
        try { p.playSound(s.id, { pitch: s.pitch, volume: s.volume }); } catch {}
      }
    } catch {}
  }
}
/** Tests only. */
export function _reset() { state.clear(); }

system.runInterval(() => { try { tick(); } catch {} }, CHECK);
world.afterEvents.playerLeave?.subscribe(ev => state.delete(ev.playerId));
