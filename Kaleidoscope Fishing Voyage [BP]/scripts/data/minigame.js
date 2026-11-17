// v1.5 fishing minigame: every number the minigame uses. Pure data (see plans/漁歌_1.5_釣魚小遊戲設計.md §2).
// Units: the track is 0..TRACK (left = deep, right = surface); speeds and progress are per game tick.

export const MG = {
  TRACK: 100,
  CELLS: 24,                 // track drawn as this many cells
  PROG_CELLS: 20,            // progress bar cells
  STEP_TICKS: 2,             // the rod loop runs every 2 ticks: the game takes 2 steps per run
  // v1.5.8 actionbar sharing: the minigame writes only while a fight is on, and only when the bar changes
  HUD_EVERY: 4,              // ticks between two writes of a changed bar (5 per second)...
  HUD_KEEP: 30,              // ...an unchanged bar is written again only this often, so it does not fade

  BOX: { tier1: 24, tier2: 28 },        // box length by rod tier (bamboo rod = tier 1)
  HOLD_ACC: 0.9,             // holding the use key pushes the box right
  FALL_ACC: 0.6,             // releasing lets it slide left (1.4.0 playtest: 0.9 slid back too fast)
  VMAX: 4.0,
  BOUNCE: 0.4,               // hitting the left end bounces back at this fraction

  START: 0.30,               // progress at the start
  GAIN: 0.012,               // per tick while the fish is inside the box (x (1 - D * GAIN_D) x legend pace)
  LOSS: 0.005,               // per tick while outside (x (1 + D * LOSS_D) x tackle factor x legend pace); 1.4.0 playtest: 0.008 drained too fast
  GAIN_D: 0.003, LOSS_D: 0.004,
  SPEED_D: 0.008,            // fish speed x (1 + D * SPEED_D)
  CAP: 85,                   // highest difficulty a non-legend can reach
  LEGEND_PACE: 0.38,         // legends: progress rises this much slower: 45-80 s with mistakes (G035)
  LEGEND_LOSS_PACE: 0.5,     // ...and falls this much slower: a legend forgives fewer mistakes than it rewards

  // difficulty 0..100
  FIGHT_DIFF: [12, 28, 46, 64, 80],     // by the catch's 1.3 "fight" value
  RARE_BELOW_W: 12, RARE_PER_W: 1.0,    // + per point of weight below 12
  SIZE_DIFF: { 1: -6, 2: 0, 3: 8 },     // small / medium / large
  LEGEND_DIFF: 92,                      // legends: at least this (overridden per fish below)

  // tackle and gear
  LINE_BOX: { 'kaleidoscope_fishing:hemp_line': 2, 'kaleidoscope_fishing:wire_line': 4, 'kaleidoscope_fishing:clear_line': -2 },
  BOBBER_LOSS: { 'kaleidoscope_fishing:bamboo_bobber': 0.8 },
  WEIGHTED_BOBBER: 'kaleidoscope_fishing:weighted_bobber',   // fish keep lower (deeper) on the track
  RAINCOAT_FALL: 0.85,       // a straw raincoat steadies the slide

  MIXED_SWITCH: 60,          // ticks between pattern switches for "mixed" (legends)

  // drawing
  COLORS: { frame: '§7', water: '§8', box: '§a', fish: '§b', caught: '§e', full: '§2', empty: '§8' },
  CHARSETS: { block: { cell: '█', left: '▕', right: '▏' }, ascii: { cell: '#', left: '[', right: ']' } },
};

// Swimming pattern by fish. Anything not listed swims "smooth"; legends always "mixed".
export const PATTERN = {
  'kaleidoscope_fishing:sculk_lanternfish': 'dart',   // 1.5.0
  'kaleidoscope_fishing:echo_ray': 'sinker',   // 1.5.0
  'kaleidoscope_fishing:cherry_trout': 'dash',   // 1.5.0
  'kaleidoscope_fishing:mycelium_flounder': 'sinker',   // 1.5.0
  'kaleidoscope_fishing:yellow_croaker': 'dart', 'kaleidoscope_fishing:saury': 'dart', 'kaleidoscope_fishing:flying_fish': 'dart',
  'minecraft:tropical_fish': 'dart', 'kaleidoscope_fishing:skipjack': 'dart', 'kaleidoscope_fishing:golden_croaker': 'dart',
  'kaleidoscope_fishing:mudskipper': 'dart', 'kaleidoscope_fishing:blazefin': 'dart', 'kaleidoscope_fishing:chorus_carp': 'dart',

  'kaleidoscope_fishing:catfish': 'sinker', 'kaleidoscope_fishing:eel': 'sinker', 'kaleidoscope_fishing:grouper': 'sinker',
  'kaleidoscope_fishing:anglerfish': 'sinker', 'kaleidoscope_fishing:lava_eel': 'sinker', 'kaleidoscope_fishing:void_eel': 'sinker',
  'kaleidoscope_fishing:loach': 'sinker', 'kaleidoscope_fishing:snakehead': 'sinker', 'kaleidoscope_fishing:octopus': 'sinker',
  'kaleidoscope_fishing:cave_blindfish': 'sinker', 'kaleidoscope_fishing:ender_angler': 'sinker', 'minecraft:pufferfish': 'sinker',

  'kaleidoscope_fishing:tuna': 'dash', 'kaleidoscope_fishing:sea_bream': 'dash', 'kaleidoscope_fishing:hairtail': 'dash',
  'kaleidoscope_fishing:sea_bass': 'dash', 'kaleidoscope_fishing:rainbow_trout': 'dash', 'kaleidoscope_fishing:arctic_char': 'dash',
  'kaleidoscope_fishing:magma_koi': 'dash', 'kaleidoscope_fishing:starfin': 'dash', 'minecraft:salmon': 'dash',
};

// Per-fish difficulty overrides (0..100). Legends are listed so their order of toughness is explicit.
export const DIFFICULTY = {
  'kaleidoscope_fishing:frostlake_char': 92,
  'kaleidoscope_fishing:river_lord_catfish': 95,
  'kaleidoscope_fishing:lava_dragon_koi': 97,
  'kaleidoscope_fishing:emperor_tuna': 100,
};

// Pattern tuning: how often the fish picks a new target (ticks, before difficulty) and how fast it moves there.
export const MOTION = {
  smooth: { every: [16, 32], ease: 0.03 },
  dart:   { every: [8, 16], ease: 0.12, pause: 0.3 },
  sinker: { every: [10, 22], ease: 0.06, drift: 0.2, rise: 0.25 },
  dash:   { every: [20, 40], ease: 0.04, dashEase: 0.16, dashChance: 0.18 },
};
