"""Copy the PR evidence only; leave the published main curves unchanged."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import subprocess

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
P = Path('/mnt/dev/lavik-report-c55e52c9-20261008')
REL = Path('perf_reports/lavik-complex-structures-2026-09-26')
ROOT = P / REL
D = ROOT / 'diagnostics/pr289-c8f128dc-20261008'
assert 'ALL_PR289_ANALYSIS_COMPLETE' in (W / 'analysis.log').read_text()
assert not subprocess.check_output(['git', '-C', str(P), 'status', '--porcelain'])
paths = set()
def copy(src, dest):
    assert src.is_file() and src.stat().st_size < 95 * 1024**2
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    assert hashlib.sha256(src.read_bytes()).digest() == hashlib.sha256(dest.read_bytes()).digest()
    paths.add(dest)

for src in W.iterdir():
    if src.is_file() and src.suffix in ['.md', '.py', '.json', '.jsonl', '.log', '.txt', '.cpp', '.c', '.patch', '.csv', '.png'] and src.name not in ['task-state.json', 'publication.json', 'publish-paths.json']:
        copy(src, D / src.name)
copy(Path('/mnt/dev/lavik-main-c55e52c9-20261008/refresh-main-CMakeCache.txt'), D / 'main-CMakeCache.txt')
rows = json.loads((W / 'repeats.json').read_text())['rows'] + json.loads((W / 'profiles.json').read_text())
for row in rows:
    raw = Path(row['raw'])
    assert raw.is_relative_to(R / 'raw')
    for src in raw.rglob('*'):
        if not src.is_file() or src.suffix not in ['.json', '.txt', '.log']:
            continue
        in_perf = any(p.name.endswith('.perf') for p in src.parents if p != raw)
        if in_perf and src.name.startswith(('stacks-', 'physical-')):
            continue
        copy(src, ROOT / src.relative_to(R))

# Add a narrowly scoped diagnostic link; the main baseline and peer selection
# remain the measured revisions already published in the previous commit.
m = json.loads((ROOT / 'current-main.json').read_text())
link = 'diagnostics/pr289-c8f128dc-20261008/README.md'
assert link not in m['notes']['zh'] and link not in m['notes']['en']
m['notes']['zh'] += f' · [#289：ZRANK 与 List push/pop 三轮对照]({link})（独立 PR 测试，不替换 main 曲线）。'
m['notes']['en'] += f' · [#289: three paired rank and List push/pop runs]({link}) (separate PR comparison; current main curves retained).'
(ROOT / 'current-main.json').write_text(json.dumps(m, indent=2) + '\n')
paths.add(ROOT / 'current-main.json')
spec = importlib.util.spec_from_file_location('plot', ROOT / 'plot_current_main.py')
plot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plot)
for zh, name in [(True, 'README.zh-CN.md'), (False, 'README.md')]:
    (ROOT / name).write_text(plot.readme(m, zh))
    paths.add(ROOT / name)
index = D / 'evidence-index.json'
index.write_text(json.dumps({'scope': 'PR289 c8f128dc versus main c55e52c9; 48 clean observations and eight independent perf observations.',
    'files': [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size,
               'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths)]}, indent=2) + '\n')
paths.add(index)
(W / 'publish-paths.json').write_text(json.dumps([str(p.relative_to(P)) for p in sorted(paths)], indent=2) + '\n')
print('PR289_PUBLICATION_PREPARED', len(paths), 'files', sum(p.stat().st_size for p in paths), 'bytes')
