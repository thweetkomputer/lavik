"""Retain every legacy-grid success/failure and audit successful command counts."""
from pathlib import Path
import json
import shutil
import subprocess
import sys

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
D = R / 'diagnostics/main-c55e52c9-20261008'
assert 'ALL_MAIN_GRIDS_AND_IMPORTS_COMPLETE' in (W / 'main-refresh-driver.log').read_text()
manifest = json.loads((R / 'current-main.json').read_text())
rows, failures = [], []
for condition in manifest['plots']:
    tag = condition['main']['tag']
    raw = R / 'raw' / ('lavik-' + tag)
    for suffix, target in [('result', rows), ('error', failures)]:
        for p in raw.glob('*.' + suffix + '.json'):
            item = json.loads(p.read_text())
            if item['connections'] != 5120:
                target.append({'tag': tag, **item})
assert len(rows) + len(failures) == 278
(D / 'main-observations.json').write_text(json.dumps({'rows': rows, 'failures': failures,
    'scope': 'Every selected legacy-grid observation. User excluded 5120; earlier measurements remain in raw. Failures remain explicit and are not plotted as zero QPS.'}, indent=2) + '\n')
subprocess.run([sys.executable, str(W / 'audit-commands.py'), '--input', str(D / 'main-observations.json'),
                '--output', str(D / 'main-command-audit.json'), '--report-root', str(R)], check=True)
print('BASELINE_COMMAND_AUDIT_COMPLETE', len(rows), 'successful', len(failures), 'failed')
