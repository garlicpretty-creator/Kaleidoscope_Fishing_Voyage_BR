// ## Glass Float + Star Sand (1.5.0, plan 10.3): star sand rubbed into a glass float makes it glow.
// Use Star Sand on a placed Glass Float: it becomes a Glowing Glass Float facing the same way (one star sand is
// used, none in Creative). Anything else in hand does nothing: the float is decoration.
import { BlockPermutation, EquipmentSlot, GameMode, system } from "@minecraft/server";

const NS = "kaleidoscope_fishing";
export const STAR_SAND = `${NS}:star_sand`;
export const GLOWING = `${NS}:glowing_glass_float`;
const DIR = "minecraft:cardinal_direction";

const creative = p => { try { const g = p.getGameMode(); return g === GameMode.Creative || g === "creative"; } catch { return false; } };

export const starFloat = {
  onPlayerInteract({ block, player }) {
    if (!player) return;
    const slot = player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
    const held = slot?.hasItem() ? slot.getItem() : undefined;
    if (held?.typeId !== STAR_SAND) return;
    let dir = "south";
    try { dir = block.permutation.getState(DIR) ?? dir; } catch {}
    try { block.setPermutation(BlockPermutation.resolve(GLOWING, { [DIR]: dir })); } catch { return; }
    if (!creative(player)) { if (held.amount <= 1) slot.setItem(undefined); else { held.amount -= 1; slot.setItem(held); } }
    try { block.dimension.playSound("random.orb", block.center(), { pitch: 1.6, volume: 0.6 }); } catch {}
  },
};

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(`${NS}:star_float`, starFloat);
});
