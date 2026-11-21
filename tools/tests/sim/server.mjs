// A small, stateful stand-in for @minecraft/server, good enough to replay player actions against the add-on's
// block components and event handlers: blocks with states, a player with an inventory and a held item,
// world dynamic properties, item drops and a controllable clock. Anything not modelled throws, so a test sees it.
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const BP = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..', 'Kaleidoscope Fishing Voyage [BP]');

export const __subs = {};
export const __sent = [];          // [id, message] of every system.sendScriptEvent
export const __log = { sounds: [], messages: [], particles: [], commands: [], forms: [], errors: [] };
const fail = m => { __log.errors.push(m); throw new Error(m); };
const queue = [];
export function __flush(limit = 50) { let n = 0; while (queue.length && n++ < limit) { const f = queue.shift(); f(); } }

function events(prefix) {
  return new Proxy({}, { get: (_, k) => ({ subscribe(fn) { (__subs[`${prefix}.${String(k)}`] ??= []).push(fn); return fn; }, unsubscribe() {} }) });
}

// ---------- known ids ----------
const itemIds = new Set(), blockDefs = new Map(), itemDefs = new Map();
for (const f of readdirSync(join(BP, 'items'))) {
  try { const it = JSON.parse(readFileSync(join(BP, 'items', f), 'utf8'))['minecraft:item']; itemIds.add(it.description.identifier); itemDefs.set(it.description.identifier, it); } catch {}
}
export const __itemDefs = itemDefs;
const tagsOf = id => itemDefs.get(id)?.components?.['minecraft:tags']?.tags ?? [];
for (const f of readdirSync(join(BP, 'blocks'))) {
  try { const b = JSON.parse(readFileSync(join(BP, 'blocks', f), 'utf8'))['minecraft:block']; blockDefs.set(b.description.identifier, b); } catch {}
}
export const __blockDefs = blockDefs;
/** Items of another (pretend) add-on a test adds and removes (register_board / register_tank). */
export const __otherItems = new Set();
const knownItem = id => itemIds.has(id) || __otherItems.has(id) || id.startsWith('minecraft:') || id.startsWith('kaleidoscope_cookery:') || blockDefs.has(id);

// ---------- items ----------
export class ItemStack {
  constructor(type, amount = 1) {
    const id = typeof type === 'string' ? type : type?.id;
    if (!id || !knownItem(id)) fail(`ItemStack: unknown item ${id}`);
    if (!Number.isInteger(amount) || amount < 1 || amount > 255) fail(`ItemStack: bad amount ${amount}`);
    this.typeId = id; this.amount = amount; this._lore = []; this._dyn = new Map(); this.nameTag = undefined;
  }
  get maxAmount() { const m = itemDefs.get(this.typeId)?.components?.['minecraft:max_stack_size']; return typeof m === 'number' ? m : (m?.value ?? (/_rod$|journal|knife|auger|bucket/.test(this.typeId) ? 1 : 64)); }
  getLore() { return [...this._lore]; }
  setLore(l) { this._lore = [...(l ?? [])]; }
  getDynamicProperty(k) { return this._dyn.get(k); }
  setDynamicProperty(k, v) { v === undefined ? this._dyn.delete(k) : this._dyn.set(k, v); }
  getDynamicPropertyIds() { return [...this._dyn.keys()]; }
  getComponent() { return undefined; }
  hasComponent() { return false; }
  getTags() { return [...tagsOf(this.typeId)]; }
  hasTag(t) { return tagsOf(this.typeId).includes(t); }
  isStackableWith(o) { return o && o.typeId === this.typeId && JSON.stringify(o._lore) === JSON.stringify(this._lore) && this.maxAmount > 1; }
  clone() { const s = new ItemStack(this.typeId, this.amount); s._lore = [...this._lore]; s._dyn = new Map(this._dyn); return s; }
}
export const ItemTypes = { get: id => (knownItem(id) ? { id } : undefined) };

