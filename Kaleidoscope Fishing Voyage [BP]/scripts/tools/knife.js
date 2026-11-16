// ## Knife drops: a Squid or Glow Squid killed with a knife drops squid for cooking.
// Any item tagged kaleidoscope_cookery:kitchen_knife counts (the Fishing Knife, Cookery's
// kitchen knives, other add-ons' knives) - the shared contract the Cookery API asks for.
// 1.5.0: Looting on the knife adds up to one more squid per level, as it does for the game's own drops.
import { EquipmentSlot, ItemStack, world } from "@minecraft/server";
import { enchantLevel } from "../util/enchant.js";

const KNIFE_TAG = "kaleidoscope_cookery:kitchen_knife";
const SQUIDS = new Set(["minecraft:squid", "minecraft:glow_squid"]);

world.afterEvents.entityDie.subscribe(ev => {
  const dead = ev.deadEntity;
  let typeId;
  try { typeId = dead.typeId; } catch { return; }
  if (!SQUIDS.has(typeId)) return;
  const killer = ev.damageSource?.damagingEntity;
  if (!killer || killer.typeId !== "minecraft:player") return;
  let held;
  try { held = killer.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand); } catch {}
  let knife = false;
  try { knife = !!held?.hasTag(KNIFE_TAG); } catch {}
  if (!knife) return;
  const looting = Math.floor(Math.random() * (enchantLevel(held, "looting") + 1));
  try { dead.dimension.spawnItem(new ItemStack("kaleidoscope_fishing:squid_tube", 1 + Math.floor(Math.random() * 2) + looting), dead.location); } catch {}
}, { entityTypes: ["minecraft:squid", "minecraft:glow_squid"] });
