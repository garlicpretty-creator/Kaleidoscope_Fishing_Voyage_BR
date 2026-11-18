// ## Angler's Journal: a book the player opens (same kind of UI as Cookery's guidebook).
// v1.4: the index lists the waters (JOURNAL_SPECIES[].group) instead of every species; each water has its own page.
// 1.6.0 (docs/PLAN_1.6.0.md section 6): a picture book. Every page is glyph characters only (journal/book.js):
//   index    a 60-cell strip of the species (caught: the fish, not yet: its shadow); a water glyph per group,
//            the pot (recipes), the tide clock and the gear (settings, journal/settings.js: the one page with words)
//   group    one button per species, fish or shadow
//   species  one row read from the data (6.3): waters, time, weather, tide, moon, sky, the rod it needs (and a
//            legend's hook / line), liked baits, times caught (dots, a star past five), best size ◆ / ◆◆ / ◆◆◆ (★ record)
//   tide     tide, moon, tonight's sky (from dusk), the merchant's two wanted fish, his order and your progress
import { world, system } from "@minecraft/server";
import { JOURNAL_SPECIES, RODS } from "../data/generated.js";
import { G, glyph, fishGlyph as ownFishGlyph, shadowGlyph as ownShadowGlyph, itemGlyph, dots } from "../data/glyphs.js";
import { glyphLikeOf } from "../fishing/registry.js";
import { getRecords } from "./records.js";
import { moonPhase, tideState } from "../fishing/water.js";
import { CATCH_BY_ID } from "../fishing/loot.js";
import { classOf } from "../fishing/size.js";
import { showRecipes } from "./recipes.js";
import { orderNear, wantsNear } from "../world/merchant.js";
import { skyTonight } from "../world/sky.js";
import { showSettings, isOperator } from "./settings.js";
import { pageSound, showPaged, showPlain } from "./book.js";

export { isOperator };
// 1.6.0 (plan 15): a catch another pack registered has no glyph of its own (the sheet is a picture in the resource
// pack); with register_catch "like" it borrows that fish's glyph and shadow, else it gets the generic fish shadow.
export const fishGlyph = id => ownFishGlyph(glyphLikeOf(id) ?? id);
export const shadowGlyph = id => ownShadowGlyph(glyphLikeOf(id) ?? id);
const JOURNAL = "kaleidoscope_fishing:angler_journal";
const UNKNOWN_ICON = "textures/items/kfv_unknown_fish";
const GROUP_ORDER = ["freshwater", "wetland", "sea", "ice", "lava", "end", "cave", "secret", "sky", "legend"];   // 1.5.0: hidden waters, sky
// groups in page order: the known ones first, then any group the data adds later
export const GROUPS = [...GROUP_ORDER, ...JOURNAL_SPECIES.map(sp => sp.group ?? "freshwater")]
  .filter((g, i, a) => a.indexOf(g) === i && JOURNAL_SPECIES.some(sp => (sp.group ?? "freshwater") === g));
const speciesOf = group => JOURNAL_SPECIES.filter(sp => (sp.group ?? "freshwater") === group);
const groupIcon = group => {
  const sp = speciesOf(group)[0];
  return sp ? sp.icon : UNKNOWN_ICON;
};
// the picture of each group's button: the water it stands for (legends: their own sign ✦)
const GROUP_GLYPH = {
  freshwater: "water.river", wetland: "water.estuary", sea: "water.ocean", ice: "water.ice", lava: "water.lava",
  end: "water.end_pond", cave: "water.cave", secret: "water.mushroom", sky: "sky.meteor",
};
/** A group's glyph; a group the data adds later takes its first species' first water. */
export function groupGlyph(group) {
  if (group === "legend") return "✦";
  if (GROUP_GLYPH[group]) return G[GROUP_GLYPH[group]];
  const w = CATCH_BY_ID[speciesOf(group)[0]?.id]?.waters?.[0];
  return glyph(w ? `water.${w}` : "fish.unknown");
}
const STRIP_ROW = 10;
/** A row of fish: caught ones as their picture, the rest as their shadow, STRIP_ROW to a line. */
export function strip(list, rec) {
  let s = "";
  list.forEach((sp, i) => { s += (i && i % STRIP_ROW === 0 ? "\n" : "") + (rec[sp.id] ? fishGlyph(sp.id) : shadowGlyph(sp.id)); });
  return s;
}

async function showIndex(player) {
  const rec = getRecords(player);
  const items = [
    { text: G["ui.recipes"], icon: "textures/ui/kfv_book/kfv_cat_recipes", go: () => showRecipes(player, () => showIndex(player)) },
    { text: G["ui.tide_clock"], icon: "textures/ui/kfv_book/kfv_tide", go: () => showTide(player) },
    ...GROUPS.map(g => ({ text: groupGlyph(g) + (speciesOf(g).every(sp => rec[sp.id]) ? ` ${G["mark.tick"]}` : ""), icon: groupIcon(g), go: () => showGroup(player, g) })),
    { text: G["ui.gear"], go: () => showSettings(player, () => showIndex(player)) },
  ];
  const res = await showPaged(player, { body: strip(JOURNAL_SPECIES, rec), items, back: false });
  if (res?.pick !== undefined) return items[res.pick].go();
}

// v1.4: one page per water, listing its species.
async function showGroup(player, group, page = 0) {
  const rec = getRecords(player);
  const list = speciesOf(group);
  const items = list.map(sp => (rec[sp.id] ? { text: fishGlyph(sp.id), icon: sp.icon } : { text: shadowGlyph(sp.id), icon: UNKNOWN_ICON }));
  const res = await showPaged(player, { body: groupGlyph(group), items, page });
  if (!res) return;
  if (res.back) return showIndex(player);
  return showSpecies(player, list[res.pick], () => showGroup(player, group, res.page));
}

