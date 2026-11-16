// ## Workstation contents survive any removal (v1.6.3, F1).
// Until 1.6.2 only a player breaking a workstation gave its contents back; an explosion, a piston (the
// stations are "popped") or a command simply lost them. Now:
//   player break   each station's onPlayerBreak calls its own drop (survival only, as before)
//   explosion      world.afterEvents.blockExplode hands over the block as it was -> the same drop
//   anything else  every station with contents keeps a world record under its position; a sweep every
//                  SWEEP ticks (and a few ticks after any piston moves) finds records whose block is loaded
//                  but is no longer that station, drops what the record says at that spot and forgets it.
// A drop always forgets the station's records first, so no path can give the contents twice.
import { system, world } from "@minecraft/server";

const SWEEP = 100;
const byBlock = new Map();     // block id -> drop(dim, pos, permutation | undefined)
const records = [];            // { prefix, blocks:Set, drop(dim, pos, key) }

/** drop(dim, pos, perm) spawns the station's contents at pos and forgets its records; perm undefined = records only. */
export function registerStation(blockId, drop) { byBlock.set(blockId, drop); }

/** World properties starting with prefix name a position (rest of the key: "<dim id>:x:y:z" or "<dim id>:x,y,z"). */
export function registerRecords(prefix, blockIds, drop) {
  records.push({ prefix, blocks: new Set([].concat(blockIds)), drop });
}

/** "<dim id>:x:y:z" or "<dim id>:x,y,z" -> { dimId, x, y, z } */
export function parsePos(rest) {
  const m = /^(.+?):(-?\d+)[:,](-?\d+)[:,](-?\d+)$/.exec(rest);
  return m ? { dimId: m[1], x: Number(m[2]), y: Number(m[3]), z: Number(m[4]) } : undefined;
}

export function spawnAll(dim, pos, stacks) {
  const at = { x: pos.x + 0.5, y: pos.y + 0.5, z: pos.z + 0.5 };
  for (const s of stacks) { if (s) { try { dim.spawnItem(s, at); } catch {} } }
}

export function sweep() {
  if (!records.length) return;
  let ids = [];
  try { ids = world.getDynamicPropertyIds(); } catch { return; }
  for (const k of ids) {
    const r = records.find(r => k.startsWith(r.prefix));
    if (!r) continue;
    const pos = parsePos(k.slice(r.prefix.length));
    if (!pos) continue;
    let dim, block;
    try { dim = world.getDimension(pos.dimId); block = dim.getBlock(pos); } catch { continue; }   // not loaded: later
    if (!block || r.blocks.has(block.typeId)) continue;
    try { r.drop(dim, pos, k); } catch (e) { console.warn(`[Fishing Voyage] station sweep ${k}: ${e}`); }
  }
}

if (!world.afterEvents.blockExplode) console.warn("[Fishing Voyage] blockExplode event missing: exploded stations are left to the sweep");
world.afterEvents.blockExplode?.subscribe(ev => {
  const perm = ev.explodedBlockPermutation;
  const drop = perm && byBlock.get(perm.type.id);
  if (!drop) return;
  const b = ev.block;
  try { drop(ev.dimension, { x: b.x, y: b.y, z: b.z }, perm); } catch (e) { console.warn(`[Fishing Voyage] station explode: ${e}`); }
});

let soon = false;
world.afterEvents.pistonActivate?.subscribe(() => {
  if (soon) return;
  soon = true;
  system.runTimeout(() => { soon = false; try { sweep(); } catch {} }, 4);
});

system.runInterval(() => { try { sweep(); } catch {} }, SWEEP);
