// ## Fish schools (魚群, v1.1). Patches of open water where fish gather and slowly drift.
// Nothing is written on screen: a school shows as fine splashes, fish leaping out of the
// water and seagulls wheeling overhead. Casting into one brings bites sooner and rarer fish.
// Schools live only in memory near players (no world scan, no saved state); a few at most.
import { system, world } from "@minecraft/server";
import { analyzeWater, isWater, weatherOf } from "../fishing/water.js";
import { spawnParticle } from "../util/particles.js";

const NS = "kaleidoscope_fishing";
const GULL = `${NS}:seagull`;
// v1.4: a school in a river shows a heron on the bank instead of gulls overhead (lakes have no schools).
const HERON = `${NS}:heron`;
const MAX_HERONS = 6;
const herons = new Map();           // entity id -> { s, pecks }
const OPEN_WATER = ["ocean", "deep_ocean", "warm_ocean", "cold_ocean", "beach", "river"];
const PER_PLAYER = 2, MAX_SCHOOLS = 10;
// v1.4 fish runs (魚汛): in a thunderstorm each player may have one more school, and they last half again as long.
const STORM_PER_PLAYER = 3, STORM_LIFE = 1.5;
const thunder = dim => { try { return /thunder/i.test(weatherOf(dim)); } catch { return false; } };
const LIFE = [3600, 7200];          // ticks a school lasts (3-6 minutes)
const SPEED = 0.03;                 // blocks per tick
// v1.3: gulls are only kept while their chunk is surely loaded (default simulation distance is
// 4 chunks = 64 blocks). Past that the script loses them and they used to stay frozen in mid-air.
const SEEN = 48, KEEP_GULLS = 56;
const MAX_GULLS = 12;              // all school gulls in the world (was up to 10 schools x 3)
const CLIMB = 4;                   // a gull flying off rises at most this many blocks
const GULL_RETRY = 200;
// v1.5.3 (luosen profile): player positions are read once per POLL ticks into `seen` instead of once
// per school per update; a heron that found no bank waits HERON_RETRY ticks before looking again.
const POLL = 10, HERON_RETRY = 600;
// Open-water checks of a column are kept COLUMN_TTL ticks (a school drifts back and forth over the same water).
const COLUMN_TTL = 600, COLUMN_MAX = 512;

const schools = [];
export const schoolGullIds = new Set();
let nextId = 1;

const rand = (a, b) => a + Math.random() * (b - a);
const d2 = (a, b) => (a.x - b.x) ** 2 + (a.z - b.z) ** 2;
const air = b => !b || b.typeId === "minecraft:air";

/** The school whose water covers loc (within r blocks), if any. */
export function schoolNear(dim, loc, r = 6) {
  return schools.find(s => s.dimId === dim.id && d2(s, loc) <= r * r);
}

// --------------------------------------------------------------------------- finding water
function surfaceAt(dim, x, z, fromY) {
  for (let y = fromY + 12; y > fromY - 28; y--) {
    let b;
    try { b = dim.getBlock({ x, y, z }); } catch { return undefined; }
    if (!b) return undefined;
    if (isWater(b)) {
      try { return air(dim.getBlock({ x, y: y + 1, z })) ? y : undefined; } catch { return undefined; }
    }
    if (!air(b)) return undefined;   // solid before any water: not open water here
  }
  return undefined;
}

function openWater(dim, x, y, z) {
  for (const [dx, dz] of [[2, 0], [-2, 0], [0, 2], [0, -2]]) {
    try { if (!isWater(dim.getBlock({ x: x + dx, y, z: z + dz })) || !air(dim.getBlock({ x: x + dx, y: y + 1, z: z + dz }))) return false; }
    catch { return false; }
  }
  try { return isWater(dim.getBlock({ x, y: y - 2, z })); } catch { return false; }
}

