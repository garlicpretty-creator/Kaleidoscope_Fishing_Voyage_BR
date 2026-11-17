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
rejected({ id: 'testpack:sky_fish', w: 5, sky: 'blood_moon' }, 'an entry with a sky field');
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

console.log(failed ? `\n${failed} script test(s) FAILED` : '\nall script tests passed');
process.exit(failed ? 1 : 0);
