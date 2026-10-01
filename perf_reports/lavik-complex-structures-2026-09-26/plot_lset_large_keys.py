#!/usr/bin/env python3
"""Plot matched LSET workloads for peers, Lavik main and unmerged PRs."""
import argparse
import csv
import json
from pathlib import Path

import plot_set_hash_high_keys as chart

ROOT = Path(__file__).resolve().parent


def load(revision, size, keys):
    product = revision.get('product', 'lavik')
    folder = ROOT / 'raw' / (product + '-' + revision['tag'])
    provenance = list(folder.glob('provenance-*.json'))
    if len(provenance) != 1:
        raise ValueError(f'Ambiguous provenance: {folder}')
    source = json.loads(provenance[0].read_text())
    expected = dict(source_commit=revision['commit'], sha256=revision['sha256'],
                    types=['list'], sizes=[size], fields=[1024], keys=keys,
                    levels=list(chart.POINT_LEVELS), seconds=10, mode='point',
                    seed_pipeline=4, fill_workers=32, seed_command_bytes=131072,
                    reused_seed_from=None)
    for name, value in expected.items():
        if source.get(name) != value:
            raise ValueError(f'{folder}: incorrect {name}')
    if json.loads((folder / 'server-exit.json').read_text())['code'] != 0:
        raise ValueError(f'Unclean server exit: {folder}')
    if json.loads((folder / 'complete.json').read_text())['failures_total']:
        raise ValueError(f'Failed measurements: {folder}')
    for stage in ('validated', 'after'):
        counts = json.loads((folder / f'list-{size}-1024.{stage}.json').read_text())['sample_cardinalities']
        if len(counts) != keys or set(counts.values()) != {size // 1024}:
            raise ValueError(f'Incomplete cardinality validation: {folder}')
    plan = folder / 'measurement-plan.json'
    if plan.exists():
        if json.loads(plan.read_text())['profile_strategy'] != 'after-entire-clean-grid-v1':
            raise ValueError(f'Profiling interrupted the clean grid: {folder}')
    elif product == 'lavik' and (revision['label'] != 'Lavik main' or list(folder.glob('diagnostic-c*'))):
        raise ValueError(f'Missing measurement-order evidence: {folder}')
    rows = {}
    for path in folder.glob('*.result.json'):
        row = json.loads(path.read_text())
        for name, value in dict(product=folder.name, type='list', logical_bytes=size, field_bytes=1024,
                                keys=keys, operation='LSET', seconds=10).items():
            if row.get(name) != value:
                raise ValueError(f'{path}: incorrect {name}')
        level = row['connections']
        if level in rows:
            raise ValueError(f'Duplicate point: {path}')
        rows[level] = row
    if set(rows) != set(chart.POINT_LEVELS):
        raise ValueError(f'Incomplete connection grid: {folder}')
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    for condition in json.loads(args.manifest.read_text())['plots']:
        size, keys = condition['size'], condition['keys']
        if (size, keys) not in ((1048576, 50000), (104857600, 500)):
            raise ValueError('Unexpected workload')
        fig, ax = chart.plt.subplots(figsize=(9, 4.8))
        records = []
        peers = condition.get('peers', [])
        if peers and {p['product'] for p in peers} != {'redis', 'valkey', 'kvrocks'}:
            raise ValueError('Peer comparison requires Redis, Valkey and Kvrocks')
        series = [(p, p['product']) for p in peers]
        series.append((condition['main'], 'lavik'))
        series.extend((p, 'variant0') for p in condition['variants'])
        for revision, style_name in series:
            rows = load(revision, size, keys)
            style = chart.STYLES[style_name]
            label = revision['label']
            if revision.get('product', 'lavik') == 'lavik':
                label += ' ' + revision['commit'][:8]
            ax.plot(chart.POINT_LEVELS, [rows[c]['qps'] / 1000 for c in chart.POINT_LEVELS],
                    color=style[0], marker=style[1], linestyle=style[2], linewidth=2,
                    label=label)
            for level, row in sorted(rows.items()):
                records.append(dict(label=revision['label'], commit=revision['commit'],
                                    keys=keys, bytes_per_key=size, connections=level,
                                    qps=row['qps'], p99_ms=row['p99_ms']))
        ax.set_title(f'List LSET · {size // 1048576} MiB/key · {keys:,} keys · 1024 B/entry')
        ax.set_xlabel('Connections (log scale)')
        ax.set_ylabel('Throughput (k QPS)')
        ax.set_xscale('log')
        ax.set_xticks(chart.POINT_LEVELS, [f'{n:,}' for n in chart.POINT_LEVELS])
        ax.set_ylim(bottom=0)
        ax.grid(alpha=0.2)
        ax.legend()
        fig.tight_layout()
        name = f'list-lset-{size}-1024-k{keys}-main-pr'
        fig.savefig(ROOT / 'charts' / (name + '.png'), dpi=160, bbox_inches='tight', pad_inches=0.2)
        chart.plt.close(fig)
        with (ROOT / (name + '.csv')).open('w', newline='') as out:
            writer = csv.DictWriter(out, fieldnames=list(records[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(records)
        print(name)


if __name__ == '__main__':
    main()
