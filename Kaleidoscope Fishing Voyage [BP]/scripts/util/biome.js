// ## Biome ids, with Biomes O' Plenty (Bedrock port) support (1.6.x).
// Everything here that looks at a biome reads its id against patterns written for vanilla names
// (/ocean|beach|shore/, "swamp", /frozen|cold|snowy|.../). A BOP biome ("bop:maple_woods") matches none
// of them, so it is read as a vanilla-style stand-in first: its main category (coast -> beach, wetland ->
// swamp, else forest / plains / mountain / arid / cave / nether, Snowblossom Grove -> cherry_grove) with
// "cold_" in front when the BOP climate is cold. Warm, hot and temperate add nothing: none of the vanilla
// patterns for those apply outside the ocean, and BOP has no ocean biomes of its own.
// Table derived from BOP_BR docs/handshake.json v1.2.0 (64 biomes). Vanilla ids pass through unchanged.
const BOP = {
  auroral_garden: "cold_mountain",
  bayou: "swamp",
  bog: "cold_swamp",
  cold_desert: "plains",
  coniferous_forest: "forest",
  crag: "mountain",
  crystalline_chasm: "nether",
  dead_forest: "cold_forest",
  dryland: "arid",
  dune_beach: "beach",
  erupting_inferno: "nether",
  field: "plains",
  fir_clearing: "forest",
  floodplain: "swamp",
  forested_field: "plains",
  fungal_jungle: "cave",
  glowing_grotto: "cave",
  gravel_beach: "beach",
  highland: "mountain",
  hot_springs: "cold_mountain",
  jade_cliffs: "mountain",
  lavender_field: "plains",
  lush_desert: "arid",
  lush_savanna: "arid",
  maple_woods: "forest",
  marsh: "swamp",
  mediterranean_forest: "arid",
  moor: "mountain",
  muskeg: "cold_swamp",
  mystic_grove: "forest",
  old_growth_dead_forest: "forest",
  old_growth_woodland: "forest",
  ominous_woods: "forest",
  orchard: "forest",
  origin_valley: "forest",
  overgrown_greens: "forest",
  pasture: "plains",
  prairie: "plains",
  pumpkin_patch: "forest",
  rainforest: "forest",
  redwood_forest: "forest",
  rocky_rainforest: "forest",
  rocky_shrubland: "mountain",
  scrubland: "arid",
  seasonal_forest: "cold_forest",
  shrubland: "plains",
  snowblossom_grove: "cold_cherry_grove",
  snowy_coniferous_forest: "cold_forest",
  snowy_fir_clearing: "cold_forest",
  snowy_maple_woods: "cold_forest",
  spider_nest: "cave",
  subtropics: "forest",
  tropics: "beach",
  tundra: "cold_plains",
  undergrowth: "nether",
  visceral_heap: "nether",
  volcanic_plains: "arid",
  volcano: "mountain",
  wasteland: "arid",
  wasteland_steppe: "arid",
  wetland: "swamp",
  wintry_origin_valley: "cold_plains",
  withered_abyss: "nether",
  woodland: "forest",
};

/** The id to match vanilla patterns against: vanilla ids unchanged, BOP ids as their stand-in. */
export function canonBiome(id) {
  const s = String(id ?? "");
  if (!s.startsWith("bop:")) return s;
  return BOP[s.slice(4)] ?? s;
}

/** The biome id at a location ("" where the engine cannot tell), BOP ids already read as their stand-in. */
export function biomeIdAt(dim, loc) {
  try {
    if (typeof dim?.getBiome !== "function") return "";
    const b = dim.getBiome(loc);
    return canonBiome(b?.id ?? b?.typeId ?? "");
  } catch { return ""; }
}
