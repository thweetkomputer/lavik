"""Compare independent Stream follow-ups against their common runtime parent."""
from pathlib import Path
import hashlib
import json
import os
import signal
import subprocess
import time
from host_execution_lock import acquire_host

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
output = W / 'stream-window-followup-repeats.json'
assert not output.exists(), 'inspect prior progress before restarting'

# Prioritize the already queued combined build before another long sweep.
waiters=[]
for pid in [740651,761017]:
    proc=Path('/proc')/str(pid)/'stat'
    waiters.append((pid,proc,proc.read_text().split()[21] if proc.exists() else None))
for pid,proc,generation in waiters:
    print('WAIT_FOR_VALIDATION',pid,generation,time.time(),flush=True)
    while generation is not None and proc.exists():
        try:
            if proc.read_text().split()[21]!=generation:break
        except FileNotFoundError:break
        time.sleep(15)
assert 'ALL_STREAM_WINDOW_BLOCKING_TESTS_PASS' in (W/'stream-window-blocking-validation-driver.log').read_text()
assert 'ALL_STREAM_WINDOW_SUITE_ORDER_DIAGNOSTICS_PASS' in (W/'stream-window-suite-order-diagnostic-corrected-driver.log').read_text()
suite=json.loads((W/'stream-window-suite-order-diagnostics.json').read_text())
assert len(suite['rows'])==2 and all(r['returncode']==0 for r in suite['rows'])
blocking=json.loads((W/'stream-window-blocking-validation.json').read_text())
assert len(blocking['rows'])==2 and all(r['exit_code']==0 for r in blocking['rows'])
V={label:dict(suite['versions'][label]) for label in ['parent','window']}
assert V['window']['sha256']==blocking['version']['sha256']
expected = {
    'parent': (270, 'adec3a3414adf7b18dc304d336253258e228cb02', 37248504314),
    'window': (275, '5b9ebdedecc0cc7a3fea93fb73b1fbbb6b7186c6', 37251491010),
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
            (W / f'stream-window-followup-{label}-full-ci.json').write_text(json.dumps(ci, indent=2) + '\n')
            V[label]['full_fault_enabled_ci'] = ci['url']
            break
        print('WAIT_FOR_FULL_CI', label, ci['status'], time.time(), flush=True)
        time.sleep(60)
# Independent suites share the host lock; unrelated CI failures must not
# prevent an otherwise validated candidate from being measured.
_execution_lock = acquire_host('clean-stream-window-pairs')
for label, v in V.items():
    assert hashlib.sha256(Path(v['binary']).read_bytes()).hexdigest() == v['sha256']
    pr, commit, _ = expected[label]
    actual = json.loads(subprocess.check_output(['gh', 'pr', 'view', str(pr), '--repo', 'eloqdata/lavik', '--json', 'headRefOid']))
    assert actual['headRefOid'] == commit

def terminate(_signal,_frame):raise SystemExit('benchmark interrupted')
signal.signal(signal.SIGTERM,terminate)
def execute(argv,log=None):
    child=subprocess.Popen(argv,cwd=R.parents[1],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        code=child.wait()
        if code:raise subprocess.CalledProcessError(code,argv)
    except BaseException:
        # The memory guard starts a separate session for its runner/server.
        # Remember descendant groups before interrupting the guard, so fallback
        # cleanup cannot leave that separate session holding an SPDK device.
        owned={child.pid};groups={child.pid}
        processes={}
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():continue
            try:
                fields=(entry/'stat').read_text().rsplit(')',1)[1].split()
                processes[int(entry.name)]=(int(fields[1]),int(fields[2]))
            except (FileNotFoundError,PermissionError,ProcessLookupError):continue
        while True:
            more={pid for pid,(parent,_) in processes.items() if parent in owned}-owned
            if not more:break
            owned.update(more)
        groups.update(group for pid,(_,group) in processes.items() if pid in owned)
        groups.discard(os.getpgrp())
        if child.poll() is None:
            subprocess.run(['sudo','-n','kill','-INT','--',f'-{child.pid}'],check=False)
            try:child.wait(timeout=45)
            except subprocess.TimeoutExpired:pass
        for group in groups:
            subprocess.run(['sudo','-n','kill','-KILL','--',f'-{group}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        child.wait();raise

rows, seeds = [], []
method = ('Three 30-second pairs parent/window, window/parent, parent/window. '
          'PR275window5b versus exactruntimeparentadec. Original production timeout '
          'was not reproduced in the same-order suite and remains unexplained; '
          'all required current native suites and full CI precede measurement. '
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
    tag = f'{label}{v["commit"][:8]}-stream-window-followup-{size}-{field}-{purpose}-repeat{round_}-20261005'
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
        execute(args,log)
    subprocess.run(['sudo', '-n', 'chown', '-R', f'{os.getuid()}:{os.getgid()}', str(raw)], check=True)
    assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
    proof = json.loads(next(raw.glob('provenance-*.json')).read_text())
    assert proof['source_commit'] == v['commit'] and proof['sha256'] == v['sha256']
    prefix = f'stream-{size}-{field}'
    before = json.loads((raw / (prefix + '.validated.json')).read_text())['sample_cardinalities']
    after = json.loads((raw / (prefix + '.after.json')).read_text())['sample_cardinalities']
    assert len(before)==keys and all(count==size//field for count in before.values())
    if not write:
        assert before == after
    else:
        assert before.keys()==after.keys() and all(before[key]<=after[key]<=before[key]+100 for key in before)
    if seed_only:
        seeds.append({'round': round_, 'tag': tag, 'cardinalities': before})
    else:
        results = [json.loads(f.read_text()) for f in list(raw.glob('*.result.json')) + list(raw.glob('*.error.json'))]
        cases = ({('XADD_MAXLEN', c) for c in ([320, 5120] if large else [2560, 5120])} if write else
                 ({('XRANGE_FULL', c) for c in ([1, 4, 16] if large else [80])} | {('XRANGE', 2560 if large else 5120)}))
        assert len(results) == len(cases) and {(x['operation'], x['connections']) for x in results} == cases
        rows.extend({'round': round_, 'version': label, 'tag': tag, **x} for x in results)
        output.write_text(json.dumps({'versions': V, 'rows': rows, 'seeds': seeds, 'method': method}, indent=2) + '\n')
        assert not any('error' in row for row in results), 'retain failed point before retrying'
    print('COMPLETE', tag, time.time(), flush=True)
    return tag, before

orders = [('parent', 'window'), ('window', 'parent'), ('parent', 'window')]
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
assert len(rows) == 60
print('ALL_STREAM_WINDOW_FOLLOWUP_REPEATS_COMPLETE', time.time(), flush=True)
