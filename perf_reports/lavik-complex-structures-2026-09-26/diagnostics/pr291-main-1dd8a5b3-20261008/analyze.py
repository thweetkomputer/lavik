"""Audit frozen PR291 measurements and aggregate paired, not pooled, ratios."""
from pathlib import Path
import csv
import hashlib
import json
from statistics import median
import sys

W = Path(__file__).resolve().parent
read = lambda p: json.loads(p.read_text())
rows = read(W / 'pairs.json')
protocol = read(W / 'protocol.json')
versions = read(W / 'versions.json')
complete = '--complete' in sys.argv
expected = {(r, v, op) for r in (1, 2, 3) for v in versions
            for kind, op in protocol['operations']}
observed = {(r['round'], r['version'], r['operation']) for r in rows}
assert len(observed) == len(rows) and observed <= expected
if complete:
    assert observed == expected
assert (W / 'main-CMakeCache.txt').read_bytes() == (W / 'pr291-CMakeCache.txt').read_bytes()
cache = (W / 'main-CMakeCache.txt').read_text()
for flag in ('BUILD_TESTING:BOOL=OFF', 'LAVIK_ENABLE_TEST_FAULTS:BOOL=OFF',
             'CMAKE_BUILD_TYPE:STRING=RelWithDebInfo', 'LAVIK_MARCH:STRING=native'):
    assert flag in cache, flag
for key in ('bycorf_commit', 'bycorf_source_status', 'bycorf_submodule_revisions'):
    assert versions['main'][key] == versions['pr291'][key]
for path, sha in read(W / 'harness-provenance.json').items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha, path

observations = []
canonical_server = None
for row in rows:
    raw = Path(row['raw'])
    one = lambda pattern: next(raw.glob(pattern))
    result = read(one('*.result.json'))
    assert result == row['result']
    client = read(one('*.client.json'))
    proof = read(one('provenance-*.json'))
    seed = read(raw / 'fixed-digest-seed.json')
    v = versions[row['version']]
    assert proof['sha256'] == seed['sha256'] == v['sha256']
    assert proof['source_commit'] == seed['source_commit'] == v['commit']
    assert seed['verified_via_proc_mem'] and seed['seed_hex'] == row['digest_seed']
    assert str(client['seed']) == row['client_seed']
    assert client['errors'] == read(raw / 'complete.json')['failures_total'] == 0
    assert read(raw / 'server-exit.json')['code'] == 0
    assert client['connections'] == 320 and client['pipeline'] == 1
    assert client['threads'] == 16 and client['seconds'] == 30
    assert 30 <= client['elapsed_seconds'] <= 40
    assert client['keys'] == 8 and client['entries'] == 8192 and client['field_bytes'] == 1024
    assert client['operation'] == row['operation']
    assert result['qps'] == client['totals']['qps']
    assert abs(client['totals']['count'] / client['elapsed_seconds'] / result['qps'] - 1) < 1e-8
    assert result['command_audit']['passed']
    assert result['requests'] == sum(c['count'] for c in client['commands'].values())
    before = read(one('*.before-cardinality.json'))['sample_cardinalities']
    after = read(one('*.after-cardinality.json'))['sample_cardinalities']
    assert set(before.values()) == {8192} and len(before) == len(after) == 8
    for key, counts in client['key_counts'].items():
        assert after[key] == before[key] + counts['net']
        assert 4096 <= after[key] <= 16384
    mixed = len(client['commands']) == 2
    if mixed:
        assert .48 < next(iter(client['commands'].values()))['count'] / result['requests'] < .52
    if row['kind'] == 'list' and mixed:
        assert 4096 <= client['observed_push_min'] <= client['observed_push_max'] <= 16384
    server = read(raw / 'server-command.json')
    server = ['BINARY' if x == v['binary'] else x for x in server if not x.startswith('--log-dir=')]
    if canonical_server is None:
        canonical_server = server
    assert server == canonical_server
    settle = read(one('*.settled.json'))
    assert settle['remaining_backlog_bytes'] <= 16 * 1024 * 1024
    info = {}
    for when in ('before', 'after'):
        info[when] = dict(line.split(':', 1) for line in
                          one('*.info-' + when + '.txt').read_text().splitlines()
                          if ':' in line)
    assert int(info['before']['tx_commit_queue_depth']) == 0
    assert int(info['before']['tx_cleaner_running']) == 0
    assert int(info['after']['tx_cleaner_failures']) == 0
    for command, stats in client['commands'].items():
        key = 'cmdstat_' + command.lower()
        parse_count = lambda when: dict(x.split('=', 1) for x in
                                       info[when].get(key, 'calls=0,failed_calls=0,rejected_calls=0').split(','))
        a, b = parse_count('before'), parse_count('after')
        assert int(b['calls']) - int(a['calls']) == stats['count']
        for error in ('failed_calls', 'rejected_calls'):
            assert int(b.get(error, 0)) - int(a.get(error, 0)) == 0
    set_fraction = None
    if row['operation'] == 'SADD_SREM':
        changes = client['set_changes']
        assert changes['adds'] - changes['removes'] == sum(k['net'] for k in client['key_counts'].values())
        assert changes['adds'] <= client['commands']['SADD']['count']
        assert changes['removes'] <= client['commands']['SREM']['count']
        set_fraction = sum(changes.values()) / result['requests']
    observations.append({
        'round': row['round'], 'version': row['version'], 'operation': row['operation'],
        'qps': result['qps'], 'p50_ms': result['p50_ms'], 'p99_ms': result['p99_ms'],
        'p999_ms': result['p999_ms'], 'requests': result['requests'],
        'set_changed_fraction': set_fraction, 'final_cardinality_min': min(after.values()),
        'final_cardinality_max': max(after.values()),
        'seed_remaining_backlog_bytes': settle['remaining_backlog_bytes'],
        'commit_queue_peak_before': int(info['before']['tx_commit_queue_peak']),
        'commit_queue_peak_after': int(info['after']['tx_commit_queue_peak']),
        'raw_directory': raw.name,
    })

