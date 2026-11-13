// ## Village decor (v1.4): glass float, anchor, hanging net, string of dried fish, crate of the catch.
// Pure decoration; the only behaviour is that the hanging net goes on walls only, turned to the face
// that was clicked (like the Fish Print).
import { system } from "@minecraft/server";

const NS = "kaleidoscope_fishing";
const WALL_FACES = { North: "north", South: "south", East: "east", West: "west" };

const wallDecor = {
  beforeOnPlayerPlace(e) {
    const dir = WALL_FACES[String(e.face)] ?? WALL_FACES[String(e.face).replace(/^./, c => c.toUpperCase())];
    if (!dir) { e.cancel = true; return; }
    try { e.permutationToPlace = e.permutationToPlace.withState("minecraft:cardinal_direction", dir); } catch {}
  },
};

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent(`${NS}:wall_decor`, wallDecor);
});