class Container {
  constructor(size) { this.size = size; this.slots = new Array(size).fill(undefined); }
  get emptySlotsCount() { return this.slots.filter(s => !s).length; }
  getItem(i) { return this.slots[i]?.clone(); }
  setItem(i, s) { this.slots[i] = s ? s.clone() : undefined; }
  getSlot(i) { const c = this; return { hasItem: () => !!c.slots[i], getItem: () => c.getItem(i), setItem: s => c.setItem(i, s),
    get typeId() { return c.slots[i]?.typeId; }, get amount() { return c.slots[i]?.amount; }, set amount(v) { c.slots[i].amount = v; },
    getLore: () => c.slots[i]?.getLore() ?? [], isValid: () => true }; }
  addItem(stack) {
    let left = stack.amount;
    for (const s of this.slots) if (s && left && s.isStackableWith(stack)) { const n = Math.min(left, s.maxAmount - s.amount); s.amount += n; left -= n; }
    for (let i = 0; i < this.size && left; i++) if (!this.slots[i]) { const n = Math.min(left, stack.maxAmount); const c = stack.clone(); c.amount = n; this.slots[i] = c; left -= n; }
    if (!left) return undefined;
    const r = stack.clone(); r.amount = left; return r;
  }
  count(id) { return this.slots.reduce((a, s) => a + (s?.typeId === id ? s.amount : 0), 0); }
}

// ---------- blocks ----------
class Permutation {
  constructor(id, states) { this.type = { id }; this._s = { ...states }; }
  getState(k) { return this._s[k]; }
  getAllStates() { return { ...this._s }; }
  withState(k, v) {
    const def = blockDefs.get(this.type.id)?.description?.states?.[k];
    if (!def) fail(`withState: ${this.type.id} has no state ${k}`);
    const ok = Array.isArray(def) ? def.includes(v) : (def.values ? (v >= def.values.min && v <= def.values.max) : true);
    if (!ok) fail(`withState: ${this.type.id} ${k}=${v} out of range`);
    return new Permutation(this.type.id, { ...this._s, [k]: v });
  }
  matches(id, st) { return id === this.type.id && Object.entries(st ?? {}).every(([k, v]) => this._s[k] === v); }
}
function defaultPerm(id) {
  const st = {};
  for (const [k, v] of Object.entries(blockDefs.get(id)?.description?.states ?? {})) st[k] = Array.isArray(v) ? v[0] : v.values?.min ?? 0;
  for (const t of Object.values(blockDefs.get(id)?.description?.traits ?? {})) for (const s of t.enabled_states ?? []) st[s] = s.includes('cardinal') ? 'north' : s.includes('facing') ? 'north' : 0;
  return new Permutation(id, st);
}
export const BlockPermutation = { resolve: (id, st) => { const p = defaultPerm(id); for (const [k, v] of Object.entries(st ?? {})) p._s[k] = v; return p; } };

