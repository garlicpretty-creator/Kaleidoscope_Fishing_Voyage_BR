// ## Fish pond (魚池, 1.5.0, plan 7.2). A pond is water the player dug (or any water) with a Fish Pond Feeder at its edge.
// The feeder counts the water joined to it (16x16 around it, 6 deep, at most 512 blocks): 18 or more holds 4 fish,
// 48 holds 8, 96 holds 12. A pond in an ocean or beach biome, or one given 8 Salt, is a sea pond; otherwise fresh.
// Which fish live in which pond, and which breed, is tools/data/POND.json (made by tools/gen_1_5.py).
//   a fish on the feeder      it goes in the pond (size marks, record and name are kept)
//   feed on the feeder        stored as items, up to 64 meals (POND_FEEDS, and what other packs register)
//   8 Salt on the feeder      it becomes a sea pond
//   an empty hand             1.6.0: takes the roe out; with no roe, a roll call: every fish swims to the feeder
//                             for a moment (the hungry ones fastest), so they can be counted. No feed is used.
//   the Hand Net on a fish    1.6.0 (tools/handNet.js): takes that very fish out (on the water: the fish nearest
//                             the crosshair)
// Each dawn (world days, caught up when the feeder was out of reach) every fish eats one meal. A fed day counts
// towards growing: small to medium after 3, medium to large after 5 more. A hungry fish does not grow or breed and
// never dies. Two fed fish of a kind that breeds, medium or larger, with room in the pond: 1 in 4 each dawn for a
// clump of roe (one at a time, shown in the feeder's basket). Left there it hatches into a small fish 2 days later;
// taken out it is Fertilized Roe (blocks/tub.js hatches it). A fish that grew or was born here is farmed (✿,
// fishing/size.js): it carries no record mark, sets no records, and the merchant pays 60% for it. A farmed fish is
// only ever small, medium or large, never a length, so it never comes near a record (the plan's 85% cap).
// The roster lives in the feeder's block record ("pd"), the only truth. The fish swimming in the pond are the
// Fish Tank's display entities, put back from the roster when missing and moved about the water now and then.
// 1.6.0 (docs/PLAN_1.6.0.md section 7, no text): there is no list any more; the pond shows its state.
//   the trough        4 looks by meals stored (state feed: 0 empty, 1 a little, 2 most, 3 full; troughStage)
//   the fish          sized by class (small 0.6, medium 0.8, large 1.0 of the species' pond size); a hungry fish
//                     swims just under the surface and now and then sends up a column of bubbles, a fed one
//                     swims lower; a fish that grows a class jumps with a splash
//   a sea pond        a white fleck on the water now and then; salt going in makes a white puff
//   events            evt "pond" with kind "grow", "spawn" (roe) or "hatch" (other packs give their own feedback)
// Particles only while a player is within 16 blocks.
// The water is counted when the feeder is set down, used, and each dawn; fish that no longer fit come out as items.
// A feeder removed in any way (player, explosion, piston, command) gives back every fish, the feed and the roe.
import { EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { CATCHES, FISH_ALIAS, POND, POND_FEEDS, TANK_FISH } from "../data/generated.js";
import { fishGlyph } from "../data/glyphs.js";
import { FIT, TANK_KIND } from "../data/tank.js";
import { FARMED_MARK, LARGE, MEDIUM, SMALL, isFarmed, markOf, readSize } from "../fishing/size.js";
import { emit } from "../api/host.js";
import { fishOut, keepOf } from "./keep.js";
import { readData, writeData } from "./blockData.js";
import { registerRecords, registerStation, spawnAll } from "./contents.js";
import { externalFeed, externalTank } from "../fishing/registry.js";
import { isWater } from "../fishing/water.js";
import { refuseAt } from "../util/hint.js";
import { spawnParticle } from "../util/particles.js";
import { ambient, burst, feedFx } from "./stationFx.js";

const NS = "kaleidoscope_fishing";
export const FEEDER = `${NS}:pond_feeder`;
const FISH_ID = `${NS}:tank_fish`;
const SALT = `${NS}:sea_salt`, ROE_ITEM = `${NS}:fertilized_roe`;
export const ROE_PROP = "kfv:roe";
const FEED = `${NS}:feed`, ROE = `${NS}:roe`;
export const MAX_MEALS = 64;
export const SALT_NEEDED = 8;
export const GROW = { [SMALL]: 3, [MEDIUM]: 5 };      // fed days to the next class
export const BREED_CHANCE = 0.25;
export const HATCH_DAYS = 2;
const CATCH_UP = 30;                                  // days caught up at most in one go
const RANGE = 8, DEEP = 6, MAX_WATER = 512;
export const TAG = "kfv_pond:";
export const FISH_ENTITY = FISH_ID;
/** 1.6.0: a pond fish's size on screen by class (0 = a creature without sizes). */
export const POND_SCALE = { 0: 0.8, [SMALL]: 0.6, [MEDIUM]: 0.8, [LARGE]: 1.0 };
/** 1.6.0: the trough's look by meals stored: 0 empty, 1 from TROUGH[0], 2 from TROUGH[1], 3 from TROUGH[2]. */
export const TROUGH = [1, 32, 56];
export const troughStage = m => (m >= TROUGH[2] ? 3 : m >= TROUGH[1] ? 2 : m >= TROUGH[0] ? 1 : 0);
const NEAR = 16;                                      // particles only for players this close
const HIT_EVENT = `${NS}:pond_fish`;                  // gives a pond fish a hitbox (the Hand Net aims at it)
const DRAWN_ABOVE = 0.55;                             // a pond fish is drawn about this far above its entity (its level)
const canon = id => FISH_ALIAS[id] ?? id;
const SEA_BIOME = /ocean|beach|shore/;
const SIZED = new Set(CATCHES.filter(c => c.size).map(c => c.id));
const CATCH_IDS = new Set(CATCHES.map(c => c.id));
// 1.5.0 (register_tank with `pond`): another pack's creature lives here drawn as its `like`, sized as its `like`.
const PONDS = { fresh: "fresh", salt: "sea", both: "both" };
/** [water, breeds] for a creature, ours or registered; undefined when it never goes in a pond. Exported for tests. */
export function pondOf(id) {
  const ours = POND[canon(id)];
  if (ours) return ours;
  const e = externalTank(id);
  return e && PONDS[e.pond] ? [PONDS[e.pond], !!e.breed] : undefined;
}
const likeOf = id => (POND[canon(id)] ? canon(id) : externalTank(id)?.like ?? canon(id));
const sized = id => SIZED.has(likeOf(id));

/** Fish the pond holds for that much water. Exported for tests. */
export const capOf = n => (n >= 96 ? 12 : n >= 48 ? 8 : n >= 18 ? 4 : 0);
/** Meals one item gives as pond feed (0 = not a feed). */
export const mealsOf = id => POND_FEEDS[id] ?? externalFeed(id) ?? 0;
const today = () => { try { return world.getDay(); } catch { return 0; } };
const creative = p => { try { const g = p.getGameMode(); return g === GameMode.Creative || g === "creative"; } catch { return false; } };
const snd = (dim, at, id, pitch = 1, volume = 0.7) => { try { dim.playSound(id, at, { pitch, volume }); } catch {} };
const centreOf = b => ({ x: b.x + 0.5, y: b.y + 0.5, z: b.z + 0.5 });
const tagOf = p => `${TAG}${p.x},${p.y},${p.z}`;

// ------------------------------------------------------------------------------------------------ the water
/** Count the water joined to a feeder at pos: { n, spots, other, sea }. `other` is true when another feeder already
 *  stands by this water. Exported for tests. */
export function countPond(dim, pos) {
  const seen = new Set(), queue = [], spots = [];
  let other = false;
  const key = (x, y, z) => `${x},${y},${z}`;
  const inside = (x, y, z) => Math.abs(x - pos.x) <= RANGE && Math.abs(z - pos.z) <= RANGE && y <= pos.y + 1 && y >= pos.y - DEEP;
  const look = (x, y, z) => {
    if (!inside(x, y, z) || seen.has(key(x, y, z)) || seen.size >= MAX_WATER) return;
    let b;
    try { b = dim.getBlock({ x, y, z }); } catch { return; }
    if (!isWater(b)) return;
    seen.add(key(x, y, z)); queue.push([x, y, z]);
  };
  for (const [dx, dy, dz] of [[1, 0, 0], [-1, 0, 0], [0, 0, 1], [0, 0, -1], [0, -1, 0], [1, -1, 0], [-1, -1, 0], [0, -1, 1], [0, -1, -1]])
    look(pos.x + dx, pos.y + dy, pos.z + dz);
  for (let i = 0; i < queue.length; i++) {
    const [x, y, z] = queue[i];
    for (const [dx, dy, dz] of [[1, 0, 0], [-1, 0, 0], [0, 0, 1], [0, 0, -1], [0, 1, 0], [0, -1, 0]]) {
      const nx = x + dx, ny = y + dy, nz = z + dz;
      if (!other && !(nx === pos.x && ny === pos.y && nz === pos.z) && dy >= 0) {
        try { if (dim.getBlock({ x: nx, y: ny, z: nz })?.typeId === FEEDER) other = true; } catch {}
      }
      look(nx, ny, nz);
    }
    if (spots.length < 32) {
      let above;
      try { above = dim.getBlock({ x, y: y + 1, z }); } catch {}
      if (!isWater(above)) spots.push([x, y, z]);           // the top water: the fish swim just under it
    }
  }
  let sea = false;
  try { sea = SEA_BIOME.test(String(dim.getBiome?.(pos)?.id ?? "")); } catch {}
  return { n: seen.size, spots, other, sea };
}

// ------------------------------------------------------------------------------------------------ the record
/** A new pond record. */
function fresh(c) { return { n: c.n, cap: capOf(c.n), sea: c.sea, salt: 0, spots: c.spots, fish: [], food: [], open: 0, day: today() }; }
const read = (dim, pos) => readData("pd", dim, pos);
const save = (dim, pos, r) => writeData("pd", dim, pos, r);
export const isSea = r => !!(r?.sea || (r?.salt ?? 0) >= SALT_NEEDED);
/** Meals stored. */
export const meals = r => (Number(r?.open) || 0) + (r?.food ?? []).reduce((a, [id, n]) => a + n * mealsOf(id), 0);
/** Eat one meal; false when there is none. */
function eat(r) {
  if (r.open > 0) { r.open--; return true; }
  while (r.food.length) {
    const top = r.food[0];
    const m = mealsOf(top[0]);
    top[1]--;
    if (top[1] <= 0) r.food.shift();
    if (m > 0) { r.open = m - 1; return true; }
  }
  return false;
}
/** Whether a pond takes this fish: "" when it does, else the reason (a hint key). Exported for tests. */
export function whyNot(r, id) {
  const p = pondOf(id);
  if (!p || !TANK_FISH.includes(likeOf(id))) return "pond_cannot";
  if (!r || !r.cap) return "pond_none";
  if (p[0] !== "both" && (p[0] === "sea") !== isSea(r)) return isSea(r) ? "pond_fresh_fish" : "pond_sea_fish";
  if (r.fish.length >= r.cap) return "pond_full";
  return "";
}
const adult = f => !sized(f.id) || f.cls >= MEDIUM;

/** One dawn: every fish eats, fed ones grow, the roe hatches, a pair may spawn. Returns what happened, for the
 *  splashes and the evt broadcast: [{ kind: "grow" | "hatch" | "spawn", id, cls?, slot? }]. Exported for tests. */
export function dawn(r, day, rand = Math.random) {
  const fed = [], ev = [];
  for (const f of r.fish) {
    f.d = (f.d ?? 0) + 1;
    f.h = eat(r) ? 0 : 1;
    if (f.h) continue;
    fed.push(f);
    if (!sized(f.id)) continue;
    f.g = (f.g ?? 0) + 1;
    const need = GROW[f.cls || MEDIUM];
    if (need && f.g >= need && f.cls < LARGE) {
      f.cls = (f.cls || MEDIUM) + 1; f.g = 0; f.f = 1; delete f.k?.lore;
      ev.push({ kind: "grow", id: f.id, cls: f.cls, slot: r.fish.indexOf(f) });
    }
  }
  if (r.roe && day - r.roe.day >= HATCH_DAYS && r.fish.length < r.cap) {
    r.fish.push({ id: r.roe.id, cls: sized(r.roe.id) ? SMALL : 0, d: 0, g: 0, f: 1 });
    ev.push({ kind: "hatch", id: r.roe.id, cls: r.fish[r.fish.length - 1].cls, slot: r.fish.length - 1 });
    r.roe = undefined;
  }
  if (!r.roe && r.fish.length < r.cap) {
    const by = {};
    for (const f of fed) if (pondOf(f.id)?.[1] && adult(f)) by[f.id] = (by[f.id] ?? 0) + 1;
    const pairs = Object.keys(by).filter(id => by[id] >= 2);
    if (pairs.length && rand() < BREED_CHANCE) { r.roe = { id: pairs[Math.floor(rand() * pairs.length)], day }; ev.push({ kind: "spawn", id: r.roe.id }); }
  }
  return ev;
}

/** A fish leaving the pond as an item. */
export function fishStack(f, n = 1) {
  let s;
  try { s = new ItemStack(f.id, n); } catch { return undefined; }   // another pack's creature whose pack is gone
  if (f.f) {
    try { s.setLore([...(f.cls ? [markOf(f.cls)] : []), FARMED_MARK]); } catch {}
    if (f.k?.name) { try { s.nameTag = f.k.name; } catch {} }
    return s;
  }
  return fishOut(s, f.cls, f.k);
}
export function roeStack(id) {
  const s = new ItemStack(ROE_ITEM, 1);
  try { s.setDynamicProperty(ROE_PROP, id); } catch {}
  try { s.setLore([`§r${fishGlyph(id)}`]); } catch {}   // 1.6.0: the fish's picture, no words (the species is ROE_PROP)
  return s;
}
/** Everything a feeder holds, as stacks. */
export function contents(r) {
  if (!r) return [];
  const out = (r.fish ?? []).map(f => fishStack(f)).filter(Boolean);
  for (const [id, n] of r.food ?? []) if (n > 0) { try { out.push(new ItemStack(id, n)); } catch {} }
  if (r.roe) out.push(roeStack(r.roe.id));
  return out;
}

// ------------------------------------------------------------------------------------------------ the fish in the water
function fishEntities(dim, pos) {
  try { return dim.getEntities({ type: FISH_ID, tags: [tagOf(pos)], location: centreOf(pos), maxDistance: 16 }); } catch { return []; }
}
const playersNear = (dim, pos) => { try { return dim.getPlayers({ location: centreOf(pos), maxDistance: NEAR }).length > 0; } catch { return false; } };
const dynOf = (e, k) => { try { return e.getDynamicProperty(k); } catch { return undefined; } };
/** 1.6.0: how deep a fish swims under the top water block: hungry just under the surface, fed lower. */
export const depthOf = f => (f?.h ? 0.15 : 0.6);
const spotAt = (s, f) => ({ x: s[0] + 0.5, y: s[1] + 0.55 - depthOf(f) - 0.45, z: s[2] + 0.5 });
/** 1.6.0: the scale property of a pond fish: the species' size in the large tank, by its class. Exported for tests. */
export function scaleOf(spec, cls) {
  const fit = FIT[spec]?.[1]?.[LARGE] ?? FIT[spec]?.[1]?.[2];
  if (!fit) return 0;
  return Math.max(1, Math.min(100, Math.round(fit[0] * 1.3 * (POND_SCALE[cls] ?? POND_SCALE[0]))));
}
function giveHitbox(e) {
  if (dynOf(e, "kfv:hit") === 1) return;
  try { e.triggerEvent(HIT_EVENT); e.setDynamicProperty("kfv:hit", 1); } catch {}
}
function spawnOne(dim, pos, r, slot) {
  const f = r.fish[slot];
  const spec = TANK_FISH.indexOf(likeOf(f.id));
  const spot = r.spots?.[Math.floor(Math.random() * (r.spots?.length || 1))];
  if (spec < 0 || !spot) return;
  const fit = FIT[spec]?.[1]?.[f.cls || MEDIUM] ?? FIT[spec]?.[1]?.[2];
  if (!fit) return;
  let e;
  try { e = dim.spawnEntity(FISH_ID, spotAt(spot, f)); } catch { return; }
  const props = { species: spec, kind: TANK_KIND[spec] ?? 0, seed: Math.floor(Math.random() * 8), turn: Math.floor(Math.random() * 4), tank: 1,
    scale: scaleOf(spec, sized(f.id) ? f.cls || MEDIUM : 0), span: fit[1], level: Math.round((fit[2] + fit[3]) / 2), lane: 60 };
  for (const [k, v] of Object.entries(props)) { try { e.setProperty(`${NS}:${k}`, v); } catch {} }
  try { e.addTag(tagOf(pos)); e.setDynamicProperty("kfv:slot", slot); e.setDynamicProperty("kfv:id", f.id); e.setDynamicProperty("kfv:cls", f.cls ?? 0); e.setDynamicProperty("kfv:h", f.h ? 1 : 0); } catch {}
  giveHitbox(e);
}
/** Make the swimming fish match the roster; move one of them to another part of the pond. */
function syncFish(dim, pos, r, wander = true) {
  const have = fishEntities(dim, pos);
  const kept = new Set(), alive = [];
  for (const e of have) {
    const slot = dynOf(e, "kfv:slot"), id = dynOf(e, "kfv:id"), cls = dynOf(e, "kfv:cls");
    const f = r?.fish?.[slot];
    if (!f || kept.has(slot) || f.id !== id || (f.cls ?? 0) !== cls) { try { e.remove(); } catch {} continue; }
    kept.add(slot); alive.push(e);
    giveHitbox(e);
    const h = f.h ? 1 : 0;
    if (dynOf(e, "kfv:h") !== h) {                     // got hungry, or was fed: up to the surface, or down
      try { e.setDynamicProperty("kfv:h", h); } catch {}
      try { const l = e.location; e.teleport({ x: l.x, y: l.y + (h ? 0.45 : -0.45), z: l.z }); } catch {}
    }
  }
  (r?.fish ?? []).forEach((f, slot) => { if (!kept.has(slot)) spawnOne(dim, pos, r, slot); });
  // a fish left mid-glide (the world closed, the glide's timer lost) stops gliding
  for (const e of alive) { try { if (e.isValid && !gliding.has(e.id) && e.getProperty(`${NS}:glide`)) e.setProperty(`${NS}:glide`, false); } catch {} }
  if (wander && alive.length && r?.spots?.length && Math.random() < 0.5) {
    const e = alive[Math.floor(Math.random() * alive.length)];
    const s = r.spots[Math.floor(Math.random() * r.spots.length)];
    if (e.isValid && !gliding.has(e.id)) swimTo(dim, e, spotAt(s, r.fish[dynOf(e, "kfv:slot")]));   // 1.6.0: at its depth (hungry high, fed low)
  }
}
// 1.5.0 (immersive motion): a pond fish moving to another spot swims there: carried in small steps along the water,
// eased in and out, facing where it goes (the `glide` property turns the model to the heading; see the resource
// pack's tank_fish animations), with a ripple where it sets off and where it stops. When the straight line crosses
// anything but water (an L-shaped pond) it dives instead: a ripple here, a ripple there, no gliding through the bank.
const gliding = new Set();
const GLIDE_SPEED = 0.07;                              // blocks per tick, an easy cruise
const ripple = (dim, at) => spawnParticle(dim, `${NS}:creature_ripple`, { x: at.x, y: Math.floor(at.y) + 1.9, z: at.z });
function clearLine(dim, a, b) {
  const n = Math.ceil(Math.hypot(b.x - a.x, b.z - a.z) * 2);
  for (let i = 1; i < n; i++) {
    const k = i / n;
    let blk;
    try { blk = dim.getBlock({ x: Math.floor(a.x + (b.x - a.x) * k), y: Math.floor(a.y + 0.5), z: Math.floor(a.z + (b.z - a.z) * k) }); } catch { return false; }
    if (!isWater(blk)) return false;
  }
  return true;
}
/** Move one pond fish to `to` as a swim (exported for tests: returns the number of steps, 0 for a jump). */
export function swimTo(dim, e, to) {
  const from = { ...e.location };
  const dist = Math.hypot(to.x - from.x, to.z - from.z);
  const turn = Math.floor(Math.random() * 4);
  if (dist < 0.3) return 0;
  ripple(dim, from);
  if (Math.abs(to.y - from.y) > 0.6 || !clearLine(dim, from, to)) {
    try { e.teleport(to); } catch {}
    try { e.setProperty(`${NS}:turn`, turn); } catch {}
    ripple(dim, to);
    return 0;
  }
  const steps = Math.max(4, Math.min(30, Math.round(dist / GLIDE_SPEED / 2)));   // a step every 2 ticks, 3 s at most
  gliding.add(e.id);
  try { e.setProperty(`${NS}:glide`, true); } catch {}
  let i = 0;
  const id = e.id;
  const h = system.runInterval(() => {
    i++;
    if (!e.isValid) { system.clearRun(h); gliding.delete(id); return; }
    const k = (1 - Math.cos(Math.PI * Math.min(1, i / steps))) / 2;
    const at = { x: from.x + (to.x - from.x) * k, y: from.y + (to.y - from.y) * k, z: from.z + (to.z - from.z) * k };
    try { e.teleport(at, { facingLocation: { x: to.x + (to.x - from.x), y: at.y, z: to.z + (to.z - from.z) } }); } catch {}
    if (i < steps) return;
    system.clearRun(h);
    gliding.delete(id);
    try { e.setProperty(`${NS}:glide`, false); e.setProperty(`${NS}:turn`, turn); } catch {}
    ripple(dim, to);
  }, 2);
  return steps;
}
function clearFish(dim, pos) { for (const e of fishEntities(dim, pos)) { try { e.remove(); } catch {} } }

/** 1.6.0 roll call: every fish swims to the water by the feeder over 2 seconds, a hungry one in half the time.
 *  Returns [{ entity, steps }] (5 ticks a step). Exported for tests. */
export function rollCall(dim, pos, r) {
  const spots = r?.spots ?? [];
  if (!spots.length) return [];
  const near = spots.reduce((a, s) => ((s[0] - pos.x) ** 2 + (s[2] - pos.z) ** 2 < (a[0] - pos.x) ** 2 + (a[2] - pos.z) ** 2 ? s : a));
  const out = [];
  for (const e of fishEntities(dim, pos)) {
    const f = r.fish?.[dynOf(e, "kfv:slot")];
    if (!f) continue;
    const steps = f.h ? 4 : 8;
    let from;
    try { from = { ...e.location }; } catch { continue; }
    const to = spotAt(near, f);
    to.x += (Math.random() - 0.5) * 0.6; to.z += (Math.random() - 0.5) * 0.6;
    for (let i = 1; i <= steps; i++) {
      const k = i / steps;
      system.runTimeout(() => {
        try { if (e.isValid) e.teleport({ x: from.x + (to.x - from.x) * k, y: from.y + (to.y - from.y) * k, z: from.z + (to.z - from.z) * k }); } catch {}
      }, i * 5);
    }
    out.push({ entity: e, steps });
  }
  if (out.length) snd(dim, centreOf(pos), "random.swim", 1.4, 0.4);
  return out;
}

/** 1.6.0 Hand Net: the pond fish nearest the line of sight from `head` along `dir` (within 8 blocks ahead and 1.5
 *  blocks off the line), among `entities`. Exported for tests. */
export function aimedFish(head, dir, entities) {
  let best, bestOff = 1.5;
  for (const e of entities) {
    let l;
    try { if (!e.getTags().some(t => t.startsWith(TAG))) continue; l = e.location; } catch { continue; }
    const v = { x: l.x - head.x, y: l.y + DRAWN_ABOVE - head.y, z: l.z - head.z };
    const along = v.x * dir.x + v.y * dir.y + v.z * dir.z;
    if (along < 0 || along > 8) continue;
    const off = Math.hypot(v.x - dir.x * along, v.y - dir.y * along, v.z - dir.z * along);
    if (off <= bestOff) { best = e; bestOff = off; }
  }
  return best;
}
/** The pond fish a player aims the net at, looking at the water. */
export function aimedPondFish(player) {
  try {
    const head = player.getHeadLocation(), dir = player.getViewDirection();
    return aimedFish(head, dir, player.dimension.getEntities({ type: FISH_ID, location: head, maxDistance: 9 }));
  } catch { return undefined; }
}
/** 1.6.0 Hand Net: take the fish this display entity stands for out of its pond. False (nothing happens) when the
 *  pond changed under it: the fish is gone, or the entity is stale. Exported for tests; tools/handNet.js calls it. */
export function scoop(player, e) {
  let tag, slot, id, cls, dim;
  try { tag = e.getTags().find(t => t.startsWith(TAG)); slot = e.getDynamicProperty("kfv:slot"); id = e.getDynamicProperty("kfv:id"); cls = e.getDynamicProperty("kfv:cls"); dim = e.dimension; } catch { return false; }
  if (!tag || typeof slot !== "number") return false;
  const [x, y, z] = tag.slice(TAG.length).split(",").map(Number);
  const pos = { x, y, z };
  let b;
  try { b = dim.getBlock(pos); } catch { return false; }
  const r = read(dim, pos);
  if (b?.typeId !== FEEDER || !r) { try { e.remove(); } catch {} return false; }
  const f = r.fish?.[slot];
  if (!f || f.id !== id || (f.cls ?? 0) !== cls) { syncFish(dim, pos, r, false); return false; }
  const out = fishStack(f);
  if (!out) { refuseAt(player, "tank_pack_gone", { dimension: dim, location: e.location }); return false; }
  let at;
  try { at = { ...e.location }; } catch { at = centreOf(pos); }
  r.fish.splice(slot, 1);
  try { e.remove(); } catch {}
  for (const o of fishEntities(dim, pos)) {         // the fish after it move up one place in the roster
    const s = dynOf(o, "kfv:slot");
    if (typeof s === "number" && s > slot) { try { o.setDynamicProperty("kfv:slot", s - 1); } catch {} }
  }
  save(dim, pos, r); show(b, r); syncFish(dim, pos, r, false);
  give(player, out, at);
  snd(dim, at, "random.splash", 1.3, 0.5);
  try { spawnParticle(dim, "minecraft:water_splash_particle", at); } catch {}
  return true;
}

// ------------------------------------------------------------------------------------------------ the feeder
function show(block, r) {
  const want = { [FEED]: troughStage(meals(r)), [ROE]: r?.roe ? 1 : 0 };
  let p = block.permutation, changed = false;
  for (const [k, v] of Object.entries(want)) { try { if (p.getState(k) !== v) { p = p.withState(k, v); changed = true; } } catch {} }
  if (changed) { try { block.setPermutation(p); } catch {} }
}
/** Count the water again; fish that no longer fit come out. */
function recount(block, r) {
  const c = countPond(block.dimension, block);
  r.n = c.n; r.cap = capOf(c.n); r.sea = c.sea; r.spots = c.spots;
  const out = r.fish.splice(r.cap);
  if (out.length) spawnAll(block.dimension, block, out.map(f => fishStack(f)).filter(Boolean));
  return r;
}
/** Days missed since the record was last seen. Returns what happened ([] when nothing did, undefined when no day passed). */
function catchUp(block, r) {
  const d = today();
  if (typeof r.day !== "number" || r.day > d) { r.day = d; return undefined; }
  if (r.day === d) return undefined;
  recount(block, r);
  const ev = [];
  let steps = 0;
  while (r.day < d && steps < CATCH_UP) { r.day++; steps++; ev.push(...dawn(r, r.day)); }
  r.day = d;
  return ev;
}
/** After a dawn: a fish that grew jumps with a splash, the roe hatching splashes too; and other packs hear of it. */
function announce(block, r, ev) {
  if (!ev?.length) return;
  const dim = block.dimension, pos = { x: block.x, y: block.y, z: block.z };
  const near = playersNear(dim, pos);
  const ents = near ? fishEntities(dim, pos) : [];
  for (const x of ev) {
    try { emit("pond", undefined, { kind: x.kind, id: x.id, ...(x.cls !== undefined ? { cls: x.cls } : {}), dim: dim.id, pos: [pos.x, pos.y, pos.z] }); } catch {}
    if (!near || x.kind === "spawn") continue;
    const e = ents.find(o => dynOf(o, "kfv:slot") === x.slot);
    let at = centreOf(pos);
    try { if (e) at = { ...e.location }; } catch {}
    const top = { x: at.x, y: Math.floor(at.y) + 1, z: at.z };
    for (let i = 0; i < 4; i++) {
      try { spawnParticle(dim, "minecraft:water_splash_particle", { x: top.x + (Math.random() - 0.5) * 0.5, y: top.y, z: top.z + (Math.random() - 0.5) * 0.5 }); } catch {}
    }
    snd(dim, top, x.kind === "grow" ? "random.splash" : "bubble.pop", 1.1, 0.6);
    if (e && x.kind === "grow") {                     // the jump (placeholder for a flip animation): up out of the water and back
      try { e.teleport({ x: at.x, y: top.y + 0.3, z: at.z }); } catch {}
      system.runTimeout(() => { try { if (e.isValid) e.teleport(at); } catch {} }, 6);
    }
  }
}
/** Now and then, for players nearby: bubbles over a hungry fish, a white fleck on a sea pond. */
function ambience(block, r) {
  if (!r?.fish?.length && !isSea(r)) return;
  ambient(block, "pond", 90, centreOf(block), () => ambienceNow(block, r));
}
function ambienceNow(block, r) {
  const dim = block.dimension, pos = { x: block.x, y: block.y, z: block.z };
  if (!playersNear(dim, pos)) return;
  for (const e of fishEntities(dim, pos)) {
    const f = r.fish[dynOf(e, "kfv:slot")];
    if (!f?.h || Math.random() >= 0.35) continue;
    let l;
    try { l = e.location; } catch { continue; }
    for (let i = 0; i < 3; i++) { try { spawnParticle(dim, "minecraft:bubble_column_up_particle", { x: l.x, y: l.y + 0.2 + i * 0.25, z: l.z }); } catch {} }
  }
  if (isSea(r) && r.spots?.length && Math.random() < 0.4) {
    const s = r.spots[Math.floor(Math.random() * r.spots.length)];
    try { spawnParticle(dim, "minecraft:snowflake_particle", { x: s[0] + 0.2 + Math.random() * 0.6, y: s[1] + 0.95, z: s[2] + 0.2 + Math.random() * 0.6 }); } catch {}
  }
}
function saltPuff(block, r) {
  const dim = block.dimension;
  for (const sp of (r.spots ?? []).slice(0, 6)) {
    try { spawnParticle(dim, "minecraft:white_smoke_particle", { x: sp[0] + 0.5, y: sp[1] + 1, z: sp[2] + 0.5 }); } catch {}
  }
}
function takeHeld(player, slot, n) {
  if (creative(player)) return;
  const it = slot.getItem(); if (!it) return;
  if (it.amount <= n) slot.setItem(undefined); else { it.amount -= n; slot.setItem(it); }
}
function give(player, stack, at) {
  try { const left = player.getComponent("minecraft:inventory")?.container?.addItem(stack); if (left) player.dimension.spawnItem(left, at); }
  catch { try { player.dimension.spawnItem(stack, at); } catch {} }
}

export const pondFeeder = {
  beforeOnPlayerPlace(e) {
    let c;
    try { c = countPond(e.block.dimension, e.block); } catch { return; }
    if (c.other) { e.cancel = true; const p = e.player; system.run(() => refuseAt(p, "pond_has_feeder", e.block)); }
  },
  onPlace({ block }) {
    if (read(block.dimension, block)) return;
    const r = fresh(countPond(block.dimension, block));
    save(block.dimension, block, r);
  },
  onPlayerInteract({ block, player }) {
    if (!player) return;
    const dim = block.dimension;
    let r = read(dim, block) ?? fresh(countPond(dim, block));
    const ev = catchUp(block, r);
    if (ev) { save(dim, block, r); show(block, r); syncFish(dim, block, r, false); announce(block, r, ev); }
    const slot = player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
    const held = slot?.hasItem() ? slot.getItem() : undefined;
    if (!held) {                                      // 1.6.0: the roe, or else a roll call
      recount(block, r);
      if (r.roe) {
        const id = r.roe.id;
        r.roe = undefined;
        save(dim, block, r); show(block, r); syncFish(dim, block, r, false);
        give(player, roeStack(id), centreOf(block));
        snd(dim, centreOf(block), "random.splash", 1.3, 0.5);
        return;
      }
      save(dim, block, r); show(block, r); syncFish(dim, block, r, false);
      rollCall(dim, block, r);
      return;
    }
    const id = held.typeId;
    const feed = mealsOf(id);
    if (feed > 0) {
      const room = Math.floor((MAX_MEALS - meals(r)) / feed);
      if (room <= 0) return refuseAt(player, "pond_feed_full", block);
      const n = Math.min(room, held.amount);
      const top = r.food[r.food.length - 1];
      if (top && top[0] === id) top[1] += n; else r.food.push([id, n]);
      takeHeld(player, slot, n);
      save(dim, block, r); show(block, r);
      snd(dim, centreOf(block), "dig.sand", 1.4, 0.5);
      feedFx(dim, block, r.spots);                        // 1.5.0: pellets scatter onto the water (stationFx.js)
      return;
    }
    if (id === SALT) {
      if (isSea(r)) return refuseAt(player, "pond_salted", block);
      if (held.amount < SALT_NEEDED && !creative(player)) return refuseAt(player, "pond_salt", block, SALT_NEEDED);
      takeHeld(player, slot, SALT_NEEDED);
      r.salt = SALT_NEEDED;
      save(dim, block, r);
      snd(dim, centreOf(block), "dig.sand", 1.0, 0.6);
      burst(dim, { x: block.x + 0.5, y: block.y + 0.8, z: block.z + 0.5 }, "salt", "salt");
      saltPuff(block, r);                                 // 1.6.0: and a white puff over the water
      return;
    }
    if (pondOf(id) !== undefined || CATCH_IDS.has(canon(id))) {
      recount(block, r);
      const why = whyNot(r, id);
      if (why) { save(dim, block, r); return refuseAt(player, why, block); }
      const cls = readSize(held).cls;
      const fid = POND[canon(id)] || CATCH_IDS.has(canon(id)) ? canon(id) : id;
      r.fish.push({ id: fid, cls: sized(fid) ? (cls || MEDIUM) : 0, d: 0, g: 0, f: isFarmed(held) ? 1 : 0, k: keepOf(held) });
      takeHeld(player, slot, 1);
      save(dim, block, r); syncFish(dim, block, r, false);
      snd(dim, centreOf(block), "random.splash", 1.0, 0.6);
      try { spawnParticle(dim, "minecraft:water_splash_particle", centreOf(block)); } catch {}
      return;
    }
    refuseAt(player, "pond_what", block);
  },
  onTick({ block }) {
    const r = read(block.dimension, block);
    if (!r) return;
    const ev = catchUp(block, r);
    if (ev) save(block.dimension, block, r);
    show(block, r);
    syncFish(block.dimension, block, r);
    announce(block, r, ev);
    ambience(block, r);
  },
  onPlayerBreak({ block, brokenBlockPermutation, player }) {
    if (player && creative(player)) { clearFish(block.dimension, block); save(block.dimension, block, undefined); return; }
    dropPond(block.dimension, block, brokenBlockPermutation);
  },
};

export function dropPond(dim, pos) {
  const r = read(dim, pos);
  save(dim, pos, undefined);
  clearFish(dim, pos);
  spawnAll(dim, pos, contents(r));
}
registerStation(FEEDER, dropPond);
registerRecords(`${NS}:bd:pd:`, FEEDER, (dim, pos) => dropPond(dim, pos));

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(FEEDER, pondFeeder);
});
