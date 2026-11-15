// A permissive mock of @minecraft/server: anything not modelled answers with another harmless proxy,
// and every event subscription is recorded in `__subs` so tests can fire them.
export const __subs = {};
export const __timers = [];

function deep(name = 'mock') {
  const fn = function () {};
  return new Proxy(fn, {
    get(_, k) {
      if (k === 'then') return undefined;
      if (k === Symbol.toPrimitive) return () => 0;
      if (k === Symbol.iterator) return function* () {};
      if (k === 'toString') return () => name;
      return deep(`${name}.${String(k)}`);
    },
    apply() { return deep(`${name}()`); },
    construct() { return deep(`new ${name}`); },
  });
}

function events(prefix) {
  return new Proxy({}, {
    get(_, k) {
      const key = `${prefix}.${String(k)}`;
      return {
        subscribe(fn) { (__subs[key] ??= []).push(fn); return fn; },
        unsubscribe() {},
      };
    },
  });
}

const dyn = new Map();
export const world = new Proxy({
  afterEvents: events('world.afterEvents'),
  beforeEvents: events('world.beforeEvents'),
  getDynamicProperty: k => dyn.get(k),
  setDynamicProperty: (k, v) => { dyn.set(k, v); },
  getDynamicPropertyIds: () => [...dyn.keys()],
  getAllPlayers: () => [],
  getPlayers: () => [],
  sendMessage() {},
}, { get: (t, k) => (k in t ? t[k] : deep(`world.${String(k)}`)) });

export const system = new Proxy({
  afterEvents: events('system.afterEvents'),
  beforeEvents: events('system.beforeEvents'),
  currentTick: 0,
  run(fn) { __timers.push(['run', fn]); return 1; },
  runTimeout(fn, t) { __timers.push(['timeout', fn, t]); return 1; },
  runInterval(fn, t) { __timers.push(['interval', fn, t]); return 1; },
  runJob() { return 1; },
  clearRun() {},
  sendScriptEvent() {},
}, { get: (t, k) => (k in t ? t[k] : deep(`system.${String(k)}`)) });

export class ItemStack {
  constructor(typeId, amount = 1) { this.typeId = typeof typeId === 'string' ? typeId : String(typeId?.id); this.amount = amount; }
  getComponent() { return undefined; }
  getLore() { return []; }
  setLore() {}
  getDynamicProperty() { return undefined; }
  setDynamicProperty() {}
  clone() { return new ItemStack(this.typeId, this.amount); }
}
export const ItemTypes = { get: id => ({ id }) };
export const BlockPermutation = { resolve: (id, states) => ({ type: { id }, getState: k => states?.[k], withState() { return this; } }) };
export const EnchantmentTypes = { get: id => ({ id }) };
export const EquipmentSlot = { Mainhand: 'Mainhand', Offhand: 'Offhand', Head: 'Head', Chest: 'Chest', Legs: 'Legs', Feet: 'Feet' };
export const GameMode = { Creative: 'Creative', Survival: 'Survival', Adventure: 'Adventure', Spectator: 'Spectator' };
export class MolangVariableMap { setFloat() {} setColorRGB() {} setColorRGBA() {} setVector3() {} setSpeedAndDirection() {} }
