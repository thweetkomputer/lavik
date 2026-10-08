"""Audit all mixed requests and create portable chart inputs from completed runs."""
from pathlib import Path
import hashlib
import json
import re

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
D = R / 'diagnostics/main-c55e52c9-20261008'
assert 'ALL_FOUR_SYSTEM_MIXED_WRITES_COMPLETE' in (W / 'mixed-driver.log').read_text()
D.mkdir(exist_ok=True)
observed = json.loads((W / 'mixed-results.json').read_text())
protocol = json.loads((W / 'protocol.json').read_text())
assert len(observed) == 200
points = []
seen = set()
checks = []
for item in observed:
    row = item['result']
    raw = Path(item['raw'])
    identity = item['system'], row['logical_bytes'], row['operation'], row['connections']
    assert identity not in seen
    seen.add(identity)
    stem = f"{row['type']}-{row['logical_bytes']}-{row['field_bytes']}-{row['operation'].lower()}-c{row['connections']}"
    failed = 'failure' in row
    result = json.loads((raw / ('workload-guard.json' if failed else stem + '.result.json')).read_text())
    assert row == result
    client = json.loads((raw / (stem + '.client.json')).read_text())
    before = json.loads((raw / (stem + '.before-cardinality.json')).read_text())['sample_cardinalities']
    after = row['failure']['final_counts'] if failed else json.loads((raw / (stem + '.after-cardinality.json')).read_text())['sample_cardinalities']
    assert len(before) == len(after) == 8
    assert set(before) == set(after) == set(client['key_counts'])
    assert set(before.values()) == {row['entries_per_key']}
    assert all(after[k] == before[k] + count['net'] for k, count in client['key_counts'].items())
    bounded = all(row['entries_per_key'] // 2 <= n <= row['entries_per_key'] * 2 for n in after.values())
    assert bounded != failed
    assert client['errors'] == 0 and client['pipeline'] == 1
    assert row['requests'] == client['totals']['count']
    if failed:
        from mixed_failures import guard_failure
        assert row == guard_failure(raw, W / row['failure']['original_log'], item['system'], row['type'], row['operation'], row['logical_bytes'], row['connections'])
    else:
        assert row['qps'] == client['totals']['qps']
    assert all(row['command_audit']['server_counts'][cmd.lower()] == value['count']
               for cmd, value in client['commands'].items())
    assert sum(c['count'] for c in client['commands'].values()) == row['requests']
    add_command = row['operation'].split('_', 1)[0]
    add = client['commands'][add_command]['count'] / row['requests']
    assert .48 <= add <= .52
    cpu = re.search(r'Percent of CPU this job got: (\d+)%', (raw / (stem + '.client-errors.txt')).read_text())
    assert cpu
    proof = json.loads(next(raw.glob('provenance-*.json')).read_text())
    assert proof == item['provenance']
    if not failed:
        assert json.loads((raw / 'complete.json').read_text())['failures_total'] == 0
    assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
    points.append({'system': item['system'], 'kind': row['type'], 'size': row['logical_bytes'],
                   'operation': row['operation'], 'connections': row['connections'],
                   'raw': str(raw.relative_to(R)), 'binary_sha256': proof['sha256'],
                   'source_commit': proof['source_commit'],
                   **({'failure': row['failure']} if failed else {})})
    checks.append({'system': item['system'], 'size': row['logical_bytes'], 'operation': row['operation'],
                   'connections': row['connections'], 'requests': row['requests'], 'add_fraction': add,
                   'guard_passed': bounded,
                   'client_cpu_percent': int(cpu[1]), 'final_min': min(after.values()),
                   'final_max': max(after.values()),
                   'max_abs_final_change_pct': max(abs(after[k] - before[k]) for k in before) * 100 / row['entries_per_key']})

specs = [
    ('list', 'LPUSH_RPOP', 'List: LPUSH / RPOP', 'List：LPUSH / RPOP'),
    ('list', 'RPUSH_LPOP', 'List: RPUSH / LPOP', 'List：RPUSH / LPOP'),
    ('zset', 'ZADD_HEAD_ZPOPMAX', 'ZSet: ZADD (descending scores) / ZPOPMAX', 'ZSet：低分方向新成员 ZADD / ZPOPMAX'),
    ('zset', 'ZADD_RANDOM_ZPOPMIN', 'ZSet: ZADD (random score) / ZPOPMIN', 'ZSet：随机分数新成员 ZADD / ZPOPMIN'),
    ('zset', 'ZADD_TAIL_ZPOPMIN', 'ZSet: ZADD (ascending scores) / ZPOPMIN', 'ZSet：高分方向新成员 ZADD / ZPOPMIN')]
charts = []
for kind, op, en, zh in specs:
    for size in [8388608, 104857600]:
        stem = f'{kind}-{size}-1024-k8-{op.lower()}-mixed'
        charts.append({'kind': kind, 'operation': op, 'size': size,
                       'title_en': en, 'title_zh': zh, 'chart': 'charts/' + stem + '.png',
                       'csv': stem + '.csv'})
selected = [p for p in points if p['connections'] != 5120]
excluded = [p for p in points if p['connections'] == 5120]
assert len(selected) == 160 and len(excluded) == 40
manifest = {'target_main': protocol['main'], 'date': '2026-10-08',
            'connections': [80, 320, 1280, 2560], 'keys': 8, 'field_bytes': 1024,
            'seconds': 30, 'pipeline': 1, 'repeats': 1, 'points': selected, 'charts': charts,
            'excluded_connections': [5120], 'excluded_points': excluded,
            'selection_note': 'User removed 5120 connections after these runs; exclude from figures and summaries, retain raw unchanged.',
            'guard_failures': [p for p in selected if 'failure' in p],
            'method': {**protocol['new_mixed'], 'connections': [80, 320, 1280, 2560],
                       'points': 160, 'measured_points_before_exclusion': 200,
                       'excluded_connections': [5120],
                       'population': protocol['new_mixed']['population'].replace('List guards', 'List/ZSet guards')},
            'audit': str((D / 'mixed-command-audit.json').relative_to(R)),
            'measurement_notes': str((D / 'mixed-writes.md').relative_to(R))}
(R / 'current-mixed-writes.json').write_text(json.dumps(manifest, indent=2) + '\n')
audit = {'points': len(checks), 'requests': sum(x['requests'] for x in checks),
         'selected_points': len(selected), 'excluded_points': len(excluded),
         'selected_requests': sum(x['requests'] for x in checks if x['connections'] != 5120),
         'selected_passed_points': sum(x['guard_passed'] and x['connections'] != 5120 for x in checks),
         'passed_points': sum(x['guard_passed'] for x in checks),
         'guard_failures': manifest['guard_failures'],
         'checks': checks, 'all_command_counts_and_key_cardinalities_match': True,
         'client_binary': json.loads((W / 'mixed-client-provenance.json').read_text()),
         'frozen_harness': json.loads((W / 'mixed-harness-provenance.json').read_text())}
for name, sha in audit['frozen_harness'].items():
    assert hashlib.sha256((W / name).read_bytes()).hexdigest() == sha
(D / 'mixed-command-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
print('ALL_200_MIXED_POINTS_AUDITED', audit['requests'])
