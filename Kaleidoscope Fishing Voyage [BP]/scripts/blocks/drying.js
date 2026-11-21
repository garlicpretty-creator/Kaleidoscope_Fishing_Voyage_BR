// ## Drying Rack (曬魚架, v1.2). One batch of up to 3 of the same kind hangs from the pole:
// whole fish (1), salted fish (2), squid (3) or skipjack loins (4). Block states show it:
// kind, count and stage (0 fresh, 1 half, 2 dry). Progress is kept in a world dynamic property
// per rack, so time passes while nobody is near: on the next tick the rack catches up.
// Rain on a rack open to the sky pauses the drying (drips show it). No text anywhere.
//   use a fish / squid / skipjack  -> hang it (same kind, before it starts to dry, max 3)
//   use Salt on fresh fish         -> they become a salted batch
//   use with an empty hand         -> dry: take the whole batch; not yet: take the last one back
// v1.6.3 (F2): only an empty hand takes fish back (a sword used to pull the last fish off and lose its
// progress); anything else, and every other refused use, says why (util/hint.js).
// v1.6.3 (F1): the record also keeps the kind and stage, so a rack removed in any way (player, explosion,
// piston, command: contents.js) gives back its fish, or its dried goods once dry. Older records learn the
// kind and stage on the rack's next block tick.
// 1.7.0 (phase 1): with a container right below the rack, a dry batch drops into it on the rack's own tick
// (whatever does not fit keeps hanging, to be taken by hand or on a later tick).
import { EquipmentSlot, GameMode, ItemStack, system, world } from "@minecraft/server";
import { DRYING, FISH_ALIAS } from "../data/generated.js";
import { applyClass, upgradeLore } from "../fishing/size.js";
import { isRaining } from "../fishing/water.js";
import { spawnParticle } from "../util/particles.js";
import { refuseAt } from "../util/hint.js";
import { ambient, burst, on } from "./stationFx.js";
import { registerRecords, registerStation, spawnAll } from "./contents.js";
import { containerNext, putWhole } from "./nextContainer.js";

const NS = "kaleidoscope_fishing";
const KIND = `${NS}:kind`, COUNT = `${NS}:count`, STAGE = `${NS}:stage`;
const RACK = `${NS}:drying_rack`;
const PREFIX = `${NS}:dry:`;
const SALT = new Set(DRYING.salt);
const canon = id => FISH_ALIAS[id] ?? id;

const keyOf = b => `${PREFIX}${b.dimension.id}:${b.x}:${b.y}:${b.z}`;
const now = () => { try { return world.getAbsoluteTime(); } catch { return system.currentTick; } };
function load(b) {
  try { const v = JSON.parse(world.getDynamicProperty(keyOf(b)) ?? "null"); if (v && Array.isArray(v.items)) return v; } catch {}
  return { items: [], p: 0, t: now() };
}
function save(b, d) {
  try { world.setDynamicProperty(keyOf(b), d.items.length ? JSON.stringify(d) : undefined); } catch {}
}
const mainhand = p => p.getComponent("minecraft:equippable")?.getEquipmentSlot(EquipmentSlot.Mainhand);
const creative = p => { try { return p.getGameMode() === GameMode.Creative; } catch { return false; } };
function takeOne(player, slot) {
  if (creative(player)) return;
  const it = slot.getItem();
  if (!it) return;
  if (it.amount <= 1) slot.setItem(undefined); else { it.amount -= 1; slot.setItem(it); }
}
function give(player, block, stack) {
  try {
    const left = player?.getComponent("minecraft:inventory")?.container?.addItem(stack);
    if (left) block.dimension.spawnItem(left, block.center());
  } catch { try { block.dimension.spawnItem(stack, block.center()); } catch {} }
}
const snd = (block, id, pitch = 1, volume = 0.7) => { try { block.dimension.playSound(id, block.center(), { pitch, volume }); } catch {} };
const fx = (block, id, n = 4) => {
  for (let i = 0; i < n; i++) {
    try { spawnParticle(block.dimension, id, { x: block.x + 0.2 + Math.random() * 0.6, y: block.y + 0.3 + Math.random() * 0.5, z: block.z + 0.5 }); } catch {}
  }
};

// 1.5.0 (immersive pass, stationFx.js): the fish hang across the pole at about half height.
const hang = block => on(block, 0.5, 0.45, 0.5);
const sfx = (block, ...names) => burst(block.dimension, hang(block), ...names);
/** Idle: fresh fish drip, the breeze blows bits past; a dry batch glints now and then. Only with someone near. */
function idle(block, stage) {
  ambient(block, "rack", 190, hang(block), () => {
    if (stage >= 2) { if (Math.random() < 0.35) sfx(block, "sparkle"); return; }
    if (stage === 0 || Math.random() < 0.3) sfx(block, "drip_slow");
    if (Math.random() < 0.45) burst(block.dimension, on(block, 0.0, 0.55, 0.5), "breeze");
  });
}

