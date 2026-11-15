// ## Cormorant fishing (鸕鶿, v1.1). A tamed cormorant near water dives every 30-45 s and
// comes up with a small fish. Wearing the ring (put on with the Cormorant Ring, taken off with
// shears — both in the entity file) it brings the fish to its owner: into a carried Fish
// Creel, or dropped at the owner's feet. Without the ring it swallows the fish itself.
// Runs only for tamed cormorants within 24 blocks of a player. No text: splash, bubbles,
// the fish in its beak, a croak.
import { ItemStack, system, world } from "@minecraft/server";
import { isWater } from "../fishing/water.js";
import { SMALL, applyClass } from "../fishing/size.js";
import { tryStore } from "../tools/basket.js";
import { spawnParticle } from "../util/particles.js";

const NS = "kaleidoscope_fishing";
const CORM = `${NS}:cormorant`;
const COOLDOWN = [600, 900];
const RIVER = [["sweetfish", 3], ["carp", 2]];
const SEA = [["mackerel", 3], ["yellow_croaker", 3], ["saury", 2], ["minecraft:cod", 1]];

const state = new Map();     // cormorant id -> { next, phase }
const randInt = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
const prop = (e, k) => { try { return e.getProperty(`${NS}:${k}`); } catch { return undefined; } };
const setProp = (e, k, v) => { try { e.setProperty(`${NS}:${k}`, v); } catch {} };
const fx = (dim, id, loc) => { try { spawnParticle(dim, id, loc); } catch {} };
const snd = (dim, id, loc, pitch = 1, volume = 0.8) => { try { dim.playSound(id, loc, { pitch, volume }); } catch {} };

// v1.4.1: the owner. minecraft:tameable sits in the wild group, which the tame event removes, so
// in the real game a tamed cormorant has no tameable component and tamedToPlayerId was never
// readable — no owner, so it never dived. The owner is now written to a dynamic property when the
// tame event fires: the player who just offered it a fish, else the only player within 8 blocks (with
// two or more around, nobody is guessed). Cormorants tamed before this fix have no property: the nearest
// player within 16 blocks claims them once and is saved.
const OWNER = `${NS}:owner`;
const feeder = new Map();    // cormorant id -> { pid, tick } of the last player who used an item on it
const players = () => { try { return world.getAllPlayers(); } catch { return []; } };
const near = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);

function nearestPlayer(c, max) {
  let best, bd = max;
  for (const p of players()) {
    if (!p.isValid || p.dimension.id !== c.dimension.id) continue;
    const d = near(p.location, c.location);
    if (d <= bd) { best = p; bd = d; }
  }
  return best;
}

function ownerOf(c) {
  let pid;
  try { pid = c.getDynamicProperty(OWNER); } catch {}
  if (!pid) { try { pid = c.getComponent("minecraft:tameable")?.tamedToPlayerId; } catch {} }
  if (pid) return players().find(p => p.id === pid);
  // a cormorant tamed before the owner was saved: the nearest player within 16 claims it once, for good,
  // so it does not switch to whoever happens to be closest on a later dive
  const p = nearestPlayer(c, 16);
  if (p) { try { c.setDynamicProperty(OWNER, p.id); } catch {} }
  return p;
}

// only players within `max` blocks; used so a tame without a known feeder is credited only when nobody
// else is close enough to have been the one feeding
function playersNear(c, max) {
  return players().filter(p => p.isValid && p.dimension.id === c.dimension.id && near(p.location, c.location) <= max);
}
const isTameFood = it => { try { return !!it && it.hasTag("minecraft:is_fish"); } catch { return false; } };

try {
  world.beforeEvents.playerInteractWithEntity.subscribe(ev => {
    if (ev.target?.typeId !== CORM || !ev.player || !isTameFood(ev.itemStack)) return;   // only a fish offered
    const prev = feeder.get(ev.target.id);
    if (prev && prev.pid !== ev.player.id && system.currentTick - prev.tick <= 5) return; // first feeder keeps it
    feeder.set(ev.target.id, { pid: ev.player.id, tick: system.currentTick });
  });
} catch {}
try {
  world.afterEvents.dataDrivenEntityTrigger.subscribe(ev => {
    const c = ev.entity;
    if (ev.eventId !== `${NS}:on_tame` || c?.typeId !== CORM) return;
    const f = feeder.get(c.id);
    feeder.delete(c.id);
    let p = f && system.currentTick - f.tick <= 5 && players().find(x => x.id === f.pid);
    if (!p) { const close = playersNear(c, 8); if (close.length === 1) p = close[0]; }   // never guess between players
    if (p) { try { c.setDynamicProperty(OWNER, p.id); } catch {} }
  }, { entityTypes: [CORM], eventTypes: [`${NS}:on_tame`] });
} catch {}

function findWater(c) {
  const dim = c.dimension, b = c.location;
  for (let i = 0; i < 14; i++) {
    const x = Math.floor(b.x) + randInt(-6, 6), z = Math.floor(b.z) + randInt(-6, 6);
    for (let y = Math.floor(b.y) + 1; y >= Math.floor(b.y) - 3; y--) {
      try {
        const w = dim.getBlock({ x, y, z });
        if (!isWater(w)) continue;
        if (dim.getBlock({ x, y: y + 1, z })?.typeId !== "minecraft:air") break;
        if (!isWater(dim.getBlock({ x, y: y - 1, z }))) break;            // at least 2 deep
        return { x: x + 0.5, y, z: z + 0.5 };
      } catch { break; }
    }
  }
  return undefined;
}

