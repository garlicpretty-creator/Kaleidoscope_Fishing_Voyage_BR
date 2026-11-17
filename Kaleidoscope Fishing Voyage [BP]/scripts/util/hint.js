// ## Refusal feedback. A workstation action that does nothing tells the player why without text
// (1.4 immersion rule, 1.6.0 "no text" rule, docs/PLAN_1.6.0.md section 10).
//
// 1.6.0: every refusal reason belongs to one of four categories, each with its own sound (only the
// refused player hears it, player.playSound) and a small particle on the block (everyone near sees it):
//
//   missing  the held thing is wrong or something is missing   note.bass 0.7            grey smoke puff
//   notyet   it is working, wait                                random.click 0.6, twice  small white bubble
//   full     no room                                            random.splash (a block with water) or
//                                                               dig.wood (anything else) 1.4, bounced-off bits
//   place    the spot or surroundings are wrong                 dig.stone 0.5            red dust
//
// REASONS maps each key to its category. A key used anywhere in scripts/ must be listed here: the offline
// tests fail otherwise (tools/tests/test_scripts.mjs, "refusal keys"). An unknown key still sounds as
// "missing" and logs a warning.
// At most one refusal per player every HINT_GAP ticks, so holding the use button does not spam it.
// The `key` and `args` stay in every call so other feedback can come back later without touching the call sites.
import { system, world } from "@minecraft/server";
import { spawnParticle } from "./particles.js";

const HINT_GAP = 10;
const last = new Map();                   // player id -> tick of the last refusal

/** The four categories: what each sounds and looks like. Other packs of the family use the same set. */
export const CATEGORIES = {
  missing: { sound: "note.bass", pitch: 0.7, volume: 0.6, particle: "minecraft:basic_smoke_particle", count: 2 },
  notyet: { sound: "random.click", pitch: 0.6, volume: 0.5, twice: 3, particle: "minecraft:basic_bubble_particle", count: 1 },
  full: { sound: "dig.wood", wetSound: "random.splash", pitch: 1.4, volume: 0.6, particle: "minecraft:basic_crit_particle", count: 3, bounce: true },
  place: { sound: "dig.stone", pitch: 0.5, volume: 0.7, particle: "minecraft:redstone_wire_dust_particle", count: 4 },
};

// 1.6.0: the plan's table (section 10) lists 33 reasons; the rest are the other reasons the scripts use,
// sorted by the same meaning.
const BY_CATEGORY = {
  missing: [
    // plan table
    "board_need_fish", "board_need_knife", "board_finish_knife", "jar_need_fish", "jar_need_salt", "jar_wrong_fish",
    "jar_paste_fresh", "tank_not_fish", "tub_what", "pond_what", "rack_empty_hand", "rack_other_kind", "auger_no_water",
    "icehole_use",
    // also: the wrong thing in hand, or something is missing
    "board_cannot_clean", "jar_more_fish", "jar_more_shrimp", "jar_need_bottle", "jar_need_bowl", "rack_cannot_dry",
    "rack_empty", "rack_salt_empty", "rack_salt_fish_only", "trap_empty_hand", "trap_not_bait", "trap_need_bait",
    "tipup_empty_hand", "tub_need_water", "tub_need_salt", "salt_pan_need_water", "pond_cannot",
  ],
  notyet: [
    "jar_fermenting", "jar_salted", "rack_drying", "tub_busy", "tub_soaking", "tub_hatching", "trap_baited", "pond_salted",
    "rack_salted", "trap_waiting", "salt_pan_drying",
  ],
  full: [
    "rack_full", "tank_full", "tub_full", "tub_clams_full", "pond_feed_full", "tipup_limit", "pond_salt",
    "tank_occupied", "tipup_set", "pond_full",
  ],
  place: [
    "salt_pan_place", "pond_has_feeder", "board_pack_gone", "tank_pack_gone",
    "trap_underwater", "tank_wrong_kind", "tub_salted", "pond_none", "pond_fresh_fish", "pond_sea_fish",
  ],
};

/** Refusal key -> category name ("missing" | "notyet" | "full" | "place"). */
export const REASONS = Object.freeze(Object.fromEntries(
  Object.entries(BY_CATEGORY).flatMap(([cat, keys]) => keys.map(k => [k, cat]))));

// "full" sounds like water on these stations (a tank, a tub, a pond); dig.wood elsewhere.
const WET = /^(tank|tub|pond)_/;

/** The category of a refusal key (unknown keys count as "missing"). */
export const categoryOf = key => REASONS[key] ?? "missing";

/** Where a refusal shows: a Block, or { dimension, location } (the particle goes just above it). */
function spot(where) {
  if (!where) return undefined;
  try {
    const dim = where.dimension;
    if (!dim) return undefined;
    if (typeof where.x === "number") return { dim, at: { x: where.x + 0.5, y: where.y + 0.9, z: where.z + 0.5 } };   // a Block
    const l = where.location;
    return l && typeof l.x === "number" ? { dim, at: { x: l.x, y: l.y, z: l.z } } : undefined;
  } catch { return undefined; }
}

function show(c, where) {
  const s = spot(where);
  if (!s) return;
  for (let i = 0; i < c.count; i++) {
    const at = { x: s.at.x + (Math.random() - 0.5) * 0.4, y: s.at.y + Math.random() * 0.2, z: s.at.z + (Math.random() - 0.5) * 0.4 };
    spawnParticle(s.dim, c.particle, at, c.bounce ? { direction: { x: (Math.random() - 0.5) * 0.6, y: 0.6, z: (Math.random() - 0.5) * 0.6 } } : undefined);
  }
}

/**
 * Tell the player an action was refused, with the sound of its category and its particle at `where`
 * (a Block or { dimension, location }; undefined plays the sound only). 1.6.0.
 */
export function refuseAt(player, key, where, ...args) {   // eslint-disable-line no-unused-vars
  if (!player) return;
  const now = system.currentTick;
  const prev = last.get(player.id);
  if (prev !== undefined && now - prev < HINT_GAP) return;
  last.set(player.id, now);
  if (!(key in REASONS)) { try { console.warn(`[kaleidoscope_fishing] refusal "${key}" has no category`); } catch {} }
  const c = CATEGORIES[categoryOf(key)];
  const sound = c.wetSound && WET.test(key) ? c.wetSound : c.sound;
  const play = () => { try { player.playSound(sound, { pitch: c.pitch, volume: c.volume }); } catch {} };
  play();
  if (c.twice) { try { system.runTimeout(play, c.twice); } catch {} }
  show(c, where);
}

/** Tell the player an action was refused (sound only; refuseAt also shows the particle on the block). */
export function refuse(player, key, ...args) {
  refuseAt(player, key, undefined, ...args);
}

world.afterEvents.playerLeave.subscribe(ev => last.delete(ev.playerId));
