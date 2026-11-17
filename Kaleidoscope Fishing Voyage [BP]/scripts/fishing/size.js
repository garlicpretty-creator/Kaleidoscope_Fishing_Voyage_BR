// ## Fish size classes (v1.1). Every fish reeled in with our rods is small, medium or large,
// written under its name as ◆ / ◆◆ / ◆◆◆ (no words, so it reads the same in every language).
// Fish of the same species and class stack together. A record fish also carries a ★.
// Fish from anywhere else (vanilla rods, traps, other add-ons) carry nothing and count as medium.
//
// 1.6.0 (docs/PLAN_1.6.0.md section 9): the record line shows only "★"; the length is no longer written out.
// It travels with the stack as invisible formatting codes after the star ("§6★§r§4§5" = 45 cm: a "§" and a
// digit only change the colour of nothing), because fish stack and Bedrock keeps ItemStack dynamic
// properties only on items that do not stack. A non-stacking stack (another pack's catch with max stack 1)
// also gets the dynamic property CM_KEY. Everything that copies a fish's lore (tanks, the board, racks,
// ponds) carries the length with it unchanged.
// Old fish with "★ N cm" are still read; upgradeLore / upgradeStack turn them into the new form, which the
// stations do whenever a fish passes through them.
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

export const CM_KEY = "kaleidoscope_fishing:cm";
const OLD_RECORD = /★\s*(\d+)\s*cm/;                    // up to 1.5.0: "§6★ 45 cm"
const NEW_RECORD = /★§r((?:§\d)+)/;                     // 1.6.0: "§6★§r§4§5"

/** The record line for a length: a gold ★ with the length hidden after it (1.6.0). */
export function recordLine(cm) {
  const n = Math.round(Number(cm));
  return Number.isFinite(n) && n > 0 ? `§6★§r${[...String(n)].map(d => `§${d}`).join("")}` : "§6★";
}

/** The record length a lore line carries (old "★ N cm" or 1.6.0 hidden digits), or undefined. */
export function recordCmOf(line) {
  if (typeof line !== "string" || !line.includes("★")) return undefined;
  const m = NEW_RECORD.exec(line) ?? OLD_RECORD.exec(line);
  if (!m) return undefined;
  const n = Number(m[1].replace(/§/g, ""));
  return Number.isFinite(n) ? n : undefined;
}

/** Lore lines for a fish: its class mark, and the ★ record line for a record. */
export function loreFor(cls, recordCm) {
  const out = [markOf(cls)];
  if (recordCm !== undefined) out.push(recordLine(recordCm));
  return out;
}

/** Lore lines with every old "★ N cm" turned into the 1.6.0 record line (other lines untouched). */
export function upgradeLore(lines) {
  if (!Array.isArray(lines)) return lines;
  return lines.map(l => (typeof l === "string" && OLD_RECORD.test(l) ? recordLine(recordCmOf(l)) : l));
}

/** Rewrite an old record fish's lore in place (and give a non-stacking one CM_KEY). True if it changed. */
export function upgradeStack(stack) {
  if (!stack) return false;
  let lore = [];
  try { lore = stack.getLore() ?? []; } catch { return false; }
  const next = upgradeLore(lore);
  const changed = next.some((l, i) => l !== lore[i]);
  if (changed) { try { stack.setLore(next); } catch { return false; } }
  const cm = next.map(recordCmOf).find(v => v !== undefined);
  if (cm !== undefined) setCmProperty(stack, cm);
  return changed;
}

/** CM_KEY on a stack that does not stack (fish do stack: their length lives in the lore line). */
function setCmProperty(stack, cm) {
  try { if (stack.maxAmount === 1 && stack.getDynamicProperty(CM_KEY) !== cm) stack.setDynamicProperty(CM_KEY, cm); } catch {}
}

/** Mark a stack as a record of `cm` (keeps its class mark and any other lines). */
export function setRecord(stack, cm) {
  let lore = [];
  try { lore = stack.getLore() ?? []; } catch {}
  const rest = lore.filter(l => recordCmOf(l) === undefined && !(typeof l === "string" && l.includes("★")));
  try { stack.setLore([...rest, recordLine(cm)]); } catch {}
  setCmProperty(stack, Math.round(Number(cm)));
  return stack;
}

// 1.5.0: a fish that grew up or was born in a fish pond (blocks/pond.js) is farmed, marked "✿" (no words, as the
// size marks). Farmed fish set no records and the fish merchant pays 60% for them.
export const FARMED_MARK = "§2✿";
/** Whether a stack is a farmed fish. */
export function isFarmed(stack) {
  try { return (stack.getLore() ?? []).some(l => typeof l === "string" && l.includes("✿")); } catch { return false; }
}

/** What a stack says about its size: { cls, cm?, record } (cls 0 = carries nothing). Reads the 1.6.0 record
 *  line, CM_KEY, and the old "★ N cm". */
export function readSize(stack) {
  let lore = [];
  try { lore = stack.getLore() ?? []; } catch {}
  let cls = 0, cm, record = false;
  for (const raw of lore) {
    const l = typeof raw === "string" ? raw : "";
    if (l.includes("★")) { record = true; const v = recordCmOf(l); if (v !== undefined) cm = v; continue; }
    const n = (l.match(/◆/g) ?? []).length;
    if (n >= 1 && n <= 3) cls = n;
  }
  if (cm === undefined) {
    try { const v = stack.getDynamicProperty?.(CM_KEY); if (typeof v === "number") { cm = v; record = true; } } catch {}
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