function pickFish(dim, at) {
  let biome = "";
  try { biome = String(dim.getBiome?.(at)?.id ?? ""); } catch {}
  const table = /ocean|beach|shore/.test(biome) ? SEA : RIVER;
  let r = Math.random() * table.reduce((a, [, w]) => a + w, 0);
  for (const [id, w] of table) { r -= w; if (r <= 0) return id.includes(":") ? id : `${NS}:${id}`; }
  return `${NS}:${table[0][0]}`;
}

function dive(c, owner, water) {
  const dim = c.dimension;
  const st = state.get(c.id);
  st.phase = "under";
  try { c.triggerEvent(`${NS}:dive`); } catch {}
  setProp(c, "diving", true);
  // A full body under: the water is at least 2 deep, so its feet go into the lower block and its
  // back stays below the surface. Held there every 2 ticks: behavior.float and buoyancy would
  // otherwise pop it straight back up between script updates (v1.4.1: it only ever bobbed).
  const under = { x: water.x, y: water.y - 1, z: water.z };
  try { c.teleport(under); } catch {}
  snd(dim, "random.splash", water, 1.1, 0.6);
  fx(dim, "minecraft:water_splash_particle", { x: water.x, y: water.y + 1, z: water.z });
  let t = 0;
  const h = system.runInterval(() => {
    t += 2;
    if (!c.isValid) { system.clearRun(h); state.delete(c.id); return; }
    if (t < 60) {
      try { c.teleport(under); } catch {}
      if (t % 10 === 0) fx(dim, "minecraft:water_wake_particle", { x: water.x + Math.random() - 0.5, y: water.y + 0.95, z: water.z + Math.random() - 0.5 });
      return;
    }
    system.clearRun(h);
    // up again, a fish in its beak
    const fish = pickFish(dim, water);
    try { c.teleport({ x: water.x, y: water.y + 0.9, z: water.z }); } catch {}
    setProp(c, "diving", false);
    setProp(c, "carrying", true);
    try { c.triggerEvent(`${NS}:surface`); } catch {}
    snd(dim, "random.splash", water, 1.3, 0.5);
    fx(dim, "minecraft:water_splash_particle", { x: water.x, y: water.y + 1, z: water.z });
    snd(dim, `${NS}.cormorant`, water, 1.1, 0.7);
    system.runTimeout(() => deliver(c, owner, fish), 40);
  }, 2);
}

function deliver(c, owner, fish) {
  const st = state.get(c.id);
  if (!c.isValid) { state.delete(c.id); return; }
  setProp(c, "carrying", false);
  if (st) { st.phase = "idle"; st.next = system.currentTick + randInt(...COOLDOWN); }
  const dim = c.dimension;
  if (!prop(c, "ringed")) {
    // no ring: it swallows the fish
    snd(dim, "random.eat", c.location, 0.8, 0.6);
    for (let i = 0; i < 4; i++) fx(dim, "minecraft:villager_happy", { x: c.location.x, y: c.location.y + 1, z: c.location.z });
    return;
  }
  if (owner?.isValid && owner.dimension.id === dim.id) {
    // walk it over: a short hop to the owner's side, then the fish
    const o = owner.location;
    try { c.teleport({ x: o.x + (Math.random() - 0.5) * 1.5, y: o.y, z: o.z + (Math.random() - 0.5) * 1.5 }, { facingLocation: o }); } catch {}
    if (tryStore(owner, fish, 1, SMALL) === 0) { snd(dim, `${NS}.cormorant`, o, 1.3, 0.6); return; }
    try { const it = dim.spawnItem(applyClass(new ItemStack(fish, 1), SMALL), { x: o.x, y: o.y + 0.3, z: o.z }); it.clearVelocity(); } catch {}
    snd(dim, `${NS}.cormorant`, o, 1.3, 0.6);
  }
}

function update() {
  const now = system.currentTick;
  const seen = new Set();
  for (const p of world.getAllPlayers()) {
    let list = [];
    try { list = p.dimension.getEntities({ type: CORM, location: p.location, maxDistance: 24, families: ["kfv_cormorant_tamed"] }); } catch {}
    for (const c of list) {
      if (seen.has(c.id)) continue;
      seen.add(c.id);
      let st = state.get(c.id);
      if (!st) { st = { next: now + randInt(200, 400), phase: "idle" }; state.set(c.id, st); }
      st.seen = now;
      if (st.phase !== "idle" || now < st.next) continue;
      const owner = ownerOf(c);
      if (!owner || owner.dimension.id !== c.dimension.id) continue;
      const d = Math.hypot(owner.location.x - c.location.x, owner.location.z - c.location.z);
      if (d > 16) continue;
      const water = findWater(c);
      if (!water) { st.next = now + 100; continue; }
      dive(c, owner, water);
    }
  }
  // Forget cormorants that died, unloaded or wandered off (v1.2: the list no longer only grows).
  for (const [id, st] of state) if (st.phase === "idle" && now - (st.seen ?? now) > 1200) state.delete(id);
}

system.runInterval(() => { try { update(); } catch (err) { console.warn(`[Fishing Voyage] cormorants: ${err}`); } }, 40);

// A cormorant left mid-dive when the world closed comes back up.
system.runTimeout(() => {
  for (const id of ["overworld", "nether", "the_end"]) {
    try {
      for (const c of world.getDimension(id).getEntities({ type: CORM })) {
        if (prop(c, "diving") || prop(c, "carrying")) {
          setProp(c, "diving", false); setProp(c, "carrying", false);
          try { c.triggerEvent(`${NS}:surface`); } catch {}
        }
      }
    } catch {}
  }
}, 40);
export const _stateForTests = state;
