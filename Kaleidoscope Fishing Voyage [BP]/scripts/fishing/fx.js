// ## Fishing feel (1.5.0): what the angler sees and hears between the cast and the catch.
// Immersion rule: no text. The bobber itself is animated on the client (RP animations/kfv_bobber.animation.json),
// picked by its "motion" property; this file sets that property on phase changes only (one sync each) and adds
// the particles and sounds around it. Particles go through util/particles.js like every other one in the pack.
// Water effects (ripples, drops, bubbles, leaping fish) are skipped on lava and over the End void.
import { system } from "@minecraft/server";
import { spawnParticle } from "../util/particles.js";

const NS = "kaleidoscope_fishing";
const P = name => `${NS}:fishing_${name}`;
export const FX = {
  ripple: P("ripple"), rippleBig: P("ripple_big"), droplets: P("droplets"), splashBig: P("splash_big"),
  bubbles: P("bubbles"), leap: P("leap"), leapBig: P("leap_big"), leapGold: P("leap_gold"), trail: P("trail"), gold: P("gold"),
};
// the bobber's client animation (entities/bobber.json property kaleidoscope_fishing:motion)
export const MOTION = { none: 0, float: 1, nibble: 2, bite: 3, thrash: 4, pop: 5 };
const MOTION_PROP = `${NS}:motion`;
const POP_TICKS = 12;                 // the pop animation is 0.6 s; then it floats again

const fx = (dim, id, loc) => { try { spawnParticle(dim, id, loc); } catch {} };
const sound = (dim, id, loc, pitch = 1, volume = 0.8) => { try { dim.playSound(id, loc, { pitch, volume }); } catch {} };
const randInt = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
const at = (l, dy = 0, dx = 0, dz = 0) => ({ x: l.x + dx, y: l.y + dy, z: l.z + dz });
export const wet = s => !s.inLava && !s.inVoid;

/** Sets the bobber's animation; a no-op when it already plays that one. */
export function setMotion(s, m) {
  if (s.motion === m) return;
  try { s.bobber.setProperty(MOTION_PROP, m); s.motion = m; } catch {}
  if (m === MOTION.pop) s.popEnd = s.age + POP_TICKS;
}

/** Every rod tick, whatever the phase: ends a pop and lets the bobber float again. */
export function settle(s) {
  if (s.motion === MOTION.pop && s.age >= (s.popEnd ?? 0)) setMotion(s, MOTION.float);
}

// ---------------------------------------------------------------- cast
/** While the bobber flies: line paying off the reel (clicks) and a drop or two behind it. */
export function flying(s, dim, loc) {
  if (s.age <= 16 && s.age % 4 === 0) sound(dim, "random.click", s.player.location, 1.7 + s.age * 0.02, 0.18);
  if (s.age <= 30 && s.age % 4 === 2) fx(dim, FX.trail, loc);
}

/** The bobber lands on the surface: a plop, rings spreading out, a few drops. */
export function landed(s, dim, loc) {
  setMotion(s, MOTION.float);
  if (!wet(s)) return;
  fx(dim, FX.ripple, at(loc, 0.02));
  fx(dim, FX.droplets, loc);
  sound(dim, "bucket.empty_water", loc, 1.6, 0.25);
}

// ---------------------------------------------------------------- waiting, nibble, bite
/** Waiting: now and then a ring spreads from the bobber; close to the bite a fish noses at it. */
export function waiting(s, dim, loc, surface) {
  const left = s.biteAt - s.age;
  if (left < 36) {
    setMotion(s, MOTION.nibble);
    if (!wet(s)) return;
    // bubbles closing on the bobber from where the fish comes in
    if (s.age % 4 === 0) {
      if (s.nibbleA === undefined) s.nibbleA = Math.random() * Math.PI * 2;
      const k = Math.max(0.15, left / 30), a = s.nibbleA;
      fx(dim, FX.bubbles, { x: loc.x + Math.cos(a) * k, y: surface - 0.15, z: loc.z + Math.sin(a) * k });
    }
    // little tugs: a tiny ring and a soft plip
    if (left % 12 === 0) { fx(dim, FX.ripple, at(loc, 0.02)); sound(dim, "random.splash", loc, 1.9, 0.12); }
    return;
  }
  s.nibbleA = undefined;
  if (s.motion !== MOTION.pop) setMotion(s, MOTION.float);
  if (wet(s) && s.age % 70 === 0 && Math.random() < 0.6) fx(dim, FX.ripple, at(loc, 0.02));
}

