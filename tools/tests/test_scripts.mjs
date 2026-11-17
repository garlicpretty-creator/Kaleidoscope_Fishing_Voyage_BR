// Script tests, run against a mock of the Minecraft scripting API (tools/tests/mock).
//   1. every script loads (main.js and all its imports)
//   2. every custom component used by a block or item JSON is registered at startup
//   3. the bait / catch registration API accepts good entries and rejects bad ones
//   4. each legend can be caught when all its conditions hold, and never when one is missing
//   5. the 1.4 species can all be caught in their own waters
//   6. 1.5.0: price registration, the event broadcast, the state / record / catalog requests
//   7. 1.5.0: the handshakes with Herbal, Harvest and Ranching; checked against their own API code when those
//      repositories sit next to this one (kaleidoscope_herbal_br, kaleidoscope_ranching_br)
//   8. 1.5.0: Lure, Luck of the Sea and Unbreaking where our own scripts do the work
//   9-11. 1.5.0: legend keepsakes, the cleaning board's per-cut format, the new waters
//   15. 1.5.0: register_board / register_tank: good and bad entries
//   14. 1.5.0: the trawl, the Meteor Marlin from a boat
//   13. 1.5.0: the fish pond: sizes, who lives where, register_pond_feed
//   12. 1.5.0: sky events: the nightly roll, pity, rain, the sky fish, the starfin, the aurora's char, the API
//   18. 1.6.0: lore keeps only symbols: the record ★ hides its length, old "★ N cm" is converted; rod and roe lore are glyphs
//   17. 1.6.0: glyph characters: every catch, water, dish, ingredient, station and tackle part has one
//   16. 1.6.0: every refusal key the scripts use has one of the four categories (util/hint.js)
// Run through tools/run_tests.py, or: node --import ./tools/tests/mock/hooks.mjs tools/tests/test_scripts.mjs
// Exit code 1 if anything fails.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { existsSync } from 'node:fs';
import { __sent, __subs } from './mock/server.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const BP = join(ROOT, 'Kaleidoscope Fishing Voyage [BP]');
const NS = 'kaleidoscope_fishing:';
const imp = p => import(pathToFileURL(join(BP, 'scripts', p)).href);
let failed = 0;
const ok = (c, m) => { if (!c) failed++; console.log(`${c ? 'OK  ' : 'FAIL'} ${m}`); };
const warns = [];
console.warn = (...a) => warns.push(a.join(' '));
const log = console.log;
console.info = () => {};

// ---------- 1. load ----------
let loadErr = null;
const quiet = console.log;
console.log = () => {};
try { await imp('main.js'); } catch (e) { loadErr = e; }
console.log = quiet;
ok(!loadErr, loadErr ? `load main.js: ${loadErr.stack.split('\n').slice(0, 3).join(' | ')}` : 'all scripts load (main.js and every import)');

// ---------- 2. custom components ----------
const registered = { block: new Set(), item: new Set() };
for (const fn of __subs['system.beforeEvents.startup'] ?? []) {
  try {
    fn({
      blockComponentRegistry: { registerCustomComponent: n => registered.block.add(n) },
      itemComponentRegistry: { registerCustomComponent: n => registered.item.add(n) },
      customCommandRegistry: { registerCommand() {}, registerEnum() {} },
    });
  } catch (e) { ok(false, `startup handler threw: ${e.message}`); }
}
function walkJs(d, acc = []) { for (const f of readdirSync(d)) { const p = join(d, f); statSync(p).isDirectory() ? walkJs(p, acc) : f.endsWith('.js') && acc.push(p); } return acc; }
function walk(d, acc = []) { for (const f of readdirSync(d)) { const p = join(d, f); statSync(p).isDirectory() ? walk(p, acc) : f.endsWith('.json') && acc.push(p); } return acc; }
for (const kind of ['block', 'item']) {
  const need = new Map();
  for (const p of walk(join(BP, kind === 'block' ? 'blocks' : 'items'))) {
    const root = JSON.parse(readFileSync(p, 'utf8'))['minecraft:' + kind];
    if (!root) continue;
    for (const c of [root.components ?? {}, ...(root.permutations ?? []).map(x => x.components ?? {})])
      for (const k of Object.keys(c)) if (k.startsWith(NS)) (need.get(k) ?? need.set(k, []).get(k)).push(p.split(/[\\/]/).pop());
  }
  const missing = [...need.keys()].filter(k => !registered[kind].has(k));
  ok(!missing.length, missing.length ? `${kind} components used but not registered: ${missing.join(', ')}`
    : `every ${kind} custom component used in JSON is registered (${need.size})`);
}

// ---------- 3. registration API ----------
const R = await imp('fishing/registry.js');
const L = await imp('fishing/loot.js');
const G = await imp('data/generated.js');
console.log = () => {};                      // the registry logs every accepted registration
R._setItemExists(id => id.startsWith('testpack:'));
R._clearRegistry();
const send = (kind, body) => R.onRegister({ id: `${NS}register_${kind}`, message: JSON.stringify({ api: 1, source: 'testpack', ...body }) });
const r1 = send('bait', { baits: [{ id: 'testpack:magic_worm', biteFactor: 0.6 }] });
const r2 = send('catch', { catches: [{ id: 'testpack:glow_eel', w: 10, waters: ['river'], size: [30, 80], needBait: ['testpack:magic_worm'] }] });
console.log = log;
ok(r1 === 1, 'register_bait accepts a valid bait');
ok(L.BAITS['testpack:magic_worm']?.biteFactor === 0.6, 'a registered bait reaches the catch code');
ok(r2 === 1, 'register_catch accepts a valid catch');
let withBait = 0, without = 0;
for (let i = 0; i < 4000; i++) {
  const base = { waters: new Set(['river']), depth: 3, slot: 'day', tier: 1, rod: true };
  if (L.rollCatch({ ...base, bait: 'testpack:magic_worm' }) === 'testpack:glow_eel') withBait++;
  if (L.rollCatch({ ...base, bait: `${NS}earthworm` }) === 'testpack:glow_eel') without++;
}
ok(withBait > 0 && without === 0, `a registered catch bites only on its bait (${withBait}/4000 with it, ${without}/4000 without)`);
const rejected = (body, why) => { const n = warns.length; const r = send('catch', { catches: [body] }); ok(r === 0 && warns.length > n, `rejected: ${why}`); };
rejected({ id: 'testpack:sky_fish', w: 5, sky: 'blood_moon' }, 'an entry with an unknown sky');
rejected({ id: 'testpack:fake_legend', w: 5, req: { weather: 'thunder' } }, 'an entry with legend conditions (req)');
rejected({ id: `${NS}carp`, w: 5 }, "an entry using Fishing Voyage's own id");
rejected({ id: 'testpack:heavy', w: 99 }, 'a weight out of range');
rejected({ id: 'otherpack:missing', w: 5 }, 'an item that does not exist');
ok(send('bait', { baits: [{ id: `${NS}earthworm` }] }) === 0, 'rejected: overriding a built-in bait');
ok(R.onRegister({ id: `${NS}register_catch`, message: '{"api":2,"source":"x","catches":[]}' }) === 0, 'rejected: a wrong api version');
R._clearRegistry();

// ---------- 4. legends ----------
const byId = Object.fromEntries(G.CATCHES.map(c => [c.id, c]));
const count = (ctx, id, n) => { let c = 0; for (let i = 0; i < n; i++) if (L.rollCatch(ctx) === id) c++; return c; };
for (const id of G.LEGENDS ?? []) {
  const e = byId[id];
  if (!e) { ok(false, `legend ${id} is missing from CATCHES`); continue; }
  const r = e.req ?? {};
  const ctx = {
    waters: new Set([...(e.waters ?? ['river']).slice(0, 1), ...(e.needs ?? [])]), depth: e.min_depth ?? 4, rod: true, tier: r.tier ?? 3,
    thunder: r.weather === 'thunder', raining: !!r.weather, hook: r.hook, line: r.line, bait: r.nobait ? undefined : r.bait,
    moon: r.moon?.[0] ?? 2, tide: r.tide, slot: r.slots?.[0] ?? (e.time === 'night' ? 'night' : 'day'), dim: r.dim, cold: true, caught: new Set(),
  };
  const name = id.slice(NS.length);
  ok(count(ctx, id, 20000) > 0, `${name} is caught when every condition holds (${JSON.stringify(r)})`);
  for (const k of Object.keys(r)) {
    if (k === 'sky_moon') continue;                     // 1.5.0: not a condition, a sky that stands in for the moon (section 12)
    const bad = { ...ctx };
    if (k === 'weather') { bad.thunder = false; bad.raining = false; }
    else if (k === 'hook') bad.hook = `${NS}copper_hook`;
    else if (k === 'line') bad.line = `${NS}hemp_line`;
    else if (k === 'bait' || k === 'nobait') bad.bait = `${NS}earthworm`;
    else if (k === 'moon') bad.moon = [0, 1, 2, 3, 4, 5, 6, 7].find(p => !r.moon.includes(p));
    else if (k === 'tide') bad.tide = r.tide === 'high' ? 'low' : 'high';
    else if (k === 'slots') bad.slot = ['dawn', 'day', 'dusk', 'night'].find(s => !r.slots.includes(s));
    else if (k === 'dim') bad.dim = 'minecraft:overworld';
    else if (k === 'tier') bad.tier = 1;
    ok(count(bad, id, 5000) === 0, `  ${name} never without "${k}"`);
  }
  ok(count({ ...ctx, rod: false }, id, 5000) === 0, `  ${name} never without a rod`);
}

