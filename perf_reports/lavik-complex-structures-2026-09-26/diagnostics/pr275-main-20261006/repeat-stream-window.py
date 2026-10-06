"""Compare independent Stream follow-ups against their common runtime parent."""
from pathlib import Path
import hashlib
import json
import os
import signal
import subprocess
import time
import sys
sys.path.insert(0,'/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
output = W / 'pr275-rebased-repeats.json'
assert not output.exists(), 'inspect prior progress before restarting'

V=json.loads((W/'pr275-versions.json').read_text())
assert 'ALL_PR275_NATIVE_TESTS_PASS' in (W/'native-driver.log').read_text()
_execution_lock=acquire_host('rebased-pr275-clean-pairs')
for label,v in V.items():
    assert hashlib.file_digest(Path(v['binary']).open('rb'),'sha256').hexdigest()==v['sha256']
assert V['parent']['commit']=='d88a5e8fdcc5702272b26f9853f4baad7a146988'
assert V['window']['commit']=='fd2972b0f9ea9ccda5d231dd0d4984d9ee1b44e5'

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
          'Rebased PR275 eccea5c7 versus main d88a5e8f. Original production timeout '
          'was not reproduced in the same-order suite and remains unexplained; '
          'Current native suites and three repeats of both previous timeout cases precede measurement. CI status is recorded separately. '
          'Each read round restarts all versions on one fresh parent-seeded unchanged '
          'population; writes use an independent fresh seed for every version. '
          'Large 100MiB/128B/8keys: XRANGE_FULL c1/4/16, XRANGE c2560, '
          'XADD_MAXLEN c320/5120. Small 64KiB/1024B/64keys: XRANGE_FULL c80, '
          'XRANGE c5120, XADD_MAXLEN c2560/5120. All errors retained. '
          'Exact production binaries pass native tests; full fault-enabled CI is separate. '
          'No concurrent builds, tests, or perf on this host.')

def run(label, size, field, keys, round_, write=False, seed_tag=None, seed_only=False):
    v = V[label]
    purpose = 'write' if write else 'read'
    tag = f'{label}{v["commit"][:8]}-pr275-rebased-{size}-{field}-{purpose}-repeat{round_}-20261006'
    if seed_only:
        tag = 'seed-' + tag
    raw = R / 'raw' / ('lavik-' + tag)
    assert not raw.exists(), raw
    helper = 'run-write-only.py' if write else 'run-stream-reply-reads.py'
    args = ['sudo', '-n', 'env', 'LAVIK_BENCH_ROOT=' + str(R), 'unshare', '--mount', '--propagation', 'private', 'python3', str(W/'private-tmp-exec.py'), str(W/'benchmark-tmp'), '0', '0', 'python3',
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
            subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'restore'], check=True) if (R/'spdk-ready.json').exists() else None
    for round_, labels in enumerate(orders, 1):
        for label in labels:
            subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'prepare'], check=True)
            try:
                run(label, size, field, keys, round_, write=True)
            finally:
                subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'restore'], check=True) if (R/'spdk-ready.json').exists() else None
assert len(rows) == 60
print('ALL_STREAM_WINDOW_FOLLOWUP_REPEATS_COMPLETE', time.time(), flush=True)
