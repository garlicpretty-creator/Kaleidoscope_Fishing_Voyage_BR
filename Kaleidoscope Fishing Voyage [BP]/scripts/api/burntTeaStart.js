// ## Kaleidoscope script role: handshakes with burnt-tea-dev's packs (下單了 menu and stove, 煙火 skewers).
// They take registrations without an api_ping of their own; see api/burntTea.js. Optional: without them, nothing happens.
import { system } from "@minecraft/server";
import { startBurntTea } from "./burntTea.js";
import { OTC_FOODS, SMOKER_RECIPES } from "../data/burntTeaCatalog.js";

startBurntTea(system, { source: "kaleidoscope_fishing", foods: OTC_FOODS, smoking: SMOKER_RECIPES });
