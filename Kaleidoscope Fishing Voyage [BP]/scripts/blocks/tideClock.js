// ## Tide Clock on a wall (1.5.0). The clock in the hand is drawn by the resource pack alone (Molang on the
// time of day). A block has no such Molang, so the wall clock's hand is one of 16 bones, a block state says
// which, and this script sets it: on placing, and every 5 s after. The moon strips follow a second state.
// The dial reads as the held one does: the hand points at the blue arc at the top while the tide is high
// (fishing/water.js tideState), and goes round clockwise once a tide.
import { system, world } from "@minecraft/server";
import { moonPhase } from "../fishing/water.js";

const NS = "kaleidoscope_fishing";
const HAND = `${NS}:hand`, MOON = `${NS}:moon`;
export const HAND_STEPS = 16;
const TIDE = 12000, SHIFT = 750;             // one tide; how much later it comes per moon phase (as tideState)

/** Which of the 16 hand positions shows now: 0 is straight up (the middle of high tide), clockwise from there. */
export function handStep(timeOfDay, moon) {
  const t = (((timeOfDay - moon * SHIFT) % TIDE) + TIDE) % TIDE;
  return Math.round(t / TIDE * HAND_STEPS) % HAND_STEPS;
}

function show(block) {
  try {
    const moon = Math.max(0, Math.min(7, moonPhase() | 0));
    const hand = handStep(world.getTimeOfDay(), moon);
    const p = block.permutation;
    if (p.getState(HAND) !== hand || p.getState(MOON) !== moon) block.setPermutation(p.withState(HAND, hand).withState(MOON, moon));
  } catch {}
}

const tideClock = {
  onPlace({ block }) { show(block); },
  onTick({ block }) { show(block); },
};

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(`${NS}:tide_clock`, tideClock);
});
