// ## Fishing minigame (v1.5), the pure part: no @minecraft/server here, so Node tests drive it directly.
// A game is a plain object. step() advances it one tick; the rod loop calls advance() every 2 ticks.
// The track runs 0 (deep, left) .. TRACK (surface, right). The player's box is pushed right while the
// use key is held and slides left when released; while the fish is inside the box progress rises.
import { MG, MOTION, PATTERN, DIFFICULTY } from "../data/minigame.js";

const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);
const between = (rand, [a, b]) => a + rand() * (b - a);

/** Difficulty 0..100 of a catch: its 1.3 fight value, rarity, size class; legends at the top. */
export function difficultyOf(entry, cls = 2, legend = false) {
  if (!entry) return 30;
  if (DIFFICULTY[entry.id] !== undefined) return DIFFICULTY[entry.id];
  let d = MG.FIGHT_DIFF[clamp(entry.fight ?? 0, 0, MG.FIGHT_DIFF.length - 1)];
  if (entry.w < MG.RARE_BELOW_W) d += (MG.RARE_BELOW_W - entry.w) * MG.RARE_PER_W;
  d += MG.SIZE_DIFF[cls] ?? 0;
  d = legend ? Math.max(d, MG.LEGEND_DIFF) : Math.min(d, MG.CAP);
  return clamp(Math.round(d), 0, 100);
}

export function patternOf(id, legend) {
  return legend ? "mixed" : PATTERN[id] ?? "smooth";
}

/** Box length from the rod tier and the line on it. */
export function boxSize(tier = 1, parts = {}) {
  return clamp((tier >= 2 ? MG.BOX.tier2 : MG.BOX.tier1) + (MG.LINE_BOX[parts.line] ?? 0), 12, 50);
}

/**
 * New game. opts: { id, entry, cls, legend, tier, parts:{hook,line,bobber}, coat:boolean, rand }
 */
export function newGame(opts) {
  const rand = opts.rand ?? Math.random;
  const legend = !!opts.legend;
  const D = difficultyOf(opts.entry, opts.cls, legend);
  const size = boxSize(opts.tier, opts.parts ?? {});
  const pattern = patternOf(opts.id, legend);
  return {
    id: opts.id, D, pattern, legend,
    size, box: 0, v: 0,
    fish: MG.TRACK * (0.35 + rand() * 0.3), target: MG.TRACK * 0.5, timer: 0, dashing: 0,
    sub: legend ? "smooth" : pattern, subTimer: MG.MIXED_SWITCH,
    deep: (opts.parts ?? {}).bobber === MG.WEIGHTED_BOBBER,
    lossMod: MG.BOBBER_LOSS[(opts.parts ?? {}).bobber] ?? 1,
    fallMod: opts.coat ? MG.RAINCOAT_FALL : 1,
    progress: MG.START, ticks: 0, inside: false, state: "play",
  };
}

function moveFish(g, rand) {
  const k = 1 + g.D / 60;                        // tougher fish change their mind more often
  if (g.pattern === "mixed" && --g.subTimer <= 0) {
    const all = ["smooth", "dart", "sinker", "dash"];
    g.sub = all[Math.floor(rand() * all.length)];
    g.subTimer = MG.MIXED_SWITCH;
  }
  const p = g.pattern === "mixed" ? g.sub : g.pattern;
  const m = MOTION[p];
  const T = MG.TRACK;
  if (--g.timer <= 0) {
    g.timer = Math.max(3, between(rand, m.every) / k);
    if (p === "smooth") g.target = rand() * T;
    else if (p === "dart") g.target = rand() < m.pause ? g.fish : rand() * T;
    else if (p === "sinker") g.target = rand() < m.rise ? rand() * T : rand() * rand() * T * 0.6;
    else if (p === "dash") {
      const far = rand() < m.dashChance + g.D / 400;
      g.target = far ? (g.fish < T / 2 ? T * (0.7 + rand() * 0.3) : T * rand() * 0.3) : clamp(g.fish + (rand() - 0.5) * 20, 0, T);
      g.dashing = far ? 12 : 0;
    }
    if (g.deep) g.target *= 0.8;                  // a weighted bobber keeps the fish deep
  }
  let ease = m.ease * (1 + g.D * MG.SPEED_D);
  if (p === "dash" && g.dashing > 0) { ease = m.dashEase * (1 + g.D * MG.SPEED_D * 0.5); g.dashing--; }
  g.fish += (g.target - g.fish) * clamp(ease, 0, 0.6);
  if (p === "sinker") g.fish -= m.drift * (1 + g.D / 100);
  g.fish = clamp(g.fish, 0, T);
}

