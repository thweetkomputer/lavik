"""Finish the existing RAID cleanup after all 200 measurements were recorded."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import time

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
sys.path.insert(0, '/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
lock = acquire_host('main-c55e52c9-finish-mixed-raid-cleanup')
rows = json.loads((W / 'mixed-results.json').read_text())
assert len(rows) == 200
assert all(json.loads((Path(x['raw']) / 'server-exit.json').read_text())['code'] == 0 for x in rows)
assert all(x['result']['command_audit']['passed'] for x in rows)
assert len({(x['system'], x['result']['logical_bytes'], x['result']['operation'], x['result']['connections']) for x in rows}) == 200
assert 'COMPLETE kvrocks ZADD_TAIL_ZPOPMIN 104857600 5120 POINTS 200' in (W / 'mixed-driver.log').read_text()
assert 'AssertionError: /dev/nvme5n1' in (W / 'mixed-driver.log').read_text()
for name, sha in json.loads((W / 'mixed-harness-provenance.json').read_text()).items():
    assert hashlib.sha256((W / name).read_bytes()).hexdigest() == sha
subprocess.run(['sudo', '-n', 'python3', str(R / 'kvrocks_host.py'), 'restore'], check=True)
assert not (R / 'kvrocks-raid-ready.json').exists()
assert not (R / 'spdk-ready.json').exists()
code = 'import sys;sys.path.insert(0,' + repr(str(R)) + ');import spdk_host;spdk_host.no_servers();spdk_host.assert_driver("nvme");print(spdk_host.checked_kernel_devices())'
snapshots = []
for _ in range(2):
    snapshots.append(subprocess.check_output(['sudo', '-n', 'python3', '-c', code], text=True))
    time.sleep(2)
record = {'time': time.time(), 'measurements': 200,
          'guard_gaps': sum('failure' in x['result'] for x in rows),
          'original_failure': 'Post-RAID teardown fuser check temporarily found /dev/nvme5n1 busy.',
          'action': 'Retried the existing idempotent restore with all original guards. No benchmark was rerun.',
          'verified_idle_snapshots': snapshots}
(W / 'mixed-cleanup-retry.json').write_text(json.dumps(record, indent=2) + '\n')
with (W / 'mixed-driver.log').open('a') as f:
    f.write(f'RAID_CLEANUP_RETRY_VERIFIED {record["time"]} mixed-cleanup-retry.json\n')
    f.write(f'ALL_FOUR_SYSTEM_MIXED_WRITES_COMPLETE {time.time()}\n')
print('ALL_FOUR_SYSTEM_MIXED_WRITES_COMPLETE_AFTER_VERIFIED_CLEANUP')