class Block {
  constructor(dim, x, y, z, id) { this.dimension = dim; this.x = x; this.y = y; this.z = z; this.permutation = id === 'minecraft:air' ? new Permutation(id, {}) : defaultPerm(id); }
  get typeId() { return this.permutation.type.id; }
  get type() { return this.permutation.type; }
  get location() { return { x: this.x, y: this.y, z: this.z }; }
  get isAir() { return this.typeId === 'minecraft:air'; }
  get isLiquid() { return this.typeId === 'minecraft:water' || this.typeId === 'minecraft:lava'; }
  get isValid() { return true; }
  isWaterlogged = false;
  center() { return { x: this.x + 0.5, y: this.y + 0.5, z: this.z + 0.5 }; }
  bottomCenter() { return { x: this.x + 0.5, y: this.y, z: this.z + 0.5 }; }
  setPermutation(p) { this.permutation = p; }
  setType(id) { this._box = undefined; this.permutation = id === 'minecraft:air' ? new Permutation(id, {}) : defaultPerm(id); }
  above(n = 1) { return this.dimension.getBlock({ x: this.x, y: this.y + n, z: this.z }); }
  below(n = 1) { return this.dimension.getBlock({ x: this.x, y: this.y - n, z: this.z }); }
  north(n = 1) { return this.dimension.getBlock({ x: this.x, y: this.y, z: this.z - n }); }
  south(n = 1) { return this.dimension.getBlock({ x: this.x, y: this.y, z: this.z + n }); }
  east(n = 1) { return this.dimension.getBlock({ x: this.x + n, y: this.y, z: this.z }); }
  west(n = 1) { return this.dimension.getBlock({ x: this.x - n, y: this.y, z: this.z }); }
  offset(o) { return this.dimension.getBlock({ x: this.x + o.x, y: this.y + o.y, z: this.z + o.z }); }
  hasTag() { return false; }
  getTags() { return []; }
  // 1.7.0: a chest or barrel has an inventory (the shrimp trap and the drying rack put things in one)
  getComponent(n) {
    if ((n === 'minecraft:inventory' || n === 'inventory') && CONTAINER_BLOCKS.has(this.typeId)) return { container: (this._box ??= new Container(27)) };
    return undefined;
  }
}
const CONTAINER_BLOCKS = new Set(['minecraft:chest', 'minecraft:barrel', 'minecraft:trapped_chest']);
class Dimension {
  constructor(id) { this.id = id; this.blocks = new Map(); this.drops = []; this.entities = []; }
  key(l) { return `${Math.floor(l.x)},${Math.floor(l.y)},${Math.floor(l.z)}`; }
  getBlock(l) { const k = this.key(l); if (!this.blocks.has(k)) this.blocks.set(k, new Block(this, Math.floor(l.x), Math.floor(l.y), Math.floor(l.z), 'minecraft:air')); return this.blocks.get(k); }
  place(id, l) { const b = this.getBlock(l); b.setType(id); return b; }
  spawnItem(stack, loc) { if (!(stack instanceof ItemStack)) fail('spawnItem: not an ItemStack'); this.drops.push({ id: stack.typeId, amount: stack.amount, lore: stack.getLore(), loc }); return { typeId: 'minecraft:item' }; }
  playSound(id, loc, o) { __log.sounds.push(id); }
  spawnParticle(id) { __log.particles.push(id); }
  getTopmostBlock() { return { y: 64 }; }
  getWeather() { return 'Clear'; }
  getEntities() { return []; }
  getEntitiesAtBlockLocation() { return []; }
  getPlayers() { return world.getAllPlayers(); }
  runCommand(c) { __log.commands.push(c); return { successCount: 1 }; }
  spawnEntity(id, loc) { const e = { typeId: id, location: loc, isValid: true, id: String(Math.random()), getComponent: () => undefined, setProperty() {}, getProperty() {}, setDynamicProperty() {}, getDynamicProperty() {}, addTag() {}, hasTag: () => false, remove() {} }; this.entities.push(e); return e; }
}

