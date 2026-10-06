"""Compare score views using shared read populations and independent write controls."""
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
output = W / 'pr283-repeats.json'
assert not output.exists(), 'inspect prior progress before restarting'

launch=json.loads((W/'native-launch.json').read_text())
proc=Path('/proc')/str(launch['pid'])/'stat';identity=launch['start_ticks']
print('WAIT_FOR_NATIVE_VALIDATION',identity,time.time(),flush=True)
while identity is not None and proc.exists():
    try:
        if proc.read_text().split()[21]!=identity:break
    except FileNotFoundError:break
    time.sleep(15)
assert 'ALL_PR283_NATIVE_TESTS_PASS' in (W/'native-driver.log').read_text()
V=json.loads((W/'pr283-versions.json').read_text())
expected=launch['expected']
for label, head in expected.items():
    assert V[label]['commit']==head
    assert all(t['failures']==0 and t.get('errors',0)==0 and t['tests']>0 for t in V[label]['tests'].values())
_execution_lock=acquire_host('clean-pr283-pairs')
for v in V.values():
    with Path(v['binary']).open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==v['sha256']

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
method = ('Three 30-second AB/BA/AB pairs of main5a3903d9 and rebased PR283ace4198b. '
          'Matched native production builds, no concurrent builds/tests/perf. '
          'ZSCORE read pairs share freshly parent-seeded logical populations with separate restarts. '
          'ZINCRBY and ZADD use independent fresh populations per version. '
          'Sizes 100MiB/1024B/8keys and64KiB/128B/64keys. ZSCORE/ZINCRBY c80/320/2560/5120; '
          'ZADD CH toggles scores0/1 at c80/5120 with distinct and all-zero initial scores. '
          'Eight sampled members; concurrent ZADD requests can be no-ops. '
          'No cardinality growth. Physical background changes and random digest seeds remain. '
          'Pipeline1. Full CI is separate from native correctness checks. No peer rerun.')

def run(label, size, field, keys, round_, write=False, seed_tag=None, seed_only=False, operation=None, layout="distinct"):
    v = V[label]
    operation = operation or ('ZINCRBY' if write else 'ZSCORE')
    purpose = operation.lower()+'-'+layout
    tag = f'{label}{v["commit"][:8]}-pr283-{size}-{field}-{purpose}-repeat{round_}-20261006'
    if seed_only:
        tag = 'seed-' + tag
    raw = R / 'raw' / ('lavik-' + tag)
    assert not raw.exists(), raw
    helper = 'run-zset-controls.py'
    args = ['sudo', '-n', 'env', 'LAVIK_BENCH_ROOT=' + str(R), 'PR283_OPERATION='+('SEED' if seed_only else operation), 'PR283_LAYOUT='+layout, 'python3',
            str(R / 'run_with_memory_guard.py'), '--minimum-available-gib=20', '--',
            'python3', str(W / helper), 'lavik', '--binary=' + v['binary'],
            '--source-repo=' + v['source_repo'], '--source-commit=' + v['commit'],
            '--types=zset', '--sizes=' + str(size), '--fields=' + str(field),
            '--keys=' + str(keys), '--tag=' + tag]
    if seed_only:
        args += ['--mode=point', '--levels=1', '--seconds=1']
    elif write:
        args += ['--mode=point', '--levels='+('80,5120' if operation=='ZADD' else '80,320,2560,5120'),
                 '--seconds=30', '--continue-on-error']
    else:
        args += ['--mode=point', '--levels=80,320,2560,5120', '--seconds=30',
                 '--reuse-seeded-data', '--seed-source-tag=' + seed_tag, '--continue-on-error']
    print('START', tag, time.time(), flush=True)
    with (W / (tag + '.log')).open('w') as log:
        execute(args,log)
    subprocess.run(['sudo', '-n', 'chown', '-R', f'{os.getuid()}:{os.getgid()}', str(raw)], check=True)
    assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
    proof = json.loads(next(raw.glob('provenance-*.json')).read_text())
    assert proof['source_commit'] == v['commit'] and proof['sha256'] == v['sha256']
    prefix = f'zset-{size}-{field}'
    before = json.loads((raw / (prefix + '.validated.json')).read_text())['sample_cardinalities']
    after = json.loads((raw / (prefix + '.after.json')).read_text())['sample_cardinalities']
    assert set(before)=={f'complex_{i}' for i in range(1,keys+1)} and all(count==size//field for count in before.values())
    assert before == after
    if seed_only:
        seeds.append({'round': round_, 'tag': tag, 'cardinalities': before})
    else:
        results = [json.loads(f.read_text()) for f in list(raw.glob('*.result.json')) + list(raw.glob('*.error.json'))]
        cases = {(operation, c) for c in ([80,5120] if operation=='ZADD' else [80,320,2560,5120])}
        assert len(results) == len(cases) and {(x['operation'], x['connections']) for x in results} == cases
        rows.extend({'round': round_, 'version': label, 'tag': tag, 'layout':layout, **x} for x in results)
        output.write_text(json.dumps({'versions': V, 'rows': rows, 'seeds': seeds, 'method': method}, indent=2) + '\n')
        assert not any('error' in row for row in results), 'retain failed point before retrying'
    assert json.loads((raw/'complete.json').read_text())['failures_total']==0
    print('COMPLETE', tag, time.time(), flush=True)
    return tag, before

orders = [('parent', 'candidate'), ('candidate', 'parent'), ('parent', 'candidate')]
for size, field, keys in [(104857600, 1024, 8), (65536, 128, 64)]:
    for round_, labels in enumerate(orders, 1):
        subprocess.run(['sudo', '-n', 'python3', '/mnt/dev/lavik-complex-iterations-20261004/host.py', 'prepare'], check=True)
        try:
            seed_tag, population = run('parent', size, field, keys, round_, seed_only=True)
            for label in labels:
                _, counts = run(label, size, field, keys, round_, seed_tag=seed_tag)
                assert counts == population
        finally:
            subprocess.run(['sudo', '-n', 'python3', '/mnt/dev/lavik-complex-iterations-20261004/host.py', 'restore'], check=True)
    for operation,layout in [('ZINCRBY','distinct'),('ZADD','distinct'),('ZADD','ties')]:
        for round_, labels in enumerate(orders, 1):
            for label in labels:
                subprocess.run(['sudo', '-n', 'python3', '/mnt/dev/lavik-complex-iterations-20261004/host.py', 'prepare'], check=True)
                try:
                    run(label, size, field, keys, round_, write=True, operation=operation, layout=layout)
                finally:
                    subprocess.run(['sudo', '-n', 'python3', '/mnt/dev/lavik-complex-iterations-20261004/host.py', 'restore'], check=True)
assert len(rows) == 144
print('ALL_PR283_REPEATS_COMPLETE', time.time(), flush=True)
