"""Validate the isolated publication without staging unrelated runtime files."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
from urllib.parse import unquote

W = Path(__file__).parent
P = Path('/mnt/dev/lavik-report-c55e52c9-20261008')
R = P / 'perf_reports/lavik-complex-structures-2026-09-26'
D = R / 'diagnostics/main-c55e52c9-20261008'
paths = json.loads((W / 'main-publish-paths.json').read_text())
index = json.loads((D / 'main-evidence-index.json').read_text())
assert len(paths) == len(index['files']) + 1
for item in index['files']:
    p = R / item['path']
    assert p.stat().st_size == item['bytes'], p
    assert hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256'], p

# Validate authored report links after all diagnostics have been copied. The
# copied reproduction scripts retain their original host paths intentionally.
linked = 0
for p in [R / 'README.md', R / 'README.zh-CN.md', *D.glob('*.md')]:
    for target in re.findall(r'\]\(([^)]+)\)', p.read_text()):
        target = target.strip('<>').split('#', 1)[0]
        if not target or re.match(r'[a-zA-Z]+://', target):
            continue
        dest = (p.parent / unquote(target)).resolve()
        assert dest.exists(), (p, target)
        linked += 1

tracked_changes = subprocess.check_output(
    ['git', '-C', str(P), 'diff', '--name-only', 'HEAD', '-z']).decode().split('\0')
assert set(filter(None, tracked_changes)) <= set(paths)
authored = [p for p in paths if p.endswith(('.md', '.py', '.cpp', '.c'))]
subprocess.run(['git', '-C', str(P), 'diff', '--check', '--', *authored], check=True)
print('PUBLICATION_BYTES_AND_LINKS_VERIFIED', len(paths), 'files', linked, 'links')
