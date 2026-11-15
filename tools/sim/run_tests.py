"""Run the add-on's scripts in Node against a stand-in for the Minecraft script API, and check what they do.

  python tools/sim/run_tests.py           (needs Node.js 18 or newer)

It copies scripts/ into a temporary folder next to the mocks of @minecraft/server and @minecraft/server-ui
(tools/sim/*_mock.js) and runs tools/sim/test.mjs there: the Fish Cleaning Board's cuts for every catch, the
Fish Creel, the legend conditions with the keepsake parts, the Fish Merchant's prices and orders, food effects,
the minigame settings and the Fish Tank tables. It cannot show anything that needs the game itself: models,
textures, sounds, the UI, world generation, or how the engine treats the files.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'Kaleidoscope Fishing Voyage [BP]', 'scripts')


def main():
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(SCRIPTS, os.path.join(tmp, 'scripts'))
        for pkg, mock in (('server', 'server_mock.js'), ('server-ui', 'server_ui_mock.js')):
            d = os.path.join(tmp, 'node_modules', '@minecraft', pkg)
            os.makedirs(d)
            shutil.copy(os.path.join(HERE, mock), os.path.join(d, 'index.js'))
            with open(os.path.join(d, 'package.json'), 'w') as f:
                f.write('{"type":"module","main":"index.js"}')
        with open(os.path.join(tmp, 'package.json'), 'w') as f:
            f.write('{"type":"module"}')
        shutil.copy(os.path.join(HERE, 'test.mjs'), tmp)
        r = subprocess.run(['node', 'test.mjs'], cwd=tmp)
        sys.exit(r.returncode)


if __name__ == '__main__':
    main()
