"""Diagnose the smaller-Hash HSET regression after the original four large-object profiles."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time
from host_execution_lock import acquire_host
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
output=W/'hash-route-small-hash-profiles.json'
assert not output.exists()
script_paths=[Path(__file__),W/'profile-hash-route-allworkers.py',R/'run.py',
              Path('/mnt/dev/lavik-test-data-20261001/profile-lset-deep.py')]
script_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in script_paths}
proc=Path('/proc/761040/stat');identity=proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_ORIGINAL_HASH_ROUTE_PROFILES',identity,time.time(),flush=True)
while identity is not None and proc.exists():
    try:
        if proc.read_text().split()[21]!=identity:break
    except FileNotFoundError:break
    time.sleep(15)
assert 'ALL_HASH_ROUTE_REPLACE_REPEATS_COMPLETE' in (W/'hash-route-replace-repeat-resume-driver.log').read_text()
assert 'ALL_HASH_ROUTE_REPLACE_PROFILES_COMPLETE' in (W/'hash-route-replace-profile-resume-driver.log').read_text()
repeats=json.loads((W/'hash-route-replace-repeats.json').read_text())
assert len(repeats['rows'])==144 and not any('error' in row for row in repeats['rows'])
V=json.loads((W/'hash-route-replace-versions-corrected.json').read_text())
for label,head in [('parent','19496654cc43b21df11fb59be60e174dc4c89dbc'),('candidate','27c65ff9c2ceaaacea4c93f42ffed01dce529b8f')]:
    assert V[label]['commit']==head
    assert V[label]['bycorf_commit']=='62509c93d40c2480f5046b71454db6cf95801b04'
    assert all(V[label][k]==repeats['versions'][label][k] for k in ['commit','sha256','binary'])
_execution_lock=acquire_host('hash-route-small-hash-perf')
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in script_hashes.items())
for version in V.values():
    with Path(version['binary']).open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==version['sha256']
def terminate(_signal,_frame):raise SystemExit('benchmark interrupted')
signal.signal(signal.SIGTERM,terminate)
def run(argv,log=None):
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
profiles={}
for kind in ['hash']:
    fixture=Path(repeats['fixtures'][f'{kind}-1048576-128']['path'])
    for label in ['parent','candidate']:
        v=V[label]
        tag=f'diagnostic-{label}{v["commit"][:8]}-hash-route-{kind}-1048576-128-k50000-c320-20261005'
        seed='seed-'+tag;raw=R/'raw'/('lavik-'+tag)
        assert not raw.exists() and not (R/'raw'/('lavik-'+seed)).exists()
        base=['lavik','--binary='+v['binary'],'--source-repo='+v['source_repo'],'--source-commit='+v['commit'],'--types='+kind,'--sizes=1048576','--fields=128','--keys=50000']
        guard=['sudo','-n','env','LAVIK_BENCH_ROOT='+str(R),'python3',str(R/'run_with_memory_guard.py'),'--minimum-available-gib=20','--','python3']
        run(['sudo','-n','python3',str(W/'host.py'),'prepare'])
        try:
            print('START',tag,time.time(),flush=True)
            with (W/(tag+'.log')).open('w') as log:
                run(guard+[str(R/'run.py')]+base+['--tag='+seed,'--seed-dump-path='+str(fixture),'--fill-workers=8','--mode=full','--levels=1','--seconds=1'],log)
                run(guard+[str(W/'profile-hash-route-allworkers.py')]+base+['--tag='+tag,'--reuse-seeded-data','--seed-source-tag='+seed,'--mode=point','--levels=320','--seconds=30'],log)
        finally:run(['sudo','-n','python3',str(W/'host.py'),'restore'])
        for current in [R/'raw'/('lavik-'+seed),raw]:
            run(['sudo','-n','chown','-R',f'{os.getuid()}:{os.getgid()}',str(current)])
            assert json.loads((current/'server-exit.json').read_text())['code']==0
            assert json.loads((current/'complete.json').read_text())['failures_total']==0
            proof=json.loads(next(current.glob('provenance-*.json')).read_text())
            assert proof['source_commit']==v['commit'] and proof['sha256']==v['sha256']
        prefix=f'{kind}-1048576-128'
        before=json.loads((raw/(prefix+'.validated.json')).read_text())['sample_cardinalities']
        after=json.loads((raw/(prefix+'.after.json')).read_text())['sample_cardinalities']
        assert set(before)==set(after)=={f'complex_{i}' for i in range(1,50001)}
        assert all(count==8192 for count in before.values())
        if kind=='hash':assert before==after
        else:assert all(after[key] in (before[key],before[key]+1) for key in before)
        diagnostic=raw/'diagnostic-c320'
        results=[json.loads(path.read_text()) for path in diagnostic.glob('*.result.json')]
        assert len(results)==1 and results[0]['operation']=='HSET' and results[0]['connections']==320
        assert results[0]['seconds']==30 and results[0]['keys']==50000
        assert not list(diagnostic.glob('*.error.json'))
        evidence=json.loads((diagnostic/'profile-provenance.json').read_text())
        assert evidence['source_commit']==v['commit'] and evidence['binary']==v['binary']
        assert len(evidence['argv_by_tid'])>=12
        profiles[f'{label}-{kind}']={'version':v,'tag':tag,'directory':str(diagnostic),'attached_tids':list(evidence['argv_by_tid'])}
        output.write_text(json.dumps({'profiles':profiles,'script_sha256':script_hashes,'method':'Independent fresh50000key/1MiB/128B restored populations, HSET c320; diagnostic for smaller-Hash QPS/p99 regressions. No new clean performance comparison, 30-second command/counter interval and25-second99Hz task-clock/DWARF per serving thread. Keep zero-sample auxiliary threads; rawperf/stacks stay local. CPU shares include polling/background/kernel work; these diagnostic QPS values never enter the clean comparisons. No concurrent host builds/tests/benchmarks.'},indent=2)+'\n')
        print('COMPLETE',tag,time.time(),flush=True)
assert len(profiles)==2
print('ALL_HASH_ROUTE_SMALL_HASH_PROFILES_COMPLETE',time.time(),flush=True)
