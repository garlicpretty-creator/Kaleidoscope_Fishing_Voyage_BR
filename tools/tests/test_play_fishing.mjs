// Play-through tests for FISHING: cast a rod, wait for a bite, strike, play (or skip) the reeling minigame, land
// the catch; tackle parts on the Tackle Rack, bait, the gold legend bobber, the Ice Hole and tip-ups, the Shrimp
// Trap and the Fish Creel. Everything goes through the add-on's real event handlers and its system.runInterval loop.
// Run: node --import ./tools/tests/sim/hooks.mjs tools/tests/test_play_fishing.mjs        (exit code 1 on failure)
//
// The shared mock (tools/tests/sim) is extended HERE only:
//   - system.runInterval / clearRun really schedule (only loops started after boot, i.e. the rod's tick loop)
//   - the bobber is a real-ish entity: projectile flight (gravity / inertia from entities/bobber.json), sticks in
//     solid blocks, slows in liquids, teleport / triggerEvent / setProperty (validated against the entity's range)
//   - rods have a durability component (max from the item JSON), so wear can be asserted
//   - Dimension.getBlockFromRay (used for the End void and the cave sky check)
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { boot, setComps, ok, finish, use, tick, breakBlock, inv, st, clearInv, P, NS, D, log, flush, fire, importScript,
  answers, S, BP, clock, GameMode, guard, sent, evts } from './sim/play.mjs';

// ---------------------------------------------------------------- mock extensions (this file only)
// timers: loops created after boot run on our clock; everything earlier (schools, gulls, merchant...) stays idle
const loops = new Map();
let nextLoop = 100, booted = false;
S.system.runInterval = (fn, every = 1) => { const id = nextLoop++; if (booted) loops.set(id, { fn, every, at: clock.abs + every }); return id; };
S.system.clearRun = id => { loops.delete(id); };

// the bobber entity
const BOBBER_ID = NS + 'bobber';
const bobberDef = JSON.parse(readFileSync(join(BP, 'entities', 'bobber.json'), 'utf8'))['minecraft:entity'];
const PROPS = bobberDef.description.properties;
const proj = bobberDef.component_groups[NS + 'flying']['minecraft:projectile'];
const bobbers = [];
let castTo = null;                    // when set, the next cast lands exactly here (instead of flying)
const solid = b => b && !b.isAir && !b.isLiquid;
class Bobber {
  constructor(dim, loc) {
    this.typeId = BOBBER_ID; this.id = 'bobber' + bobbers.length; this.dimension = dim; this.location = { ...loc };
    this.isValid = true; this.v = { x: 0, y: 0, z: 0 }; this.props = {}; this.events = []; this.flying = true; this.stuck = false;
  }
  getComponent(n) {
    if (n !== 'minecraft:projectile') return undefined;
    return { owner: undefined, shoot: v => {
      this.v = { ...v };
      if (castTo) { this.location = { ...castTo }; this.v = { x: 0, y: 0, z: 0 }; this.stuck = true; castTo = null; }
    } };
  }
  applyImpulse(v) { this.v = { x: this.v.x + v.x, y: this.v.y + v.y, z: this.v.z + v.z }; }
  clearVelocity() { this.v = { x: 0, y: 0, z: 0 }; }
  getVelocity() { return { ...this.v }; }
  teleport(l) { if (!this.isValid) throw new Error('bobber removed'); this.location = { ...l }; }
  triggerEvent(e) {
    if (!bobberDef.events?.[e]) { log.errors.push(`bobber.triggerEvent: no event ${e}`); throw new Error(`no event ${e}`); }
    this.events.push(e); if (e === NS + 'float') this.flying = false;
  }
  setProperty(k, v) {
    const d = PROPS[k];
    if (!d) { log.errors.push(`bobber.setProperty: no property ${k}`); throw new Error(`no property ${k}`); }
    if (d.type === 'int' && (!Number.isInteger(v) || v < d.range[0] || v > d.range[1])) { log.errors.push(`bobber ${k}=${v} out of range`); throw new Error('out of range'); }
    this.props[k] = v;
  }
  getProperty(k) { return this.props[k] ?? PROPS[k]?.default; }
  remove() { this.isValid = false; }
  physics() {                         // one game tick of the "flying" component group
    if (!this.isValid || !this.flying || this.stuck) return;
    const n = { x: this.location.x + this.v.x, y: this.location.y + this.v.y, z: this.location.z + this.v.z };
    const b = this.dimension.getBlock(n);
    if (solid(b)) { this.stuck = true; this.v = { x: 0, y: 0, z: 0 }; return; }   // stick_in_ground
    this.location = n;
    const k = b.isLiquid ? proj.liquid_inertia : proj.inertia;
    this.v = { x: this.v.x * k, y: (this.v.y - proj.gravity) * k, z: this.v.z * k };
    if (this.location.y < -64) this.isValid = false;
  }
}
const DimProto = Object.getPrototypeOf(D);
const spawnEntity0 = DimProto.spawnEntity;
DimProto.spawnEntity = function (id, loc) {
  if (id !== BOBBER_ID) return spawnEntity0.call(this, id, loc);
  const b = new Bobber(this, loc); bobbers.push(b); return b;
};
DimProto.getBlockFromRay = function (from, dir, opts = {}) {
  const max = opts.maxDistance ?? 64;
  for (let t = 0; t <= max; t += 0.25) {
    const b = this.getBlock({ x: from.x + dir.x * t, y: from.y + dir.y * t, z: from.z + dir.z * t });
    if (b.isAir) continue;
    if (b.isLiquid && !opts.includeLiquidBlocks) continue;
    return { block: b, faceLocation: { x: 0.5, y: 0.5, z: 0.5 } };
  }
  return undefined;
};
// rods wear: a durability component stored on the stack (copied by clone)
const IP = S.ItemStack.prototype, getComponent0 = IP.getComponent, clone0 = IP.clone;
IP.getComponent = function (n) {
  const max = S.__itemDefs.get(this.typeId)?.components?.['minecraft:durability']?.max_durability;
  if (max && (n === 'minecraft:durability' || n === 'durability')) {
    const it = this;
    return { get damage() { return it._damage ?? 0; }, set damage(v) { if (v < 0 || v > max) log.errors.push(`durability ${v} out of 0..${max}`); it._damage = v; }, maxDurability: max };
  }
  return getComponent0.call(this, n);
};
IP.clone = function () { const s = clone0.call(this); s._damage = this._damage; return s; };

