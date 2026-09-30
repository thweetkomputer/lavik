#!/usr/bin/env python3
"""Summarize completed LSET intervals; I/O includes background work."""
import json
import sys
from pathlib import Path


def counters(path):
    result = {}
    for line in path.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        name, _, value = line.rpartition(' ')
        result[name] = float(value)
    return result


def info(path):
    result = {}
    for line in path.read_text().splitlines():
        name, sep, value = line.partition(':')
        if sep:
            try:
                result[name] = float(value)
            except ValueError:
                pass
    return result


def main():
    root = Path(sys.argv[1])
    summaries = []
    for folder in [root, *sorted(root.glob('diagnostic-c*'))]:
        for path in sorted(folder.glob('*.result.json')):
            row = json.loads(path.read_text())
            level = row['connections']
            before_name, after_name = ('before.prom', 'after.prom') if folder != root else (f'c{level}-clean-before.prom', f'c{level}-clean-after.prom')
            before, after = counters(folder / before_name), counters(folder / after_name)
            delta = {name: value - before.get(name, 0) for name, value in after.items()}
            stem = path.name.removesuffix('.result.json')
            ib, ia = (info(folder / (stem + suffix)) for suffix in ('.info-before.txt', '.info-after.txt'))
            di = {name: value - ib.get(name, 0) for name, value in ia.items()}
            batches = di['tx_commit_batches']
            calls = delta['lavik_command_duration_seconds_count{command="lset"}']
            summaries.append(dict(kind='clean' if folder == root else 'profiled', connections=level, qps=row['qps'], requests=row['requests'],
                io_per_operation={name: value / row['requests'] for name, value in delta.items() if name.startswith(('lavik_storage_io_operations_total', 'lavik_storage_io_bytes_total'))},
                transactions_per_batch=di['tx_commit_batch_transactions'] / batches if batches else None,
                backpressure_waits=di['tx_commit_backpressure_waits'],
                command_mean_ms=1000 * delta['lavik_command_duration_seconds_sum{command="lset"}'] / calls if calls else None))
    (root / 'io-summary.json').write_text(json.dumps(summaries, indent=2) + '\n')
    print(root.name, len(summaries), 'intervals')


if __name__ == '__main__':
    main()