summary = []
for kind, op in protocol['operations']:
    pairs = []
    for r in (1, 2, 3):
        p = {x['version']: x for x in rows if x['round'] == r and x['operation'] == op}
        if len(p) != 2:
            continue
        assert p['main']['digest_seed'] == p['pr291']['digest_seed']
        assert p['main']['client_seed'] == p['pr291']['client_seed']
        a, b = p['main']['result'], p['pr291']['result']
        pairs.append({'round': r, 'main_qps': a['qps'], 'pr291_qps': b['qps'],
                      'qps_change_pct': 100 * (b['qps'] / a['qps'] - 1),
                      'main_p99_ms': a['p99_ms'], 'pr291_p99_ms': b['p99_ms'],
                      'p99_change_pct': 100 * (b['p99_ms'] / a['p99_ms'] - 1)})
    if not pairs:
        continue
    entry = {'operation': op, 'pairs_completed': len(pairs),
             'qps_change_pct': median(x['qps_change_pct'] for x in pairs),
             'p99_change_pct': median(x['p99_change_pct'] for x in pairs),
             'qps_change_min_pct': min(x['qps_change_pct'] for x in pairs),
             'qps_change_max_pct': max(x['qps_change_pct'] for x in pairs),
             'paired_results': pairs}
    for label in versions:
        paired_rounds = {p['round'] for p in pairs}
        results = [x['result'] for x in rows if x['version'] == label
                   and x['operation'] == op and x['round'] in paired_rounds]
        for metric in ('qps', 'p50_ms', 'p99_ms', 'p999_ms'):
            entry[label + '_' + metric] = median(x[metric] for x in results)
    summary.append(entry)
    print(f"{op:22} {len(pairs)}/3 {entry['main_qps']:9.0f} -> {entry['pr291_qps']:9.0f} "
          f"paired QPS {entry['qps_change_pct']:+6.1f}% p99 {entry['p99_change_pct']:+6.1f}%")

output = {'complete': observed == expected, 'observations': len(rows),
          'aggregation': 'Median of three paired percentage changes. Absolute values are separate medians; their ratio need not equal the median paired ratio.',
          'results': summary}
(W / 'analysis.json').write_text(json.dumps(output, indent=2) + '\n')
for name, data in [('observations.csv', observations),
                   ('summary.csv', [{k: v for k, v in s.items() if k != 'paired_results'} for s in summary])]:
    if data:
        with (W / name).open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(data)
print(f"AUDITED {len(rows)}/42 observations; complete={output['complete']}")
