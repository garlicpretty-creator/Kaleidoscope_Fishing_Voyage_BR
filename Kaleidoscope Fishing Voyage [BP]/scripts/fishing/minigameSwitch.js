// ## Fishing minigame switch (v1.5): world-wide on/off and the HUD charset, kept in a world property.
//   /scriptevent kaleidoscope_fishing:minigame on | off | status | charset block | charset ascii
// Off = the 1.4 behaviour (tug-of-war reeling, or landing at once). Commands need command permission,
// so only operators can change it. Read once and cached; every change is saved at once.
import { system, world } from "@minecraft/server";

const NS = "kaleidoscope_fishing";
const KEY = `${NS}:minigame`;
const EVENT = `${NS}:minigame`;
export const DEFAULTS = { on: true, charset: "block" };
let cfg;

function load() {
  if (cfg) return cfg;
  cfg = { ...DEFAULTS };
  try { const v = JSON.parse(world.getDynamicProperty(KEY) ?? "null"); if (v && typeof v === "object") cfg = { ...cfg, ...v }; } catch {}
  return cfg;
}
function save() { try { world.setDynamicProperty(KEY, JSON.stringify(cfg)); } catch {} }

export const minigameOn = () => load().on !== false;
export const charset = () => load().charset;

/** Apply one command line; returns the reply text (or undefined when the line is not understood). */
export function command(message) {
  const [verb, arg] = String(message ?? "").trim().toLowerCase().split(/\s+/);
  load();
  if (verb === "on" || verb === "off") { cfg.on = verb === "on"; save(); }
  else if (verb === "charset" && (arg === "block" || arg === "ascii")) { cfg.charset = arg; save(); }
  else if (verb !== "status") return undefined;
  return `fishing minigame: ${cfg.on ? "on" : "off"}, charset ${cfg.charset}`;
}

system.afterEvents.scriptEventReceive.subscribe(ev => {
  if (ev.id !== EVENT) return;
  const reply = command(ev.message) ?? "usage: on | off | status | charset block | charset ascii";
  try { ev.sourceEntity?.sendMessage?.(reply); } catch {}
  try { console.info(`[Fishing Voyage] ${reply}`); } catch {}
});
