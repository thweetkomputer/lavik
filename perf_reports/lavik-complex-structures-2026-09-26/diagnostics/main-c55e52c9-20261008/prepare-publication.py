"""Copy an explicit evidence allowlist into the clean fork-report worktree."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import subprocess

W = Path(__file__).parent
REPO = Path('/mnt/dev/lavik-complex-refresh-20261004')
R = REPO / 'perf_reports/lavik-complex-structures-2026-09-26'
P = Path('/mnt/dev/lavik-report-c55e52c9-20261008')
D = R / 'diagnostics/main-c55e52c9-20261008'
assert 'ALL_MAIN_REPORT_ANALYSIS_COMPLETE' in (W / 'analysis-driver.log').read_text()
assert subprocess.check_output(['git', '-C', str(P), 'diff', 'HEAD', '--']) == b''
read = lambda p: json.loads(p.read_text())
m, imports, mixed = [read(R / name) for name in ['current-main.json', 'current-imports.json', 'current-mixed-writes.json']]
assert m['target_main'] == imports['target_main'] == mixed['target_main'] == 'c55e52c98d785dec9603d33ddcf55eab299eb11e'
for p in W.iterdir():
    if p.is_file() and p.suffix in ['.py', '.json', '.txt', '.log', '.cpp', '.c'] and p.name not in ['main-publish-paths.json', 'task-state.json', 'publication.json']:
        shutil.copy2(p, D / p.name)

paths = {p for p in D.rglob('*') if p.is_file()}
paths.update(R / name for name in [
    'README.md', 'README.zh-CN.md', 'current-main.json', 'current-imports.json', 'current-mixed-writes.json',
    'published-main.json', 'ordered-published.json', 'lset-large-published.json',
    'plot_current_main.py', 'plot_mixed_writes.py', 'plot_fill_reference.py', 'plot_set_hash_high_keys.py',
    'run.py', 'run_with_memory_guard.py', 'seed_batched_import.py', 'spdk_host.py', 'kvrocks_host.py', 'kvrocks-perf.conf'])
raw_dirs = set()
ops = {'hash': ['hget', 'hset', 'hgetall'], 'set': ['sismember', 'sadd_srem', 'smembers'],
       'list': ['lindex', 'lset', 'lrange'], 'stream': ['xrange', 'xadd_maxlen', 'xrange_full'],
       'zset': ['zscore', 'zincrby', 'zrange']}
for c in m['plots']:
    raw_dirs.add(R / 'raw' / ('lavik-' + c['main']['tag']))
    if 'seed_tag' in c['main']:
        raw_dirs.add(R / 'raw' / ('lavik-' + c['main']['seed_tag']))
    stem = f"{c['kind']}-{c['size']}-{c['field']}-k{c['keys']}"
    paths.add(R / (stem + '-current.csv'))
    for op in ['lset'] if c['category'] == 'lset' else ops[c['kind']]:
        paths.add(R / 'charts' / (stem + '-' + op + '-current.png'))
    if c['category'] == 'lset':
        paths.update([R / (stem + '-rpush-fill-current.csv'), R / 'charts' / (stem + '-rpush-fill-current.png')])
for c in imports['plots']:
    raw_dirs.add(R / 'raw' / ('lavik-' + c['main']['tag']))
    stem = f"{c['kind']}-{c['size']}-{c['field']}-k{c['keys']}-fill"
    paths.update([R / (stem + '.csv'), R / 'charts' / (stem + '.png')])
for chart in mixed['charts']:
    paths.update([R / chart['csv'], R / chart['chart']])
for point in mixed['points'] + mixed.get('excluded_points', []):
    raw_dirs.add(R / point['raw'])
for smoke in read(W / 'mixed-smoke-results.json'):
    raw_dirs.add(Path(smoke['raw']))
for raw in raw_dirs:
    assert raw.is_relative_to(R / 'raw')
    assert read(raw / 'server-exit.json')['code'] == 0
    paths.update(p for p in raw.rglob('*') if p.is_file() and p.suffix in ['.json', '.txt', '.log', '.conf'])

# Mutable host state, binaries, device contents and raw perf captures are not
# publication inputs. This allowlist also preserves unrelated working changes.
for p in paths:
    assert p.is_relative_to(R) and p.is_file()
    assert p.stat().st_size < 95 * 1024**2, p
    assert p.name not in ['spdk-host-original.json', 'spdk-host-commands.jsonl', 'spdk-restored.json',
                          'kvrocks-host-commands.jsonl', 'kvrocks-raid-restored.json']
index = D / 'main-evidence-index.json'
paths.discard(index)
index.write_text(json.dumps({
    'main': m['target_main'], 'scope': '28 legacy grids (278 selected points), four imports, 160 selected four-system mixed-write attempts (workload-bound violations retained as gaps); earlier 5120-connection observations are archived without plotting, and 20 excluded smoke checks. 96 generated charts, 94 shown per README.',
    'files': [{'path': str(p.relative_to(R)), 'bytes': p.stat().st_size,
               'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths)]
}, indent=2) + '\n')
paths.add(index)
relative = []
for source in sorted(paths):
    dest = P / source.relative_to(REPO)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    assert hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(dest.read_bytes()).digest()
    relative.append(str(source.relative_to(REPO)))
(W / 'main-publish-paths.json').write_text(json.dumps(relative, indent=2) + '\n')
print('REVIEWABLE_PUBLICATION_PREPARED', len(relative), 'files', sum(p.stat().st_size for p in paths), 'bytes')
