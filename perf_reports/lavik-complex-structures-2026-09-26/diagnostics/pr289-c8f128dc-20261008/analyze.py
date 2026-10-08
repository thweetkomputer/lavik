"""Audit paired raw observations and summarize the pinned PR comparison."""
from pathlib import Path
import collections
import csv
import hashlib
import json
import re
import statistics
import sys

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
source = json.loads((W / 'repeats.json').read_text())
rows = source['rows']
groups = collections.defaultdict(dict)
for row in rows:
    k = row['kind'], row['size'], row['operation']
    assert (row['round'], row['version']) not in groups[k]
    groups[k][row['round'], row['version']] = row
summary = []
for (kind, size, op), g in sorted(groups.items()):
    pairs = []
    for n in range(1, 4):
        if (n, 'main') not in g or (n, 'pr289') not in g:
            continue
        a, b = g[n, 'main'], g[n, 'pr289']
        assert a['digest_seed'] == b['digest_seed'] and a['client_seed'] == b['client_seed']
        p = {'round': n}
        for metric in ['qps', 'p99_ms']:
            p['main_' + metric] = a['result'][metric]
            p['pr289_' + metric] = b['result'][metric]
            p[metric + '_ratio'] = b['result'][metric] / a['result'][metric]
            p[metric + '_change_pct'] = (p[metric + '_ratio'] - 1) * 100
        pairs.append(p)
    if not pairs:
        continue
    s = {'kind': kind, 'size': size, 'operation': op, 'connections': 320, 'pairs': pairs}
    for k in pairs[0]:
        if k != 'round':
            s[k] = statistics.median(p[k] for p in pairs)
    for metric in ['qps', 'p99_ms']:
        s[metric + '_change_range_pct'] = [min(p[metric + '_change_pct'] for p in pairs), max(p[metric + '_change_pct'] for p in pairs)]
    summary.append(s)
    print(size // 1048576, op, len(pairs), 'pairs', f"{s['main_qps']:.1f} -> {s['pr289_qps']:.1f} QPS ({s['qps_ratio']:.3f}x), p99 {s['p99_ms_change_pct']:+.2f}%", flush=True)
if '--partial' in sys.argv:
    sys.exit()
assert 'ALL_PR289_MEASUREMENTS_COMPLETE' in (W / 'benchmark.log').read_text()
assert len(rows) == 48 and len(summary) == 8 and all(len(s['pairs']) == 3 for s in summary)

def counters(path):
    out = {}
    for line in path.read_text().splitlines():
        if line.startswith('cmdstat_'):
            name, values = line.split(':', 1)
            out[name[8:]] = dict((k, float(v)) for k, v in (x.split('=', 1) for x in values.split(',')))
    return out

checks, cpus, deviations, fractions = [], [], [], []
for row in rows:
    d = Path(row['raw'])
    stem = f"{row['kind']}-{row['size']}-1024-{row['operation'].lower()}-c320"
    c = json.loads((d / (stem + '.client.json')).read_text())
    result = json.loads((d / (stem + '.result.json')).read_text())
    assert row['result'] == result
    assert c['errors'] == 0 and c['pipeline'] == 1 and c['connections'] == 320
    assert c['seconds'] == 30 and c['threads'] == 16 and c['seed'] == int(row['client_seed'])
    for metric in ['qps', 'p50_ms', 'p99_ms', 'p999_ms']:
        assert c['totals'][metric] == result[metric]
    assert c['totals']['count'] == result['requests'] == sum(x['count'] for x in c['commands'].values())
    a, b = [counters(d / (stem + '.info-' + side + '.txt')) for side in ['before', 'after']]
    delta = {}
    for name in a.keys() | b.keys():
        for field in ['failed_calls', 'rejected_calls']:
            assert b.get(name, {}).get(field, 0) - a.get(name, {}).get(field, 0) == 0
        calls = b.get(name, {}).get('calls', 0) - a.get(name, {}).get('calls', 0)
        assert calls >= 0
        if calls:
            delta[name] = calls
    assert set(delta) <= {x.lower() for x in c['commands']} | {'info'}
    assert all(delta[name.lower()] == stats['count'] for name, stats in c['commands'].items())
    before, after = [json.loads((d / (stem + f'.{side}-cardinality.json')).read_text())['sample_cardinalities'] for side in ['before', 'after']]
    n = row['size'] // 1024
    assert set(before) == set(after) == set(c['key_counts']) == {f'complex_{i}' for i in range(1, 9)}
    assert set(before.values()) == {n}
    assert all(after[k] == n + v['net'] and n // 2 <= after[k] <= n * 2 for k, v in c['key_counts'].items())
    if row['kind'] == 'list':
        fraction = next(iter(c['commands'].values()))['count'] / c['totals']['count']
        assert .48 <= fraction <= .52
        fractions.append(fraction)
        deviations.append(100 * max(abs(v - n) for v in after.values()) / n)
    else:
        assert set(after.values()) == {n}
    cpu = re.search(r'Percent of CPU this job got: (\d+)%', (d / (stem + '.client-errors.txt')).read_text())
    assert cpu
    cpus.append(int(cpu[1]))
    assert json.loads((d / 'server-exit.json').read_text())['code'] == 0
    assert json.loads((d / 'complete.json').read_text())['failures_total'] == 0
    proof = json.loads(next(d.glob('provenance-*.json')).read_text())
    v = source['versions'][row['version']]
    assert proof['sha256'] == v['sha256'] and proof['source_commit'] == v['commit']
    seed = json.loads((d / 'fixed-digest-seed.json').read_text())
    assert seed['verified_via_proc_mem'] and seed['seed_hex'] == row['digest_seed']
    checks.append({'tag': row['tag'], 'requests': result['requests'], 'verified': True})
for path, sha in json.loads((W / 'harness-provenance.json').read_text()).items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha, path
old_cache = Path('/mnt/dev/lavik-main-c55e52c9-20261008/refresh-main-CMakeCache.txt')
assert old_cache.read_bytes() == (W / 'refresh-pr289-CMakeCache.txt').read_bytes()
audit = {'points': 48, 'requests': sum(x['requests'] for x in checks), 'checks': checks,
         'production_cmake_caches_identical': True, 'client_cpu_percent_range': [min(cpus), max(cpus)],
         'add_fraction_range': [min(fractions), max(fractions)], 'max_final_length_deviation_pct': max(deviations)}
(W / 'command-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
(W / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
with (W / 'summary.csv').open('w') as f:
    keys = [k for k in summary[0] if k not in ['pairs', 'qps_change_range_pct', 'p99_ms_change_range_pct']]
    writer = csv.DictWriter(f, fieldnames=keys)
    writer.writeheader()
    writer.writerows({k: s[k] for k in keys} for s in summary)
with (W / 'observations.csv').open('w') as f:
    keys = ['round', 'version', 'kind', 'size', 'operation', 'qps', 'p99_ms', 'requests', 'raw']
    writer = csv.DictWriter(f, fieldnames=keys)
    writer.writeheader()
    for row in rows:
        values = {**row, **row['result']}
        values['raw'] = '../../raw/lavik-' + row['tag']
        writer.writerow({k: values[k] for k in keys})
print('ALL_48_PR289_POINTS_AUDITED', flush=True)