// ------------------------------------------------------------------ the species row (6.3), from the data
const SLOT = s => G[`time.${s}`];
const uniq = a => a.filter((x, i) => x && a.indexOf(x) === i);
/** The lowest rod that can land it: tier from `tier` / `req.tier`; the lava rod for lava only, the ender rod for the void only. */
export function minRod(e) {
  const reach = [...(e.waters ?? []), ...Object.values(e.sky_waters ?? {}).flat()];
  const lava = reach.length > 0 && reach.every(w => w === "lava");
  const isVoid = reach.length > 0 && reach.every(w => w === "void");
  const tier = Math.max(1, e.tier ?? 1, e.req?.tier ?? 1);
  const fits = Object.entries(RODS).filter(([, r]) => (r.tier ?? 1) >= tier && (!lava || r.lava) && (!isVoid || r.void));
  fits.sort(([, a], [, b]) => (a.tier ?? 1) - (b.tier ?? 1) || (!!a.lava + !!a.void) - (!!b.lava + !!b.void));
  return fits[0]?.[0];
}
/**
 * The species page's row: one string per kind of fact, empty kinds left out.
 * Returns { waters, time, weather, tide, moon, sky, rod, bait, times, size } (each a glyph string, or "").
 */
export function speciesFacts(id, r) {
  const e = CATCH_BY_ID[id] ?? {};
  const q = e.req ?? {};
  const f = {};
  f.waters = (e.waters ?? []).slice(0, 4).map(w => glyph(`water.${w}`, "item.unknown")).join("");
  const slots = q.slots ?? e.slots;
  let time;
  if (slots) time = slots.map(SLOT);
  else {
    time = [SLOT(e.time === "day" || e.time === "night" ? e.time : "any")];
    if (e.dawn_dusk) time = e.time ? [...time, SLOT("dawn"), SLOT("dusk")] : [SLOT("dawn"), SLOT("dusk")];
  }
  f.time = time.join("");
  f.weather = q.weather === "thunder" ? G["weather.thunder"] : (q.weather === "rain" || e.rain) ? G["weather.rain"] : "";
  f.tide = uniq([q.tide, ...Object.keys(e.tide ?? {})]).map(t => glyph(`tide.${t}`, "")).join("");
  const moons = uniq([...(e.moon === "full" ? [0] : Array.isArray(e.moon) ? e.moon : []), ...(q.moon ?? [])].map(String));
  f.moon = moons.map(m => glyph(`moon.${m}`, "")).join("");
  f.sky = uniq([e.sky, q.sky, q.sky_moon, ...Object.keys(e.sky_waters ?? {})]).map(s => glyph(`sky.${s}`, "")).join("");
  const rod = minRod(e);
  f.rod = [rod, q.hook, q.line].filter(Boolean).map(x => itemGlyph(x)).join("");
  const liked = Object.entries(e.bait ?? {}).sort((a, b) => b[1] - a[1]).map(([b]) => b);
  f.bait = uniq([q.bait, ...(e.needBait ?? []), ...liked]).slice(0, 3).map(b => itemGlyph(b)).join("");
  const n = r?.n ?? 0;
  f.times = n > 0 ? dots(Math.min(n, 5), 5) + (n > 5 ? G["mark.star"] : "") : "";
  f.size = r && r.b !== undefined && e.size ? "◆".repeat(classOf(id, r.b)) + (r.r ? "★" : "") : "";
  return f;
}
export const FACT_ORDER = ["waters", "time", "weather", "tide", "moon", "sky", "rod", "bait", "times", "size"];
/** The species page body: the fish (or its shadow) over the row of facts. */
export function speciesBody(sp, r) {
  const f = speciesFacts(sp.id, r);
  return `${r ? fishGlyph(sp.id) : shadowGlyph(sp.id)}\n\n${FACT_ORDER.map(k => f[k]).filter(Boolean).join("  ")}`;
}

async function showSpecies(player, sp, back = () => showIndex(player)) {
  if (await showPlain(player, speciesBody(sp, getRecords(player)[sp.id]))) return back();
}

// ------------------------------------------------------------------ v1.3: the tide page (6.5)
/** The tide page body: tide, moon and tonight's sky; the merchant's wanted fish; his order and how far you are. */
export function tideBody(player) {
  const lines = [[glyph(`tide.${tideState()}`, ""), glyph(`moon.${moonPhase()}`, ""), skyTonight() ? glyph(`sky.${skyTonight()}`, "") : ""].filter(Boolean).join("  ")];
  const wants = wantsNear(player);                       // v1.4: what the fish merchant wants today, if one is about
  if (wants?.length) lines.push(`${G["ui.merchant"]}  ${wants.map(fishGlyph).join(" ")}`);
  const order = orderNear(player);                       // 1.5.0: his order, and how far you are with it
  if (order) lines.push(`${fishGlyph(order.id)}${order.min ? " " + "◆".repeat(order.min) : ""}  ${order.have >= order.n ? G["mark.tick"] : dots(order.have, order.n)}`);
  return lines.join("\n\n");
}

async function showTide(player) {
  if (await showPlain(player, tideBody(player))) return showIndex(player);
}

world.afterEvents.itemUse.subscribe(ev => {
  if (ev.itemStack?.typeId !== JOURNAL || !ev.source) return;
  const player = ev.source;
  pageSound(player);
  system.run(() => showIndex(player).catch(() => {}));
});
