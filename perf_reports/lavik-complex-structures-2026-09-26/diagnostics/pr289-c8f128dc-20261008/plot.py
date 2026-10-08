"""Compare three process repetitions; whiskers show observed min/max, not CIs."""
from pathlib import Path
import json
import statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

W = Path(__file__).parent
rows = json.loads((W / 'repeats.json').read_text())['rows']
summary = json.loads((W / 'summary.json').read_text())
plt.rcParams.update({'font.size': 11})
for kind in ['list', 'zset']:
    cases = [s for s in summary if s['kind'] == kind]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    x = np.arange(len(cases))
    for ax, metric, title in zip(axes, ['qps', 'p99_ms'], ['Command QPS (higher is better)', 'p99, ms (lower is better)']):
        for offset, version, color, label in [(-.18, 'main', '#5973ab', 'main c55e52c9'), (.18, 'pr289', '#df8a3f', 'PR #289 c8f128dc')]:
            sets = [[r['result'][metric] for r in rows if (r['kind'], r['size'], r['operation'], r['version']) == (kind, s['size'], s['operation'], version)] for s in cases]
            med = np.array([statistics.median(v) for v in sets])
            err = [med - [min(v) for v in sets], np.array([max(v) for v in sets]) - med]
            ax.bar(x + offset, med, .34, yerr=err, capsize=3, color=color, label=label)
        ax.set_xticks(x, [f"{s['size']//1048576} MiB\n{s['operation'].replace('_', '/') }" for s in cases], fontsize=9)
        ax.set_yscale('log')
        ax.set_title(title)
        ax.set_ylabel('Log scale')
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(.5, .06), ncol=2, frameon=False)
    fig.suptitle(f"{kind.title()}: PR #289 versus its main base\n8 keys | 1 KiB entries | 320 connections | pipeline=1 | 30 s/point", fontsize=14)
    fig.text(.5, .025, 'Bars: medians of 3 AB/BA/AB repetitions. Whiskers: observed min/max, not confidence intervals.', ha='center', fontsize=9)
    fig.subplots_adjust(top=.77, bottom=.25, wspace=.25)
    fig.savefig(W / (kind + '-comparison.png'), dpi=160)
    plt.close(fig)
print('PR289_PLOTS_COMPLETE')
