// ## Tackle parts (v1.1): a hook, a line and a bobber can be fitted to a rod on the Tackle Rack.
// They are stored on the rod itself (an ItemStack dynamic property; rods never stack), so the
// rod keeps them wherever it goes. What they do is in tools/data.py (PARTS).
import { LINE_STYLE, PARTS } from "../data/generated.js";

const NS = "kaleidoscope_fishing";
const KEY = `${NS}:parts`;
export const SLOTS = ["hook", "line", "bobber"];
export const isPart = id => !!PARTS[id];
export const slotOf = id => PARTS[id]?.slot;

export function readParts(stack) {
  try {
    const v = JSON.parse(stack?.getDynamicProperty(KEY) ?? "{}");
    return v && typeof v === "object" ? v : {};
  } catch { return {}; }
}

/** Store the parts on the rod and list them under its name (in the player's language). */
export function writeParts(stack, parts) {
  const clean = Object.fromEntries(SLOTS.filter(k => PARTS[parts?.[k]]).map(k => [k, parts[k]]));
  try { stack.setDynamicProperty(KEY, Object.keys(clean).length ? JSON.stringify(clean) : undefined); } catch {}
  const ids = SLOTS.map(k => clean[k]).filter(Boolean);
  try { stack.setLore(ids.map(id => ({ translate: `${NS}.name.${id.split(":")[1]}` }))); }
  catch { try { stack.setLore([]); } catch {} }
  return stack;
}

/** Combined effect of a rod's parts. */
export function effects(parts) {
  const e = { bite: 1, window: 0, strain: 0, rare: 1, size: 0, wear: 0, depth: 0, night: 1, style: 0, line: undefined, lure: false, shallow: 1 };
  for (const id of Object.values(parts ?? {})) {
    const p = PARTS[id];
    if (!p) continue;
    if (p.bite) e.bite *= p.bite;
    if (p.night) e.night *= p.night;
    if (p.rare) e.rare *= p.rare;
    if (p.lure) e.lure = true;                 // v1.4: a lure hook fishes without bait
    if (p.shallow) e.shallow *= p.shallow;     // v1.4: a feather bobber favours shallow-water catches
    for (const k of ["window", "strain", "size", "wear", "depth"]) if (p[k]) e[k] += p[k];
    if (p.style) e.style = p.style;
  }
  e.line = LINE_STYLE[parts?.line];
  return e;
}
