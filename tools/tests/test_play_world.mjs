// Play-through tests for the world side of the add-on: feasts, fish tanks, decor, station contents on explosion /
// piston, the fish merchant, food effects, clam digging, knife drops, journal pages and recipe unlocks, seagulls,
// cormorants, the Kaleidoscope Cookery bridge and the refusal sound. Everything goes through the add-on's real
// event handlers and block components in the simulation of tools/tests/sim.
// Run: node --import ./tools/tests/sim/hooks.mjs tools/tests/test_play_world.mjs        (exit code 1 on failure)
//
// The shared mock is extended here (not in sim/): timers (system.runInterval / clearRun on a tick clock, tagged by
// the file that registered them), entities with properties and events checked against the BP entity files,
// Dimension.getEntities filters, a hunger component, effects, teleport, yaw, biome, weather and script events.
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { boot, setComps, ok, finish, use, breakBlock, inv, st, clearInv, drops, P, NS, D, log, flush, fire, guard,
  importScript, GameMode, ItemStack, S, answers, BP, thrown, blockDefs } from './sim/play.mjs';

const clock = S.__clock;
const bad = m => { log.errors.push(m); throw new Error(m); };

// ---------------------------------------------------------------- timers
const timers = [];
let hseq = 1000;
const callerFile = () => { const m = /scripts\/([^:)]+?\.js)/.exec(new Error().stack.split('\n').slice(2).join('\n')); return m ? m[1] : '?'; };
S.system.runInterval = (fn, every = 1) => { const h = ++hseq; const e = Math.max(1, every | 0); timers.push({ h, fn, every: e, next: clock.abs + e, file: callerFile() }); return h; };
S.system.clearRun = h => { const i = timers.findIndex(t => t.h === h); if (i >= 0) timers.splice(i, 1); };
/** Step the world clock tick by tick, running the intervals registered by the given script files. */
function advance(ticks, files) {
  for (let i = 0; i < ticks; i++) {
    clock.abs++;
    for (const t of [...timers]) {
      if (!timers.includes(t) || !files.some(f => t.file.endsWith(f)) || clock.abs < t.next) continue;
      t.next = clock.abs + t.every;          // no catch-up runs after the clock jumped
      guard(`interval ${t.file}`, t.fn);
    }
  }
}

// ---------------------------------------------------------------- script events
const sent = [];
S.system.sendScriptEvent = (id, msg) => { if (typeof msg !== 'string') bad(`sendScriptEvent ${id}: message is not a string`); sent.push({ id, msg }); };

// ---------------------------------------------------------------- entities
const ENT = new Map();
for (const f of readdirSync(join(BP, 'entities'))) {
  try {
    const e = JSON.parse(readFileSync(join(BP, 'entities', f), 'utf8'))['minecraft:entity'];
    const fam = new Set();
    const scan = c => { for (const x of c?.['minecraft:type_family']?.family ?? []) fam.add(x); };
    scan(e.components); for (const g of Object.values(e.component_groups ?? {})) scan(g);
    ENT.set(e.description.identifier, { props: e.description.properties ?? {}, events: e.events ?? {}, families: fam });
  } catch {}
}
let eseq = 0;
class Ent {
  constructor(typeId, loc, dim = D, o = {}) {
    if (typeId !== 'minecraft:item' && typeId !== 'minecraft:squid' && !ENT.has(typeId)) bad(`spawnEntity: unknown entity ${typeId}`);
    this.id = `e${++eseq}`; this.typeId = typeId; this.location = { ...loc }; this.dimension = dim; this.isValid = true;
    this._p = new Map(); this._dyn = new Map(); this._tags = new Set(); this.events = []; this.comps = o.comps ?? {};
    this.families = new Set(o.families ?? []); dim.entities.push(this);
  }
  _def(k) { const d = ENT.get(this.typeId)?.props?.[k]; if (!d) bad(`property: ${this.typeId} has no property ${k}`); return d; }
  getProperty(k) { const d = this._def(k); return this._p.has(k) ? this._p.get(k) : d.default; }
  setProperty(k, v) {
    const d = this._def(k);
    const okv = d.type === 'bool' ? typeof v === 'boolean' : d.type === 'enum' ? d.values.includes(v)
      : typeof v === 'number' && (!d.range || (v >= d.range[0] && v <= d.range[1])) && (d.type !== 'int' || Number.isInteger(v));
    if (!okv) bad(`setProperty: ${this.typeId} ${k}=${v} out of range`);
    this._p.set(k, v);
  }
  getDynamicProperty(k) { return this._dyn.get(k); }
  setDynamicProperty(k, v) { v === undefined ? this._dyn.delete(k) : this._dyn.set(k, v); }
  addTag(t) { this._tags.add(t); return true; } hasTag(t) { return this._tags.has(t); } getTags() { return [...this._tags]; } removeTag(t) { return this._tags.delete(t); }
  triggerEvent(ev) { if (!ENT.get(this.typeId)?.events?.[ev]) bad(`triggerEvent: ${this.typeId} has no event ${ev}`); this.events.push(ev); }
  teleport(loc) { this.location = { ...loc }; }
  getRotation() { return { x: 0, y: 0 }; }
  clearVelocity() {}
  getComponent(n) { if (n === 'minecraft:type_family') return { hasTypeFamily: f => this.families.has(f) }; return this.comps[n]; }
  remove() { this.isValid = false; const a = this.dimension.entities, i = a.indexOf(this); if (i >= 0) a.splice(i, 1); }
}
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
for (const dim of [D, S.world.getDimension('minecraft:nether'), S.world.getDimension('minecraft:the_end')]) {
  dim.spawnEntity = (id, loc) => { const fam = ENT.get(id)?.families; const e = new Ent(id, loc, dim); for (const f of fam ?? []) if (!/tamed|scripted/.test(f)) e.families.add(f); return e; };
  dim.getEntities = (o = {}) => {
    let l = dim.entities.filter(e => e.isValid);
    if (o.type) l = l.filter(e => e.typeId === o.type);
    if (o.tags) l = l.filter(e => o.tags.every(t => e._tags.has(t)));
    if (o.families) l = l.filter(e => o.families.every(f => e.families.has(f)));
    if (o.location && o.maxDistance !== undefined) l = l.filter(e => dist(e.location, o.location) <= o.maxDistance);
    if (o.location && o.closest) l = l.sort((a, b) => dist(a.location, o.location) - dist(b.location, o.location)).slice(0, o.closest);
    return l;
  };
}
const itemEntity = (stack, loc) => { const e = new Ent('minecraft:item', loc); e.comps['minecraft:item'] = { itemStack: stack }; return e; };
S.world.getEntity = id => (id === P.id ? P : D.entities.find(e => e.id === id));
let biome = 'minecraft:plains', weather = 'Clear';
D.getBiome = () => ({ id: biome });
D.getWeather = () => weather;

// ---------------------------------------------------------------- player
const hunger = { currentValue: 20, effectiveMax: 20, setCurrentValue(v) { this.currentValue = v; } };
const saturation = { currentValue: 0, effectiveMax: 20, setCurrentValue(v) { this.currentValue = v; } };
const baseComp = P.getComponent.bind(P);
P.getComponent = n => (n === 'minecraft:player.hunger' ? hunger : n === 'minecraft:player.saturation' ? saturation : baseComp(n));
const EFFECTS = new Set(['speed', 'slowness', 'haste', 'mining_fatigue', 'strength', 'instant_health', 'instant_damage', 'jump_boost', 'nausea',
  'regeneration', 'resistance', 'fire_resistance', 'water_breathing', 'invisibility', 'blindness', 'night_vision', 'hunger', 'weakness', 'poison',
  'wither', 'health_boost', 'absorption', 'saturation', 'levitation', 'fatal_poison', 'conduit_power', 'slow_falling', 'bad_omen', 'village_hero', 'darkness']);
let effects = [];
P.addEffect = (id, dur, o) => { const e = String(id?.id ?? id).replace(/^minecraft:/, ''); if (!EFFECTS.has(e)) bad(`addEffect: unknown effect ${e}`); effects.push({ id: e, dur, amp: o?.amplifier ?? 0 }); };
P.teleport = loc => { P.location = { ...loc }; };
let yaw = 0;
P.getRotation = () => ({ x: 0, y: yaw });

// ---------------------------------------------------------------- helpers
const realRandom = Math.random;
function withRandom(v, fn) { const seq = Array.isArray(v) ? [...v] : null; Math.random = () => (seq ? (seq.length > 1 ? seq.shift() : seq[0]) : v); try { return fn(); } finally { Math.random = realRandom; } }
async function settle(n = 12) { for (let i = 0; i < n; i++) { await new Promise(r => setImmediate(r)); flush(); } }
const at = (x, y, z) => D.getBlock({ x, y, z });
function floor(cx, cz, r = 2, y = 64) {
  for (let dx = -r; dx <= r; dx++) for (let dz = -r; dz <= r; dz++) { D.place('minecraft:stone', { x: cx + dx, y, z: cz + dz }); D.place('minecraft:air', { x: cx + dx, y: y + 1, z: cz + dz }); }
}
const stack = (id, n = 1, lore) => { const s = new ItemStack(id.includes(':') ? id : NS + id, n); if (lore) s.setLore(lore); return s; };
function holdStack(s) { P.inv.setItem(P.selectedSlotIndex, s); }
const short = id => String(id).split(':').pop();
const sortIds = d => d.map(x => x.id).sort().join();
const dropIds = list => list.map(x => short(x.id) + (x.amount > 1 ? ` x${x.amount}` : '')).join(', ') || 'nothing';
let nx = 2000;
const spot = () => { nx += 12; return nx; };

const comps = await boot();
setComps(comps);
const G = await importScript('data/generated.js');
const { FEASTS, FOOD_EFFECTS, KC_RECIPES, GUIDEBOOK_JSON, TANK_FISH, WANT_LIST, MERCHANT_PRICES, MERCHANT_BUDGET, RECIPE_HINTS, JOURNAL_SPECIES, CLEANING, BASKET_ITEMS } = G;
const startupMessages = log.messages.length;
P.location = { x: 0.5, y: 65, z: 0.5 };

