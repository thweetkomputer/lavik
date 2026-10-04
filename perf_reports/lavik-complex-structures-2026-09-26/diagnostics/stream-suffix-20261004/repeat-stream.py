from pathlib import Path
import json,os,subprocess,time
W=Path(__file__).parent;R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26');V=json.loads((W/'versions.json').read_text())
results=[]
for round_,labels in enumerate([['main','candidate'],['candidate','main'],['main','candidate']],1):
 for label in labels:
  v=V[label];tag=f'{label}{v["commit"][:8]}-stream-100m-f1024-k8-repeat{round_}-20261004';raw=R/'raw'/('lavik-'+tag)
  if not (raw/'complete.json').exists():
   assert not raw.exists(),raw
   args=['sudo','-n','env','LAVIK_BENCH_ROOT='+str(R),'python3',str(R/'run_with_memory_guard.py'),'--minimum-available-gib=20','--','python3',str(W/'run-write-only.py'),'lavik','--binary='+v['binary'],'--source-repo='+v['source_repo'],'--source-commit='+v['commit'],'--types=stream','--sizes=104857600','--fields=1024','--keys=8','--tag='+tag,'--mode=point','--levels=80,320,2560','--seconds=15']
   subprocess.run(['sudo','-n','python3',str(W/'host.py'),'prepare'],check=True)
   try:
    print('START',tag,time.time(),flush=True)
    with (W/(tag+'.log')).open('w') as f:subprocess.run(args,cwd=R.parents[1],stdout=f,stderr=subprocess.STDOUT,check=True)
   finally:subprocess.run(['sudo','-n','python3',str(W/'host.py'),'restore'],check=True)
   subprocess.run(['sudo','-n','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(raw)],check=True)
  assert json.loads((raw/'server-exit.json').read_text())['code']==0
  assert json.loads((raw/'complete.json').read_text())['failures_total']==0
  proof=json.loads(next(raw.glob('provenance-*.json')).read_text());assert proof['source_commit']==v['commit'] and proof['sha256']==v['sha256']
  for f in raw.glob('*.result.json'):
   result=json.loads(f.read_text());assert result['operation']=='XADD_MAXLEN';results.append({'round':round_,'version':label,'tag':tag,'connections':result['connections'],'qps':result['qps'],'p99_ms':result['p99_ms']})
  (W/'stream-write-repeats.json').write_text(json.dumps({'main':V['main'],'candidate':V['candidate'],'rows':results,'method':'Three independent seed pairs ordered A/B, B/A, A/B; 15-second XADD MAXLEN points at 80/320/2560 connections; same baseline workload and settings; no concurrent build, tests or perf.'},indent=2)+'\n')
  print('COMPLETE',tag,time.time(),flush=True)