// ---------------------------------------------------------------- boot
setComps(await boot());
booted = true;
const rod = await importScript('fishing/rod.js');
const sw = await importScript('fishing/minigameSwitch.js');
const { LURE, LEGEND_SET, CATCH_BY_ID } = await importScript('fishing/loot.js');
const { readParts } = await importScript('fishing/parts.js');
const { KEEPSAKES } = await importScript('data/generated.js');
const MG_TRACK = (await importScript('data/minigame.js')).MG.TRACK;
const W = S.world;
const NETHER = W.getDimension('minecraft:nether'), END = W.getDimension('minecraft:the_end');

// ---------------------------------------------------------------- helpers
/** Advance n game ticks: bobber physics, then every due loop (the rod's tick runs every 2). */
function advance(n = 1) {
  for (let i = 0; i < n; i++) {
    clock.abs++;
    for (const b of bobbers) b.physics();
    for (const [id, l] of [...loops]) if (loops.has(id) && clock.abs >= l.at) { l.at += l.every; guard('interval', l.fn); }
  }
  flush();
}
const session = () => rod._sessionsForTests.get(P.id);
const phase = () => session()?.phase;
function waitFor(pred, max = 3000) { for (let i = 0; i < max; i++) { if (pred()) return true; advance(1); } return pred(); }
// pressing the use key with a rod: the game sends itemStartUse and itemUse together; letting go sends itemReleaseUse
const press = () => { const it = P.held(); fire('world.afterEvents.itemStartUse', { source: P, itemStack: it, useDuration: 3600 }); fire('world.afterEvents.itemUse', { source: P, itemStack: it }); };
const release = () => fire('world.afterEvents.itemReleaseUse', { source: P, itemStack: P.held(), useDuration: 3500 });
const click = () => { press(); release(); };
const cool = () => advance(9);                       // past the rod's 8-tick use cooldown
const setBox = (dim, id, x0, x1, y0, y1, z0, z1) => { for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) for (let z = z0; z <= z1; z++) dim.place(id, { x, y, z }); };
const allDrops = () => [D, NETHER, END].flatMap(d => d.drops.splice(0));
const dmg = () => P.held()?._damage ?? 0;
const STYLE = NS + 'style';
const rodItem = n => NS + n + '_fishing_rod';
function minigame(on) { fire('system.afterEvents.scriptEventReceive', { id: NS + 'minigame', message: on ? 'on' : 'off', sourceEntity: P }); }
function stand(dim, x, y, z) { P.dimension = dim; P.location = { x, y, z }; }
/** Play the hooked fish to the end. how: 'bot' (minigame: keep the box on the fish), 'avoid' (minigame: keep the box
 *  away from it), 'idle' (do nothing), 'reel' (minigame off: reel only while the fish rests), 'yank' (minigame off:
 *  reel while it pulls). A 'bot' or 'reel' angler whose fish gets away strikes again at the next bite (up to 4 times). */
function fight(how, max = 4000, again = 4) {
  const s = session(); let held = false;
  if (!s) return s;
  for (let i = 0; i < max && session() === s; i++) {
    if (s.phase === 'game' && (how === 'bot' || how === 'avoid')) {
      const g = s.game;
      const want = how === 'bot' ? g.box + g.size / 2 + g.v * 3 < g.fish : g.fish < MG_TRACK / 2;
      if (want !== held) { want ? press() : release(); held = want; }
    } else if (s.phase === 'game' && held) { release(); held = false; }
    if (s.phase === 'rest' && how === 'reel') press();
    if (s.phase === 'pull' && how === 'yank') press();
    if (s.phase === 'waiting' || s.phase === 'bite') break;   // the fish got away: back to waiting
    advance(1);
  }
  if (held) release();
  if (again > 0 && (how === 'bot' || how === 'reel') && session() === s && (s.phase === 'waiting' || s.phase === 'bite')) {
    if (waitFor(() => s.phase === 'bite' || session() !== s, 2600) && session() === s) { press(); return fight(how, max, again - 1); }
  }
  return s;
}
/** Cast from where the player stands (or exactly at `at`), wait for the bite and strike. Returns the session. */
function castAndHook(at) {
  if (at) castTo = at;
  press(); release();
  const s = session();
  if (!s) return undefined;
  if (!waitFor(() => s.phase === 'waiting' || session() !== s, 200)) return s;
  if (!waitFor(() => s.phase === 'bite' || session() !== s, 2600)) return s;
  if (session() !== s) return s;
  press();
  return s;
}
/** Abandon a session by switching the hotbar slot away from the rod (the loop ends it). */
function drop(s) { const i = P.selectedSlotIndex; P.selectedSlotIndex = 35; advance(3); P.selectedSlotIndex = i; cool(); return session() !== s; }

