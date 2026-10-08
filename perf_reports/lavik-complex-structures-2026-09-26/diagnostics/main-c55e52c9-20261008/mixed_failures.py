"""Retain a measured workload-bound violation without rerunning or hiding it."""
import ast
import json
import re


def guard_failure(raw, log, product, kind, op, size, connections):
    """Accept only the exact final-cardinality guard with a clean server exit."""
    text = log.read_text()
    assert 'assert all(entries//2<=n<=entries*2 for n in counts.values()),counts' in text
    assert 'after_cardinality=run.validate' in text
    assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
    assert not (raw / 'complete.json').exists()
    assert not list(raw.glob('*.result.json'))
    matches = re.findall(r'^AssertionError: (\{.*\})$', text, re.M)
    assert len(matches) == 1
    after = ast.literal_eval(matches[0])
    stem = f'{kind}-{size}-1024-{op.lower()}-c{connections}'
    c = json.loads((raw / (stem + '.client.json')).read_text())
    before = json.loads((raw / (stem + '.before-cardinality.json')).read_text())['sample_cardinalities']
    entries = size // 1024
    assert set(before.values()) == {entries}
    assert len(after) == len(before) == 8 and set(after) == set(before) == set(c['key_counts'])
    assert c['errors'] == 0 and c['seconds'] == 30 and c['connections'] == connections
    assert all(after[k] == before[k] + v['net'] for k, v in c['key_counts'].items())
    assert not all(entries // 2 <= n <= entries * 2 for n in after.values())
    assert all(n > 0 for n in after.values())
    def counters(label):
        values = {}
        for line in (raw / (stem + '.info-' + label + '.txt')).read_text().splitlines():
            if line.startswith('cmdstat_'):
                key, data = line.split(':', 1)
                values[key[8:]] = {k: float(v) for k, v in (p.split('=', 1) for p in data.split(','))}
        return values
    a, b = counters('before'), counters('after')
    delta = {}
    for name in set(a) | set(b):
        for metric in ['failed_calls', 'rejected_calls']:
            assert b.get(name, {}).get(metric, 0) - a.get(name, {}).get(metric, 0) == 0
        n = b.get(name, {}).get('calls', 0) - a.get(name, {}).get('calls', 0)
        assert n >= 0
        if n: delta[name] = n
    assert set(delta) <= {k.lower() for k in c['commands']} | {'info'}
    assert all(delta[k.lower()] == v['count'] for k, v in c['commands'].items())
    assert sum(v['count'] for v in c['commands'].values()) == c['totals']['count']
    assert .48 <= c['commands'][op.split('_', 1)[0]]['count'] / c['totals']['count'] <= .52
    failure = {'reason': 'final cardinality outside predeclared [0.5N, 2N] guard',
               'initial_per_key': entries, 'minimum': entries // 2, 'maximum': entries * 2,
               'final_counts': after, 'original_log': log.name,
               'disposition': 'Retained without rerun; excluded from QPS/p99 curves as a gap. No client or server command errors.'}
    result = {'type': kind, 'operation': op, 'logical_bytes': size, 'field_bytes': 1024,
              'entries_per_key': entries, 'keys': 8, 'connections': connections, 'seconds': 30,
              'qps': None, 'p50_ms': None, 'p99_ms': None, 'p999_ms': None,
              'requests': c['totals']['count'], 'failure': failure,
              'observed_client_metrics_excluded_from_curves': c['totals'],
              'command_audit': {'passed': True, 'server_counts': delta}, 'key_counts': c['key_counts']}
    target = raw / 'workload-guard.json'
    if target.exists(): assert json.loads(target.read_text()) == result
    else: target.write_text(json.dumps(result, indent=2) + '\n')
    return result
