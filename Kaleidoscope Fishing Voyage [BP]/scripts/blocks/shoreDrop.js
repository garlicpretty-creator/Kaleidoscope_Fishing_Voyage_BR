// ## Shore blocks (Oyster Bed, Laver Rock): breaking one gives 1-3 of its catch; with
// Silk Touch the whole block comes along. Done here rather than in a loot table: Bedrock
// loot tables have no "without Silk Touch" condition, and a bad condition drops nothing.
// Component params: { item, min, max }.
import { EquipmentSlot, GameMode, ItemStack, system } from "@minecraft/server";

const NS = "kaleidoscope_fishing";

function hasSilkTouch(player) {
  try {
    const item = player.getComponent("minecraft:equippable").getEquipment(EquipmentSlot.Mainhand);
    return !!item?.getComponent("minecraft:enchantable")?.getEnchantment("silk_touch");
  } catch { return false; }
}

const shoreDrop = {
  onPlayerBreak({ block, brokenBlockPermutation, player }, arg) {
    if (!player || player.getGameMode() === GameMode.Creative) return;
    const p = arg?.params ?? {};
    const min = p.min ?? 1, max = p.max ?? 3;
    const self = brokenBlockPermutation?.type?.id ?? `${NS}:oyster_bed`;
    const drop = hasSilkTouch(player) ? new ItemStack(self, 1)
      : new ItemStack(p.item ?? `${NS}:oyster`, min + Math.floor(Math.random() * (max - min + 1)));
    try { block.dimension.spawnItem(drop, block.center()); } catch {}
  },
};

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(`${NS}:shore_drop`, shoreDrop);
});
