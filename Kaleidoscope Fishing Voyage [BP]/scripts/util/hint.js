// ## Refusal feedback. A workstation action that does nothing plays a fixed "refused" sound that only
// that player hears. No text (1.4 immersion rule): the `key` and `args` stay in every call so a
// text line can come back later without touching the call sites.
// At most one refusal sound per player every HINT_GAP ticks, so holding the use button does not spam it.
import { system, world } from "@minecraft/server";

const HINT_GAP = 10;
const last = new Map();                   // player id -> tick of the last refusal sound

/** Tell the player an action was refused (sound only). */
export function refuse(player, key, ...args) {   // eslint-disable-line no-unused-vars
  if (!player) return;
  const now = system.currentTick;
  const prev = last.get(player.id);
  if (prev !== undefined && now - prev < HINT_GAP) return;
  last.set(player.id, now);
  try { player.playSound("note.bass", { pitch: 0.7, volume: 0.6 }); } catch {}
}

world.afterEvents.playerLeave.subscribe(ev => last.delete(ev.playerId));
