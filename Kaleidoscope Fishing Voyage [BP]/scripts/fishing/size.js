// ## Fish size classes (v1.1). Every fish reeled in with our rods is small, medium or large,
// written under its name as ◆ / ◆◆ / ◆◆◆ (no words, so it reads the same in every language).
// Fish of the same species and class stack together. A record fish also carries "★ N cm".
// Fish from anywhere else (vanilla rods, traps, other add-ons) carry nothing and count as medium.
import { CATCHES } from "../data/generated.js";

export const SMALL = 1, MEDIUM = 2, LARGE = 3;
const RANGE = Object.fromEntries(CATCHES.filter(c => c.size).map(c => [c.id, c.size]));
const MARK = { [SMALL]: "§7◆", [MEDIUM]: "§f◆◆", [LARGE]: "§6◆◆◆" };

export const hasSize = id => !!RANGE[id];
export const rangeOf = id => RANGE[id];

/** Size class for a length in cm: the species' range split in thirds. */
export function classOf(id, cm) {
  const r = RANGE[id];
  if (!r || cm === undefined) return MEDIUM;
  const p = (cm - r[0]) / Math.max(1, r[1] - r[0]);
  return p < 1 / 3 ? SMALL : p < 2 / 3 ? MEDIUM : LARGE;
}

export const markOf = cls => MARK[cls] ?? MARK[MEDIUM];

/** Lore lines for a fish: its class mark, and "★ N cm" for a record. */
export function loreFor(cls, recordCm) {
  const out = [markOf(cls)];
  if (recordCm !== undefined) out.push(`§6★ ${recordCm} cm`);
  return out;
}

// 1.5.0: a fish that grew up or was born in a fish pond (blocks/pond.js) is farmed, marked "✿" (no words, as the
// size marks). Farmed fish set no records and the fish merchant pays 60% for them.
export const FARMED_MARK = "§2✿";
/** Whether a stack is a farmed fish. */
export function isFarmed(stack) {
  try { return (stack.getLore() ?? []).some(l => typeof l === "string" && l.includes("✿")); } catch { return false; }
}

/** What a stack says about its size: { cls, cm?, record } (cls 0 = carries nothing). */
export function readSize(stack) {
  let lore = [];
  try { lore = stack.getLore() ?? []; } catch {}
  let cls = 0, cm, record = false;
  for (const raw of lore) {
    const l = typeof raw === "string" ? raw : "";
    const m = /★\s*(\d+)\s*cm/.exec(l);
    if (m) { cm = Number(m[1]); record = true; continue; }
    const n = (l.match(/◆/g) ?? []).length;
    if (n >= 1 && n <= 3) cls = n;
  }
  if (!cls && cm !== undefined) cls = classOf(stack.typeId, cm);
  return { cls, cm, record };
}

/** Put a class mark on a stack (nothing for cls 0). */
export function applyClass(stack, cls) {
  if (!cls) return stack;
  try { stack.setLore(loreFor(cls)); } catch {}
  return stack;
}
