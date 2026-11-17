// ## Workstation effects (1.5.0, immersive pass). Blocks cannot play skeletal animations, so the stations show what
// they are doing with particles and sound: scales flicking off the board, clams breathing in the brine, heat over
// the salt pan, a jar that bubbles while it ferments and puffs when the lid comes off, drips under the drying rack.
// No text. Purely cosmetic: nothing here reads or changes what a station holds or how long it takes.
// Particles: Kaleidoscope Fishing Voyage [RP]/particles/kfv_station_*.json (kaleidoscope_fishing:station_*).
// Cost: one-shot bursts only on a player's own use; the idle effects are emitters that run for a whole block tick
// (5 s, the rack 10 s) from one spawn, sent only with a player within NEAR blocks and at most once per `gap` ticks
// per block and kind.
import { system } from "@minecraft/server";
import { spawnParticle } from "../util/particles.js";

const NS = "kaleidoscope_fishing";
export const NEAR = 24;
/** The particle id of a station effect. */
export const fxId = name => `${NS}:station_${name}`;

/** A point on a block: its corner plus an offset (default: the middle of its top face, y given). */
export const on = (block, dx = 0.5, dy = 0.5, dz = 0.5) => ({ x: block.x + dx, y: block.y + dy, z: block.z + dz });

/** Is a player close enough to see it? */
export function playerNear(dim, at, r = NEAR) {
  try { return dim.getPlayers({ location: at, maxDistance: r }).length > 0; } catch { return false; }
}

const last = new Map();
/** Throttle: true at most once per `gap` ticks for this block and kind. Exported for tests. */
export function due(block, kind, gap) {
  const k = `${block.dimension?.id}:${block.x}:${block.y}:${block.z}:${kind}`;
  let t = 0;
  try { t = system.currentTick; } catch {}
  const l = last.get(k);
  if (l !== undefined && t >= l && t - l < gap) return false;
  if (last.size > 2048) last.clear();                   // stale blocks: start over rather than grow
  last.set(k, t);
  return true;
}

/** Spawn station effects (names, or [name, at] pairs) at `at`. */
export function burst(dim, at, ...names) {
  for (const n of names) {
    if (Array.isArray(n)) spawnParticle(dim, fxId(n[0]), n[1]);
    else if (n) spawnParticle(dim, n.includes(":") ? n : fxId(n), at);
  }
}
/** A sound, never throwing. */
export function sound(dim, id, at, pitch = 1, volume = 0.7) {
  try { dim.playSound(id, at, { pitch, volume }); } catch {}
}
/** An idle effect for a block's tick: runs `fn` only with a player near and not more often than `gap` ticks. */
export function ambient(block, kind, gap, at, fn) {
  if (!due(block, kind, gap)) return false;
  if (!playerNear(block.dimension, at)) return false;
  try { fn(); } catch {}
  return true;
}

// ------------------------------------------------------------------ the pond feeder
/** Feed thrown in: pellets fly off the feeder and patter onto the nearest stretch of water (r.spots). */
export function feedFx(dim, block, spots) {
  const at = on(block, 0.5, 0.8, 0.5);
  burst(dim, at, "pellets");
  let near = [];
  if (Array.isArray(spots)) {
    near = spots.filter(s => Array.isArray(s) && s.length === 3)
      .map(s => [Math.hypot(s[0] - block.x, s[2] - block.z), s]).sort((a, b) => a[0] - b[0]).slice(0, 2).map(x => x[1]);
  }
  for (const [x, y, z] of near) {
    const w = { x: x + 0.5, y: y + 0.95, z: z + 0.5 };
    burst(dim, w, "pellet_drop", "minecraft:water_splash_particle");
  }
  if (near.length) sound(dim, "random.splash", at, 1.9, 0.15);
}
