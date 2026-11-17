// Play-through tests: replay player actions (hold an item, use a block, wait, break it) against the add-on's
// real block components and event handlers, in the stateful simulation of tools/tests/sim.
// Run: node --import ./tools/tests/sim/hooks.mjs tools/tests/test_play.mjs        (exit code 1 on failure)
// Play-through tests for the workstations, the fish tank, the fish print and the journal: replay player actions
// (hold an item, use a block, wait, break it) against the add-on's real code in the simulation of tools/tests/sim.
// Run: node --import ./tools/tests/sim/hooks.mjs tools/tests/test_play.mjs        (exit code 1 on failure)
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { boot, setComps, ok, finish, use, tick, wait, breakBlock, place, inv, st, clearInv, drops, P, NS, D, log, flush,
  fire, blockDefs, compsOf, importScript, GameMode, ROOT, thrown, sent, evts, ItemStack, clock } from './sim/play.mjs';
setComps(await boot());

// ---------- drying rack ----------
{
  clearInv(); const r = place(NS + 'drying_rack');
  P.hold(NS + 'gutted_fish', 4);
  use(r); use(r); use(r);
  ok(st(r, 'count') === 3 && inv('gutted_fish') === 1, `drying rack: three gutted fish hang (count ${st(r, 'count')}, 1 left in hand)`);
  use(r);
  ok(st(r, 'count') === 3 && inv('gutted_fish') === 1, 'drying rack: a fourth fish is refused');
  P.hold(undefined); use(r);
  ok(st(r, 'count') === 2 && inv('gutted_fish') === 1, 'drying rack: an empty hand takes one fish back before it is dry');
  P.selectedSlotIndex = 0; P.hold(NS + 'gutted_fish', 1); use(r);
  wait(r, 24100);
  ok(st(r, 'stage') === 1, `drying rack: half dry after one in-game day (stage ${st(r, 'stage')})`);
  wait(r, 24100);
  ok(st(r, 'stage') === 2, `drying rack: dry after two days (stage ${st(r, 'stage')})`);
  P.hold(undefined); use(r);
  ok(inv('air_dried_fish') === 3 && st(r, 'count') === 0, `drying rack: collecting gives 3 air-dried fish (${inv('air_dried_fish')}) and empties the rack`);
}
{
  clearInv(); const r = place(NS + 'drying_rack');
  P.hold(NS + 'gutted_fish', 2); use(r); use(r);
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
  P.hold(NS + 'gutted_flying_fish', 1); use(r); wait(r, 24200); P.hold(undefined); use(r);
  ok(inv('dried_flying_fish') === 1, `drying rack: flying fish becomes dried flying fish after one day (${inv('dried_flying_fish')})`);
}
{
  clearInv(); const r = place(NS + 'drying_rack');
  P.hold(NS + 'gutted_fish', 2); use(r); use(r); drops();
  breakBlock(r);
  const d = drops();
  ok(d.filter(x => x.id === NS + 'gutted_fish').length === 2, `drying rack: breaking it drops the fish on it (${d.map(x => x.id.split(':')[1]).join(', ') || 'nothing'})`);
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
  P.hold(NS + 'dried_shrimp', 4); use(j);
  ok(inv('dried_shrimp') === 4 && st(j, 'stage') === 0, '1.5.0 fish sauce jar: dried shrimp no longer make shrimp paste');
  P.hold(NS + 'shrimp', 2); use(j); use(j); P.hold(NS + 'live_shrimp', 2); use(j); use(j);
  ok(st(j, 'stage') === 2, `fish sauce jar: salt and four fresh shrimp (shrimp or live shrimp) seal it (stage ${st(j, 'stage')})`);
  wait(j, 3700);
  P.hold('minecraft:bowl', 4); for (let i = 0; i < 4; i++) use(j);
  ok(inv('shrimp_paste') === 4, `fish sauce jar: fresh shrimp make shrimp paste (${inv('shrimp_paste')})`);
}
{
  // a jar left half full of dried shrimp by 1.4 gives them back and keeps its salt
  clearInv(); drops(); const j = place(NS + 'fish_sauce_jar');
  const { writeData } = await importScript('blocks/blockData.js');
  writeData('sj', D, j, { left: 2, salted: 1, kind: 2, stage: 1, salt: NS + 'sea_salt', fish: [NS + 'dried_shrimp', NS + 'dried_shrimp'] });
  j.setPermutation(j.permutation.withState(NS + 'kind', 2).withState(NS + 'stage', 1).withState(NS + 'left', 2).withState(NS + 'salted', 1));
  tick(j);
  const back = drops();
  ok(back.filter(d => d.id === NS + 'dried_shrimp').reduce((a, d) => a + d.amount, 0) === 2 && st(j, 'stage') === 0 && st(j, 'salted') === 1,
    `fish sauce jar: a 1.4 jar half full of dried shrimp gives them back and keeps its salt (${back.map(d => d.id.split(':')[1])})`);
}
{
  // dried shrimp, the 1.5.0 way: salted shrimp on the tray, then one rub on the board
  const { KC_RECIPES } = await importScript('data/generated.js');
  const trays = KC_RECIPES.filter(r => r.kind === 'bamboo_tray').map(r => r.recipe);
  ok(!trays.some(r => r.input === NS + 'shrimp' || r.result === NS + 'dried_shrimp'), 'dried shrimp: the bamboo tray no longer dries raw shrimp into dried shrimp');
  ok(trays.some(r => r.input === NS + 'salted_shrimp' && r.result === NS + 'dried_shell_shrimp'), 'dried shrimp: the bamboo tray dries salted shrimp, shells on');
  const salted = KC_RECIPES.find(r => r.recipe.result === NS + 'salted_shrimp')?.recipe;
  ok(salted && salted.base === 'minecraft:water' && salted.count === 3 && salted.ingredients.includes(NS + 'sea_salt'), 'dried shrimp: salt and three shrimp boil into three salted shrimp');
  clearInv(); drops(); const c = place(NS + 'fish_cleaning_board');
  P.hold(NS + 'dried_shell_shrimp', 1); use(c);
  const laid = st(c, 'cut');
  P.hold(NS + 'fishing_knife', 1); use(c);
  ok(laid === 3 && st(c, 'cut') === 0 && inv('dried_shrimp') === 2 && inv('shrimp_shell') === 1,
    `dried shrimp: one rub on the board gives 2 dried shrimp and the shells (${inv('dried_shrimp')}, ${inv('shrimp_shell')})`);
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
  // 1.5.0: shrimp, crab and jellyfish, each with its own cuts
  const cutUp = (id, lore) => {
    clearInv(); drops();
    const s0 = new ItemStack(NS + id, 1); if (lore) s0.setLore(lore); P.inv.setItem(P.selectedSlotIndex, s0); use(c);
    const stages = [st(c, 'cut')];
    P.hold(NS + 'fishing_knife', 1);
    const steps = [];
    let g = 0;
    while (st(c, 'cut') > 0 && g++ < 5) {
      const before = new Map(P.inv.slots.filter(Boolean).map(x => [x.typeId, x.amount]));
      use(c);
      stages.push(st(c, 'cut'));
      steps.push(P.inv.slots.filter(Boolean).filter(x => x.typeId !== NS + 'fishing_knife').map(x => [x.typeId.split(':')[1], x.amount - (before.get(x.typeId) ?? 0)]).filter(x => x[1] > 0));
    }
    return { stages, steps, all: Object.fromEntries(P.inv.slots.filter(Boolean).filter(x => x.typeId !== NS + 'fishing_knife').map(x => [x.typeId.split(':')[1], x.amount])) };
  };
  let r = cutUp('shrimp');
  ok(r.stages.join() === '1,2,3,0' && JSON.stringify(r.steps) === JSON.stringify([[['shrimp_head', 1]], [['shrimp_shell', 1]], [['shrimp_meat', 1]]]),
    `cleaning board: a shrimp takes three cuts, head, shell, vein (${r.stages} / ${JSON.stringify(r.steps)})`);
  r = cutUp('shrimp', ['§6◆◆◆']);
  ok(r.all.shrimp_meat === 2, `cleaning board: a large shrimp gives two peeled shrimp (${JSON.stringify(r.all)})`);
  r = cutUp('lobster');
  ok(r.all.shrimp_head === 2 && r.all.shrimp_shell === 2 && r.all.shrimp_meat === 3, `cleaning board: a lobster gives 2 heads, 2 shells, 3 peeled shrimp (${JSON.stringify(r.all)})`);
  r = cutUp('live_shrimp');
  ok(r.all.shrimp_meat === 1 && r.stages.join() === '1,2,3,0', 'cleaning board: live shrimp go on the board too');
  r = cutUp('crab');
  ok(r.stages.join() === '1,2,3,0' && r.all.crab_shell === 1 && r.all.fish_offal === 1 && r.all.crab_meat === 1 && r.all.crab_leg === 2,
    `cleaning board: a crab is opened, cleaned and taken apart (${JSON.stringify(r.all)})`);
  r = cutUp('king_crab');
  ok(r.all.crab_shell === 2 && r.all.crab_roe === 1 && r.all.crab_meat === 2 && r.all.crab_leg === 4, `cleaning board: a king crab gives 2 shells, roe, 2 meat, 4 legs (${JSON.stringify(r.all)})`);
  let roeCrabs = 0;
  for (let i = 0; i < 40; i++) if (cutUp('crab').all.crab_roe) roeCrabs++;
  ok(roeCrabs > 8 && roeCrabs < 32, `cleaning board: about one crab in two has roe (${roeCrabs} in 40)`);
  r = cutUp('moon_jellyfish');
  ok(r.stages.join() === '2,3,0' && r.all.fish_offal === 1 && r.all.jellyfish_skin === 2, `cleaning board: a jellyfish takes two cuts, feelers then strips (${r.stages} / ${JSON.stringify(r.all)})`);
  // 1.5.0: gutted, then taken back with an empty hand: a Gutted Fish for the drying rack
  for (const [fish, got] of [['carp', 'gutted_fish'], ['catfish', 'gutted_fish'], ['skipjack', 'gutted_skipjack'], ['flying_fish', 'gutted_flying_fish']]) {
    clearInv(); drops(); P.hold(NS + fish, 1); use(c); P.hold(NS + 'fishing_knife', 1);
    let g = 0; while (inv('fish_offal') === 0 && g++ < 3) use(c);
    P.hold(undefined); use(c);
    ok(inv(got) === 1 && st(c, 'cut') === 0 && !inv('white_fish_fillet') && !inv('fish_bones'), `cleaning board: a ${fish} gutted and taken back is a ${got.replace(/_/g, ' ')}`);
  }
  clearInv(); P.hold(NS + 'tuna', 1); use(c); P.hold(NS + 'fishing_knife', 1); use(c); use(c); P.hold(undefined); use(c);
  ok(st(c, 'cut') === 3 && !inv('gutted_fish'), 'cleaning board: a tuna does not come back gutted (it does not go on the rack)');
  P.hold(NS + 'fishing_knife', 1); use(c);
  { const rk = place(NS + 'drying_rack'); clearInv(); P.hold(NS + 'carp', 1); use(rk);
    ok(st(rk, 'count') === 0 && inv('carp') === 1, 'drying rack: a whole fish is no longer hung (gut it on the board first)'); }
  // 1.5.0: the whole squid, and tuna by part
  let inks = 0;
  for (let i = 0; i < 20; i++) {
    r = cutUp('whole_squid');
    if (i === 0) ok(r.stages.join() === '1,2,3,0' && r.all.fish_offal === 1 && r.all.squid_tube === 1 && r.all.squid_tentacles === 1 && JSON.stringify(r.steps[1]) === '[]',
      `cleaning board: a whole squid is gutted, its cartilage drawn (nothing comes of it), then cut into tube and tentacles (${JSON.stringify(r.steps)})`);
    if (r.all.ink_sac) inks++;
  }
  ok(inks > 2 && inks < 18, `cleaning board: about one squid in two gives an ink sac (${inks} in 20)`);
  r = cutUp('tuna');
  ok(r.all.tuna_sashimi === 4 && r.all.chutoro === 1 && r.all.otoro === 1, `cleaning board: a tuna gives 4 akami, 1 chutoro, 1 otoro (${JSON.stringify(r.all)})`);
  r = cutUp('tuna', ['§6◆◆◆']);
  ok(r.all.otoro === 2 && r.all.tuna_sashimi === 4, `cleaning board: a large tuna's extra slice is otoro (${JSON.stringify(r.all)})`);
  r = cutUp('skipjack');
  ok(r.all.bonito_sashimi === 3 && !r.all.tuna_sashimi, `cleaning board: a skipjack gives bonito sashimi (${JSON.stringify(r.all)})`);
  clearInv(); drops(); P.hold(NS + 'crab', 1); use(c); P.hold(undefined); use(c);
  ok(inv('crab') === 1 && st(c, 'cut') === 0, 'cleaning board: a crab can be taken back before the first cut');
  clearInv(); P.hold(NS + 'oyster', 1); use(c);
  ok(inv('oyster') === 1 && st(c, 'cut') === 0, 'cleaning board: an oyster is still refused');
}

