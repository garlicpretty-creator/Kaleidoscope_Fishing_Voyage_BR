// Play-through tests: replay player actions (hold an item, use a block, wait, break it) against the add-on's
// real block components and event handlers, in the stateful simulation of tools/tests/sim.
// Run: node --import ./tools/tests/sim/hooks.mjs tools/tests/test_play.mjs        (exit code 1 on failure)
// Play-through tests for the workstations, the fish tank, the fish print and the journal: replay player actions
// (hold an item, use a block, wait, break it) against the add-on's real code in the simulation of tools/tests/sim.
// Run: node --import ./tools/tests/sim/hooks.mjs tools/tests/test_play.mjs        (exit code 1 on failure)
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { boot, setComps, ok, finish, use, tick, wait, breakBlock, place, inv, st, clearInv, drops, P, NS, D, log, flush,
  fire, blockDefs, compsOf, importScript, GameMode, ROOT, thrown, sent, evts } from './sim/play.mjs';
setComps(await boot());

// ---------- drying rack ----------
{
  clearInv(); const r = place(NS + 'drying_rack');
  P.hold(NS + 'carp', 4);
  use(r); use(r); use(r);
  ok(st(r, 'count') === 3 && inv('carp') === 1, `drying rack: three carp hang (count ${st(r, 'count')}, 1 left in hand)`);
  use(r);
  ok(st(r, 'count') === 3 && inv('carp') === 1, 'drying rack: a fourth fish is refused');
  P.hold(undefined); use(r);
  ok(st(r, 'count') === 2 && inv('carp') === 1, 'drying rack: an empty hand takes one fish back before it is dry');
  P.selectedSlotIndex = 0; P.hold(NS + 'carp', 1); use(r);
  wait(r, 24100);
  ok(st(r, 'stage') === 1, `drying rack: half dry after one in-game day (stage ${st(r, 'stage')})`);
  wait(r, 24100);
  ok(st(r, 'stage') === 2, `drying rack: dry after two days (stage ${st(r, 'stage')})`);
  P.hold(undefined); use(r);
  ok(inv('air_dried_fish') === 3 && st(r, 'count') === 0, `drying rack: collecting gives 3 air-dried fish (${inv('air_dried_fish')}) and empties the rack`);
}
{
  clearInv(); const r = place(NS + 'drying_rack');
  P.hold(NS + 'carp', 2); use(r); use(r);
  P.hold(NS + 'sea_salt', 1); use(r);
  ok(st(r, 'kind') === 2 && inv('sea_salt') === 0, `drying rack: sea salt turns the batch salted (kind ${st(r, 'kind')})`);
  wait(r, 48200); P.hold(undefined); use(r);
  ok(inv('salted_fish') === 2, `drying rack: a salted batch gives 2 salted fish (${inv('salted_fish')})`);
}
{
  clearInv(); const r = place(NS + 'drying_rack');
  P.hold(NS + 'salted_mullet_roe', 1); use(r);
  wait(r, 48100); P.hold(undefined);
  ok(st(r, 'stage') < 2, 'drying rack: salted mullet roe is not ready after two days');
  wait(r, 24200); use(r);
  ok(inv('karasumi') === 1, `drying rack: salted mullet roe becomes karasumi after three days (${inv('karasumi')})`);
}
{
  clearInv(); const r = place(NS + 'drying_rack');
  P.hold(NS + 'flying_fish', 1); use(r); wait(r, 24200); P.hold(undefined); use(r);
  ok(inv('dried_flying_fish') === 1, `drying rack: flying fish becomes dried flying fish after one day (${inv('dried_flying_fish')})`);
}
{
  clearInv(); const r = place(NS + 'drying_rack');
  P.hold(NS + 'carp', 2); use(r); use(r); drops();
  breakBlock(r);
  const d = drops();
  ok(d.filter(x => x.id === NS + 'carp').length === 2, `drying rack: breaking it drops the fish on it (${d.map(x => x.id.split(':')[1]).join(', ') || 'nothing'})`);
}

