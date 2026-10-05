"""Compare independent Stream follow-ups against their common runtime parent."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time
from host_execution_lock import acquire_host

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
output = W / 'stream-followup-repeats.json'
assert not output.exists(), 'inspect prior progress before restarting'

def wait_process(pid):
    proc = Path(f'/proc/{pid}/stat')
    identity = proc.read_text().split()[21] if proc.exists() else None
    print('WAIT_FOR_PROCESS', pid, identity, time.time(), flush=True)
    while identity is not None and proc.exists():
        try:
            if proc.read_text().split()[21] != identity:
                break
        except FileNotFoundError:
            break
        time.sleep(15)

wait_process(673760)
assert 'ALL_CORRECTED_STREAM_PRODUCTION_TESTS_PASS' in (W / 'stream-window-corrected-production-driver.log').read_text()
V = json.loads((W / 'stream-followup-corrected-versions.json').read_text())
expected = {
    'parent': (270, 'adec3a3414adf7b18dc304d336253258e228cb02', 37248504314),
    'window': (275, '5b9ebdedecc0cc7a3fea93fb73b1fbbb6b7186c6', 37251491010),
    'singleton': (274, '85bc7ad0d7932b27dd6784c023fcbfdbd2dd8b08', 37243195035),
}
for label, (pr, commit, run_id) in expected.items():
    assert V[label]['commit'] == commit
    while True:
        actual = json.loads(subprocess.check_output(['gh', 'pr', 'view', str(pr), '--repo', 'eloqdata/lavik', '--json', 'headRefOid']))
        assert actual['headRefOid'] == commit, (label, actual, commit)
        ci = json.loads(subprocess.check_output(['gh', 'run', 'view', str(run_id), '--repo', 'eloqdata/lavik', '--json', 'headSha,status,conclusion,jobs,url']))
        assert ci['headSha'] == commit
        assert not [j for j in ci['jobs'] if j['conclusion'] in ('failure', 'cancelled', 'timed_out', 'action_required')], (label, ci)
        if ci['status'] == 'completed':
            assert ci['conclusion'] == 'success'
            shards = [j for j in ci['jobs'] if j['name'].startswith('Test shard (')]
            assert len(shards) == 12 and all(j['conclusion'] == 'success' for j in shards)
            (W / f'stream-followup-{label}-full-ci.json').write_text(json.dumps(ci, indent=2) + '\n')
            V[label]['full_fault_enabled_ci'] = ci['url']
            break
        print('WAIT_FOR_FULL_CI', label, ci['status'], time.time(), flush=True)
        time.sleep(60)
# Independent suites share the host lock; unrelated CI failures must not
# prevent an otherwise validated candidate from being measured.
_execution_lock = acquire_host('clean-stream-followup-pairs')
for label, v in V.items():
    assert hashlib.sha256(Path(v['binary']).read_bytes()).hexdigest() == v['sha256']
    pr, commit, _ = expected[label]
    actual = json.loads(subprocess.check_output(['gh', 'pr', 'view', str(pr), '--repo', 'eloqdata/lavik', '--json', 'headRefOid']))
    assert actual['headRefOid'] == commit

rows, seeds = [], []
method = ('Three 30-second rounds, balanced version order parent/window/singleton, '
          'window/singleton/parent, singleton/parent/window. Independent candidates '
          'are compared to the same runtime parent; they are not combined. '
          'Each read round restarts all versions on one fresh parent-seeded unchanged '
          'population; writes use an independent fresh seed for every version. '
          'Large 100MiB/128B/8keys: XRANGE_FULL c1/4/16, XRANGE c2560, '
          'XADD_MAXLEN c320/5120. Small 64KiB/1024B/64keys: XRANGE_FULL c80, '
          'XRANGE c5120, XADD_MAXLEN c2560/5120. All errors retained. '
          'Exact production binaries pass native tests and full fault-enabled CI. '
          'No concurrent builds, tests, or perf on this host.')

def run(label, size, field, keys, round_, write=False, seed_tag=None, seed_only=False):
    v = V[label]
    purpose = 'write' if write else 'read'
    tag = f'{label}{v["commit"][:8]}-stream-followup-{size}-{field}-{purpose}-repeat{round_}-20261005'
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
    large = size == 104857600
    if seed_only:
        args += ['--mode=point', '--levels=1', '--seconds=1', '--seed-only']
    elif write:
        args += ['--mode=point', '--levels=' + ('320,5120' if large else '2560,5120'),
                 '--seconds=30', '--continue-on-error']
    else:
        args += ['--mode=both', '--levels=' + ('2560' if large else '5120'),
                 '--full-levels=' + ('1,4,16' if large else '80'), '--seconds=30',
                 '--reuse-seeded-data', '--seed-source-tag=' + seed_tag, '--continue-on-error']
    print('START', tag, time.time(), flush=True)
    with (W / (tag + '.log')).open('w') as log:
        subprocess.run(args, cwd=R.parents[1], stdout=log, stderr=subprocess.STDOUT, check=True)
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
        cases = ({('XADD_MAXLEN', c) for c in ([320, 5120] if large else [2560, 5120])} if write else
                 ({('XRANGE_FULL', c) for c in ([1, 4, 16] if large else [80])} | {('XRANGE', 2560 if large else 5120)}))
        assert len(results) == len(cases) and {(x['operation'], x['connections']) for x in results} == cases
        rows.extend({'round': round_, 'version': label, 'tag': tag, **x} for x in results)
        output.write_text(json.dumps({'versions': V, 'rows': rows, 'seeds': seeds, 'method': method}, indent=2) + '\n')
    print('COMPLETE', tag, time.time(), flush=True)
    return tag, before

orders = [('parent', 'window', 'singleton'), ('window', 'singleton', 'parent'), ('singleton', 'parent', 'window')]
for size, field, keys in [(104857600, 128, 8), (65536, 1024, 64)]:
    for round_, labels in enumerate(orders, 1):
        subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'prepare'], check=True)
        try:
            seed_tag, population = run('parent', size, field, keys, round_, seed_only=True)
            for label in labels:
                _, counts = run(label, size, field, keys, round_, seed_tag=seed_tag)
                assert counts == population
        finally:
            subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'restore'], check=True)
    for round_, labels in enumerate(orders, 1):
        for label in labels:
            subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'prepare'], check=True)
            try:
                run(label, size, field, keys, round_, write=True)
            finally:
                subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'restore'], check=True)
assert len(rows) == 90
print('ALL_STREAM_FOLLOWUP_REPEATS_COMPLETE', time.time(), flush=True)
