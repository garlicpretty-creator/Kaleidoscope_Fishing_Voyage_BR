// ## Fish pond (魚池, 1.5.0, plan 7.2). A pond is water the player dug (or any water) with a Fish Pond Feeder at its edge.
// The feeder counts the water joined to it (16x16 around it, 6 deep, at most 512 blocks): 18 or more holds 4 fish,
// 48 holds 8, 96 holds 12. A pond in an ocean or beach biome, or one given 8 Salt, is a sea pond; otherwise fresh.
// Which fish live in which pond, and which breed, is tools/data/POND.json (made by tools/gen_1_5.py).
//   a fish on the feeder      it goes in the pond (size marks, record and name are kept)
//   feed on the feeder        stored as items, up to 64 meals (POND_FEEDS, and what other packs register)
//   8 Salt on the feeder      it becomes a sea pond
//   an empty hand             the list: take a fish (or the roe) back out
// Each dawn (world days, caught up when the feeder was out of reach) every fish eats one meal. A fed day counts
// towards growing: small to medium after 3, medium to large after 5 more. A hungry fish does not grow or breed and
// never dies. Two fed fish of a kind that breeds, medium or larger, with room in the pond: 1 in 4 each dawn for a
// clump of roe (one at a time, shown in the feeder's basket). Left there it hatches into a small fish 2 days later;
// taken out it is Fertilized Roe (blocks/tub.js hatches it). A fish that grew or was born here is farmed (✿,
// fishing/size.js): it carries no record mark, sets no records, and the merchant pays 60% for it. A farmed fish is
// only ever small, medium or large, never a length, so it never comes near a record (the plan's 85% cap).
// The roster lives in the feeder's block record ("pd"), the only truth. The fish swimming in the pond are the
// Fish Tank's display entities, put back from the roster when missing and moved about the water now and then.
// The water is counted when the feeder is set down, used, and each dawn; fish that no longer fit come out as items.
// A feeder removed in any way (player, explosion, piston, command) gives back every fish, the feed and the roe.
import { EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";
import { CATCHES, FISH_ALIAS, POND, POND_FEEDS, TANK_FISH } from "../data/generated.js";
import { FIT, TANK_KIND } from "../data/tank.js";
import { FARMED_MARK, LARGE, MEDIUM, SMALL, isFarmed, markOf, readSize } from "../fishing/size.js";
import { fishOut, keepOf } from "./keep.js";
import { readData, writeData } from "./blockData.js";
import { registerRecords, registerStation, spawnAll } from "./contents.js";
import { externalFeed, externalTank } from "../fishing/registry.js";
import { isWater } from "../fishing/water.js";
import { refuseAt } from "../util/hint.js";
import { spawnParticle } from "../util/particles.js";

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
const TAG = "kfv_pond:";
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

/** One dawn: every fish eats, fed ones grow, the roe hatches, a pair may spawn. Exported for tests. */
export function dawn(r, day, rand = Math.random) {
  const fed = [];
  for (const f of r.fish) {
    f.d = (f.d ?? 0) + 1;
    f.h = eat(r) ? 0 : 1;
    if (f.h) continue;
    fed.push(f);
    if (!sized(f.id)) continue;
    f.g = (f.g ?? 0) + 1;
    const need = GROW[f.cls || MEDIUM];
    if (need && f.g >= need && f.cls < LARGE) { f.cls = (f.cls || MEDIUM) + 1; f.g = 0; f.f = 1; delete f.k?.lore; }
  }
  if (r.roe && day - r.roe.day >= HATCH_DAYS && r.fish.length < r.cap) {
    r.fish.push({ id: r.roe.id, cls: sized(r.roe.id) ? SMALL : 0, d: 0, g: 0, f: 1 });
    r.roe = undefined;
  }
  if (!r.roe && r.fish.length < r.cap) {
    const by = {};
    for (const f of fed) if (pondOf(f.id)?.[1] && adult(f)) by[f.id] = (by[f.id] ?? 0) + 1;
    const pairs = Object.keys(by).filter(id => by[id] >= 2);
    if (pairs.length && rand() < BREED_CHANCE) r.roe = { id: pairs[Math.floor(rand() * pairs.length)], day };
  }
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
  try { s.setLore([{ translate: `${NS}.lore.roe_of`, with: { rawtext: [{ translate: `${NS}.name.${id.split(":")[1]}` }] } }]); } catch {}
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
function spawnOne(dim, pos, r, slot) {
  const f = r.fish[slot];
  const spec = TANK_FISH.indexOf(likeOf(f.id));
  const spot = r.spots?.[Math.floor(Math.random() * (r.spots?.length || 1))];
  if (spec < 0 || !spot) return;
  const fit = FIT[spec]?.[1]?.[f.cls || MEDIUM] ?? FIT[spec]?.[1]?.[2];
  if (!fit) return;
  let e;
  const at = { x: spot[0] + 0.5, y: spot[1] - 0.45, z: spot[2] + 0.5 };
  try { e = dim.spawnEntity(FISH_ID, at); } catch { return; }
  const props = { species: spec, kind: TANK_KIND[spec] ?? 0, seed: Math.floor(Math.random() * 8), turn: Math.floor(Math.random() * 4), tank: 1,
    scale: Math.min(100, Math.round(fit[0] * 1.3)), span: fit[1], level: Math.round((fit[2] + fit[3]) / 2), lane: 60 };
  for (const [k, v] of Object.entries(props)) { try { e.setProperty(`${NS}:${k}`, v); } catch {} }
  try { e.addTag(tagOf(pos)); e.setDynamicProperty("kfv:slot", slot); e.setDynamicProperty("kfv:id", f.id); e.setDynamicProperty("kfv:cls", f.cls ?? 0); } catch {}
}
/** Make the swimming fish match the roster; move one of them to another part of the pond. */
function syncFish(dim, pos, r, wander = true) {
  const have = fishEntities(dim, pos);
  const kept = new Set();
  for (const e of have) {
    let slot, id, cls;
    try { slot = e.getDynamicProperty("kfv:slot"); id = e.getDynamicProperty("kfv:id"); cls = e.getDynamicProperty("kfv:cls"); } catch {}
    const f = r?.fish?.[slot];
    if (!f || kept.has(slot) || f.id !== id || (f.cls ?? 0) !== cls) { try { e.remove(); } catch {} continue; }
    kept.add(slot);
  }
  (r?.fish ?? []).forEach((f, slot) => { if (!kept.has(slot)) spawnOne(dim, pos, r, slot); });
  if (wander && have.length && r?.spots?.length && Math.random() < 0.5) {
    const e = have[Math.floor(Math.random() * have.length)];
    const s = r.spots[Math.floor(Math.random() * r.spots.length)];
    try { if (e.isValid) e.teleport({ x: s[0] + 0.5, y: s[1] - 0.45, z: s[2] + 0.5 }); } catch {}
    try { e.setProperty(`${NS}:turn`, Math.floor(Math.random() * 4)); } catch {}
  }
}
function clearFish(dim, pos) { for (const e of fishEntities(dim, pos)) { try { e.remove(); } catch {} } }

// ------------------------------------------------------------------------------------------------ the feeder
function show(block, r) {
  const want = { [FEED]: meals(r) > 0 ? 1 : 0, [ROE]: r?.roe ? 1 : 0 };
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
function catchUp(block, r) {
  const d = today();
  if (typeof r.day !== "number" || r.day > d) { r.day = d; return false; }
  if (r.day === d) return false;
  recount(block, r);
  let steps = 0;
  while (r.day < d && steps < CATCH_UP) { r.day++; steps++; dawn(r, r.day); }
  r.day = d;
  return true;
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
const t = key => ({ translate: `${NS}.pond.${key}` });
const tw = (key, ...args) => ({ translate: `${NS}.pond.${key}`, with: { rawtext: args.map(a => (typeof a === "object" ? a : { text: String(a) })) } });
const nameOf = id => ({ translate: `${NS}.name.${canon(id).split(":")[1]}` });

async function showList(player, block) {
  const pos = { x: block.x, y: block.y, z: block.z }, dim = block.dimension;
  const r = read(dim, pos);
  const form = new ActionFormData().title(t("title"));
  if (!r?.cap) form.body(t("none"));
  else form.body({ rawtext: [tw("summary", t(isSea(r) ? "sea" : "fresh"), r.n, r.fish.length, r.cap, meals(r)), { text: "\n" }, t("pick")] });
  const rows = [];
  if (r?.roe) { form.button(tw("roe", nameOf(r.roe.id))); rows.push({ roe: r.roe.id }); }
  for (const [i, f] of (r?.fish ?? []).entries()) {
    form.button({ rawtext: [tw("fish_line", nameOf(f.id), { text: `${f.cls ? markOf(f.cls) : ""}${f.f ? ` ${FARMED_MARK}` : ""}§r` }, f.d ?? 0), ...(f.h ? [t("hungry")] : [])] });
    rows.push({ i, id: f.id });
  }
  form.button(t("close"));
  let res;
  try { res = await form.show(player); } catch { return; }
  if (!res || res.canceled || res.selection === undefined || res.selection >= rows.length) return;
  const pick = rows[res.selection];
  const now = read(dim, pos);                      // the pond may have changed while the list was open
  let b;
  try { b = dim.getBlock(pos); } catch { return; }
  if (!now || b?.typeId !== FEEDER) return;
  if (pick.roe) {
    if (now.roe?.id !== pick.roe) return;
    now.roe = undefined;
    give(player, roeStack(pick.roe), centreOf(pos));
  } else {
    const f = now.fish[pick.i];
    if (!f || f.id !== pick.id) return;
    const out = fishStack(f);
    if (!out) return refuseAt(player, "tank_pack_gone", { dimension: dim, location: centreOf(pos) });
    now.fish.splice(pick.i, 1);
    give(player, out, centreOf(pos));
  }
  save(dim, pos, now); show(b, now); syncFish(dim, pos, now, false);
  snd(dim, centreOf(pos), "random.splash", 1.3, 0.5);
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
    catchUp(block, r);
    const slot = player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
    const held = slot?.hasItem() ? slot.getItem() : undefined;
    if (!held) { recount(block, r); save(dim, block, r); show(block, r); syncFish(dim, block, r, false); showList(player, block); return; }
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
      return;
    }
    if (id === SALT) {
      if (isSea(r)) return refuseAt(player, "pond_salted", block);
      if (held.amount < SALT_NEEDED && !creative(player)) return refuseAt(player, "pond_salt", block, SALT_NEEDED);
      takeHeld(player, slot, SALT_NEEDED);
      r.salt = SALT_NEEDED;
      save(dim, block, r);
      snd(dim, centreOf(block), "dig.sand", 1.0, 0.6);
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
    if (catchUp(block, r)) save(block.dimension, block, r);
    show(block, r);
    syncFish(block.dimension, block, r);
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
