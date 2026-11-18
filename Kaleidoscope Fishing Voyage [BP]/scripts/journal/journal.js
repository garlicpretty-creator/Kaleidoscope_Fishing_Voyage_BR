// ## Angler's Journal: a book the player opens (same kind of UI as Cookery's guidebook).
// All text comes from the resource pack's lang files, so it follows the game language.
// v1.4: the index lists the waters (JOURNAL_SPECIES[].group) instead of every species; each water
// has its own page. Records and recipe pages are unchanged.
// 1.6.0 tried a picture book of glyphs only; in game it read worse than words, so the pages are words again
// (2026-11-18). The settings page lives in journal/settings.js (it gained the operator's animation switch).
import { world, system } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";
import { JOURNAL_SPECIES } from "../data/generated.js";
import { getRecords } from "./records.js";
import { moonPhase, tideState } from "../fishing/water.js";
import { showRecipes } from "./recipes.js";
import { orderNear, wantsNear } from "../world/merchant.js";
import { skyTonight } from "../world/sky.js";
import { showSettings, isOperator } from "./settings.js";

const NS = "kaleidoscope_fishing";
const JOURNAL = `${NS}:angler_journal`;
const t = (key, ...with_) => with_.length ? { translate: `${NS}.journal.${key}`, with: with_.map(String) } : { translate: `${NS}.journal.${key}` };
const nameOf = sp => ({ translate: `${NS}.name.${sp.key}` });
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

function pageSound(player) { try { player.playSound("item.book.page_turn", { volume: 0.8 }); } catch {} }

async function showIndex(player) {
  const rec = getRecords(player);
  const caught = JOURNAL_SPECIES.filter(sp => rec[sp.id]).length;
  const form = new ActionFormData()
    .title(t("title"))
    .body(t("summary", caught, JOURNAL_SPECIES.length));
  form.button(t("recipes"), "textures/ui/kfv_book/kfv_cat_recipes");
  form.button(t("tide"), "textures/ui/kfv_book/kfv_tide");
  for (const g of GROUPS) form.button(t(`group_${g}`), groupIcon(g));
  form.button(t("settings"));
  form.button(t("close"));
  const res = await form.show(player);
  if (res.canceled || res.selection === undefined || res.selection > GROUPS.length + 2) return;
  pageSound(player);
  if (res.selection === 0) return showRecipes(player, () => showIndex(player));
  if (res.selection === 1) return showTide(player);
  if (res.selection === GROUPS.length + 2) return showSettings(player, () => showIndex(player));
  return showGroup(player, GROUPS[res.selection - 2]);
}

export { isOperator };

// v1.4: one page per water, listing its species.
async function showGroup(player, group) {
  const rec = getRecords(player);
  const list = speciesOf(group);
  const caught = list.filter(sp => rec[sp.id]).length;
  const form = new ActionFormData()
    .title(t(`group_${group}`))
    .body(t("group_summary", caught, list.length));
  for (const sp of list) {
    const known = !!rec[sp.id];
    form.button(known ? nameOf(sp) : t("unknown"), known ? sp.icon : UNKNOWN_ICON);
  }
  form.button(t("back"));
  const res = await form.show(player);
  if (res.canceled || res.selection === undefined) return;
  pageSound(player);
  if (res.selection >= list.length) return showIndex(player);
  return showSpecies(player, list[res.selection], () => showGroup(player, group));
}

// v1.3: the tide and the moon tonight, and what they change.
/** The tide page's text (a rawtext message): tide, moon, tonight's sky, the merchant's wants and order, the help. */
export function tideBody(player) {
  const body = { rawtext: [] };
  const line = m => { body.rawtext.push(m, { text: "\n" }); };
  const tw = (key, inner) => ({ translate: `${NS}.journal.${key}`, with: { rawtext: [{ translate: `${NS}.journal.${inner}` }] } });
  line(tw("tide_now", `tide_${tideState()}`));
  line(tw("moon_now", `moon_${moonPhase()}`));
  const sky = skyTonight();                             // 1.5.0: only from dusk, only on a night that has one
  if (sky) line(t(`sky_${sky}`));
  // v1.4: what the fish merchant wants today, if one is about
  const wants = wantsNear(player);
  if (wants === undefined) line(t("market_none"));
  else line({ rawtext: [t("market_wants"), ...wants.flatMap((id, i) => [{ text: i ? "、" : "" }, { translate: `${NS}.name.${id.split(":")[1]}` }])] });
  // 1.5.0: his order, and how far you are with it
  const order = orderNear(player);
  if (order) {
    line({ rawtext: [t("market_order"), { translate: `${NS}.name.${order.id.split(":")[1]}` }, { text: ` ×${order.n}` },
      ...(order.min ? [t("order_medium")] : []), { text: "  " },
      order.have >= order.n ? t("order_done") : t("order_progress", order.have, order.n)] });
  }
  line({ text: "" });
  line(t("tide_help_high"));
  line(t("tide_help_low"));
  line(t("tide_help_moon"));
  line({ text: "" });
  line(t("end_hint"));
  return body;
}

async function showTide(player) {
  const res = await new ActionFormData().title(t("tide")).body(tideBody(player)).button(t("back")).show(player);
  if (!res.canceled) { pageSound(player); return showIndex(player); }
}

async function showSpecies(player, sp, back = () => showIndex(player)) {
  const r = getRecords(player)[sp.id];
  const body = { rawtext: [] };
  const line = m => { body.rawtext.push(m, { text: "\n" }); };
  line({ rawtext: [t("where"), { translate: `${NS}.habitat.${sp.key}` }] });
  line({ text: "" });
  if (r) {
    line(t("times", r.n ?? 0));
    if (sp.sized) line(r.b !== undefined ? t("best", r.b) : t("no_size"));
  } else {
    line(t("not_yet"));
  }
  const form = new ActionFormData()
    .title(r ? nameOf(sp) : t("unknown"))
    .body(body)
    .button(t("back"));
  const res = await form.show(player);
  if (!res.canceled) { pageSound(player); return back(); }
}

world.afterEvents.itemUse.subscribe(ev => {
  if (ev.itemStack?.typeId !== JOURNAL || !ev.source) return;
  const player = ev.source;
  pageSound(player);
  system.run(() => showIndex(player).catch(() => {}));
});