// ---------------------------------------------------------------- the worlds
// a river-like pond in front of the player (depth 4 at sea level: "river" without the biome API)
setBox(D, 'minecraft:stone', -4, 4, 64, 64, -3, 2);
setBox(D, 'minecraft:water', -4, 4, 60, 63, 3, 18);
setBox(D, 'minecraft:stone', -4, 4, 59, 59, 3, 18);
const atPond = () => stand(D, 0.5, 65, 0.5);
// a frozen lake at x 100: ice on top of water, the player on the ice
setBox(D, 'minecraft:ice', 96, 104, 64, 64, -4, 8);
setBox(D, 'minecraft:water', 96, 104, 58, 63, -4, 8);
// a nether lava lake (depth 5)
setBox(NETHER, 'minecraft:netherrack', -4, 4, 63, 63, -3, 2);
setBox(NETHER, 'minecraft:lava', -4, 4, 58, 62, 3, 18);
setBox(NETHER, 'minecraft:netherrack', -4, 4, 57, 57, 3, 18);
// an End island (nothing below its edge) and an End pond at x 40
setBox(END, 'minecraft:end_stone', -3, 3, 60, 60, -3, 1);
setBox(END, 'minecraft:end_stone', 36, 44, 60, 60, -3, 18);
setBox(END, 'minecraft:water', 36, 44, 61, 63, 3, 18);
setBox(END, 'minecraft:end_stone', 36, 44, 61, 63, -3, 2);

clock.day = 6000; clock.moon = 2;
D.getWeather = () => 'Clear';

// ---------------------------------------------------------------- 1. casting, bite, landing (each rod)
{
  clearInv(); atPond(); minigame(true); allDrops();
  P.hold(rodItem('bamboo'));
  const n = bobbers.length;
  press(); release();
  const s = session();
  ok(bobbers.length === n + 1 && s?.phase === 'flying', `bamboo rod: casting spawns a bobber and starts a session (${s?.phase})`);
  ok(waitFor(() => s.phase === 'waiting', 200), `bamboo rod: the bobber lands on the pond and floats (phase ${s.phase}, at z ${bobbers.at(-1).location.z.toFixed(1)})`);
  ok(s.ctx?.waters?.has('river') && s.ctx.depth === 4, `bamboo rod: the water reads as river, depth 4 (${[...(s.ctx?.waters ?? [])]}, ${s.ctx?.depth})`);
  ok(bobbers.at(-1).events.includes(NS + 'float'), 'bamboo rod: the bobber switches to its floating group');
  ok(s.biteAt - s.age >= 120 && s.biteAt - s.age <= 400, `bamboo rod: the bite is due within the rod's 120-400 ticks (${s.biteAt - s.age})`);
  const y0 = bobbers.at(-1).location.y;
  ok(waitFor(() => s.phase === 'bite', 600), `bamboo rod: a bite comes (age ${s.age})`);
  advance(2);
  ok(bobbers.at(-1).location.y < y0 - 0.2, `bamboo rod: on a bite the bobber is pulled under (${y0.toFixed(2)} -> ${bobbers.at(-1).location.y.toFixed(2)})`);
  const sent0 = sent.length;                 // a small fish lands on the strike itself, a big one after the fight
  cool(); press();
  const id = s.catchId;
  ok(!!id, `bamboo rod: striking during the bite hooks something (${id})`);
  fight('bot');
  const d = allDrops();
  const heard = evts(sent0).filter(e => e.t === 'caught');
  ok(heard.length === 1 && heard[0].id === id && heard[0].via === 'rod' && heard[0].p === P.id && typeof heard[0].first === 'boolean',
    `bamboo rod: other packs hear "caught" once for the landed fish (${JSON.stringify(heard)})`);
  ok(session() === undefined && d.some(x => x.id === id), `bamboo rod: the catch is landed (drops: ${d.map(x => x.id.split(':')[1]).join(', ')})`);
  ok(!bobbers.at(-1).isValid, 'bamboo rod: the bobber is removed after landing');
  ok(!loops.size, 'bamboo rod: the tick loop stops when no bobber is out');
  ok(dmg() === 1, `bamboo rod: landing a catch wears the rod by 1 (${dmg()})`);
  const sized = CATCH_BY_ID[id]?.size;
  ok(!sized || d.find(x => x.id === id)?.lore?.some(l => /◆/.test(l)), `bamboo rod: a sized fish carries its size class (${JSON.stringify(d.find(x => x.id === id)?.lore)})`);
  const rec = JSON.parse(P.getDynamicProperty(NS + 'journal') ?? '{}');
  ok(rec[id]?.n === 1, `bamboo rod: the catch is written in the angler's journal (${JSON.stringify(rec[id])})`);
}
{
  // a missed bite: the bobber pops back up and the wait starts over
  clearInv(); atPond(); P.hold(rodItem('bamboo')); cool();
  press(); release(); const s = session();
  waitFor(() => s.phase === 'bite', 800);
  waitFor(() => s.phase !== 'bite', 200);
  ok(s.phase === 'waiting' && s.biteAt > s.age, `missed bite: back to waiting with a new bite time (${s.phase})`);
  cool(); press(); release();
  ok(session() === undefined && !bobbers.at(-1).isValid, 'reeling in an empty line ends the session and removes the bobber');
  ok(dmg() === 0, 'reeling in an empty line does not wear the rod');
}
{
  // cast onto dry ground: it lies there until reeled in
  clearInv(); stand(D, 0.5, 65, -10); setBox(D, 'minecraft:stone', -4, 4, 64, 64, -12, -4);
  P.hold(rodItem('bamboo')); cool();
  castTo = { x: 0.5, y: 65.05, z: -8 }; press(); release();
  const s = session();
  ok(waitFor(() => s.phase === 'ground', 100), `cast on the ground: the bobber lies still (${s.phase})`);
  advance(400);
  ok(s.phase === 'ground' && !s.catchId, 'cast on the ground: nothing ever bites');
  cool(); press(); release();
  ok(!session(), 'cast on the ground: reeling in ends it');
}
{
  // the voyage rod: tier 2, bigger window
  clearInv(); atPond(); P.hold(rodItem('voyage')); cool(); allDrops();
  const s = castAndHook();
  ok(s?.rod?.tier === 2 && !!s.catchId, `voyage rod: casts, bites and hooks (${s?.catchId})`);
  fight('bot');
  ok(!session() && allDrops().some(x => x.id === s.catchId), 'voyage rod: the catch is landed');
}
{
  // the lava rod in a nether lava lake: lava catches, landed at the angler's feet
  clearInv(); stand(NETHER, 0.5, 64, 0.5); P.hold(rodItem('lava')); cool(); allDrops();
  const s = castAndHook();
  ok(s?.inLava && s.ctx?.waters?.has('lava') && s.ctx.depth >= 4, `lava rod: the bobber floats on lava (${[...(s?.ctx?.waters ?? [])]}, depth ${s?.ctx?.depth})`);
  const lavaIds = Object.values(CATCH_BY_ID).filter(e => e.waters?.includes('lava')).map(e => e.id).concat(['minecraft:magma_cream', 'minecraft:gold_nugget', 'minecraft:quartz', 'minecraft:gold_ingot', 'minecraft:netherite_scrap']);
  ok(lavaIds.includes(s?.catchId), `lava rod: a lava catch is hooked (${s?.catchId})`);
  fight('bot');
  const d = allDrops();
  const got = d.find(x => x.id === s.catchId);
  ok(!session() && got && Math.abs(got.loc.x - P.location.x) < 0.01 && Math.abs(got.loc.z - P.location.z) < 0.01, `lava rod: the catch lands at the angler's feet (${got ? JSON.stringify(got.loc) : 'nothing'})`);
  // a bamboo rod cannot fish lava: the bobber never floats there
  P.hold(rodItem('bamboo')); cool(); press(); release(); const t = session();
  advance(120);
  ok(t && t.phase !== 'waiting' && t.phase !== 'bite', `bamboo rod on lava: no floating, no bite (${t?.phase})`);
  cool(); press(); release(); stand(D, 0.5, 65, 0.5); advance(4);
}
{
  // the ender rod off an End island: the bobber hangs in the void
  clearInv(); stand(END, 0.5, 61, 0.5); P.hold(rodItem('ender')); cool(); allDrops();
  const s = castAndHook();
  ok(s?.inVoid && s.ctx?.waters?.has('void'), `ender rod: the bobber hangs over the void (${s?.phase}, ${[...(s?.ctx?.waters ?? [])]}, voidY ${s?.voidY?.toFixed?.(1)})`);
  const voidIds = Object.values(CATCH_BY_ID).filter(e => e.waters?.includes('void')).map(e => e.id);
  ok(voidIds.includes(s?.catchId), `ender rod: a void catch is hooked (${s?.catchId})`);
  fight('bot');
  const got = allDrops().find(x => x.id === s?.catchId);
  ok(!session() && !!got, `ender rod: the void catch is landed (${got ? JSON.stringify(got.loc) : 'nothing'})`);
  // an End pond: a plain bobber takes the End look
  stand(END, 40.5, 64, 0.5); P.hold(rodItem('bamboo')); cool(); press(); release(); const t = session();
  waitFor(() => t.phase === 'waiting', 200);
  ok(t.ctx?.waters?.has('end_pond') && bobbers.at(-1).getProperty(STYLE) === 4, `End pond: end_pond water and the ender bobber look (style ${bobbers.at(-1).getProperty(STYLE)})`);
  cool(); press(); release();
}

