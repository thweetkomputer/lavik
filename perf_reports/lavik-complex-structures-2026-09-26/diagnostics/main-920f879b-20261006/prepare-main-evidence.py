"""Validate and collect the reviewed main report without publishing it."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys

W = Path(__file__).parent
REPO = Path('/mnt/dev/lavik-complex-refresh-20261004')
R = REPO / 'perf_reports/lavik-complex-structures-2026-09-26'
D = R / 'diagnostics/main-920f879b-20261006'
assert 'ALL_MAIN_GRIDS_AND_IMPORTS_COMPLETE' in (W / 'main-refresh-driver.log').read_text()
manifest = json.loads((R / 'current-main.json').read_text())
imports = json.loads((R / 'current-imports.json').read_text())
assert manifest['target_main'] == imports['target_main'] == '920f879b05636d066ef0485f1ee1121813ef79ac'
assert len(manifest['plots']) == 28 and len(imports['plots']) == 4
assert (D / 'README.md').exists(), 'Write the reviewed measurement summary first'
plot_audit = json.loads((D / 'report-audit.json').read_text())
assert plot_audit['target_main'] == manifest['target_main'] and plot_audit['fresh_conditions'] == 28
for name in ('README.md', 'README.zh-CN.md'):
    assert '920f879b' in (R / name).read_text()
    assert len(re.findall(r'!\[[^]]*\]\(([^)]+)\)', (R / name).read_text())) == 84

rows, failures, tags = [], [], set()
for condition in manifest['plots']:
    version = condition['main']
    assert version['fresh'] and version['commit'] == manifest['target_main']
    tag = version['tag']
    tags.add(tag)
    if 'seed_tag' in version:
        tags.add(version['seed_tag'])
    raw = R / 'raw' / ('lavik-' + tag)
    for suffix, destination in (('result', rows), ('error', failures)):
        for path in raw.glob('*.' + suffix + '.json'):
            value = json.loads(path.read_text())
            destination.append({'tag': tag, **value})
assert len(rows) + len(failures) == 332
(D / 'main-observations.json').write_text(json.dumps({'rows': rows, 'failures': failures,
    'scope': 'Successful points audited against command counts; failed points remain separate, with no invented QPS.'}, indent=2) + '\n')
for name in ('audit-commands.py', 'audit-current.py', 'build-main-gap-summary.py',
             'prepare-main-evidence.py'):
    shutil.copyfile(W / name, D / name)
subprocess.run([sys.executable, str(D / 'audit-commands.py'), '--input', str(D / 'main-observations.json'),
                '--output', str(D / 'main-command-audit.json'), '--report-root', str(R)], check=True)

for condition in imports['plots']:
    tag = condition['main']['tag']
    tags.add(tag)
    raw = R / 'raw' / ('lavik-' + tag)
    fill = json.loads((raw / f'{condition["kind"]}-{condition["size"]}-{condition["field"]}.fill.json').read_text())
    assert fill['client_encoding'] == 'per-command'
    assert json.loads((raw / 'seed-client-proof.json').read_text())['client_encoding'] == 'per-command'

paths = {p for p in D.rglob('*') if p.is_file()}
for tag in tags:
    raw = R / 'raw' / ('lavik-' + tag)
    assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
    paths.update(p for p in raw.rglob('*') if p.is_file() and p.suffix in ('.json', '.txt', '.log'))
paths.update(R / n for n in ('README.md', 'README.zh-CN.md', 'current-main.json', 'current-imports.json',
                             'published-main.json', 'ordered-published.json', 'lset-large-published.json',
                             'plot_current_main.py', 'plot_fill_reference.py', 'run.py',
                             'seed_batched_import.py', 'run_with_memory_guard.py', 'spdk_host.py'))
ops = {'hash': ['hget', 'hset', 'hgetall'], 'set': ['sismember', 'sadd_srem', 'smembers'],
       'list': ['lindex', 'lset', 'lrange'], 'stream': ['xrange', 'xadd_maxlen', 'xrange_full'],
       'zset': ['zscore', 'zincrby', 'zrange']}
for c in manifest['plots']:
    key = f'{c["kind"]}-{c["size"]}-{c["field"]}-k{c["keys"]}'
    paths.add(R / (key + '-current.csv'))
    for op in (['lset'] if c['category'] == 'lset' else ops[c['kind']]):
        paths.add(R / 'charts' / (key + '-' + op + '-current.png'))
    if c['category'] == 'lset':
        paths.add(R / 'charts' / (key + '-rpush-fill-current.png'))
        paths.add(R / (key + '-rpush-fill-current.csv'))
for c in imports['plots']:
    key = f'{c["kind"]}-{c["size"]}-{c["field"]}-k{c["keys"]}-fill'
    paths.update((R / (key + '.csv'), R / 'charts' / (key + '.png')))
index = D / 'main-evidence-index.json'
paths.discard(index)
entries = [{'path': str(p.relative_to(R)), 'bytes': p.stat().st_size,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths)]
index.write_text(json.dumps({'scope': 'Pinned main, all 28 throughput conditions and four batched imports; historical peers retained. Includes all 86 generated charts, of which 84 are displayed in each README.',
                            'files': entries}, indent=2) + '\n')
paths.add(index)
(W / 'main-publish-paths.json').write_text(json.dumps([str(p.relative_to(REPO)) for p in sorted(paths)], indent=2) + '\n')
print('Prepared', len(paths), 'main evidence paths;', len(rows), 'successful and', len(failures), 'failed observations.')
