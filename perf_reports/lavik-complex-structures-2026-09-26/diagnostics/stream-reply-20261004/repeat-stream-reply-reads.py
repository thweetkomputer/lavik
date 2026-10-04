"""Three paired read sweeps; both binaries recover the same untouched seed."""
from pathlib import Path
import json,os,subprocess,time
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
V=json.loads((W/'stream-reply-versions.json').read_text())
assert 'ALL_STREAM_REPLY_INITIAL_MEASUREMENTS_COMPLETE' in (W/'stream-reply-measurement-driver.log').read_text()
output=W/'stream-reply-read-repeats.json';assert not output.exists(), 'inspect prior progress before restarting'
rows=[];seeds=[]
def run(v,tag,seed=None):
    raw=R/'raw'/('lavik-'+tag);assert not raw.exists(),raw
    args=['sudo','-n','env','LAVIK_BENCH_ROOT='+str(R),'python3',str(R/'run_with_memory_guard.py'),'--minimum-available-gib=20','--','python3',str(W/'run-stream-reply-reads.py'),'lavik','--binary='+v['binary'],'--source-repo='+v['source_repo'],'--source-commit='+v['commit'],'--types=stream','--sizes=104857600','--fields=128','--keys=8','--tag='+tag]
    args+=['--mode=both','--levels=2560','--full-levels=1,4,16','--seconds=30','--reuse-seeded-data','--seed-source-tag='+seed,'--continue-on-error'] if seed else ['--mode=point','--levels=1','--seconds=1','--seed-only']
    print('START',tag,time.time(),flush=True)
    with (W/(tag+'.log')).open('w') as f:subprocess.run(args,cwd=R.parents[1],stdout=f,stderr=subprocess.STDOUT,check=True)
    subprocess.run(['sudo','-n','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(raw)],check=True)
    assert json.loads((raw/'server-exit.json').read_text())['code']==0
    proof=json.loads(next(raw.glob('provenance-*.json')).read_text());assert proof['source_commit']==v['commit'] and proof['sha256']==v['sha256']
    prefix='stream-104857600-128'
    before=json.loads((raw/(prefix+'.validated.json')).read_text())['sample_cardinalities']
    after=json.loads((raw/(prefix+'.after.json')).read_text())['sample_cardinalities'];assert before==after,(before,after)
    print('COMPLETE',tag,time.time(),flush=True)
    return raw,before
for round_,labels in enumerate([['main','candidate'],['candidate','main'],['main','candidate']],1):
    seed_tag=f'seed-maina565d603-stream-reply-read-repeat{round_}-20261004'
    subprocess.run(['sudo','-n','python3',str(W/'host.py'),'prepare'],check=True)
    try:
        seed_raw,population=run(V['main'],seed_tag)
        seeds.append({'round':round_,'tag':seed_tag,'cardinalities':population})
        for label in labels:
            v=V[label];tag=f'{label}{v["commit"][:8]}-stream-reply-read-repeat{round_}-20261004'
            raw,counts=run(v,tag,seed_tag);assert counts==population
            results=[json.loads(f.read_text()) for f in list(raw.glob('*.result.json'))+list(raw.glob('*.error.json'))]
            assert {(x['operation'],x['connections']) for x in results}=={('XRANGE_FULL',1),('XRANGE_FULL',4),('XRANGE_FULL',16),('XRANGE',2560)}
            for result in results:rows.append({'round':round_,'version':label,'tag':tag,**result})
            output.write_text(json.dumps({'main':V['main'],'candidate':V['candidate'],'seeds':seeds,'rows':rows,'method':'Three 30-second paired read sweeps ordered A/B, B/A, A/B. Each round seeds a fresh main population once, shuts the seed server down, then both immutable binaries separately recover that same untouched population. Full XRANGE at1/4/16, point XRANGE at2560; exact before/after and between-binary cardinalities must match. No XADD in these pairs, and no overlapping build/tests/perf. Write controls require separate comparisons. Small command counts limit tail-latency precision.'},indent=2)+'\n')
    finally:subprocess.run(['sudo','-n','python3',str(W/'host.py'),'restore'],check=True)
print('ALL_STREAM_REPLY_READ_REPEATS_COMPLETE',time.time(),flush=True)
