// ## What a fish carries while it sits in a block (v1.3.3).
// Block states only hold a fish's species and size class, so a record fish laid in a Fish Tank or on
// a Fish Cleaning Board used to come back without its "★ N cm" (and a renamed fish without its name).
// Everything beyond the plain class mark now waits in a world property under the block's position
// (the Large Fish Tank keeps it in its own fish list) until the fish comes back out.
import { world } from "@minecraft/server";
import { applyClass, markOf, readSize } from "../fishing/size.js";

const NS = "kaleidoscope_fishing";

/** World property key for one block: kind "tk" (Fish Tank) or "cb" (Fish Cleaning Board). */
export const keepKey = (kind, dim, p) => `${NS}:${kind}:${dim.id}:${p.x},${p.y},${p.z}`;

/** What the stack carries beyond its class mark: { lore?, name? }, or undefined for a plain fish. */
export function keepOf(stack) {
  if (!stack) return undefined;
  let lore = [], name;
  try { lore = (stack.getLore() ?? []).filter(l => typeof l === "string"); } catch {}
  try { name = stack.nameTag || undefined; } catch {}
  const plain = lore.length === 0 || (lore.length === 1 && lore[0] === markOf(readSize(stack).cls));
  if (plain && !name) return undefined;
  const k = {};
  if (!plain) k.lore = lore.slice(0, 20);
  if (name) k.name = String(name).slice(0, 64);
  return k;
}

/** A fish coming back out of a block: its class mark, then everything it went in with. */
export function fishOut(stack, cls, keep) {
  applyClass(stack, cls);
  if (keep && typeof keep === "object") {
    if (Array.isArray(keep.lore) && keep.lore.length) { try { stack.setLore(keep.lore.map(String)); } catch {} }
    if (typeof keep.name === "string" && keep.name) { try { stack.nameTag = keep.name; } catch {} }
  }
  return stack;
}

/** Remember (or, with nothing to keep, forget) what the fish in a block carries. */
export function stash(key, keep) {
  try { world.setDynamicProperty(key, keep ? JSON.stringify(keep) : undefined); } catch {}
}

/** Take back what was remembered for a block (and forget it). */
export function unstash(key) {
  let keep;
  try {
    const v = world.getDynamicProperty(key);
    if (typeof v === "string") keep = JSON.parse(v);
  } catch {}
  stash(key, undefined);
  return keep && typeof keep === "object" ? keep : undefined;
}
