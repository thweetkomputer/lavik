"""Compare existing inline-manifest and decoded-digest candidates against their common parent."""
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
output = W / 'grouped-lookup-repeats.json'
assert not output.exists(), 'inspect prior progress before restarting'
# Freeze the scripts while queued as well as the eventual server binaries.
script_paths=[Path(__file__), W/'run-zset-score-controls.py', R/'run.py', R/'run_with_memory_guard.py', W/'host.py']
script_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in script_paths}

# Capture process generations before waiting; PID reuse cannot extend a dependency.
waiting = {}
for pid in [851633, 795645]:
    proc = Path('/proc') / str(pid) / 'stat'
    if proc.exists(): waiting[pid] = proc.read_text().rsplit(')', 1)[1].split()[19]
print('WAIT_FOR_NATIVE_AND_WORKER_CONTROLS', waiting, time.time(), flush=True)
for pid, identity in waiting.items():
    proc = Path('/proc') / str(pid) / 'stat'
    while proc.exists():
        try:
            if proc.read_text().rsplit(')', 1)[1].split()[19] != identity: break
        except FileNotFoundError: break
        time.sleep(15)
assert 'ALL_GROUPED_LOOKUP_NATIVE_TESTS_PASS' in (W/'grouped-lookup-native-driver.log').read_text()
V=json.loads((W/'grouped-lookup-native-versions.json').read_text())
expected={
    'parent':('067c75891f819831620e277eac0592c360f8b585',37241392671),
    'inline':('2e6e4f3559d284e6fe5d0dddc7eb1de5929761ae',37241742696),
    'decoded':('8babe581213f2cd781f13665a45fdbf1012cf449',37241670139),
}
assert set(V)==set(expected)

def cache_values(path):
    return {line.split('=',1)[0].split(':',1)[0]:line.split('=',1)[1]
            for line in path.read_text().splitlines()
            if line and not line.startswith(('#','//')) and '=' in line}
cache_paths={'parent':W/'zset-source-reuse-previous-CMakeCache.txt',
             **{label:W/f'grouped-lookup-{label}-CMakeCache.txt' for label in ['inline','decoded']}}
cache_keys=['CMAKE_BUILD_TYPE','CMAKE_CXX_COMPILER','CMAKE_CXX_FLAGS',
            'CMAKE_CXX_FLAGS_RELWITHDEBINFO','CMAKE_INTERPROCEDURAL_OPTIMIZATION',
            'LAVIK_KERNEL_BYPASS','LAVIK_ENABLE_TEST_FAULTS','BUILD_TESTING','LAVIK_MARCH']
reference=cache_values(cache_paths['parent'])
for label,(head,run_id) in expected.items():
    assert V[label]['commit']==head
    assert V[label]['bycorf_commit']=='62509c93d40c2480f5046b71454db6cf95801b04'
    assert all(t['failures']==0 and t['tests']>0 for t in V[label]['tests'].values())
    values=cache_values(cache_paths[label])
    assert all(values.get(k)==reference.get(k) for k in cache_keys)
    assert values['BUILD_TESTING']=='OFF' and values['LAVIK_ENABLE_TEST_FAULTS']=='OFF'
    assert values['LAVIK_MARCH']=='native'
    V[label]['comparison_build_options']={k:values.get(k) for k in cache_keys}
    proof=json.loads(subprocess.check_output(['gh','run','view',str(run_id),'--repo','eloqdata/lavik','--json','headSha,conclusion,jobs,url']))
    assert proof['headSha']==head and proof['conclusion']=='success'
    assert len(proof['jobs'])==17 and all(j['conclusion']=='success' for j in proof['jobs'])
    V[label]['full_fault_enabled_ci']=proof['url']
_execution_lock=acquire_host('clean-grouped-lookup-three-version-controls')
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in script_hashes.items())
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
method = ('Three 30-second rotations parent/inline/decoded, inline/decoded/parent, '
          'decoded/parent/inline on fixed parent067, PR2712e6 and PR2728b. '
          'Each version occupies each position once; pair each candidate with the '
          'common parent within each round. Each ZSCORE rotation restarts all three '
          'versions on one fresh parent-seeded logical population without an '
          'intervening write; background physical changes are not excluded. '
          'Independent fresh seeds for ZINCRBY. 100MiB/1024B/8keys and '
          '64KiB/128B/64keys at320/5120connections, pipeline1. Full CI and native '
          'tests pass first; native build options and exact binary hashes checked. '
          'All keys/cardinalities, errors and server exit checked. No concurrent '
          'builds/tests/perf, no peer rerun and no combined-candidate gain claim.')

def run(label, size, field, keys, round_, write=False, seed_tag=None, seed_only=False):
    v = V[label]
    purpose = 'write' if write else 'read'
    tag = f'{label}{v["commit"][:8]}-grouped-lookup-{size}-{field}-{purpose}-repeat{round_}-20261005'
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
        args += ['--mode=point', '--levels=320,5120', '--write-only',
                 '--seconds=30', '--continue-on-error']
    else:
        args += ['--mode=point', '--levels=320,5120', '--seconds=30',
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
        assert not list(raw.glob('*.result.json')) and not list(raw.glob('*.error.json'))
        seeds.append({'round': round_, 'tag': tag, 'cardinalities': before})
    else:
        results = [json.loads(f.read_text()) for f in list(raw.glob('*.result.json')) + list(raw.glob('*.error.json'))]
        cases = {('ZINCRBY' if write else 'ZSCORE', c) for c in [320,5120]}
        assert len(results) == len(cases) and {(x['operation'], x['connections']) for x in results} == cases
        rows.extend({'round': round_, 'version': label, 'tag': tag, **x} for x in results)
        output.write_text(json.dumps({'versions': V, 'rows': rows, 'seeds': seeds, 'method': method, 'script_sha256':script_hashes}, indent=2) + '\n')
        assert not any('error' in row for row in results), 'retain failed point before retrying'
        assert all(row['seconds']==30 and row['requests']>0 and row['keys']==keys
                   and row['logical_bytes']==size and row['field_bytes']==field
                   and row['entries_per_key']==size//field for row in results)
    assert json.loads((raw/'complete.json').read_text())['failures_total']==0
    print('COMPLETE', tag, time.time(), flush=True)
    return tag, before

orders = [('parent', 'inline', 'decoded'), ('inline', 'decoded', 'parent'), ('decoded', 'parent', 'inline')]
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
assert len(rows) == 72
print('ALL_GROUPED_LOOKUP_REPEATS_COMPLETE', time.time(), flush=True)
