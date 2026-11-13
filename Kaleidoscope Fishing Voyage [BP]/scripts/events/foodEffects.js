// ## Food effects for 漁歌 dishes.
// The Bedrock port of Cookery excludes custom status effects, so only vanilla effects are used.
import { system, world } from "@minecraft/server";
import { FOOD_EFFECTS } from "../data/generated.js";

const NS = "kaleidoscope_fishing";
// v1.3: Chorus Sashimi blinks you a short way, like a chorus fruit, but only onto solid ground:
// it tries 16 spots within 8 blocks and stays put if none has a floor (no falls into the void).
const BLINKERS = new Set([`${NS}:chorus_sashimi`]);

function solid(b) {
  try { return !!b && !b.isAir && !b.isLiquid; } catch { return false; }
}
function open(b) {
  try { return !!b && b.isAir; } catch { return false; }
}

function safeSpot(player) {
  const dim = player.dimension, p = player.location;
  for (let i = 0; i < 16; i++) {
    const x = Math.floor(p.x + (Math.random() * 2 - 1) * 8), z = Math.floor(p.z + (Math.random() * 2 - 1) * 8);
    for (let dy = 4; dy >= -4; dy--) {
      const y = Math.floor(p.y) + dy;
      try {
        if (solid(dim.getBlock({ x, y: y - 1, z })) && open(dim.getBlock({ x, y, z })) && open(dim.getBlock({ x, y: y + 1, z })))
          return { x: x + 0.5, y, z: z + 0.5 };
      } catch {}
    }
  }
  return undefined;
}

function blink(player) {
  const to = safeSpot(player);
  if (!to) return;
  const dim = player.dimension;
  try { dim.playSound("mob.endermen.portal", player.location, { pitch: 1.2, volume: 0.6 }); } catch {}
  try { player.teleport(to); } catch { return; }
  try { dim.playSound("mob.endermen.portal", to, { pitch: 1.2, volume: 0.6 }); } catch {}
}

/** What eating dish `id` does to `player`: its FOOD_EFFECTS, and the chorus blink. Hunger is the game's job. */
export function applyFoodEffects(player, id) {
  if (!player || typeof id !== "string") return false;
  const effects = FOOD_EFFECTS[id] ?? [];
  for (const e of effects) {
    try { player.addEffect(e.effect, e.duration, { amplifier: e.amplifier ?? 0, showParticles: true }); } catch {}
  }
  if (BLINKERS.has(id)) system.run(() => { try { blink(player); } catch {} });
  return effects.length > 0 || BLINKERS.has(id);
}

world.afterEvents.itemCompleteUse.subscribe(ev => {
  applyFoodEffects(ev.source, ev.itemStack?.typeId);
});

// v1.5.9 (B047, Senluo PHASE2 contract §9): AWW's magic backpack feeds players without the vanilla eating
// flow, so itemCompleteUse never fires. AWW then sends
//   aww:evt {"v":1,"t":"autofed","p":"<player.id>","id":"<food id>","n":<hunger>}
// and a 漁歌 dish gets the same effects as eating it by hand. AWW already gave the hunger and returns
// the container; the integration pack turns every autofed into tf:ate. So only the effects happen here.
export const AUTOFED_EVT = "aww:evt";
export function onAutofed(ev) {
  if (ev?.id !== AUTOFED_EVT) return false;
  let m;
  try { m = JSON.parse(String(ev.message ?? "")); } catch { return false; }
  if (m?.v !== 1 || m.t !== "autofed" || typeof m.id !== "string" || !m.id.startsWith(`${NS}:`) || typeof m.p !== "string") return false;
  let player;
  try { player = world.getEntity(m.p); } catch { return false; }
  if (!player?.isValid || player.typeId !== "minecraft:player") return false;
  return applyFoodEffects(player, m.id);
}
system.afterEvents.scriptEventReceive.subscribe(ev => { try { onAutofed(ev); } catch {} }, { namespaces: ["aww"] });
