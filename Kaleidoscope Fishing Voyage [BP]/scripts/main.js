// ============================================================================
// 森羅物語：漁歌 / Kaleidoscope Cookery: Fishing Voyage — script entry
// Role: ADDON. Talks to Kaleidoscope Cookery only through its public Script Event
// API. Never imports Cookery's scripts and never hard-depends on its pack UUID.
// ============================================================================
import "./kc/bridge.js";
import "./kc/guidebookPublisher.js";
import "./fishing/registry.js";   // v1.6.2: register_bait / register_catch for other packs
import "./api/host.js";           // 1.5.0: events, and the state / record / catalog requests
import "./api/family.js";         // 1.5.0: handshakes with Herbal, Harvest and Ranching
import "./api/burntTeaStart.js";    // handshakes with Order To Cook and Grilling (burnt-tea-dev)
import "./fishing/rod.js";
import "./fishing/minigameSwitch.js";
import "./events/foodEffects.js";
import "./events/clamDigging.js";
import "./journal/journal.js";
import "./blocks/fishTrap.js";
import "./blocks/feast.js";
import "./blocks/shoreDrop.js";
import "./tools/basket.js";
import "./tools/knife.js";
import "./tools/handNet.js";      // 1.6.0: the Hand Net (pond, tub, tank)
import "./blocks/decor.js";
import "./blocks/tanks.js";
import "./journal/recipes.js";
import "./blocks/cleaning.js";
import "./blocks/drying.js";
import "./blocks/iceHole.js";
import "./blocks/fishSauceJar.js";
import "./blocks/villageDecor.js";
import "./blocks/tideClock.js";
import "./blocks/tub.js";          // 1.5.0: the Wooden Tub (purging clams, hatching roe)
import "./blocks/saltPan.js";      // 1.5.0: the Salt Pan     // 1.5.0: the Tide Clock hung on a wall
import "./world/schools.js";
import "./creatures/seagull.js";
import "./creatures/cormorant.js";
import "./creatures/pets.js";      // 1.5.0: Fish Bones tame wolves, our fish tame cats
import "./world/merchant.js";
import "./world/sky.js";         // 1.5.0: meteor showers and aurora nights
import "./blocks/glassFloat.js";   // 1.5.0: star sand makes a glass float glow
import "./blocks/pond.js";         // 1.5.0: the fish pond
import "./world/boat.js";         // 1.5.0: fishing from a boat, the Fishing Skiff
