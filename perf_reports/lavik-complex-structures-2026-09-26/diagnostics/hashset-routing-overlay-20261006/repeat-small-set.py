"""Main versus bounded routing overlay: three fresh AB/BA/AB pairs."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time,sys
sys.path.insert(0,'/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
output=W/'small-set-repeats.json'
assert not output.exists()
V=json.loads((W/'validated-versions.json').read_text())
assert 'ALL_HASHSET_OVERLAY_NATIVE_TESTS_PASS' in (W/'native-driver.log').read_text()
_execution_lock=acquire_host('hashset-small-set-priority-pairs')
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
if (R/'spdk-ready.json').exists():
 run(['sudo','-n','python3',str(W/'host.py'),'restore'])
else:
 sys.path.insert(0,str(R));import spdk_host
 spdk_host.no_servers();spdk_host.assert_driver('nvme')
original=json.loads((W/'overlay-repeats.json').read_text())
assert len(original['rows'])==42
rows=[r for r in original['rows'] if r['type']=='set' and r['logical_bytes']==1048576]
assert len(rows)==6 and all(r['round']==1 for r in rows)
method=('Small Set regression diagnosis:1MiB/key,128Bmembers,50000keys,c320,pipeline1,12workers. '
        'Retain the original round1AB pair; run round2BA andround3AB first. Three30secondconditions '
        'perpopulation:read,write,read-after-write. Source,fixture,hardware andcommands unchanged. '
        'Independent RESTORE/restart perversion; no concurrent builds/tests/perf. '
        'The broader108pointmatrix was intentionally stopped after42completepoints while the '
        'next RESTORE was still in progress; no completed clean point was discarded. '
        'Set QPS counts commands includingnoops. Profile runs follow separately.')
scopes=[('standard','set',1048576,128,50000)]
for round_,labels in [(2,['candidate','parent']),(3,['parent','candidate'])]:
 for pattern,kind,size,field,keys in scopes:
  fixture=Path('/mnt/dev/lavik-benchmark-binaries')/f'lavik-{kind}-{"1m" if size==1048576 else "100m"}-f{field}-generated.dump'
  for label in labels:
   v=V[label]
   tag=f'{label}{v["commit"][:8]}-route-overlay-{pattern}-{kind}-{size}-{field}-k{keys}-r{round_}-20261006'
   seed='seed-'+tag;raw=R/'raw'/('lavik-'+tag)
   assert not raw.exists() and not (R/'raw'/('lavik-'+seed)).exists()
   base=['lavik','--binary='+v['binary'],'--source-repo='+v['source_repo'],'--source-commit='+v['commit'],'--types='+kind,'--sizes='+str(size),'--fields='+str(field),'--keys='+str(keys)]
   guard=['sudo','-n','env','LAVIK_BENCH_ROOT='+str(R),'unshare','--mount','--propagation','private','python3',str(W/'private-tmp-exec.py'),str(W/'benchmark-tmp'),'0','0','python3',str(R/'run_with_memory_guard.py'),'--minimum-available-gib=20','--','python3']
   run(['sudo','-n','python3',str(W/'host.py'),'prepare'])
   try:
    print('START',tag,time.time(),flush=True)
    with (W/(tag+'.log')).open('w') as log:
     run(guard+[str(R/'run.py')]+base+['--tag='+seed,'--seed-dump-path='+str(fixture),'--fill-workers='+('32' if keys==50000 else '8'),'--mode=full','--levels=1','--seconds=1'],log)
     runner=W/'run-overlay-controls.py'
     run(guard+[str(runner)]+base+['--tag='+tag,'--reuse-seeded-data','--seed-source-tag='+seed,'--mode=point','--levels=320','--seconds=30','--continue-on-error'],log)
   finally:run(['sudo','-n','python3',str(W/'host.py'),'restore'])
   for current in [R/'raw'/('lavik-'+seed),raw]:
    run(['sudo','-n','chown','-R',f'{os.getuid()}:{os.getgid()}',str(current)])
    assert json.loads((current/'server-exit.json').read_text())['code']==0
    proof=json.loads(next(current.glob('provenance-*.json')).read_text())
    assert proof['source_commit']==v['commit'] and proof['sha256']==v['sha256']
   prefix=f'{kind}-{size}-{field}'
   before=json.loads((raw/(prefix+'.validated.json')).read_text())['sample_cardinalities']
   after=json.loads((raw/(prefix+'.after.json')).read_text())['sample_cardinalities']
   assert before.keys()==after.keys() and len(before)==keys
   assert all(after[k]==before[k] if kind=='hash' else before[k]<=after[k]<=before[k]+(64 if pattern=='dispersed64' else 1) for k in before)
   results=[json.loads(p.read_text()) for p in list(raw.glob('*.result.json'))+list(raw.glob('*.error.json'))]
   operations=('HGET','HSET','HGET_AFTER_WRITE') if kind=='hash' else ('SISMEMBER','SADD_SREM','SISMEMBER_AFTER_WRITE')
   assert len(results)==3 and {(r['operation'],r['connections']) for r in results}=={(op,320) for op in operations}
   rows.extend({'round':round_,'version':label,'pattern':pattern,'tag':tag,**r} for r in results)
   output.write_text(json.dumps({'versions':{label:{k:v[k] for k in ['commit','source_repo','binary','sha256','bycorf_commit']} for label,v in V.items()},'method':method,'rows':rows},indent=2)+'\n')
   assert json.loads((raw/'complete.json').read_text())['failures_total']==0 and not any('error' in r for r in results)
   print('COMPLETE',tag,time.time(),flush=True)
assert len(rows)==18
print('ALL_SMALL_SET_REPEATS_COMPLETE',time.time(),flush=True)
