"""Summarize sampled process progress without treating it as clean latency."""
from pathlib import Path
import argparse
from collections import Counter
import json
import os


def counters(text):
    return {key: int(value) for key, value in
            (line.split(':', 1) for line in text.splitlines())}


def task_stat(text):
    # comm may itself contain spaces or parentheses; fields start after its
    # final closing parenthesis, with state as field 3.
    fields = text.rsplit(')', 1)[1].split()
    return {'start_ticks': int(fields[19]), 'user_ticks': int(fields[11]),
            'system_ticks': int(fields[12])}


def summarize(row, ticks):
    directory = Path(row['image']).parent
    samples = json.loads((directory / 'operation-progress.json').read_text())
    valid = [s for s in samples if 'sample_error' not in s]
    assert len(valid) >= 2, ('insufficient progress samples', directory)
    assert all(s['phase']['command'] == 'GET' and
               s['phase']['key_bytes'] == 9437184 for s in valid)
    assert all(a['monotonic'] < b['monotonic'] for a, b in zip(valid, valid[1:]))
    first, last = valid[0], valid[-1]
    span = last['monotonic'] - first['monotonic']
    before, after = counters(first['io']), counters(last['io'])
    assert before.keys() == after.keys()
    io_delta = {key: after[key] - value for key, value in before.items()}
    # cancelled_write_bytes may exceed writes and is not a monotonic balance.
    assert all(value >= 0 for key, value in io_delta.items()
               if key != 'cancelled_write_bytes')
    intervals = []
    boundaries = list(range(0, len(valid), 20))
    if boundaries[-1] != len(valid) - 1:
        boundaries.append(len(valid) - 1)
    for left, right in zip(boundaries, boundaries[1:]):
        a, b = valid[left], valid[right]
        first_io, last_io = counters(a['io']), counters(b['io'])
        intervals.append({'from_first_sample_seconds': a['monotonic'] - first['monotonic'],
                          'to_first_sample_seconds': b['monotonic'] - first['monotonic'],
                          'read_bytes': last_io['read_bytes'] - first_io['read_bytes'],
                          'write_bytes': last_io['write_bytes'] - first_io['write_bytes']})
    assert sum(i['read_bytes'] for i in intervals) == io_delta['read_bytes']
    threads = []
    common = set.intersection(*(set(s['tasks']) for s in valid))
    for tid in sorted(common, key=int):
        observations = [s['tasks'][tid] for s in valid]
        states = [task_stat(s['stat']) for s in observations]
        assert len({s['start_ticks'] for s in states}) == 1, ('thread ID reused', tid)
        cpu = {key.removesuffix('_ticks') + '_seconds':
               (states[-1][key] - states[0][key]) / ticks
               for key in ('user_ticks', 'system_ticks')}
        assert all(value >= 0 for value in cpu.values())
        scheduling = [[int(x) for x in s['schedstat'].split()]
                      for s in observations]
        assert all(len(s) >= 3 for s in scheduling)
        schedule_delta = [b - a for a, b in zip(scheduling[0][:3], scheduling[-1][:3])]
        assert all(value >= 0 for value in schedule_delta)
        threads.append({'tid': int(tid), **cpu,
                        'runtime_seconds': schedule_delta[0] / 1e9,
                        'runqueue_wait_seconds': schedule_delta[1] / 1e9,
                        'timeslices': schedule_delta[2],
                        'wchan_sample_counts': dict(Counter(s['wchan'].strip() for s in observations))})
    completed = [op for op in row['operations'] if op['command'] == 'GET'
                 and op['key_bytes'] == 9437184]
    assert len(completed) <= 1
    operation = completed[0] if completed else row.get('failed_phase', {})
    assert operation.get('command') == 'GET' and operation.get('key_bytes') == 9437184
    start = operation['started_monotonic']
    finish = start + operation['seconds'] if completed else None
    return {'version': row['version'], 'whole_replay_success': row['success'],
            'get_completed': bool(completed), 'get_observation': operation,
            'error': row.get('error'), 'perf_exit': row.get('perf_exit'),
            'samples': len(samples), 'excluded_samples': len(samples) - len(valid),
            'sample_span_seconds': span,
            'first_sample_from_get_start_seconds': first['monotonic'] - start,
            'last_sample_before_get_finish_seconds': finish - last['monotonic'] if finish else None,
            'sampled_process_io_delta': io_delta, 'progress_intervals': intervals, 'threads': threads,
            'thread_ids_not_present_in_every_sample': sorted(set.union(*(set(s['tasks']) for s in valid)) - common),
            'theoretical_repeated_key_payload_bytes': 9 * 1024 * 1024 * (6 * 1024 * 1024 // 8192)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path(__file__).parent / 'pr267-retained-image-profiles.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    assert len(data['rows']) == 2 and {r['version'] for r in data['rows']} == {'main', 'candidate'}
    ticks = os.sysconf('SC_CLK_TCK')
    result = {'source': str(args.input), 'original_sha256': data['original_sha256'],
              'versions': data['versions'], 'clock_ticks_per_second': ticks,
              'limitations': 'Diagnostic sampled intervals, not clean paired QPS or command-exclusive CPU/IO. Process counters include background work. First/last samples can omit boundary intervals, and missing samples are reported. Thread CPU covers only IDs present throughout. wchan counts are observations, not time fractions. Theoretical repeated key bytes exclude headers, first verification and retries; do not equate them to device traffic.',
              'rows': [summarize(row, ticks) for row in data['rows']]}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    for row in result['rows']:
        print(row['version'], 'GET complete:', row['get_completed'],
              'sampled read bytes:', row['sampled_process_io_delta'].get('read_bytes'),
              'sample span:', row['sample_span_seconds'])


if __name__ == '__main__':
    main()
