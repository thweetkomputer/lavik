"""Validate the existing fixed-binary worker-count experiment before summarizing."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--report-root', type=Path, required=True)
parser.add_argument('--validate-only', action='store_true')
args = parser.parse_args()
source = args.input.read_bytes()
data = json.loads(source)
version = data['version']
assert version['commit'] == '067c75891f819831620e277eac0592c360f8b585'
expected = {(n, workers, op, c) for n in (1, 2, 3) for workers in (8, 12)
            for op in ('ZSCORE', 'ZINCRBY') for c in (80, 320)}
observed = {}
proofs = {}
cpu = []
commands = set()

for row in data['rows']:
    identity = (row['round'], row['workers'], row['operation'], row['connections'])
    assert identity in expected and identity not in observed
    observed[identity] = row
    assert 'error' not in row and row['seconds'] == 30 and row['requests'] > 0
    assert (row['logical_bytes'], row['field_bytes'], row['keys'], row['entries_per_key']) == (104857600, 1024, 8, 102400)
    assert all(math.isfinite(row[k]) and row[k] > 0 for k in ('qps', 'p99_ms'))
    raw = args.report_root / 'raw' / ('lavik-' + row['tag'])
    stem = f"zset-104857600-1024-{row['operation'].lower()}-c{row['connections']}"
    result = json.loads((raw / (stem + '.result.json')).read_text())
    assert all(row[k] == value for k, value in result.items())
    if row['tag'] not in proofs:
        assert not list(raw.glob('*.error.json'))
        assert json.loads((raw / 'complete.json').read_text())['failures_total'] == 0
        assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
        provenance = json.loads(next(raw.glob('provenance-*.json')).read_text())
        assert provenance['source_commit'] == version['commit'] and provenance['sha256'] == version['sha256']
        experiment = json.loads((raw / 'worker-experiment.json').read_text())
        assert experiment['workers'] == row['workers']
        argv = json.loads((raw / 'server-command.json').read_text())
        assert [a for a in argv if a.startswith('--threads=')] == [f"--threads={row['workers']}"]
        # Per-run log destinations are bookkeeping, not a server configuration difference.
        commands.add(tuple(a for a in argv if not a.startswith(('--threads=', '--log-dir='))))
        before = json.loads((raw / 'zset-104857600-1024.validated.json').read_text())['sample_cardinalities']
        after = json.loads((raw / 'zset-104857600-1024.after.json').read_text())['sample_cardinalities']
        assert before == after == {f'complex_{i}': 102400 for i in range(1, 9)}
        proofs[row['tag']] = {'workers': row['workers'], 'source': provenance,
                              'experiment': experiment, 'keys_checked': 8, 'clean_exit': True}
    before, after = [json.loads((raw / f'{stem}.cpu-{phase}.json').read_text()) for phase in ('before', 'after')]
    assert before['pid'] == after['pid']
    assert before['ticks_per_second'] == after['ticks_per_second'] > 0
    elapsed = after['monotonic'] - before['monotonic']
    assert elapsed > 0
    b = {t['tid']: t for t in before['threads']}
    a = {t['tid']: t for t in after['threads']}
    assert a.keys() == b.keys()
    threads = []
    for tid in sorted(a):
        assert a[tid]['starttime_ticks'] == b[tid]['starttime_ticks']
        user = a[tid]['utime_ticks'] - b[tid]['utime_ticks']
        system = a[tid]['stime_ticks'] - b[tid]['stime_ticks']
        assert user >= 0 and system >= 0
        seconds = (user + system) / before['ticks_per_second']
        threads.append({'tid': tid, 'comm': a[tid]['comm'], 'user_ticks': user,
                        'system_ticks': system, 'cpu_seconds': seconds,
                        'one_core_percent': 100 * seconds / elapsed})
    cpu.append({'identity': identity, 'tag': row['tag'], 'elapsed_seconds': elapsed,
                'process_cpu_seconds': sum(t['cpu_seconds'] for t in threads),
                'threads': threads})

assert observed and len(commands) == 1
output = {'input_sha256': hashlib.sha256(source).hexdigest(), 'version': version,
          'method': data['method'], 'observations': len(observed),
          'expected_observations': 24, 'proofs': proofs, 'cpu_windows': cpu,
          'summary': [], 'limits': 'Configuration comparison on one frozen binary; different worker counts also change per-worker pools, placement and owner mapping. CPU snapshots include client startup/result collection, network, kernel, polling and background work. No TID-to-owner binding or command-exclusive CPU claim. Original 12-worker peer curves remain unchanged.'}
if args.validate_only:
    output['status'] = 'Available observations validated; incomplete scopes have no comparison conclusion.'
else:
    assert observed.keys() == expected, (len(observed), len(expected))
    for op in ('ZSCORE', 'ZINCRBY'):
        for c in (80, 320):
            pairs = []
            for n in (1, 2, 3):
                baseline, candidate = observed[n, 12, op, c], observed[n, 8, op, c]
                pairs.append({'round': n, 'workers12': baseline, 'workers8': candidate,
                              'qps_change_percent': 100 * (candidate['qps'] / baseline['qps'] - 1),
                              'p99_change_percent': 100 * (candidate['p99_ms'] / baseline['p99_ms'] - 1)})
            entry = {'operation': op, 'connections': c, 'pairs': pairs}
            for metric in ('qps', 'p99'):
                values = [pair[metric + '_change_percent'] for pair in pairs]
                entry[metric + '_paired_percent'] = {'median': statistics.median(values),
                    'min': min(values), 'max': max(values),
                    'positive_pairs': sum(v > 0 for v in values),
                    'negative_pairs': sum(v < 0 for v in values)}
            output['summary'].append(entry)
    output['status'] = 'All 24 observations and three pairs per cell validated.'
args.output.write_text(json.dumps(output, indent=2) + '\n')
print(output['status'], len(observed), '/ 24')