// ---------- 5. 1.4 species ----------
for (const n of ['loach', 'mudskipper', 'snakehead', 'cave_blindfish', 'grey_mullet', 'sea_bass', 'flying_fish', 'lobster', 'king_crab', 'cave_crayfish']) {
  const e = byId[NS + n];
  if (!e) { ok(false, `${n} is missing from the catch table`); continue; }
  const ctx = { waters: new Set([...(e.waters ?? ['river']), ...(e.needs ?? [])]), depth: e.min_depth ?? Math.min(4, e.max_depth ?? 4),
    rod: true, tier: e.tier ?? 3, slot: e.slots?.[0] ?? (e.time === 'night' ? 'night' : 'day'), moon: 2, raining: false, cold: false };
  ok(count(ctx, e.id, 20000) > 0, `${n} can be caught (${(e.waters ?? []).join('/') || 'any water'}${e.needs ? ', needs ' + e.needs : ''}${e.tier ? ', rod tier ' + e.tier : ''})`);
}

// ---------- 6. host API (1.5.0) ----------
const H = await imp('api/host.js');
const M = await imp('world/merchant.js');
const sentSince = (n, id) => __sent.slice(n).filter(e => e[0] === id).map(e => JSON.parse(e[1]));
console.log = () => {};
R._clearRegistry();
const pr = body => R.onRegister({ id: `${NS}register_price`, message: JSON.stringify({ api: 1, source: 'testpack', ...body }) });
const p1 = pr({ prices: [{ id: 'testpack:glow_eel', price: 0.5 }] });
console.log = log;
ok(p1 === 1 && M.priceOf('testpack:glow_eel') === 0.5, 'register_price: the merchant pays the registered price');
ok(M.priceOf(`${NS}carp`) === G.MERCHANT_PRICES[`${NS}carp`], 'register_price: our own prices are untouched');
{
  const n = warns.length;
  ok(pr({ prices: [{ id: `${NS}carp`, price: 3 }] }) === 0, 'rejected: a price for one of our own fish');
  ok(pr({ prices: [{ id: 'minecraft:diamond', price: 1 }] }) === 0, 'rejected: a price for a vanilla item');
  ok(pr({ prices: [{ id: 'testpack:glow_eel', price: 64 }] }) === 0, 'rejected: a price out of range');
  ok(pr({ prices: [{ id: 'otherpack:missing', price: 1 }] }) === 0, 'rejected: a price for an item that does not exist');
  ok(warns.length === n + 4, 'every rejected price is reported once');
}
R._clearRegistry();
ok(M.priceOf('testpack:glow_eel') === undefined, 'register_price: gone after the registry is cleared');
for (const c of ['bait', 'catch', 'price', 'events', 'state', 'records', 'catalog']) ok(R.CAPABILITIES.includes(c), `api_ready lists the capability "${c}"`);

let mark = __sent.length;
H.emitCaught({ id: 'p1' }, `${NS}emperor_tuna`, { via: 'rod', size: 210, cls: 3, rec: { first: true, newBest: false } });
const caught = sentSince(mark, H.EVT)[0];
ok(caught && caught.v === 1 && caught.t === 'caught' && caught.p === 'p1' && caught.id === `${NS}emperor_tuna` && caught.via === 'rod'
  && caught.size === 210 && caught.cls === 3 && caught.legend === true && caught.first === true && caught.record === false,
  `evt caught carries the fish, how, its size and whether it is a legend, a first or a record (${JSON.stringify(caught)})`);
mark = __sent.length;
H.emitCaught({ id: 'p1' }, `${NS}shrimp`, { via: 'tip_up', cls: 0, rec: { first: false, newBest: false } });
ok(!('size' in sentSince(mark, H.EVT)[0]) && sentSince(mark, H.EVT)[0].legend === false, 'evt caught: an unsized catch has no size, an ordinary fish is no legend');
ok(__sent.every(e => String(e[1]).length <= 2048), 'every script event we send fits in 2048 characters');

const ask = (name, body) => { const n = __sent.length; const handled = H.onRequest({ id: `${NS}${name}_request`, message: JSON.stringify({ api: 1, source: 'testpack', ...body }) }); return { handled, out: sentSince(n, `${NS}${name}`) }; };
const st = ask('state', { req: 'a1' });
ok(st.handled && st.out.length === 1 && st.out[0].to === 'testpack' && st.out[0].req === 'a1' && st.out[0].ok === true
  && ['high', 'low'].includes(st.out[0].tide) && Number.isInteger(st.out[0].moon) && typeof st.out[0].slot === 'string',
  `state_request is answered to the asker with tide, moon and time slot (${JSON.stringify(st.out[0])})`);
ok(!H.onRequest({ id: `${NS}state_request`, message: '{"api":2,"source":"testpack"}' }), 'a request with the wrong api gets no answer');
ok(!H.onRequest({ id: `${NS}state_request`, message: `{"api":1,"source":"kaleidoscope_fishing"}` }), 'a request claiming to be us gets no answer');
ok(!H.onRequest({ id: `${NS}state_request`, message: 'not json' }), 'a request that is not JSON gets no answer');
const rc = ask('record', { p: 'nobody' });
ok(rc.out[0]?.ok === false && rc.out[0].code === 'NO_PLAYER', 'record_request for a player who is not there answers NO_PLAYER');
const cat = ask('catalog', { kind: 'catches', req: 7 });
const items = cat.out.sort((a, b) => a.index - b.index).flatMap(m => m.items);
ok(cat.out.length > 1 && cat.out.every(m => m.parts === cat.out.length && m.req === 7 && m.ok) && items.length === G.CATCHES.length,
  `catalog catches comes in ${cat.out.length} parts with all ${G.CATCHES.length} catches`);
ok(items.filter(i => i.legend).length === G.LEGENDS.length && items.every(i => Array.isArray(i.waters)), 'catalog catches marks the legends and lists the waters');
const baits = ask('catalog', { kind: 'baits' }).out.flatMap(m => m.items);
ok(baits.some(b => b.id === `${NS}earthworm`) && !baits.some(b => b.id === L.LURE), 'catalog baits lists the real baits, not the lure hook stand-in');
ok(ask('catalog', { kind: 'nope' }).out[0]?.code === 'UNKNOWN_KIND', 'catalog of an unknown kind answers UNKNOWN_KIND');

// ---------- 7. sister packs (1.5.0) ----------
const F = await imp('api/family.js');
F._resetFamily();
mark = __sent.length;
F.pingFamily();
ok(['kaleidoscope_herbal', 'kaleidoscope_harvest', 'kaleidoscope_ranching'].every(ns => __sent.slice(mark).some(e => e[0] === `${ns}:api_ping` && e[1] === 'kaleidoscope_fishing')),
  'the handshake pings Herbal, Harvest and Ranching with our namespace');
mark = __sent.length;
ok(!F.onFamilyEvent({ id: 'kaleidoscope_herbal:api_ready', message: '{"api":2,"capabilities":["external_heat"]}' }) && __sent.length === mark,
  'a sister pack with a newer, incompatible api is left alone');
ok(F.onFamilyEvent({ id: 'kaleidoscope_herbal:api_ready', message: JSON.stringify({ api: 1, source: 'kaleidoscope_herbal', version: '1.2.0', capabilities: ['events'], limits: {} }) }) && __sent.length === mark,
  'Herbal without external_heat: we note it and send nothing');