// ---------------------------------------------------------------- 2. minigame on / off
{
  // switching the minigame off through /scriptevent
  const m = log.messages.length;
  minigame(false);
  ok(!sw.minigameOn() && /off/.test(log.messages.slice(m).join(' ')), `/scriptevent minigame off: switched off and replied (${log.messages.slice(m)})`);
  ok(JSON.parse(W.getDynamicProperty(NS + 'minigame')).on === false, 'minigame switch: saved in the world property');
  fire('system.afterEvents.scriptEventReceive', { id: NS + 'minigame', message: 'bogus', sourceEntity: P });
  ok(/usage/.test(log.messages.at(-1)), 'minigame switch: an unknown word gets the usage line');
}
{
  // minigame off: a fighting fish is a tug of war; reel while it rests and it lands
  clearInv(); atPond(); P.hold(rodItem('bamboo')); minigame(false); allDrops();
  let s, tries = 0;
  do { cool(); s = castAndHook(); if (s && !CATCH_BY_ID[s.catchId]?.fight && session() === s) drop(s); } while (++tries < 30 && !(s && session() === s && s.phase === 'pull'));
  ok(s?.phase === 'pull' && !s.game, `minigame off: a fighting fish pulls (no minigame) (${s?.catchId}, ${s?.phase})`);
  const before = dmg();
  fight('reel');
  ok(!session() && allDrops().some(x => x.id === s.catchId), `minigame off: reeling while it rests lands the ${s.catchId?.split(':')[1]}`);
  ok(dmg() === before + 1, `minigame off: a landed fight wears the rod by 1 (${before} -> ${dmg()})`);
}
{
  // minigame off: reeling while it pulls snaps the line
  clearInv(); atPond(); P.hold(rodItem('bamboo')); minigame(false); allDrops();
  let s, tries = 0;
  do { cool(); s = castAndHook(); if (s && session() === s && s.phase !== 'pull') drop(s); } while (++tries < 30 && !(s && session() === s && s.phase === 'pull'));
  const n = log.sounds.length, w0 = dmg();
  advance(3); fight('yank', 200);
  ok(!session() && log.sounds.slice(n).includes('random.break'), 'minigame off: reeling against a pulling fish snaps the line');
  ok(!allDrops().some(x => x.id === s.catchId), 'minigame off: a snapped line lands nothing');
  ok(dmg() - w0 === 2, `minigame off: a snapped line wears the rod by 2 (${w0} -> ${dmg()})`);
}
{
  // minigame off: a fish left alone through four rests shakes the hook
  clearInv(); atPond(); P.hold(rodItem('bamboo')); minigame(false);
  let s, tries = 0;
  do { cool(); s = castAndHook(); if (s && session() === s && s.phase !== 'pull') drop(s); } while (++tries < 30 && !(s && session() === s && s.phase === 'pull'));
  ok(waitFor(() => s.phase === 'waiting', 1200), `minigame off: an unattended fish gets away, the wait starts over (${s.phase})`);
  cool(); press(); release();
}
{
  // minigame on: a sized fish plays the minigame; the bot wins it
  clearInv(); atPond(); P.hold(rodItem('bamboo')); minigame(true); allDrops();
  let s, tries = 0;
  do { cool(); s = castAndHook(); if (s && session() === s && s.phase !== 'game') drop(s); } while (++tries < 30 && !(s && session() === s && s.phase === 'game'));
  ok(s?.phase === 'game' && s.game?.state === 'play', `minigame on: a sized fish starts the minigame (${s?.catchId})`);
  advance(4);
  ok(!!s.hud && /█/.test(s.hud.text), 'minigame on: the actionbar shows the track (block charset)');
  fight('bot');
  ok(!session() && allDrops().some(x => x.id === s.catchId), 'minigame on: keeping the box on the fish lands it');
}
{
  // minigame on: keeping the box away from the fish loses it (it shakes the hook); the rod wears by 1
  clearInv(); atPond(); P.hold(rodItem('bamboo')); minigame(true); allDrops();
  let s, tries = 0;
  do { cool(); s = castAndHook(); if (s && session() === s && s.phase !== 'game') drop(s); } while (++tries < 30 && !(s && session() === s && s.phase === 'game'));
  const id = s.catchId, w0 = dmg();
  fight('avoid', 2000);
  ok(session() === s && s.phase === 'waiting' && !s.game, `minigame lost: the fish gets away, the bobber goes back to waiting (${s.phase})`);
  ok(!allDrops().some(x => x.id === id), 'minigame lost: nothing is landed');
  ok(dmg() - w0 === 1, `minigame lost: the rod wears by 1 (${w0} -> ${dmg()})`);
  cool(); press(); release();
}
{
  // minigame switched off in the middle of a game: the fish lands at once
  clearInv(); atPond(); P.hold(rodItem('bamboo')); minigame(true); allDrops();
  let s, tries = 0;
  do { cool(); s = castAndHook(); if (s && session() === s && s.phase !== 'game') drop(s); } while (++tries < 30 && !(s && session() === s && s.phase === 'game'));
  minigame(false); advance(3);
  ok(!session() && allDrops().some(x => x.id === s.catchId), 'minigame switched off mid-game: the fish lands');
  minigame(true);
}

