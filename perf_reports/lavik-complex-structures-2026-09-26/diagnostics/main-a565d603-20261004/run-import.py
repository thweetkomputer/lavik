from pathlib import Path
import hashlib,json,os,subprocess,sys,time
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
v=json.loads((W/'versions.json').read_text())['main']
kind,field=sys.argv[1:];field=int(field)
assert kind in ['hash','set'] and field in [128,1024]
tag=f'main{v["commit"][:8]}-import-{kind}-1048576-k50000-f{field}-20261004'
raw=R/'raw'/('lavik-'+tag)
if (raw/'complete.json').exists():
 assert json.loads((raw/'server-exit.json').read_text())['code']==0
 print('ALREADY_COMPLETE',tag,flush=True);raise SystemExit(0)
assert not raw.exists(),raw
def run(args):
 with (W/'commands.jsonl').open('a') as f:f.write(json.dumps({'time':time.time(),'argv':args,'cwd':str(R.parents[1])})+'\n')
 subprocess.run(args,cwd=R.parents[1],check=True)
run(['sudo','-n','python3',str(W/'host.py'),'prepare'])
try:
 print('START',tag,time.time(),flush=True)
 run(['sudo','-n','env','LAVIK_BENCH_ROOT='+str(R),'python3',str(R/'run_with_memory_guard.py'),'--minimum-available-gib=20','--','python3',str(R/'seed_batched_import.py'),'lavik','--binary='+v['binary'],'--source-repo='+v['source_repo'],'--source-commit='+v['commit'],'--tag='+tag,'--types='+kind,'--sizes=1048576','--fields='+str(field),'--keys=50000','--mode=full','--levels=1','--seconds=1','--fill-workers=8','--seed-pipeline=64','--seed-command-bytes=16384'])
 print('COMPLETE',tag,time.time(),flush=True)
finally:run(['sudo','-n','python3',str(W/'host.py'),'restore'])
run(['sudo','-n','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(raw)])
assert json.loads((raw/'complete.json').read_text())['failures_total']==0
assert json.loads((raw/'server-exit.json').read_text())['code']==0
(raw/'source-build-verification.json').write_text(json.dumps(v,indent=2)+'\n')
(raw/'seed-client-proof.json').write_text(json.dumps({'wrapper':'seed_batched_import.py','sha256':hashlib.sha256((R/'seed_batched_import.py').read_bytes()).hexdigest(),'client_encoding':'per-command','wire_workload':'8 clients, pipeline 64, 16 KiB entry batches, disjoint keys'},indent=2)+'\n')
(W/(tag+'-host.json')).write_text(json.dumps({'original':json.loads((R/'spdk-host-original.json').read_text()),'restored':json.loads((R/'spdk-restored.json').read_text())},indent=2)+'\n')