/** One tick. holding: is the use key held. */
export function step(g, holding, rand = Math.random) {
  if (g.state !== "play") return g;
  g.ticks++;
  moveFish(g, rand);
  const max = MG.TRACK - g.size;
  g.v = clamp(g.v + (holding ? MG.HOLD_ACC : -MG.FALL_ACC * g.fallMod), -MG.VMAX, MG.VMAX);
  g.box += g.v;
  if (g.box < 0) { g.box = 0; if (g.v < 0) g.v = -g.v * MG.BOUNCE; }
  if (g.box > max) { g.box = max; if (g.v > 0) g.v = 0; }
  g.inside = g.fish >= g.box && g.fish <= g.box + g.size;
  g.progress += g.inside ? MG.GAIN * (1 - g.D * MG.GAIN_D) * (g.legend ? MG.LEGEND_PACE : 1)
                         : -MG.LOSS * (1 + g.D * MG.LOSS_D) * g.lossMod * (g.legend ? MG.LEGEND_LOSS_PACE : 1);
  g.progress = clamp(g.progress, 0, 1);
  if (g.progress >= 1) g.state = "won";
  else if (g.progress <= 0) g.state = "lost";
  return g;
}

export function advance(g, holding, ticks = MG.STEP_TICKS, rand = Math.random) {
  for (let i = 0; i < ticks && g.state === "play"; i++) step(g, holding, rand);
  return g.state;
}

/**
 * v1.5.8: whether the minigame writes the actionbar now. The actionbar is shared with other packs, so a
 * write happens only when the bar changed and HUD_EVERY ticks passed, or at once when the fish enters or
 * leaves the box (its colour is the feedback that must not lag). A key press needs no shortcut: in the
 * 2 ticks it could gain, the box moves less than one cell. An unchanged bar is rewritten every HUD_KEEP
 * ticks so it stays visible. `last` is the previous write.
 */
export function hudDue(last, text, age, inside) {
  if (!last) return true;
  if (text === last.text) return age - last.at >= MG.HUD_KEEP;
  if (inside !== last.inside) return true;
  return age - last.at >= MG.HUD_EVERY;
}

/** The two actionbar lines: the track (water, box, fish) and the progress bar. One glyph, colours only. */
export function hud(g, charset = "block") {
  const cs = MG.CHARSETS[charset] ?? MG.CHARSETS.block;
  const C = MG.COLORS, n = MG.CELLS, w = MG.TRACK / n;
  const fishCell = Math.min(n - 1, Math.floor(g.fish / w));
  let line = C.frame + cs.left, last = "";
  for (let i = 0; i < n; i++) {
    const lo = i * w, hi = lo + w;
    const inBox = hi > g.box && lo < g.box + g.size;
    const col = i === fishCell ? (g.inside ? C.caught : C.fish) : inBox ? C.box : C.water;
    if (col !== last) { line += col; last = col; }
    line += cs.cell;
  }
  line += C.frame + cs.right;
  const full = Math.round(g.progress * MG.PROG_CELLS);
  const bar = C.full + cs.cell.repeat(full) + C.empty + cs.cell.repeat(MG.PROG_CELLS - full);
  return `${line}\n${bar}`;
}
