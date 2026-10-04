"""Recheck observed control regressions after the exact read-pair driver exits."""
from pathlib import Path
import json
import os
import subprocess
import time

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
V = json.loads((W / 'stream-reply-versions.json').read_text())
output = W / 'stream-reply-control-repeats.json'
assert not output.exists(), 'inspect existing progress before restarting'
proc = Path('/proc/582559/stat')
identity = proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_READ_PAIRS', identity, time.time(), flush=True)
while proc.exists() and identity is not None:
    try:
        if proc.read_text().split()[21] != identity:
            break
    except FileNotFoundError:
        break
    time.sleep(15)
assert 'ALL_STREAM_REPLY_READ_REPEATS_COMPLETE' in (W / 'stream-reply-read-repeat-driver.log').read_text()
reads = json.loads((W / 'stream-reply-read-repeats.json').read_text())
assert len(reads['rows']) == 24 and reads['candidate'] == V['candidate']
rows = []
seeds = []
method = ('Three 30-second pairs A/B, B/A, A/B per scenario. Small 64KiB/1024B reads: '
          'both immutable binaries restart the same freshly seeded main population, full XRANGE c80 '
          'and point XRANGE c5120. Small writes: XADD_MAXLEN c2560/5120, independent fresh seed '
          'per binary. Large 100MiB/128B writes: XADD_MAXLEN c320/5120, independent fresh seed '
          'per binary. All raw results/errors retained. No builds, tests or perf overlap.')

def run(label, scenario, round_, seed_tag=None, seed_only=False):
    size, field, keys, write = scenario
    v = V[label]
    purpose = 'write' if write else 'read'
    tag = f'{label}{v["commit"][:8]}-stream-reply-control-{size}-{field}-{purpose}-repeat{round_}-20261004'
    if seed_only:
        tag = 'seed-' + tag
    raw = R / 'raw' / ('lavik-' + tag)
    assert not raw.exists(), raw
    helper = 'run-write-only.py' if write else 'run-stream-reply-reads.py'
    args = ['sudo', '-n', 'env', 'LAVIK_BENCH_ROOT=' + str(R), 'python3',
            str(R / 'run_with_memory_guard.py'), '--minimum-available-gib=20', '--',
            'python3', str(W / helper), 'lavik', '--binary=' + v['binary'],
            '--source-repo=' + v['source_repo'], '--source-commit=' + v['commit'],
            '--types=stream', '--sizes=' + str(size), '--fields=' + str(field),
            '--keys=' + str(keys), '--tag=' + tag]
    if seed_only:
        args += ['--mode=point', '--levels=1', '--seconds=1', '--seed-only']
    elif write:
        args += ['--mode=point', '--levels=' + ('320,5120' if size == 104857600 else '2560,5120'),
                 '--seconds=30', '--continue-on-error']
    else:
        args += ['--mode=both', '--levels=5120', '--full-levels=80', '--seconds=30',
                 '--reuse-seeded-data', '--seed-source-tag=' + seed_tag, '--continue-on-error']
    print('START', tag, time.time(), flush=True)
    with (W / (tag + '.log')).open('w') as f:
        subprocess.run(args, cwd=R.parents[1], stdout=f, stderr=subprocess.STDOUT, check=True)
    subprocess.run(['sudo', '-n', 'chown', '-R', f'{os.getuid()}:{os.getgid()}', str(raw)], check=True)
    assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
    proof = json.loads(next(raw.glob('provenance-*.json')).read_text())
    assert proof['source_commit'] == v['commit'] and proof['sha256'] == v['sha256']
    prefix = f'stream-{size}-{field}'
    before = json.loads((raw / (prefix + '.validated.json')).read_text())['sample_cardinalities']
    after = json.loads((raw / (prefix + '.after.json')).read_text())['sample_cardinalities']
    if not write:
        assert before == after
    if seed_only:
        seeds.append({'round': round_, 'tag': tag, 'cardinalities': before})
    else:
        results = [json.loads(f.read_text()) for f in list(raw.glob('*.result.json')) + list(raw.glob('*.error.json'))]
        expected = {('XADD_MAXLEN', c) for c in ([320, 5120] if size == 104857600 else [2560, 5120])} if write else {('XRANGE_FULL', 80), ('XRANGE', 5120)}
        assert len(results) == 2 and {(x['operation'], x['connections']) for x in results} == expected
        for result in results:
            rows.append({'round': round_, 'version': label, 'tag': tag, **result})
        output.write_text(json.dumps({'main': V['main'], 'candidate': V['candidate'], 'rows': rows,
                                      'seeds': seeds, 'method': method}, indent=2) + '\n')
    print('COMPLETE', tag, time.time(), flush=True)
    return tag, before

for scenario in [(65536, 1024, 64, False), (65536, 1024, 64, True), (104857600, 128, 8, True)]:
    for round_, labels in enumerate([['main', 'candidate'], ['candidate', 'main'], ['main', 'candidate']], 1):
        if not scenario[3]:
            subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'prepare'], check=True)
            try:
                seed_tag, population = run('main', scenario, round_, seed_only=True)
                for label in labels:
                    _, counts = run(label, scenario, round_, seed_tag=seed_tag)
                    assert counts == population
            finally:
                subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'restore'], check=True)
        else:
            for label in labels:
                subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'prepare'], check=True)
                try:
                    run(label, scenario, round_)
                finally:
                    subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'restore'], check=True)
assert len(rows) == 36
print('ALL_STREAM_REPLY_CONTROL_REPEATS_COMPLETE', time.time(), flush=True)
