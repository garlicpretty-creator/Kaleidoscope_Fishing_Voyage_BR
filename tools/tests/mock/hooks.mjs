// Map the @minecraft/* modules to local mocks so the add-on's scripts can be loaded by Node.
import { registerHooks } from 'node:module';
import { pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const map = {
  '@minecraft/server': pathToFileURL(join(here, 'server.mjs')).href,
  '@minecraft/server-ui': pathToFileURL(join(here, 'server-ui.mjs')).href,
};
registerHooks({
  resolve(spec, ctx, next) {
    if (map[spec]) return { url: map[spec], shortCircuit: true };
    return next(spec, ctx);
  },
});
