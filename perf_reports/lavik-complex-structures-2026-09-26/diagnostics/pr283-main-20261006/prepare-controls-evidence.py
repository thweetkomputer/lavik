"""Collect complete PR283 evidence; never stage, commit or publish automatically."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

W = Path(__file__).parent
REPO = Path('/mnt/dev/lavik-complex-refresh-20261004')
R = REPO / 'perf_reports/lavik-complex-structures-2026-09-26'
D = R / 'diagnostics/pr283-main-20261006'
assert 'ALL_PR283_REPEATS_COMPLETE' in (W / 'controls-driver.log').read_text()
assert 'ALL_PR283_PROFILES_COMPLETE' in (W / 'main-refresh-driver.log').read_text()


def run(name, *args):
    subprocess.run([sys.executable, str(W / name), *map(str, args)], check=True)


run('summarize-controls.py', '--output', W / 'controls-validation.json')
run('audit-commands.py', '--input', W / 'pr283-repeats.json',
    '--output', W / 'controls-command-audit.json')
run('render-controls.py', '--observations', W / 'pr283-repeats.json',
    '--validation', W / 'controls-validation.json',
    '--audit', W / 'controls-command-audit.json', '--output', W / 'pr283-complete.md')
run('validate-profiles.py')
run('summarize-perf.py')
run('render-perf.py', '--output', W / 'pr283-perf.md')
names = ['pr283-repeats.json', 'controls-validation.json', 'controls-command-audit.json',
         'pr283-complete.md', 'pr283-perf.md', 'profiles.json',
         'profile-observations.json', 'profile-command-audit.json',
         'pr283-self-comparison.json', 'controls-driver.log', 'duration-analysis-amendment.json',
         'small-read-c320-audit.json',
         'summarize-controls.py', 'audit-commands.py', 'render-controls.py',
         'validate-profiles.py', 'summarize-perf.py', 'render-perf.py',
         'profile-ordered-allworkers.py', 'prepare-controls-evidence.py']
names += [p.name for p in W.glob('pr283-*-self-summary.json')]
for name in names:
    shutil.copyfile(W / name, D / name)

# A mutable main-refresh log is not copied as a completed-task log while its
# grid runs are still active. Keep just its completed profiling prefix.
log = (W / 'main-refresh-driver.log').read_text().splitlines()
end = next(i for i, line in enumerate(log) if line.startswith('ALL_PR283_PROFILES_COMPLETE'))
(D / 'profiles-driver.log').write_text('\n'.join(log[:end + 1]) + '\n')
obs = json.loads((W / 'pr283-repeats.json').read_text())
profiles = json.loads((W / 'profiles.json').read_text())
tags = {r['tag'] for r in obs['rows']} | {s['tag'] for s in obs['seeds']} | {p['tag'] for p in profiles}
paths = {D / name for name in names} | {D / 'profiles-driver.log'}
for tag in sorted(tags):
    raw = R / 'raw' / ('lavik-' + tag)
    assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
    for path in raw.rglob('*'):
        if not path.is_file() or path.suffix not in ('.json', '.txt', '.log', '.prom'):
            continue
        if path.name.startswith('stacks-') and path.stat().st_size:
            continue
        paths.add(path)
    driver = W / (tag + '.log')
    assert driver.exists(), driver
    shutil.copyfile(driver, D / driver.name)
    paths.add(D / driver.name)

entries = [{'path': str(p.relative_to(R)), 'bytes': p.stat().st_size,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths)]
index = D / 'performance-evidence-index.json'
index.write_text(json.dumps({'scope': 'All 144 clean observations, six read seeds and four separate profiles; no raw perf binaries or nonempty full stacks.',
                            'files': entries}, indent=2) + '\n')
paths.add(index)
(W / 'controls-publish-paths.json').write_text(json.dumps([str(p.relative_to(REPO)) for p in sorted(paths)], indent=2) + '\n')
print('Prepared', len(paths), 'paths; review conclusions before explicit publication.')
