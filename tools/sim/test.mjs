import { SIM, ItemStack, BlockPermutation } from '@minecraft/server';
const NS = 'kaleidoscope_fishing';
let pass = 0, fail = 0;
const ok = (cond, msg) => { if (cond) pass++; else { fail++; console.log('FAIL', msg); } };
const flush = () => { while (SIM.runs.length) SIM.runs.shift()(); };

// ---- mocks
function container(n = 36) {
  const s = new Array(n).fill(undefined);
  return { size: n, getItem: i => s[i], setItem: (i, v) => { s[i] = v; },
    addItem(st) { const i = s.findIndex(x => !x); if (i < 0) return st; s[i] = st; return undefined; },
    all: () => s.filter(Boolean) };
}
function dimension() {
  const d = { id: 'minecraft:overworld', spawned: [], entities: [],
    spawnItem(st, loc) { d.spawned.push(st); return { clearVelocity() {}, applyImpulse() {}, teleport() {}, isValid: true, location: loc }; },
    playSound() {}, spawnParticle() {}, getBlock: () => undefined, getEntities: () => d.entities, getPlayers: () => [] };
  return d;
}
function player(dim) {
  const inv = container(); const effects = [];
  const p = { id: 'p' + Math.random(), typeId: 'minecraft:player', isValid: true, location: { x: 0, y: 64, z: 0 }, dimension: dim,
    gm: 'Survival', getGameMode() { return this.gm; }, _dp: {}, effects, selectedSlotIndex: 0, inv, isSneaking: false,
    getDynamicProperty(k) { return this._dp[k]; }, setDynamicProperty(k, v) { this._dp[k] = v; },
    playSound() {}, addEffect(e, d, o) { effects.push(e); }, sendMessage() {}, onScreenDisplay: { setActionBar() {} } };
  const slot = { hasItem: () => !!inv.getItem(p.selectedSlotIndex), getItem: () => inv.getItem(p.selectedSlotIndex),
    setItem: v => inv.setItem(p.selectedSlotIndex, v), get typeId() { return inv.getItem(p.selectedSlotIndex)?.typeId; } };
  p.getComponent = name => name === 'minecraft:inventory' ? { container: inv }
    : name === 'minecraft:equippable' ? { getEquipmentSlot: () => slot, getEquipment: () => inv.getItem(p.selectedSlotIndex) } : undefined;
  p.hold = st => inv.setItem(p.selectedSlotIndex, st);
  return p;
}
const count = (p, id) => p.inv.all().filter(s => s.typeId === id).reduce((a, s) => a + s.amount, 0);

// ---- load the add-on (main.js imports everything)
await import('./scripts/main.js');
const G = await import('./scripts/data/generated.js');

// ======== Fish Cleaning Board ========
{
  const board = SIM.components[`${NS}:fish_cleaning`];
  ok(board, 'board component registered');
  SIM.tags[`${NS}:fishing_knife`] = ['kaleidoscope_cookery:kitchen_knife'];
  const st = k => `${NS}:${k}`;
  const run = (fish) => {
    const dim = dimension(); const p = player(dim);
    const block = { x: 1, y: 2, z: 3, dimension: dim, location: { x: 1, y: 2, z: 3 }, typeId: `${NS}:fish_cleaning_board`,
      permutation: BlockPermutation.resolve(`${NS}:fish_cleaning_board`, { [st('fish')]: 0, [st('fish_bank')]: 0, [st('cut')]: 0, [st('size')]: 0 }),
      setPermutation(v) { this.permutation = v; }, center() { return { x: 1.5, y: 2.5, z: 3.5 }; } };
    p.hold(new ItemStack(fish.includes(":") ? fish : `${NS}:${fish}`, 2));
    board.onPlayerInteract({ block, player: p });
    const startCut = block.permutation.getState(st('cut'));
    let cuts = 0;
    while (block.permutation.getState(st('cut')) && cuts < 5) {
      p.hold(new ItemStack(`${NS}:fishing_knife`, 1));
      board.onPlayerInteract({ block, player: p }); cuts++;
    }
    return { p, startCut, cuts, left: block.permutation.getState(st('cut')) };
  };
  for (const [fish, c] of Object.entries(G.CLEANING)) {
    const name = fish.split(':')[1];
    const r = run(fish);
    const first = c.first ?? (c.scales ? 1 : 2);
    ok(r.startCut === first, `${name}: starts at cut ${first} (got ${r.startCut})`);
    ok(r.cuts === 4 - first && r.left === 0, `${name}: ${4 - first} cuts empty the board (got ${r.cuts}, left ${r.left})`);
    ok(count(r.p, c.out[0]) >= 1, `${name}: gives ${c.out[0]}`);
    for (const [id, n] of c.last ?? []) ok(count(r.p, id) >= n, `${name}: last cut gives ${id}`);
    for (const [id, n] of c.gut ?? []) ok(count(r.p, id) >= n, `${name}: gutting gives ${id}`);
    if (!c.gut && first <= 2) ok(count(r.p, `${NS}:fish_offal`) >= 1, `${name}: gutting gives offal`);
    if (c.gut) ok(count(r.p, `${NS}:fish_offal`) === 0, `${name}: no offal from shellfish`);
    if (first === 1) ok(count(r.p, `${NS}:fish_scales`) >= 1, `${name}: scaling gives scales`);
  }
  // an oyster is refused
  const dim = dimension(); const p = player(dim);
  const block = { x: 0, y: 0, z: 0, dimension: dim, location: { x: 0, y: 0, z: 0 }, permutation: BlockPermutation.resolve('b', { [st('fish')]: 0, [st('fish_bank')]: 0, [st('cut')]: 0 }), setPermutation(v) { this.permutation = v; }, center: () => ({}) };
  p.hold(new ItemStack(`${NS}:oyster`, 1)); board.onPlayerInteract({ block, player: p });
  ok(block.permutation.getState(st('cut')) === 0 && p.inv.getItem(0)?.amount === 1, 'oyster is refused by the board');
}