// ---------- 1.5.0: wooden tub (purging clams) ----------
{
  clearInv(); drops(); const t = place(NS + 'wooden_tub');
  P.hold(NS + 'clam', 1); use(t);
  ok(st(t, 'fill') === 0 && inv('clam') === 1, 'wooden tub: clams need brine first');
  P.hold('minecraft:water_bucket', 1); use(t);
  ok(st(t, 'fill') === 1 && inv('minecraft:bucket') === 1, `wooden tub: a water bucket fills it and the bucket comes back empty (fill ${st(t, 'fill')})`);
  P.hold(NS + 'sea_salt', 1); use(t);
  ok(st(t, 'fill') === 2 && inv('sea_salt') === 0, 'wooden tub: salt turns the water into brine');
  P.hold(NS + 'clam', 9); for (let i = 0; i < 9; i++) use(t);
  ok(st(t, 'fill') === 3 && inv('clam') === 1, `wooden tub: up to 8 clams soak in it (${9 - inv('clam')} went in)`);
  P.hold(undefined); use(t);
  ok(st(t, 'fill') === 3 && !inv('purged_clam'), 'wooden tub: nothing comes out before they are done');
  wait(t, 12400);
  ok(st(t, 'fill') === 4, `wooden tub: after half a day they are purged (fill ${st(t, 'fill')})`);
  P.hold(undefined); use(t);
  ok(inv('purged_clam') === 8 && st(t, 'fill') === 2, `wooden tub: an empty hand takes out 8 purged clams and the brine stays (${inv('purged_clam')}, fill ${st(t, 'fill')})`);
  P.hold(NS + 'clam', 2); use(t); use(t);
  breakBlock(t); const d = drops();
  ok(d.filter(x => x.id === NS + 'clam').reduce((a, x) => a + x.amount, 0) === 2, `wooden tub: breaking it gives back the clams soaking in it (${d.map(x => x.id.split(':')[1])})`);
  const t2 = place(NS + 'wooden_tub'); clearInv(); P.hold('minecraft:water_bucket', 1); use(t2); P.hold('minecraft:bucket', 1); use(t2);
  ok(st(t2, 'fill') === 0 && inv('minecraft:water_bucket') === 1, 'wooden tub: an empty bucket drains it');
}