// ---------- fish sauce jar ----------
{
  clearInv(); const j = place(NS + 'fish_sauce_jar');
  const { SAUCE_FISH } = await importScript('data/generated.js');
  P.hold(SAUCE_FISH[0], 4); use(j);
  ok(inv(SAUCE_FISH[0].split(':')[1]) === 4, 'fish sauce jar: fish before salt is refused');
  P.selectedSlotIndex = 1; P.hold(NS + 'sea_salt', 1); use(j);
  P.selectedSlotIndex = 0; use(j); use(j); use(j); use(j);
  ok(st(j, 'stage') === 2, `fish sauce jar: salt then four fish seals it (stage ${st(j, 'stage')})`);
  wait(j, 3700);
  ok(st(j, 'stage') === 3, `fish sauce jar: ready after fermenting (stage ${st(j, 'stage')})`);
  P.hold('minecraft:glass_bottle', 5); for (let i = 0; i < 5; i++) use(j);
  ok(inv('fish_sauce') === 4 && st(j, 'stage') === 0, `fish sauce jar: four bottles of fish sauce, then empty (${inv('fish_sauce')})`);
}
{
  clearInv(); const j = place(NS + 'fish_sauce_jar');
  P.hold(NS + 'sea_salt', 1); use(j);
  P.hold(NS + 'dried_shrimp', 4); use(j); use(j); use(j); use(j);
  wait(j, 3700);
  P.hold('minecraft:bowl', 4); for (let i = 0; i < 4; i++) use(j);
  ok(inv('shrimp_paste') === 4, `fish sauce jar: dried shrimp make shrimp paste (${inv('shrimp_paste')})`);
}

// ---------- cleaning board ----------
{
  clearInv(); drops(); const c = place(NS + 'fish_cleaning_board');
  P.hold(NS + 'grey_mullet', 1); use(c);
  ok(st(c, 'cut') > 0 && !P.held(), `cleaning board: a grey mullet is laid on the board (cut ${st(c, 'cut')})`);
  P.hold(NS + 'fishing_knife', 1);
  const sent0 = sent.length;
  let guard = 0; while (st(c, 'cut') > 0 && guard++ < 5) use(c);
  const cleaned = evts(sent0).filter(e => e.t === 'cleaned');
  ok(cleaned.length === 1 && cleaned[0].id === NS + 'grey_mullet' && cleaned[0].p === P.id, `cleaning board: other packs hear "cleaned" once, at the last cut (${JSON.stringify(cleaned)})`);
  const got = P.inv.slots.filter(Boolean).map(s => s.typeId).concat(drops().map(x => x.id));
  ok(got.includes(NS + 'fish_scales') && got.includes(NS + 'fish_offal') && got.includes(NS + 'fish_bones') && st(c, 'cut') === 0,
    `cleaning board: three knife cuts give scales, offal, fillets and bones (${[...new Set(got)].map(x => x.split(':')[1]).join(', ')})`);
  let roe = 0;
  for (let i = 0; i < 40; i++) {
    clearInv(); P.hold(NS + 'grey_mullet', 1); use(c); P.hold(NS + 'fishing_knife', 1);
    let g = 0; while (st(c, 'cut') > 0 && g++ < 5) use(c);
    roe += inv('mullet_roe');
  }
  ok(roe > 0, `cleaning board: grey mullet sometimes gives mullet roe (${roe} in 40 fish)`);
  for (const n of ['loach', 'mudskipper', 'golden_croaker', 'chorus_carp', 'ender_angler', 'blazefin', 'lava_eel', 'magma_koi', 'lava_dragon_koi']) {
    clearInv(); drops(); P.hold(NS + n, 1); use(c);
    const laid = st(c, 'cut') > 0 && !P.held();
    P.hold(NS + 'fishing_knife', 1);
    let g = 0; while (st(c, 'cut') > 0 && g++ < 5) use(c);
    const got = P.inv.slots.filter(Boolean).map(s => s.typeId).concat(drops().map(x => x.id));
    ok(laid && st(c, 'cut') === 0 && got.includes(NS + 'fish_offal') && got.includes(NS + 'fish_bones'),
      `cleaning board: ${n} is laid down and cut up (${[...new Set(got)].map(x => x.split(':')[1]).join(', ')})`);
  }
  clearInv(); P.hold(NS + 'carp', 1); use(c); P.hold(undefined); use(c);
  ok(inv('carp') === 1 && st(c, 'cut') === 0, 'cleaning board: an empty hand takes the fish back before the first cut');
}

