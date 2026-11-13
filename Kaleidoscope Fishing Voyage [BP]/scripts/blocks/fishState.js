// ## Fish index on blocks (tank, cleaning board, fish print).
// A block state may hold at most 16 values, so the fish index (0 = empty, 1..N) is split over
// two states: fish = index % 16 and fish_bank = index / 16. Approach from the v1.0.3 review.
const FISH = "kaleidoscope_fishing:fish";
const BANK = "kaleidoscope_fishing:fish_bank";
const LIMIT = 16;

export function readFishIndex(permutation) {
  return Number(permutation.getState(FISH) ?? 0) + LIMIT * Number(permutation.getState(BANK) ?? 0);
}

export function withFishIndex(permutation, index) {
  if (!Number.isInteger(index) || index < 0 || index >= LIMIT * LIMIT) throw new RangeError(`Invalid fish index ${index}`);
  const p = permutation.withState(FISH, index % LIMIT);
  return index >= LIMIT || permutation.getState(BANK) !== undefined ? p.withState(BANK, Math.floor(index / LIMIT)) : p;
}
