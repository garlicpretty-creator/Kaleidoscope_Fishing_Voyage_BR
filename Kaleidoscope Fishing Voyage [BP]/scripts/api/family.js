// ## Kaleidoscope script role: handshakes with the sister packs (1.5.0).
// 森羅物語：草本 (Herbal), 豐收 (Harvest) and 樂牧 (Ranching) each speak the same kind of Script Event API as
// Cookery and as we do: `<namespace>:api_ping` is answered by `<namespace>:api_ready` with
// {"api":1,"version":"...","capabilities":[...]}, and a pack also sends api_ready by itself soon after load.
// We ping all three a second after load and act on whoever answers. Every one of them is optional: with none
// installed nothing is sent back, nothing is logged, and Fishing Voyage plays exactly as before.
// We never import their scripts and never depend on their pack UUIDs.
//
//   Herbal    capability "external_heat": our dishes get a warming / cooling value (HERBAL_HEAT), so eating crab
//             cools a player and a Nether soup warms them. Herbal answers with heat_ack; refusals are logged once.
//   Ranching  capability "register_feed": Fish Meal, Dried Fish and (with "feed_1_1") Dried Shrimp go in its
//             troughs (RANCHING_FEEDS). Ranching answers each with api_result. Ranching itself already takes our
//             Fish Offal and Fish Bones as feed and registers its own baits with us.
//   Harvest   1.0.0 has no api_ping / api_ready of its own (it talks to Cookery, Herbal, Ranching and Tavern, nobody
//             asks it anything). So we look for its items instead (harvestPresent): our dishes that use its crops are
//             sent to Cookery only when they exist (kc/bridge.js checks every ingredient). Should Harvest add an
//             api_ready later, it is remembered like the others.
//
// Registrations in the sister packs last for the world session, like ours: every api_ready sends them again.
import { ItemTypes, system } from "@minecraft/server";
import { HERBAL_HEAT, RANCHING_FEEDS } from "../data/generated.js";

const SOURCE = "kaleidoscope_fishing";
export const FAMILY = Object.freeze({ herbal: "kaleidoscope_herbal", harvest: "kaleidoscope_harvest", ranching: "kaleidoscope_ranching" });
const BATCH_CHARS = 1700;                    // a script event message holds 2048 characters

const info = new Map();                      // namespace -> the pack's api_ready payload
const warned = new Set();                    // one console line per refusal
/** The api_ready payload of a sister pack ({api, version, capabilities, ...}), or undefined if it has not answered. */
export const familyInfo = ns => info.get(ns);
/** Whether 森羅物語：豐收 is installed: it answered, or its items exist. */
export function harvestPresent() {
  if (info.has(FAMILY.harvest)) return true;
  try { return !!ItemTypes.get(`${FAMILY.harvest}:ginger`); } catch { return false; }
}
/** Tests only. */
export function _resetFamily() { info.clear(); warned.clear(); }

function send(id, message) {
  try { system.sendScriptEvent(id, typeof message === "string" ? message : JSON.stringify(message)); } catch {}
}
function warnOnce(text) {
  if (warned.has(text)) return;
  warned.add(text);
  try { console.warn(`[Fishing Voyage] ${text}`); } catch {}
}
const has = (m, capability) => Array.isArray(m?.capabilities) && m.capabilities.includes(capability);

// ------------------------------------------------------------------------------------------------ Herbal
function herbalReady(m) {
  if (!has(m, "external_heat")) return;
  const perMessage = Math.max(1, Math.min(32, Number(m.limits?.itemsPerMessage) || 32));
  let batch = [], length = 0;
  const flush = () => { if (batch.length) send(`${FAMILY.herbal}:heat_register`, { api: 1, source: SOURCE, items: batch }); batch = []; length = 0; };
  for (const [id, heat] of Object.entries(HERBAL_HEAT)) {
    const row = { id, heat }, cost = JSON.stringify(row).length + 1;
    if (batch.length >= perMessage || length + cost > BATCH_CHARS) flush();
    batch.push(row);
    length += cost;
  }
  flush();
}
function herbalAck(m) {
  if (m.to !== SOURCE) return;
  if (m.ok === false && m.code) warnOnce(`Herbal refused our heat values: ${m.code}`);
  for (const row of Array.isArray(m.rejected) ? m.rejected : []) warnOnce(`Herbal rejected the heat value of ${row?.id}: ${row?.code}`);
}

// ------------------------------------------------------------------------------------------------ Ranching
function ranchingReady(m) {
  if (!has(m, "register_feed")) return;
  for (const f of RANCHING_FEEDS) {
    if (f.needs && !has(m, f.needs)) continue;
    send(`${FAMILY.ranching}:register_feed`, { item: f.item, kind: f.kind, units: f.units });   // one registration per message
  }
}
function ranchingResult(m) {
  if (typeof m.id !== "string" || !m.id.startsWith(`${SOURCE}:`) || m.ok !== false) return;
  warnOnce(`Ranching refused ${m.event ?? "a registration"} for ${m.id}: ${m.error ?? "no reason given"}`);
}

// ------------------------------------------------------------------------------------------------ the handshake
const READY = { [FAMILY.herbal]: herbalReady, [FAMILY.ranching]: ranchingReady, [FAMILY.harvest]: () => {} };

/** Handle one script event from a sister pack; returns true for an api_ready we acted on. Exported for tests. */
export function onFamilyEvent(ev) {
  const id = String(ev?.id ?? ""), cut = id.indexOf(":");
  const ns = id.slice(0, cut), name = id.slice(cut + 1);
  if (!READY[ns]) return false;
  let m;
  try { m = JSON.parse(String(ev.message ?? "")); } catch { return false; }
  if (!m || typeof m !== "object") return false;
  if (name === "api_ready") {
    if (Number(m.api) !== 1) return false;               // a later, incompatible API: leave it alone
    const first = !info.has(ns);
    info.set(ns, m);
    READY[ns](m);
    if (first) { try { console.info(`[Fishing Voyage] ${ns} ${m.version ?? "?"} answered`); } catch {} }
    return true;
  }
  if (ns === FAMILY.herbal && name === "heat_ack") herbalAck(m);
  else if (ns === FAMILY.ranching && name === "api_result") ranchingResult(m);
  return false;
}

/** Ask the sister packs to (re)send api_ready; harmless when one is not installed. */
export function pingFamily() {
  for (const ns of Object.values(FAMILY)) send(`${ns}:api_ping`, SOURCE);
}

system.afterEvents.scriptEventReceive.subscribe(ev => { try { onFamilyEvent(ev); } catch (err) { warnOnce(`${ev?.id}: ${err}`); } },
  { namespaces: Object.values(FAMILY) });
system.runTimeout(pingFamily, 20);
system.runTimeout(() => { try { if (harvestPresent()) console.info("[Fishing Voyage] kaleidoscope_harvest found (by its items): its dishes are on"); } catch {} }, 40);
