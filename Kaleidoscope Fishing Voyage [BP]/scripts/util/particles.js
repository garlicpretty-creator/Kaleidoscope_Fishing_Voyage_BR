// ## Particles (v1.5.2). Every particle the pack spawns goes through spawnParticle() here.
// Some vanilla particles read Molang variables that the code spawning them has to supply (their
// definitions in the vanilla resource pack read variable.direction / variable.note_color without
// setting them). Spawned without a MolangVariableMap, every client that sees one logs a Molang
// error in its content log (luosen, v1.5.1). VARS lists the ones this pack uses; the release check
// (tools/check_pack.py, "particles") fails if a script names another vanilla particle that needs
// variables without an entry here, or calls .spawnParticle() anywhere but this file.
import { MolangVariableMap } from "@minecraft/server";

const ZERO = { x: 0, y: 0, z: 0 };

// Vanilla note block colours (24 pitches round the colour wheel), as the note block itself picks them.
export function noteColor(note = Math.floor(Math.random() * 25)) {
  const f = (note % 25) / 24, c = k => Math.max(0, Math.sin((f + k / 3) * Math.PI * 2) * 0.65 + 0.35);
  return { red: c(0), green: c(1), blue: c(2) };
}

// v1.5.3: the zero-direction map is built once and shared (the engine copies the values on every
// spawnParticle call); building a new one per splash was a quarter of the fish schools' cost on luosen.
let zeroDirection;
const direction = opts => {
  if (!opts?.direction) {
    if (!zeroDirection) { zeroDirection = new MolangVariableMap(); zeroDirection.setVector3("variable.direction", ZERO); }
    return zeroDirection;
  }
  const m = new MolangVariableMap();
  m.setVector3("variable.direction", opts.direction);
  return m;
};

// id -> (opts) => MolangVariableMap. A zero direction looks exactly as these did before (an unset
// variable reads as 0); pass opts.direction to give them a push.
export const VARS = {
  "minecraft:water_splash_particle": direction,
  "minecraft:water_wake_particle": direction,
  "minecraft:basic_crit_particle": direction,
  "minecraft:portal_reverse_particle": direction,
  "minecraft:note_particle": opts => {
    const m = new MolangVariableMap();
    m.setColorRGB("variable.note_color", opts?.color ?? noteColor(opts?.note));
    return m;
  },
};

/**
 * Spawn a particle for everyone near it (target = a Dimension) or for one player only (target = a
 * Player). opts: { direction: {x,y,z} } or { note: 0..24 | color: {red,green,blue} } where the
 * particle takes them. Never throws (an unloaded chunk or a gone player just skips it).
 */
export function spawnParticle(target, id, location, opts) {
  try {
    const vars = VARS[id]?.(opts);
    if (vars) target.spawnParticle(id, location, vars);
    else target.spawnParticle(id, location);
    return true;
  } catch {
    return false;
  }
}