// ================================================================ 7. Kaleidoscope Cookery bridge (boot-time pings first)
{
  ok(sent.some(e => e.id === 'kaleidoscope_cookery:api_ping' && JSON.parse(e.msg).source === 'kaleidoscope_fishing'), 'bridge: pings Cookery at startup with {source}');
  ok(sent.some(e => e.id === 'kaleidoscope_cookery:guidebook_ping'), 'guidebook: pings Cookery\'s guidebook at startup');
  const n0 = sent.length;
  const caps = ['chopping_board', 'wok', 'stockpot_exact', 'steamer', 'bamboo_tray', 'teapot', 'stockpot_base_containers', 'stockpot_base_visuals'];
  fire('system.afterEvents.scriptEventReceive', { id: 'kaleidoscope_cookery:api_ready', message: JSON.stringify({ api: 1, capabilities: caps }), sourceType: 'Server' });
  const recs = sent.slice(n0).filter(e => e.id === 'kaleidoscope_cookery:register_recipe');
  const bases = sent.slice(n0).filter(e => e.id === 'kaleidoscope_cookery:register_stockpot_base');
  ok(KC_RECIPES.length === 84 && recs.length === 84, `bridge: api_ready -> all 84 recipes registered (${recs.length} of ${KC_RECIPES.length})`);
  const parsed = recs.map(e => { try { return JSON.parse(e.msg); } catch { return null; } });
  ok(parsed.every(p => p && p.api === 1 && p.source === 'kaleidoscope_fishing' && p.kind && p.recipe?.id), 'bridge: every recipe message is valid JSON with api, source, kind and recipe.id');
  const longest = Math.max(...sent.slice(n0).map(e => e.msg.length));
  ok(longest <= 2048, `bridge: every registration message is at most 2048 characters (longest ${longest})`);
  ok(new Set(parsed.map(p => p?.kind + '|' + p?.recipe?.id)).size === recs.length, 'bridge: no recipe is registered twice (kind + id unique)');
  ok(bases.length === 2 && bases.every(e => { const p = JSON.parse(e.msg); return p.filled && p.base && p.empty && p.visualBase; }), `bridge: both stockpot bases (fish stock, dashi) registered with visuals (${bases.length})`);
  const n1 = sent.length;
  fire('system.afterEvents.scriptEventReceive', { id: 'kaleidoscope_cookery:api_ready', message: JSON.stringify({ api: 1, capabilities: caps }) });
  ok(sent.length === n1, 'bridge: a second api_ready does not register again');
  fire('system.afterEvents.scriptEventReceive', { id: 'kaleidoscope_cookery:api_ready', message: 'not json' });
  ok(sent.length === n1, 'bridge: a malformed api_ready is ignored');

  const g0 = sent.length;
  fire('system.afterEvents.scriptEventReceive', { id: 'kaleidoscope_cookery:guidebook_ready', message: '{}' });
  advance(200, ['guidebookPublisher.js']);
  const gb = sent.slice(g0);
  const begin = gb.find(e => e.id === 'kaleidoscope_cookery:guidebook_begin');
  const chunks = gb.filter(e => e.id === 'kaleidoscope_cookery:guidebook_chunk');
  const end = gb.find(e => e.id === 'kaleidoscope_cookery:guidebook_end');
  const b = begin ? JSON.parse(begin.msg) : {};
  ok(!!begin && !!end && b.chunks === chunks.length && JSON.parse(end.msg).revision === b.revision, `guidebook: begin -> ${chunks.length} chunks -> end, same revision (${b.revision})`);
  const glong = Math.max(...gb.map(e => e.msg.length));
  ok(glong <= 2048, `guidebook: every message is at most 2048 characters (longest ${glong})`);
  const body = chunks.map(e => { const p = e.msg.split('\n'); return { i: Number(p[3]), rev: p[2], src: p[0], id: p[1], data: p.slice(4).join('\n') }; });
  ok(body.every((c, i) => c.i === i && c.rev === b.revision && c.src === 'kaleidoscope_fishing' && c.id === 'kaleidoscope_fishing:guidebook'), 'guidebook: chunk headers carry source, id, revision and a running index');
  const joined = body.map(c => c.data).join('');
  let gbOk = false; try { gbOk = joined === GUIDEBOOK_JSON && !!JSON.parse(joined); } catch {}
  ok(gbOk, `guidebook: the chunks rebuild the guidebook exactly and it parses as JSON (${joined.length} chars)`);
  ok(!/[^\x00-\x7f]/.test(joined), 'guidebook: the payload is ASCII-only (characters = bytes)');
  const g1 = sent.length;
  fire('system.afterEvents.scriptEventReceive', { id: 'kaleidoscope_cookery:guidebook_ready', message: '{}' });
  advance(20, ['guidebookPublisher.js']);
  ok(sent.length === g1, 'guidebook: a second guidebook_ready does not publish again');
}

// ================================================================ 1. Feasts
const FOOD_EFFECT_IDS = id => (FOOD_EFFECTS[id] ?? []).map(e => e.effect).sort().join(',');
function placeFeast(cx, cz, face = 'Up') {
  const ev = { block: at(cx, 64, cz), player: P, itemStack: P.held(), blockFace: face, isFirstEvent: true, cancel: false, faceLocation: { x: 0.5, y: 1, z: 0.5 } };
  fire('world.beforeEvents.playerInteractWithBlock', ev);
  return ev;
}
function cellsOf(id, cx, cz) { const out = []; for (let dx = -2; dx <= 2; dx++) for (let dz = -2; dz <= 2; dz++) { const b = at(cx + dx, 65, cz + dz); if (b.typeId === id) out.push(b); } return out; }
const PARTK = NS + 'part', STAGEK = NS + 'food_stage', DIRK = NS + 'dir';
for (const [bid, def] of Object.entries(FEASTS)) {
  const name = short(bid);
  const problems = [];
  const MAX = def.bites ?? 2;
  for (const y of [0, 90, 180, -90]) {
    const cx = spot(), cz = 0; floor(cx, cz); clearInv(); drops(); yaw = y; P.mode = GameMode.Survival;
    P.hold(def.item, 2);
    const ev = placeFeast(cx, cz);
    let cells = cellsOf(bid, cx, cz);
    if (!ev.cancel) problems.push('placing is not cancelled (vanilla would also act)');
    if (cells.length !== def.parts.length) { problems.push(`yaw ${y}: ${cells.length}/${def.parts.length} blocks placed`); continue; }
    if (inv(def.item) !== 1) problems.push(`yaw ${y}: item not used up (${inv(def.item)} left of 2)`);
    const parts = new Set(cells.map(c => Number(c.permutation.getState(PARTK) ?? 0)));
    if (parts.size !== def.parts.length) problems.push(`yaw ${y}: parts ${[...parts]}`);
    if (new Set(cells.map(c => c.permutation.getState(DIRK))).size !== 1) problems.push(`yaw ${y}: mixed dir states`);
    // the boat starts on the clicked spot (anchor above the clicked floor block)
    if (!cells.some(c => c.x === cx && c.z === cz)) problems.push(`yaw ${y}: nothing stands on the clicked spot`);
    // placing again on the same spot is refused and keeps the item
    placeFeast(cx, cz);
    if (inv(def.item) !== 1) problems.push(`yaw ${y}: a second feast was placed over the first`);

    if (def.decor) {
      P.hold(undefined); use(cells[0]);
      if (cellsOf(bid, cx, cz).length !== def.parts.length) problems.push('decor: using it changed it');
      breakBlock(cells[cells.length - 1]);
      const d = drops();
      if (cellsOf(bid, cx, cz).length) problems.push(`yaw ${y}: breaking one block left ${cellsOf(bid, cx, cz).length} blocks`);
      if (!(d.length === 1 && d[0].id === def.item)) problems.push(`yaw ${y}: breaking decor gave ${dropIds(d)}`);
      continue;
    }
    // full hunger: no bite
    P.hold(undefined); hunger.currentValue = 20; use(cells[0]);
    if (Number(cells[0].permutation.getState(STAGEK)) !== 0) problems.push('a full player still took a bite');
    // eat every block, every bite
    let bites = 0;
    for (const c of cells) {
      for (let k = 0; k < MAX; k++) {
        hunger.currentValue = 0; saturation.currentValue = 0; effects = [];
        use(c);
        const sNow = Number(c.permutation.getState(STAGEK));
        if (sNow !== k + 1) { problems.push(`yaw ${y}: part ${c.permutation.getState(PARTK) ?? 0} bite ${k + 1}: stage ${sNow}`); break; }
        if (hunger.currentValue !== def.nutrition) problems.push(`bite fed ${hunger.currentValue}, want ${def.nutrition}`);
        if (effects.map(e => e.id).sort().join(',') !== FOOD_EFFECT_IDS(def.item)) problems.push(`bite effects ${effects.map(e => e.id)} want ${FOOD_EFFECT_IDS(def.item)}`);
        bites++;
      }
      if (c !== cells[cells.length - 1]) {                          // an empty block alone does not clear the feast
        hunger.currentValue = 0; use(c);
        if (cellsOf(bid, cx, cz).length !== def.parts.length) problems.push(`yaw ${y}: one empty block cleared the feast early`);
      }
    }
    if (bites !== MAX * def.parts.length) problems.push(`yaw ${y}: ${bites} servings, want ${MAX * def.parts.length}`);
    drops();
    hunger.currentValue = 0; use(cells[0]);
    const d = drops();
    if (cellsOf(bid, cx, cz).length) problems.push(`yaw ${y}: emptied feast not cleared`);
    if (d.map(x => x.id).sort().join() !== [...def.remains].sort().join()) problems.push(`yaw ${y}: emptied feast gave ${dropIds(d)}, want ${def.remains.map(short).join(', ') || 'nothing'}`);
    if (P.inv.slots.some(Boolean)) problems.push(`eating gave the player items (${P.inv.slots.filter(Boolean).map(x => short(x.typeId))})`);

    // breaking: untouched -> the item back; bitten -> the remains; creative -> nothing
    P.hold(def.item, 1); placeFeast(cx, cz); cells = cellsOf(bid, cx, cz); drops();
    breakBlock(cells[cells.length - 1]);
    let dd = drops();
    if (cellsOf(bid, cx, cz).length) problems.push(`yaw ${y}: breaking one block left ${cellsOf(bid, cx, cz).length}`);
    if (!(dd.length === 1 && dd[0].id === def.item)) problems.push(`yaw ${y}: breaking an untouched feast gave ${dropIds(dd)}`);
    P.hold(def.item, 1); placeFeast(cx, cz); cells = cellsOf(bid, cx, cz);
    P.hold(undefined); hunger.currentValue = 0; use(cells[cells.length - 1]); drops();
    breakBlock(cells[0]);
    dd = drops();
    if (dd.map(x => x.id).sort().join() !== [...def.remains].sort().join()) problems.push(`yaw ${y}: breaking a bitten feast gave ${dropIds(dd)}, want ${def.remains.map(short).join(', ') || 'nothing'}`);
    P.mode = GameMode.Creative; P.hold(def.item, 1); placeFeast(cx, cz);
    if (inv(def.item) !== 1) problems.push('creative placing used up the item');
    cells = cellsOf(bid, cx, cz); breakBlock(cells[0]); dd = drops();
    if (dd.length || cellsOf(bid, cx, cz).length) problems.push(`creative break gave ${dropIds(dd)}`);
    P.mode = GameMode.Survival;
  }
  ok(!problems.length, `feast ${name}: placed in 4 directions, ${def.decor ? 'decor only' : `${def.parts.length} x ${MAX} servings`}, emptied -> ${def.remains.map(short).join('+') || 'nothing'}, break -> item / remains` +
    (problems.length ? ':\n    ' + [...new Set(problems)].slice(0, 6).join('\n    ') : ''));
}
{ // the whole tuna's slicing stages
  const cx = spot(); floor(cx, 0); clearInv(); yaw = 0; P.hold(NS + 'whole_tuna', 1); placeFeast(cx, 0);
  const c = cellsOf(NS + 'whole_tuna_block', cx, 0)[1]; P.hold(undefined);
  const seen = [Number(c.permutation.getState(STAGEK))];
  for (let i = 0; i < 3; i++) { hunger.currentValue = 0; use(c); seen.push(Number(c.permutation.getState(STAGEK))); }
  ok(seen.join() === '0,1,2,3', `feast whole_tuna: a block is sliced through stages ${seen.join(' -> ')}`);
}
{ // sneak-to-place (Cookery setting) and sneaking past a feast
  const cx = spot(); floor(cx, 0); clearInv(); P.hold(NS + 'oden_pot', 1);
  P.setDynamicProperty('kc:sneak_to_place_food', true);
  placeFeast(cx, 0);
  const none = !cellsOf(NS + 'oden_pot_block', cx, 0).length;
  P.isSneaking = true; placeFeast(cx, 0); P.isSneaking = false;
  P.setDynamicProperty('kc:sneak_to_place_food', undefined);
  ok(none && cellsOf(NS + 'oden_pot_block', cx, 0).length === 1, 'feast: with Cookery\'s sneak-to-place on, only a sneaking player sets the feast down');
}

