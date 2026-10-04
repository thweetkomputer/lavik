from pathlib import Path
import csv
import importlib.util
import json
import re
import time

R = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('current_plot', R/'plot_current_main.py')
plot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plot)
m = json.loads((R/'current-main.json').read_text())
imports = json.loads((R/'current-imports.json').read_text())
assert len(m['plots']) == 28 and len(imports['plots']) == 4
assert all(r['main']['fresh'] for r in m['plots'] + imports['plots'])
assert {r['main']['commit'] for r in m['plots'] + imports['plots']} == {m['target_main']}
points = {}
failures = []
for row in m['plots']:
    assert row['size'] != 10 * 1024 * 1024
    assert all(v['pr'] == 249 for v in row.get('variants', []))
    records = list(csv.DictReader((R/(plot.key(row)+'-current.csv')).open()))
    expected_count = 0
    for label, source, revision in plot.series(row):
        values, errors = plot.load(row, source, revision)
        selected = [r for r in records if r['series'] == label]
        assert len(selected) == len(values) + len(errors)
        expected_count += len(selected)
        points[label] = points.get(label, 0) + len(selected)
        for record in selected:
            key = (record['command'], int(record['connections']))
            if key in values:
                assert float(record['qps']) == values[key]['qps']
                assert float(record['p99_ms']) == values[key]['p99_ms']
                assert not record['error']
            else:
                assert not record['qps'] and record['error'] == errors[key]['error']
                failures.append({'series': label, 'condition': plot.key(row), 'operation': key[0], 'connections': key[1], 'source': str(source.relative_to(R))})
    assert len(records) == expected_count
figures = {}
for name in ['README.md', 'README.zh-CN.md']:
    text = (R/name).read_text()
    assert not re.search(r'^\|', text, re.M)
    assert '10 MiB/key' not in text
    assert 'previous measurement' not in text.lower()
    assert '历史测量，' not in text
    images = re.findall(r'!\[[^]]*\]\(([^)]+)\)', text)
    assert len(images) == 84 and len(set(images)) == 84
    for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', text):
        if not link.startswith(('https:', 'http:', 'mailto:')):
            assert (R/link).exists(), link
    for image in images:
        assert (R/image).stat().st_size > 10000
    figures[name] = len(images)
for row in imports['plots']:
    source = R/'raw'/('lavik-'+row['main']['tag'])
    assert json.loads((source/'complete.json').read_text())['failures_total'] == 0
    assert json.loads((source/'server-exit.json').read_text())['code'] == 0
    assert (source/'seed-client-proof.json').exists()
result = {'time': time.time(), 'measured_main': m['target_main'], 'main_conditions': 28, 'import_conditions': 4, 'embedded_figures': figures, 'observations_by_series': points, 'failed_observations': failures, 'checks': ['raw QPS and p99 match plot CSV', 'complete connection grids', 'source commits and binary hashes match manifest', 'cardinality checks and clean server exits', 'all relative README links and images exist', 'no result tables or 10 MiB conditions', 'no pending historical main rows']}
(R/'diagnostics/main-refresh-20261004/report-audit.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
