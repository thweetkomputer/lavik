from pathlib import Path
import argparse,json,os,subprocess,time
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
p=argparse.ArgumentParser();p.add_argument('kind');p.add_argument('size',type=int);p.add_argument('field',type=int);p.add_argument('keys',type=int);p.add_argument('category',choices=['ordered','lset','hashset']);p.add_argument('--profile',action='store_true');p.add_argument('--version',default='main');a=p.parse_args()
v=json.loads((W/'versions.json').read_text())[a.version]
tag=f'{a.version}{v["commit"][:8]}-{a.category}-{a.kind}-{a.size}-k{a.keys}-f{a.field}-20261004'
raw=R/'raw'/('lavik-'+tag)
def run(args):
 with (W/'commands.jsonl').open('a') as f:f.write(json.dumps({'time':time.time(),'argv':args,'cwd':str(R.parents[1])})+'\n')
 subprocess.run(args,cwd=R.parents[1],check=True)
if (raw/'complete.json').exists():
 assert json.loads((raw/'server-exit.json').read_text())['code']==0
 print('ALREADY_COMPLETE',tag,flush=True);raise SystemExit(0)
assert not raw.exists(),f'Unfinished run needs explicit resume: {raw}'
base=['lavik','--binary='+v['binary'],'--source-repo='+v['source_repo'],'--source-commit='+v['commit'],'--types='+a.kind,'--sizes='+str(a.size),'--fields='+str(a.field),'--keys='+str(a.keys)]
guard=['sudo','-n','env','LAVIK_BENCH_ROOT='+str(R),'LAVIK_LSET_NO_PERF=1','python3',str(R/'run_with_memory_guard.py'),'--minimum-available-gib=20','--','python3']
run(['sudo','-n','python3',str(W/'host.py'),'prepare'])
try:
 print('START',tag,time.time(),flush=True)
 if a.category=='hashset':
  fixture=Path('/mnt/dev/lavik-benchmark-binaries')/f'lavik-{a.kind}-{"1m" if a.size==1048576 else "100m"}-f{a.field}-generated.dump'
  assert fixture.exists()
  run(guard+[str(R/'run.py'),*base,'--tag=seed-'+tag,'--seed-dump-path='+str(fixture),'--fill-workers='+('32' if a.keys==50000 else '8'),'--mode=full','--levels=1','--seconds=1'])
  run(guard+[str(R/'run.py'),*base,'--tag='+tag,'--reuse-seeded-data','--seed-source-tag=seed-'+tag,'--mode=both','--levels=80,320,1280,2560,5120','--full-levels='+('1,4,16' if a.size==104857600 else '16,80'),'--seconds=8','--continue-on-error'])
 elif a.category=='lset':
  run(guard+['/mnt/dev/lavik-test-data-20261001/bench-lset-large.py',*base,'--tag='+tag,'--levels=80,320,1280,2560,5120','--full-levels=1','--seconds=10','--mode=point','--fill-workers=32','--seed-pipeline=4','--seed-command-bytes=131072'])
 else:
  run(guard+[str(R/'run.py'),*base,'--tag='+tag,'--mode=both','--levels=80,320,1280,2560,5120','--full-levels='+('1,4,16' if a.size==104857600 else '16,80'),'--seconds=8','--continue-on-error'])
 if a.profile:
  assert a.kind=='stream'
  run(guard+['/mnt/dev/lavik-write-paths-20261003/profile-stream-allworkers.py',*base,'--tag=diagnostic-'+tag,'--reuse-seeded-data','--seed-source-tag='+tag,'--mode=point','--levels=80','--seconds=30'])
 print('COMPLETE',tag,time.time(),flush=True)
finally:run(['sudo','-n','python3',str(W/'host.py'),'restore'])
for source_tag in [tag]+(['seed-'+tag] if a.category=='hashset' else []):
 source=R/'raw'/('lavik-'+source_tag)
 proof=source/'source-build-verification.json'
 run(['sudo','-n','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(source)])
 proof.write_text(json.dumps(v,indent=2)+'\n')
(W/(tag+'-host.json')).write_text(json.dumps({'original':json.loads((R/'spdk-host-original.json').read_text()),'restored':json.loads((R/'spdk-restored.json').read_text())},indent=2)+'\n')
