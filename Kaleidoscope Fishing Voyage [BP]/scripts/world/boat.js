// ## Fishing from a boat, and the Fishing Skiff (釣魚小船, 1.5.0, plan 8).
// Any boat (the game's boats and chest boats, and the skiff): the bait hangs 4 blocks deeper and big fish come a
// little more often (fishing/rod.js asks onBoat). The Fishing Skiff runs on the game's chest boat, so the game moves
// it, seats its rider and keeps its 27-slot hold (crouch and use it to open, as a chest boat). On top of that:
//   the hold      a catch the creel cannot take goes into the hold before the angler's hands (stow)
//   the lantern   at night bites come a little sooner (not with a Glow Bobber: rod.js)
//   the trawl     a Fishing Net used on the skiff hangs a trawl off the stern (crouch and use a net again to take it
//                 in). Over water 8 or more deep, every 64 blocks it sails brings up 1-2 small fish into the hold,
//                 until the hold is full; after 32 hauls the net is worn through and gone.
// Not done: the trawl does not slow the boat (the game's boat speed is not ours to change).
import { ItemStack, system, world } from "@minecraft/server";
import { isWater, timeSlot } from "../fishing/water.js";

const NS = "kaleidoscope_fishing";
export const SKIFF = `${NS}:fishing_skiff`;
const NET = `${NS}:fishing_net`;
const TRAWL = `${NS}:trawl`;
export const BOATS = new Set(["minecraft:boat", "minecraft:chest_boat", SKIFF]);
export const BOAT_DEPTH = 4;
export const LANTERN_BITE = 0.85;
export const TRAWL_EVERY = 64, TRAWL_DEPTH = 8, NET_HAULS = 32;
// small, common sea fish (no legends, rare, sky or big fish), always small
export const TRAWL_CATCH = [[`${NS}:shrimp`, 30], [`${NS}:mackerel`, 25], [`${NS}:saury`, 20], [`${NS}:yellow_croaker`, 15], ["minecraft:cod", 10]];
const SIZED = new Set([`${NS}:mackerel`, `${NS}:saury`, `${NS}:yellow_croaker`, "minecraft:cod"]);

/** The boat a player sits in, or undefined. */
export function boatOf(player) {
  try {
    const e = player.getComponent("minecraft:riding")?.entityRidingOn;
    return e && BOATS.has(e.typeId) ? e : undefined;
  } catch { return undefined; }
}
export const onSkiff = player => boatOf(player)?.typeId === SKIFF;
/** The lantern helps at night, on the skiff only. */
export const lanternOn = player => onSkiff(player) && timeSlot() === "night";
const holdOf = boat => { try { return boat.getComponent("minecraft:inventory")?.container; } catch { return undefined; } };

/** Put a catch in the skiff's hold; returns what did not fit (the whole stack when not on the skiff). */
export function stow(player, stack) {
  const boat = boatOf(player);
  if (boat?.typeId !== SKIFF) return stack;
  const hold = holdOf(boat);
  if (!hold) return stack;
  try { return hold.addItem(stack); } catch { return stack; }
}

function pick(rand) {
  let r = rand() * TRAWL_CATCH.reduce((a, [, w]) => a + w, 0);
  for (const [id, w] of TRAWL_CATCH) { r -= w; if (r <= 0) return id; }
  return TRAWL_CATCH[0][0];
}
/** One haul: 1-2 small fish as stacks. Exported for tests. */
export function haul(rand = Math.random) {
  const out = [];
  for (let i = 0, n = 1 + (rand() < 0.5 ? 1 : 0); i < n; i++) {
    const s = new ItemStack(pick(rand), 1);
    if (SIZED.has(s.typeId)) { try { s.setLore(["§7◆"]); } catch {} }
    out.push(s);
  }
  return out;
}
/** The trawl's distance count: { gone, hauls } after sailing `moved` blocks over water `depth` deep. Exported for tests. */
export function trawlStep(gone, moved, depth) {
  if (depth < TRAWL_DEPTH || !(moved > 0)) return { gone, hauls: 0 };
  let g = gone + Math.min(moved, 20);                  // a teleport is not sailing
  let hauls = 0;
  while (g >= TRAWL_EVERY) { g -= TRAWL_EVERY; hauls++; }
  return { gone: g, hauls };
}

