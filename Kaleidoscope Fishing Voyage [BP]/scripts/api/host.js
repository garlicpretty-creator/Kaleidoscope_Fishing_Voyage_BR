// ## Kaleidoscope script role: what other packs can hear and ask (1.5.0).
// fishing/registry.js takes registrations (baits, catches, prices). This file is the other half of the public
// API: a broadcast of what happens here, and three questions any pack may ask. Same envelope as the registry and
// as the sister packs (Herbal, Ranching): script events carrying one line of JSON, at most 2048 characters.
//
//   out  kaleidoscope_fishing:evt             {"v":1,"t":"<event>","p":"<player.id>",...}        capability "events"
//          caught   id, via ("rod" | "tip_up"), size? (cm), cls (0 none, 1 small, 2 medium, 3 large),
//                   legend, first (first of its species for this player), record (a new personal best)
//          cleaned  id            the last cut of a fish on the Fish Cleaning Board
//          sold     id, n, paid   fish sold to the Fish Merchant (paid in emeralds)
//          order_filled  id, n   the player handed in the last fish of the merchant's order
//          tide     state ("high" | "low")   world event, no "p": the tide turned
//          sky      kind ("meteor" | "aurora"), phase ("start" at dusk | "end" at dawn), dim   world event   "sky"
//   in   kaleidoscope_fishing:state_request   {"api":1,"source":"<ns>","req"?}                   capability "state"
//   out  kaleidoscope_fishing:state           {"api":1,"to":"<ns>","req"?,"ok":true,"tide","moon","slot","day","sky"}
//   in   kaleidoscope_fishing:record_request  {"api":1,"source":"<ns>","req"?,"p":"<player.id>","id"?}   "records"
//   out  kaleidoscope_fishing:record          with "id": {"ok":true,"id","n","best"?}
//                                             without: {"ok":true,"caught","total","legends","legendTotal"}
//   in   kaleidoscope_fishing:catalog_request {"api":1,"source":"<ns>","req"?,"kind":"catches"|"baits"}  "catalog"
//   out  kaleidoscope_fishing:catalog         {"ok":true,"kind","index","parts","items":[...]}  (may come in parts)
//
// Replies are broadcasts: they carry "to" (the asker's source) and give back "req" unchanged, so a pack handles
// only its own. A request with a bad envelope gets no answer. New things only ever add a capability or an event;
// the meaning of an existing field does not change within api 1.
import { system, world } from "@minecraft/server";
import { CATCHES, JOURNAL_SPECIES, LEGENDS } from "../data/generated.js";
import { getRecords } from "../journal/records.js";
import { moonPhase, tideState, timeSlot } from "../fishing/water.js";
import { BAITS, LURE } from "../fishing/loot.js";
import { API, SOURCE, externalCatches } from "../fishing/registry.js";
import { skyTonight } from "../world/sky.js";

export const EVT = `${SOURCE}:evt`;
const REQ = { state: `${SOURCE}:state_request`, record: `${SOURCE}:record_request`, catalog: `${SOURCE}:catalog_request` };
const PART_CHARS = 1500;                       // items per catalog message stay well inside the 2048 limit
const LEGEND = new Set(LEGENDS ?? []);
const GROUP = Object.fromEntries(JOURNAL_SPECIES.map(sp => [sp.id, sp.group]));

function send(id, body) {
  try { system.sendScriptEvent(id, JSON.stringify(body)); } catch {}
}

/** Broadcast one event. `player` may be undefined for a world event (the tide). Never throws. */
export function emit(t, player, extra = {}) {
  let p;
  try { p = player?.id; } catch {}
  send(EVT, { v: 1, t, ...(p !== undefined ? { p } : {}), ...extra });
}

/** A landed catch, from the rod or a tip-up. */
export function emitCaught(player, id, { via, size, cls, rec }) {
  emit("caught", player, { id, via, ...(size !== undefined ? { size } : {}), cls: cls ?? 0,
    legend: LEGEND.has(id), first: !!rec?.first, record: !!rec?.newBest });
}