F.onFamilyEvent({ id: 'kaleidoscope_herbal:api_ready', message: JSON.stringify({ api: 1, source: 'kaleidoscope_herbal', version: '1.2.0', capabilities: ['external_heat'], limits: { itemsPerMessage: 32 } }) });
const heatMsgs = sentSince(mark, 'kaleidoscope_herbal:heat_register');
const heatRows = heatMsgs.flatMap(m => m.items);
ok(heatMsgs.length >= 1 && heatMsgs.every(m => m.api === 1 && m.source === 'kaleidoscope_fishing' && m.items.length <= 32)
  && heatRows.length === Object.keys(G.HERBAL_HEAT).length, `Herbal: ${heatRows.length} heat values sent in ${heatMsgs.length} message(s) of at most 32`);
ok(F.familyInfo('kaleidoscope_herbal')?.version === '1.2.0' && F.familyInfo('kaleidoscope_harvest') === undefined, 'familyInfo tells who has answered');
{
  const foods = new Set();
  for (const p of walk(join(BP, 'items'))) { const it = JSON.parse(readFileSync(p, 'utf8'))['minecraft:item']; if (it?.components?.['minecraft:food']) foods.add(it.description.identifier); }
  const bad = Object.entries(G.HERBAL_HEAT).filter(([id, h]) => !foods.has(id) || !Number.isInteger(h) || h === 0 || h < -100 || h > 100);
  ok(!bad.length, bad.length ? `HERBAL_HEAT entries that are not our food or not a non-zero integer -100..100: ${bad.map(b => b[0])}` : 'every HERBAL_HEAT entry is one of our food items with a heat of -100..100');
}
{
  const n = warns.length;
  F.onFamilyEvent({ id: 'kaleidoscope_herbal:heat_ack', message: JSON.stringify({ api: 1, to: 'someone_else', ok: true, accepted: 0, rejected: [{ id: 'x:y', code: 'TAKEN' }] }) });
  ok(warns.length === n, "an ack addressed to another pack is not ours to report");
  F.onFamilyEvent({ id: 'kaleidoscope_herbal:heat_ack', message: JSON.stringify({ api: 1, to: 'kaleidoscope_fishing', ok: true, accepted: 1, rejected: [{ id: `${NS}oden`, code: 'TAKEN' }] }) });
  F.onFamilyEvent({ id: 'kaleidoscope_herbal:heat_ack', message: JSON.stringify({ api: 1, to: 'kaleidoscope_fishing', ok: true, accepted: 1, rejected: [{ id: `${NS}oden`, code: 'TAKEN' }] }) });
  ok(warns.length === n + 1, 'a heat value Herbal rejects is reported once, however often it is sent again');
}
mark = __sent.length;
F.onFamilyEvent({ id: 'kaleidoscope_ranching:api_ready', message: JSON.stringify({ api: 1, version: '1.0.0', capabilities: ['register_feed'] }) });
const oldFeeds = sentSince(mark, 'kaleidoscope_ranching:register_feed');
mark = __sent.length;
F.onFamilyEvent({ id: 'kaleidoscope_ranching:api_ready', message: JSON.stringify({ api: 1, version: '1.1.0', capabilities: ['register_feed', 'feed_1_1'] }) });
const newFeeds = sentSince(mark, 'kaleidoscope_ranching:register_feed');
ok(oldFeeds.length === G.RANCHING_FEEDS.filter(f => !f.needs).length && newFeeds.length === G.RANCHING_FEEDS.length
  && newFeeds.every(f => f.item.startsWith(NS) && typeof f.kind === 'string' && f.units >= 1 && f.units <= 9),
  `Ranching: ${newFeeds.length} feeds registered, one per message (${oldFeeds.length} for a Ranching without feed_1_1)`);
{
  const n = warns.length;
  F.onFamilyEvent({ id: 'kaleidoscope_ranching:api_result', message: JSON.stringify({ event: 'register_feed', id: 'other_pack:oats', ok: false, error: 'x' }) });
  F.onFamilyEvent({ id: 'kaleidoscope_ranching:api_result', message: JSON.stringify({ event: 'register_feed', id: `${NS}fish_meal`, ok: true }) });
  ok(warns.length === n, "Ranching's results for other packs, and its acceptances, are not reported");
  F.onFamilyEvent({ id: 'kaleidoscope_ranching:api_result', message: JSON.stringify({ event: 'register_feed', id: `${NS}fish_meal`, ok: false, error: 'built-in feeds cannot be replaced' }) });
  ok(warns.length === n + 1, 'a feed Ranching refuses is reported');
}
mark = __sent.length;
ok(F.onFamilyEvent({ id: 'kaleidoscope_harvest:api_ready', message: JSON.stringify({ api: 1, version: '1.0.0', capabilities: [] }) }) && __sent.length === mark
  && F.familyInfo('kaleidoscope_harvest')?.version === '1.0.0', 'Harvest: the handshake is remembered and nothing is sent yet');
ok(!F.onFamilyEvent({ id: 'some_other_pack:api_ready', message: '{"api":1}' }), 'api_ready from a pack outside the family is ignored');

// Against the sister packs' own code, when their repositories are checked out next to this one.
const beside = name => [name, name.replace(/(^|_)([a-z])/g, (_, a, b) => a + b.toUpperCase()).replace(/_Br$/, '_BR')].map(n => join(ROOT, '..', n)).find(existsSync);
const herbalRepo = beside('kaleidoscope_herbal_br');
if (herbalRepo) {
  const core = await import(pathToFileURL(join(herbalRepo, 'Kaleidoscope Herbal [BP]', 'scripts', 'api', 'herbalHostCore.js')).href);
  const out = [], externalHeat = new Map();
  const host = core.createHerbalHost({ send: (id, message) => out.push([id, JSON.parse(message)]), now: () => 0, version: 'test', catalogs: {},
    externalHeat, ownsItem: id => id.startsWith('kaleidoscope_herbal:'), getPlayer: () => undefined, getHeat: () => 0, shiftHeat: () => ({ heat: 0 }), log: () => {} });
  for (const m of heatMsgs) host.handle('kaleidoscope_herbal:heat_register', JSON.stringify(m), 'Server');
  const acks = out.filter(e => e[0] === 'kaleidoscope_herbal:heat_ack').map(e => e[1]);
  const accepted = acks.reduce((n, a) => n + (a.accepted ?? 0), 0), refused = acks.flatMap(a => a.rejected ?? []);
  ok(acks.length === heatMsgs.length && acks.every(a => a.ok && a.to === 'kaleidoscope_fishing') && accepted === heatRows.length && !refused.length && externalHeat.size === heatRows.length,
    `Herbal's own host code accepts all ${heatRows.length} of our heat values (${refused.length} rejected${refused.length ? ': ' + JSON.stringify(refused) : ''})`);
} else console.log('NOTE Herbal repository not found next to this one: heat_register checked against our reading of its API only');
const ranchRepo = beside('kaleidoscope_ranching_br');
if (ranchRepo) {
  const api = readFileSync(join(ranchRepo, 'packs', 'BP', 'scripts', 'api', 'ranchingApi.js'), 'utf8');
  const feeds = readFileSync(join(ranchRepo, 'packs', 'BP', 'scripts', 'data', 'feeds.js'), 'utf8');
  const kinds = new Set([...(api.match(/const FEED_KINDS = \{([^}]*)\}/)?.[1] ?? '').matchAll(/(\w+):/g)].map(m => m[1]));
  const caps = new Set([...(api.match(/export const CAPABILITIES = \[([\s\S]*?)\];/)?.[1] ?? '').matchAll(/"([a-z0-9_]+)"/g)].map(m => m[1]));
  ok(G.RANCHING_FEEDS.every(f => kinds.has(f.kind) && (!f.needs || caps.has(f.needs))) && caps.has('register_feed'),
    `Ranching's own API knows every feed kind and capability we use (${[...new Set(G.RANCHING_FEEDS.map(f => f.kind))].join(', ')})`);
  ok(G.RANCHING_FEEDS.every(f => !feeds.includes(`"${f.item}"`)), 'none of the feeds we register is already built into Ranching (it would be refused)');
} else console.log('NOTE Ranching repository not found next to this one: register_feed checked against our reading of its API only');
const harvestRepo = beside('kaleidoscope_harvest_br');
const harvestFishing = harvestRepo && join(harvestRepo, 'packs', 'BP', 'scripts', 'api', 'fishing.js');
if (harvestFishing && existsSync(harvestFishing)) {
  // Harvest's own bridge builds the messages; our registry takes them as any other pack's
  const { fishingMessages } = await import(pathToFileURL(harvestFishing).href);
  const msgs = fishingMessages({ api: 1, capabilities: [...R.CAPABILITIES] });
  R._setItemExists(id => id.startsWith('kaleidoscope_harvest:'));
  const took = msgs.reduce((n, [id, message]) => n + R.onRegister({ id, message }), 0);
  const rows = msgs.flatMap(([, m]) => { const j = JSON.parse(m); return [...(j.baits ?? []), ...(j.feeds ?? [])]; });
  ok(msgs.length === 2 && rows.length > 0 && took === rows.length
    && rows.every(r => (r.biteFactor !== undefined ? R.externalBait(r.id)?.source === 'kaleidoscope_harvest' : R.externalFeed(r.id) === r.meals)),
    `Harvest's own bridge: all ${rows.length} of its baits and pond feeds are accepted`);
  R._clearRegistry();
  R._setItemExists(id => id.startsWith('testpack:'));
} else console.log('NOTE Harvest repository (with api/fishing.js) not found next to this one: its baits and pond feeds not checked');

