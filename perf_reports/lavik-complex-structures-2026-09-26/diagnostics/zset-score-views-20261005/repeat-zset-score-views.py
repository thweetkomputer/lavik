"""Compare score views using shared read populations and independent write controls."""
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
output = W / 'zset-score-views-repeats.json'
assert not output.exists(), 'inspect prior progress before restarting'

proc=Path('/proc/789134/stat');identity=proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_NATIVE_VALIDATION',identity,time.time(),flush=True)
while identity is not None and proc.exists():
    try:
        if proc.read_text().split()[21]!=identity:break
    except FileNotFoundError:break
    time.sleep(15)
assert 'ALL_ZSET_SCORE_VIEWS_NATIVE_TESTS_PASS' in (W/'zset-score-views-native-driver.log').read_text()
V=json.loads((W/'zset-score-views-versions.json').read_text())
expected={'parent':('4610d6077e8e32d59639a5ee88dbe8cbd305aab2','eloqdata/lavik',37258162392),
          'candidate':('9d1ffc8572f558cc139b1801488d014c2099dbfd','thweetkomputer/lavik',37272089111)}
for label,(head,repo,run_id) in expected.items():
    assert V[label]['commit']==head
    assert all(t['failures']==0 and t['tests']>0 for t in V[label]['tests'].values())
    proof=json.loads(subprocess.check_output(['gh','run','view',str(run_id),'--repo',repo,'--json','headSha,conclusion,jobs,url']))
    assert proof['headSha']==head and proof['conclusion']=='success'
    assert len(proof['jobs'])==17 and all(j['conclusion']=='success' for j in proof['jobs'])
    (W/f'zset-score-views-{label}-full-ci.json').write_text(json.dumps(proof,indent=2)+'\n')
    V[label]['full_fault_enabled_ci']=proof['url']
_execution_lock=acquire_host('clean-zset-score-views-pairs')
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
method = ('Three 30-second AB/BA/AB pairs for main4610 and score-views9d1f. '
          'Each ZSCORE read pair restarts both versions on one fresh parent-seeded '
          'population without an intervening write. Background physical changes '
          'are not excluded; this is the same logical population, not an immutable '
          'device snapshot. Independent fresh seeds for ZINCRBY write controls. '
          '100MiB/1024B/8keys and64KiB/128B/64keys, all80/320/2560/5120connections. '
          'Pipeline1. Exact native binaries and full fault-enabled CI pass first. '
          'All keys/cardinalities, binary SHA, errors and server exit checked. '
          'No concurrent builds/tests/perf. Separate diagnostics follow. No peer rerun.')

def run(label, size, field, keys, round_, write=False, seed_tag=None, seed_only=False):
    v = V[label]
    purpose = 'write' if write else 'read'
    tag = f'{label}{v["commit"][:8]}-zset-score-views-{size}-{field}-{purpose}-repeat{round_}-20261005'
    if seed_only:
        tag = 'seed-' + tag
    raw = R / 'raw' / ('lavik-' + tag)
    assert not raw.exists(), raw
    helper = 'run-zset-score-controls.py'
    args = ['sudo', '-n', 'env', 'LAVIK_BENCH_ROOT=' + str(R), 'python3',
            str(R / 'run_with_memory_guard.py'), '--minimum-available-gib=20', '--',
            'python3', str(W / helper), 'lavik', '--binary=' + v['binary'],
            '--source-repo=' + v['source_repo'], '--source-commit=' + v['commit'],
            '--types=zset', '--sizes=' + str(size), '--fields=' + str(field),
            '--keys=' + str(keys), '--tag=' + tag]
    if seed_only:
        args += ['--mode=point', '--levels=1', '--seconds=1', '--seed-only']
    elif write:
        args += ['--mode=point', '--levels=80,320,2560,5120', '--write-only',
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
        cases = {('ZINCRBY' if write else 'ZSCORE', c) for c in [80,320,2560,5120]}
        assert len(results) == len(cases) and {(x['operation'], x['connections']) for x in results} == cases
        rows.extend({'round': round_, 'version': label, 'tag': tag, **x} for x in results)
        output.write_text(json.dumps({'versions': V, 'rows': rows, 'seeds': seeds, 'method': method}, indent=2) + '\n')
        assert not any('error' in row for row in results), 'retain failed point before retrying'
    assert json.loads((raw/'complete.json').read_text())['failures_total']==0
    print('COMPLETE', tag, time.time(), flush=True)
    return tag, before

orders = [('parent', 'candidate'), ('candidate', 'parent'), ('parent', 'candidate')]
for size, field, keys in [(104857600, 1024, 8), (65536, 128, 64)]:
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
assert len(rows) == 96
print('ALL_ZSET_SCORE_VIEWS_REPEATS_COMPLETE', time.time(), flush=True)
