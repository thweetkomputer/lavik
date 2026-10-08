"""Build and check the shared benchmark client after native validation."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

W = Path(__file__).parent
sys.path.insert(0, '/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
lock = acquire_host('pr289-client-validation')
assert 'ALL_PR289_NATIVE_TESTS_PASS' in (W / 'native-driver.log').read_text()
subprocess.run(['g++', '-std=c++20', '-O2', '-pthread', str(W / 'random-client.cpp'),
                '-o', str(W / 'random-client')], check=True)
subprocess.run(['python3', str(W / 'random-client-smoke.py')], check=True)
subprocess.run(['scp', str(W / 'random-client'), '172.16.0.5:/mnt/dev/random-client-pr289-20261008'], check=True)
remote = subprocess.check_output(['ssh', '-o', 'BatchMode=yes', '172.16.0.5',
                                  'sha256sum /mnt/dev/random-client-pr289-20261008'], text=True).split()[0]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert remote == sha(W / 'random-client')
(W / 'client-provenance.json').write_text(json.dumps({
    'source_sha256': sha(W / 'random-client.cpp'), 'binary_sha256': remote,
    'remote_sha256': remote, 'smoke_points': 4,
    'rank_distribution': 'Uniform draw among eight evenly spaced seeded ranks, including endpoints; exact forward/reverse integer replies checked.'
}, indent=2) + '\n')
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
paths = [W / n for n in ['random-client.cpp', 'random-client', 'run-random.py',
          'fixed-seed-exec.py', 'fixed-digest-seed.c', 'fixed-digest-seed.so',
          'private-tmp-exec.py', 'host.py', 'process_helpers.py', 'profile_capture.py', 'benchmark.py']]
paths += [R / n for n in ['run.py', 'run_with_memory_guard.py', 'spdk_host.py']]
(W / 'harness-provenance.json').write_text(json.dumps({str(p): sha(p) for p in paths}, indent=2) + '\n')
print('ALL_PR289_CLIENT_CHECKS_PASS', flush=True)