// ---------- fish tank ----------
{
  clearInv(); const t = place(NS + 'fish_tank');
  const before = JSON.stringify(t.permutation.getAllStates());
  P.hold(NS + 'carp', 1); use(t);
  ok(JSON.stringify(t.permutation.getAllStates()) !== before && inv('carp') === 0, `fish tank: a carp goes in (${JSON.stringify(t.permutation.getAllStates())})`);
}

{
  const { FIT, TANK_KIND } = await importScript('data/tank.js');
  const { TANK_FISH } = await importScript('data/generated.js');
  const over = FIT.flat(2).filter(r => r[0] > 100);
  ok(FIT.length >= TANK_FISH.length && TANK_KIND.length >= TANK_FISH.length && !over.length,
    `fish tank: every species has a fit and a kind, and no scale passes the property's 100 cap (${over.length} over)`);
  clearInv(); const t2 = place(NS + 'fish_tank');
  P.hold(NS + 'purpur_shrimp', 1); use(t2);
  ok(inv('purpur_shrimp') === 0, 'fish tank: purpur shrimp go in');
}

// ---------- fish print ----------
{
  clearInv(); const f = place(NS + 'fish_print');
  P.hold(NS + 'carp', 1); use(f);
  ok(st(f, 'tier') > 0, `fish print: printing a carp sets a frame (tier ${st(f, 'tier')})`);
  ok(st(f, 'tier') !== 4, 'fish print: an unmarked fish does not get the record frame');
}

// ---------- journal ----------
{
  clearInv(); P.hold(NS + 'angler_journal', 1);
  const n = log.forms.length;
  fire('world.afterEvents.itemUse', { source: P, itemStack: P.held() });
  await new Promise(r => setTimeout(r, 20)); flush();
  const form = log.forms[n];
  const keys = (form?.buttons ?? []).map(b => b.t?.translate ?? String(b.t));
  ok(!!form, `journal: using it opens the index (${keys.length} buttons)`);
  const want = ['recipes', 'tide', 'group_freshwater', 'group_wetland', 'group_sea', 'group_ice', 'group_lava', 'group_end', 'group_cave', 'group_legend'];
  ok(want.every(k => keys.includes('kaleidoscope_fishing.journal.' + k)), 'journal: recipes, tides and the eight water groups are there');
  ok(!keys.some(k => /title_|contest|longline|group_sky|hints|cleaning/.test(k)), `journal: no titles, contest, longline, sky, hint or cleaning pages (${keys.map(k => k.split('.').pop()).join(', ')})`);
  const icons = (form?.buttons ?? []).map(b => b.icon).filter(Boolean);
  const RP = join(ROOT, 'Kaleidoscope Fishing Voyage [RP]');
  const missing = icons.filter(i => !existsSync(join(RP, i + '.png')));
  ok(!missing.length, `journal: every index icon exists (${missing.join(', ') || icons.length + ' icons'})`);
}

// ---------- sweep: every scripted block against a handful of held items ----------
const HELD = [undefined, 'carp', 'sea_salt', 'grey_mullet', 'salted_mullet_roe', 'dried_shrimp', 'shrimp', 'live_shrimp',
  'fishing_knife', 'angler_journal', 'minecraft:glass_bottle', 'minecraft:bowl', 'minecraft:stick', 'minecraft:bucket', 'emperor_tuna'];
const scripted = [...blockDefs.keys()].filter(id => compsOf({ typeId: id }).length);
const before = thrown.length;
for (const id of scripted) {
  for (const h of HELD) {
    clearInv(); const b = place(id);
    P.hold(h ? (h.includes(':') ? h : NS + h) : undefined, 3);
    use(b); use(b); wait(b, 30000, 3); P.hold(undefined); use(b);
    P.mode = GameMode.Creative; use(b); P.mode = GameMode.Survival;
    breakBlock(b);
  }
}
ok(thrown.length === before, `sweep: ${scripted.length} scripted blocks x ${HELD.length} held items, no handler threw`);
finish('play (stations)');
