"""Separate worker CPU/IO profiles after the 144 clean Hash/Set observations."""
from pathlib import Path
import json,os,signal,subprocess,time
from host_execution_lock import acquire_host
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
output=W/'hash-route-replace-profiles.json'
assert not output.exists()
proc=Path('/proc/761025/stat');identity=proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_HASH_ROUTE_PAIRS',identity,time.time(),flush=True)
while identity is not None and proc.exists():
    try:
        if proc.read_text().split()[21]!=identity:break
    except FileNotFoundError:break
    time.sleep(15)
assert 'ALL_HASH_ROUTE_REPLACE_REPEATS_COMPLETE' in (W/'hash-route-replace-repeat-resume-driver.log').read_text()
repeats=json.loads((W/'hash-route-replace-repeats.json').read_text())
assert len(repeats['rows'])==144 and not any('error' in row for row in repeats['rows'])
V=repeats['versions']
_execution_lock=acquire_host('hash-route-replace-perf')
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
for kind in ['hash','set']:
    fixture=Path(repeats['fixtures'][f'{kind}-104857600-1024']['path'])
    for label in ['parent','candidate']:
        v=V[label]
        tag=f'diagnostic-{label}{v["commit"][:8]}-hash-route-{kind}-104857600-1024-k500-c320-20261005'
        seed='seed-'+tag;raw=R/'raw'/('lavik-'+tag)
        assert not raw.exists() and not (R/'raw'/('lavik-'+seed)).exists()
        base=['lavik','--binary='+v['binary'],'--source-repo='+v['source_repo'],'--source-commit='+v['commit'],'--types='+kind,'--sizes=104857600','--fields=1024','--keys=500']
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
        prefix=f'{kind}-104857600-1024'
        before=json.loads((raw/(prefix+'.validated.json')).read_text())['sample_cardinalities']
        after=json.loads((raw/(prefix+'.after.json')).read_text())['sample_cardinalities']
        assert before.keys()==after.keys()
        if kind=='hash':assert before==after
        else:assert all(after[key] in (before[key],before[key]+1) for key in before)
        diagnostic=raw/'diagnostic-c320'
        evidence=json.loads((diagnostic/'profile-provenance.json').read_text())
        assert evidence['source_commit']==v['commit'] and evidence['binary']==v['binary']
        assert len(evidence['argv_by_tid'])>=12
        profiles[f'{label}-{kind}']={'version':v,'tag':tag,'directory':str(diagnostic),'attached_tids':list(evidence['argv_by_tid'])}
        output.write_text(json.dumps({'profiles':profiles,'method':'Independent fresh500key/100MiB/1024B restored populations, HSET or SADD_SREM c320, 30-second command/counter interval and25-second99Hz task-clock/DWARF per serving thread. Keep zero-sample auxiliary threads; rawperf/stacks stay local. CPU shares include polling/background/kernel work; these diagnostic QPS values never enter the clean comparisons. No concurrent host builds/tests/benchmarks.'},indent=2)+'\n')
        print('COMPLETE',tag,time.time(),flush=True)
print('ALL_HASH_ROUTE_REPLACE_PROFILES_COMPLETE',time.time(),flush=True)
