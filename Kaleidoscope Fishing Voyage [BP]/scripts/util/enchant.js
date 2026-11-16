// ## Enchantments our own code has to honour (1.5.0).
// The game applies a sword's or a rod's enchantments only where the game itself does the work: damage, knockback,
// fire, mob loot. Whatever a script does with the item (a cut on the Fish Cleaning Board, the squid a knife kill
// adds, the whole of rod fishing) sees no enchantment unless it asks. These are the questions.
/** The level of an enchantment on a stack, 0 when it has none (or the stack cannot be enchanted). */
export function enchantLevel(stack, id) {
  try { return Number(stack?.getComponent("minecraft:enchantable")?.getEnchantment(id)?.level) || 0; } catch { return 0; }
}
/** Unbreaking, as the game does it for tools: a use costs a durability point with chance 1 / (level + 1). */
export const wears = (level, rand = Math.random) => !(level > 0) || rand() < 1 / (level + 1);

// --- fishing rods -------------------------------------------------------------------------------------------
/** Lure: the wait for a bite, 15 % shorter per level (the game's own rod loses 5 s of 5-30 s per level). */
export const LURE_FACTOR = [1, 0.85, 0.7, 0.55];
const LURE_FLOOR = 40;                      // Lure alone never takes a wait under 2 s
/** The ticks to wait given what bait, weather and tackle already made of it. Never longer than without Lure. */
export function lureTicks(ticks, level) {
  const f = LURE_FACTOR[Math.max(0, Math.min(3, level | 0))];
  return f === 1 ? ticks : Math.max(Math.min(ticks, LURE_FLOOR), Math.round(ticks * f));
}
/** Luck of the Sea: the less common fish, 15 % likelier per level. Legends are left to their own conditions. */
export const luckFactor = level => 1 + 0.15 * Math.max(0, Math.min(3, level | 0));
/** Luck of the Sea and size: with chance 10 % per level the size is rolled twice and the larger one kept. */
export function luckSize(level, roll, rand = Math.random) {
  const first = roll();
  if (first === undefined || !(level > 0) || rand() >= 0.1 * Math.min(3, level)) return first;
  const second = roll();
  return second !== undefined && second > first ? second : first;
}