// ---------------------------------------------------------------- 3. tackle parts (Tackle Rack), bait
const rack = D.place(NS + 'tackle_rack', { x: 10, y: 65, z: -5 });
/** Hang a rod, fit parts (each held and used on the rack), take it back. Returns the rod stack in slot 0. */
function fit(rodId, parts) {
  clearInv(); P.hold(rodId); use(rack);
  for (const p of parts) { P.selectedSlotIndex = 0; P.hold(p); use(rack); }
  clearInv(); use(rack);
  return P.held();
}
{
  const r = fit(rodItem('bamboo'), [NS + 'bone_hook', NS + 'hemp_line', NS + 'bamboo_bobber']);
  const parts = readParts(r);
  ok(r?.typeId === rodItem('bamboo') && parts.hook === NS + 'bone_hook' && parts.line === NS + 'hemp_line' && parts.bobber === NS + 'bamboo_bobber',
    `tackle rack: hook, line and bobber are fitted to the rod (${JSON.stringify(parts)})`);
  ok(r.getLore().length === 3, `tackle rack: the parts are listed under the rod's name (${r.getLore().length} lines)`);
  ok(st(rack, 'rod_a') === 0 && st(rack, 'rod_b') === 0, 'tackle rack: the rod is taken back (rack empty)');
  // swap the hook: the old one comes back
  P.hold(rodItem('bamboo')); P.inv.setItem(0, r); use(rack);
  P.hold(NS + 'gold_hook'); use(rack);
  ok(inv('bone_hook') === 1 && inv('gold_hook') === 0, 'tackle rack: fitting a new hook gives the old one back');
  // shears take every part off
  P.hold('minecraft:shears'); use(rack);
  ok(inv('gold_hook') === 1 && inv('hemp_line') === 1 && inv('bamboo_bobber') === 1, 'tackle rack: shears take all parts off, back to the inventory');
  P.selectedSlotIndex = 5; P.hold(undefined); use(rack);
  ok(Object.keys(readParts(P.inv.getItem(0) ?? P.held())).length === 0 || Object.keys(readParts(P.held())).length === 0, 'tackle rack: the rod comes back bare after shearing');
}
{
  // wear is kept through the rack
  clearInv(); P.hold(rodItem('bamboo')); const r = P.held(); r._damage = 7; P.inv.setItem(0, r);
  use(rack); P.hold(undefined); use(rack);
  ok(P.held()?._damage === 7, `tackle rack: a hung rod keeps its wear (${P.held()?._damage})`);
}
{
  // eye of ender turns a hung voyage rod into an ender rod, parts kept
  clearInv(); const r = fit(rodItem('voyage'), [NS + 'wire_line']);
  P.inv.setItem(0, r); use(rack); P.hold(NS + 'wire_line'); P.hold('minecraft:ender_eye'); use(rack);
  P.hold(undefined); use(rack);
  ok(P.held()?.typeId === rodItem('ender') && readParts(P.held()).line === NS + 'wire_line', `tackle rack: an eye of ender makes an ender rod, its line kept (${P.held()?.typeId})`);
}
{
  // parts act on the cast: the bamboo bobber's look and longer bite window
  const r = fit(rodItem('bamboo'), [NS + 'bamboo_bobber']);
  atPond(); cool(); press(); release(); const s = session();
  ok(bobbers.at(-1).getProperty(STYLE) === 1, `bamboo bobber: the bobber shows its style (${bobbers.at(-1).getProperty(STYLE)})`);
  ok(s.fx.window === 10 && s.fx.bite === 0.9, `bamboo bobber: wider bite window, quicker bites (${s.fx.window}, ${s.fx.bite})`);
  cool(); press(); release();
}
{
  // bait: carried in the inventory, eaten when the fish takes it
  clearInv(); atPond(); P.hold(rodItem('bamboo')); P.inv.setItem(3, new S.ItemStack(NS + 'earthworm', 3)); minigame(false);
  cool(); press(); release(); const s = session();
  ok(s.bait === NS + 'earthworm', `bait: the cast carries the earthworm (${s.bait})`);
  waitFor(() => s.phase === 'waiting', 200);
  ok(inv('earthworm') === 3, 'bait: nothing is eaten while waiting');
  waitFor(() => s.phase === 'bite', 800); press();
  ok(inv('earthworm') === 2, `bait: one earthworm is eaten when the fish bites (${inv('earthworm')} left)`);
  if (session() === s) drop(s);
}
{
  // bait put away while the line is out: the hook carries the next bait in the bag
  clearInv(); atPond(); P.hold(rodItem('bamboo')); P.inv.setItem(3, new S.ItemStack(NS + 'earthworm', 1)); minigame(false);
  cool(); press(); release(); const s = session();
  waitFor(() => s.phase === 'waiting', 200);
  P.inv.setItem(3, undefined); P.inv.setItem(4, new S.ItemStack(NS + 'fish_offal', 2));
  advance(24);
  ok(s.bait === NS + 'fish_offal', `bait: an earthworm put away is replaced by the next bait in the bag (${s.bait})`);
  waitFor(() => s.phase === 'bite', 800); press();
  ok(inv('fish_offal') === 1, `bait: that bait is eaten instead (${inv('fish_offal')} offal left)`);
  if (session() === s) drop(s);
}
{
  // the lure hook: an empty bag still fishes, nothing is eaten
  const r = fit(rodItem('bamboo'), [NS + 'lure_hook']);
  atPond(); minigame(false); cool(); press(); release(); const s = session();
  ok(s.bait === LURE && s.fx.lure, `lure hook: an empty bag fishes with the lure (${s.bait})`);
  waitFor(() => s.phase === 'waiting', 200); waitFor(() => s.phase === 'bite', 800);
  const items = P.inv.slots.filter(Boolean).length;
  press();
  ok(!!s.catchId && P.inv.slots.filter(Boolean).length === items, `lure hook: the strike hooks a fish and takes nothing from the bag (${s.catchId})`);
  if (session() === s) drop(s);
  // with a real bait in the bag, the bait is used (and eaten); the lure only stands in for an empty bag (cast() comment)
  P.inv.setItem(3, new S.ItemStack(NS + 'earthworm', 2));
  cool(); press(); release(); const t = session();
  waitFor(() => t.phase === 'waiting', 200); waitFor(() => t.phase === 'bite', 800); press();
  ok(t.bait === NS + 'earthworm' && inv('earthworm') === 1, `lure hook + bait in the bag: the bait is used and eaten (${t.bait}, ${inv('earthworm')} left)`);
  if (session() === t) drop(t);
  // SUSPECTED BUG: the bait runs out / is put away while the line is out -> the lure hook should take over again
  P.inv.setItem(3, new S.ItemStack(NS + 'earthworm', 1));
  cool(); press(); release(); const u = session();
  waitFor(() => u.phase === 'waiting', 200);
  P.inv.setItem(3, undefined); advance(24);
  ok(u.bait === LURE, `lure hook: when the bait is put away mid-cast the lure takes over again (bait now ${u.bait}) [rod.js baitGone]`);
  if (session() === u) drop(u);
}
{
  // gold hook wears the rod faster (wear 1): a landed catch costs 2
  const r = fit(rodItem('bamboo'), [NS + 'gold_hook']);
  atPond(); minigame(false); allDrops();
  let s, tries = 0;
  do { cool(); s = castAndHook(); if (s && session() === s && s.phase !== 'pull') drop(s); } while (++tries < 30 && !(s && session() === s && s.phase === 'pull'));
  const w0 = dmg(); fight('reel');
  ok(!session() && dmg() - w0 === 2, `gold hook: a landed catch wears the rod by 2 (${w0} -> ${dmg()})`);
  minigame(true);
}
{
  // a worn-out rod breaks on its last catch
  clearInv(); atPond(); minigame(false); allDrops();
  P.hold(rodItem('bamboo')); const r = P.held(); r._damage = 63; P.inv.setItem(0, r);
  cool(); const s = castAndHook(); if (session() === s) fight('reel');
  ok(!P.held() && log.sounds.includes('random.break'), `a rod at its last durability point breaks when the catch lands (${P.held()?.typeId ?? 'gone'})`);
  minigame(true);
}