// ---------- 1.5.0: salt pan ----------
{
  const getBiome0 = D.getBiome;
  clearInv(); drops(); const s1 = place(NS + 'salt_pan');
  D.getBiome = () => ({ id: 'minecraft:plains' });
  P.hold('minecraft:water_bucket', 1); use(s1);
  ok(st(s1, 'stage') === 0 && inv('minecraft:water_bucket') === 1, 'salt pan: away from the sea it takes no water');
  D.getBiome = () => ({ id: 'minecraft:beach' });
  use(s1);
  ok(st(s1, 'stage') === 1 && inv('minecraft:bucket') === 1, 'salt pan: by the sea a water bucket fills it');
  wait(s1, 6400, 40);
  ok(st(s1, 'stage') === 2, `salt pan: half dry after half a day of sun (stage ${st(s1, 'stage')})`);
  const day0 = clock.day; clock.day = 18000;         // night: nothing dries
  wait(s1, 8000, 50);
  ok(st(s1, 'stage') === 2, 'salt pan: nothing dries at night');
  clock.day = day0;
  wait(s1, 6400, 40);
  ok(st(s1, 'stage') === 3, `salt pan: dry after a whole day of daylight in all (stage ${st(s1, 'stage')})`);
  P.hold(undefined); use(s1);
  ok(inv('sea_salt') === 4 && st(s1, 'stage') === 0, `salt pan: an empty hand gathers 4 salt (${inv('sea_salt')})`);
  D.getBiome = getBiome0;
}

