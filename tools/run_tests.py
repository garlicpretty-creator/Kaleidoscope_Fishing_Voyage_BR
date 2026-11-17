"""Run every offline test of the pack in one go:   python tools/run_tests.py

  1. build.py check       generated.js matches tools/data
  2. validate.py          cross-references; only findings not in tests/validate_baseline.txt fail
  3. check_models.py      3D model structure (the 10 models borrowed from Cookery are verified only when a
                          Kaleidoscope-Cookery-*.mcaddon sits next to this repository folder)
  4. tests/test_pack.py   JSON, manifests, icons, RTX maps, catalog, placeable blocks, spawn eggs, features
  5. tests/test_scripts.mjs  scripts under a mock game API: loading, custom components, the register API,
                          legend conditions, the 1.4 species (needs Node.js 22.15+)
  6-8. tests/test_play*.mjs  play-throughs in a stateful simulation (tests/sim): workstations, fishing from cast
                          to catch, feasts, tanks, merchant, gulls, cormorants, digging, journal, Cookery bridge

None of this replaces playing the pack: it only proves the files and the script logic hang together.
Exit code 1 if any step fails.
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENV = dict(os.environ, PYTHONUTF8='1')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')   # test output has ★ and ✦
except AttributeError:
    pass
results = []


def run(name, cmd, judge=None):
    print(f'\n=== {name}')
    p = subprocess.run(cmd, cwd=ROOT, env=ENV, capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = (p.stdout or '') + (p.stderr or '')
    good, note = judge(out) if judge else (p.returncode == 0, '')
    print(out.rstrip() if not good or (name.startswith('tests') and 'play' not in name) else '\n'.join(out.rstrip().splitlines()[-2:]))
    if note:
        print(note)
    results.append((name, good))


def judge_validate(out):
    base = os.path.join(HERE, 'tests', 'validate_baseline.txt')
    known = {l.strip() for l in open(base, encoding='utf-8') if l.strip() and not l.startswith('#')}
    found = {l.strip() for l in out.splitlines() if l.strip() and not l.startswith(('defined ', 'PROBLEMS '))}
    new = sorted(found - known)
    gone = len(known - found)
    note = (f'{len(found)} findings, all known false positives' if not new else 'NEW findings:\n  ' + '\n  '.join(new))
    if gone:
        note += f'\n({gone} baseline finding(s) no longer appear; tools/tests/validate_baseline.txt can be trimmed)'
    return not new, note


py = sys.executable
run('build.py check', [py, '-X', 'utf8', 'tools/build.py', 'check'], lambda o: ('matches' in o, ''))
run('validate.py', [py, '-X', 'utf8', 'tools/validate.py', '.'], judge_validate)
run('check_models.py', [py, '-X', 'utf8', 'tools/check_models.py'], lambda o: (any(l.startswith('0 error(s)') for l in o.splitlines()), ''))
run('tests/test_pack.py', [py, '-X', 'utf8', 'tools/tests/test_pack.py'])
node = shutil.which('node')
if node:
    run('tests/test_scripts.mjs', [node, '--import', './tools/tests/mock/hooks.mjs', 'tools/tests/test_scripts.mjs'])
    for t in ('test_play', 'test_play_fishing', 'test_play_world'):
        run(f'tests/{t}.mjs', [node, '--import', './tools/tests/sim/hooks.mjs', f'tools/tests/{t}.mjs'])
    run('tests/burnt_tea.test.mjs', [node, '--test', 'tools/tests/burnt_tea.test.mjs'])
else:
    print('\n=== tests/test_scripts.mjs\nskipped: Node.js not found')
    results.append(('tests/test_scripts.mjs (skipped, no Node.js)', False))

print('\n=== summary')
for name, good in results:
    print(f"{'PASS' if good else 'FAIL'}  {name}")
sys.exit(0 if all(g for _, g in results) else 1)