// ---------------------------------------------------------------- 4. legends: the gold bobber
const iceAt = { x: 100, y: 64, z: 2 };
{
  // drill an ice hole with the auger
  clearInv(); stand(D, 100.5, 65, 0.5);
  P.hold(NS + 'ice_auger'); use(D.getBlock(iceAt));
  ok(D.getBlock(iceAt).typeId === NS + 'ice_hole', `ice auger: drills an ice hole in ice over water (${D.getBlock(iceAt).typeId})`);
  const dry = { x: 0, y: 64, z: -3 }; D.place('minecraft:ice', dry); D.place('minecraft:stone', { x: 0, y: 63, z: -3 });
  advance(12); use(D.getBlock(dry));
  ok(D.getBlock(dry).typeId === 'minecraft:ice', 'ice auger: refuses ice with no water under it');
}
const hole = D.getBlock(iceAt);
const holeTop = { x: iceAt.x + 0.5, y: iceAt.y + 1.05, z: iceAt.z + 0.5 };
/** Cast through the hole until a legend is hooked (abandoning every other fish). */
function fishForLegend(atFn, rodId, max = 800) {   // a frostlake char is ~1.5% of ice bites
  const seen = {};
  for (let i = 0; i < max; i++) {
    cool();
    if (P.held()?.typeId !== rodId) P.hold(rodId);
    const s = atFn();
    const k = (s?.catchId ?? s?.phase ?? 'no cast').replace(NS, '');
    seen[k] = (seen[k] ?? 0) + 1;
    if (!s || session() !== s) continue;
    if (s.catchId && LEGEND_SET.has(s.catchId)) return { s, tries: i + 1 };
    drop(s);
  }
  return { s: undefined, tries: JSON.stringify(seen) };
}
{
  // fishing through the ice hole: ice water
  clearInv(); stand(D, 100.5, 65, 0.5); P.hold(rodItem('bamboo')); minigame(true); cool();
  castTo = holeTop; use(hole);
  const s = session();
  ok(!!s, 'ice hole: using a rod on the hole casts');
  waitFor(() => s?.phase === 'waiting', 100);
  ok(s?.ctx?.waters?.has('ice'), `ice hole: the bobber drops into the hole, ice water (${[...(s?.ctx?.waters ?? [])]})`);
  cool(); press(); release();
}
{
  // frostlake char: ice water, new moon, dawn. Its bite turns the bobber gold.
  clearInv(); stand(D, 100.5, 65, 0.5); minigame(true); clock.moon = 4; clock.day = 23500;
  const r = fit(rodItem('bamboo'), [NS + 'bamboo_bobber']); stand(D, 100.5, 65, 0.5);
  const { s, tries } = fishForLegend(() => castAndHook(holeTop), rodItem('bamboo'));
  ok(s?.catchId === NS + 'frostlake_char', `legend: a frostlake char bites through the ice hole at a new-moon dawn (${tries} bites)`);
  const b = s?.bobber;
  ok(b?.getProperty(STYLE) === 6, `legend: the bobber turns gold (style ${b?.getProperty(STYLE)}, was the bamboo bobber's 1)`);
  ok(s?.game?.legend && s.game.pattern === 'mixed' && s.game.D >= 92, `legend: it plays the hardest minigame (D ${s?.game?.D}, ${s?.game?.pattern})`);
  // SUSPECTED BUG: the legend shakes the hook; the bobber stays gold for the next ordinary fish
  if (s) {
    fight('avoid', 4000);
    ok(s.phase === 'waiting', `legend lost: back to waiting (${s.phase})`);
    ok(b.getProperty(STYLE) !== 6, `legend lost: the bobber is no longer gold once the legend is gone (style ${b.getProperty(STYLE)}) [rod.js:221]`);
    cool(); press(); release();
  }
  // without the new moon it never bites (a short sample, the full check is in test_scripts)
  clock.moon = 2; let seen = 0;
  for (let i = 0; i < 25; i++) { cool(); const t = castAndHook(holeTop); if (t?.catchId === NS + 'frostlake_char') seen++; if (t && session() === t) drop(t); }
  ok(seen === 0, `legend: no frostlake char without the new moon (25 bites)`);
  clock.moon = 2; clock.day = 6000;
}
{
  // lava dragon koi: nether lava, wire line, no bait. Landed (minigame off): legend mark and its keepsake.
  const r = fit(rodItem('lava'), [NS + 'wire_line']);
  stand(NETHER, 0.5, 64, 0.5); minigame(false); allDrops();
  const { s, tries } = fishForLegend(() => castAndHook(), rodItem('lava'));
  ok(s?.catchId === NS + 'lava_dragon_koi' && s.bobber.getProperty(STYLE) === 6, `legend: a lava dragon koi bites on a wire line in nether lava, gold bobber (${tries} bites)`);
  if (s) {
    fight('reel', 8000);
    const d = allDrops();
    const koi = d.find(x => x.id === NS + 'lava_dragon_koi');
    ok(!session() && !!koi, `legend: the koi is reeled in (${d.map(x => x.id.split(':')[1]).join(', ')})`);
    ok(koi?.lore?.includes('§d✦'), `legend: it carries the legend mark (${JSON.stringify(koi?.lore)})`);
    ok(d.some(x => x.id === KEEPSAKES[NS + 'lava_dragon_koi']), 'legend: the first one brings its keepsake (dragon scale)');
  }
  stand(D, 0.5, 65, 0.5); minigame(true);
}

