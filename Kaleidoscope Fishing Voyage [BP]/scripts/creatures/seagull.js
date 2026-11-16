// ## Seagull thieves (v1.1). Raw fish left lying on the ground for a while tempts a nearby
// gull: it swoops down, takes one fish and flies off with it in its beak. Gulls are shy, so
// they only try when nobody stands right next to the fish. No text: you see and hear it.
import { ItemStack, system, world } from "@minecraft/server";
import { BASKET_ITEMS } from "../data/generated.js";
import { schoolGullIds, schoolTracks } from "../world/schools.js";
import { knownRacks, stealFromRack } from "../blocks/drying.js";

const NS = "kaleidoscope_fishing";
const GULL = `${NS}:seagull`;
const FISH = new Set(BASKET_ITEMS.map(b => b.id));
const WAIT = 100;            // ticks a fish must lie there before a gull goes for it
const SHY = 4;               // a player this close keeps gulls away
const CHANCE = 0.5;          // per check, per tempting fish
const RACK_CHANCE = 0.004;   // per check, per unattended Drying Rack with a gull in reach (v1.2)
const CLIMB = 4;             // v1.3: a gull flying off rises at most this many blocks
const SCRIPTED = "kfv_scripted_gull";

const firstSeen = new Map(); // item entity id -> tick first seen
const targeted = new Set();  // item entity ids a gull is already after
const busy = new Map();      // gull id -> flight
const fleeing = [];          // v1.3: scripted gulls that were hit, flying off level
const lerp = (a, b, k) => a + (b - a) * k;

function sound(dim, loc, pitch = 1) { try { dim.playSound(`${NS}.gull`, loc, { pitch, volume: 0.9 }); } catch {} }

function takeOne(item) {
  let stack;
  try { stack = item.getComponent("minecraft:item")?.itemStack; } catch {}
  if (!stack) return false;
  const loc = item.location, dim = item.dimension;
  try { item.remove(); } catch { return false; }
  if (stack.amount > 1) {
    const rest = stack.clone ? stack.clone() : new ItemStack(stack.typeId, stack.amount);
    rest.amount = stack.amount - 1;
    try { if (!stack.clone) rest.setLore(stack.getLore()); } catch {}
    try { const e = dim.spawnItem(rest, loc); e.clearVelocity(); } catch {}
  }
  return true;
}

function startTheft(gull, item, now, rack) {
  schoolGullIds.delete(gull.id);                   // a school gull breaks off its circle
  try { gull.triggerEvent(`${NS}:carry`); } catch {}
  const itemId = item ? item.id : `rack:${rack.x}:${rack.y}:${rack.z}`;
  targeted.add(itemId);
  busy.set(gull.id, { gull, item, rack, itemId, from: { ...gull.location }, t: 0, dur: 30, phase: "swoop" });
  sound(gull.dimension, gull.location, 1.1);
}

function nearestPlayer(dim, loc) {
  let best;
  for (const p of world.getAllPlayers()) {
    if (p.dimension.id !== dim.id) continue;
    const d = (p.location.x - loc.x) ** 2 + (p.location.z - loc.z) ** 2;
    if (!best || d < best.d) best = { p, d };
  }
  return best;
}

function fly() {
  for (const [id, f] of busy) {
    const g = f.gull;
    if (!g?.isValid) { busy.delete(id); targeted.delete(f.itemId); continue; }
    f.t += 2;
    if (f.phase === "swoop") {
      const target = f.rack ? { x: f.rack.x + 0.5, y: f.rack.y + 0.6, z: f.rack.z + 0.5 }
        : f.item?.isValid ? f.item.location : f.last ?? g.location;
      f.last = target;
      const k = Math.min(1, f.t / f.dur);
      const pos = { x: lerp(f.from.x, target.x, k), y: lerp(f.from.y, target.y + 0.3, k) + Math.sin(Math.PI * k) * 0.8, z: lerp(f.from.z, target.z, k) };
      try { g.teleport(pos, { facingLocation: { x: target.x, y: target.y + 0.3, z: target.z } }); } catch {}
      if (k >= 1) {
        let got = false;
        if (f.rack) { try { got = stealFromRack(g.dimension.getBlock(f.rack)); } catch {} }
        else got = f.item?.isValid && takeOne(f.item);
        targeted.delete(f.itemId);
        if (got) { try { g.setProperty(`${NS}:carrying`, true); } catch {} sound(g.dimension, g.location, 1.3); }
        const near = nearestPlayer(g.dimension, g.location);
        let dx = Math.random() - 0.5, dz = Math.random() - 0.5;
        if (near) { dx = g.location.x - near.p.location.x; dz = g.location.z - near.p.location.z; }
        const h = Math.hypot(dx, dz) || 1;
        Object.assign(f, { phase: "away", t: 0, dx: dx / h, dz: dz / h, rose: 0 });
      }
    } else {
      const p = g.location;
      const up = f.rose < CLIMB ? 0.2 : 0;
      f.rose += up;
      const n = { x: p.x + f.dx * 0.55, y: p.y + up, z: p.z + f.dz * 0.55 };
      try { g.teleport(n, { facingLocation: { x: n.x + f.dx, y: n.y + 0.2, z: n.z + f.dz } }); } catch {}
      if (f.t > 100) { try { g.remove(); } catch {} busy.delete(id); }
    }
  }
}

