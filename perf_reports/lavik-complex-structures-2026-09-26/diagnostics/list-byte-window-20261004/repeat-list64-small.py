from pathlib import Path
import json,os,subprocess,time,statistics
W=Path(__file__).parent;R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26');v=json.loads((W/'list64-versions.json').read_text());rows=[]
for field,op in [(128,'LINDEX'),(1024,'LSET')]:
 for round_,order in enumerate([['previous','candidate'],['candidate','previous'],['previous','candidate']],1):
  for label in order:
   x=v[label];tag=f'{label}{x["commit"][:8]}-list64-small-f{field}-{op.lower()}-k64-against4863c98d-repeat{round_}-20261004';raw=R/'raw'/('lavik-'+tag)
   if not (raw/'complete.json').exists():
    assert not raw.exists(),raw
    subprocess.run(['sudo','-n','python3',str(W/'host.py'),'prepare'],check=True)
    try:
     print('START',tag,time.time(),flush=True)
     args=['sudo','-n','env','LAVIK_BENCH_ROOT='+str(R),'LAVIK_LIST_CONTROL_OP='+op,'python3',str(R/'run_with_memory_guard.py'),'--minimum-available-gib=20','--','python3',str(W/'run-list64-point-control.py'),'lavik','--binary='+x['binary'],'--source-repo='+x['source_repo'],'--source-commit='+x['commit'],'--types=list','--sizes=65536','--fields='+str(field),'--keys=64','--tag='+tag,'--mode=point','--levels=5120','--seconds=15']
     with (W/(tag+'.log')).open('w') as f:subprocess.run(args,cwd=R.parents[1],stdout=f,stderr=subprocess.STDOUT,check=True)
    finally:subprocess.run(['sudo','-n','python3',str(W/'host.py'),'restore'],check=True)
    subprocess.run(['sudo','-n','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(raw)],check=True)
   assert json.loads((raw/'server-exit.json').read_text())['code']==0
   proof=json.loads(next(raw.glob('provenance-*.json')).read_text());assert proof['source_commit']==x['commit'] and proof['sha256']==x['sha256']
   results=list(raw.glob('*.result.json'))+list(raw.glob('*.error.json'));assert len(results)==1,results
   r=json.loads(results[0].read_text());assert r['operation']==op and r['connections']==5120
   rows.append({'field':field,'round':round_,'version':label,'tag':tag,**r})
   (W/'list64-small-repeats.json').write_text(json.dumps({'previous':v['previous'],'candidate':v['candidate'],'rows':rows,'method':'Three 15-second paired runs A/B, B/A, A/B for each observed small-list regression: 64KiB/128B LINDEX and 64KiB/1024B LSET, 64 keys, 5120 connections. Independent seed and server per observation; no build/tests/perf overlap.'},indent=2)+'\n')
   print('COMPLETE',tag,time.time(),flush=True)
summary=[]
for field,op in [(128,'LINDEX'),(1024,'LSET')]:
 pairs=[]
 for round_ in [1,2,3]:
  a=next(x for x in rows if x['field']==field and x['round']==round_ and x['version']=='previous');b=next(x for x in rows if x['field']==field and x['round']==round_ and x['version']=='candidate')
  pairs.append({'round':round_,'previous':a,'candidate':b,'qps_change_percent':None if 'error' in a or 'error' in b else 100*(b['qps']/a['qps']-1)})
 ratios=[p['qps_change_percent'] for p in pairs if p['qps_change_percent'] is not None]
 summary.append({'field':field,'operation':op,'connections':5120,'pairs':pairs,'median_paired_change_percent':statistics.median(ratios) if ratios else None,'change_range_percent':[min(ratios),max(ratios)] if ratios else None})
(W/'list64-small-repeat-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