function trySpawn(player) {
  const dim = player.dimension;
  if (dim.id !== "minecraft:overworld") return;
  const p = player.location;
  for (let i = 0; i < 6; i++) {
    const a = Math.random() * Math.PI * 2, r = rand(20, 56);
    const x = Math.floor(p.x + Math.cos(a) * r), z = Math.floor(p.z + Math.sin(a) * r);
    const y = surfaceAt(dim, x, z, Math.floor(p.y));
    if (y === undefined || !openWater(dim, x, y, z)) continue;
    let w;
    try { w = analyzeWater(dim, { x, y, z }); } catch { continue; }
    if (!OPEN_WATER.some(k => w.waters.has(k))) continue;
    const life = rand(...LIFE) * (thunder(dim) ? STORM_LIFE : 1);     // v1.4: storm schools last longer
    schools.push({ id: nextId++, dimId: dim.id, dim, x: x + 0.5, y: y + 0.9, z: z + 0.5, wy: y, river: w.waters.has("river"),
                   heading: Math.random() * Math.PI * 2, ends: system.currentTick + Math.round(life), gulls: [], heron: undefined });
    return;
  }
}

// --------------------------------------------------------------------------- gulls overhead
function liveGullCount() {
  let n = leaving.length;
  for (const s of schools) n += s.gulls.length;
  return n;
}

/** Ids of gulls the school script still steers (circling or flying off). */
export function schoolTracks(id) {
  return schoolGullIds.has(id) || leaving.some(l => l.e?.id === id);
}

/** A bank within 7 blocks of the school: solid ground beside water, air above it. */
function bankNear(s) {
  for (let i = 0; i < 16; i++) {
    const a = Math.random() * Math.PI * 2, r = rand(3, 7);
    const x = Math.floor(s.x + Math.cos(a) * r), z = Math.floor(s.z + Math.sin(a) * r);
    for (const y of [s.wy, s.wy + 1]) {
      try {
        const g = s.dim.getBlock({ x, y, z }), up = s.dim.getBlock({ x, y: y + 1, z });
        if (!g || isWater(g) || air(g) || !air(up)) continue;
        if ([[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dz]) => isWater(s.dim.getBlock({ x: x + dx, y, z: z + dz })))) return { x: x + 0.5, y: y + 1, z: z + 0.5 };
      } catch {}
    }
  }
  return undefined;
}
function spawnHeron(s) {
  if (herons.size >= MAX_HERONS) return false;
  const at = bankNear(s);
  if (!at) return false;
  try {
    const e = s.dim.spawnEntity(HERON, at, { spawnEvent: `${NS}:as_school` });
    try { e.teleport(at, { facingLocation: { x: s.x, y: at.y, z: s.z } }); } catch {}
    s.heron = e; herons.set(e.id, { s, pecks: 0 });
    return true;
  } catch { return false; }
}
function steerHerons() {
  for (const [id, h] of herons) {
    const e = h.s.heron;
    if (!e?.isValid) { herons.delete(id); h.s.heron = undefined; continue; }
    // every few seconds it dips for a fish; the head comes back up a moment later
    if (t % 100 === 0 && Math.random() < 0.5) { try { e.setProperty(`${NS}:pecking`, true); } catch {} h.pecks = t; }
    else if (h.pecks && t - h.pecks >= 24) { try { e.setProperty(`${NS}:pecking`, false); } catch {} h.pecks = 0; }
  }
}
function releaseHeron(s) {
  if (!s.heron) return;
  herons.delete(s.heron.id);
  try { s.heron.remove(); } catch {}
  s.heron = undefined;
}

function spawnGulls(s) {
  const n = Math.min(2 + (Math.random() < 0.5 ? 1 : 0), MAX_GULLS - liveGullCount());
  for (let i = 0; i < n; i++) {
    const g = { phase: Math.random() * Math.PI * 2, r: rand(3.5, 6), h: rand(7, 10), w: rand(0.035, 0.055) * (Math.random() < 0.5 ? -1 : 1) };
    try {
      g.e = s.dim.spawnEntity(GULL,
        { x: s.x + Math.cos(g.phase) * g.r, y: s.y + g.h, z: s.z + Math.sin(g.phase) * g.r },
        { spawnEvent: `${NS}:as_school` });
      schoolGullIds.add(g.e.id);
      s.gulls.push(g);
    } catch {}
  }
}

