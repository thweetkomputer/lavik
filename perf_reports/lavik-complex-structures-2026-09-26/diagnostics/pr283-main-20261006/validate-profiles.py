"""Check separately instrumented runs without treating their QPS as clean data."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--report-root', type=Path, default=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26'))
p.add_argument('--input', type=Path, default=Path(__file__).parent / 'profiles.json')
p.add_argument('--versions', type=Path, default=Path(__file__).parent / 'pr283-versions.json')
p.add_argument('--output-dir', type=Path, default=Path(__file__).parent)
a = p.parse_args()
profiles = json.loads(a.input.read_text())
versions = json.loads(a.versions.read_text())
assert len(profiles) == 4
rows, proofs, identities = [], [], set()
for item in profiles:
    raw = a.report_root / 'raw' / ('lavik-' + item['tag'])
    directory = raw / 'diagnostic-c80'
    provenance, = list(raw.glob('provenance-*.json'))
    source = json.loads(provenance.read_text())
    v = versions[item['version']]
    assert source['source_commit'] == v['commit'] and source['sha256'] == v['sha256']
    assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
    assert json.loads((raw / 'complete.json').read_text())['failures_total'] == 0
    assert not list(raw.rglob('*.error.json'))
    result, = list(directory.glob('*.result.json'))
    row = json.loads(result.read_text())
    assert row['operation'] == 'ZINCRBY' and row['connections'] == 80 and row['seconds'] == 30
    identity = item['version'], row['logical_bytes'], row['field_bytes'], row['keys']
    assert identity not in identities
    identities.add(identity)
    prefix = f'zset-{row["logical_bytes"]}-{row["field_bytes"]}'
    counts = []
    for stage in ('validated', 'after'):
        c = json.loads((raw / (prefix + '.' + stage + '.json')).read_text())['sample_cardinalities']
        assert set(c) == {f'complex_{i}' for i in range(1, row['keys'] + 1)}
        assert all(n == row['logical_bytes'] // row['field_bytes'] for n in c.values())
        counts.append(c)
    assert counts[0] == counts[1]
    profile = json.loads((directory / 'profile-provenance.json').read_text())
    assert profile == item['profile'] and profile['source_commit'] == v['commit']
    assert profile['operation'] == 'ZINCRBY' and len(profile['argv_by_tid']) >= 12
    assert not source['reused_seed_from']
    rows.append({'tag': item['tag'], **row})
    proofs.append({'tag': item['tag'], 'source_sha256': hashlib.sha256(provenance.read_bytes()).hexdigest(),
                   'result_sha256': hashlib.sha256(result.read_bytes()).hexdigest(),
                   'keys_checked': len(counts[0]), 'server_exit': 0})
assert identities == {(version, *size) for version in ('parent', 'candidate')
                      for size in [(104857600, 1024, 8), (65536, 128, 64)]}
out = a.output_dir / 'profile-observations.json'
out.write_text(json.dumps({'rows': rows, 'proofs': proofs,
                           'limits': 'Instrumented QPS excluded from clean comparison.'}, indent=2) + '\n')
subprocess.run([sys.executable, str(Path(__file__).parent / 'audit-commands.py'),
                '--profile-layout', '--input', str(out), '--output',
                str(a.output_dir / 'profile-command-audit.json'), '--report-root', str(a.report_root)], check=True)
print('Verified four separate profiles, full populations and command counts.')
