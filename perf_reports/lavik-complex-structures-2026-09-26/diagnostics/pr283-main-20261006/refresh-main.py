"""Serialize existing #283 perf and a complete pinned-main report refresh."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, '/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
launch = json.loads((W / 'controls-launch.json').read_text())
proc = Path('/proc') / str(launch['pid']) / 'stat'
print('WAIT_FOR_CLEAN_CONTROLS', launch, flush=True)
while proc.exists():
    try:
        if proc.read_text().split()[21] != launch['start_ticks']:
            break
    except FileNotFoundError:
        break
    time.sleep(15)
assert 'ALL_PR283_REPEATS_COMPLETE' in (W / 'controls-driver.log').read_text()
repeats = json.loads((W / 'pr283-repeats.json').read_text())
assert len(repeats['rows']) == 144 and not any('error' in r for r in repeats['rows'])
V = repeats['versions']
assert V['parent']['commit'] == '5a3903d9b3c0632e3b34e827b779d9daa58455c2'
assert V['candidate']['commit'] == 'ace4198b0e1080cbb5116d40817b4dcc38f7ff8c'
lock = acquire_host('pr283-perf-and-main-refresh')
for v in V.values():
    with Path(v['binary']).open('rb') as f:
        assert hashlib.file_digest(f, 'sha256').hexdigest() == v['sha256']


def execute(argv, name):
    print('START', name, time.time(), flush=True)
    with (W / (name + '.log')).open('w') as log:
        subprocess.run(argv, cwd=R.parents[1], stdout=log,
                       stderr=subprocess.STDOUT, check=True)
    print('COMPLETE', name, time.time(), flush=True)


profiles = []
for size, field, keys in [(104857600, 1024, 8), (65536, 128, 64)]:
    for label in ('parent', 'candidate'):
        v = V[label]
        tag = f'diagnostic-{label}{v["commit"][:8]}-pr283-zincrby-{size}-{field}-c80-20261006'
        raw = R / 'raw' / ('lavik-' + tag)
        assert not raw.exists(), raw
        subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'prepare'], check=True)
        try:
            execute(['sudo', '-n', 'env', 'LAVIK_BENCH_ROOT=' + str(R),
                     'LAVIK_PROFILE_ZSET_OPERATION=ZINCRBY', 'python3',
                     str(R / 'run_with_memory_guard.py'), '--minimum-available-gib=20', '--',
                     'python3', str(W / 'profile-ordered-allworkers.py'), 'lavik',
                     '--binary=' + v['binary'], '--source-repo=' + v['source_repo'],
                     '--source-commit=' + v['commit'], '--types=zset', '--sizes=' + str(size),
                     '--fields=' + str(field), '--keys=' + str(keys), '--tag=' + tag,
                     '--mode=point', '--levels=80', '--seconds=30'], tag)
        finally:
            subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'restore'], check=True)
        subprocess.run(['sudo', '-n', 'chown', '-R', f'{os.getuid()}:{os.getgid()}', str(raw)], check=True)
        assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
        assert json.loads((raw / 'complete.json').read_text())['failures_total'] == 0
        proof = json.loads(next(raw.glob('provenance-*.json')).read_text())
        assert proof['source_commit'] == v['commit'] and proof['sha256'] == v['sha256']
        profile = json.loads((raw / 'diagnostic-c80/profile-provenance.json').read_text())
        assert profile['operation'] == 'ZINCRBY' and len(profile['argv_by_tid']) >= 12
        profiles.append({'version': label, 'tag': tag, 'profile': profile})
        (W / 'profiles.json').write_text(json.dumps(profiles, indent=2) + '\n')
print('ALL_PR283_PROFILES_COMPLETE', time.time(), flush=True)

# Main is the exact parent used in the paired comparison. Save a separate
# selection; never relabel old observations or candidates as refreshed main.
(W / 'versions.json').write_text(json.dumps({'main': V['parent']}, indent=2) + '\n')
manifest = json.loads((R / 'current-main.json').read_text())
imports = json.loads((R / 'current-imports.json').read_text())
(W / 'previous-current-main.json').write_text(json.dumps(manifest, indent=2) + '\n')
(W / 'previous-current-imports.json').write_text(json.dumps(imports, indent=2) + '\n')
rows = sorted(manifest['plots'], key=lambda r: (r['category'] != 'ordered', r['size'], r['kind'], r['field']))
completed = []
for row in rows:
    args = [str(row[k]) for k in ('kind', 'size', 'field', 'keys', 'category')]
    name = 'main-grid-' + '-'.join(args)
    execute(['python3', str(W / 'run-condition.py'), *args], name)
    completed.append({'kind': row['kind'], 'size': row['size'], 'field': row['field'],
                      'keys': row['keys'], 'category': row['category']})
    (W / 'main-refresh-progress.json').write_text(json.dumps(completed, indent=2) + '\n')
for row in imports['plots']:
    execute(['python3', str(W / 'run-import.py'), row['kind'], str(row['field'])],
            f'main-import-{row["kind"]}-{row["field"]}')
assert len(completed) == 28
print('ALL_MAIN_GRIDS_AND_IMPORTS_COMPLETE', time.time(), flush=True)