// ================================================================ 2. Fish tanks
const TANK_FISH_ID = NS + 'tank_fish';
const fishIn = tag => D.getEntities({ type: TANK_FISH_ID, tags: [tag] });
{
  clearInv(); drops(); const x = spot(); const t = D.place(NS + 'fish_tank', { x, y: 64, z: 0 });
  const tag = `kfv_tank:s:${x},64,0`;
  holdStack(stack('mackerel', 2, ['§6◆◆◆'])); use(t);
  const idx = TANK_FISH.indexOf(NS + 'mackerel') + 1;
  ok(st(t, 'fish') + 16 * st(t, 'fish_bank') === idx && st(t, 'size') === 3 && inv('mackerel') === 1,
    `fish tank: a large mackerel goes in (fish index ${st(t, 'fish') + 16 * st(t, 'fish_bank')}, size ${st(t, 'size')}, 1 left in hand)`);
  ok(fishIn(tag).length === 1, `fish tank: one swimming fish entity appears (${fishIn(tag).length})`);
  const snd = log.sounds.length; clock.abs += 20; use(t);
  ok(inv('mackerel') === 1 && log.sounds.slice(snd).includes('note.bass'), 'fish tank: a second fish is refused (refusal sound)');
  P.selectedSlotIndex = 1; P.hold(undefined); use(t);
  const out = inv('mackerel') === 2 && P.inv.slots.filter(Boolean).every(s => s.typeId !== NS + 'mackerel' || s.getLore().includes('§6◆◆◆'));
  ok(st(t, 'fish') === 0 && st(t, 'size') === 0 && !!out && fishIn(tag).length === 0, 'fish tank: an empty hand takes the fish back with its size mark, the tank empties');
  P.selectedSlotIndex = 0;
  holdStack(stack('carp', 1, ['§f◆◆', '§6★ 77 cm'])); use(t);
  breakBlock(t);
  const d = drops();
  ok(d.length === 1 && d[0].id === NS + 'carp' && d[0].lore.includes('§6★ 77 cm') && fishIn(tag).length === 0,
    `fish tank: breaking it drops the record carp with its "★ 77 cm" (${dropIds(d)} ${JSON.stringify(d[0]?.lore)})`);
  // tank removed without a player (explosion / piston): the 10 s sweep drops the fish where the entity swam
  const t2 = D.place(NS + 'fish_tank', { x, y: 64, z: 3 });
  holdStack(stack('tuna', 1)); use(t2);
  t2.setType('minecraft:air'); drops();
  advance(200, ['tanks.js']);
  const d2 = drops();
  ok(d2.length === 1 && d2[0].id === NS + 'tuna', `fish tank: a tank gone without a player gives its fish back on the sweep (${dropIds(d2)})`);
  clearInv(); P.hold('minecraft:stick', 1); const t3 = D.place(NS + 'fish_tank', { x, y: 64, z: 6 });
  const s3 = log.sounds.length; clock.abs += 20; use(t3);
  ok(st(t3, 'fish') === 0 && log.sounds.slice(s3).includes('note.bass'), 'fish tank: a stick is refused with the refusal sound');
}
{
  clearInv(); drops(); const cx = spot(); floor(cx, 0); yaw = 0;
  P.hold(NS + 'large_fish_tank', 1);
  placeFeast(cx, 0);
  const halves = cellsOf(NS + 'large_fish_tank_block', cx, 0);
  ok(halves.length === 2 && new Set(halves.map(b => b.permutation.getState(PARTK))).size === 2 && inv('large_fish_tank') === 0,
    `large fish tank: the item sets down two halves (parts ${halves.map(b => b.permutation.getState(PARTK))}) and is used up`);
  const anchor = halves.find(b => b.permutation.getState(PARTK) === 0), other = halves.find(b => b.permutation.getState(PARTK) === 1);
  const tag = `kfv_tank:l:${anchor.x},${anchor.y},${anchor.z}`;
  const four = ['carp', 'tuna', 'octopus', 'moon_jellyfish'];
  holdStack(stack('carp', 1, ['§7◆'])); use(other);
  for (const f of four.slice(1)) { holdStack(stack(f, 1)); use(f === 'tuna' ? anchor : other); }
  ok(fishIn(tag).length === 4, `large fish tank: four fish swim in it (${fishIn(tag).length} entities)`);
  const props = fishIn(tag).map(e => e.getProperty(NS + 'tank'));
  ok(props.every(v => v === 1), 'large fish tank: its fish are posed for the large tank (tank property 1)');
  holdStack(stack('mackerel', 1)); const s5 = log.sounds.length; clock.abs += 20; use(anchor);
  ok(inv('mackerel') === 1 && log.sounds.slice(s5).includes('note.bass') && fishIn(tag).length === 4, 'large fish tank: a fifth fish is refused');
  clearInv(); use(anchor);
  ok(inv('moon_jellyfish') === 1 && fishIn(tag).length === 3, 'large fish tank: an empty hand takes the last fish put in back out');
  drops(); breakBlock(other);
  const d = drops();
  const ids = d.map(x => x.id).sort();
  ok(!cellsOf(NS + 'large_fish_tank_block', cx, 0).length && ids.join() === [NS + 'carp', NS + 'large_fish_tank', NS + 'octopus', NS + 'tuna'].sort().join() && fishIn(tag).length === 0,
    `large fish tank: breaking either half removes both and drops the tank and its three fish (${dropIds(d)})`);
  ok(d.find(x => x.id === NS + 'carp')?.lore?.includes('§7◆'), 'large fish tank: the small carp keeps its size mark');
}

{ // the large tank in every direction: two halves side by side, either half finds the other
  const bad = [];
  for (const y of [0, 90, 180, -90]) {
    clearInv(); drops(); const cx = spot(); floor(cx, 0); yaw = y;
    P.hold(NS + 'large_fish_tank', 1); placeFeast(cx, 0);
    const h = cellsOf(NS + 'large_fish_tank_block', cx, 0);
    if (h.length !== 2 || Math.abs(h[0].x - h[1].x) + Math.abs(h[0].z - h[1].z) !== 1) { bad.push(`yaw ${y}: ${h.length} halves`); continue; }
    const p1 = h.find(b => b.permutation.getState(PARTK) === 1);
    holdStack(stack('carp', 1)); use(p1); P.hold(undefined);
    const a = h.find(b => b.permutation.getState(PARTK) === 0);
    use(a);
    if (inv('carp') !== 1) bad.push(`yaw ${y}: a fish put in through part 1 did not come out through part 0`);
    holdStack(stack('carp', 1)); use(a); drops(); breakBlock(p1);
    const d = drops();
    if (cellsOf(NS + 'large_fish_tank_block', cx, 0).length || sortIds(d) !== [NS + 'carp', NS + 'large_fish_tank'].sort().join()) bad.push(`yaw ${y}: break gave ${dropIds(d)}`);
  }
  yaw = 0;
  ok(!bad.length, 'large fish tank: placed in all four directions, both halves share one tank, breaking either gives tank and fish' + (bad.length ? ':\n    ' + bad.join('\n    ') : ''));
}

