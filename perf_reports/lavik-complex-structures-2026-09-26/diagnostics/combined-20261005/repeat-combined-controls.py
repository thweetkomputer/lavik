"""Measure the frozen three-PR combination against its native main baseline."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time
from host_execution_lock import acquire_host
W=Path(__file__).resolve().parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
output=W/'combined-controls-repeats.json'
assert not output.exists(), 'retain prior observations before any restart'
script_paths=[Path(__file__),R/'run.py',R/'run_with_memory_guard.py',W/'host.py',
              W/'run-zset-score-controls.py',W/'run-stream-reply-reads.py',W/'run-write-only.py']
script_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in script_paths}
waiting={}
for pid in [761017,798316,803021]:
    p=Path('/proc')/str(pid)/'stat'
    if p.exists():waiting[pid]=p.read_text().rsplit(')',1)[1].split()[19]
print('WAIT_FOR_NATIVE_AND_PRIOR_CONTROLS',waiting,time.time(),flush=True)
for pid,identity in waiting.items():
    p=Path('/proc')/str(pid)/'stat'
    while p.exists():
        try:
            if p.read_text().rsplit(')',1)[1].split()[19]!=identity:break
        except FileNotFoundError:break
        time.sleep(15)
assert 'ALL_COMBINED_NATIVE_TESTS_PASS' in (W/'combined-native-driver.log').read_text()
# Original live validator loaded the obsolete dependency resolver. Require the
# separately verified correction; never relabel the original work manifest.
V=json.loads((W/'combined-native-versions-corrected.json').read_text())
expected={'main':('4610d6077e8e32d59639a5ee88dbe8cbd305aab2','eloqdata/lavik',37258162392),
          'combined':('78e29277618f4ef40ccefab0930cbab667a0a40e','thweetkomputer/lavik',37260751356)}
assert set(V)==set(expected)
def cache_values(path):
    return {line.split('=',1)[0].split(':',1)[0]:line.split('=',1)[1]
            for line in path.read_text().splitlines()
            if line and not line.startswith(('#','//')) and '=' in line}
keys=['CMAKE_BUILD_TYPE','CMAKE_CXX_COMPILER','CMAKE_CXX_FLAGS','CMAKE_CXX_FLAGS_RELWITHDEBINFO',
      'CMAKE_INTERPROCEDURAL_OPTIMIZATION','LAVIK_KERNEL_BYPASS','LAVIK_ENABLE_TEST_FAULTS','BUILD_TESTING','LAVIK_MARCH']
reference=cache_values(W/'combined-main-CMakeCache.txt')
for label,(head,repo,run_id) in expected.items():
    assert V[label]['commit']==head and V[label]['bycorf_commit']=='62509c93d40c2480f5046b71454db6cf95801b04'
    assert all(t['failures']==0 and t['tests']>0 for t in V[label]['tests'].values())
    assert V[label]['pubsub_exit']==0
    current=cache_values(W/f'combined-{label}-CMakeCache.txt')
    assert all(current.get(k)==reference.get(k) for k in keys)
    assert current['LAVIK_MARCH']=='native' and current['BUILD_TESTING']==current['LAVIK_ENABLE_TEST_FAULTS']=='OFF'
    V[label]['comparison_build_options']={k:current.get(k) for k in keys}
    proof=json.loads(subprocess.check_output(['gh','run','view',str(run_id),'--repo',repo,'--json','headSha,conclusion,jobs,url']))
    assert proof['headSha']==head and proof['conclusion']=='success'
    assert len(proof['jobs'])==17 and all(j['conclusion']=='success' for j in proof['jobs'])
    V[label]['full_fault_enabled_ci']=proof['url']
_execution_lock=acquire_host('clean-combined-main-controls')
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in script_hashes.items())
for v in V.values():
    with Path(v['binary']).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==v['sha256']

def terminate(_signal,_frame):raise SystemExit('combined controls interrupted')
signal.signal(signal.SIGTERM,terminate)
def execute(argv,log=None):
    child=subprocess.Popen(argv,cwd=R.parents[1],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        code=child.wait()
        if code:raise subprocess.CalledProcessError(code,argv)
    except BaseException:
        # Memory guard creates a separate child session: retain descendant
        # groups before signalling so no surviving server owns scratch devices.
        owned={child.pid};groups={child.pid};processes={}
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

# Preserve the existing report's cardinality and field sizes. The third Stream
# condition additionally exercises #265's measured large-1KiB suffix workload.
conditions=[
    {'kind':'stream','size':104857600,'field':128,'keys':8,'read':[2560],'full':[1,4,16],'write':[320,5120]},
    {'kind':'stream','size':65536,'field':1024,'keys':64,'read':[5120],'full':[80],'write':[2560,5120]},
    {'kind':'stream','size':104857600,'field':1024,'keys':8,'read':[],'full':[],'write':[80,320,5120]},
    {'kind':'zset','size':104857600,'field':1024,'keys':8,'read':[80,320,5120],'full':[],'write':[80,320,5120]},
    {'kind':'zset','size':65536,'field':128,'keys':64,'read':[80,320,5120],'full':[],'write':[80,320,5120]},
]
assert 6*sum(len(c['read'])+len(c['full'])+len(c['write']) for c in conditions)==150
rows=[];seeds=[]
method=('Three30second AB/BA/AB pairs main4610 versus combined78e29277 containing PR265/266/270. '
        '150 observations,25 command/condition/concurrency cells. Shared fresh parent-seeded '
        'logical population for each read pair, restart without intervening writes; background '
        'physical changes remain possible. Independent fresh populations for writes. Pipeline1. '
        'All keys/cardinalities, errors, exact native binaries, matching build options and full CI '
        'checked. No concurrent host builds/tests/perf. Stage-one combination only; neither summed '
        'individual gains nor proof of whole-suite parity. Historical peers not rerun.')

def measure(label,condition,round_,write=False,seed_tag=None,seed_only=False):
    kind,size,field,count=(condition[k] for k in ['kind','size','field','keys'])
    v=V[label];purpose='write' if write else 'read'
    tag=f'{label}{v["commit"][:8]}-combined-controls-{kind}-{size}-{field}-{purpose}-repeat{round_}-20261005'
    if seed_only:tag='seed-'+tag
    raw=R/'raw'/('lavik-'+tag);assert not raw.exists(),raw
    helper='run-zset-score-controls.py' if kind=='zset' else 'run-write-only.py' if write else 'run-stream-reply-reads.py'
    args=['sudo','-n','env','LAVIK_BENCH_ROOT='+str(R),'python3',str(R/'run_with_memory_guard.py'),
          '--minimum-available-gib=20','--','python3',str(W/helper),'lavik','--binary='+v['binary'],
          '--source-repo='+v['source_repo'],'--source-commit='+v['commit'],'--types='+kind,
          '--sizes='+str(size),'--fields='+str(field),'--keys='+str(count),'--tag='+tag]
    if seed_only:args+=['--mode=point','--levels=1','--seconds=1','--seed-only']
    elif write:
        args+=['--mode=point','--levels='+','.join(map(str,condition['write'])),'--seconds=30','--continue-on-error']
        if kind=='zset':args+=['--write-only']
    else:
        args+=['--mode='+('both' if condition['full'] else 'point'),
               '--levels='+','.join(map(str,condition['read'])),'--seconds=30',
               '--reuse-seeded-data','--seed-source-tag='+seed_tag,'--continue-on-error']
        if condition['full']:args+=['--full-levels='+','.join(map(str,condition['full']))]
    print('START',tag,time.time(),flush=True)
    with (W/(tag+'.log')).open('w') as log:execute(args,log)
    subprocess.run(['sudo','-n','chown','-R',f'{os.getuid()}:{os.getgid()}',str(raw)],check=True)
    assert json.loads((raw/'server-exit.json').read_text())['code']==0
    provs=list(raw.glob('provenance-*.json'));assert len(provs)==1
    proof=json.loads(provs[0].read_text());assert proof['source_commit']==v['commit'] and proof['sha256']==v['sha256']
    prefix=f'{kind}-{size}-{field}'
    before=json.loads((raw/(prefix+'.validated.json')).read_text())['sample_cardinalities']
    after=json.loads((raw/(prefix+'.after.json')).read_text())['sample_cardinalities']
    assert set(before)==set(after)=={f'complex_{i}' for i in range(1,count+1)}
    assert all(n==size//field for n in before.values())
    if kind=='stream' and write:assert all(before[k]<=after[k]<=before[k]+100 for k in before)
    else:assert before==after
    if seed_only:
        assert not list(raw.glob('*.result.json')) and not list(raw.glob('*.error.json'))
        seeds.append({'round':round_,'tag':tag,'cardinalities':before})
    else:
        results=[json.loads(p.read_text()) for p in [*raw.glob('*.result.json'),*raw.glob('*.error.json')]]
        op=('XADD_MAXLEN' if kind=='stream' else 'ZINCRBY') if write else ('XRANGE' if kind=='stream' else 'ZSCORE')
        cases={(op,c) for c in condition['write' if write else 'read']}
        if not write:cases|={('XRANGE_FULL',c) for c in condition['full']}
        assert len(results)==len(cases) and {(x['operation'],x['connections']) for x in results}==cases
        rows.extend({'round':round_,'version':label,'tag':tag,**x} for x in results)
        output.write_text(json.dumps({'versions':V,'rows':rows,'seeds':seeds,'conditions':conditions,
                                     'method':method,'script_sha256':script_hashes},indent=2)+'\n')
        assert not any('error' in x for x in results),'failed observations retained'
        assert all(x['seconds']==30 and x['requests']>0 and x['keys']==count and x['logical_bytes']==size
                   and x['field_bytes']==field and x['entries_per_key']==size//field for x in results)
    assert json.loads((raw/'complete.json').read_text())['failures_total']==0
    print('COMPLETE',tag,time.time(),flush=True)
    return tag,before

orders=[('main','combined'),('combined','main'),('main','combined')]
for condition in conditions:
    if condition['read'] or condition['full']:
        for round_,labels in enumerate(orders,1):
            subprocess.run(['sudo','-n','python3',str(W/'host.py'),'prepare'],check=True)
            try:
                seed,population=measure('main',condition,round_,seed_only=True)
                for label in labels:
                    _,counts=measure(label,condition,round_,seed_tag=seed);assert counts==population
            finally:subprocess.run(['sudo','-n','python3',str(W/'host.py'),'restore'],check=True)
    for round_,labels in enumerate(orders,1):
        for label in labels:
            subprocess.run(['sudo','-n','python3',str(W/'host.py'),'prepare'],check=True)
            try:measure(label,condition,round_,write=True)
            finally:subprocess.run(['sudo','-n','python3',str(W/'host.py'),'restore'],check=True)
assert len(rows)==150
print('ALL_COMBINED_CONTROLS_COMPLETE',time.time(),flush=True)
