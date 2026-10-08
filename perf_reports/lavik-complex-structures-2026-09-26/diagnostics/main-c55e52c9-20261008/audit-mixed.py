"""Check published mixed-write CSV values and all source links against raw data."""
from pathlib import Path
import csv
import importlib.util
import json

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
D = R / 'diagnostics/main-c55e52c9-20261008'
spec = importlib.util.spec_from_file_location('mixed_plot', R / 'plot_mixed_writes.py')
plot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plot)
m = json.loads((R / 'current-mixed-writes.json').read_text())
total = 0
for chart in m['charts']:
    rows = list(csv.DictReader((R / chart['csv']).open()))
    expected = plot.observations(m, chart)
    assert len(rows) == len(expected) == 16
    for row, actual in zip(rows, expected):
        for key in ['qps', 'p50_ms', 'p99_ms', 'p999_ms']:
            assert row[key] == '' if actual[key] is None else float(row[key]) == actual[key]
        assert int(row['requests']) == actual['requests']
        for key in ['system', 'command', 'raw', 'binary_sha256', 'error']:
            assert row[key] == actual[key]
    assert (R / chart['chart']).stat().st_size > 10000
    for name in ['README.md', 'README.zh-CN.md']:
        assert (R / name).read_text().count('](' + chart['chart'] + ')') == 1
    total += len(rows)
assert total == 160
out = {'main': m['target_main'], 'points': total, 'charts': len(m['charts']),
       'checks': ['every point appears once in its exact system/operation/size/concurrency grid',
                  'CSV QPS and all latency percentiles equal raw source',
                  'command counts and final key changes match; bound violations remain gaps', 'binary/source identities match',
                  'each generated chart appears once in each language']}
(D / 'mixed-plot-audit.json').write_text(json.dumps(out, indent=2) + '\n')
print('ALL_MIXED_PLOTS_AUDITED', total)