// ================================================================ 3. Decor
{
  const tiers = [[['§7◆'], 1, 'bronze (small)'], [['§f◆◆'], 2, 'silver (medium)'], [['§6◆◆◆'], 3, 'gold (large)'], [['§6◆◆◆', '§6★ 80 cm'], 4, 'record seal'], [undefined, 2, 'unmarked = silver']];
  const printPerm = JSON.parse(readFileSync(join(BP, 'blocks', 'fish_print.json'), 'utf8'))['minecraft:block'].permutations.map(p => p.condition);
  for (const [lore, want, label] of tiers) {
    clearInv(); const f = D.place(NS + 'fish_print', { x: spot(), y: 64, z: 0 });
    holdStack(stack('sea_bream', 1, lore)); use(f);
    ok(st(f, 'tier') === want && inv('sea_bream') === 1, `fish print: a ${label} sea bream gives tier ${st(f, 'tier')} (want ${want}), the fish is kept`);
  }
  clearInv(); const f = D.place(NS + 'fish_print', { x: spot(), y: 64, z: 0 });
  holdStack(stack('sea_bass', 1, ['§6◆◆◆'])); use(f);
  const idx = st(f, 'fish') + 16 * st(f, 'fish_bank');
  ok(idx === 41 && printPerm.some(c => c.includes(`== ${idx} &&`) && c.includes(`tier') == 3`)), `fish print: a 1.4 species (sea bass) prints as index ${idx} and has a drawn permutation`);
  holdStack(stack('carp', 1, ['§7◆'])); use(f);
  ok(st(f, 'fish') + 16 * st(f, 'fish_bank') === 41 && st(f, 'tier') === 3, 'fish print: a printed frame is not printed over');
  const g = D.place(NS + 'fish_print', { x: spot(), y: 64, z: 0 });
  holdStack(stack('crab', 1)); use(g);
  ok(st(g, 'tier') === 0, 'fish print: a species without a print (crab) leaves the frame blank');
  const wall = comps.get(NS + 'wall_decor'), fp = comps.get(NS + 'fish_print');
  for (const [c, label, id] of [[fp, 'fish print', 'fish_print'], [wall, 'net wall', 'net_wall']]) {
    // the cardinal_direction state comes from the placement_direction trait, which the shared mock's withState does not know
    const perm = (s = {}) => ({ getState: k => s[k], withState: (k, v) => perm({ ...s, [k]: v }) });
    const up = { face: 'Up', permutationToPlace: perm(), cancel: false };
    c.beforeOnPlayerPlace(up);
    const side = { face: 'East', permutationToPlace: perm(), cancel: false };
    c.beforeOnPlayerPlace(side);
    ok(up.cancel && !side.cancel && side.permutationToPlace.getState('minecraft:cardinal_direction') === 'east', `${label}: goes on walls only, turned to the clicked face`);
  }
  const gf = blockDefs.get(NS + 'glass_float');
  const loot = gf?.components?.['minecraft:loot'];
  const lootOk = loot && JSON.parse(readFileSync(join(BP, loot), 'utf8')).pools?.[0]?.entries?.[0]?.name === NS + 'glass_float';
  ok(!!gf && !Object.keys(gf.components).some(k => k.startsWith(NS)) && lootOk, 'glass float: pure decor (no script component), breaking gives itself back');
  for (const id of ['anchor', 'catch_crate', 'dried_fish_string', 'net_wall']) {
    const l = blockDefs.get(NS + id)?.components?.['minecraft:loot'];
    ok(l && existsSync(join(BP, l)) && JSON.parse(readFileSync(join(BP, l), 'utf8')).pools?.[0]?.entries?.[0]?.name === NS + id, `${id}: breaking gives itself back`);
  }
  // fish scale needle
  for (const [lore, want] of [[['§7◆'], 1], [['§6◆◆◆'], 6], [undefined, 4]]) {
    clearInv(); const sc = D.place(NS + 'fish_scale', { x: spot(), y: 64, z: 0 });
    holdStack(stack('carp', 1, lore)); use(sc);
    ok(st(sc, 'needle') === want, `fish scale: ${lore?.[0] ?? 'unmarked'} carp settles the needle on ${st(sc, 'needle')} (want ${want})`);
  }
  // tackle rack
  clearInv(); drops(); const r = D.place(NS + 'tackle_rack', { x: spot(), y: 64, z: 0 });
  P.hold(NS + 'bamboo_fishing_rod', 1); use(r);
  const hung = st(r, 'rod_a') === 1 && !P.held();
  P.hold(NS + 'copper_hook', 1); use(r);
  P.hold('minecraft:shears', 1); use(r);
  const hookBack = inv('copper_hook') === 1;
  P.selectedSlotIndex = 2; P.hold(undefined); use(r);
  ok(hung && hookBack && st(r, 'rod_a') === 0 && inv('bamboo_fishing_rod') === 1, 'tackle rack: hang a rod, fit a hook, shears take the hook off, an empty hand takes the rod back');
  P.selectedSlotIndex = 0;
}

// ================================================================ 4. Station contents on explosion / piston
function explode(b) { const perm = b.permutation; b.setType('minecraft:air'); fire('world.afterEvents.blockExplode', { block: b, dimension: D, explodedBlockPermutation: perm, source: undefined }); }
function piston(b) { b.setType('minecraft:air'); fire('world.afterEvents.pistonActivate', { block: at(b.x + 1, b.y, b.z), dimension: D, isExpanding: true }); }
{
  for (const [how, remove] of [['explosion', explode], ['piston', piston]]) {
    clearInv(); drops();
    const r = D.place(NS + 'drying_rack', { x: spot(), y: 64, z: 0 });
    P.hold(NS + 'carp', 2); use(r); use(r); P.hold(NS + 'sea_salt', 1); use(r);
    remove(r);
    let d = drops();
    ok(sortIds(d) === [NS + 'carp', NS + 'carp', NS + 'sea_salt'].sort().join(), `${how}: a salted drying rack gives back its 2 carp and the salt (${dropIds(d)})`);
    fire('world.afterEvents.pistonActivate', {}); d = drops();
    ok(!d.length, `${how}: the rack's contents come back only once`);

    const r2 = D.place(NS + 'drying_rack', { x: spot(), y: 64, z: 0 });
    P.hold(NS + 'flying_fish', 2); use(r2); use(r2); P.hold(undefined); r2.__t = 0;
    for (let i = 0; i < 4; i++) { clock.abs += 7000; guard('tick rack', () => comps.get(NS + 'drying_rack').onTick({ block: r2, dimension: D })); }
    const dry = st(r2, 'stage') === 2;
    remove(r2); d = drops();
    ok(dry && sortIds(d) === [NS + 'dried_flying_fish', NS + 'dried_flying_fish'].join(), `${how}: a dry rack gives its dried goods (${dropIds(d)})`);

    const j = D.place(NS + 'fish_sauce_jar', { x: spot(), y: 64, z: 0 });
    P.hold(NS + 'sea_salt', 1); use(j); P.hold(G.SAUCE_FISH[1], 2); use(j); use(j);
    remove(j); d = drops();
    ok(sortIds(d) === [NS + 'sea_salt', G.SAUCE_FISH[1], G.SAUCE_FISH[1]].sort().join(), `${how}: a filling fish sauce jar gives back salt and both fish (${dropIds(d)})`);
    fire('world.afterEvents.pistonActivate', {}); ok(!drops().length, `${how}: the jar's contents come back only once`);

    const c = D.place(NS + 'fish_cleaning_board', { x: spot(), y: 64, z: 0 });
    holdStack(stack('grey_mullet', 1, ['§6◆◆◆'])); use(c);
    remove(c); d = drops();
    ok(d.length === 1 && d[0].id === NS + 'grey_mullet' && d[0].lore.includes('§6◆◆◆'), `${how}: a cleaning board gives back its whole, uncut fish with its mark (${dropIds(d)})`);
    const c2 = D.place(NS + 'fish_cleaning_board', { x: spot(), y: 64, z: 0 });
    holdStack(stack('grey_mullet', 1)); use(c2); P.hold(NS + 'fishing_knife', 1); use(c2);
    const gm = CLEANING[NS + 'grey_mullet'];
    remove(c2); d = drops();
    ok(sortIds(d) === [gm.out[0], NS + 'fish_bones'].sort().join() && d.find(x => x.id === gm.out[0])?.amount === gm.out[1],
      `${how}: a half-cut board gives the fillets and bones the last cut would (${dropIds(d)})`);
  }
}

