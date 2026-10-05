"""Compare8/12workers on the unchanged eight-key ZSet workload and binary."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time
from host_execution_lock import acquire_host
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
output=W/'zset-worker-count-repeats.json'
assert not output.exists()
proc=Path('/proc/790686/stat');identity=proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_PRIOR_SCORE_DIAGNOSTICS',identity,time.time(),flush=True)
while identity is not None and proc.exists():
    try:
        if proc.read_text().split()[21]!=identity:break
    except FileNotFoundError:break
    time.sleep(15)
v=json.loads((W/'zset-source-reuse-versions.json').read_text())['previous']
assert v['commit']=='067c75891f819831620e277eac0592c360f8b585'
ci=json.loads(subprocess.check_output(['gh','run','view','37241392671','--repo','eloqdata/lavik','--json','headSha,conclusion,jobs,url']))
assert ci['headSha']==v['commit'] and ci['conclusion']=='success'
assert len(ci['jobs'])==17 and all(j['conclusion']=='success' for j in ci['jobs'])
tests=json.loads((W/'zset-source-reuse-previous-native-tests.json').read_text())
assert tests['failures']==0 and tests['tests']>0
_execution_lock=acquire_host('zset-worker-count-controls')
with Path(v['binary']).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==v['sha256']
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


rows=[]
method=('Worker-count configuration experiment on one frozen nativeparent067binary. '
        'Three12/8,8/12,12/8 pairs; independent fresh populations each time. '
        'Same complex_1..8 keys,100MiB/key,1024B/member; ZSCORE andZINCRBY atc80/320,30s,pipeline1. '
        'All server flags except --threads remain unchanged; per-worker pools and CPU placement naturally follow worker count. '
        'No concurrent builds/tests/perf. Lightweight per-thread/proc CPU snapshots bracket measure() including client startup/result collection and background CPU; they are not command-exclusive CPU. '
        'This diagnoses workload distribution and configuration, not an implementation speedup; original12worker/peer curves remain unchanged.')
for round_,counts in enumerate([(12,8),(8,12),(12,8)],1):
    for workers in counts:
        tag=f'parent067c7589-zset-worker-count-w{workers}-104857600-1024-k8-repeat{round_}-20261005'
        raw=R/'raw'/('lavik-'+tag);assert not raw.exists()
        argv=['sudo','-n','env','LAVIK_BENCH_ROOT='+str(R),'LAVIK_WORKER_EXPERIMENT_COUNT='+str(workers),'python3',str(R/'run_with_memory_guard.py'),'--minimum-available-gib=20','--','python3',str(W/'run-zset-worker-controls.py'),'lavik','--binary='+v['binary'],'--source-repo='+v['source_repo'],'--source-commit='+v['commit'],'--types=zset','--sizes=104857600','--fields=1024','--keys=8','--tag='+tag,'--mode=point','--levels=80,320','--seconds=30','--continue-on-error']
        subprocess.run(['sudo','-n','python3',str(W/'host.py'),'prepare'],check=True)
        try:
            print('START',tag,time.time(),flush=True)
            with (W/(tag+'.log')).open('w') as log:execute(argv,log)
        finally:subprocess.run(['sudo','-n','python3',str(W/'host.py'),'restore'],check=True)
        subprocess.run(['sudo','-n','chown','-R',f'{os.getuid()}:{os.getgid()}',str(raw)],check=True)
        assert json.loads((raw/'server-exit.json').read_text())['code']==0
        proof=json.loads(next(raw.glob('provenance-*.json')).read_text())
        assert proof['source_commit']==v['commit'] and proof['sha256']==v['sha256']
        assert json.loads((raw/'worker-experiment.json').read_text())['workers']==workers
        command=json.loads((raw/'server-command.json').read_text())
        assert [a for a in command if a.startswith('--threads=')]==['--threads='+str(workers)]
        before=json.loads((raw/'zset-104857600-1024.validated.json').read_text())['sample_cardinalities']
        after=json.loads((raw/'zset-104857600-1024.after.json').read_text())['sample_cardinalities']
        assert before==after and set(before)=={f'complex_{i}' for i in range(1,9)} and all(n==102400 for n in before.values())
        results=[json.loads(p.read_text()) for p in list(raw.glob('*.result.json'))+list(raw.glob('*.error.json'))]
        assert len(results)==4 and {(x['operation'],x['connections']) for x in results}=={(op,c) for op in ['ZSCORE','ZINCRBY'] for c in [80,320]}
        rows.extend({'workers':workers,'round':round_,'tag':tag,**r} for r in results)
        output.write_text(json.dumps({'version':v,'method':method,'rows':rows},indent=2)+'\n')
        assert not any('error' in r for r in results) and json.loads((raw/'complete.json').read_text())['failures_total']==0
        print('COMPLETE',tag,time.time(),flush=True)
assert len(rows)==24
print('ALL_ZSET_WORKER_COUNT_REPEATS_COMPLETE',time.time(),flush=True)