// ======== Fish Creel takes legends ========
{
  const { tryStore } = await import('./scripts/tools/basket.js');
  const p = player(dimension());
  p.inv.setItem(5, new ItemStack(`${NS}:fish_basket`, 1));
  for (const id of G.LEGENDS) ok(tryStore(p, id, 1, 3) === 0, `creel takes ${id}`);
  ok(tryStore(p, `${NS}:carp`, 1, 2) === 0, 'creel takes a carp');
}

// ======== Legend conditions: the keepsake parts count as the parts they are made from ========
{
  const { reqOk } = await import('./scripts/fishing/loot.js');
  const catches = Object.fromEntries(G.CATCHES.map(c => [c.id.split(':')[1], c]));
  const as = id => G.PARTS[id]?.as ?? id;
  ok(reqOk(catches.river_lord_catfish, { rod: true, tier: 2, thunder: true, hook: as(`${NS}:emperor_bone_hook`) }), 'Emperor Bone Hook counts as a Bone Hook');
  ok(!reqOk(catches.river_lord_catfish, { rod: true, tier: 2, thunder: true, hook: as(`${NS}:gold_hook`) }), 'a Gold Hook does not');
  ok(reqOk(catches.lava_dragon_koi, { rod: true, dim: 'minecraft:nether', line: as(`${NS}:whisker_line`) }), 'Whisker Line counts as a Wire Line');
  ok(!reqOk(catches.lava_dragon_koi, { rod: true, dim: 'minecraft:nether', line: as(`${NS}:hemp_line`) }), 'a Hemp Line does not');
  const rod = await import('fs').then(fs => fs.readFileSync('./scripts/fishing/rod.js', 'utf8'));
  ok(/hook: partAs\(s\.parts\?\.hook\)/.test(rod) && /line: partAs\(s\.parts\?\.line\)/.test(rod), 'rod.js passes parts through partAs');
}

