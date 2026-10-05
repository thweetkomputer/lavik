"""Hash/Set single-route comparisons on the report's 50 GiB populations."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time
from host_execution_lock import acquire_host
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
output=W/'hash-route-replace-repeats.json'
assert not output.exists()
proc=Path('/proc/720974/stat');identity=proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_NATIVE_VALIDATION',identity,time.time(),flush=True)
while identity is not None and proc.exists():
    try:
        if proc.read_text().split()[21]!=identity:break
    except FileNotFoundError:break
    time.sleep(15)
assert 'ALL_HASH_ROUTE_REPLACE_NATIVE_TESTS_PASS' in (W/'hash-route-replace-native-driver.log').read_text()
V=json.loads((W/'hash-route-replace-versions.json').read_text())
assert V['parent']['commit']=='19496654cc43b21df11fb59be60e174dc4c89dbc'
assert V['candidate']['commit']=='27c65ff9c2ceaaacea4c93f42ffed01dce529b8f'
ci=json.loads((W/'hash-route-replace-full-ci.json').read_text())
assert ci['headSha']==V['candidate']['commit'] and ci['conclusion']=='success'
assert len(ci['jobs'])==17 and all(j['conclusion']=='success' for j in ci['jobs'])
_execution_lock=acquire_host('clean-hash-route-pairs')
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
rows=[]
method=('Three independent fresh RESTORE population pairs A/B, B/A, A/B for Hash and Set. '
        '100MiB/1024B/500keys and 1MiB/128B/50000keys match report population sizes. '
        'Each version restores the same checked RDB fixture then restarts; fresh routing seeds/graphs '
        'are independent, not shared disk snapshots. Read controls and writes at80/320/5120connections, '
        'pipeline1,30seconds. HGET/HSET and SISMEMBER/SADD_SREM. Set commands can be no-ops; '
        'QPS counts commands, not durable mutations. Full candidate CI plus native tests on both '
        'frozen production binaries precede runs. No concurrent builds/tests/perf. Stop after a '
        'failed condition, retaining all observations and error files. Historical peers not rerun.')
fixtures={}
for kind in ['hash','set']:
    for size,field,keys in [(104857600,1024,500),(1048576,128,50000)]:
        fixture=Path('/mnt/dev/lavik-benchmark-binaries')/f'lavik-{kind}-{"1m" if size==1048576 else "100m"}-f{field}-generated.dump'
        metadata=json.loads(fixture.with_suffix('.json').read_text())
        # The runner rechecks the complete dump hash before using it.
        assert metadata['kind']==kind and metadata['logical_bytes']==size and metadata['field_bytes']==field
        fixtures[f'{kind}-{size}-{field}']={'path':str(fixture),'sha256':metadata['output_sha256']}
        for round_,labels in enumerate([['parent','candidate'],['candidate','parent'],['parent','candidate']],1):
            for label in labels:
                v=V[label]
                tag=f'{label}{v["commit"][:8]}-hash-route-{kind}-{size}-{field}-k{keys}-repeat{round_}-20261005'
                seed='seed-'+tag;raw=R/'raw'/('lavik-'+tag)
                assert not raw.exists() and not (R/'raw'/('lavik-'+seed)).exists()
                base=['lavik','--binary='+v['binary'],'--source-repo='+v['source_repo'],'--source-commit='+v['commit'],'--types='+kind,'--sizes='+str(size),'--fields='+str(field),'--keys='+str(keys)]
                guard=['sudo','-n','env','LAVIK_BENCH_ROOT='+str(R),'python3',str(R/'run_with_memory_guard.py'),'--minimum-available-gib=20','--','python3',str(R/'run.py')]
                run(['sudo','-n','python3',str(W/'host.py'),'prepare'])
                try:
                    print('START',tag,time.time(),flush=True)
                    with (W/(tag+'.log')).open('w') as log:
                        run(guard+base+['--tag='+seed,'--seed-dump-path='+str(fixture),'--fill-workers='+('32' if keys==50000 else '8'),'--mode=full','--levels=1','--seconds=1'],log)
                        run(guard+base+['--tag='+tag,'--reuse-seeded-data','--seed-source-tag='+seed,'--mode=point','--levels=80,320,5120','--seconds=30','--continue-on-error'],log)
                finally:run(['sudo','-n','python3',str(W/'host.py'),'restore'])
                for current in [R/'raw'/('lavik-'+seed),raw]:
                    run(['sudo','-n','chown','-R',f'{os.getuid()}:{os.getgid()}',str(current)])
                    assert json.loads((current/'server-exit.json').read_text())['code']==0
                    proof=json.loads(next(current.glob('provenance-*.json')).read_text())
                    assert proof['source_commit']==v['commit'] and proof['sha256']==v['sha256']
                prefix=f'{kind}-{size}-{field}'
                before=json.loads((raw/(prefix+'.validated.json')).read_text())['sample_cardinalities']
                after=json.loads((raw/(prefix+'.after.json')).read_text())['sample_cardinalities']
                assert before.keys()==after.keys()
                if kind=='hash':assert before==after
                else:assert all(after[key] in (before[key],before[key]+1) for key in before)
                results=[json.loads(p.read_text()) for p in list(raw.glob('*.result.json'))+list(raw.glob('*.error.json'))]
                operations=('HGET','HSET') if kind=='hash' else ('SISMEMBER','SADD_SREM')
                assert len(results)==6 and {(r['operation'],r['connections']) for r in results}=={(op,c) for op in operations for c in (80,320,5120)}
                rows.extend({'round':round_,'version':label,'tag':tag,**r} for r in results)
                output.write_text(json.dumps({'versions':V,'fixtures':fixtures,'method':method,'rows':rows},indent=2)+'\n')
                assert json.loads((raw/'complete.json').read_text())['failures_total']==0 and not any('error' in r for r in results)
                print('COMPLETE',tag,time.time(),flush=True)
assert len(rows)==144
print('ALL_HASH_ROUTE_REPLACE_REPEATS_COMPLETE',time.time(),flush=True)
