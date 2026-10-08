"""Analyze only after all clean and profile windows and host cleanup finish."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import time

W = Path(__file__).parent
pid = int((W / 'after-native.pid').read_text())
while True:
    try:
        state = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
    except FileNotFoundError:
        break
    if state == 'Z':
        break
    time.sleep(10)
assert 'ALL_PR289_MEASUREMENTS_COMPLETE' in (W / 'benchmark.log').read_text()
subprocess.run(['python3', str(W / 'profile-small-list.py')], check=True)
sys.path.insert(0, '/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
lock = acquire_host('pr289-post-measurement-analysis')
python = '/mnt/dev/lavik-complex-bench/perf_reports/lavik-complex-structures-2026-09-26/.venv/bin/python'
captures = []
for row in json.loads((W / 'profiles.json').read_text()):
    for p in sorted(Path(row['perf']).rglob('*')):
        if p.is_file():
            with p.open('rb') as f:
                digest = hashlib.file_digest(f, 'sha256').hexdigest()
            captures.append({'path': str(p), 'bytes': p.stat().st_size, 'sha256': digest})
(W / 'perf-capture-index.json').write_text(json.dumps(captures, indent=2) + '\n')
for name in ['analyze.py', 'summarize-perf.py', 'plot.py', 'write-report.py']:
    print('START_ANALYSIS', name, time.time(), flush=True)
    subprocess.run([python, str(W / name)], check=True)
    print('PASS_ANALYSIS', name, time.time(), flush=True)
print('ALL_PR289_ANALYSIS_COMPLETE', time.time(), flush=True)