// ================================================================ 5. Fish merchant
const MERCHANT = NS + 'fish_merchant';
const interactEntity = (m, item = P.held()) => fire('world.beforeEvents.playerInteractWithEntity', { player: P, target: m, itemStack: item, cancel: false });
{
  // he turns up by the water in the day
  clearInv(); P.location = { x: 500.5, y: 65, z: 500.5 }; clock.day = 6000;
  D.place('minecraft:water', { x: 490, y: 64, z: 490 });
  withRandom(0, () => advance(6000, ['merchant.js']));
  const ms = D.getEntities({ type: MERCHANT });
  ok(ms.length === 1, `merchant: he turns up near a player by the water in the day (${ms.length})`);
  withRandom(0, () => advance(6000, ['merchant.js']));
  ok(D.getEntities({ type: MERCHANT }).length === 1, 'merchant: only one at a time');
  const m = ms[0];
  const wants = JSON.parse(m.getDynamicProperty(NS + 'wants') ?? '[]');
  ok(wants.length === 2 && new Set(wants).size === 2 && wants.every(w => WANT_LIST.includes(w)), `merchant: exactly 2 different wanted fish (${wants.map(short).join(', ')})`);
  ok(m.getProperty(NS + 'want_a') === WANT_LIST.indexOf(wants[0]) + 1 && m.getProperty(NS + 'want_b') === WANT_LIST.indexOf(wants[1]) + 1, 'merchant: both wanted fish hang from his pole (want_a / want_b)');
  for (const w of wants) ok(MERCHANT_PRICES[w] !== undefined, `merchant: wanted ${short(w)} has a price`);
  const day1 = m.getDynamicProperty(NS + 'wants_day');
  clock.abs += 24000; advance(6000, ['merchant.js']);
  const day2 = JSON.parse(m.getDynamicProperty(NS + 'wants') ?? '[]');
  ok(day2.length === 2 && m.getDynamicProperty(NS + 'wants_day') > day1, `merchant: on his second day he rolls that day's wanted fish (${day2.map(short).join(', ')})`);

  // the journal tide page shows what he wants
  clearInv(); P.hold(NS + 'angler_journal', 1); const f0 = log.forms.length;
  answers.push(1);
  fire('world.afterEvents.itemUse', { source: P, itemStack: P.held() }); await settle();
  const tide = log.forms[f0 + 1];
  const txt = JSON.stringify(tide?.body ?? {});
  const nowWants = JSON.parse(m.getDynamicProperty(NS + 'wants') ?? '[]');
  ok(txt.includes('market_wants') && nowWants.length === 2 && nowWants.every(w => txt.includes(`name.${short(w)}"`)), 'journal: the tide page lists the merchant\'s two wanted fish');

  // selling: fixed wants so the prices are known
  m.setDynamicProperty(NS + 'wants', JSON.stringify([NS + 'tuna'.slice(1), NS + 'anglerfish'].map(x => x.replace('::', ':'))));
  m.setDynamicProperty(NS + 'wants', JSON.stringify([NS + 'tuna', NS + 'anglerfish']));
  clearInv(); P.hold(NS + 'tuna', 3);
  const sent0 = sent.length;
  const ev = interactEntity(m);
  const sold = sent.slice(sent0).filter(e => e.id === 'kaleidoscope_fishing:evt').map(e => JSON.parse(e.msg)).filter(e => e.t === 'sold');
  ok(sold.length === 1 && sold[0].id === NS + 'tuna' && sold[0].n === 3 && sold[0].paid === 12 && sold[0].p === P.id, `merchant: other packs hear "sold" with the fish, the count and the emeralds (${JSON.stringify(sold)})`);
  ok(ev.cancel && inv('tuna') === 0 && inv('minecraft:emerald') === 12, `merchant: 3 wanted tuna (2 emeralds each) pay double: ${inv('minecraft:emerald')} emeralds (want 12)`);
  clearInv(); P.hold(NS + 'octopus', 3); interactEntity(m);
  ok(inv('minecraft:emerald') === 1 && Math.abs(Number(P.getDynamicProperty(NS + 'merchant_credit')) - 0.5) < 1e-9, `merchant: 3 octopus (0.5 each, not wanted) pay 1 emerald and 0.5 credit (${inv('minecraft:emerald')}, credit ${P.getDynamicProperty(NS + 'merchant_credit')})`);
  clearInv(); holdStack(stack('octopus', 1, ['§6◆◆◆'])); interactEntity(m);
  ok(inv('minecraft:emerald') === 1 && Math.abs(Number(P.getDynamicProperty(NS + 'merchant_credit')) - 0.3) < 1e-9, `merchant: a large octopus is worth x1.6 (0.5 credit + 0.8 = 1 emerald, 0.3 left; got ${inv('minecraft:emerald')})`);
  clearInv(); holdStack(stack('tuna', 1, ['§6◆◆◆', '§6★ 120 cm'])); interactEntity(m);
  ok(inv('minecraft:emerald') === 10, `merchant: a wanted record tuna is worth 2 x 2.5 x 2 = 10 (${inv('minecraft:emerald')})`);
  const spent = Number(m.getDynamicProperty(NS + 'spent'));
  clearInv(); P.hold(NS + 'anglerfish', 64); interactEntity(m);
  const paid = inv('minecraft:emerald');
  ok(spent === 24 && paid + spent <= MERCHANT_BUDGET && paid >= MERCHANT_BUDGET - spent - 6 && inv('anglerfish') === 64 - Math.round(paid / 6 + 0.0),
    `merchant: his purse is ${MERCHANT_BUDGET}: after ${spent} he pays ${paid} more for wanted anglerfish (6 each) and leaves ${inv('anglerfish')} in hand`);
  const before = inv('minecraft:emerald'); interactEntity(m);
  ok(inv('minecraft:emerald') === before && log.sounds.includes('mob.wanderingtrader.no'), 'merchant: an empty purse buys nothing (he says no)');
  ok(P.inv.slots.filter(Boolean).every(s => s.typeId === 'minecraft:emerald' || s.typeId === NS + 'anglerfish'), 'merchant: selling only ever pays emeralds (no tackle or other items)');
  clearInv(); P.hold('minecraft:emerald', 5); const ev2 = interactEntity(m);
  ok(!ev2.cancel && inv('minecraft:emerald') === 5, 'merchant: using anything but fish opens his normal trading screen');
  clearInv(); P.hold(NS + 'carp', 1);
  const fresh = D.spawnEntity(MERCHANT, { x: 520, y: 65, z: 500 });
  interactEntity(fresh);
  const fw = JSON.parse(fresh.getDynamicProperty(NS + 'wants') ?? '[]');
  ok(fw.length === 2, 'merchant: a merchant from an older version gets two wants the first time he is asked');
  // trade table: tackle comes only from the trading file's own groups
  const trade = JSON.parse(readFileSync(join(BP, 'trading', 'kfv_fish_merchant.json'), 'utf8'));
  const tg = trade.tiers.flatMap(t => t.groups);
  const tackleSelect = tg.filter(g => g.trades.some(x => /hook|line|bobber/.test(x.gives[0].item))).reduce((a, g) => a + (g.num_to_select ?? g.trades.length), 0);
  ok(tackleSelect <= 3, `merchant: his trading screen offers at most 3 tackle trades (${tackleSelect})`);
  for (const x of D.getEntities({ type: MERCHANT })) x.remove();
  P.location = { x: 0.5, y: 65, z: 0.5 };
}

// ================================================================ 6a. Food effects
{
  const wrong = [];
  for (const [id, list] of Object.entries(FOOD_EFFECTS)) {
    effects = [];
    fire('world.afterEvents.itemCompleteUse', { source: P, itemStack: new ItemStack(id, 1), useDuration: 0 });
    const got = effects.map(e => `${e.id}:${e.dur}:${e.amp}`).sort().join();
    const want = list.map(e => `${e.effect}:${e.duration}:${e.amplifier ?? 0}`).sort().join();
    if (got !== want) wrong.push(`${short(id)} got ${got} want ${want}`);
  }
  ok(!wrong.length, `food effects: eating each of the ${Object.keys(FOOD_EFFECTS).length} dishes gives its effects` + (wrong.length ? ':\n    ' + wrong.slice(0, 5).join('\n    ') : ''));
  effects = []; fire('world.afterEvents.itemCompleteUse', { source: P, itemStack: new ItemStack('minecraft:bread', 1) });
  ok(!effects.length, 'food effects: vanilla food gets nothing extra');
  P.location = { x: 3000.5, y: 65, z: 0.5 }; floor(3000, 0, 9);
  const from = { ...P.location };
  fire('world.afterEvents.itemCompleteUse', { source: P, itemStack: new ItemStack(NS + 'chorus_sashimi', 1) });
  const moved = dist(from, P.location);
  ok(moved > 0 && at(Math.floor(P.location.x), Math.floor(P.location.y) - 1, Math.floor(P.location.z)).typeId === 'minecraft:stone' && log.sounds.includes('mob.endermen.portal'),
    `food effects: chorus sashimi blinks the eater ${moved.toFixed(1)} blocks onto solid ground`);
  P.location = { x: 3100.5, y: 65, z: 0.5 };
  const stay = { ...P.location };
  fire('world.afterEvents.itemCompleteUse', { source: P, itemStack: new ItemStack(NS + 'chorus_sashimi', 1) });
  ok(dist(stay, P.location) === 0, 'food effects: chorus sashimi over the void (no floor anywhere) stays put');
  effects = [];
  fire('system.afterEvents.scriptEventReceive', { id: 'aww:evt', message: JSON.stringify({ v: 1, t: 'autofed', p: P.id, id: NS + 'lava_eel' }) });
  ok(effects.map(e => e.id).join() === FOOD_EFFECT_IDS(NS + 'lava_eel'), `food effects: an AWW autofed message gives the dish's effects (${effects.map(e => e.id)})`);
  P.location = { x: 0.5, y: 65, z: 0.5 };
}