function releaseGulls(s, remove) {
  for (const g of s.gulls) {
    schoolGullIds.delete(g.e?.id);
    if (remove) { try { g.e?.remove(); } catch {} continue; }
    leaving.push({ e: g.e, dx: Math.cos(g.phase), dz: Math.sin(g.phase), t: 0, rose: 0 });
  }
  s.gulls = [];
}

const leaving = [];
function steerGulls(s) {
  // A gull whose chunk unloaded is no longer ours: forget it, so the load-time cleanup in
  // creatures/seagull.js removes it instead of leaving a frozen gull in the sky.
  s.gulls = s.gulls.filter(g => {
    if (g.e?.isValid && schoolGullIds.has(g.e.id)) return true;
    schoolGullIds.delete(g.e?.id);
    return false;
  });
  for (const g of s.gulls) {
    g.phase += g.w * 2;
    const at = a => ({ x: s.x + Math.cos(a) * g.r, y: s.y + g.h + Math.sin(a * 0.5) * 0.6, z: s.z + Math.sin(a) * g.r });
    try { g.e.teleport(at(g.phase), { facingLocation: at(g.phase + Math.sign(g.w) * 0.4) }); } catch {}
  }
}

function flyAway() {
  for (let i = leaving.length - 1; i >= 0; i--) {
    const l = leaving[i];
    l.t += 2;
    if (!l.e?.isValid || l.t > 100) { try { l.e?.remove(); } catch {} leaving.splice(i, 1); continue; }
    const p = l.e.location;
    const up = l.rose < CLIMB ? 0.15 : 0;
    l.rose += up;
    const n = { x: p.x + l.dx * 0.6, y: p.y + up, z: p.z + l.dz * 0.6 };
    try { l.e.teleport(n, { facingLocation: { x: n.x + l.dx, y: n.y, z: n.z + l.dz } }); } catch {}
  }
}

// --------------------------------------------------------------------------- the school itself
const columns = new Map();          // "dim|x|y|z" -> { ok, at }
function columnOpen(dim, x, y, z) {
  const key = `${dim.id}|${x}|${y}|${z}`, now = system.currentTick;
  const hit = columns.get(key);
  if (hit && now - hit.at < COLUMN_TTL) return hit.ok;
  let ok = false;
  try { ok = isWater(dim.getBlock({ x, y, z })) && air(dim.getBlock({ x, y: y + 1, z })) && openWater(dim, x, y, z); } catch {}
  if (columns.size >= COLUMN_MAX) columns.clear();
  columns.set(key, { ok, at: now });
  return ok;
}

function drift(s) {
  const nx = s.x + Math.cos(s.heading) * SPEED * 20, nz = s.z + Math.sin(s.heading) * SPEED * 20;
  const ok = columnOpen(s.dim, Math.floor(nx), s.wy, Math.floor(nz));
  if (ok) s.heading += rand(-0.25, 0.25);
  else s.heading += Math.PI + rand(-0.6, 0.6);
}

function show(s) {
  const fx = (id, x, z, dy = 0.05) => { try { spawnParticle(s.dim, id, { x, y: s.y + dy, z }); } catch {} };
  for (let i = 0; i < 2; i++) {
    const a = Math.random() * Math.PI * 2, r = Math.random() * 2.6;
    fx("minecraft:water_splash_particle", s.x + Math.cos(a) * r, s.z + Math.sin(a) * r);
  }
  if (Math.random() < 0.4) fx("minecraft:water_wake_particle", s.x + rand(-2, 2), s.z + rand(-2, 2));
  if (Math.random() < 0.22) {
    const x = s.x + rand(-2.2, 2.2), z = s.z + rand(-2.2, 2.2);
    fx(`${NS}:fish_jump`, x, z, -0.1);
    fx("minecraft:water_splash_particle", x, z);
    try { s.dim.playSound("random.splash", { x, y: s.y, z }, { pitch: rand(1.4, 1.8), volume: 0.25 }); } catch {}
  }
}