// ---------------------------------------------------------------- 5a. ice hole: tip-ups
{
  clearInv(); stand(D, 100.5, 65, 0.5);
  P.hold(NS + 'tip_up', 4); use(hole);
  ok(st(hole, 'tipup') === 1 && inv('tip_up') === 3, `tip-up: set in the hole (state ${st(hole, 'tipup')}, ${inv('tip_up')} left)`);
  let n = 0; while (st(hole, 'tipup') === 1 && n++ < 500) { clock.abs += 100; tick(hole); }
  ok(st(hole, 'tipup') === 2, `tip-up: a bite springs the flag (${n} block ticks)`);
  for (let i = 0; i < 20; i++) tick(hole);
  ok(st(hole, 'tipup') === 2, 'tip-up: a hooked fish stays on the line until taken');
  P.selectedSlotIndex = 8; P.hold(undefined);
  const before = P.inv.slots.filter(Boolean).reduce((a, s) => a + s.amount, 0);
  use(hole);
  const got = P.inv.slots.filter(Boolean).reduce((a, s) => a + s.amount, 0) - before;
  ok(st(hole, 'tipup') === 1 && got === 1, `tip-up: using the hole takes the fish, the tip-up stays (got ${got})`);
  const fish = P.inv.slots.find(s => s && s.typeId !== NS + 'tip_up');
  ok(fish && !(fish.getLore() ?? []).some(l => /◆◆◆/.test(l)), `tip-up: never a large fish (${fish?.typeId}, ${JSON.stringify(fish?.getLore())})`);
  P.selectedSlotIndex = 8; P.hold(undefined); use(hole);
  ok(st(hole, 'tipup') === 0 && inv('tip_up') === 4, 'tip-up: an empty hand takes the tip-up back');
}
{
  // the limit: three tip-ups per player
  clearInv(); stand(D, 100.5, 65, 0.5);
  const holes = [0, 1, 2, 3].map(i => { const h = D.place(NS + 'ice_hole', { x: 97 + i * 2, y: 64, z: 6 }); return h; });
  P.hold(NS + 'tip_up', 4);
  for (const h of holes) { use(h); advance(1); }
  ok(holes.slice(0, 3).every(h => st(h, 'tipup') === 1) && st(holes[3], 'tipup') === 0 && inv('tip_up') === 1, `tip-up: a fourth one is refused (${holes.map(h => st(h, 'tipup'))})`);
  D.drops.splice(0);
  breakBlock(holes[0]);
  ok(D.drops.splice(0).some(x => x.id === NS + 'tip_up'), 'tip-up: breaking a hole gives the tip-up back');
  use(holes[3]);
  ok(st(holes[3], 'tipup') === 1, 'tip-up: after one hole is gone, a new one can be set');
}

