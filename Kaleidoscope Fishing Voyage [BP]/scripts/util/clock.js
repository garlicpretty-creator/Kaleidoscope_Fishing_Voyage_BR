// ## World clock for stations (v1.6.4, F3). Waiting is measured in world time (absolute ticks), so a station
// that was unloaded catches up when it loads again, and the server's randomtickspeed no longer matters.
import { system, world } from "@minecraft/server";

export const now = () => { try { return world.getAbsoluteTime(); } catch { return system.currentTick; } };

/** How many whole steps of `step` ticks fit between t and n (at most cap), and the clock moved past them.
 *  t undefined or in the future (the time was set back): no steps, the clock starts again at n. */
export function steps(t, n, step, cap) {
  if (typeof t !== "number" || n < t) return { k: 0, t: n };
  const all = Math.floor((n - t) / step);
  return { k: Math.min(all, cap), t: t + all * step };
}