// ---------- 8. enchantments our scripts honour (1.5.0) ----------
const E = await imp('util/enchant.js');
const enchanted = levels => ({ getComponent: n => (n === 'minecraft:enchantable' ? { getEnchantment: id => (levels[id] ? { level: levels[id] } : undefined) } : undefined) });
ok(E.enchantLevel(enchanted({ lure: 2 }), 'lure') === 2 && E.enchantLevel(enchanted({}), 'lure') === 0 && E.enchantLevel(undefined, 'lure') === 0
  && E.enchantLevel({ getComponent() { throw new Error('x'); } }, 'lure') === 0, 'enchantLevel reads a level, and is 0 for no enchantment, no stack or a stack that throws');
ok([0, 1, 2, 3].map(l => E.lureTicks(200, l)).join() === '200,170,140,110', 'Lure: a 200-tick wait becomes 170 / 140 / 110 at levels 1-3');
ok(E.lureTicks(50, 3) === 40 && E.lureTicks(18, 3) === 18 && E.lureTicks(18, 0) === 18, 'Lure: never under 2 s by itself, and never longer than the wait without it');
ok(E.luckFactor(0) === 1 && Math.abs(E.luckFactor(3) - 1.45) < 1e-9 && Math.abs(E.luckFactor(9) - 1.45) < 1e-9, 'Luck of the Sea: +15 % per level, capped at level 3');
{
  let n = 0; const rolls = [40, 70];
  ok(E.luckSize(0, () => rolls[n++], () => 0) === 40 && n === 1, 'Luck of the Sea: without it the size is rolled once');
  n = 0; ok(E.luckSize(3, () => rolls[n++], () => 0) === 70 && n === 2, 'Luck of the Sea: when it strikes, the larger of two rolls is kept');
  n = 0; ok(E.luckSize(3, () => rolls[n++], () => 0.99) === 40 && n === 1, 'Luck of the Sea: most casts roll once all the same');
  ok(E.luckSize(3, () => undefined, () => 0) === undefined, 'Luck of the Sea: an unsized catch stays unsized');
}
{
  let worn = 0; for (let i = 0; i < 6000; i++) if (E.wears(3)) worn++;
  ok(E.wears(0) === true && worn > 1200 && worn < 1800, `Unbreaking III spares about three uses in four (${worn}/6000 wore the tool)`);
}
{
  // Luck of the Sea reaches the catch table: the less common sized fish come up more often, legends do not
  const rareIds = new Set(G.CATCHES.filter(c => c.size && c.w <= 12 && !c.req).map(c => c.id));
  const sea = { waters: new Set(['ocean', 'deep_ocean']), depth: 12, slot: 'day', tier: 2, rod: true, moon: 2, caught: new Set() };
  const share = luck => { let r = 0; for (let i = 0; i < 30000; i++) if (rareIds.has(L.rollCatch({ ...sea, luck }))) r++; return r / 30000; };
  const plain = share(1), lucky = share(E.luckFactor(3));
  ok(lucky > plain * 1.12, `Luck of the Sea III brings up more of the less common fish (${(plain * 100).toFixed(1)} % -> ${(lucky * 100).toFixed(1)} %)`);
  const src = readFileSync(join(BP, 'scripts', 'fishing', 'loot.js'), 'utf8');
  ok(/!e\.req\) w \*= ctx\.luck/.test(src), 'Luck of the Sea leaves the legends (entries with req) alone');
}

// ---------- 9. legend keepsakes and tackle, legends in the creel (1.5.0) ----------
{
  const ROD = await imp('fishing/rod.js');
  const PT = await imp('fishing/parts.js');
  ok(G.LEGENDS.every(id => G.KEEPSAKES[id]), `every legend has a keepsake (${G.LEGENDS.filter(id => G.KEEPSAKES[id]).length}/${G.LEGENDS.length})`);
  ok(ROD.partAs(`${NS}emperor_bone_hook`) === `${NS}bone_hook` && ROD.partAs(`${NS}whisker_line`) === `${NS}wire_line`
    && ROD.partAs(`${NS}gold_hook`) === `${NS}gold_hook` && ROD.partAs(undefined) === undefined,
    'the Emperor Bone Hook counts as a Bone Hook and the Whisker Line as a Wire Line; other parts are themselves');
  const lord = byId[`${NS}river_lord_catfish`], lordCtx = { rod: true, tier: 3, thunder: true, raining: true, moon: 2, slot: 'night', caught: new Set() };
  ok(L.reqOk(lord, { ...lordCtx, hook: ROD.partAs(`${NS}emperor_bone_hook`) }) && !L.reqOk(lord, { ...lordCtx, hook: ROD.partAs(`${NS}gold_hook`) }),
    'the River Lord Catfish takes an Emperor Bone Hook, and still not a Gold Hook');
  ok(ROD.KEEPSAKE_AGAIN > 0 && ROD.KEEPSAKE_AGAIN < 1, `a legend caught again drops its keepsake now and then (${ROD.KEEPSAKE_AGAIN})`);
  const styles = Object.values(G.PARTS).map(p => p.style ?? 0);
  const bob = JSON.parse(readFileSync(join(BP, 'entities', 'bobber.json'), 'utf8'))['minecraft:entity'].description.properties[`${NS}style`];
  const RPdir = join(ROOT, 'Kaleidoscope Fishing Voyage [RP]');
  const skins = JSON.parse(readFileSync(join(RPdir, 'render_controllers', 'kfv_bobber.render_controllers.json'), 'utf8')).render_controllers['controller.render.kfv_bobber'].arrays.textures['Array.skins'];
  const client = JSON.parse(readFileSync(join(RPdir, 'entity', 'bobber.entity.json'), 'utf8'))['minecraft:client_entity'].description.textures;
  ok(Math.max(...styles) <= bob.range[1] && skins.length === bob.range[1] + 1 && skins.every(t => client[t.split('.')[1]] && existsSync(join(RPdir, client[t.split('.')[1]] + '.png'))),
    `every bobber style has a skin: styles up to ${Math.max(...styles)}, property 0..${bob.range[1]}, ${skins.length} textures`);
  ok(Object.values(G.LINE_STYLE).every(n => existsSync(join(RPdir, 'particles', `${n}.json`)) && existsSync(join(RPdir, 'textures', 'particle', `kfv_${n}.png`))),
    `every line colour has its particle and texture (${Object.values(G.LINE_STYLE).join(', ')})`);
  const fx = PT.effects({ hook: `${NS}emperor_bone_hook`, line: `${NS}whisker_line`, bobber: `${NS}frost_scale_bobber` });
  ok(fx.rare === 1.5 && fx.size === 1 && fx.strain === 2 && fx.depth === 6 && fx.night === 0.75 && fx.style === 8 && fx.line === 'line_whisker' && fx.wear === 0,
    `the legend tackle works as tackle (${JSON.stringify(fx)})`);
  ok(G.LEGENDS.every(id => G.BASKET_ITEMS.some(b => b.id === id)), 'the Fish Creel has a place for every legend');
}