// ======== Fish Merchant: prices and orders ========
{
  ok(['shrimp', 'oyster', 'loach', 'crab', 'mudskipper', 'cave_crayfish', 'purpur_shrimp', 'basalt_crab'].every(n => G.MERCHANT_PRICES[`${NS}:${n}`] > 0)
     && G.MERCHANT_PRICES['minecraft:tropical_fish'] > 0 && G.MERCHANT_PRICES['minecraft:pufferfish'] > 0, 'ten new merchant prices');
  const { orderNear } = await import('./scripts/world/merchant.js');
  const sale = SIM.events['world.before.playerInteractWithEntity'].find(f => /MERCHANT|merchant/.test(f.toString()));
  const dim = dimension();
  const m = { typeId: `${NS}:fish_merchant`, dimension: dim, location: { x: 3, y: 64, z: 0 }, _dp: {}, props: {},
    getDynamicProperty(k) { return this._dp[k]; }, setDynamicProperty(k, v) { this._dp[k] = v; }, setProperty(k, v) { this.props[k] = v; } };
  dim.entities = [m];
  const p = player(dim);
  const o = orderNear(p);
  ok(o && o.n > 0 && G.WANT_LIST.includes(o.id), `merchant has an order (${o?.id} x${o?.n}${o?.min ? ', medium+' : ''})`);
  ok(m.props[`${NS}:order`] === G.WANT_LIST.indexOf(o.id) + 1, 'order fish shown on the pole (entity property)');
  const wants = JSON.parse(m._dp[`${NS}:wants`]);
  ok(!wants.includes(o.id), 'order is not one of the two wanted fish');
  const sell = (n, lore = ['§f◆◆']) => { const st = new ItemStack(o.id, n); st.setLore(lore); p.hold(st); const ev = { player: p, target: m, itemStack: st, cancel: false }; sale(ev); flush(); return ev; };
  const before = p.inv.all().length;
  sell(o.n - 1);
  ok(orderNear(p).have === o.n - 1, `progress counts (${orderNear(p).have}/${o.n})`);
  sell(1);
  ok(orderNear(p).have === o.n, 'order filled');
  const rewards = p.inv.all().filter(s => s.typeId !== 'minecraft:emerald' || s.amount === 6);
  ok(rewards.length >= 1, `a reward was handed over (${p.inv.all().map(s => s.typeId.split(':')[1] + 'x' + s.amount).join(', ')})`);
  const after = p.inv.all().length;
  sell(1); ok(p.inv.all().length <= after + 1, 'no second reward');
  // another player, purse empty: still counted
  const q = player(dim);
  m._dp[`${NS}:spent`] = 999;
  const st = new ItemStack(o.id, 1); st.setLore(['§6◆◆◆']); q.hold(st);
  sale({ player: q, target: m, itemStack: st, cancel: false }); flush();
  ok(orderNear(q).have === 1, 'empty purse: the order fish is still taken and counted');
  ok(count(q, 'minecraft:emerald') === 0, 'empty purse: nothing paid');
  if (o.min) {
    const r = player(dim); const s2 = new ItemStack(o.id, 1); s2.setLore(['§7◆']); r.hold(s2);
    m._dp[`${NS}:spent`] = 0; sale({ player: r, target: m, itemStack: s2, cancel: false }); flush();
    ok(orderNear(r).have === 0, 'a small fish does not count toward a medium+ order');
  }
}

// ======== Food effects ========
{
  const { applyFoodEffects } = await import('./scripts/events/foodEffects.js');
  const want = { crab_congee: 'regeneration', crab_roe_rice: 'absorption', jellyfish_salad: 'water_breathing', steamed_king_crab: 'absorption',
    steamed_lobster: 'regeneration', karasumi_fried_rice: 'haste', crab_roe_bun: 'regeneration', river_lord_casserole: 'resistance', dragon_koi_sizzle: 'fire_resistance' };
  for (const [n, e] of Object.entries(want)) { const p = player(dimension()); applyFoodEffects(p, `${NS}:${n}`); ok(p.effects.includes(e), `${n} gives ${e}`); }
}

// ======== Minigame charset per player ========
{
  const M = await import('./scripts/fishing/minigameSwitch.js');
  const a = player(dimension()), b = player(dimension());
  M.setCharsetFor(a, 'ascii');
  ok(M.charsetFor(a) === 'ascii' && M.charsetFor(b) === M.charset(), 'charset is per player');
  M.setMinigame(false); ok(!M.minigameOn(), 'minigame switch off'); M.setMinigame(true); ok(M.minigameOn(), 'and on');
}

// ======== Fish Tank ========
{
  const T = await import('./scripts/data/tank.js');
  for (const n of ['shrimp', 'purpur_shrimp', 'oyster']) ok(G.TANK_FISH.includes(`${NS}:${n}`), `${n} can go in the tank`);
  const oi = G.TANK_FISH.indexOf(`${NS}:oyster`);
  ok(T.FIT[oi].every(t => t.every(f => f[1] === 0)), 'the oyster does not stroll');
  ok(T.TANK_KIND.length === G.TANK_FISH.length && T.FIT.length === G.TANK_FISH.length, 'tank tables line up with TANK_FISH');
  for (const n of ['blazefin', 'lava_eel', 'magma_koi', 'basalt_crab']) ok(!G.TANK_FISH.includes(`${NS}:${n}`), `${n} stays out of the tank`);
}

// ======== Feasts ========
{
  for (const n of ['river_lord_casserole', 'dragon_koi_sizzle']) {
    const f = G.FEASTS[`${NS}:${n}_block`];
    ok(f && f.item === `${NS}:${n}` && f.bites > 0, `${n}: feast data`);
  }
}
console.log(`\n${pass} passed, ${fail} failed`);
if (fail) process.exitCode = 1;
