// ## 1.6.0: the world's "animations" switch (docs/PLAN_1.6.0.md section 12.3).
// The display entities and particle effects that make stations move can be turned off for a slow server.
// One world property, changed by an operator on the journal's settings page (journal/settings.js); on by default.
// Read once and cached; every change is saved at once. Code that spawns a station's moving parts asks animationsOn().
import { world } from "@minecraft/server";

const KEY = "kaleidoscope_fishing:animations";
let on;

/** Whether stations show their moving parts and effects (default: yes). */
export function animationsOn() {
  if (on === undefined) {
    on = true;
    try { const v = world.getDynamicProperty(KEY); if (v === false || v === "off") on = false; } catch {}
  }
  return on;
}

/** Turn the animations on or off for the whole world (the settings page checks the player is an operator). */
export function setAnimations(value) {
  on = !!value;
  try { world.setDynamicProperty(KEY, on); } catch {}
}

/** For tests: forget the cached value. */
export function _resetFx() { on = undefined; }
