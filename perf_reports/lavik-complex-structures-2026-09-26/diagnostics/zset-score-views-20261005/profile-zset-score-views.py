"""Separate ZSCORE diagnostics after the complete clean comparison."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time
from host_execution_lock import acquire_host
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
output=W/'zset-score-views-profiles.json'
assert not output.exists()
proc=Path('/proc/790154/stat');identity=proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_CLEAN_SCORE_PAIRS',identity,time.time(),flush=True)
while identity is not None and proc.exists():
    try:
        if proc.read_text().split()[21]!=identity:break
    except FileNotFoundError:break
    time.sleep(15)
assert 'ALL_ZSET_SCORE_VIEWS_REPEATS_COMPLETE' in (W/'zset-score-views-repeat-driver.log').read_text()
repeats=json.loads((W/'zset-score-views-repeats.json').read_text())
assert len(repeats['rows'])==96 and not any('error' in r for r in repeats['rows'])
V=repeats['versions']
assert V['parent']['commit']=='4610d6077e8e32d59639a5ee88dbe8cbd305aab2'
assert V['candidate']['commit']=='9d1ffc8572f558cc139b1801488d014c2099dbfd'
_execution_lock=acquire_host('zset-score-views-perf')
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


profiles={}
for size,field,keys,connections in [(104857600,1024,8,5120),(65536,128,64,320)]:
    seed_tag=f'seed-zset-score-views-perf-{size}-{field}-20261005'
    subprocess.run(['sudo','-n','python3',str(W/'host.py'),'prepare'],check=True)
    try:
        for label in ['seed','parent','candidate']:
            v=V['parent' if label=='seed' else label]
            seed=label=='seed'
            tag=seed_tag if seed else f'diagnostic-{label}{v["commit"][:8]}-zset-score-views-{size}-{field}-c{connections}-20261005'
            raw=R/'raw'/('lavik-'+tag);assert not raw.exists()
            helper='run-zset-score-controls.py' if seed else 'profile-ordered-allworkers.py'
            argv=['sudo','-n','env','LAVIK_BENCH_ROOT='+str(R),'LAVIK_PROFILE_ZSET_OPERATION=ZSCORE','python3',str(R/'run_with_memory_guard.py'),'--minimum-available-gib=20','--','python3',str(W/helper),'lavik','--binary='+v['binary'],'--source-repo='+v['source_repo'],'--source-commit='+v['commit'],'--types=zset','--sizes='+str(size),'--fields='+str(field),'--keys='+str(keys),'--tag='+tag,'--mode=point']
            argv+=['--seed-only','--levels=1','--seconds=1'] if seed else ['--reuse-seeded-data','--seed-source-tag='+seed_tag,'--levels='+str(connections),'--seconds=30']
            print('START',tag,time.time(),flush=True)
            with (W/(tag+'.log')).open('w') as log:execute(argv,log)
            subprocess.run(['sudo','-n','chown','-R',f'{os.getuid()}:{os.getgid()}',str(raw)],check=True)
            assert json.loads((raw/'server-exit.json').read_text())['code']==0
            assert json.loads((raw/'complete.json').read_text())['failures_total']==0
            proof=json.loads(next(raw.glob('provenance-*.json')).read_text())
            assert proof['source_commit']==v['commit'] and proof['sha256']==v['sha256']
            prefix=f'zset-{size}-{field}'
            before=json.loads((raw/(prefix+'.validated.json')).read_text())['sample_cardinalities']
            after=json.loads((raw/(prefix+'.after.json')).read_text())['sample_cardinalities']
            assert before==after and set(before)=={f'complex_{i}' for i in range(1,keys+1)}
            assert all(n==size//field for n in before.values())
            if seed:
                population=before
                continue
            assert before==population and proof['reused_seed_from']==seed_tag
            diagnostic=raw/f'diagnostic-c{connections}'
            evidence=json.loads((diagnostic/'profile-provenance.json').read_text())
            assert evidence['operation']=='ZSCORE' and evidence['source_commit']==v['commit'] and evidence['binary']==v['binary']
            assert len(evidence['argv_by_tid'])>=12
            measured=list(diagnostic.glob('*.result.json'));assert len(measured)==1
            result=json.loads(measured[0].read_text());assert result['operation']=='ZSCORE' and result['connections']==connections
            profiles[f'{label}-{size}-{field}']={'version':v,'tag':tag,'seed_tag':seed_tag,'directory':str(diagnostic),'attached_tids':list(evidence['argv_by_tid']),'profile_driver_sha256':evidence['driver_sha256']}
            output.write_text(json.dumps({'profiles':profiles,'method':'Independent ZSCORE diagnostics after all96 clean points. Large100MiB1024B8keys c5120; small64KiB128B64keys c320. Each pair restarts parent then candidate on one fresh parent-seeded logical population, no intervening writes. 30s counter window,25s99Hz task-clock/16KiB DWARF perworker. Includes background/polling/kernel; no QPS claim from these instrumented fixed-order pairs. All attached threads retained, raw perf/stacks local only.'},indent=2)+'\n')
            print('COMPLETE',tag,time.time(),flush=True)
    finally:subprocess.run(['sudo','-n','python3',str(W/'host.py'),'restore'],check=True)
assert len(profiles)==4
print('ALL_ZSET_SCORE_VIEWS_PROFILES_COMPLETE',time.time(),flush=True)
