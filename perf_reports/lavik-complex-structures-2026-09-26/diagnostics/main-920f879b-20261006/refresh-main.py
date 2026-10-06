from pathlib import Path
import hashlib,json,subprocess,sys,time
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
def execute(argv,name):
 print('START',name,time.time(),flush=True)
 with (W/(name+'.log')).open('w') as log:subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True)
 print('COMPLETE',name,time.time(),flush=True)
execute(['python3',str(W/'validate-native.py')],'native-driver')
assert 'ALL_MAIN_NATIVE_TESTS_PASS' in (W/'native-driver.log').read_text()
sys.path.insert(0,'/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
lock=acquire_host('main920f879b-complete-report-refresh')
v=json.loads((W/'versions.json').read_text())['main']
assert v['commit']=='920f879b05636d066ef0485f1ee1121813ef79ac'
with Path(v['binary']).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==v['sha256']
manifest=json.loads((W/'previous-current-main.json').read_text());imports=json.loads((W/'previous-current-imports.json').read_text())
rows=sorted(manifest['plots'],key=lambda r:(r['category']!='ordered',r['size'],r['kind'],r['field']))
completed=[]
for row in rows:
 args=[str(row[k]) for k in ('kind','size','field','keys','category')]
 execute(['python3',str(W/'run-condition.py'),*args],'main-grid-'+'-'.join(args))
 completed.append({k:row[k] for k in ('kind','size','field','keys','category')})
 (W/'main-refresh-progress.json').write_text(json.dumps(completed,indent=2)+'\n')
for row in imports['plots']:
 execute(['python3',str(W/'run-import.py'),row['kind'],str(row['field'])],f'main-import-{row["kind"]}-{row["field"]}')
assert len(completed)==28
sys.path.insert(0,str(R));import spdk_host
assert not (R/'spdk-ready.json').exists();spdk_host.no_servers();spdk_host.assert_driver('nvme')
(W/'host-final.json').write_text(json.dumps({'no_servers':True,'scratch_drivers':'nvme','spdk_ready_absent':True},indent=2)+'\n')
print('ALL_MAIN_GRIDS_AND_IMPORTS_COMPLETE',time.time(),flush=True)
