// ## Sky events (天象漁況, 1.5.0): some nights are special.
// Once each dusk the world rolls one sky for the night, the same for every player:
//   meteor  meteor shower, 10%: starfins come up into the open sea, the Meteor Marlin bites, bubbling beach sand
//           may give star sand. Cancelled (clouds) when it is raining at dusk; a cancelled night does not count
//           towards the pity count, and the next dusk rolls again.
//   aurora  aurora night, 12.5%: only seen, and only felt, in a cold biome (ice fishing bites 30% sooner, the
//           Aurora Icefish, the Frostlake Char without the new moon).
// Pity: after 10 quiet nights in a row the next dusk always brings one (a meteor shower unless it is raining).
// The roll and the count live in one world property, so a restart neither re-rolls the night nor forgets it.
// The night lasts until dawn (the day number changes at sunrise, so "tonight" is the roll of today's dusk).
// The sky is drawn with particles, only for players on the surface under the open sky, and the aurora only for
// players standing in a cold biome. Other packs hear "sky" on kaleidoscope_fishing:evt (start at dusk, end at
// dawn), in the same shape as A Witch Way's sky events.
import { system, world } from "@minecraft/server";
import { isRaining, timeSlot } from "../fishing/water.js";
import { spawnParticle } from "../util/particles.js";
import { canonBiome } from "../util/biome.js";
import { emit } from "../api/host.js";

const NS = "kaleidoscope_fishing";
const KEY = `${NS}:sky`;
const OVERWORLD = "minecraft:overworld";
export const SKY_CHANCE = { meteor: 0.10, aurora: 0.125 };
export const PITY = 10;
export const SKIES = ["meteor", "aurora"];
export const AURORA_BITE = 0.7;                       // ice fishing bites 30% sooner under the aurora
const COLD_BIOME = /frozen|cold|snowy|taiga|grove|ice|peaks|jagged/;

let state;                                            // { day, sky, quiet, ended? }
function load() {
  if (state) return state;
  state = { day: -1, sky: "", quiet: 0 };
  try {
    const s = JSON.parse(String(world.getDynamicProperty(KEY) ?? "{}"));
    if (s && typeof s === "object") state = { day: Number(s.day) || -1, sky: SKIES.includes(s.sky) ? s.sky : "", quiet: Number(s.quiet) || 0, ended: !!s.ended };
  } catch {}
  return state;
}
function save() { try { world.setDynamicProperty(KEY, JSON.stringify(state)); } catch {} }
const today = () => { try { return world.getDay(); } catch { return 0; } };
const night = () => { const s = timeSlot(); return s === "dusk" || s === "night"; };

/** One dusk's roll. `quiet` is the count of quiet nights before it. Exported for tests. */
export function rollSky(quiet, raining, rand = Math.random) {
  let sky = "";
  if (quiet >= PITY) sky = raining ? "aurora" : "meteor";
  else {
    const r = rand();
    sky = r < SKY_CHANCE.meteor ? "meteor" : r < SKY_CHANCE.meteor + SKY_CHANCE.aurora ? "aurora" : "";
  }
  if (sky === "meteor" && raining) return { sky: "", quiet, cancelled: true };   // behind the clouds: not counted
  return { sky, quiet: sky ? 0 : quiet + 1 };
}

/** The world's sky tonight ("meteor", "aurora" or ""), from dusk until dawn. */
export function skyTonight() {
  const s = load();
  return s.day === today() && night() ? s.sky : "";
}
/** The sky as felt at one place: the aurora only counts in the cold. */
export function skyAt(cold) {
  const s = skyTonight();
  return s === "aurora" && !cold ? "" : s;
}

const dimKey = dim => String(dim?.id ?? OVERWORLD);
/** Look once: roll at dusk, broadcast the start and, at dawn, the end. Exported for tests. */
export function watchSky(rand = Math.random) {
  const s = load();
  const day = today();
  if (s.sky && !s.ended && (s.day !== day || !night())) {       // dawn (or a day skipped by sleeping)
    emit("sky", undefined, { kind: s.sky, phase: "end", dim: OVERWORLD });
    s.ended = true; save();
  }
  if (!night() || s.day === day) return;
  let raining = false;
  try { raining = isRaining(world.getDimension(OVERWORLD)); } catch {}
  const r = rollSky(s.quiet, raining, rand);
  state = { day, sky: r.sky, quiet: r.quiet, ended: false };
  save();
  if (r.sky) emit("sky", undefined, { kind: r.sky, phase: "start", dim: OVERWORLD });
}

// ------------------------------------------------------------------------------------------------ the sky drawn
const METEOR = `${NS}:meteor`, AURORA = `${NS}:aurora`;
function underSky(player) {
  try {
    if (player.dimension.id !== OVERWORLD) return false;
    const l = player.location;
    const top = player.dimension.getTopmostBlock({ x: Math.floor(l.x), z: Math.floor(l.z) });
    return !top || top.y <= l.y + 1;
  } catch { return false; }
}
function coldAt(player) {
  try { return COLD_BIOME.test(canonBiome(player.dimension.getBiome(player.location)?.id)); } catch { return false; }
}
/** Draw tonight's sky for the players who can see it. Exported for tests. */
export function drawSky(rand = Math.random) {
  const sky = skyTonight();
  if (!sky || timeSlot() !== "night") return 0;
  let drawn = 0;
  for (const p of world.getAllPlayers()) {
    if (!underSky(p) || (sky === "aurora" && !coldAt(p))) continue;
    const l = p.location;
    const a = rand() * Math.PI * 2, d = 15 + rand() * 25;
    const at = { x: l.x + Math.cos(a) * d, y: Math.min(318, l.y + 35 + rand() * 20), z: l.z + Math.sin(a) * d };
    try { spawnParticle(p.dimension, sky === "meteor" ? METEOR : AURORA, at); drawn++; } catch {}
  }
  return drawn;
}

/** For tests: forget the cached state (as a restart would). */
export function _resetSkyForTests() { state = undefined; }

system.runInterval(() => { try { watchSky(); } catch {} }, 100);
system.runInterval(() => { try { drawSky(); } catch {} }, 30);
