// ## Angler records: per-player species log (count + largest size), kept on the player.
const KEY = "kaleidoscope_fishing:journal";

export function getRecords(player) {
  try {
    const raw = player.getDynamicProperty(KEY);
    const data = typeof raw === "string" ? JSON.parse(raw) : {};
    return data && typeof data === "object" ? data : {};
  } catch { return {}; }
}

/** Log one landed catch. Returns { first, newBest } for the visual celebration. */
export function recordCatch(player, id, size) {
  const data = getRecords(player);
  const prev = data[id];
  const entry = prev ? { ...prev } : { n: 0 };
  entry.n = (entry.n ?? 0) + 1;
  let newBest = false;
  if (size !== undefined && (entry.b === undefined || size > entry.b)) {
    newBest = entry.b !== undefined; // the first ever catch is not a "record"
    entry.b = size;
  }
  data[id] = entry;
  try { player.setDynamicProperty(KEY, JSON.stringify(data)); } catch {}
  return { first: !prev, newBest };
}
