// ## Angler's Journal: a book the player opens (same kind of UI as Cookery's guidebook).
// All text comes from the resource pack's lang files, so it follows the game language.
// v1.4: the index lists the waters (JOURNAL_SPECIES[].group) instead of every species; each water
// has its own page. Records and recipe pages are unchanged.
import { ItemStack, world, system } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";
import { JOURNAL_SPECIES } from "../data/generated.js";
import { getRecords } from "./records.js";
import { moonPhase, tideState } from "../fishing/water.js";
import { showRecipes } from "./recipes.js";
import { orderNear, wantsNear } from "../world/merchant.js";
import { charsetFor, minigameOn, setCharsetFor, setMinigame } from "../fishing/minigameSwitch.js";
import { spawnParticle } from "../util/particles.js";

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

// 1.4.0: a water whose every species you have caught is complete: its page is marked and gives a reward once.
const CLAIMED = `${NS}:journal_claimed`;
const REWARD = {
  freshwater: [`${NS}:recipe_scrap`, 2], wetland: [`${NS}:live_shrimp`, 16], sea: [`${NS}:glow_bobber`, 1],
  ice: [`${NS}:tip_up`, 2], lava: [`${NS}:wire_line`, 1], end: [`${NS}:end_maggot`, 16], cave: [`${NS}:glow_line`, 1],
  legend: [`${NS}:gold_hook`, 1],
};
const completeIn = (rec, group) => { const list = speciesOf(group); return list.length > 0 && list.every(sp => rec[sp.id]); };
function claimed(player) {
  try { const v = JSON.parse(player.getDynamicProperty(CLAIMED) ?? "[]"); return Array.isArray(v) ? v : []; } catch { return []; }
}
/** Hand over a completed water's reward the first time its page is opened; true if it was given now. */
function claim(player, group) {
  const had = claimed(player);
  if (had.includes(group) || !REWARD[group]) return false;
  try { player.setDynamicProperty(CLAIMED, JSON.stringify([...had, group])); } catch { return false; }
  const stack = new ItemStack(REWARD[group][0], REWARD[group][1]);
  try { const rest = player.getComponent("minecraft:inventory")?.container?.addItem(stack); if (rest) player.dimension.spawnItem(rest, player.location); }
  catch { try { player.dimension.spawnItem(stack, player.location); } catch {} }
  try { player.playSound("random.levelup", { pitch: 1.2, volume: 0.6 }); } catch {}
  const l = player.location;
  for (let i = 0; i < 8; i++) {
    try { spawnParticle(player.dimension, "minecraft:villager_happy", { x: l.x + (Math.random() - 0.5), y: l.y + 1.2 + Math.random() * 0.6, z: l.z + (Math.random() - 0.5) }); } catch {}
  }
  return true;
}
const MARK = { text: "§6✔§r " };

function isOperator(player) {
  try { const lvl = player.playerPermissionLevel; if (lvl !== undefined) return lvl === 2 || lvl === "Operator"; } catch {}
  try { return typeof player.isOp === "function" && player.isOp(); } catch { return false; }
}

function pageSound(player) { try { player.playSound("item.book.page_turn", { volume: 0.8 }); } catch {} }

async function showIndex(player) {
  const rec = getRecords(player);
  const caught = JOURNAL_SPECIES.filter(sp => rec[sp.id]).length;
  const form = new ActionFormData()
    .title(completeIn(rec, "legend") ? { rawtext: [t("title"), { text: " §6✦" }] } : t("title"))
    .body(t("summary", caught, JOURNAL_SPECIES.length));
  form.button(t("recipes"), "textures/ui/kfv_book/kfv_cat_recipes");
  form.button(t("tide"), "textures/ui/kfv_book/kfv_tide");
  form.button(t("settings"), "textures/ui/kfv_book/kfv_cat_tools");
  for (const g of GROUPS) form.button(completeIn(rec, g) ? { rawtext: [MARK, t(`group_${g}`)] } : t(`group_${g}`), groupIcon(g));
  form.button(t("close"));
  const res = await form.show(player);
  if (res.canceled || res.selection === undefined || res.selection > GROUPS.length + 2) return;
  pageSound(player);
  if (res.selection === 0) return showRecipes(player, () => showIndex(player));
  if (res.selection === 1) return showTide(player);
  if (res.selection === 2) return showSettings(player);
  return showGroup(player, GROUPS[res.selection - 3]);
}

// v1.4: one page per water, listing its species.
async function showGroup(player, group) {
  const rec = getRecords(player);
  const list = speciesOf(group);
  const caught = list.filter(sp => rec[sp.id]).length;
  const complete = completeIn(rec, group);
  const rewarded = complete && claim(player, group);
  const body = { rawtext: [t("group_summary", caught, list.length)] };
  if (complete) body.rawtext.push({ text: "\n" }, MARK, t(rewarded ? "group_reward" : "group_complete"));
  const form = new ActionFormData()
    .title(t(`group_${group}`))
    .body(body);
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

// 1.4.0: settings. The HUD charset is each player's own; the minigame switch is the world's, for operators.
async function showSettings(player) {
  const ascii = charsetFor(player) === "ascii", op = isOperator(player);
  const form = new ActionFormData().title(t("settings")).body(t("settings_body"))
    .button(t(ascii ? "set_charset_ascii" : "set_charset_block"));
  if (op) form.button(t(minigameOn() ? "set_minigame_on" : "set_minigame_off"));
  form.button(t("back"));
  const res = await form.show(player);
  if (res.canceled || res.selection === undefined) return;
  pageSound(player);
  if (res.selection === 0) { setCharsetFor(player, ascii ? "block" : "ascii"); return showSettings(player); }
  if (op && res.selection === 1) { setMinigame(!minigameOn()); return showSettings(player); }
  return showIndex(player);
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
  // 1.4.0: his order, and how far you are with it
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