// ---------- 10. the Fish Cleaning Board's per-cut format gives what 1.4 gave (1.5.0) ----------
{
  const CB = await imp('blocks/cleaning.js');
  const OLD = JSON.parse(readFileSync(join(ROOT, 'tools', 'tests', 'cleaning_1_4.json'), 'utf8'));
  // 1.4's rules, written out: scale (if any) -> scales; gut -> offal and chance extras; fillet -> sized fillets and bones
  const oldCuts = (f, cls, rolls) => {
    const out = [];
    if (f.scales) out.push([[`${NS}fish_scales`, 1]]);
    out.push([[`${NS}fish_offal`, 1], ...f.extra.filter((e, i) => rolls[i] < e[1]).map(e => [e[0], 1])]);
    out.push([[f.out[0], Math.max(1, f.out[1] + (cls === 3 ? 1 : cls === 1 ? -1 : 0))], ...(f.bones > 0 ? [[`${NS}fish_bones`, f.bones]] : [])]);
    return out;
  };
  const bad = [];
  // cut differently on purpose in 1.5.0: tuna by part, skipjack into its own bonito slices (plan 5.7)
  const CHANGED = new Set([`${NS}tuna`, `${NS}emperor_tuna`, `${NS}skipjack`]);
  for (const [id, f] of Object.entries(OLD)) {
    if (CHANGED.has(id)) continue;
    const n = G.CLEANING[id];
    if (!n || n.index !== f.index || n.first !== (f.scales ? 1 : 2)) { bad.push(`${id}: index or first stage`); continue; }
    for (const cls of [0, 1, 2, 3]) for (const rolls of [[0], [0.999]]) {
      const want = JSON.stringify(oldCuts(f, cls, f.extra.map(() => rolls[0])));
      const got = JSON.stringify(n.cuts.map(cut => CB.cutYield(cut, cls, () => rolls[0])));
      if (want !== got) bad.push(`${id} size ${cls}: ${got} != ${want}`);
    }
    for (const cls of [0, 2, 3]) {
      const gotDrop = JSON.stringify(CB.boardContents(f.index, 3, cls));
      const wantDrop = JSON.stringify([[f.out[0], Math.max(1, f.out[1] + (cls === 3 ? 1 : 0)), 0], ...(f.bones > 0 ? [[`${NS}fish_bones`, f.bones, 0]] : [])]);
      if (gotDrop !== wantDrop) bad.push(`${id} half-cut drop: ${gotDrop} != ${wantDrop}`);
    }
  }
  ok(!bad.length, bad.length ? `board format: ${bad.length} differences: ${bad.slice(0, 3).join(' | ')}` : `board format: all ${Object.keys(OLD).length - CHANGED.size} fish of 1.4 not changed on purpose give exactly what they gave, cut by cut, at every size`);
  {
    const tuna = G.CLEANING[`${NS}tuna`].cuts.at(-1).out, emp = G.CLEANING[`${NS}emperor_tuna`].cuts.at(-1).out, sj = G.CLEANING[`${NS}skipjack`].cuts.at(-1).out;
    const n = (out, id) => out.find(r => r[0] === `${NS}${id}`)?.[1] ?? 0;
    ok(n(tuna, 'tuna_sashimi') + n(tuna, 'chutoro') + n(tuna, 'otoro') === OLD[`${NS}tuna`].out[1] && n(emp, 'tuna_sashimi') + n(emp, 'chutoro') + n(emp, 'otoro') === OLD[`${NS}emperor_tuna`].out[1],
      `board: tuna is cut into akami, chutoro and otoro, as many slices as before (${n(tuna, 'tuna_sashimi')}/${n(tuna, 'chutoro')}/${n(tuna, 'otoro')}, emperor ${n(emp, 'tuna_sashimi')}/${n(emp, 'chutoro')}/${n(emp, 'otoro')})`);
    ok(n(sj, 'bonito_sashimi') === OLD[`${NS}skipjack`].out[1] && !n(sj, 'tuna_sashimi'), 'board: skipjack gives bonito sashimi, no longer tuna');
  }
  ok(Object.values(G.CLEANING).every(f => f.first >= 1 && f.first + f.cuts.length - 1 <= 3 && f.cuts.every(c => (c.out.length || c.act === 'bone') && c.out.every(r => typeof r[0] === 'string' && r[1] >= 1))),
    'board format: every catch fits the board (stages 1-3) and every cut gives something (drawing a squid\'s cartilage gives nothing)');
}

// ---------- 11. the new waters (1.5.0) ----------
{
  const roll = (ctx, n) => { const got = {}; for (let i = 0; i < n; i++) { const id = L.rollCatch(ctx); got[id] = (got[id] ?? 0) + 1; } return got; };
  const base = { depth: 4, rod: true, tier: 2, moon: 2, caught: new Set(), raining: false };
  let g = roll({ ...base, waters: new Set(['lake', 'mushroom']), slot: 'night' }, 20000);
  ok(g[`${NS}mycelium_flounder`] > 0 && g[`${NS}spore_seahorse`] > 0, `mushroom island: flounder and, at night, the seahorse (${g[`${NS}mycelium_flounder`]}, ${g[`${NS}spore_seahorse`]})`);
  g = roll({ ...base, waters: new Set(['lake', 'mushroom']), slot: 'day' }, 20000);
  ok(!g[`${NS}spore_seahorse`], 'mushroom island: no seahorse by day');
  g = roll({ ...base, waters: new Set(['river', 'cherry']), slot: 'day', bait: `${NS}earthworm` }, 20000);
  ok(g[`${NS}cherry_trout`] > 0 && g[`${NS}creek_shrimp`] > 0 && g[`${NS}carp`] > 0, `cherry grove: trout and creek shrimp among the river's own fish (${g[`${NS}cherry_trout`]}, ${g[`${NS}creek_shrimp`]})`);
  g = roll({ ...base, waters: new Set(['lake']), slot: 'day' }, 20000);
  ok(!g[`${NS}cherry_trout`] && !g[`${NS}mycelium_flounder`], 'an ordinary lake has neither');
  g = roll({ ...base, waters: new Set(['deep_dark']), slot: 'day' }, 20000);
  const ids = Object.keys(g).filter(k => k.startsWith(NS) || k.startsWith('minecraft:'));
  ok(g[`${NS}echo_ray`] > 0 && !g[`${NS}sculk_lanternfish`] && ids.every(id => !G.CATCHES.find(c => c.id === id) || G.CATCHES.find(c => c.id === id).waters?.includes('deep_dark')),
    `deep dark: only its own catches; no lanternfish without glow bait (${ids.filter(i => G.CATCHES.some(c => c.id === i)).map(i => i.split(':')[1])})`);
  g = roll({ ...base, waters: new Set(['deep_dark']), slot: 'day', bait: `${NS}glow_bait` }, 20000);
  ok(g[`${NS}sculk_lanternfish`] > 0, `deep dark: the lanternfish comes to glow bait (${g[`${NS}sculk_lanternfish`]})`);
  const sp = G.JOURNAL_SPECIES.filter(s => s.group === 'secret').map(s => s.key);
  ok(sp.length === 6 && sp.every(k => G.BASKET_ITEMS.some(b => b.id === NS + k) && G.MERCHANT_PRICES[NS + k] > 0 && G.TANK_FISH.includes(NS + k)),
    `the six new fish have a journal page, a creel place, a price and a tank model (${sp})`);
  ok(['mycelium_flounder', 'cherry_trout', 'creek_shrimp', 'echo_ray', 'sculk_lanternfish'].every(k => G.CLEANING[NS + k]) && !G.CLEANING[NS + 'spore_seahorse'],
    'they go on the Fish Cleaning Board, except the seahorse');
}