// ================================================================ 6b. Clam digging, earthworms
{
  const { _spotsForTests: spots } = await importScript('events/clamDigging.js');
  const sand = S.BlockPermutation.resolve('minecraft:sand');
  const dig = (x, y, z, tool = 'minecraft:iron_shovel', dim = D, perm = sand) => { const b = dim.getBlock({ x, y, z }); fire('world.afterEvents.playerBreakBlock', { block: b, brokenBlockPermutation: perm, player: P, dimension: dim, itemStackBeforeBreak: tool ? new ItemStack(tool, 1) : undefined }); return drops(); };
  const x = spot();
  D.place('minecraft:water', { x: x + 1, y: 64, z: 0 });
  drops();
  let d = withRandom(0.05, () => dig(x, 64, 0));
  ok(d.length === 1 && d[0].id === NS + 'clam', `clam digging: lucky sand dug by the water gives a clam (${dropIds(d)})`);
  d = withRandom(0.5, () => dig(x, 64, 0)); ok(!d.length, 'clam digging: unlucky sand gives nothing');
  d = withRandom(0.05, () => dig(x, 64, 0, null)); ok(!d.length, 'clam digging: sand dug without a shovel gives nothing');
  d = withRandom(0.05, () => dig(x + 8, 64, 8)); ok(!d.length, 'clam digging: sand far from water (not a beach) gives nothing');
  spots.set(`minecraft:overworld|${x + 5},64,5`, { dim: 'minecraft:overworld', x: x + 5, y: 64, z: 5, ends: clock.abs + 2400 });
  const nether = S.world.getDimension('minecraft:nether');
  d = withRandom(0.9, () => dig(x + 5, 64, 5, 'minecraft:iron_shovel', nether)); nether.drops.splice(0);
  ok(!d.length && spots.size >= 1, 'clam digging: the same x, y, z in the Nether is not the bubbling spot');
  d = withRandom(0.9, () => dig(x + 5, 64, 5));
  ok(d.length === 1 && [NS + 'clam', NS + 'oyster', NS + 'crab', NS + 'shrimp', 'minecraft:nautilus_shell'].includes(d[0].id) && !spots.has(`minecraft:overworld|${x + 5},64,5`),
    `clam digging: a bubbling spot always gives something (${dropIds(d)}) and is used up`);
  // spots appear on a beach
  spots.clear(); const bx = 4000; biome = 'minecraft:beach'; P.location = { x: bx + 0.5, y: 65, z: 0.5 };
  for (let dx = -17; dx <= 17; dx++) for (let dz = -17; dz <= 17; dz++) { D.place((dx + dz) % 2 ? 'minecraft:water' : 'minecraft:sand', { x: bx + dx, y: 64, z: dz }); D.place('minecraft:air', { x: bx + dx, y: 65, z: dz }); }
  advance(2400, ['clamDigging.js']);
  const n = spots.size;
  const inCircle = [...spots.values()].filter(s => (s.x - P.location.x) ** 2 + (s.z - P.location.z) ** 2 <= 256).length;
  ok(n >= 1 && inCircle <= 6, `clam digging: bubbling spots turn up on a beach (${n}), at most 6 within 16 blocks at low tide (${inCircle})`);
  // SUSPECTED BUG (clamDigging.js:68 vs :81): spots are placed in a 33x33 square but counted only within a radius of 16, so
  // the corners never count against the cap and a player ends up with more bubbling spots than PER_PLAYER x 2.
  // Deterministic: let every new spot land in a corner of the square (16 > distance <= 22.6 blocks, still in sight).
  spots.clear();
  const corners = [];
  for (const sx of [1, -1]) for (const sz of [1, -1]) for (const [a, b] of [[15, 15], [14, 14], [13, 13], [12, 12], [15, 13], [13, 15]]) corners.push([sx * a, sz * b]);
  const seq = corners.flatMap(([a, b]) => [(a / 16 + 1) / 2, (b / 16 + 1) / 2]);
  let k = 0;
  Math.random = () => seq[k++ % seq.length];
  try { advance(1200, ['clamDigging.js']); } finally { Math.random = realRandom; }
  ok(spots.size <= 6, `clam digging: at most 6 bubbling spots around a lone player at low tide (${spots.size} after one minute when they fall in the corners of the search square)`);
  const first = [...spots.values()][0];
  if (first) { d = dig(first.x, first.y, first.z); ok(d.length === 1, `clam digging: digging a generated spot gives ${dropIds(d)}`); }
  biome = 'minecraft:plains'; P.location = { x: 0.5, y: 65, z: 0.5 };
  advance(40, ['clamDigging.js']);
  ok(spots.size === 0, 'clam digging: spots nobody is near any more go away');
  weather = 'Rain';
  d = withRandom(0.01, () => dig(x, 70, 0, 'minecraft:iron_shovel', D, S.BlockPermutation.resolve('minecraft:grass_block')));
  ok(d.length === 1 && d[0].id === NS + 'earthworm', `earthworms: grass dug with a shovel in the rain gives an earthworm (${dropIds(d)})`);
  weather = 'Clear';
  d = withRandom(0.01, () => dig(x, 70, 0, 'minecraft:iron_shovel', D, S.BlockPermutation.resolve('minecraft:grass_block')));
  ok(!d.length, 'earthworms: not when it is dry');
}

// ================================================================ 6c. Knife drops
{
  const squid = (type = 'minecraft:squid') => ({ typeId: type, dimension: D, location: { x: 10, y: 60, z: 10 }, isValid: true });
  clearInv(); P.hold(NS + 'fishing_knife', 1); drops();
  let n = 0, tubes = 0;
  for (let i = 0; i < 20; i++) { fire('world.afterEvents.entityDie', { deadEntity: squid(i % 2 ? 'minecraft:glow_squid' : 'minecraft:squid'), damageSource: { cause: 'entityAttack', damagingEntity: P } }); const d = drops(); n += d.length; tubes += d.reduce((a, x) => a + (x.id === NS + 'squid_tube' ? x.amount : 0), 0); }
  ok(n === 20 && tubes >= 20 && tubes <= 40, `knife: 20 squid killed with the fishing knife drop ${tubes} squid tubes (1-2 each)`);
  P.hold('minecraft:iron_sword', 1);
  fire('world.afterEvents.entityDie', { deadEntity: squid(), damageSource: { damagingEntity: P } });
  ok(!drops().length, 'knife: a squid killed with a sword drops no squid tube');
  P.hold(NS + 'fishing_knife', 1);
  fire('world.afterEvents.entityDie', { deadEntity: { typeId: 'minecraft:cod', dimension: D, location: { x: 0, y: 0, z: 0 } }, damageSource: { damagingEntity: P } });
  ok(!drops().length, 'knife: other mobs drop nothing extra');
}

// ================================================================ 6d. Journal recipe unlocks and sub-pages
{
  const { learned } = await importScript('journal/recipes.js');
  P.setDynamicProperty(NS + 'recipes', undefined); clearInv();
  const r3 = RECIPE_HINTS[3];
  const s0 = log.sounds.length;
  fire('world.afterEvents.playerInventoryItemChange', { player: P, itemStack: new ItemStack(r3.id, 1), slot: 0 });
  ok(learned(P).has(r3.id) && log.sounds.slice(s0).includes('random.orb'), `journal: first holding ${short(r3.id)} teaches its recipe (with a flourish)`);
  const s1 = log.sounds.length;
  fire('world.afterEvents.playerInventoryItemChange', { player: P, itemStack: new ItemStack(r3.id, 1), slot: 0 });
  ok(!log.sounds.slice(s1).includes('random.orb'), 'journal: holding it again does not flourish again');
  P.hold(NS + 'recipe_scrap', 2); const f0 = log.forms.length;
  fire('world.afterEvents.itemUse', { source: P, itemStack: P.held() }); await settle();
  ok(learned(P).size === 2 && inv('recipe_scrap') === 1 && log.forms.length === f0 + 1 && RECIPE_HINTS.some(r => r.nameKey === log.forms[f0].title?.translate && learned(P).has(r.id)),
    `journal: reading a recipe scrap teaches one more dish, uses the scrap and shows that recipe (${learned(P).size} known)`);

  const J = 'kaleidoscope_fishing.journal.';
  const titleOf = f => f?.title?.translate ?? String(f?.title);
  async function openJournal(seq) {
    clearInv(); P.hold(NS + 'angler_journal', 1); const n = log.forms.length;
    answers.length = 0; answers.push(...seq);
    fire('world.afterEvents.itemUse', { source: P, itemStack: P.held() }); await settle(30);
    answers.length = 0;
    return log.forms.slice(n);
  }
  // recipes: index -> recipes -> a known recipe -> back -> back to the index -> close
  let fs = await openJournal([0, 3, 0, RECIPE_HINTS.length]);
  ok(fs.map(titleOf).join(' > ') === [J + 'title', J + 'recipes', r3.nameKey, J + 'recipes', J + 'title'].join(' > '), `journal: index > recipes > ${short(r3.id)} > recipes > index (${fs.map(f => short(titleOf(f))).join(' > ')})`);
  const rbody = JSON.stringify(fs[2]?.body ?? {});
  ok(rbody.includes(`method_${r3.method}`) && r3.ingredients.every(([k]) => rbody.includes(k)), 'journal: a recipe page shows its station and every ingredient');
  ok(fs[1]?.buttons?.length === RECIPE_HINTS.length + 1 && fs[1].buttons.filter(b => b.t?.translate === J + 'unknown').length === RECIPE_HINTS.length - 2, 'journal: the recipe list shows known dishes by name and the rest as unknown');
  const unknownIdx = RECIPE_HINTS.findIndex(r => !learned(P).has(r.id));
  fs = await openJournal([0, unknownIdx]);
  ok(fs.map(titleOf).slice(0, 3).join() === [J + 'title', J + 'recipes', J + 'recipes'].join(), 'journal: an unknown recipe keeps you on the recipe list');
  // tide (no merchant about)
  fs = await openJournal([1, 0]);
  ok(fs.map(titleOf).join() === [J + 'title', J + 'tide', J + 'title'].join() && JSON.stringify(fs[1].body).includes('market_none') && /tide_(high|low)/.test(JSON.stringify(fs[1].body)),
    'journal: index > tide (tide, moon, "no merchant about") > back to the index');
  // every water group, one species page each
  const { GROUPS } = await importScript('journal/journal.js');
  const first = JOURNAL_SPECIES[0];
  P.setDynamicProperty(NS + 'journal', JSON.stringify({ [first.id]: { n: 3, b: 42 } }));
  for (let gi = 0; gi < GROUPS.length; gi++) {
    const g = GROUPS[gi], list = JOURNAL_SPECIES.filter(sp => (sp.group ?? 'freshwater') === g);
    fs = await openJournal([2 + gi, 0, 0, list.length]);
    const want = [J + 'title', J + `group_${g}`, list[0].id === first.id ? `kaleidoscope_fishing.name.${first.key}` : J + 'unknown', J + `group_${g}`, J + 'title'];
    const sbody = JSON.stringify(fs[2]?.body ?? {});
    const bodyOk = list[0].id === first.id ? sbody.includes(J + 'times') && (!first.sized || sbody.includes(J + 'best')) : sbody.includes(J + 'not_yet');
    ok(fs.map(titleOf).join() === want.join() && fs[1].buttons.length === list.length + 1 && bodyOk,
      `journal: index > ${g} (${list.length} species) > ${short(list[0].id)} page > ${g} > index`);
  }
  fs = await openJournal([GROUPS.length + 3]);
  ok(fs.length === 1 && fs[0].buttons.length === GROUPS.length + 4, 'journal: the close button closes the journal');
  // 1.5.0 settings: each player's own track style; only an operator sees the minigame switch
  {
    const SW = await importScript('fishing/minigameSwitch.js');
    const SET = GROUPS.length + 2;
    SW._reset(); P.setDynamicProperty(NS + 'charset', undefined);
    delete P.commandPermissionLevel; delete P.playerPermissionLevel;
    fs = await openJournal([SET, 0, 1, 0]);
    ok(fs.map(titleOf).slice(0, 2).join() === [J + 'title', J + 'settings'].join() && fs[1].buttons.length === 2 && JSON.stringify(fs[1].body).includes('settings_op_only'),
      'journal settings: a player who is not an operator sees the track style and Back, and is told why there is no switch');
    ok(SW.charsetFor(P) === 'ascii' && SW.charset() === 'block', `journal settings: the track style is the player's own (theirs ${SW.charsetFor(P)}, the world's ${SW.charset()})`);
    ok(SW.charsetFor({ getDynamicProperty: () => undefined }) === 'block', 'journal settings: a player who has not chosen follows the world');
    ok(SW.minigameOn(), 'journal settings: without operator rights the minigame stays as it was');
    P.commandPermissionLevel = 1;
    fs = await openJournal([SET, 1, 2, 0]);
    ok(fs[1].buttons.length === 3 && !SW.minigameOn() && JSON.stringify(fs[2].body).includes('settings_minigame_off'), 'journal settings: an operator turns the minigame off for the world');
    fs = await openJournal([SET, 1, 0, 2, 0]);
    ok(SW.minigameOn() && SW.charsetFor(P) === 'block', 'journal settings: and on again; the track style switches back');
    delete P.commandPermissionLevel; P.setDynamicProperty(NS + 'charset', undefined); SW._reset();
  }
  P.setDynamicProperty(NS + 'journal', undefined);
}