function look() {
  const now = system.currentTick;
  const seen = new Set();
  for (const p of world.getAllPlayers()) {
    const dim = p.dimension;
    if (dim.id !== "minecraft:overworld") continue;
    let items = [];
    try { items = dim.getEntities({ type: "minecraft:item", location: p.location, maxDistance: 40 }); } catch {}
    for (const item of items) {
      if (seen.has(item.id)) continue;
      seen.add(item.id);
      let id;
      try { id = item.getComponent("minecraft:item")?.itemStack?.typeId; } catch {}
      if (!FISH.has(id)) continue;
      if (!firstSeen.has(item.id)) firstSeen.set(item.id, now);
      if (now - firstSeen.get(item.id) < WAIT || targeted.has(item.id)) continue;
      const near = nearestPlayer(dim, item.location);
      if (near && near.d < SHY * SHY) continue;
      if (Math.random() > CHANCE) continue;
      let gulls = [];
      try { gulls = dim.getEntities({ type: GULL, location: item.location, maxDistance: 24 }); } catch {}
      const gull = gulls.find(g => !busy.has(g.id));
      if (gull) startTheft(gull, item, now);
    }
  }
  for (const id of firstSeen.keys()) if (!seen.has(id)) firstSeen.delete(id);
  lookAtRacks();
}

// Fish hung on a Drying Rack tempt gulls too, but far less: a rack keeps its fish up off the
// sand, and only a gull already close by (by the sea, over a school) notices it.
function lookAtRacks() {
  const players = world.getAllPlayers().filter(p => p.dimension.id === "minecraft:overworld");
  if (!players.length) return;
  for (const r of knownRacks()) {
    if (r.dimId !== "minecraft:overworld") continue;
    const at = { x: r.x + 0.5, y: r.y, z: r.z + 0.5 };
    const near = players.map(p => (p.location.x - at.x) ** 2 + (p.location.z - at.z) ** 2);
    if (!near.some(d => d < 40 * 40) || near.some(d => d < SHY * SHY)) continue;
    if (targeted.has(`rack:${r.x}:${r.y}:${r.z}`) || Math.random() > RACK_CHANCE) continue;
    const dim = players[0].dimension;
    let gulls = [];
    try { gulls = dim.getEntities({ type: GULL, location: at, maxDistance: 24 }); } catch {}
    const gull = gulls.find(g => !busy.has(g.id));
    if (gull) startTheft(gull, undefined, system.currentTick, r);
  }
}

// --------------------------------------------------------------------------- v1.3 fixes
// Scripted gulls (school circlers and thieves) have no gravity, no AI and no despawn of their
// own: the script moves them every 2 ticks. A gull the script no longer tracks therefore hung
// frozen in the sky forever and piled up over a long session. Three nets catch it now:
// untracking on unload (world/schools.js), removal when such a gull loads again, and a sweep.
const tracked = id => busy.has(id) || schoolTracks(id) || fleeing.some(f => f.e?.id === id);

function isScripted(e) {
  try { return e.typeId === GULL && !!e.getComponent("minecraft:type_family")?.hasTypeFamily(SCRIPTED); } catch { return false; }
}

function dropIfOrphan(e) {
  if (!e?.isValid || !isScripted(e) || tracked(e.id)) return;
  try { e.remove(); } catch {}
}

function sweep() {
  for (const p of world.getAllPlayers()) {
    if (p.dimension.id !== "minecraft:overworld") continue;
    let gulls = [];
    try { gulls = p.dimension.getEntities({ type: GULL, families: [SCRIPTED], location: p.location, maxDistance: 96 }); } catch {}
    for (const g of gulls) dropIfOrphan(g);
  }
}

// A scripted gull that is hit leaves its circle or its theft and flies off away from the
// attacker, level (at most CLIMB blocks up), instead of drifting straight up without gravity.
function onHurt(ev) {
  const g = ev.hurtEntity;
  if (!g?.isValid || !isScripted(g) || fleeing.some(f => f.e?.id === g.id)) return;
  if ((g.getComponent?.("minecraft:health")?.currentValue ?? 1) <= 0) return;
  schoolGullIds.delete(g.id);
  const f = busy.get(g.id);
  if (f) { targeted.delete(f.itemId); busy.delete(g.id); }
  const from = ev.damageSource?.damagingEntity?.location;
  let dx = Math.random() - 0.5, dz = Math.random() - 0.5;
  if (from) { dx = g.location.x - from.x; dz = g.location.z - from.z; }
  const h = Math.hypot(dx, dz) || 1;
  try { g.clearVelocity(); } catch {}
  fleeing.push({ e: g, dx: dx / h, dz: dz / h, t: 0, rose: 0 });
  sound(g.dimension, g.location, 1.5);
}

function flee() {
  for (let i = fleeing.length - 1; i >= 0; i--) {
    const f = fleeing[i];
    f.t += 2;
    if (!f.e?.isValid || f.t > 100) { try { f.e?.remove(); } catch {} fleeing.splice(i, 1); continue; }
    const p = f.e.location;
    const up = f.rose < CLIMB ? 0.25 : 0;
    f.rose += up;
    const n = { x: p.x + f.dx * 0.7, y: p.y + up, z: p.z + f.dz * 0.7 };
    try { f.e.teleport(n, { facingLocation: { x: n.x + f.dx, y: n.y, z: n.z + f.dz } }); } catch {}
  }
}

const guard = fn => () => { try { fn(); } catch (err) { console.warn(`[Fishing Voyage] seagulls: ${err}`); } };
system.runInterval(guard(() => { if (busy.size) fly(); if (fleeing.length) flee(); }), 2);
system.runInterval(guard(look), 40);
system.runInterval(guard(sweep), 200);
world.afterEvents.entityLoad.subscribe(ev => { try { dropIfOrphan(ev.entity); } catch {} });
world.afterEvents.entityHurt.subscribe(ev => { try { onHurt(ev); } catch {} }, { entityTypes: [GULL] });
export const _busyForTests = busy;
