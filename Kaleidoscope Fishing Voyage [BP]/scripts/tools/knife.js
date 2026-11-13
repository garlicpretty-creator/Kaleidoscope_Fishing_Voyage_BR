// ## Knife drops: a Squid or Glow Squid killed with a knife drops squid for cooking.
// Any item tagged kaleidoscope_cookery:kitchen_knife counts (the Fishing Knife, Cookery's
// kitchen knives, other add-ons' knives) - the shared contract the Cookery API asks for.
import { EquipmentSlot, ItemStack, world } from "@minecraft/server";

const KNIFE_TAG = "kaleidoscope_cookery:kitchen_knife";
const SQUIDS = new Set(["minecraft:squid", "minecraft:glow_squid"]);

world.afterEvents.entityDie.subscribe(ev => {
  const dead = ev.deadEntity;
  let typeId;
  try { typeId = dead.typeId; } catch { return; }
  if (!SQUIDS.has(typeId)) return;
  const killer = ev.damageSource?.damagingEntity;
  if (!killer || killer.typeId !== "minecraft:player") return;
  let knife = false;
  try { knife = !!killer.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand)?.hasTag(KNIFE_TAG); } catch {}
  if (!knife) return;
  try { dead.dimension.spawnItem(new ItemStack("kaleidoscope_fishing:squid_tube", 1 + Math.floor(Math.random() * 2)), dead.location); } catch {}
}, { entityTypes: ["minecraft:squid", "minecraft:glow_squid"] });
