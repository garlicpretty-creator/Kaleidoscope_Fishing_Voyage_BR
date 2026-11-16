// Script tests, run against a mock of the Minecraft scripting API (tools/tests/mock).
//   1. every script loads (main.js and all its imports)
//   2. every custom component used by a block or item JSON is registered at startup
//   3. the bait / catch registration API accepts good entries and rejects bad ones
//   4. each legend can be caught when all its conditions hold, and never when one is missing
//   5. the 1.4 species can all be caught in their own waters
// Run through tools/run_tests.py, or: node --import ./tools/tests/mock/hooks.mjs tools/tests/test_scripts.mjs
// Exit code 1 if anything fails.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { __subs } from './mock/server.mjs';

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

console.log(failed ? `\n${failed} script test(s) FAILED` : '\nall script tests passed');
process.exit(failed ? 1 : 0);
