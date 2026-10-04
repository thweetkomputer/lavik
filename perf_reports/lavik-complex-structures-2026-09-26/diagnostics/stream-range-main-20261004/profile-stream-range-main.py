from pathlib import Path
import json,subprocess,os
w=Path(__file__).parent;r=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
v=json.loads((w/'versions.json').read_text())['main'];seed='maina565d603-ordered-stream-104857600-k8-f128-20261004';tag='diagnostic-full-reused-'+seed
raw=r/'raw'/('lavik-'+tag)
assert not raw.exists(),raw
subprocess.run(['sudo','-n','python3',str(w/'host.py'),'resume'],check=True)
try:
 subprocess.run(['sudo','-n','env','LAVIK_BENCH_ROOT='+str(r),'LAVIK_LSET_NO_PERF=1','python3',str(r/'run_with_memory_guard.py'),'--minimum-available-gib=20','--','python3',str(w/'profile-ordered-allworkers.py'),'lavik','--binary='+v['binary'],'--source-repo='+v['source_repo'],'--source-commit='+v['commit'],'--types=stream','--sizes=104857600','--fields=128','--keys=8','--tag='+tag,'--reuse-seeded-data','--seed-source-tag='+seed,'--mode=full','--levels=1','--full-levels=1','--seconds=30'],cwd=r.parents[1],check=True)
finally:subprocess.run(['sudo','-n','python3',str(w/'host.py'),'restore'],check=True)
subprocess.run(['sudo','-n','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(raw)],check=True)
(raw/'source-build-verification.json').write_text(json.dumps(v,indent=2)+'\n')
(w/'stream-range-main-host.json').write_text(json.dumps({'original':json.loads((r/'spdk-host-original.json').read_text()),'restored':json.loads((r/'spdk-restored.json').read_text())},indent=2)+'\n')
