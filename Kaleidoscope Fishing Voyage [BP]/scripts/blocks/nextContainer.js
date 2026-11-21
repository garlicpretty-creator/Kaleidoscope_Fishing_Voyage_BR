// ## A container right next to a station (1.7.0, phase 1). The shrimp trap empties into a chest or barrel beside
// or below it, the drying rack drops its dried goods into one below it. Only the station's own block ticks look,
// and only at the few blocks touching it: no world scans.
const SIDES = {
  below: b => b.below(), north: b => b.north(), south: b => b.south(), east: b => b.east(), west: b => b.west(),
};

/** The first container (anything with an inventory) touching `block` on one of `sides` (names of SIDES), or undefined. */
export function containerNext(block, sides = ["below"]) {
  for (const s of sides) {
    try {
      const c = SIDES[s]?.(block)?.getComponent("minecraft:inventory")?.container;
      if (c && (c.size ?? 0) > 0) return c;
    } catch {}                                          // unloaded neighbour: nothing there for now
  }
  return undefined;
}

/** Put one stack in; true only if all of it went in (a stack that does not fit whole stays out). */
export function putWhole(container, stack) {
  try {
    if (!canTake(container, stack)) return false;
    return !container.addItem(stack);
  } catch { return false; }
}

/** Room for all of `stack`: an empty slot, or stacks of the same item with space left. */
function canTake(container, stack) {
  if ((container.emptySlotsCount ?? 0) > 0) return true;
  let room = 0;
  for (let i = 0; i < container.size; i++) {
    const it = container.getItem(i);
    if (it && it.isStackableWith?.(stack)) room += it.maxAmount - it.amount;
    if (room >= stack.amount) return true;
  }
  return false;
}