function setState(block, kind, count, stage) {
  const d = load(block);                                // v1.6.3: the record knows what it is, for a rack that is gone
  if (d.items.length && (d.kind !== kind || d.stage !== stage)) { d.kind = kind; d.stage = stage; save(block, d); }
  try {
    block.setPermutation(block.permutation.withState(KIND, count ? kind : 0).withState(COUNT, count).withState(STAGE, count ? stage : 0));
  } catch {}
}
const stateOf = perm => ({ kind: Number(perm.getState(KIND) ?? 0), count: Number(perm.getState(COUNT) ?? 0), stage: Number(perm.getState(STAGE) ?? 0) });
// v1.2.0: the fish's whole description (size mark, "★ N cm" of a record) comes back with it
const rawStack = it => {
  const s = new ItemStack(it.id, 1);
  if (Array.isArray(it.lore) && it.lore.length) { try { s.setLore(upgradeLore(it.lore)); } catch {} return s; }   // 1.6.0: old "★ N cm" comes back as ★
  return it.cls ? applyClass(s, it.cls) : s;           // racks filled by v1.2.0-pre2..pre7
};
const productOf = kind => DRYING.kinds[kind]?.product;

/** Everything a rack holds, as item stacks (dry: products; otherwise the raw fish back). */
function contents(kind, stage, d) {
  if (stage >= 2) return d.items.map(() => new ItemStack(productOf(kind), 1));
  const out = d.items.map(rawStack);
  if (kind === 2 && out.length) out.push(new ItemStack(saltOf(d), 1));   // v1.6.3: a salted batch not yet dry gives its salt back too
  return out;
}
const saltOf = d => (typeof d.salt === "string" && SALT.has(d.salt) ? d.salt : DRYING.salt[0]);

/** 1.7.0: a dry batch drops into the container below the rack. How many went in. */
function dropBelow(block, kind, d) {
  const product = productOf(kind);
  if (!product || !d.items.length) return 0;
  const box = containerNext(block, ["below"]);
  if (!box) return 0;
  let n = 0;
  while (d.items.length && putWhole(box, new ItemStack(product, 1))) { d.items.pop(); n++; }
  if (!n) return 0;
  d.kind = kind; d.stage = 2;
  save(block, d);
  setState(block, kind, d.items.length, 2);
  snd(block, "dig.cloth", 1.5, 0.4);
  snd(block, "random.pop", 0.8, 0.3);
  return n;
}

