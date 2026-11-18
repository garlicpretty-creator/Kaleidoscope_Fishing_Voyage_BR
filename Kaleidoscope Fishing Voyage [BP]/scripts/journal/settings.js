// ## The Angler's Journal settings page (1.5.0; its own file since 1.6.0).
// The one journal page that keeps words (docs/PLAN_1.6.0.md 4.2, decision 22.1 #8): it sets up the reeling
// minigame, which is the exception to the no-text rule, so it is listed as a permanent exception in
// tools/check_notext.py. Each player picks how the reeling track is drawn for them; an operator can turn the
// minigame off or on for the world (the /scriptevent command still works), and, since 1.6.0, the stations'
// animations (util/fx.js, section 12.3).
import { ActionFormData } from "@minecraft/server-ui";
import { charsetFor, minigameOn, setCharsetFor, setMinigame } from "../fishing/minigameSwitch.js";
import { animationsOn, setAnimations } from "../util/fx.js";
import { G } from "../data/glyphs.js";

const NS = "kaleidoscope_fishing";
const t = (key, ...with_) => with_.length ? { translate: `${NS}.journal.${key}`, with: with_.map(String) } : { translate: `${NS}.journal.${key}` };
const withGlyph = (g, m) => ({ rawtext: [{ text: `${g} ` }, m] });

/** Someone who may change a world setting: an operator. The API has named this differently over time, so ask every way. */
export function isOperator(player) {
  try { if (typeof player.commandPermissionLevel === "number") return player.commandPermissionLevel >= 1; } catch {}
  try { if (typeof player.playerPermissionLevel === "number") return player.playerPermissionLevel === 2; } catch {}
  try { if (typeof player.isOp === "function") return !!player.isOp(); } catch {}
  return false;
}

function pageSound(player) { try { player.playSound("item.book.page_turn", { volume: 0.8 }); } catch {} }

/** The settings page; `back` is called when the player leaves it with the back button. */
export async function showSettings(player, back = () => {}) {
  const op = isOperator(player);
  const mine = charsetFor(player);
  const body = { rawtext: [t("settings_charset", { block: "▕██ ▏", ascii: "[## ]" }[mine]), { text: "\n" },
    t(minigameOn() ? "settings_minigame_on" : "settings_minigame_off"), { text: "\n" },
    withGlyph(G["ui.animation"], t(animationsOn() ? "settings_anim_on" : "settings_anim_off")),
    ...(op ? [] : [{ text: "\n" }, t("settings_op_only")])] };
  const form = new ActionFormData().title(withGlyph(G["ui.gear"], t("settings"))).body(body);
  form.button(t(mine === "block" ? "settings_use_ascii" : "settings_use_block"));
  if (op) {
    form.button(t(minigameOn() ? "settings_turn_off" : "settings_turn_on"));
    form.button(withGlyph(G["ui.animation"], t(animationsOn() ? "settings_anim_turn_off" : "settings_anim_turn_on")));
  }
  form.button(t("back"));
  const res = await form.show(player);
  if (res.canceled || res.selection === undefined) return;
  pageSound(player);
  if (res.selection === 0) { setCharsetFor(player, mine === "block" ? "ascii" : "block"); return showSettings(player, back); }
  if (op && res.selection === 1) { setMinigame(!minigameOn()); return showSettings(player, back); }
  if (op && res.selection === 2) { setAnimations(!animationsOn()); return showSettings(player, back); }
  return back();
}