// ---------- 12. sky events (1.5.0) ----------
{
  const Sk = await imp('world/sky.js');
  let seq = 0;
  const fixed = v => () => v;
  ok(Sk.rollSky(0, false, fixed(0.05)).sky === 'meteor' && Sk.rollSky(0, false, fixed(0.15)).sky === 'aurora' && Sk.rollSky(0, false, fixed(0.5)).sky === '',
    'roll: meteor under 10%, aurora under 22.5%, else a quiet night');
  ok(Sk.rollSky(3, false, fixed(0.5)).quiet === 4 && Sk.rollSky(3, false, fixed(0.05)).quiet === 0, 'roll: a quiet night counts one more, a sky resets the count');
  const pity = Sk.rollSky(Sk.PITY, false, fixed(0.99));
  ok(Sk.PITY === 10 && pity.sky === 'meteor' && pity.quiet === 0 && Sk.rollSky(Sk.PITY, true, fixed(0.99)).sky === 'aurora',
    'pity: after 10 quiet nights the next one always has a sky (the aurora when it rains)');
  const wet = Sk.rollSky(4, true, fixed(0.05));
  ok(wet.sky === '' && wet.cancelled && wet.quiet === 4, 'rain at dusk: the meteor shower is cancelled and the night does not count');
  let n = { meteor: 0, aurora: 0, '': 0 }, q = 0, longest = 0, run = 0;
  const rnd = () => { seq = (seq * 1103515245 + 12345) % 2147483648; return seq / 2147483648; };
  for (let i = 0; i < 20000; i++) { const r = Sk.rollSky(q, false, rnd); n[r.sky]++; q = r.quiet; run = r.sky ? 0 : run + 1; longest = Math.max(longest, run); }
  ok(longest <= Sk.PITY && n.meteor + n.aurora > 20000 / 5.5 && n.meteor + n.aurora < 20000 / 3.5,
    `20000 nights: a sky about every 4-5 nights (${n.meteor} meteor, ${n.aurora} aurora), never more than 10 quiet in a row (${longest})`);

  const roll = (ctx, k) => { const got = {}; for (let i = 0; i < k; i++) { const id = L.rollCatch(ctx); got[id] = (got[id] ?? 0) + 1; } return got; };
  const base = { depth: 14, rod: true, tier: 2, moon: 2, caught: new Set(), raining: false, slot: 'night' };
  let g = roll({ ...base, waters: new Set(['ocean', 'deep_ocean']), sky: 'meteor' }, 30000);
  ok(g[`${NS}meteor_marlin`] > 0 && g[`${NS}starfin`] > 0, `meteor night, deep sea: the Meteor Marlin and the starfin (${g[`${NS}meteor_marlin`]}, ${g[`${NS}starfin`]})`);
  g = roll({ ...base, waters: new Set(['ocean', 'deep_ocean']), sky: '' }, 30000);
  ok(!g[`${NS}meteor_marlin`] && !g[`${NS}starfin`], 'a quiet night at sea: neither');
  g = roll({ ...base, waters: new Set(['ocean', 'deep_ocean']), sky: 'meteor', tier: 1 }, 30000);
  ok(!g[`${NS}meteor_marlin`], 'the Meteor Marlin needs a better rod (tier 2)');
  g = roll({ ...base, waters: new Set(['ice']), cold: true, sky: 'aurora' }, 20000);
  const g0 = roll({ ...base, waters: new Set(['ice']), cold: true, sky: '' }, 20000);
  ok(g[`${NS}aurora_icefish`] > 0 && !g0[`${NS}aurora_icefish`], `aurora night under the ice: the Aurora Icefish, and only then (${g[`${NS}aurora_icefish`]})`);
  const charCtx = { ...base, waters: new Set(['ice']), cold: true, slot: 'dawn', moon: 2 };
  ok(roll({ ...charCtx, sky: 'aurora' }, 20000)[`${NS}frostlake_char`] > 0 && !roll({ ...charCtx, sky: '' }, 20000)[`${NS}frostlake_char`],
    'the Frostlake Char: the aurora stands in for the new moon, a quiet night does not');
  ok(Sk.skyAt(true) === '' && Sk.skyAt(false) === '', 'skyAt: no sky by day (the clock is at noon)');
  ok(G.JOURNAL_SPECIES.filter(s => s.group === 'sky').map(s => s.key).sort().join() === 'aurora_icefish,meteor_marlin'
    && G.TANK_FISH.includes(`${NS}aurora_icefish`) && !G.TANK_FISH.includes(`${NS}meteor_marlin`)
    && G.CLEANING[`${NS}meteor_marlin`] && !G.CLEANING[`${NS}aurora_icefish`],
    'the Sky page has both fish; the icefish goes in a tank, not on the board; the marlin the other way round');

  // the API: registered sky catches, the capability, the state reply
  console.log = () => {};
  R._clearRegistry();
  const reg = e => R.onRegister({ id: `${NS}register_catch`, message: JSON.stringify({ api: 1, source: 'testpack', catches: [e] }) });
  const good = reg({ id: 'testpack:comet_eel', w: 5, waters: ['ocean'], sky: 'meteor' });
  const bad = reg({ id: 'testpack:comet_eel2', w: 5, waters: ['ocean'], sky: 'eclipse' });
  console.log = log;
  ok(good === 1 && bad === 0 && R.CAPABILITIES.includes('sky'), 'register_catch takes sky "meteor" / "aurora", refuses any other; api_ready lists "sky"');
  g = roll({ ...base, waters: new Set(['ocean']), depth: 6, sky: 'meteor' }, 20000);
  const g2 = roll({ ...base, waters: new Set(['ocean']), depth: 6, sky: '' }, 20000);
  ok(g['testpack:comet_eel'] > 0 && !g2['testpack:comet_eel'], 'a registered sky catch bites only on its night');
  R._clearRegistry();
  const st2 = ask('state', {});
  ok(st2.out[0]?.sky === 'none', `state_request answers sky "none" on a quiet day (${JSON.stringify(st2.out[0])})`);
}

// ---------- 13. the fish pond (1.5.0) ----------
{
  const PD = await imp('blocks/pond.js');
  ok(PD.capOf(17) === 0 && PD.capOf(18) === 4 && PD.capOf(48) === 8 && PD.capOf(96) === 12 && PD.capOf(512) === 12, 'pond: 18 / 48 / 96 blocks of water hold 4 / 8 / 12 fish');
  const P_ = G.POND;
  ok(P_[`${NS}carp`]?.[0] === 'fresh' && P_[`${NS}mackerel`]?.[0] === 'sea' && P_['minecraft:salmon']?.[0] === 'both' && P_[`${NS}mycelium_flounder`]?.[0] === 'sea',
    'pond: carp fresh, mackerel sea, salmon either, the mycelium flounder sea');
  ok(!P_[`${NS}emperor_tuna`] && !P_[`${NS}blazefin`] && !P_[`${NS}echo_ray`] && !P_[`${NS}moon_jellyfish`] && !P_[`${NS}octopus`] && !P_[`${NS}spore_seahorse`] && !P_[`${NS}oyster`] && !P_[`${NS}chorus_carp`],
    'pond: no legends, lava, Deep Dark or End creatures, jellyfish, octopus, seahorse or oyster');
  ok(P_[`${NS}crab`]?.[1] === false && P_[`${NS}lobster`]?.[1] === false && P_[`${NS}shrimp`]?.[1] === true && P_[`${NS}carp`]?.[1] === true, 'pond: crabs and lobsters live there but do not breed; fish and shrimp do');
  const fresh = { cap: 4, sea: false, fish: [] };
  ok(PD.whyNot(fresh, `${NS}carp`) === '' && PD.whyNot(fresh, `${NS}mackerel`) === 'pond_sea_fish' && PD.whyNot({ ...fresh, salt: 8 }, `${NS}mackerel`) === ''
    && PD.whyNot({ ...fresh, cap: 0 }, `${NS}carp`) === 'pond_none' && PD.whyNot(fresh, `${NS}lava_dragon_koi`) === 'pond_cannot', 'pond: whyNot gives the reason a fish stays out');
  console.log = () => {};
  R._clearRegistry();
  const reg = e => R.onRegister({ id: `${NS}register_pond_feed`, message: JSON.stringify({ api: 1, source: 'testpack', feeds: [e] }) });
  const a = reg({ id: 'testpack:corn_mash', meals: 3 }), b = reg({ id: `${NS}fish_meal`, meals: 4 }), d = reg({ id: 'testpack:corn_mash2', meals: 9 });
  console.log = log;
  ok(a === 1 && b === 0 && d === 0 && PD.mealsOf('testpack:corn_mash') === 3 && PD.mealsOf(`${NS}fish_meal`) === 4 && R.CAPABILITIES.includes('pond_feed'),
    'register_pond_feed: another pack\'s feed counts its meals; ours are closed; 1..4 meals; capability "pond_feed"');
  R._clearRegistry();
  ok(PD.mealsOf('testpack:corn_mash') === 0, 'register_pond_feed: gone when the registry is cleared');
  const M2 = await imp('world/merchant.js');
  ok(M2.FARMED_PRICE === 0.6, 'merchant: farmed fish at 60%');
}