const dryingRack = {
  onPlayerInteract({ block, player }) {
    if (!player) return;
    const slot = mainhand(player);
    const held = slot?.hasItem() ? slot.getItem() : undefined;
    const id = held ? canon(held.typeId) : undefined;
    const { kind, count, stage } = stateOf(block.permutation);
    const d = load(block);
    const want = id ? DRYING.inputs[id] : undefined;

    if (want) {                                           // hang one more
      if (count !== 0 && kind !== want) return refuseAt(player, "rack_other_kind", block);
      if (count !== 0 && stage !== 0) return refuseAt(player, "rack_drying", block);
      if (count >= DRYING.max) return refuseAt(player, "rack_full", block, DRYING.max);
      {
        let lore = [];
        try { lore = upgradeLore(held.getLore() ?? []); } catch {}
        d.items.push({ id, lore });
        if (count === 0) { d.p = 0; }
        d.t = now();
        save(block, d);
        takeOne(player, slot);
        setState(block, want, count + 1, 0);
        snd(block, "dig.cloth", 1.2);
        sfx(block, "drip");
      }
      return;
    }
    if (id && SALT.has(id)) {                             // rub salt on fresh fish
      if (kind === 1 && stage === 0 && count > 0) {
        d.salt = id; save(block, d);
        takeOne(player, slot);
        setState(block, 2, count, 0);
        snd(block, "dig.sand", 1.3);
        sfx(block, "salt", "salt");
        return;
      }
      return refuseAt(player, !count ? "rack_salt_empty" : kind === 2 ? "rack_salted" : kind !== 1 ? "rack_salt_fish_only" : "rack_drying", block);
    }
    if (!count) return refuseAt(player, held ? "rack_cannot_dry" : "rack_empty", block);
    if (held) return refuseAt(player, "rack_empty_hand", block);
    if (stage >= 2) {                                     // collect the whole dry batch
      for (const s of contents(kind, stage, d)) give(player, block, s);
      save(block, { items: [] });
      setState(block, 0, 0, 0);
      snd(block, "random.pop", 0.9);
      snd(block, "dig.cloth", 1.5, 0.4);
      return;
    }
    const it = d.items.pop();                             // not dry yet: take one back
    if (it) give(player, block, rawStack(it));
    if (kind === 2 && !d.items.length) give(player, block, new ItemStack(saltOf(d), 1));   // the last salted fish: the salt too
    save(block, d);
    setState(block, kind, d.items.length, d.items.length ? stage : 0);
    snd(block, "dig.cloth", 0.9);
  },

  onPlayerBreak({ block, brokenBlockPermutation, player }) {
    if (player && creative(player)) { save(block, { items: [] }); return; }
    dropRack(block.dimension, block, brokenBlockPermutation);
  },

  onTick({ block }) {
    const { kind, count, stage } = stateOf(block.permutation);
    if (!count) return;
    const d = load(block);
    if (d.items.length && (d.kind !== kind || d.stage !== stage)) { d.kind = kind; d.stage = stage; save(block, d); }   // pre-1.6.3 record
    if (stage >= 2) { if (!dropBelow(block, kind, d)) idle(block, stage); return; }
    if (!d.items.length) { setState(block, 0, 0, 0); return; }
    const t = now();
    const delta = Math.max(0, t - (d.t ?? t));
    d.t = t;
    // a short gap = the rack stayed loaded, so the weather we see now is the weather it had
    if (delta <= 400 && rainedOn(block)) {
      fx(block, "minecraft:water_drip_particle", 3);
      save(block, d);
      return;
    }
    d.p = (d.p ?? 0) + delta;
    const total = DRYING.kinds[kind]?.ticks ?? 48000;
    const next = Math.min(2, Math.floor(d.p / (total / 2)));
    save(block, d);
    if (next !== stage) {
      setState(block, kind, count, next);
      if (next === 2) { snd(block, "random.pop", 1.3, 0.4); fx(block, "minecraft:villager_happy", 3); sfx(block, "sparkle_burst"); dropBelow(block, kind, d); }
    } else idle(block, stage);
  },
};

function rainedOn(block) {
  if (!isRaining(block.dimension)) return false;
  try {
    const top = block.dimension.getTopmostBlock?.({ x: block.x, z: block.z });
    return !top || top.y <= block.y;
  } catch { return true; }
}

// --------------------------------------------------------------- for seagulls
/** Racks someone has hung something on, from the saved progress (dimension id + position). */
export function knownRacks() {
  const out = [];
  try {
    for (const k of world.getDynamicPropertyIds()) {
      if (!k.startsWith(PREFIX)) continue;
      const [dimId, x, y, z] = k.slice(PREFIX.length).split(/:(?=-?\d)/);
      out.push({ dimId, x: Number(x), y: Number(y), z: Number(z) });
    }
  } catch {}
  return out;
}
/** A gull takes one item off the rack (any kind except the hard skipjack loins). True if it did. */
export function stealFromRack(block) {
  try {
    if (block?.typeId !== RACK) return false;
    const { kind, count, stage } = stateOf(block.permutation);
    if (!count || kind === 4) return false;
    const d = load(block);
    if (!d.items.pop()) return false;
    save(block, d);
    setState(block, kind, d.items.length, stage);
    return true;
  } catch { return false; }
}

// v1.6.3 (F1): a rack gone by any means gives back what its record says (contents.js); until 1.6.2 the
// record was only tidied away here every 5 minutes and the fish were lost.
function dropRack(dim, pos, perm) {
  const key = `${PREFIX}${dim.id}:${pos.x}:${pos.y}:${pos.z}`;
  let d;
  try { d = JSON.parse(world.getDynamicProperty(key) ?? "null"); } catch {}
  try { world.setDynamicProperty(key, undefined); } catch {}
  if (!d || !Array.isArray(d.items) || !d.items.length) return;
  const s = perm ? stateOf(perm) : { kind: Number(d.kind) || 0, stage: Number(d.stage) || 0 };
  // a record from before 1.6.3 that never saw a tick: no kind known, so the fish come back raw
  spawnAll(dim, pos, contents(s.kind, productOf(s.kind) ? s.stage : 0, d));
}
registerStation(RACK, dropRack);
registerRecords(PREFIX, RACK, (dim, pos) => dropRack(dim, pos, undefined));

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(RACK, dryingRack);
});
