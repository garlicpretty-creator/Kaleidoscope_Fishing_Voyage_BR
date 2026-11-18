// ## Hand Net (撈網, 1.6.0; docs/PLAN_1.6.0.md section 7.1). Sticks, string and a Fishing Net; 64 uses.
//   on a fish in a pond      that very fish comes out (blocks/pond.js scoop: the display entity knows its place
//                            in the pond's roster). Aimed at the water instead, the fish nearest the crosshair.
//   on a Wooden Tub          the hatched fry come out (blocks/tub.js), as with an empty hand
//   on a Fish Tank           the fish comes out (blocks/tanks.js), as with an empty hand
// Each catch costs one use (Unbreaking spares it as it does a tool). A pond fish that is no longer there (the pond
// changed under it) costs nothing and gives nothing.
import { EquipmentSlot, GameMode, system, world } from "@minecraft/server";
import { enchantLevel, wears } from "../util/enchant.js";
import { FISH_ENTITY, TAG, aimedPondFish, scoop } from "../blocks/pond.js";

const NS = "kaleidoscope_fishing";
export const HAND_NET = `${NS}:hand_net`;
const creative = p => { try { const g = p.getGameMode(); return g === GameMode.Creative || g === "creative"; } catch { return false; } };
const last = new Map();                                // player id -> tick of the last scoop (one per use)

/** One use of the net in the player's main hand: a point of wear, and it breaks at the end. */
export function wearNet(player, rand = Math.random) {
  if (creative(player)) return;
  try {
    const slot = player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
    const it = slot?.getItem();
    if (it?.typeId !== HAND_NET) return;
    const d = it.getComponent("minecraft:durability");
    if (!d) return;
    if (!wears(enchantLevel(it, "unbreaking"), rand)) return;
    if (d.damage + 1 >= d.maxDurability) {
      slot.setItem(undefined);
      try { player.playSound("random.break"); } catch {}
      return;
    }
    d.damage += 1;
    slot.setItem(it);
  } catch {}
}

/** Scoop a pond fish with the net (an entity, or the one aimed at). True when a fish came out. Exported for tests. */
export function netFish(player, entity) {
  const now = system.currentTick;
  if (last.get(player.id) === now) return false;
  const e = entity ?? aimedPondFish(player);
  if (!e) return false;
  last.set(player.id, now);
  if (!scoop(player, e)) return false;
  wearNet(player);
  return true;
}

const isPondFish = e => { try { return e?.typeId === FISH_ENTITY && e.getTags().some(t => t.startsWith(TAG)); } catch { return false; } };

world.beforeEvents.playerInteractWithEntity.subscribe(ev => {
  if (ev.itemStack?.typeId !== HAND_NET || !isPondFish(ev.target)) return;
  ev.cancel = true;
  const { player, target } = ev;
  system.run(() => netFish(player, target));
});
world.afterEvents.itemUse.subscribe(ev => {
  if (ev.itemStack?.typeId !== HAND_NET || !ev.source) return;
  const player = ev.source;
  system.run(() => netFish(player));
});
world.afterEvents.playerLeave.subscribe(ev => last.delete(ev.playerId));
