// ## Fishing: read the water the bobber landed in.
// Biome comes from Dimension.getBiome when the running engine has it. When it does not,
// the water type is inferred from depth, sea level and nearby blocks, so the add-on still
// works on builds without the biome API.
import { world } from "@minecraft/server";

const SEA_LEVEL = 63;
const MAX_DEPTH_SCAN = 24;

export function isWater(block) {
  if (!block) return false;
  const id = block.typeId;
  if (id === "minecraft:water" || id === "minecraft:flowing_water") return true;
  try { return block.isWaterlogged === true; } catch { return false; }
}

function biomeId(dim, loc) {
  try {
    if (typeof dim.getBiome !== "function") return "";
    const b = dim.getBiome(loc);
    return String(b?.id ?? b?.typeId ?? "").replace(/^minecraft:/, "");
  } catch { return ""; }
}

/** Return the top water block's Y above `block` (scans up to 12 blocks). */
export function waterSurfaceY(dim, x, y, z) {
  let top = y;
  for (let i = 0; i < 12; i++) {
    const above = dim.getBlock({ x, y: top + 1, z });
    if (!isWater(above)) break;
    top++;
  }
  return top;
}

function waterDepth(dim, x, surfaceY, z) {
  let d = 0;
  for (let y = surfaceY; d < MAX_DEPTH_SCAN; y--, d++) {
    const b = dim.getBlock({ x, y, z });
    if (!isWater(b)) break;
  }
  return d;
}

function nearby(dim, x, y, z, ids, r = 3) {
  for (let dx = -r; dx <= r; dx += r)
    for (let dz = -r; dz <= r; dz += r)
      for (let dy = -1; dy <= 1; dy++) {
        try { if (ids.has(dim.getBlock({ x: x + dx, y: y + dy, z: z + dz })?.typeId)) return true; } catch {}
      }
  return false;
}

const SWAMPY = new Set(["minecraft:waterlily", "minecraft:mangrove_roots", "minecraft:muddy_mangrove_roots", "minecraft:mangrove_propagule", "minecraft:mud"]);
// v1.4: three more waters. mangrove (with swamp), estuary (with river: a river that reaches the sea),
// cave (alone: underground water with no sky over it, below CAVE_Y; "lush" added among moss and glow berries).
const MANGROVE = new Set(["minecraft:mangrove_roots", "minecraft:muddy_mangrove_roots", "minecraft:mangrove_propagule", "minecraft:mud", "minecraft:mangrove_log"]);
const LUSH = new Set(["minecraft:moss_block", "minecraft:moss_carpet", "minecraft:cave_vines", "minecraft:cave_vines_body_with_berries", "minecraft:cave_vines_head_with_berries", "minecraft:azalea", "minecraft:flowering_azalea", "minecraft:spore_blossom", "minecraft:big_dripleaf", "minecraft:small_dripleaf", "minecraft:clay"]);
const CAVE_Y = 48;
const ESTUARY_REACH = 16;

/** Open sky straight above (x, y, z)? One upward ray at cast time; a loop when the ray API is missing. */
function skyAbove(dim, x, y, z) {
  try {
    const hit = dim.getBlockFromRay({ x: x + 0.5, y: y + 1, z: z + 0.5 }, { x: 0, y: 1, z: 0 },
      { maxDistance: 320 - y, includeLiquidBlocks: false, includePassableBlocks: false });
    return !hit;
  } catch {}
  for (let yy = y + 1; yy <= y + 64; yy++) {
    try { const b = dim.getBlock({ x, y: yy, z }); if (!b) return true; if (!b.isAir && !b.isLiquid) return false; } catch { return true; }
  }
  return true;
}

/** A river biome with an ocean biome within ESTUARY_REACH blocks in any of the four directions. */
function nearOcean(dim, x, y, z) {
  for (const [dx, dz] of [[ESTUARY_REACH, 0], [-ESTUARY_REACH, 0], [0, ESTUARY_REACH], [0, -ESTUARY_REACH]]) {
    if (biomeId(dim, { x: x + dx, y, z: z + dz }).includes("ocean")) return true;
  }
  return false;
}
const SANDY = new Set(["minecraft:sand", "minecraft:sandstone", "minecraft:gravel"]);
const COLD = new Set(["minecraft:ice", "minecraft:packed_ice", "minecraft:snow_layer", "minecraft:snow", "minecraft:blue_ice"]);
export const ICE_HOLE = "kaleidoscope_fishing:ice_hole";
const ICE = new Set(["minecraft:ice", "minecraft:packed_ice", "minecraft:blue_ice", ICE_HOLE]);

/** Water closed in by ice (v1.2): under an Ice Hole, or a gap in a frozen lake or sea. */
function underIce(dim, x, surface, z) {
  try { if (dim.getBlock({ x, y: surface + 1, z })?.typeId === ICE_HOLE) return true; } catch {}
  let n = 0;
  for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    try { if (ICE.has(dim.getBlock({ x: x + dx, y: surface, z: z + dz })?.typeId)) n++; } catch {}
  }
  return n >= 2;
}

/**
 * Classify water at the bobber.
 * @returns {{waters:Set<string>, depth:number, cold:boolean, biome:string}}
 * waters: river | lake | swamp | beach | ocean | warm_ocean | cold_ocean | deep_ocean
 */