// ---------- 14. boats and the Fishing Skiff (1.5.0) ----------
{
  const B = await imp('world/boat.js');
  let r = B.trawlStep(0, 10, 12);
  ok(r.gone === 10 && r.hauls === 0 && B.trawlStep(60, 10, 12).hauls === 1 && B.trawlStep(60, 10, 12).gone === 6, 'trawl: one haul for every 64 blocks sailed');
  ok(B.trawlStep(60, 10, 5).hauls === 0 && B.trawlStep(60, 10, 5).gone === 60, 'trawl: nothing over water less than 8 deep');
  ok(B.trawlStep(0, 500, 12).hauls === 0, 'trawl: a jump (teleport) is not sailing');
  const hauls = Array.from({ length: 400 }, () => B.haul()).flat();
  ok(hauls.every(h => B.TRAWL_CATCH.some(([id]) => id === h.typeId)) && hauls.length >= 400 && hauls.length <= 800,
    'trawl: each haul is 1-2 common small fish (their small mark is checked in the world play test)');
  ok(B.TRAWL_CATCH.every(([id]) => !G.LEGENDS.includes(id) && !G.CATCHES.find(c => c.id === id)?.sky), 'trawl: never a legend or a sky fish');
  const roll = (ctx, k) => { let n = 0; for (let i = 0; i < k; i++) if (L.rollCatch(ctx) === `${NS}meteor_marlin`) n++; return n; };
  const base = { depth: 14, rod: true, tier: 2, moon: 2, caught: new Set(), raining: false, slot: 'night', sky: 'meteor', waters: new Set(['ocean', 'deep_ocean']) };
  const onBoat = roll({ ...base, boat: true }, 40000), ashore = roll({ ...base, boat: false }, 40000);
  ok(onBoat > ashore * 1.4, `the Meteor Marlin bites more readily from a boat (${onBoat} vs ${ashore} in 40000)`);
}

// ---------- 15. register_board and register_tank (1.5.0) ----------
{
  console.log = () => {};
  R._clearRegistry();
  const n0 = warns.length;
  const reg = (kind, e) => R.onRegister({ id: `${NS}register_${kind}`, message: JSON.stringify({ api: 1, source: 'testpack', [kind + 's']: [e] }) });
  const cuts3 = [{ act: 'scale', out: [[`${NS}fish_scales`, 1]] }, { act: 'gut', out: [[`${NS}fish_offal`, 1]] }, { act: 'fillet', out: [['testpack:fillet', 2, 1, 'sized']] }];
  const good = reg('board', { id: 'testpack:trout', like: `${NS}carp`, cuts: cuts3 });
  const bads = [
    ['someone else\'s id', { id: `${NS}carp`, like: `${NS}carp`, cuts: cuts3 }],
    ['a vanilla id', { id: 'minecraft:cod', like: `${NS}carp`, cuts: cuts3 }],
    ['a like that is not on the board', { id: 'testpack:t2', like: `${NS}spore_seahorse`, cuts: cuts3 }],
    ['the wrong number of cuts', { id: 'testpack:t3', like: `${NS}carp`, cuts: cuts3.slice(0, 2) }],
    ['an unknown act', { id: 'testpack:t4', like: `${NS}carp`, cuts: [{ act: 'chop', out: [[`${NS}fish_scales`, 1]] }, ...cuts3.slice(1)] }],
    ['an output that is not open', { id: 'testpack:t5', like: `${NS}carp`, cuts: [{ act: 'scale', out: [[`${NS}otoro`, 1]] }, ...cuts3.slice(1)] }],
    ['a vanilla output', { id: 'testpack:t6', like: `${NS}carp`, cuts: [{ act: 'scale', out: [['minecraft:diamond', 1]] }, ...cuts3.slice(1)] }],
    ['too many of one output', { id: 'testpack:t7', like: `${NS}carp`, cuts: [{ act: 'scale', out: [[`${NS}fish_scales`, 9]] }, ...cuts3.slice(1)] }],
    ['two sized outputs', { id: 'testpack:t8', like: `${NS}carp`, cuts: [{ act: 'scale', out: [['testpack:fillet', 1, 1, 'sized']] }, ...cuts3.slice(1)] }],
  ].map(([why, e]) => [why, reg('board', e)]);
  const tgood = reg('tank', { id: 'testpack:trout', like: `${NS}carp`, scale: 0.8, pond: 'both', breed: true });
  const tbads = [
    ['a like that is no tank creature', { id: 'testpack:u1', like: `${NS}meteor_marlin` }],
    ['a scale out of range', { id: 'testpack:u2', like: `${NS}carp`, scale: 3 }],
    ['an unknown tank', { id: 'testpack:u3', like: `${NS}carp`, tank: 'glass' }],
    ['an unknown pond', { id: 'testpack:u4', like: `${NS}carp`, pond: 'sea' }],
  ].map(([why, e]) => [why, reg('tank', e)]);
  console.log = log;
  ok(good === 1 && R.externalBoard('testpack:trout')?.cuts?.length === 3, 'register_board: a good entry is taken');
  for (const [why, n] of bads) ok(n === 0, `register_board rejects ${why}`);
  ok(tgood === 1 && R.externalTank('testpack:trout')?.pond === 'both' && R.externalTank('testpack:trout')?.breed === true, 'register_tank: a good entry is taken');
  for (const [why, n] of tbads) ok(n === 0, `register_tank rejects ${why}`);
  ok(warns.length - n0 === bads.length + tbads.length, 'every rejected entry is reported once');
  ok(['board', 'tank'].every(c => R.CAPABILITIES.includes(c)), 'api_ready lists "board" and "tank"');
  R._clearRegistry();
}

// ---------- 16. 1.6.0: refusal keys ----------
{
  const { REASONS } = await imp('util/hint.js');
  const used = new Map();                      // key -> file
  const scripts = walkJs(join(BP, 'scripts'));
  for (const f of scripts) {
    const src = readFileSync(f, 'utf8');
    if (f.endsWith('hint.js')) continue;
    // every string literal in a refuse(...) / refuseAt(...) call's key argument (ternaries included)
    for (const m of src.matchAll(/\brefuse(?:At)?\(\s*[\w.]+\s*,\s*/g)) {
      let i = m.index + m[0].length, depth = 0, q = '';
      const s = i;
      for (; i < src.length; i++) {
        const c = src[i];
        if (q) { if (c === q && src[i - 1] !== '\\') q = ''; continue; }
        if (c === '"' || c === "'" || c === '`') q = c;
        else if ('([{'.includes(c)) depth++;
        else if (')]}'.includes(c)) { if (!depth) break; depth--; }
        else if (c === ',' && !depth) break;
      }
      for (const k of src.slice(s, i).matchAll(/"([a-z0-9_]+)"/g)) used.set(k[1], f.split('/scripts/')[1]);
    }
    // keys handed over by a helper: pond.js whyNot() returns its reason as a string
    const why = /export function whyNot[\s\S]*?\n\}/.exec(src);
    if (why) for (const k of why[0].matchAll(/"(pond_[a-z0-9_]+)"/g)) used.set(k[1], f.split('/scripts/')[1]);
  }
  const missing = [...used].filter(([k]) => !(k in REASONS));
  ok(used.size >= 60 && !missing.length, `refusal keys: all ${used.size} keys the scripts use have a category (missing: ${missing.map(([k, f]) => `${k} in ${f}`).join(', ') || 'none'})`);
  const unused = Object.keys(REASONS).filter(k => !used.has(k));
  ok(!unused.length, `refusal keys: every categorised key is used somewhere (unused: ${unused.join(', ') || 'none'})`);
}