// ---------- fish tank ----------
{
  clearInv(); const t = place(NS + 'fish_tank');
  const before = JSON.stringify(t.permutation.getAllStates());
  P.hold(NS + 'carp', 1); use(t);
  ok(JSON.stringify(t.permutation.getAllStates()) !== before && inv('carp') === 0, `fish tank: a carp goes in (${JSON.stringify(t.permutation.getAllStates())})`);
}
// ---------- 1.5.0: lava fish tank, and the oyster ----------
{
  const T = await importScript('blocks/tanks.js');
  const { TANK_FISH } = await importScript('data/generated.js');
  const { TANK_KIND, FIT } = await importScript('data/tank.js');
  const idxOf = id => TANK_FISH.indexOf(NS + id) + 1;
  const fishIn = b => b.permutation.getState(NS + 'fish') + 16 * b.permutation.getState(NS + 'fish_bank');
  for (const n of ['blazefin', 'lava_eel', 'magma_koi', 'basalt_crab', 'lava_dragon_koi']) {
    clearInv(); const lt = place(NS + 'lava_fish_tank'); P.hold(NS + n, 1); use(lt);
    ok(inv(n) === 0 && fishIn(lt) === idxOf(n), `lava fish tank: a ${n.replace(/_/g, ' ')} goes in`);
    P.hold(undefined); use(lt);
    ok(inv(n) === 1 && fishIn(lt) === 0, `lava fish tank: and comes back out`);
  }
  clearInv(); const lt = place(NS + 'lava_fish_tank'); P.hold(NS + 'carp', 1); use(lt);
  ok(inv('carp') === 1 && fishIn(lt) === 0, 'lava fish tank: a water fish is refused');
  for (const n of ['blazefin', 'lava_eel', 'magma_koi', 'basalt_crab']) {
    clearInv(); const wt = place(NS + 'fish_tank'); P.hold(NS + n, 1); use(wt);
    ok(inv(n) === 1, `fish tank: a ${n.replace(/_/g, ' ')} is refused (it needs the lava tank)`);
  }
  clearInv(); const wt = place(NS + 'fish_tank'); P.hold(NS + 'lava_dragon_koi', 1); use(wt);
  ok(inv('lava_dragon_koi') === 0, 'fish tank: the Lava Dragon Koi still goes in a water tank, as in 1.4');
  clearInv(); const ot = place(NS + 'fish_tank'); P.hold(NS + 'oyster', 1); use(ot);
  ok(inv('oyster') === 0 && fishIn(ot) === idxOf('oyster'), 'fish tank: an oyster goes in');
  const o = idxOf('oyster') - 1;
  ok(FIT[o].every(t => t.every(r => r[1] === 0)) && TANK_KIND[o] === TANK_KIND[idxOf('crab') - 1], 'fish tank: the oyster sits still on the bottom (no span to walk)');
  ok(TANK_FISH.length === FIT.length && TANK_FISH.length === TANK_KIND.length, `fish tank: every species has its placement rows (${TANK_FISH.length})`);
  ok(T.tankIndex(NS + 'blazefin', true) > 0 && T.tankIndex(NS + 'blazefin') === 0 && T.tankIndex(NS + 'carp', true) === 0, 'tankIndex: lava creatures for the lava tank only, water fish for the water tanks only');
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
