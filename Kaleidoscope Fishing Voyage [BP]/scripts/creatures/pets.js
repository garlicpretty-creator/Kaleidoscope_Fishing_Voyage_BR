// ## Wolves and cats take what we catch (1.5.0).
// Fish Bones tame a wild wolf as a bone does, and any fish of ours tames a stray cat as raw cod does: one item
// a try, one chance in three. A tamed cat that is hurt eats a fish to heal. Legends are never offered (nobody
// should lose one to a cat), and shellfish are not fish: the same rule the cormorant has.
// All of it is script. The parts the game keeps inside the wolf's and the cat's own entity files stay as they
// are, because changing them means shipping our own copy of a vanilla mob (decided against, plan 11.9): a wolf
// does not tilt its head at Fish Bones, cats do not breed on our fish, ocelots do not come to trust it. What a
// script can do for the cat that runs away: while a player who is not sprinting holds one of our fish, stray
// cats within 8 blocks stand still, so the player can walk up to them.
import { EquipmentSlot, GameMode, system, world } from "@minecraft/server";
import { LEGEND_SET } from "../fishing/loot.js";
import { spawnParticle } from "../util/particles.js";

const NS = "kaleidoscope_fishing";
const BONES = `${NS}:fish_bones`;
const WOLF = "minecraft:wolf", CAT = "minecraft:cat";
export const TAME_CHANCE = 1 / 3;
const CAT_HEAL = 2;                          // one heart, as a raw fish heals a tamed cat
const HOLD_RANGE = 8;

const creative = p => { try { return p.getGameMode() === GameMode.Creative; } catch { return false; } };
const tamed = e => { try { return !!e.getComponent("minecraft:is_tamed"); } catch { return false; } };
const hostile = e => { try { return !!e.target; } catch { return false; } };
/** A fish of ours a cat will take: tagged as fish, not a legend. */
export function isCatFish(stack) {
  try { return !!stack && stack.typeId.startsWith(`${NS}:`) && stack.hasTag("minecraft:is_fish") && !LEGEND_SET.has(stack.typeId); } catch { return false; }
}
function mainhand(player) {
  try { return player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand); } catch { return undefined; }
}
/** Take one of `id` from the player's hand; false when it is no longer there. */
function spend(player, id) {
  const slot = mainhand(player);
  if (!slot?.hasItem() || slot.typeId !== id) return false;
  if (creative(player)) return true;
  try {
    const stack = slot.getItem();
    if (stack.amount <= 1) slot.setItem(undefined); else { stack.amount -= 1; slot.setItem(stack); }
    return true;
  } catch { return false; }
}
function puff(entity, particle, n) {
  for (let i = 0; i < n; i++) {
    try {
      const l = entity.location;
      spawnParticle(entity.dimension, particle, { x: l.x + (Math.random() - 0.5) * 0.8, y: l.y + 0.6 + Math.random() * 0.6, z: l.z + (Math.random() - 0.5) * 0.8 });
    } catch {}
  }
}

/** One offer to a wild animal: the item is eaten; it is tamed with TAME_CHANCE. Returns "tamed" | "refused" | undefined. */
export function offer(player, animal, id, rand = Math.random) {
  if (!animal?.isValid || tamed(animal) || hostile(animal)) return undefined;
  let tameable;
  try { tameable = animal.getComponent("minecraft:tameable"); } catch {}
  if (!tameable || !spend(player, id)) return undefined;
  let ok = false;
  if (rand() < TAME_CHANCE) { try { ok = tameable.tame(player) !== false; } catch {} }
  puff(animal, ok ? "minecraft:heart_particle" : "minecraft:basic_smoke_particle", 7);
  return ok ? "tamed" : "refused";
}

/** A hurt, tamed cat eats the fish and heals a heart. Returns true when it ate. */
export function feedCat(player, cat, id) {
  if (!cat?.isValid || !tamed(cat)) return false;
  let health;
  try { health = cat.getComponent("minecraft:health"); } catch {}
  if (!health || health.currentValue >= health.effectiveMax || !spend(player, id)) return false;
  try { health.setCurrentValue(Math.min(health.effectiveMax, health.currentValue + CAT_HEAL)); } catch {}
  puff(cat, "minecraft:heart_particle", 3);
  return true;
}

try {
  world.beforeEvents.playerInteractWithEntity.subscribe(ev => {
    const { player, target, itemStack } = ev;
    if (!player || !target || !itemStack) return;
    const id = itemStack.typeId;
    if (target.typeId === WOLF && id === BONES && !tamed(target)) {
      ev.cancel = true;
      system.run(() => { try { offer(player, target, id); } catch (err) { console.warn(`[Fishing Voyage] wolf: ${err}`); } });
    } else if (target.typeId === CAT && isCatFish(itemStack)) {
      ev.cancel = true;
      system.run(() => { try { if (tamed(target)) feedCat(player, target, id); else offer(player, target, id); } catch (err) { console.warn(`[Fishing Voyage] cat: ${err}`); } });
    }
  });
} catch {}

/** Stray cats near a player who holds one of our fish and is not sprinting stand still. Exported for tests. */
export function holdStrays() {
  for (const p of world.getAllPlayers()) {
    try {
      if (!p.isValid || p.isSprinting) continue;
      const slot = mainhand(p);
      if (!slot?.hasItem() || !isCatFish(slot.getItem())) continue;
      for (const cat of p.dimension.getEntities({ type: CAT, location: p.location, maxDistance: HOLD_RANGE })) {
        if (!tamed(cat)) cat.addEffect("slowness", 30, { amplifier: 6, showParticles: false });
      }
    } catch {}
  }
}
system.runInterval(() => { try { holdStrays(); } catch {} }, 10);