// ---------- 17. 1.6.0: glyph characters ----------
{
  const GL = await imp('data/glyphs.js');
  const D = await imp('data/generated.js');
  const { G, PAGES, glyph, hasGlyph, fishGlyph, shadowGlyph, itemGlyph, stationGlyph, idOfKey, dots, PLACEHOLDERS } = GL;
  const chars = Object.values(G);
  ok(chars.length > 300 && new Set(chars).size === chars.length, `glyphs: ${chars.length} glyphs, no two share a character`);
  const pageHex = new Set(Object.values(PAGES).map(h => parseInt(h, 16)));
  ok(chars.every(c => c.length === 1 && pageHex.has(c.charCodeAt(0) >> 8)), 'glyphs: every glyph is one private-use character on one of the PAGES');
  const ids = D.CATCHES.map(c => c.id);
  const noFish = ids.filter(id => !hasGlyph(id) || !hasGlyph(`shadow.${id}`));
  ok(!noFish.length && ids.every(id => fishGlyph(id) === G[id] && shadowGlyph(id) === G[`shadow.${id}`]),
    `glyphs: all ${ids.length} catches (legends included) have a picture and a silhouette (missing: ${noFish.join(', ') || 'none'})`);
  ok(fishGlyph('testpack:mystery_fish') === G['fish.unknown'] && shadowGlyph('testpack:mystery_fish') === G['fish.unknown'] && glyph('no.such') === G['fish.unknown'],
    'glyphs: another pack\'s fish (or any unknown name) falls back to the generic fish');
  ok(fishGlyph('kaleidoscope_chinesefood:yellow_croaker') === G['kaleidoscope_fishing:yellow_croaker'], 'glyphs: an aliased fish uses its own glyph');
  const waters = [...new Set(D.CATCHES.flatMap(c => c.waters ?? []))];
  const noWater = waters.filter(w => !hasGlyph(`water.${w}`));
  ok(!noWater.length, `glyphs: all ${waters.length} waters have a symbol (missing: ${noWater.join(', ') || 'none'})`);
  const symbols = ['time.day', 'time.night', 'time.dawn', 'time.dusk', 'weather.rain', 'weather.thunder', 'tide.high', 'tide.low', 'tide.slack',
    ...Array.from({ length: 8 }, (_, i) => `moon.${i}`), 'sky.meteor', 'sky.aurora', 'dot.full', 'dot.empty', 'mark.x', 'mark.tick', 'mark.cross',
    'arrow.left', 'arrow.right', 'bowl.full', 'bowl.half', 'bowl.empty', 'ui.gear', 'ui.recipes', 'ui.tide_clock', 'fish.unknown', 'item.unknown'];
  const noSym = symbols.filter(s => !hasGlyph(s));
  ok(!noSym.length, `glyphs: the plan's symbols are there (missing: ${noSym.join(', ') || 'none'})`);
  const tackle = [...Object.keys(D.PARTS), ...Object.keys(D.RODS)].filter(id => !hasGlyph(id));
  ok(!tackle.length, `glyphs: every hook, line, bobber and rod has a glyph (missing: ${tackle.join(', ') || 'none'})`);
  const baits = [...new Set(D.CATCHES.flatMap(c => [...Object.keys(c.bait ?? {}), ...(c.req?.bait ? [c.req.bait] : [])]))].filter(id => !hasGlyph(id));
  ok(!baits.length, `glyphs: every bait the catches like has a glyph (missing: ${baits.join(', ') || 'none'})`);
  const dishes = D.RECIPE_HINTS.filter(h => !hasGlyph(h.id)).map(h => h.id);
  ok(D.RECIPE_HINTS.length === 102 && !dishes.length, `glyphs: all ${D.RECIPE_HINTS.length} dishes have a glyph (missing: ${dishes.join(', ') || 'none'})`);
  const ings = [...new Set(D.RECIPE_HINTS.flatMap(h => h.ingredients.map(i => i[0])))];
  const noIng = ings.filter(k => !hasGlyph(idOfKey(k)) || itemGlyph(k) === G['item.unknown']);
  ok(ings.length > 100 && !noIng.length, `glyphs: all ${ings.length} ingredients of the recipe hints have a glyph by their key (missing: ${noIng.join(', ') || 'none'})`);
  const methods = [...new Set(D.RECIPE_HINTS.map(h => h.method))].filter(m => stationGlyph(m) === G['item.unknown']);
  ok(!methods.length, `glyphs: every cooking method has a station glyph (missing: ${methods.join(', ') || 'none'})`);
  ok(idOfKey('kaleidoscope_fishing.ing.minecraft.egg') === 'minecraft:egg' && idOfKey('kaleidoscope_fishing.name.oyster') === 'kaleidoscope_fishing:oyster'
    && idOfKey('kaleidoscope_fishing.ing.kaleidoscope_cookery.raw_noodles') === 'kaleidoscope_cookery:raw_noodles', 'glyphs: recipe keys turn into item ids');
  ok(dots(3, 5) === G['dot.full'].repeat(3) + G['dot.empty'].repeat(2) && dots(9, 5) === G['dot.full'].repeat(5) && dots(-1, 2) === G['dot.empty'].repeat(2) && dots(0, 0) === '',
    'glyphs: dots(n, max) gives n filled and max - n empty dots, clamped');
  ok(PLACEHOLDERS.every(n => hasGlyph(n)) && !PLACEHOLDERS.some(n => ids.includes(n) && n.startsWith('kaleidoscope_fishing:')), `glyphs: ${PLACEHOLDERS.length} placeholders listed; none of our own fish is one`);
}

// ---------- 18. 1.6.0: lore keeps only symbols ----------
{
  const SZ = await imp('fishing/size.js');
  const { G } = await imp('data/glyphs.js');
  const { partsLore } = await imp('fishing/parts.js');
  const fake = (typeId, lore = [], maxAmount = 64) => {
    const dyn = new Map();
    return { typeId, maxAmount, _lore: [...lore], getLore() { return [...this._lore]; }, setLore(l) { this._lore = [...l]; },
      getDynamicProperty: k => dyn.get(k), setDynamicProperty(k, v) { if (maxAmount !== 1) throw new Error('stackable'); dyn.set(k, v); }, dyn };
  };
  const visible = l => l.replace(/§./g, '');
  const lore = SZ.loreFor(SZ.LARGE, 77);
  ok(lore.length === 2 && visible(lore[1]) === '★' && !/cm|\d/.test(visible(lore.join(''))), `lore: a record shows only ★, no length or "cm" (${JSON.stringify(lore)})`);
  const rec = fake(NS + 'carp', lore);
  const r = SZ.readSize(rec);
  ok(r.cls === SZ.LARGE && r.cm === 77 && r.record, 'lore: the hidden length reads back (77 cm, record, large)');
  const old = fake(NS + 'carp', ['§f◆◆', '§6★ 45 cm']);
  const ro = SZ.readSize(old);
  ok(ro.cls === 2 && ro.cm === 45 && ro.record, 'lore: an old "★ 45 cm" fish still reads as a 45 cm record');
  ok(SZ.upgradeStack(old) && old.getLore()[1] === SZ.recordLine(45) && SZ.readSize(old).cm === 45 && !SZ.upgradeStack(old),
    `lore: upgradeStack turns "★ 45 cm" into ★ with the length hidden, once (${JSON.stringify(old.getLore())})`);
  ok(JSON.stringify(SZ.upgradeLore(['§6◆◆◆', '§6★ 120 cm', '§d✦'])) === JSON.stringify(['§6◆◆◆', SZ.recordLine(120), '§d✦']), 'lore: upgradeLore leaves the other lines alone');
  const one = fake('testpack:big_fish', [], 1);
  SZ.setRecord(one, 63);
  ok(one.dyn.get(SZ.CM_KEY) === 63 && SZ.readSize(one).cm === 63, 'lore: a stack that does not stack also keeps the length in kaleidoscope_fishing:cm');
  const fish = fake(NS + 'carp', ['§7◆']);
  SZ.setRecord(fish, 30);
  ok(!fish.dyn.size && SZ.readSize(fish).cm === 30 && fish.getLore()[0] === '§7◆', 'lore: a stacking fish keeps it in the lore line only (no dynamic property on stackable items)');
  const bare = fake(NS + 'carp', []);
  bare.getDynamicProperty = () => 50;
  ok(SZ.readSize(bare).cm === 50 && SZ.readSize(bare).record, 'lore: the dynamic property alone is read too');
  const pl = partsLore({ hook: NS + 'gold_hook', line: NS + 'wire_line', bobber: NS + 'glow_bobber' });
  ok(pl.length === 1 && visible(pl[0]) === `${G[NS + 'gold_hook']} ${G[NS + 'wire_line']} ${G[NS + 'glow_bobber']}` && partsLore({}).length === 0,
    'lore: a rod shows its hook, line and bobber as three glyphs; no parts, no lore');
  const glyphOnly = s => [...visible(s)].every(c => c === ' ' || (c.charCodeAt(0) >= 0xE000 && c.charCodeAt(0) <= 0xF8FF));
  ok(glyphOnly(pl[0]), 'lore: the rod line has nothing but glyphs');
  for (const f of ['blocks/pond.js', 'blocks/tub.js']) {
    const src = readFileSync(join(BP, 'scripts', f), 'utf8');
    ok(!src.includes('lore.roe_of') && /setLore\(\[`§r\$\{fishGlyph\(id\)\}`\]\)/.test(src), `lore: ${f} labels roe with the fish's glyph, not its name`);
  }
}

console.log(failed ? `\n${failed} script test(s) FAILED` : '\nall script tests passed');
process.exit(failed ? 1 : 0);
