// ## Kaleidoscope script role: Guidebook extension publisher.
// Publishes the 森羅物語：漁歌 tab into Cookery's guidebook (KC_GUIDEBOOK_EXTENSION_API.md).
// Script Event messages are limited to 2048 characters, so the payload is ASCII-only
// JSON split into chunks of CHUNK characters: begin -> chunk x N -> end.
import { system } from "@minecraft/server";
import { ADDON_VERSION, GUIDEBOOK_JSON } from "../data/generated.js";

const SOURCE = "kaleidoscope_fishing";
const ID = "kaleidoscope_fishing:guidebook";
const CHUNK = 1500;
const PER_TICK = 8;
const EV = {
  ready: "kaleidoscope_cookery:guidebook_ready",
  ping: "kaleidoscope_cookery:guidebook_ping",
  begin: "kaleidoscope_cookery:guidebook_begin",
  chunk: "kaleidoscope_cookery:guidebook_chunk",
  end: "kaleidoscope_cookery:guidebook_end",
};

let publishing = false;
let published = false;

function publish() {
  if (publishing || published) return;
  publishing = true;
  const revision = `r${ADDON_VERSION.replace(/\./g, "_")}_${system.currentTick}`;
  const parts = [];
  for (let i = 0; i < GUIDEBOOK_JSON.length; i += CHUNK) parts.push(GUIDEBOOK_JSON.slice(i, i + CHUNK));
  system.sendScriptEvent(EV.begin, JSON.stringify({ api: 1, source: SOURCE, id: ID, revision, chunks: parts.length }));
  let index = 0;
  const handle = system.runInterval(() => {
    try {
      for (let n = 0; n < PER_TICK && index < parts.length; n++, index++) {
        system.sendScriptEvent(EV.chunk, `${SOURCE}\n${ID}\n${revision}\n${index}\n${parts[index]}`);
      }
      if (index >= parts.length) {
        system.clearRun(handle);
        system.sendScriptEvent(EV.end, JSON.stringify({ api: 1, source: SOURCE, id: ID, revision }));
        published = true;
        publishing = false;
      }
    } catch (err) {
      system.clearRun(handle);
      publishing = false;
      console.warn(`[Fishing Voyage] Guidebook publish failed: ${err}`);
    }
  }, 1);
}

system.afterEvents.scriptEventReceive.subscribe(ev => {
  if (ev.id === EV.ready) publish();
});
system.runTimeout(() => { try { system.sendScriptEvent(EV.ping, SOURCE); } catch {} }, 12);
