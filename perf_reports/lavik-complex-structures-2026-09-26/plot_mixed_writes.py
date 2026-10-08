#!/usr/bin/env python3
"""Render audited random-key mixed writes, keeping QPS and tail latency together."""
from pathlib import Path
import csv
import json
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent
PRODUCTS = ['redis', 'valkey', 'kvrocks', 'lavik']
LABELS = {'redis': 'Redis', 'valkey': 'Valkey', 'kvrocks': 'Kvrocks (80 GiB cache)',
          'lavik': 'Lavik main'}
STYLES = [('#bd3f43', 'o', '-'), ('#008681', 's', '--'),
          ('#a75b19', 'D', '-.'), ('#6574bc', '^', '-')]


def observations(manifest, chart):
    """Reject missing, duplicate, mismatched, or unaudited source observations."""
    selected = [p for p in manifest['points']
                if (p['kind'], p['size'], p['operation']) ==
                (chart['kind'], chart['size'], chart['operation'])]
    expected = {(system, c) for system in PRODUCTS for c in manifest['connections']}
    seen = set()
    rows = []
    for point in selected:
        identity = point['system'], point['connections']
        assert identity in expected and identity not in seen
        seen.add(identity)
        raw = ROOT / point['raw']
        failed = 'failure' in point
        results = [raw / 'workload-guard.json'] if failed else list(raw.glob('*.result.json'))
        assert len(results) == 1
        result = json.loads(results[0].read_text())
        proof = json.loads(next(raw.glob('provenance-*.json')).read_text())
        assert proof['sha256'] == point['binary_sha256']
        if point['system'] == 'lavik':
            assert proof['source_commit'] == manifest['target_main']
        if not failed:
            assert json.loads((raw / 'complete.json').read_text())['failures_total'] == 0
        assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
        assert result['command_audit']['passed']
        assert (result['operation'], result['logical_bytes'], result['field_bytes'],
                result['keys'], result['connections'], result['seconds']) == (
                    chart['operation'], chart['size'], manifest['field_bytes'],
                    manifest['keys'], point['connections'], manifest['seconds'])
        if failed:
            assert result['failure'] == point['failure']
            assert result['qps'] is None and result['p99_ms'] is None
        else:
            assert all(math.isfinite(result[k]) and result[k] > 0 for k in ['qps', 'p99_ms'])
        rows.append({'system': point['system'], 'command': chart['operation'],
                     'connections': point['connections'], 'qps': result['qps'],
                     'p50_ms': result['p50_ms'], 'p99_ms': result['p99_ms'],
                     'p999_ms': result['p999_ms'], 'requests': result['requests'],
                     'seconds': result['seconds'], 'raw': point['raw'],
                     'binary_sha256': point['binary_sha256'],
                     'error': result['failure']['reason'] if failed else ''})
    assert seen == expected
    return rows


def draw(manifest, chart):
    rows = observations(manifest, chart)
    with (ROOT / chart['csv']).open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6))
    for system, (color, marker, style) in zip(PRODUCTS, STYLES):
        data = sorted((r for r in rows if r['system'] == system), key=lambda r: r['connections'])
        label = LABELS[system]
        if system == 'lavik':
            label += ' ' + manifest['target_main'][:8]
        for ax, metric in zip(axes, ['qps', 'p99_ms']):
            ax.plot([r['connections'] for r in data], [r[metric] if r[metric] is not None else float('nan') for r in data],
                    label=label, color=color, marker=marker, linestyle=style,
                    linewidth=2, markersize=6,
                    markerfacecolor='none' if system == 'redis' else color)
    for ax in axes:
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xticks(manifest['connections'], [f'{n:,}' for n in manifest['connections']])
        ax.set_xlabel('Connections (log scale)')
        ax.grid(alpha=.2)
    axes[0].set_ylabel('Commands / second (log scale; higher is better)')
    axes[0].yaxis.set_major_formatter(FuncFormatter(lambda n, _: f'{n/1000:g}k' if n >= 1000 else f'{n:g}'))
    axes[1].set_ylabel('Mixed-command p99, ms (log scale; lower is better)')
    axes[1].yaxis.set_major_formatter(FuncFormatter(lambda n, _: f'{n:g}'))
    fig.suptitle(chart['title_en'] + '\n' +
                 f"{chart['size']//1048576} MiB/key | {manifest['keys']} keys | " +
                 f"{manifest['field_bytes']} B/entry | 50:50 add/pop", fontsize=13)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(.5, .085),
               ncol=4, frameon=False, fontsize=9)
    failures = sum(bool(r['error']) for r in rows)
    footer = 'Uniform random key per command; fresh data per point; 30 s; pipeline=1; one sweep.\n' + \
             'Redis/Valkey persistence OFF; Kvrocks WAL OFF; Lavik SPDK persistent. Durability differs.'
    if failures:
        footer += f'\n{failures} workload-bound violation(s) shown as gaps; see source CSV and report.'
    fig.text(.5, .025, footer,
             ha='center', va='bottom', fontsize=8, color='#444444')
    fig.subplots_adjust(top=.78, bottom=.25, left=.075, right=.98, wspace=.27)
    fig.savefig(ROOT / chart['chart'], dpi=160)
    plt.close(fig)


def main():
    manifest = json.loads((ROOT / 'current-mixed-writes.json').read_text())
    assert len(manifest['points']) == 160 and len(manifest['charts']) == 10
    for chart in manifest['charts']:
        draw(manifest, chart)


if __name__ == '__main__':
    main()
