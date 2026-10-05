"""Check ordinary short-key grouped performance after verified-root reuse."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time
from host_execution_lock import acquire_host
W=Path(__file__).resolve().parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
output=W/'grouped-root-controls-repeats.json'
assert not output.exists(), 'retain prior observations before any restart'
script_paths=[Path(__file__),R/'run.py',R/'run_with_memory_guard.py',W/'host.py',
              W/'run-grouped-root-controls.py']
script_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in script_paths}
waiting={}
for pid in [837210]:
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
assert 'ALL_GROUPED_ROOT_NATIVE_TESTS_PASS' in (W/'grouped-root-native-driver.log').read_text()
V=json.loads((W/'grouped-root-native-versions.json').read_text())
expected={'parent':('19496654cc43b21df11fb59be60e174dc4c89dbc','eloqdata/lavik',37237724710),
          'candidate':('28d7cca498655e02f46407adb65335219b10ee6b','thweetkomputer/lavik',37258994628)}
assert set(V)==set(expected)
def cache_values(path):
    return {line.split('=',1)[0].split(':',1)[0]:line.split('=',1)[1]
            for line in path.read_text().splitlines()
            if line and not line.startswith(('#','//')) and '=' in line}
keys=['CMAKE_BUILD_TYPE','CMAKE_CXX_COMPILER','CMAKE_CXX_FLAGS','CMAKE_CXX_FLAGS_RELWITHDEBINFO',
      'CMAKE_INTERPROCEDURAL_OPTIMIZATION','LAVIK_KERNEL_BYPASS','LAVIK_ENABLE_TEST_FAULTS','BUILD_TESTING','LAVIK_MARCH']
reference=cache_values(W/'hash-route-replace-parent-CMakeCache.txt')
for label,(head,repo,run_id) in expected.items():
    assert V[label]['commit']==head and V[label]['bycorf_commit']=='62509c93d40c2480f5046b71454db6cf95801b04'
    assert all(t['failures']==0 and t['tests']>0 for t in V[label]['ordinary_tests'].values())
    current=reference if label=='parent' else cache_values(W/'grouped-root-candidate-CMakeCache.txt')
    assert all(current.get(k)==reference.get(k) for k in keys)
    assert current['LAVIK_MARCH']=='native' and current['BUILD_TESTING']==current['LAVIK_ENABLE_TEST_FAULTS']=='OFF'
    V[label]['comparison_build_options']={k:current.get(k) for k in keys}
    proof=json.loads(subprocess.check_output(['gh','run','view',str(run_id),'--repo',repo,'--json','headSha,conclusion,jobs,url']))
    assert proof['headSha']==head and proof['conclusion']=='success'
    assert len(proof['jobs'])==17 and all(j['conclusion']=='success' for j in proof['jobs'])
    V[label]['full_fault_enabled_ci']=proof['url']
_execution_lock=acquire_host('clean-grouped-root-short-key-controls')
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in script_hashes.items())
for v in V.values():
    with Path(v['binary']).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==v['sha256']

def terminate(_signal,_frame):raise SystemExit('grouped root controls interrupted')
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

# Ordinary-key regression controls, not the historical peer grid: fewer
# Hash/Set keys keep this gate bounded while retaining grouped pages.
conditions=[
    {'kind':'hash','size':1048576,'field':128,'keys':500,'read':[320],'full':[],'write':[320]},
    {'kind':'set','size':1048576,'field':128,'keys':500,'read':[320],'full':[],'write':[320]},
    {'kind':'list','size':65536,'field':128,'keys':64,'read':[320],'full':[80],'write':[320]},
    {'kind':'zset','size':65536,'field':128,'keys':64,'read':[320],'full':[],'write':[320]},
    {'kind':'stream','size':65536,'field':1024,'keys':64,'read':[320],'full':[80],'write':[320]},
]
assert 6*sum(len(c['read'])+len(c['full'])+len(c['write']) for c in conditions)==72
point={'hash':('HGET','HSET'),'set':('SISMEMBER','SADD_SREM'),'list':('LINDEX','LSET'),
       'zset':('ZSCORE','ZINCRBY'),'stream':('XRANGE','XADD_MAXLEN')}
full={'list':'LRANGE','stream':'XRANGE_FULL'}
rows=[];seeds=[]
method=('Three30second AB/BA/AB pairs parent194 versus rootreuse28.72 ordinaryshortkey '
        'controls,12 command/condition/concurrency cells acrossHash/Set/List/ZSet/Stream. '
        'Hash/Set1MiB128B500keys;List/ZSet64KiB128B64keys;Stream64KiB1024B64keys. '
        'Allpointread/writec320,fullList/Streamc80. Shared fresh parent-seeded logical '
        'population for each read pair, restart without intervening writes; background '
        'physical changes remain possible. Independent fresh populations for writes. '
        'Pipeline1. All keys/cardinalities, errors, exact native binaries, matching '
        'build options and full CI checked. No concurrent host builds/tests/perf. '
        'Not the historical peer grid, not longkey latency or whole-suite parity.')

def measure(label,condition,round_,write=False,seed_tag=None,seed_only=False):
    kind,size,field,count=(condition[k] for k in ['kind','size','field','keys'])
    v=V[label];purpose='write' if write else 'read'
    tag=f'{label}{v["commit"][:8]}-grouped-root-controls-{kind}-{size}-{field}-{purpose}-repeat{round_}-20261005'
    if seed_only:tag='seed-'+tag
    raw=R/'raw'/('lavik-'+tag);assert not raw.exists(),raw
    helper='run-grouped-root-controls.py'
    args=['sudo','-n','env','LAVIK_BENCH_ROOT='+str(R),'python3',str(R/'run_with_memory_guard.py'),
          '--minimum-available-gib=20','--','python3',str(W/helper),'lavik','--binary='+v['binary'],
          '--source-repo='+v['source_repo'],'--source-commit='+v['commit'],'--types='+kind,
          '--sizes='+str(size),'--fields='+str(field),'--keys='+str(count),'--tag='+tag]
    if seed_only:args+=['--mode=point','--levels=1','--seconds=1','--seed-only']
    elif write:
        args+=['--mode=point','--levels='+','.join(map(str,condition['write'])),'--seconds=30','--continue-on-error']
        args+=['--write-only']
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
    elif kind=='set' and write:assert all(after[k] in (before[k],before[k]+1) for k in before)
    else:assert before==after
    if seed_only:
        assert not list(raw.glob('*.result.json')) and not list(raw.glob('*.error.json'))
        seeds.append({'round':round_,'tag':tag,'cardinalities':before})
    else:
        results=[json.loads(p.read_text()) for p in [*raw.glob('*.result.json'),*raw.glob('*.error.json')]]
        op=point[kind][int(write)]
        cases={(op,c) for c in condition['write' if write else 'read']}
        if not write and condition['full']:cases|={(full[kind],c) for c in condition['full']}
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

orders=[('parent','candidate'),('candidate','parent'),('parent','candidate')]
for condition in conditions:
    if condition['read'] or condition['full']:
        for round_,labels in enumerate(orders,1):
            subprocess.run(['sudo','-n','python3',str(W/'host.py'),'prepare'],check=True)
            try:
                seed,population=measure('parent',condition,round_,seed_only=True)
                for label in labels:
                    _,counts=measure(label,condition,round_,seed_tag=seed);assert counts==population
            finally:subprocess.run(['sudo','-n','python3',str(W/'host.py'),'restore'],check=True)
    for round_,labels in enumerate(orders,1):
        for label in labels:
            subprocess.run(['sudo','-n','python3',str(W/'host.py'),'prepare'],check=True)
            try:measure(label,condition,round_,write=True)
            finally:subprocess.run(['sudo','-n','python3',str(W/'host.py'),'restore'],check=True)
assert len(rows)==72
print('ALL_GROUPED_ROOT_CONTROLS_COMPLETE',time.time(),flush=True)
