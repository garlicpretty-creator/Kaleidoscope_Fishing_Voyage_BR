// Map @minecraft/* to the stateful simulation in this folder (tools/tests/sim).
import { registerHooks } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const map = {
  '@minecraft/server': pathToFileURL(join(here, 'server.mjs')).href,
  '@minecraft/server-ui': pathToFileURL(join(here, 'server-ui.mjs')).href,
};
registerHooks({ resolve(spec, ctx, next) { return map[spec] ? { url: map[spec], shortCircuit: true } : next(spec, ctx); } });