// ---------------------------------------------------------------- 5b. shrimp trap
{
  clearInv(); stand(D, 0.5, 65, 0.5);
  const trap = D.place(NS + 'shrimp_trap', { x: 0, y: 61, z: 10 });   // inside the pond: water above it
  P.hold('kaleidoscope_cookery:caterpillar', 2); use(trap);
  ok(st(trap, 'bait') === 1 && inv('kaleidoscope_cookery:caterpillar') === 1, 'shrimp trap: baited with a caterpillar (one taken)');
  use(trap);
  ok(inv('kaleidoscope_cookery:caterpillar') === 1, 'shrimp trap: a baited trap takes no second bait');
  tick(trap); clock.abs += 2400 * 3 + 10; tick(trap);
  const c = st(trap, 'catch');
  ok(c > 0, `shrimp trap: something crawls in after three tries (catch ${c})`);
  P.selectedSlotIndex = 8; P.hold(undefined);
  use(trap);
  const got = ['shrimp', 'live_shrimp', 'crab'].reduce((a, k) => a + inv(k), 0);
  ok(got === c && st(trap, 'catch') === 0 && st(trap, 'crab') === 0, `shrimp trap: an empty hand empties it (${got} of ${c}: ${['shrimp', 'live_shrimp', 'crab'].map(k => inv(k)).join('/')})`);
  // a dry trap never fills
  const dry = D.place(NS + 'shrimp_trap', { x: 10, y: 65, z: 10 });
  P.selectedSlotIndex = 0; P.hold('kaleidoscope_cookery:caterpillar', 1); use(dry);
  tick(dry); clock.abs += 2400 * 3 + 10; tick(dry);
  ok(st(dry, 'catch') === 0, 'shrimp trap: out of the water it catches nothing');
  D.drops.splice(0); breakBlock(dry);
  ok(D.drops.splice(0).some(x => x.id === 'kaleidoscope_cookery:caterpillar'), 'shrimp trap: breaking a baited trap gives the bait back');
}

// ---------------------------------------------------------------- 5c. fish creel (basket)
{
  clearInv(); atPond(); minigame(false); allDrops();
  P.hold(rodItem('bamboo')); P.inv.setItem(5, new S.ItemStack(NS + 'fish_basket', 1));
  // land creel fish until one goes in (first catches go in; a new size record stays out as a trophy)
  let stored = 0, landed = [], tries = 0;
  const creel = () => JSON.parse(P.inv.getItem(5)?.getDynamicProperty(NS + 'creel') ?? '{}');
  while (!stored && tries++ < 40) {
    cool(); const s = castAndHook(); if (!s) continue;
    if (session() === s) fight('reel');
    landed.push(s.catchId);
    stored = Object.values(creel()).reduce((a, b) => a + b, 0);
  }
  const d = allDrops();
  ok(stored >= 1, `fish creel: a landed fish goes into the creel (${JSON.stringify(creel())})`);
  ok(P.inv.getItem(5)?.getLore()?.[0]?.includes(`${stored} / 256`), `fish creel: the creel shows its count (${P.inv.getItem(5)?.getLore()})`);
  // open it and take the first entry out
  P.selectedSlotIndex = 5;
  const key = Object.keys(creel()).sort((a, b) => a.localeCompare(b))[0];
  const [fid, cls] = key.split('#');
  answers.push(0);
  const n0 = log.forms.length;
  fire('world.afterEvents.itemUse', { source: P, itemStack: P.held() });
  for (let i = 0; i < 4; i++) { await new Promise(r => setTimeout(r, 5)); flush(); }
  ok(log.forms.length > n0 && log.forms[n0].buttons.length >= 2, `fish creel: using it opens its list (${log.forms[n0]?.buttons.length} buttons)`);
  const out = P.inv.slots.find((s, i) => s && i !== 5 && s.typeId === fid);
  ok(!!out && (!cls || out.getLore().some(l => (l.match(/◆/g) ?? []).length === Number(cls))), `fish creel: picking a fish puts it in the pockets with its size mark (${fid}, ${JSON.stringify(out?.getLore())})`);
  ok(!creel()[key], 'fish creel: it is taken out of the creel');
  // a shrimp trap empties into a carried creel
  const trap = D.place(NS + 'shrimp_trap', { x: 2, y: 61, z: 12 });
  P.selectedSlotIndex = 0; P.hold('kaleidoscope_cookery:caterpillar', 1); use(trap); tick(trap);
  clock.abs += 2400 * 3 + 10; tick(trap); const c = st(trap, 'catch'), k = st(trap, 'crab');
  const before = creel();
  P.selectedSlotIndex = 8; P.hold(undefined); use(trap);
  const after = creel();
  const inCreel = (after[NS + 'shrimp'] ?? 0) - (before[NS + 'shrimp'] ?? 0) + (after[NS + 'crab'] ?? 0) - (before[NS + 'crab'] ?? 0);
  ok(c > 0 && inCreel + inv('live_shrimp') === c, `fish creel: trap shrimp and crabs go into the creel (catch ${c}, crab ${k}, creel +${inCreel}, live ${inv('live_shrimp')})`);
  minigame(true);
}

finish('play (fishing)');