// ================================================================ 6e. Seagulls
{
  const { _busyForTests: busy } = await importScript('creatures/seagull.js');
  const { stealFromRack } = await importScript('blocks/drying.js');
  const GULL = NS + 'seagull';
  const gull = loc => { const g = D.spawnEntity(GULL, loc); g.comps['minecraft:health'] = { currentValue: 4 }; return g; };   // a wild gull (not a scripted school gull)
  // rack
  clearInv(); const rx = 6000; P.location = { x: rx + 10.5, y: 65, z: 0.5 };
  const r = D.place(NS + 'drying_rack', { x: rx, y: 64, z: 0 });
  P.hold(NS + 'carp', 2); use(r); use(r); P.hold(undefined);
  const g = gull({ x: rx + 5, y: 70, z: 0 });
  withRandom(0, () => advance(80, ['seagull.js']));
  ok(st(r, 'count') === 1 && g.getProperty(NS + 'carrying') === true && g.events.includes(NS + 'carry'), `seagull: a gull swoops on an unattended drying rack and takes one fish (count ${st(r, 'count')})`);
  withRandom(0, () => advance(240, ['seagull.js']));
  ok(!g.isValid && busy.size === 0, 'seagull: the thief flies off and is gone');
  P.location = { x: rx + 2.5, y: 65, z: 0.5 };
  const g2 = gull({ x: rx + 5, y: 70, z: 0 });
  withRandom(0, () => advance(80, ['seagull.js']));
  ok(st(r, 'count') === 1 && g2.isValid && !busy.size, 'seagull: a player standing by the rack keeps gulls away');
  g2.remove();
  // fish on the ground
  P.location = { x: rx + 130.5, y: 65, z: 0.5 };            // far from the rack (more than 40 blocks), so only the fish tempts
  const fish = itemEntity(stack('mackerel', 3, ['§6◆◆◆']), { x: rx + 120, y: 64, z: 0 });
  const g3 = gull({ x: rx + 122, y: 70, z: 0 }); drops();
  withRandom(0, () => advance(60, ['seagull.js']));
  ok(fish.isValid, 'seagull: a fish lying there only a moment is not taken yet');
  withRandom(0, () => advance(140, ['seagull.js']));
  const d = drops();
  ok(!fish.isValid && d.length === 1 && d[0].id === NS + 'mackerel' && d[0].amount === 2 && d[0].lore.includes('§6◆◆◆'), `seagull: a fish left on the ground: a gull takes one, the other 2 stay with their mark (${dropIds(d)})`);
  withRandom(0, () => advance(240, ['seagull.js'])); g3.remove();
  // stealFromRack directly
  const r2 = D.place(NS + 'drying_rack', { x: rx, y: 64, z: 6 });
  P.hold(NS + 'skipjack', 1); use(r2);
  ok(!stealFromRack(r2) && st(r2, 'count') === 1, 'seagull: gulls leave the hard skipjack loins alone');
  const r3 = D.place(NS + 'drying_rack', { x: rx, y: 64, z: 9 });
  P.hold(NS + 'carp', 1); use(r3); P.hold(NS + 'sea_salt', 1); use(r3); drops();
  const took = stealFromRack(r3);
  P.hold(undefined); use(r3);
  ok(took && st(r3, 'count') === 0 && st(r3, 'kind') === 0 && !P.inv.slots.some(Boolean), 'seagull: a gull taking the last salted fish empties the rack');
  ok(!stealFromRack(at(rx + 50, 64, 0)), 'seagull: stealFromRack on something that is not a rack does nothing');
  P.location = { x: 0.5, y: 65, z: 0.5 };
}

// ================================================================ 6f. Cormorants
{
  const CORM = NS + 'cormorant';
  const cx = 7000;
  function setup(ringed) {
    const c = D.spawnEntity(CORM, { x: cx + 3.5, y: 64, z: 0.5 });
    c.families.add('kfv_cormorant_tamed'); c.comps['minecraft:tameable'] = { tamedToPlayerId: P.id };
    c.setProperty(NS + 'ringed', ringed);
    return c;
  }
  P.location = { x: cx + 0.5, y: 64, z: 0.5 };
  D.place('minecraft:water', { x: cx + 3, y: 63, z: 0 }); D.place('minecraft:water', { x: cx + 3, y: 62, z: 0 });
  clearInv(); drops();
  let c = setup(true);
  withRandom(0.5, () => advance(600, ['cormorant.js']));
  let d = drops();
  ok(c.events.includes(NS + 'dive') && c.events.includes(NS + 'surface') && d.length === 1 && d[0].id === NS + 'sweetfish' && d[0].lore.includes('§7◆'),
    `cormorant: a ringed, tamed cormorant dives and brings its owner a small fish (${dropIds(d)} ${JSON.stringify(d[0]?.lore)})`);
  ok(c.getProperty(NS + 'diving') === false && c.getProperty(NS + 'carrying') === false, 'cormorant: it is neither diving nor carrying afterwards');
  c.remove();
  clearInv(); P.inv.setItem(5, new ItemStack(NS + 'fish_basket', 1));
  c = setup(true);
  withRandom(0.5, () => advance(600, ['cormorant.js']));
  d = drops();
  const creel = JSON.parse(P.inv.getItem(5)?.getDynamicProperty(NS + 'creel') ?? '{}');
  ok(!d.length && Object.values(creel).reduce((a, b) => a + b, 0) >= 1, `cormorant: with a Fish Creel carried, the fish goes into the creel (${JSON.stringify(creel)})`);
  c.remove(); clearInv();
  c = setup(false);
  withRandom(0.5, () => advance(600, ['cormorant.js']));
  d = drops();
  ok(c.events.includes(NS + 'dive') && !d.length && log.sounds.includes('random.eat'), 'cormorant: without the ring it swallows the fish itself');
  c.remove();
  P.location = { x: cx + 40.5, y: 64, z: 0.5 };
  c = setup(true);
  withRandom(0.5, () => advance(600, ['cormorant.js']));
  ok(!c.events.includes(NS + 'dive'), 'cormorant: it does not fish when its owner is far away');
  c.remove();
  // v1.4.1: in the game the tame event removes the wild group and with it minecraft:tameable, so a tamed cormorant
  // has no tamedToPlayerId. The owner comes from the tame event: the player who fed it is written to a dynamic property.
  P.location = { x: cx + 0.5, y: 64, z: 0.5 };
  clearInv(); drops();
  c = D.spawnEntity(CORM, { x: cx + 3.5, y: 64, z: 0.5 });
  fire('world.beforeEvents.playerInteractWithEntity', { player: P, target: c, itemStack: stack('grass_carp'), cancel: false });
  fire('world.afterEvents.dataDrivenEntityTrigger', { entity: c, eventId: NS + 'on_tame' });
  c.families.add('kfv_cormorant_tamed'); c.setProperty(NS + 'ringed', true);
  ok(c.getDynamicProperty(NS + 'owner') === P.id && !c.comps['minecraft:tameable'], 'cormorant: taming records the player who fed it as the owner');
  let lowest = Infinity;
  const watch = S.system.runInterval(() => { if (c.getProperty(NS + 'diving')) lowest = Math.min(lowest, c.location.y); }, 1);
  timers[timers.length - 1].file = 'cormorant.js';
  withRandom(0.5, () => advance(600, ['cormorant.js']));
  S.system.clearRun(watch);
  d = drops();
  ok(c.events.includes(NS + 'dive') && c.events.includes(NS + 'surface') && d.length === 1,
    `cormorant: tamed in play (no tameable component left), it still dives and brings its owner a fish (${dropIds(d)})`);
  ok(lowest <= 62, `cormorant: while diving it is held fully under water (lowest y ${lowest}, water surface block 63)`);
  c.remove();
  // a cormorant tamed before v1.4.1 (no owner property, no tameable component) fishes for the player next to it
  c = D.spawnEntity(CORM, { x: cx + 3.5, y: 64, z: 0.5 }); c.families.add('kfv_cormorant_tamed');
  withRandom(0.5, () => advance(600, ['cormorant.js']));
  ok(c.events.includes(NS + 'dive'), 'cormorant: an older tamed cormorant with no recorded owner fishes for the nearest player');
  c.remove(); drops();
  // every raw fish of the add-on tames, tempts and heals it (not only the vanilla fish and five river/sea fish)
  const cj = JSON.parse(readFileSync(join(BP, 'entities', 'cormorant.json'), 'utf8'))['minecraft:entity'];
  const tame = new Set(cj.component_groups[NS + 'wild']['minecraft:tameable'].tame_items);
  const tempt = new Set(cj.component_groups[NS + 'wild']['minecraft:behavior.tempt'].items);
  const heal = new Set(cj.component_groups[NS + 'tamed']['minecraft:healable'].items.map(x => x.item));
  const legends = new Set(JSON.parse(readFileSync(join(BP, '..', 'tools', 'data', 'LEGENDS.json'), 'utf8')));
  const notFish = /crab|crayfish|lobster|shrimp|jellyfish|octopus|oyster|clam|squid/;
  const modFish = [];
  for (const f of readdirSync(join(BP, 'items'))) {
    try {
      const it = JSON.parse(readFileSync(join(BP, 'items', f), 'utf8'))['minecraft:item'];
      const id = it.description.identifier;
      if ((it.components['minecraft:tags']?.tags ?? []).includes('minecraft:is_fish') && !legends.has(id) && !notFish.test(id)) modFish.push(id);
    } catch {}
  }
  const missing = modFish.filter(id => !tame.has(id) || !tempt.has(id) || !heal.has(id));
  ok(modFish.length >= 25 && !missing.length, `cormorant: every mod fish (${modFish.length}) tames, tempts and heals it (missing: ${missing.join(', ') || 'none'})`);
  ok(tame.has(NS + 'grass_carp') && tame.has(NS + 'sea_bass') && tame.has('minecraft:cod'), 'cormorant: a mod fish such as grass carp or sea bass tames it, as cod does');
  P.location = { x: 0.5, y: 65, z: 0.5 };
}

