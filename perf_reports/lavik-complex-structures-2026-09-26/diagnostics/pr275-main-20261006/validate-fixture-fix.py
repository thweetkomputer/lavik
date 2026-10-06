from pathlib import Path
import json,subprocess,time,sys
sys.path.insert(0,'/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
W=Path(__file__).parent;S=Path('/mnt/dev/lavik-pr275-main-20261006');H=Path('/mnt/dev/lavik-hashset-write-20261006')
launch=json.loads((H/'matched-seed-launch.json').read_text());stat=Path('/proc')/str(launch['pid'])/'stat'
while stat.exists():
 try:
  fields=stat.read_text().split()
  if fields[21]!=str(launch['generation']) or fields[2]=='Z':break
 except FileNotFoundError:break
 time.sleep(10)
assert 'ALL_MATCHED_SEED_MEASUREMENTS_COMPLETE' in (H/'matched-seed-chain.log').read_text()
lock=acquire_host('pr275-rebased-fixture-regressions')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()=='eccea5c79d4e71e39ae1e1217aecb226f4ff75e9'
paths=['tests/meta_integration/test_data_control_fixture_startup.py','tests/meta_integration/test_native_fixture_startup.py']
assert set(subprocess.check_output(['git','diff','--name-only'],cwd=S,text=True).splitlines())==set(paths)
for name,argv in [('format',['/tmp/lavik-precommit-venv/bin/pre-commit','run','--files',*paths]),('data-control',['python3',paths[0]]),('native-startup',['python3',paths[1]]),('diff-check',['git','diff','--check'])]:
 print('START',name,time.time(),flush=True)
 with (W/('fixture-fix-'+name+'.log')).open('w') as log:subprocess.run(argv,cwd=S,stdout=log,stderr=subprocess.STDOUT,check=True)
 print('PASS',name,time.time(),flush=True)
print('ALL_PR275_FIXTURE_TESTS_PASS',flush=True)