/** The fish takes it: the bobber goes under with a big splash and a burst of bubbles. */
export function bite(s, dim, loc) {
  setMotion(s, MOTION.bite);
  if (!wet(s)) return;
  fx(dim, FX.splashBig, loc);
  fx(dim, FX.rippleBig, at(loc, 0.02));
  fx(dim, FX.bubbles, at(loc, -0.2));
}

/** During the bite window: bubbles keep coming up where the bobber went down. */
export function biting(s, dim, loc) {
  if (wet(s) && s.age % 4 === 0) fx(dim, FX.bubbles, at(loc, 0.1));
}

// ---------------------------------------------------------------- the fight
const big = s => s.legend || (s.cls ?? 0) >= 3;
/** A hooked fish (minigame or tug of war). near: the fish is up at the surface (it may leap). */
export function fighting(s, dim, loc, near = true) {
  setMotion(s, MOTION.thrash);
  if (s.legend && s.age % 4 === 0) fx(dim, FX.gold, at(loc, 0.3));
  if (!wet(s)) return;
  if (s.age % 6 === 3) fx(dim, big(s) ? FX.splashBig : FX.droplets, at(loc, 0.2));
  if (s.age % 10 === 0) fx(dim, FX.ripple, at(loc, 0.35));
  if (s.age % 8 === 4) fx(dim, FX.bubbles, at(loc, 0.2));
  leapTick(s, dim, loc, near);
}

/** The fish rests (minigame off): the bobber floats, rings and a few bubbles. */
export function resting(s, dim, loc) {
  if (s.motion !== MOTION.pop) setMotion(s, MOTION.float);
  if (s.legend && s.age % 8 === 0) fx(dim, FX.gold, at(loc, 0.3));
  if (wet(s) && s.age % 12 === 0) fx(dim, FX.bubbles, at(loc, -0.1));
}

// Now and then the fish breaks the surface and leaps clear in an arc, landing again ~0.7 s later.
function leapTick(s, dim, loc, near) {
  if (s.leapAt === undefined) s.leapAt = s.age + randInt(30, 70);
  if (s.reentryAt !== undefined && s.age >= s.reentryAt) {
    s.reentryAt = undefined;
    fx(dim, big(s) ? FX.rippleBig : FX.ripple, at(loc, 0.35));
    fx(dim, FX.droplets, at(loc, 0.2));
    sound(dim, "random.splash", loc, big(s) ? 0.75 : 1.15, 0.6);
  }
  if (s.age < s.leapAt || !near) return;
  s.leapAt = s.age + (s.legend ? randInt(40, 80) : randInt(60, 130));
  s.reentryAt = s.age + (big(s) ? 18 : 14);
  s.leaps = (s.leaps ?? 0) + 1;
  fx(dim, s.legend ? FX.leapGold : big(s) ? FX.leapBig : FX.leap, at(loc, 0.3));
  fx(dim, big(s) ? FX.splashBig : FX.droplets, at(loc, 0.2));
  sound(dim, "random.splash", loc, big(s) ? 0.85 : 1.25, 0.7);
  sound(dim, "mob.fish.flop", loc, big(s) ? 0.7 : 1.1, 0.5);
}

// ---------------------------------------------------------------- the end of it
/** The fish shakes the hook: a splash, and the bobber pops back up. */
export function escaped(s, dim, loc) {
  s.leapAt = s.reentryAt = undefined;
  setMotion(s, MOTION.pop);
  if (!wet(s)) return;
  fx(dim, FX.droplets, loc);
  fx(dim, FX.ripple, at(loc, 0.02));
}

/** The catch comes out: a splash where it was, then drops along its arc to the angler. */
export function landedCatch(s, dim, from, player) {
  if (!wet(s)) return;
  fx(dim, big(s) ? FX.splashBig : FX.droplets, from);
  fx(dim, FX.rippleBig, at(from, -0.35));
  let to;
  try { to = player.location; } catch { return; }
  const dx = to.x - from.x, dz = to.z - from.z, dy = to.y + 1 - from.y;
  const h = Math.min(2.5, 0.6 + Math.hypot(dx, dz) * 0.15);
  for (let i = 1; i <= 5; i++) {
    const t = i / 6;
    system.runTimeout(() => fx(dim, FX.trail, { x: from.x + dx * t, y: from.y + dy * t + Math.sin(Math.PI * t) * h, z: from.z + dz * t }), i * 2);
  }
}
