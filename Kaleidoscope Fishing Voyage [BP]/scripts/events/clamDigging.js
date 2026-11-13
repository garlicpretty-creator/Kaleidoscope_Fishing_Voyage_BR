// ## Clams: digging Sand with a shovel on a beach or beside water can turn up a clam.
// v1.3 (趕海): bubbling spots. On a beach, a few patches of wet sand near each player bubble for
// two minutes; digging one with a shovel always gives something. Low tide brings twice as many.
// Spots live only in memory (no blocks placed, nothing saved), like the fish schools.
// v1.3.3: a spot belongs to its dimension; sand dug at the same x, y, z elsewhere is not it.
import { ItemStack, system, world } from "@minecraft/server";
import { isRaining, isWater, tideState } from "../fishing/water.js";
import { spawnParticle } from "../util/particles.js";

const NS = "kaleidoscope_fishing";
const CLAM = `${NS}:clam`;
const CHANCE = 0.12;

const SPOT_LIFE = 2400;          // ticks (2 minutes)
const PER_PLAYER = 3;            // spots within RANGE of a player (x2 at low tide)
const RANGE = 16;
const BUBBLE = `${NS}:dig_bubble`;
const DIG_TABLE = [
  [CLAM, 50], [`${NS}:oyster`, 20], [`${NS}:crab`, 15], [`${NS}:shrimp`, 10], ["minecraft:nautilus_shell", 5],
];

/** key "dimension|x,y,z" -> { dim, x, y, z, ends } (spots appear in the Overworld only) */
const spots = new Map();
const OVERWORLD = "minecraft:overworld";
const keyOf = (dimId, l) => `${dimId}|${l.x},${l.y},${l.z}`;

function biomeIsBeach(dim, loc) {
  try {
    if (typeof dim.getBiome === "function") return String(dim.getBiome(loc)?.id ?? "").includes("beach");
  } catch {}
  return false;
}

function onBeach(dim, loc) {
  if (biomeIsBeach(dim, loc)) return true;
  for (let dx = -2; dx <= 2; dx++)
    for (let dz = -2; dz <= 2; dz++)
      for (let dy = -1; dy <= 1; dy++) {
        if (!dx && !dz && !dy) continue;
        try { if (isWater(dim.getBlock({ x: loc.x + dx, y: loc.y + dy, z: loc.z + dz }))) return true; } catch {}
      }
  return false;
}

function pick(table) {
  let total = 0;
  for (const [, w] of table) total += w;
  let r = Math.random() * total;
  for (const [id, w] of table) { r -= w; if (r <= 0) return id; }
  return table[0][0];
}

// Wet sand: sand with air above and water right beside it.
function wetSand(dim, x, y, z) {
  let b;
  try { b = dim.getBlock({ x, y, z }); } catch { return false; }
  if (b?.typeId !== "minecraft:sand") return false;
  try { if (!dim.getBlock({ x, y: y + 1, z })?.isAir) return false; } catch { return false; }
  for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    try { if (isWater(dim.getBlock({ x: x + dx, y, z: z + dz }))) return true; } catch {}
  }
  return false;
}

function trySpot(player) {
  const dim = player.dimension, p = player.location;
  for (let i = 0; i < 10; i++) {
    const x = Math.floor(p.x + (Math.random() * 2 - 1) * RANGE), z = Math.floor(p.z + (Math.random() * 2 - 1) * RANGE);
    for (let y = Math.floor(p.y) + 3; y >= Math.floor(p.y) - 4; y--) {
      if (!wetSand(dim, x, y, z)) continue;
      const loc = { x, y, z }, k = keyOf(dim.id, loc);
      if (spots.has(k)) break;
      spots.set(k, { dim: dim.id, ...loc, ends: system.currentTick + SPOT_LIFE });
      return;
    }
  }
}

function nearCount(dimId, p) {
  let n = 0;
  for (const s of spots.values()) if (s.dim === dimId && (s.x - p.x) ** 2 + (s.z - p.z) ** 2 <= RANGE * RANGE) n++;
  return n;
}

let t = 0;
system.runInterval(() => {
  try {
    t += 20;
    const now = system.currentTick;
    const all = world.getAllPlayers();
    for (const [k, s] of spots) {
      const seen = all.some(p => p.dimension.id === s.dim && (s.x - p.location.x) ** 2 + (s.z - p.location.z) ** 2 < 48 * 48);
      if (now > s.ends || !seen) { spots.delete(k); continue; }
      try { spawnParticle(world.getDimension(s.dim), BUBBLE, { x: s.x + 0.5, y: s.y + 1.02, z: s.z + 0.5 }); } catch {}
    }
    if (t % 100 !== 0) return;                       // look for new spots every 5 s
    const cap = PER_PLAYER * (tideState() === "low" ? 2 : 1);
    for (const p of all) {
      if (p.dimension.id !== OVERWORLD || nearCount(OVERWORLD, p.location) >= cap) continue;
      const at = { x: Math.floor(p.location.x), y: Math.floor(p.location.y), z: Math.floor(p.location.z) };
      if (!biomeIsBeach(p.dimension, at)) continue;
      trySpot(p);
    }
  } catch (err) { console.warn(`[Fishing Voyage] dig spots: ${err}`); }
}, 20);

// v1.4: earthworms. Grass or dirt dug with a shovel in the rain sometimes turns one up.
const WORM = `${NS}:earthworm`, WORM_CHANCE = 0.15;
const WORM_BLOCKS = new Set(["minecraft:grass_block", "minecraft:dirt", "minecraft:podzol", "minecraft:mud", "minecraft:moss_block"]);
world.afterEvents.playerBreakBlock.subscribe(ev => {
  const id = ev.brokenBlockPermutation?.type?.id;
  if (!WORM_BLOCKS.has(id) || !(ev.itemStackBeforeBreak?.typeId ?? "").endsWith("_shovel")) return;
  if (!isRaining(ev.dimension) || Math.random() >= WORM_CHANCE) return;
  const l = ev.block.location, at = { x: l.x + 0.5, y: l.y + 0.5, z: l.z + 0.5 };
  try { ev.dimension.spawnItem(new ItemStack(WORM, 1), at); ev.dimension.playSound("dig.grass", at, { pitch: 1.5, volume: 0.4 }); } catch {}
});

world.afterEvents.playerBreakBlock.subscribe(ev => {
  if (ev.brokenBlockPermutation?.type?.id !== "minecraft:sand") return;
  const tool = ev.itemStackBeforeBreak?.typeId ?? "";
  if (!tool.endsWith("_shovel")) return;
  const loc = ev.block.location;
  const at = { x: loc.x + 0.5, y: loc.y + 0.5, z: loc.z + 0.5 };
  const k = keyOf(ev.dimension.id, loc);
  if (spots.has(k)) {
    spots.delete(k);
    try { ev.dimension.spawnItem(new ItemStack(pick(DIG_TABLE), 1), at); } catch {}
    try { ev.dimension.playSound("random.splash", at, { pitch: 1.6, volume: 0.4 }); } catch {}
    return;
  }
  if (Math.random() >= CHANCE) return;
  if (!onBeach(ev.dimension, loc)) return;
  try { ev.dimension.spawnItem(new ItemStack(CLAM, 1), at); } catch {}
});

export const _spotsForTests = spots;
