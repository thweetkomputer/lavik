"""Serialize PR275 validation after the entire existing Hash/Set measurement chain."""
from pathlib import Path
import json,subprocess,time
W=Path(__file__).parent
H=Path('/mnt/dev/lavik-hashset-write-20261006')
launch=json.loads((H/'matched-seed-launch.json').read_text())
assert launch['pid']==1209159 and str(launch['generation'])=='38109358'
stat=Path('/proc')/str(launch['pid'])/'stat'
print('WAIT_FOR_HASHSET_COMPLETE_CHAIN',launch,flush=True)
while stat.exists():
 try:
  fields=stat.read_text().split()
  if fields[21]!=str(launch['generation']) or fields[2]=='Z':break
 except FileNotFoundError:break
 time.sleep(10)
assert 'ALL_MATCHED_SEED_MEASUREMENTS_COMPLETE' in (H/'matched-seed-chain.log').read_text()
for job,logname in [('validate-native','native-driver'),('repeat-stream-window','repeat-driver')]:
 print('START_JOB',job,time.time(),flush=True)
 with (W/(logname+'.log')).open('w') as log:
  subprocess.run(['python3',str(W/(job+'.py'))],stdout=log,stderr=subprocess.STDOUT,check=True)
print('ALL_PR275_REBASED_MEASUREMENTS_COMPLETE',time.time(),flush=True)