// ================================================================ 8. Refusals: a sound, never text
{
  const { refuse } = await importScript('util/hint.js');
  const s0 = log.sounds.filter(s => s === 'note.bass').length;
  clock.abs += 100; refuse(P, 'rack_full', 3); refuse(P, 'rack_full', 3);
  const s1 = log.sounds.filter(s => s === 'note.bass').length;
  clock.abs += 11; refuse(P, 'rack_full', 3);
  const s2 = log.sounds.filter(s => s === 'note.bass').length;
  ok(s1 - s0 === 1 && s2 - s1 === 1, 'refusals: one refusal sound, at most one every 10 ticks');
  // a handful of refused uses across the stations
  const m0 = log.messages.length, b0 = log.sounds.filter(s => s === 'note.bass').length;
  const cases = [
    () => { const r = D.place(NS + 'drying_rack', { x: spot(), y: 64, z: 0 }); P.hold('minecraft:stick', 1); use(r); },
    () => { const j = D.place(NS + 'fish_sauce_jar', { x: spot(), y: 64, z: 0 }); P.hold(G.SAUCE_FISH[0], 1); use(j); },
    () => { const j = D.place(NS + 'fish_sauce_jar', { x: spot(), y: 64, z: 0 }); P.hold(NS + 'sea_salt', 1); use(j); P.hold('minecraft:stick', 1); use(j); },
    () => { const c = D.place(NS + 'fish_cleaning_board', { x: spot(), y: 64, z: 0 }); P.hold('minecraft:stick', 1); use(c); },
    () => { const c = D.place(NS + 'fish_cleaning_board', { x: spot(), y: 64, z: 0 }); P.hold(undefined); use(c); },
    () => { const t = D.place(NS + 'fish_tank', { x: spot(), y: 64, z: 0 }); P.hold('minecraft:stick', 1); use(t); },
  ];
  for (const f of cases) { clearInv(); clock.abs += 20; f(); }
  const b1 = log.sounds.filter(s => s === 'note.bass').length;
  ok(b1 - b0 === cases.length && log.messages.length === m0, `refusals: ${cases.length} refused station uses each play the refusal sound and send no chat text (${b1 - b0} sounds, ${log.messages.length - m0} messages)`);
}
ok(log.messages.length === startupMessages && startupMessages === 0, `no chat text at all during the whole play-through (${log.messages.length}: ${log.messages.slice(0, 3).join(' | ')})`);
ok(!log.commands.some(c => /^\s*\/?(tellraw|say|tell|msg|title)\b/.test(c)), 'no chat text through commands either');

// ================================================================ 1.5.0: wolves, cats and the knife's Looting
{
  const PETS = await importScript('creatures/pets.js');
  const animal = (typeId, { isTamed = false, target, hp = 10, max = 10 } = {}) => {
    const a = { typeId, id: 'a' + Math.random(), isValid: true, dimension: D, location: { x: 3, y: 64, z: 3 }, target, tamedBy: undefined, effects: [],
      health: { currentValue: hp, effectiveMax: max, setCurrentValue(v) { this.currentValue = v; } },
      addEffect(id, t, o) { a.effects.push([id, t, o?.amplifier]); },
      getComponent(n) {
        if (n === 'minecraft:is_tamed') return a.tamedBy || isTamed ? {} : undefined;
        if (n === 'minecraft:tameable') return a.tamedBy || isTamed ? undefined : { tame(p) { a.tamedBy = p; return true; } };
        if (n === 'minecraft:health') return a.health;
        return undefined;
      } };
    return a;
  };
  const offerTo = (a, rnd) => withRandom(rnd, () => interactEntity(a));

  // Fish Bones and the wolf
  let wolf = animal('minecraft:wolf');
  clearInv(); P.hold(NS + 'fish_bones', 3);
  let ev = offerTo(wolf, 0.9);
  ok(ev.cancel && !wolf.tamedBy && inv('fish_bones') === 2, `wolf: Fish Bones are taken; two times in three the wolf is not tamed yet (${inv('fish_bones')} left)`);
  offerTo(wolf, 0);
  ok(wolf.tamedBy === P && inv('fish_bones') === 1, 'wolf: one chance in three, the wolf is tamed to the player who offered');
  ev = offerTo(wolf, 0);
  ok(inv('fish_bones') === 1, 'wolf: a tamed wolf takes no more Fish Bones');
  wolf = animal('minecraft:wolf', { target: P });
  offerTo(wolf, 0);
  ok(!wolf.tamedBy && inv('fish_bones') === 1, 'wolf: an angry wolf cannot be tamed and eats nothing');
  P.hold('minecraft:stick', 1); wolf = animal('minecraft:wolf');
  ok(!interactEntity(wolf).cancel && !wolf.tamedBy, 'wolf: only Fish Bones do it');
  P.mode = GameMode.Creative; P.hold(NS + 'fish_bones', 1); wolf = animal('minecraft:wolf');
  offerTo(wolf, 0);
  ok(wolf.tamedBy === P && inv('fish_bones') === 1, 'wolf: creative mode keeps the Fish Bones');
  P.mode = GameMode.Survival;

  // our fish and the cat
  let cat = animal('minecraft:cat');
  clearInv(); P.hold(NS + 'carp', 2);
  ev = offerTo(cat, 0);
  ok(ev.cancel && cat.tamedBy === P && inv('carp') === 1, 'cat: a carp tames a stray cat (one chance in three), and is eaten');
  for (const [id, why] of [[NS + 'emperor_tuna', 'a legend'], [NS + 'shrimp', 'shellfish'], [NS + 'crab', 'a crab'], ['minecraft:stick', 'a stick']]) {
    cat = animal('minecraft:cat'); clearInv(); P.hold(id, 1);
    ok(!interactEntity(cat).cancel && !cat.tamedBy && P.held()?.amount === 1, `cat: ${why} is not offered to a cat`);
  }
  ok(PETS.isCatFish(new ItemStack(NS + 'sweetfish', 1)) && PETS.isCatFish(new ItemStack(NS + 'lobster', 1)) === new ItemStack(NS + 'lobster', 1).hasTag('minecraft:is_fish'),
    'cat: what counts is the fish tag, as for the cormorant');
  cat = animal('minecraft:cat', { isTamed: true, hp: 6, max: 10 }); clearInv(); P.hold(NS + 'carp', 2);
  interactEntity(cat);
  ok(cat.health.currentValue === 8 && inv('carp') === 1, `cat: a hurt, tamed cat eats a fish and heals a heart (${cat.health.currentValue}/10)`);
  cat = animal('minecraft:cat', { isTamed: true, hp: 10, max: 10 });
  interactEntity(cat);
  ok(inv('carp') === 1, 'cat: a healthy tamed cat is not fed');

  // stray cats stand still for a player who holds a fish and walks
  const stray = animal('minecraft:cat'), pet = animal('minecraft:cat', { isTamed: true });
  const getEntities0 = D.getEntities;
  D.getEntities = o => (o?.type === 'minecraft:cat' ? [stray, pet] : getEntities0(o));
  clearInv(); P.hold(NS + 'carp', 1); P.isSprinting = false;
  PETS.holdStrays();
  ok(stray.effects.length === 1 && stray.effects[0][0] === 'slowness' && pet.effects.length === 0, 'cat: a stray stands still while a walking player holds a fish; a tamed cat is left alone');
  P.isSprinting = true; PETS.holdStrays();
  ok(stray.effects.length === 1, 'cat: sprinting at it does not hold a stray');
  P.isSprinting = false; P.hold(NS + 'emperor_tuna', 1); PETS.holdStrays();
  ok(stray.effects.length === 1, 'cat: a legend in hand does not hold a stray');
  D.getEntities = getEntities0;

  // Looting on the knife
  const IP = S.ItemStack.prototype, getComponent0 = IP.getComponent;
  IP.getComponent = function (n) { return n === 'minecraft:enchantable' && this.typeId === NS + 'fishing_knife' ? { getEnchantment: id => (id === 'looting' ? { level: 3 } : undefined) } : getComponent0.call(this, n); };
  clearInv(); P.hold(NS + 'fishing_knife', 1); drops();
  let tubes = 0;
  for (let i = 0; i < 200; i++) { fire('world.afterEvents.entityDie', { deadEntity: { typeId: 'minecraft:squid', dimension: D, location: { x: 10, y: 60, z: 10 }, isValid: true }, damageSource: { damagingEntity: P } }); tubes += drops().reduce((a, d) => a + d.amount, 0); }
  IP.getComponent = getComponent0;
  ok(tubes > 500 && tubes <= 1000, `knife: Looting III brings more squid (200 kills gave ${tubes}; 1-2 each without it, up to 5 with)`);
}

finish('play (world)');
