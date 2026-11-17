// ## Fish Sauce Jar (魚露甕, v1.4). Salt first, then four small fish (fish sauce) or four dried
// shrimp (shrimp paste). The jar seals itself and ferments on random ticks; when it is done the
// lid comes off and the liquid shows. Bottles draw fish sauce, bowls scoop shrimp paste: four
// servings a batch. Kind and stage are block states (they are drawn); since v1.5.5 servings left and the
// salt are in a world record per jar (blockData.js "sj"), with the old left / salted states kept for 1.5.4.
//   stage 0 empty (salted or not)  1 raw, filling  2 sealed, fermenting  3 ready
// v1.6.3 (F1): the record also keeps which salt and which fish went in, and the kind and stage, so a jar
// removed in any way (player, explosion, piston, command: contents.js) gives back exactly what it holds:
// the salt and every fish as it went in until the batch is ready, then the servings left.
// A jar filled before 1.6.3 has no fish list; its raw batch comes back as the first sauce fish, as before.
// v1.6.3 (F2): every refused use says why (util/hint.js).
// v1.6.4 (F3): fermentation takes FERMENT_TICKS of world time from sealing (record "t", absolute time), checked on the
// block tick; a jar that was unloaded catches up when it loads again. Until 1.6.3 it ended on a random tick (30 %
// each, about 3.8 min on average, often much longer, and only while loaded). A jar sealed before 1.6.4 has no start
// time: it is taken as half done (FERMENT_TICKS / 2 left from the first tick after the update), neither restarted
// nor finished at once.
import { EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { SAUCE_FISH } from "../data/generated.js";
import { spawnParticle } from "../util/particles.js";
import { refuse } from "../util/hint.js";
import { readData, writeData } from "./blockData.js";
import { registerRecords, registerStation, spawnAll } from "./contents.js";

const NS = "kaleidoscope_fishing";
const BLOCK = `${NS}:fish_sauce_jar`;
const KIND = `${NS}:kind`, STAGE = `${NS}:stage`, LEFT = `${NS}:left`, SALTED = `${NS}:salted`;
const SEA_SALT = `${NS}:sea_salt`;
const SALT = new Set([SEA_SALT]);
// 1.5.0: shrimp paste is fresh shrimp pounded with salt, as it is made for real: Dried Shrimp no longer goes in.
const SHRIMP = `${NS}:dried_shrimp`;                     // what a jar filled before 1.5.0 may still hold
export const PASTE_SHRIMP = new Set([`${NS}:shrimp`, `${NS}:live_shrimp`]);
const NEED = 4;                      // fish or shrimp per batch
export const FERMENT_TICKS = 3600;   // v1.6.4: 3 minutes of world time, sealed -> ready
const now = () => { try { return world.getAbsoluteTime(); } catch { return system.currentTick; } };
const PRODUCT = { 1: { item: `${NS}:fish_sauce`, vessel: "minecraft:glass_bottle" }, 2: { item: `${NS}:shrimp_paste`, vessel: "minecraft:bowl" } };

// v1.5.5: servings left and the salt live in blockData ("sj": { left, salted }); the left / salted states are
// still written for 1.5.4 and read only for a jar with no record yet (copied over on its next block tick).
// v1.6.3: the record also holds { kind, stage, salt: id, fish: [id...] }.
const st = (block, p = block.permutation) => fromRecord(readData("sj", block.dimension, block), p);
/** Jar state from its record and (when the block is still known) its permutation. Exported for tests. */
export function fromRecord(d, p) {
  const num = (v, s) => (v !== undefined ? Number(v) || 0 : p ? Number(p.getState(s) ?? 0) : 0);
  return { kind: p ? Number(p.getState(KIND) ?? 0) : Number(d?.kind) || 0, stage: p ? Number(p.getState(STAGE) ?? 0) : Number(d?.stage) || 0,
           left: num(d?.left, LEFT), salted: num(d?.salted, SALTED), salt: d?.salt, fish: Array.isArray(d?.fish) ? d.fish.map(String) : undefined,
           t: typeof d?.t === "number" ? d.t : undefined, saved: !!d };
}
const saveJar = (block, s) => writeData("sj", block.dimension, block, s && (s.left || s.salted || s.stage)
  ? { left: s.left, salted: s.salted, kind: s.kind, stage: s.stage, ...(s.salt ? { salt: s.salt } : {}), ...(s.fish ? { fish: s.fish } : {}), ...(s.stage === 2 && s.t !== undefined ? { t: s.t } : {}) } : undefined);
const snd = (block, id, pitch = 1, volume = 0.7) => { try { block.dimension.playSound(id, block.center(), { pitch, volume }); } catch {} };
const creative = p => { try { return p.getGameMode() === GameMode.Creative; } catch { return false; } };
function takeOne(player, slot) {
  if (creative(player)) return;
  const it = slot.getItem(); if (!it) return;
  if (it.amount <= 1) slot.setItem(undefined); else { it.amount -= 1; slot.setItem(it); }
}
function give(player, block, id) {
  const stack = new ItemStack(id, 1);
  try { const left = player.getComponent("minecraft:inventory")?.container?.addItem(stack); if (left) block.dimension.spawnItem(left, block.center()); }
  catch { try { block.dimension.spawnItem(stack, block.center()); } catch {} }
}
function set(block, s) {
  saveJar(block, s);
  try { block.setPermutation(block.permutation.withState(KIND, s.kind).withState(STAGE, s.stage).withState(LEFT, s.left).withState(SALTED, s.salted)); } catch {}
}

/** v1.6.4: sealed at t, is it ready at time n? (world time; a clock set back far before the sealing counts as done) */
export const fermentDone = (t, n) => n - t >= FERMENT_TICKS || n < t - FERMENT_TICKS;

/** What a jar holds, as item ids (exported for tests). */
export function jarContents(s) {
  const out = [];
  if (s.stage >= 3) {                                              // ready: the servings left
    const prod = PRODUCT[s.kind];
    if (prod) for (let i = 0; i < s.left; i++) out.push(prod.item);
    return out;
  }
  if (s.salted) out.push(s.salt && SALT.has(s.salt) ? s.salt : SEA_SALT);
  const n = s.stage === 2 ? NEED : s.stage === 1 ? s.left : 0;
  const fallback = s.kind === 2 ? SHRIMP : SAUCE_FISH[0];
  for (let i = 0; i < n; i++) out.push(s.fish?.[i] ?? fallback);
  return out;
}
function dropJar(dim, pos, perm) {
  const s = fromRecord(readData("sj", dim, pos), perm);
  writeData("sj", dim, pos, undefined);
  spawnAll(dim, pos, jarContents(s).map(id => new ItemStack(id, 1)));
}

/** A jar left half filled with Dried Shrimp before 1.5.0: the shrimp come out, the salt stays. True if it did. */
function returnOldShrimp(block, s) {
  if (s.stage !== 1 || s.kind !== 2) return false;
  const fish = s.fish ?? Array(s.left).fill(SHRIMP);
  const old = fish.filter(id => id === SHRIMP);
  if (!old.length) return false;
  spawnAll(block.dimension, block, old.map(id => new ItemStack(id, 1)));
  const keep = fish.filter(id => id !== SHRIMP);
  if (keep.length) set(block, { ...s, left: keep.length, fish: keep });
  else set(block, { ...s, kind: 0, stage: 0, left: 0, fish: undefined });
  snd(block, "random.pop", 1.2, 0.5);
  return true;
}

const jar = {
  onPlayerInteract({ block, player }) {
    if (!player) return;
    const slot = player.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
    const held = slot?.hasItem() ? slot.typeId : undefined;
    const s = st(block);
    if (s.stage === 0) {
      if (held && SALT.has(held)) {
        if (s.salted) return refuse(player, "jar_salted");
        takeOne(player, slot); set(block, { ...s, salted: 1, salt: held }); snd(block, "dig.sand", 1.3); return;
      }
      if (!s.salted) return refuse(player, "jar_need_salt");
      if (!held) return refuse(player, "jar_need_fish");
      if (held === SHRIMP) return refuse(player, "jar_paste_fresh");
      const kind = SAUCE_FISH.includes(held) ? 1 : PASTE_SHRIMP.has(held) ? 2 : 0;
      if (!kind) return refuse(player, "jar_wrong_fish");
      takeOne(player, slot); set(block, { ...s, kind, stage: 1, left: 1, salted: 1, fish: [held] }); snd(block, "random.splash", 1.4, 0.5); return;
    }
    if (s.stage === 1 && returnOldShrimp(block, s)) return;      // 1.5.0: a half-filled jar of dried shrimp gives them back
    if (s.stage === 1) {                                          // filling: same kind only
      const want = s.kind === 1 ? SAUCE_FISH.includes(held) : PASTE_SHRIMP.has(held);
      if (!want) return refuse(player, s.kind === 1 ? "jar_more_fish" : "jar_more_shrimp", NEED - s.left);
      takeOne(player, slot);
      const left = s.left + 1;
      const fish = [...(s.fish ?? Array(s.left).fill(s.kind === 2 ? SHRIMP : SAUCE_FISH[0])), held];
      if (left >= NEED) { set(block, { ...s, stage: 2, left: 0, fish, t: now() }); snd(block, "block.barrel.close", 1.0); }
      else { set(block, { ...s, left, fish }); snd(block, "random.splash", 1.4, 0.5); }
      return;
    }
    if (s.stage === 2) return refuse(player, "jar_fermenting");   // sealed: wait
    const prod = PRODUCT[s.kind];                                  // stage 3: draw a serving
    if (!prod) return;
    if (held !== prod.vessel) return refuse(player, s.kind === 1 ? "jar_need_bottle" : "jar_need_bowl");
    takeOne(player, slot);
    give(player, block, prod.item);
    const left = s.left - 1;
    snd(block, s.kind === 1 ? "bucket.fill_water" : "dig.gravel", 1.2, 0.6);
    if (left <= 0) set(block, { kind: 0, stage: 0, left: 0, salted: 0 }); else set(block, { ...s, left });
  },
  onTick({ block }) {
    const s = st(block);
    const d = readData("sj", block.dimension, block);
    // v1.5.5: copy a 1.5.4 jar into its record; v1.6.3: and the kind and stage into an older record
    if ((s.left || s.salted || s.stage) && (!d || Number(d.stage ?? -1) !== s.stage || Number(d.kind ?? -1) !== s.kind)) saveJar(block, s);
    if (returnOldShrimp(block, s)) return;
    if (s.stage !== 2) return;
    if (s.t === undefined) { saveJar(block, { ...s, t: now() - FERMENT_TICKS / 2 }); return; }   // sealed before 1.6.4: half done
    if (fermentDone(s.t, now())) {
      set(block, { ...s, stage: 3, left: NEED, fish: undefined, salt: undefined, t: undefined });
      snd(block, "random.pop", 0.8, 0.5);
      return;
    }
    // fermenting: a bubble now and then
    try { spawnParticle(block.dimension, "minecraft:basic_bubble_particle", { x: block.x + 0.5, y: block.y + 0.95, z: block.z + 0.5 }); } catch {}
    if (Math.random() < 0.2) snd(block, "bubble.pop", 0.8, 0.3);
  },
  onPlayerBreak({ block, brokenBlockPermutation, player }) {
    if (player && creative(player)) { writeData("sj", block.dimension, block, undefined); return; }
    dropJar(block.dimension, block, brokenBlockPermutation);
  },
};

registerStation(BLOCK, dropJar);
registerRecords(`${NS}:bd:sj:`, BLOCK, (dim, pos) => dropJar(dim, pos, undefined));

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(BLOCK, jar);
});
