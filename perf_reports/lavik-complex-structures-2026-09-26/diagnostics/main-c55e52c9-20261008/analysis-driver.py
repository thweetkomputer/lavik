"""Run report generation only after the full serialized benchmark completes."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
PYTHON = '/mnt/dev/lavik-complex-bench/perf_reports/lavik-complex-structures-2026-09-26/.venv/bin/python'
# The final in-process README render needs the same plotting environment as
# the child scripts, even when this supervisor is launched with system Python.
if Path(sys.prefix) != Path(PYTHON).parent.parent:
    os.execv(PYTHON, [PYTHON, str(Path(__file__).resolve()), *sys.argv[1:]])
pid = int((W / 'refresh.pid').read_text())
while True:
    try:
        state = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
    except FileNotFoundError:
        break
    if state == 'Z':
        break
    time.sleep(10)
assert 'ALL_MAIN_GRIDS_AND_IMPORTS_COMPLETE' in (W / 'main-refresh-driver.log').read_text()
assert 'ALL_FOUR_SYSTEM_MIXED_WRITES_COMPLETE' in (W / 'mixed-driver.log').read_text()
sys.path.insert(0, '/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
lock = acquire_host('main-c55e52c9-report-analysis')
for script, args in [
    (W / 'collect-mixed.py', []),
    (W / 'render-main-refresh.py', []),
    (R / 'plot_mixed_writes.py', []),
    (W / 'build-main-gap-summary.py', [str(R)]),
    (W / 'collect-baseline.py', []),
    (W / 'write-report.py', []),
    (W / 'audit-current.py', [str(R)]),
    (W / 'audit-mixed.py', []),
]:
    print('START_ANALYSIS', script.name, time.time(), flush=True)
    subprocess.run([PYTHON, str(script), *args], check=True)
    print('PASS_ANALYSIS', script.name, time.time(), flush=True)

# Add the now-existing audit link without rerunning chart generation.
spec = importlib.util.spec_from_file_location('plot', R / 'plot_current_main.py')
plot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plot)
manifest = json.loads((R / 'current-main.json').read_text())
for zh, name in [(True, 'README.zh-CN.md'), (False, 'README.md')]:
    (R / name).write_text(plot.readme(manifest, zh))
v = json.loads((W / 'versions.json').read_text())['main']
with Path(v['binary']).open('rb') as f:
    assert hashlib.file_digest(f, 'sha256').hexdigest() == v['sha256']
assert subprocess.check_output(['git', '-C', v['source_repo'], 'rev-parse', 'HEAD'], text=True).strip() == v['commit']
assert subprocess.check_output(['git', '-C', v['source_repo'], 'diff', 'HEAD', '--']) == b''
code = 'import sys;sys.path.insert(0,' + repr(str(R)) + ');import spdk_host;spdk_host.no_servers();spdk_host.assert_driver("nvme");print(spdk_host.checked_kernel_devices())'
restored = subprocess.check_output(['sudo', '-n', 'python3', '-c', code], text=True)
assert not (R / 'spdk-ready.json').exists() and not (R / 'kvrocks-raid-ready.json').exists()
(W / 'final-audit.json').write_text(json.dumps({
    'main': v['commit'], 'binary_sha256_verified': True, 'source_cache_clean': True,
    'legacy_points': 278, 'imports': 4, 'mixed_points': 160, 'mixed_measured_points': 200, 'new_charts': 10,
    'mixed_guard_failures': len(json.loads((R / 'current-mixed-writes.json').read_text())['guard_failures']),
    'host_restored': restored,
    'original_repo_status': subprocess.check_output(['git', '-C', '/mnt/dev/lavik', 'status', '--short', '--untracked-files=no'], text=True),
    'hugepages': Path('/proc/sys/vm/nr_hugepages').read_text().strip(),
    'unsafe_noiommu': Path('/sys/module/vfio/parameters/enable_unsafe_noiommu_mode').read_text().strip()
}, indent=2) + '\n')
print('ALL_MAIN_REPORT_ANALYSIS_COMPLETE', time.time(), flush=True)