function depthUnder(boat) {
  const l = boat.location;
  let d = 0;
  try {
    for (let y = Math.floor(l.y); d < TRAWL_DEPTH + 1; y--, d++) if (!isWater(boat.dimension.getBlock({ x: Math.floor(l.x), y, z: Math.floor(l.z) }))) break;
  } catch {}
  return d;
}
const last = new Map();                               // boat id -> { x, z, gone }
/** Look at every skiff with its trawl out. Exported for tests. */
export function trawlTick(rand = Math.random) {
  let boats = [];
  try { boats = world.getDimension("minecraft:overworld").getEntities({ type: SKIFF }); } catch {}
  const seen = new Set();
  for (const b of boats) {
    let on = 0;
    try { on = b.getProperty(TRAWL); } catch {}
    if (!on) { last.delete(b.id); continue; }
    seen.add(b.id);
    const l = b.location, p = last.get(b.id) ?? { x: l.x, z: l.z, gone: 0 };
    const moved = Math.hypot(l.x - p.x, l.z - p.z);
    const r = trawlStep(p.gone, moved, depthUnder(b));
    last.set(b.id, { x: l.x, z: l.z, gone: r.gone });
    for (let i = 0; i < r.hauls; i++) {
      const hold = holdOf(b);
      if (!hold || hold.emptySlotsCount === 0) break;     // a full hold: the net brings nothing more
      for (const s of haul(rand)) { try { const left = hold.addItem(s); if (left) break; } catch {} }
      let n = 0;
      try { n = Number(b.getDynamicProperty("kfv:hauls") ?? 0) + 1; b.setDynamicProperty("kfv:hauls", n); } catch {}
      try { b.dimension.playSound("random.splash", l, { pitch: 1.4, volume: 0.6 }); } catch {}
      if (n >= NET_HAULS) {                               // worn through
        try { b.setProperty(TRAWL, 0); b.setDynamicProperty("kfv:hauls", 0); b.dimension.playSound("random.break", l, { pitch: 1.2, volume: 0.7 }); } catch {}
        break;
      }
    }
  }
  for (const k of [...last.keys()]) if (!seen.has(k)) last.delete(k);
}

/** A net used on the skiff: hang the trawl, or (crouching) take it in. Returns true when it acted. Exported for tests. */
export function useNet(player, boat, held) {
  if (boat?.typeId !== SKIFF || held?.typeId !== NET) return false;
  let on = 0;
  try { on = boat.getProperty(TRAWL); } catch {}
  const crouch = !!player.isSneaking;
  if (!on && !crouch) {
    try { boat.setProperty(TRAWL, 1); } catch { return false; }
    const slot = player.getComponent("minecraft:equippable")?.getEquipmentSlot("Mainhand");
    try {
      const g = player.getGameMode?.();
      if (g !== "Creative" && g !== "creative") { if (held.amount <= 1) slot.setItem(undefined); else { held.amount -= 1; slot.setItem(held); } }
    } catch {}
    try { boat.dimension.playSound("random.splash", boat.location, { pitch: 0.9, volume: 0.6 }); } catch {}
    return true;
  }
  if (on && crouch) {
    try { boat.setProperty(TRAWL, 0); } catch { return false; }
    try { player.getComponent("minecraft:inventory")?.container?.addItem(new ItemStack(NET, 1)); } catch {}   // the wear stays with the skiff
    return true;
  }
  return false;
}

world.beforeEvents.playerInteractWithEntity?.subscribe(ev => {
  if (ev.target?.typeId !== SKIFF || ev.itemStack?.typeId !== NET) return;
  ev.cancel = true;                                   // a net never seats you or opens the hold
  const { player, target, itemStack } = ev;
  system.run(() => { try { useNet(player, target, player.getComponent("minecraft:equippable")?.getEquipmentSlot("Mainhand")?.getItem() ?? itemStack); } catch {} });
});
system.runInterval(() => { try { trawlTick(); } catch {} }, 20);