let t = 0;
let seen = [], polledAt = -Infinity; // [{ dimId, x, z, p }] of every player, refreshed every POLL ticks
system.runInterval(() => { try { update(); } catch (err) { console.warn(`[Fishing Voyage] fish schools: ${err}`); } }, 2);
function update() {
  t += 2;
  const spawnCheck = t % 200 === 0;
  if (!spawnCheck && !schools.length && !leaving.length && !herons.size) return;   // nothing to steer
  if (spawnCheck || system.currentTick - polledAt >= POLL) {
    const players = world.getAllPlayers();
    polledAt = system.currentTick;
    seen = [];
    for (const p of players) {
      try { const l = p.location; seen.push({ dimId: p.dimension.id, x: l.x, z: l.z, p }); } catch {}
    }
    if (spawnCheck) {
      for (const q of seen) {
        try {
          const near = schools.filter(s => s.dimId === q.dimId && d2(s, q) < 96 * 96).length;
          if (near < (thunder(q.p.dimension) ? STORM_PER_PLAYER : PER_PLAYER) && schools.length < MAX_SCHOOLS) trySpawn(q.p);
        } catch {}
      }
    }
  }
  const now = system.currentTick;
  for (let i = schools.length - 1; i >= 0; i--) {
    const s = schools[i];
    let nearest = Infinity;
    for (const q of seen) if (q.dimId === s.dimId) nearest = Math.min(nearest, d2(s, q));
    if (now > s.ends || nearest > 160 * 160) { releaseGulls(s, nearest > KEEP_GULLS * KEEP_GULLS); releaseHeron(s); schools.splice(i, 1); continue; }
    s.x += Math.cos(s.heading) * SPEED * 2; s.z += Math.sin(s.heading) * SPEED * 2;
    if (t % 20 === 0) drift(s);
    if (nearest < SEEN * SEEN) {
      if (s.river && !s.heron && !s.heronTried && now >= (s.heronRetryAt ?? 0)) { s.heronTried = spawnHeron(s); if (!s.heronTried) s.heronRetryAt = now + HERON_RETRY; }
      if (!s.river && !s.gulls.length && !s.gullsSpawned && now >= (s.gullsRetryAt ?? 0) && liveGullCount() < MAX_GULLS) {
        spawnGulls(s);
        s.gullsSpawned = s.gulls.length > 0;
        // A temporarily unloaded spawn position must not lock out the school forever
        // or retry on every update while it remains unavailable.
        s.gullsRetryAt = s.gullsSpawned ? 0 : now + GULL_RETRY;
      }
      if (t % 6 === 0) show(s);
    } else if (nearest > KEEP_GULLS * KEEP_GULLS && (s.gulls.length || s.heron)) {
      releaseGulls(s, true); s.gullsSpawned = false;
      releaseHeron(s); s.heronTried = false;
    }
    steerGulls(s);
  }
  steerHerons();
  flyAway();
}

// School gulls left over from a previous session are removed once.
system.runTimeout(() => {
  for (const id of ["overworld", "nether", "the_end"]) {
    try {
      for (const e of world.getDimension(id).getEntities({ type: GULL, families: ["kfv_scripted_gull"] })) {
        if (!schoolGullIds.has(e.id)) e.remove();
      }
      for (const e of world.getDimension(id).getEntities({ type: HERON, families: ["kfv_scripted_heron"] })) {
        if (!herons.has(e.id)) e.remove();
      }
    } catch {}
  }
}, 40);
