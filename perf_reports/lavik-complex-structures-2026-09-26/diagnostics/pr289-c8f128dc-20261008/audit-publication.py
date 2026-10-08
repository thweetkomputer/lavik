"""Verify the exact reviewed evidence bytes and links before publication."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
from urllib.parse import unquote

W = Path(__file__).parent
P = Path('/mnt/dev/lavik-report-c55e52c9-20261008')
R = P / 'perf_reports/lavik-complex-structures-2026-09-26'
D = R / 'diagnostics/pr289-c8f128dc-20261008'
paths = json.loads((W / 'publish-paths.json').read_text())
index = json.loads((D / 'evidence-index.json').read_text())
assert len(paths) == len(index['files']) + 1
for row in index['files']:
    p = R / row['path']
    assert p.stat().st_size == row['bytes']
    assert hashlib.sha256(p.read_bytes()).hexdigest() == row['sha256']
links = 0
for p in [R / 'README.md', R / 'README.zh-CN.md', D / 'README.md']:
    for target in re.findall(r'\]\(([^)]+)\)', p.read_text()):
        target = target.strip('<>').split('#', 1)[0]
        if not target or re.match(r'[a-zA-Z]+://', target):
            continue
        assert (p.parent / unquote(target)).resolve().exists(), (p, target)
        links += 1
changed = subprocess.check_output(['git', '-C', str(P), 'diff', 'HEAD', '--name-only', '-z']).decode().split('\0')
assert set(filter(None, changed)) <= set(paths)
baseline = subprocess.check_output(['git', '-C', str(P), 'show', 'HEAD:perf_reports/lavik-complex-structures-2026-09-26/current-main.json'])
a, b = json.loads(baseline), json.loads((R / 'current-main.json').read_text())
a.pop('notes'); b.pop('notes')
assert a == b, 'PR diagnostic publication changed main data selection'
print('PR289_PUBLICATION_AUDITED', len(paths), 'files', links, 'links; main data selection unchanged')