// ------------------------------------------------------------------------------------------------ requests
function parse(message) {
  let m;
  try { m = JSON.parse(String(message ?? "")); } catch { return undefined; }
  if (!m || typeof m !== "object" || Number(m.api) !== API) return undefined;
  if (typeof m.source !== "string" || !/^[a-z0-9_.-]{1,64}$/.test(m.source) || m.source === SOURCE) return undefined;
  return m;
}
function reply(name, m, body) {
  const req = (typeof m.req === "string" || typeof m.req === "number") && String(m.req).length <= 32 ? { req: m.req } : {};
  send(`${SOURCE}:${name}`, { api: API, to: m.source, ...req, ...body });
}
function playerOf(id) {
  if (typeof id !== "string") return undefined;
  try { const e = world.getEntity(id); return e?.isValid && e.typeId === "minecraft:player" ? e : undefined; } catch { return undefined; }
}

function state(m) {
  let day = 0;
  try { day = world.getDay(); } catch {}
  reply("state", m, { ok: true, tide: tideState(), moon: moonPhase(), slot: timeSlot(), day, sky: skyTonight() || "none" });
}

function record(m) {
  const player = playerOf(m.p);
  if (!player) return reply("record", m, { p: m.p, ok: false, code: "NO_PLAYER" });
  const rec = getRecords(player);
  if (m.id !== undefined) {
    if (typeof m.id !== "string") return reply("record", m, { p: m.p, ok: false, code: "BAD_ID" });
    const r = rec[m.id];
    return reply("record", m, { p: m.p, ok: true, id: m.id, n: r?.n ?? 0, ...(r?.b !== undefined ? { best: r.b } : {}) });
  }
  const caught = JOURNAL_SPECIES.filter(sp => rec[sp.id]);
  reply("record", m, { p: m.p, ok: true, caught: caught.length, total: JOURNAL_SPECIES.length,
    legends: caught.filter(sp => LEGEND.has(sp.id)).length, legendTotal: LEGEND.size });
}

const KINDS = {
  catches: () => [
    ...CATCHES.map(c => ({ id: c.id, waters: c.waters ?? [], ...(GROUP[c.id] ? { group: GROUP[c.id] } : {}),
      ...(c.size ? { size: c.size } : {}), ...(LEGEND.has(c.id) ? { legend: true } : {}), ...(c.sky ? { sky: c.sky } : {}) })),
    ...externalCatches().map(c => ({ id: c.id, waters: c.waters ?? [], ...(c.size ? { size: c.size } : {}), ...(c.sky ? { sky: c.sky } : {}), source: c.source })),
  ],
  baits: () => Object.entries(BAITS).filter(([id]) => id !== LURE)
    .map(([id, b]) => ({ id, biteFactor: b.biteFactor, ...(b.source ? { source: b.source } : {}) })),
};
function catalog(m) {
  const make = KINDS[m.kind];
  if (!make) return reply("catalog", m, { ok: false, code: "UNKNOWN_KIND", kinds: Object.keys(KINDS) });
  const parts = [[]];
  let length = 0;
  for (const item of make()) {
    const cost = JSON.stringify(item).length + 1;
    if (length + cost > PART_CHARS && parts[parts.length - 1].length) { parts.push([]); length = 0; }
    parts[parts.length - 1].push(item);
    length += cost;
  }
  parts.forEach((items, index) => reply("catalog", m, { kind: m.kind, ok: true, index, parts: parts.length, items }));
}

/** Handle one *_request event; returns true when it was answered. Exported for tests. */
export function onRequest(ev) {
  const handler = ev?.id === REQ.state ? state : ev?.id === REQ.record ? record : ev?.id === REQ.catalog ? catalog : undefined;
  if (!handler) return false;
  const m = parse(ev.message);
  if (!m) return false;
  handler(m);
  return true;
}

// ------------------------------------------------------------------------------------------------ the tide
let lastTide;
/** Broadcast the tide when it turns. The first look only remembers it. Exported for tests. */
export function watchTide() {
  const now = tideState();
  if (lastTide !== undefined && now !== lastTide) emit("tide", undefined, { state: now });
  lastTide = now;
}

system.afterEvents.scriptEventReceive.subscribe(ev => { try { onRequest(ev); } catch (err) { console.warn(`[Fishing Voyage] ${ev?.id}: ${err}`); } }, { namespaces: [SOURCE] });
system.runInterval(() => { try { watchTide(); } catch {} }, 100);
