from pathlib import Path
from datetime import datetime, timezone
import json

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
print(datetime.now(timezone.utc).isoformat())
for pid_name, log_name in [('native', 'native-driver'), ('refresh', 'main-refresh-driver'), ('analysis', 'analysis-driver')]:
    file = W / (pid_name + '.pid')
    if not file.exists():
        continue
    pid = int(file.read_text())
    try:
        state = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
    except FileNotFoundError:
        state = 'gone'
    log = W / (log_name + '.log')
    print(pid_name, pid, state, ' | '.join(log.read_text().splitlines()[-2:]) if log.exists() else '')
for name in ['mixed-smoke-results.json', 'mixed-results.json', 'main-refresh-progress.json']:
    p = W / name
    if p.exists():
        value = json.loads(p.read_text())
        print(name, len(value))
        if name == 'mixed-results.json':
            for item in value[-2:]:
                r = item['result']
                print(item['system'], r['operation'], r['logical_bytes'], r['connections'], round(r['qps']) if r['qps'] is not None else 'GUARD_GAP', r['p99_ms'])
log = W / 'mixed-driver.log'
if log.exists():
    print('mixed log:', ' | '.join(log.read_text().splitlines()[-3:]))
