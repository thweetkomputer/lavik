"""Independent perf diagnostics after all clean Stream follow-up rounds finish."""
from pathlib import Path
import json
import os
import subprocess
import time

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
output = W / 'stream-followup-profiles.json'
assert not output.exists(), 'inspect prior profile before restarting'
proc = Path('/proc/695113/stat')
identity = proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_CLEAN_STREAM_ROUNDS', identity, time.time(), flush=True)
while proc.exists() and identity is not None:
    try:
        if proc.read_text().split()[21] != identity:
            break
    except FileNotFoundError:
        break
    time.sleep(15)
assert 'ALL_STREAM_FOLLOWUP_REPEATS_COMPLETE' in (W / 'stream-followup-independent-repeat-driver.log').read_text()
repeats = json.loads((W / 'stream-followup-repeats.json').read_text())
assert len(repeats['rows']) == 90
assert not any('error' in row for row in repeats['rows']), 'investigate clean benchmark errors before profiling'
from host_execution_lock import acquire_host
_execution_lock = acquire_host('stream-followup-perf')

profiles = {}
for mode, connections in [('full', 1), ('point', 2560)]:
    for label in ['parent', 'window', 'singleton']:
        v = repeats['versions'][label]
        tag = f'diagnostic-{label}{v["commit"][:8]}-stream-followup-{mode}-104857600-128-20261005'
        raw = R / 'raw' / ('lavik-' + tag)
        assert not raw.exists(), raw
        argv = ['sudo', '-n', 'env', 'LAVIK_BENCH_ROOT=' + str(R), 'python3',
                str(R / 'run_with_memory_guard.py'), '--minimum-available-gib=20', '--',
                'python3', str(W / 'profile-stream-followup-allworkers.py'), 'lavik',
                '--binary=' + v['binary'], '--source-repo=' + v['source_repo'],
                '--source-commit=' + v['commit'], '--types=stream', '--sizes=104857600',
                '--fields=128', '--keys=8', '--tag=' + tag, '--mode=' + mode,
                '--levels=' + str(connections), '--seconds=30']
        subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'prepare'], check=True)
        try:
            print('START', tag, time.time(), flush=True)
            with (W / (tag + '.log')).open('w') as log:
                subprocess.run(argv, cwd=R.parents[1], stdout=log, stderr=subprocess.STDOUT, check=True)
        finally:
            subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'restore'], check=True)
        subprocess.run(['sudo', '-n', 'chown', '-R', f'{os.getuid()}:{os.getgid()}', str(raw)], check=True)
        assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
        assert json.loads((raw / 'complete.json').read_text())['failures_total'] == 0
        proof = json.loads(next(raw.glob('provenance-*.json')).read_text())
        assert proof['source_commit'] == v['commit'] and proof['sha256'] == v['sha256']
        prefix = 'stream-104857600-128'
        assert json.loads((raw / (prefix + '.validated.json')).read_text())['sample_cardinalities'] == json.loads((raw / (prefix + '.after.json')).read_text())['sample_cardinalities']
        diagnostic = raw / f'diagnostic-c{connections}'
        evidence = json.loads((diagnostic / 'profile-provenance.json').read_text())
        assert evidence['source_commit'] == v['commit'] and evidence['binary'] == v['binary']
        assert len(evidence['argv_by_tid']) >= 12
        # Keep every attached thread, including a valid zero-sample helper. Raw
        # stacks/perf stay local; later publication selects small reports explicitly.
        profiles[f'{label}-{mode}'] = {'version': v, 'tag': tag, 'directory': str(diagnostic), 'attached_tids': list(evidence['argv_by_tid'])}
        output.write_text(json.dumps({'profiles': profiles, 'method': 'Separate fresh populations, Stream XRANGE_FULL c1 or point XRANGE c2560, 30-second counter window and 25-second 99Hz task-clock/DWARF recording on each serving thread. Not a clean QPS point. CPU shares include polling/background/kernel work; IO counters are server-wide. No concurrent benchmark/build/tests.'}, indent=2) + '\n')
        print('COMPLETE', tag, time.time(), flush=True)
print('ALL_STREAM_FOLLOWUP_PROFILES_COMPLETE', time.time(), flush=True)