export function analyzeWater(dim, loc) {
  const x = Math.floor(loc.x), z = Math.floor(loc.z);
  let y = Math.floor(loc.y);
  if (!isWater(dim.getBlock({ x, y, z }))) y -= 1;
  const surface = waterSurfaceY(dim, x, y, z);
  const depth = waterDepth(dim, x, surface, z);
  const biome = biomeId(dim, { x, y: surface, z });
  const waters = new Set();
  let cold = false;

  if (biome) {
    // "grove" alone is the snowy mountain grove; mangrove_swamp and cherry_grove are not cold
    cold = /frozen|cold|snowy|taiga|ice/.test(biome) || biome === "grove";
    if (biome.includes("ocean")) {
      if (biome.includes("deep")) waters.add("deep_ocean");
      if (biome.includes("warm") && !biome.includes("lukewarm")) waters.add("warm_ocean");
      else if (biome.includes("lukewarm")) { waters.add("ocean"); waters.add("warm_ocean"); }
      else if (cold) waters.add("cold_ocean");
      else waters.add("ocean");
    } else if (biome.includes("river")) { waters.add("river"); if (nearOcean(dim, x, surface, z)) waters.add("estuary"); }
    else if (biome.includes("swamp") || biome.includes("mangrove")) { waters.add("swamp"); if (biome.includes("mangrove")) waters.add("mangrove"); }
    else if (biome.includes("beach") || biome.includes("stony_shore")) { waters.add("beach"); waters.add("ocean"); }
    else waters.add("lake");
  } else {
    // Fallback inference without the biome API.
    cold = nearby(dim, x, surface, z, COLD, 4);
    const nearSea = surface >= SEA_LEVEL - 2 && surface <= SEA_LEVEL;
    if (nearSea && depth >= 12) { waters.add("deep_ocean"); waters.add(cold ? "cold_ocean" : "ocean"); }
    else if (nearSea && depth >= 5) waters.add(cold ? "cold_ocean" : "ocean");
    else if (nearby(dim, x, surface, z, SWAMPY, 3)) { waters.add("swamp"); if (nearby(dim, x, surface, z, MANGROVE, 3)) waters.add("mangrove"); }
    else if (nearSea && depth <= 3 && nearby(dim, x, surface, z, SANDY, 2)) { waters.add("beach"); waters.add("ocean"); }
    else waters.add(depth >= 3 ? "river" : "lake");
    // no estuary here: without biomes a river mouth at sea level reads as ocean, which is what it offers anyway
  }
  // v1.4: cave water is its own world (only cave catches), checked before ice so a frozen cave pool is still a cave.
  if (dim.id === "minecraft:overworld" && surface < CAVE_Y && !skyAbove(dim, x, surface, z)) {
    const cave = new Set(["cave"]);
    if (nearby(dim, x, surface, z, LUSH, 3)) cave.add("lush");
    return { waters: cave, depth, cold: false, biome, surface };
  }
  if (underIce(dim, x, surface, z)) return { waters: new Set(["ice"]), depth, cold: true, biome, surface };
  // v1.3: any water in the End is an End pond, with its own catches (the void stays the Ender rod's).
  if (dim.id === "minecraft:the_end") return { waters: new Set(["end_pond"]), depth, cold: false, biome: "the_end", surface };
  return { waters, depth, cold, biome, surface };
}

// v1.3: moon and tide. world.getMoonPhase(): 0 = full moon ... 4 = new moon.
export function moonPhase() {
  try { return Number(world.getMoonPhase()); } catch { return 4; }
}

/** "high" or "low". The sea is high twice a day, around dawn and dusk (1500 ticks each side);
 *  like a real tide it comes later every day, 750 ticks per moon phase. Nothing moves: the
 *  tide only changes what bites and what the sand gives up. */
export function tideState() {
  const t = world.getTimeOfDay?.() ?? 6000;
  const shift = moonPhase() * 750;
  const near = centre => {
    const d = (((t - centre - shift) % 24000) + 24000) % 24000;
    return Math.min(d, 24000 - d) <= 1500;
  };
  return near(0) || near(12000) ? "high" : "low";
}

export function timeSlot() {
  const t = world.getTimeOfDay?.() ?? 6000; // 0 = sunrise, 6000 = noon, 12000 = sunset
  if (t >= 23000 || t < 1500) return "dawn";
  if (t >= 11000 && t < 13500) return "dusk";
  if (t >= 13500 && t < 23000) return "night";
  return "day";
}

// Weather (v1.2.0): the server's script API has no Dimension.getWeather, so the weather is
// followed through world.afterEvents.weatherChange and kept in a world property (it survives
// a restart). Until the first change after installing, the sky counts as clear.
const WEATHER_KEY = "kaleidoscope_fishing:weather";
// The event names a dimension "overworld", Dimension.id says "minecraft:overworld" (v1.2.0):
// both sides go through this before they touch the cache.
const dimKey = id => String(id ?? "").replace(/^minecraft:/, "");
let weatherNow;
function weatherState() {
  if (!weatherNow) {
    weatherNow = {};
    try {
      for (const [k, v] of Object.entries(JSON.parse(world.getDynamicProperty(WEATHER_KEY) ?? "{}"))) weatherNow[dimKey(k)] = v;
    } catch {}
  }
  return weatherNow;
}
try {
  world.afterEvents.weatherChange.subscribe(ev => {
    const st = weatherState();
    st[dimKey(ev.dimension)] = String(ev.newWeather);
    try { world.setDynamicProperty(WEATHER_KEY, JSON.stringify(st)); } catch {}
  });
} catch {}

/** "Clear", "Rain" or "Thunder" for a dimension. */
export function weatherOf(dim) {
  try { const w = dim.getWeather?.(); if (w !== undefined && w !== null) return String(w); } catch {}
  return weatherState()[dimKey(dim?.id)] ?? "Clear";
}

export function isRaining(dim) {
  return /rain|thunder/i.test(weatherOf(dim));
}
