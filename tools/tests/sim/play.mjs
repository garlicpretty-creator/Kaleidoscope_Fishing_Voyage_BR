// Shared helpers for the play-through tests (tools/tests/test_play*.mjs): load the add-on into the simulation,
// then replay player actions against its real block components and event handlers.
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import * as S from './server.mjs';
import { __answers } from './server-ui.mjs';

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
export const BP = join(ROOT, 'Kaleidoscope Fishing Voyage [BP]');
export const NS = 'kaleidoscope_fishing:';
export const { __subs: subs, __log: log, __flush: flush, __player: P, __clock: clock, __overworld: D, __blockDefs: blockDefs, __dyn: dyn, __sent: sent, ItemStack, GameMode } = S;
/** The kaleidoscope_fishing:evt broadcasts sent since index `from` of `sent` (1.5.0). */
export const evts = (from = 0) => sent.slice(from).filter(e => e[0] === 'kaleidoscope_fishing:evt').map(e => JSON.parse(e[1]));
export { S, __answers as answers };
export const importScript = p => import(pathToFileURL(join(BP, 'scripts', p)).href);

let failed = 0;
export const ok = (c, m) => { if (!c) failed++; console.log(`${c ? 'OK  ' : 'FAIL'} ${m}`); };
export function finish(name) {
  const t = [...new Set(thrown)];
  const e = [...new Set(log.errors)];
  ok(!t.length, `${name}: no handler threw` + (t.length ? ':\n    ' + t.slice(0, 10).join('\n    ') : ''));
  ok(!e.length, `${name}: no invalid item id, amount or block state` + (e.length ? ':\n    ' + e.slice(0, 10).join('\n    ') : ''));
  console.log(failed ? `\n${failed} ${name} test(s) FAILED` : `\nall ${name} tests passed`);
  process.exit(failed ? 1 : 0);
}

/** Load main.js and run the startup handlers; returns the registered block components by name. */
export async function boot() {
  console.warn = () => {}; console.info = () => {};
  const quiet = console.log; console.log = () => {};
  await importScript('main.js');
  console.log = quiet;
  const comps = new Map();
  for (const fn of subs['system.beforeEvents.startup'] ?? []) fn({
    blockComponentRegistry: { registerCustomComponent: (n, c) => comps.set(n, c) },
    itemComponentRegistry: { registerCustomComponent() {} },
    customCommandRegistry: { registerCommand() {}, registerEnum() {} },
  });
  flush();
  P.mode = GameMode.Survival;
  return comps;
}

export const thrown = [];
export function guard(what, fn) { try { fn(); flush(); } catch (e) { thrown.push(`${what}: ${e.message}`); } }
export async function guardAsync(what, fn) { try { await fn(); flush(); } catch (e) { thrown.push(`${what}: ${e.message}`); } }
/** Fire every subscriber of an event, e.g. fire('world.afterEvents.itemUse', {...}). */
export function fire(name, ev) { guard(name, () => { for (const fn of subs[name] ?? []) fn(ev); }); return ev; }

let comps;
export function setComps(c) { comps = c; }
export const compsOf = b => Object.entries(blockDefs.get(b.typeId)?.components ?? {}).filter(([k]) => comps.has(k)).map(([k, v]) => [comps.get(k), v]);
export function use(b) {
  guard(`use ${b.typeId} with ${P.held()?.typeId ?? 'empty hand'}`, () => {
    const ev = { block: b, player: P, itemStack: P.held(), cancel: false, isFirstEvent: true, blockFace: 'Up', faceLocation: { x: 0.5, y: 1, z: 0.5 } };
    for (const fn of subs['world.beforeEvents.playerInteractWithBlock'] ?? []) fn(ev);
    flush();
    if (ev.cancel) return;
    for (const [c, params] of compsOf(b)) c.onPlayerInteract?.({ block: b, player: P, dimension: D, face: 'Up' }, { params });
  });
}
export function tick(b) { guard(`tick ${b.typeId}`, () => { for (const [c, params] of compsOf(b)) c.onTick?.({ block: b, dimension: D }, { params }); }); }
export function wait(b, t, steps = 4) { for (let i = 0; i < steps; i++) { clock.abs += Math.ceil(t / steps); if (b) tick(b); } }
export function breakBlock(b) {
  const perm = b.permutation, cs = compsOf(b);
  b.setType('minecraft:air');
  guard(`break ${perm.type.id}`, () => {
    for (const [c, params] of cs) c.onPlayerBreak?.({ block: b, brokenBlockPermutation: perm, player: P, dimension: D }, { params });
    for (const fn of subs['world.afterEvents.playerBreakBlock'] ?? []) fn({ block: b, brokenBlockPermutation: perm, player: P, dimension: D, itemStackBeforeBreak: P.held() });
  });
}
let nextX = 0;
export const place = (id, at) => D.place(id, at ?? { x: (nextX += 3), y: 64, z: 0 });
export const inv = id => P.inv.count(id.includes(':') ? id : NS + id);
export const st = (b, k) => b.permutation.getState(k.includes(':') ? k : NS + k);
export const clearInv = () => { for (let i = 0; i < 36; i++) P.inv.setItem(i, undefined); P.selectedSlotIndex = 0; };
export const drops = () => D.drops.splice(0);
export const ids = list => list.map(x => (x.id ?? x.typeId ?? x).split(':')[1]).join(', ');
