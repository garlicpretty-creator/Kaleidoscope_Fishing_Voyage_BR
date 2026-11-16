// ## Angler's Journal: a book the player opens (same kind of UI as Cookery's guidebook).
// All text comes from the resource pack's lang files, so it follows the game language.
// v1.4: the index lists the waters (JOURNAL_SPECIES[].group) instead of every species; each water
// has its own page. Records and recipe pages are unchanged.
import { world, system } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";
import { JOURNAL_SPECIES } from "../data/generated.js";
import { getRecords } from "./records.js";
import { moonPhase, tideState } from "../fishing/water.js";
import { showRecipes } from "./recipes.js";
import { orderNear, wantsNear } from "../world/merchant.js";
import { charsetFor, minigameOn, setCharsetFor, setMinigame } from "../fishing/minigameSwitch.js";

const NS = "kaleidoscope_fishing";
const JOURNAL = `${NS}:angler_journal`;
const t = (key, ...with_) => with_.length ? { translate: `${NS}.journal.${key}`, with: with_.map(String) } : { translate: `${NS}.journal.${key}` };
const nameOf = sp => ({ translate: `${NS}.name.${sp.key}` });
const UNKNOWN_ICON = "textures/items/kfv_unknown_fish";
const GROUP_ORDER = ["freshwater", "wetland", "sea", "ice", "lava", "end", "cave", "legend"];
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
  if (res.selection === GROUPS.length + 2) return showSettings(player);
  return showGroup(player, GROUPS[res.selection - 2]);
}

/** Someone who may change a world setting: an operator. The API has named this differently over time, so ask every way. */
export function isOperator(player) {
  try { if (typeof player.commandPermissionLevel === "number") return player.commandPermissionLevel >= 1; } catch {}
  try { if (typeof player.playerPermissionLevel === "number") return player.playerPermissionLevel === 2; } catch {}
  try { if (typeof player.isOp === "function") return !!player.isOp(); } catch {}
  return false;
}

// 1.5.0: settings without commands. Each player picks how the reeling track is drawn for them; an operator can
// turn the minigame off or on for the world. The /scriptevent command still works.
async function showSettings(player) {
  const op = isOperator(player);
  const mine = charsetFor(player);
  const body = { rawtext: [t("settings_charset", { block: "▕██ ▏", ascii: "[## ]" }[mine]), { text: "\n" },
    t(minigameOn() ? "settings_minigame_on" : "settings_minigame_off"), ...(op ? [] : [{ text: "\n" }, t("settings_op_only")])] };
  const form = new ActionFormData().title(t("settings")).body(body);
  form.button(t(mine === "block" ? "settings_use_ascii" : "settings_use_block"));
  if (op) form.button(t(minigameOn() ? "settings_turn_off" : "settings_turn_on"));
  form.button(t("back"));
  const res = await form.show(player);
  if (res.canceled || res.selection === undefined) return;
  pageSound(player);
  if (res.selection === 0) { setCharsetFor(player, mine === "block" ? "ascii" : "block"); return showSettings(player); }
  if (op && res.selection === 1) { setMinigame(!minigameOn()); return showSettings(player); }
  return showIndex(player);
}

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
async function showTide(player) {
  const body = { rawtext: [] };
  const line = m => { body.rawtext.push(m, { text: "\n" }); };
  const tw = (key, inner) => ({ translate: `${NS}.journal.${key}`, with: { rawtext: [{ translate: `${NS}.journal.${inner}` }] } });
  line(tw("tide_now", `tide_${tideState()}`));
  line(tw("moon_now", `moon_${moonPhase()}`));
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
  const res = await new ActionFormData().title(t("tide")).body(body).button(t("back")).show(player);
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
