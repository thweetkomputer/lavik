"""Serialize native validation, new four-system writes, and legacy main grids."""
from pathlib import Path
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
sys.path.insert(0, '/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
from process_helpers import execute

def interrupted(_signal, _frame):
    raise SystemExit('report refresh interrupted')

signal.signal(signal.SIGTERM, interrupted)

def run(argv, name):
    print('START', name, time.time(), flush=True)
    with (W / (name + '.log')).open('w') as log:
        execute(argv, log)
    print('COMPLETE', name, time.time(), flush=True)

pid = int((W / 'native.pid').read_text())
while True:
    try:
        state = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
    except FileNotFoundError:
        break
    if state == 'Z':
        break
    time.sleep(5)
assert 'ALL_MAIN_NATIVE_TESTS_PASS' in (W / 'native-driver.log').read_text()
if '--resume-legacy' in sys.argv:
    assert (W / 'mixed-cleanup-retry.json').exists()
    assert len(json.loads((W / 'mixed-results.json').read_text())) == 200
    print('RETAIN_COMPLETE_MIXED_MEASUREMENTS_AND_VERIFIED_CLEANUP', time.time(), flush=True)
else:
    run(['python3', str(W / 'run-mixed-suite.py'), *(['--resume'] if (W / 'mixed-smoke-results.json').exists() else [])], 'mixed-driver')
assert 'ALL_FOUR_SYSTEM_MIXED_WRITES_COMPLETE' in (W / 'mixed-driver.log').read_text()

lock = acquire_host('main-c55e52c9-complete-legacy-report-refresh')
v = json.loads((W / 'versions.json').read_text())['main']
assert v['commit'] == 'c55e52c98d785dec9603d33ddcf55eab299eb11e'
with Path(v['binary']).open('rb') as f:
    assert hashlib.file_digest(f, 'sha256').hexdigest() == v['sha256']
manifest = json.loads((W / 'previous-current-main.json').read_text())
imports = json.loads((W / 'previous-current-imports.json').read_text())
rows = sorted(manifest['plots'], key=lambda r: (r['category'] != 'ordered', r['size'], r['kind'], r['field']))
completed = []
for row in rows:
    args = [str(row[k]) for k in ('kind', 'size', 'field', 'keys', 'category')]
    run(['python3', str(W / 'run-condition.py'), *args], 'main-grid-' + '-'.join(args))
    completed.append({k: row[k] for k in ('kind', 'size', 'field', 'keys', 'category')})
    (W / 'main-refresh-progress.json').write_text(json.dumps(completed, indent=2) + '\n')
for row in imports['plots']:
    run(['python3', str(W / 'run-import.py'), row['kind'], str(row['field'])],
        f'main-import-{row["kind"]}-{row["field"]}')
assert len(completed) == 28
sys.path.insert(0, str(R))
import spdk_host
assert not (R / 'spdk-ready.json').exists()
assert not (R / 'kvrocks-raid-ready.json').exists()
spdk_host.no_servers()
spdk_host.assert_driver('nvme')
(W / 'host-final.json').write_text(json.dumps({
    'no_servers': True, 'scratch_drivers': 'nvme', 'spdk_ready_absent': True,
    'kvrocks_raid_ready_absent': True,
    'hugepages': Path('/proc/sys/vm/nr_hugepages').read_text().strip(),
    'unsafe_noiommu': Path('/sys/module/vfio/parameters/enable_unsafe_noiommu_mode').read_text().strip()
}, indent=2) + '\n')
print('ALL_MAIN_GRIDS_AND_IMPORTS_COMPLETE', time.time(), flush=True)
