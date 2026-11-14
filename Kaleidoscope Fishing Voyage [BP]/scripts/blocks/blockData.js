// ## Block data kept outside block states (v1.5.5, B019).
// A few blocks used block states only to remember data that nothing draws: the Fish Cleaning Board's size
// class, the Fish Tank's fish and size class, the Fish Sauce Jar's servings left and salt. Every state value
// multiplies the block's client permutations (the server is far past the engine's advised 65,536), so the data
// moves to one world property per block. v1.5.5 writes both and reads the property first, falling back to the
// old states; the tank and the jar copy old states over on their next block tick, the board on its next use.
// v1.5.6 then drops those states.
import { world } from "@minecraft/server";

const NS = "kaleidoscope_fishing";
/** Kinds: "cb" cleaning board { size }, "tk" fish tank { idx, cls }, "sj" sauce jar { left, salted }. */
export const dataKey = (kind, dim, p) => `${NS}:bd:${kind}:${dim.id}:${p.x},${p.y},${p.z}`;

const cache = new Map();          // key -> object | undefined; tank and jar ticks read it every 5-10 s
const MAX = 4096;
const remember = (k, v) => { if (cache.size >= MAX) cache.clear(); cache.set(k, v); };

export function readData(kind, dim, p) {
  const k = dataKey(kind, dim, p);
  if (cache.has(k)) return cache.get(k);
  let v;
  try { const s = world.getDynamicProperty(k); if (typeof s === "string") v = JSON.parse(s); } catch {}
  v = v && typeof v === "object" ? v : undefined;
  remember(k, v);
  return v;
}

/** Store (or, with undefined, forget) a block's data. */
export function writeData(kind, dim, p, v) {
  const k = dataKey(kind, dim, p);
  try { world.setDynamicProperty(k, v ? JSON.stringify(v) : undefined); } catch {}
  remember(k, v || undefined);
}
