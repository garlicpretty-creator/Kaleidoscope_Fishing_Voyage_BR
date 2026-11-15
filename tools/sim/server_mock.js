// A small stand-in for @minecraft/server: enough state to drive the add-on's scripts in Node.
export const SIM = { events: {}, components: {}, scriptEvents: [], props: new Map(), tick: 1000, tags: {}, timeOfDay: 6000, moon: 0, runs: [] };
const bus = side => new Proxy({}, { get: (_, name) => ({ subscribe: (fn) => { (SIM.events[`${side}.${name}`] ??= []).push(fn); return fn; }, unsubscribe() {} }) });
export const GameMode = { Survival: 'Survival', Creative: 'Creative', Adventure: 'Adventure', Spectator: 'Spectator' };
export const EquipmentSlot = { Mainhand: 'Mainhand', Offhand: 'Offhand', Head: 'Head', Chest: 'Chest', Legs: 'Legs', Feet: 'Feet' };
export const ItemTypes = { get: id => ({ id }) };
export const EnchantmentTypes = { get: id => ({ id }) };
export class MolangVariableMap { setFloat() {} setColorRGB() {} setVector3() {} }
export class ItemStack {
  constructor(typeId, amount = 1) { this.typeId = typeId.includes(':') ? typeId : `minecraft:${typeId}`; this.amount = amount; this._lore = []; this._dp = {}; this.nameTag = undefined; }
  get maxAmount() { return 64; }
  getLore() { return [...this._lore]; } setLore(l) { this._lore = l ? [...l] : []; }
  getDynamicProperty(k) { return this._dp[k]; } setDynamicProperty(k, v) { if (v === undefined) delete this._dp[k]; else this._dp[k] = v; }
  hasTag(t) { return (SIM.tags[this.typeId] ?? []).includes(t); }
  getComponent() { return undefined; }
  clone() { const s = new ItemStack(this.typeId, this.amount); s._lore = [...this._lore]; s._dp = { ...this._dp }; s.nameTag = this.nameTag; return s; }
}
export class BlockPermutation {
  constructor(type, states) { this.type = { id: type }; this._s = { ...states }; }
  static resolve(type, states = {}) { return new BlockPermutation(type, states); }
  getState(k) { return this._s[k]; } withState(k, v) { return new BlockPermutation(this.type.id, { ...this._s, [k]: v }); }
  getAllStates() { return { ...this._s }; }
}
export const system = {
  get currentTick() { return SIM.tick; },
  run(fn) { SIM.runs.push(fn); return 0; }, runTimeout(fn) { return 0; }, runInterval(fn) { return 0; }, clearRun() {},
  sendScriptEvent(id, msg) { SIM.scriptEvents.push([id, msg]); },
  afterEvents: bus('system.after'), beforeEvents: new Proxy({}, { get: (_, name) => ({ subscribe: fn => {
    if (name === 'startup') fn({ blockComponentRegistry: { registerCustomComponent: (n, c) => { SIM.components[n] = c; } }, itemComponentRegistry: { registerCustomComponent() {} } });
    else (SIM.events[`system.before.${name}`] ??= []).push(fn);
  } }) }),
};
export const world = {
  afterEvents: bus('world.after'), beforeEvents: bus('world.before'),
  getDynamicProperty: k => SIM.props.get(k), setDynamicProperty: (k, v) => { if (v === undefined) SIM.props.delete(k); else SIM.props.set(k, v); },
  getDynamicPropertyIds: () => [...SIM.props.keys()],
  getDimension: id => SIM.dimension ?? { id: `minecraft:${id}`, getEntities: () => [], getPlayers: () => [] },
  getAllPlayers: () => [], getTimeOfDay: () => SIM.timeOfDay, getMoonPhase: () => SIM.moon, getEntity: () => undefined,
};