// ---------- player ----------
export const EquipmentSlot = { Mainhand: 'Mainhand', Offhand: 'Offhand', Head: 'Head', Chest: 'Chest', Legs: 'Legs', Feet: 'Feet' };
export const GameMode = { Creative: 'Creative', Survival: 'Survival', Adventure: 'Adventure', Spectator: 'Spectator' };
class Player {
  constructor(dim) {
    this.id = 'p1'; this.name = 'Tester'; this.nameTag = 'Tester'; this.typeId = 'minecraft:player'; this.dimension = dim; this.location = { x: 0.5, y: 65, z: 0.5 };
    this.inv = new Container(36); this.selectedSlotIndex = 0; this.mode = GameMode.Survival; this._dyn = new Map(); this.isSneaking = false; this.isValid = true;
    this.equip = { Head: undefined, Chest: undefined, Legs: undefined, Feet: undefined, Offhand: undefined };
  }
  getGameMode() { return this.mode; }
  getComponent(name) {
    const p = this;
    if (name === 'minecraft:inventory' || name === 'inventory') return { container: p.inv, inventorySize: 36 };
    if (name === 'minecraft:equippable' || name === 'equippable') return {
      getEquipmentSlot: s => (s === EquipmentSlot.Mainhand ? p.inv.getSlot(p.selectedSlotIndex)
        : { hasItem: () => !!p.equip[s], getItem: () => p.equip[s], setItem: i => { p.equip[s] = i; }, get typeId() { return p.equip[s]?.typeId; } }),
      getEquipment: s => (s === EquipmentSlot.Mainhand ? p.inv.getItem(p.selectedSlotIndex) : p.equip[s]),
      setEquipment: (s, i) => { if (s === EquipmentSlot.Mainhand) p.inv.setItem(p.selectedSlotIndex, i); else p.equip[s] = i; },
    };
    return undefined;
  }
  hold(id, n = 1) { this.inv.setItem(this.selectedSlotIndex, id ? new ItemStack(id, n) : undefined); }
  held() { return this.inv.getItem(this.selectedSlotIndex); }
  playSound(id) { __log.sounds.push(id); }
  sendMessage(m) { __log.messages.push(typeof m === 'string' ? m : JSON.stringify(m)); }
  getDynamicProperty(k) { return this._dyn.get(k); }
  setDynamicProperty(k, v) { v === undefined ? this._dyn.delete(k) : this._dyn.set(k, v); }
  getDynamicPropertyIds() { return [...this._dyn.keys()]; }
  getRotation() { return { x: 0, y: 0 }; }
  getViewDirection() { return { x: 0, y: 0, z: 1 }; }
  getHeadLocation() { return { ...this.location, y: this.location.y + 1.6 }; }
  addEffect() {}
  addTag() {} hasTag() { return false; } getTags() { return []; } removeTag() {}
  runCommand(c) { __log.commands.push(c); return { successCount: 1 }; }
  get onScreenDisplay() { return { setActionBar() {}, setTitle() {}, updateSubtitle() {} }; }
  get camera() { return { fade() {}, setCamera() {}, clear() {} }; }
  getBlockFromViewDirection() { return undefined; }
}

// ---------- world / system ----------
const dyn = new Map();
const overworld = new Dimension('minecraft:overworld');
const dims = { 'minecraft:overworld': overworld, overworld, 'minecraft:nether': new Dimension('minecraft:nether'), 'minecraft:the_end': new Dimension('minecraft:the_end') };
export const __player = new Player(overworld);
export const __clock = { abs: 1000, day: 6000, moon: 0 };
export const world = {
  afterEvents: events('world.afterEvents'),
  beforeEvents: events('world.beforeEvents'),
  getDynamicProperty: k => dyn.get(k),
  setDynamicProperty: (k, v) => { if (v === undefined) dyn.delete(k); else { if (typeof v === 'string' && v.length > 32767) throw new Error('dynamic property too long'); dyn.set(k, v); } },
  getDynamicPropertyIds: () => [...dyn.keys()],
  getAllPlayers: () => [__player],
  getPlayers: () => [__player],
  getDimension: id => dims[id] ?? overworld,
  getAbsoluteTime: () => __clock.abs,
  getTimeOfDay: () => __clock.day,
  getDay: () => Math.floor(__clock.abs / 24000),
  getMoonPhase: () => __clock.moon,
  sendMessage: m => __log.messages.push(String(m)),
  getEntity: () => undefined,
  scoreboard: { getObjective: () => undefined, addObjective: () => ({ setScore() {}, getScore: () => 0 }) },
  gameRules: {},
};
export const __dyn = dyn;
export const system = {
  afterEvents: events('system.afterEvents'),
  beforeEvents: events('system.beforeEvents'),
  get currentTick() { return __clock.abs; },
  run(fn) { queue.push(fn); return 1; },
  runTimeout(fn) { queue.push(fn); return 1; },
  runInterval() { return 1; },
  runJob() { return 1; },
  clearRun() {},
  sendScriptEvent(id, message) { __sent.push([id, message]); },
};
export const EnchantmentTypes = { get: id => ({ id }) };
export class MolangVariableMap { setFloat() {} setColorRGB() {} setColorRGBA() {} setVector3() {} setSpeedAndDirection() {} }
export const __overworld = overworld;
