from pathlib import Path
import json,time
W=Path(__file__).parent
assert 'ALL_PUSHOPT_NATIVE_TESTS_PASS' in (W/'native-driver.log').read_text()
from benchmark import point, R
rows=[]
protocol={'rounds':[4,5,6],'orders':[['main','pushopt'],['pushopt','main'],['main','pushopt']], 'size_per_key':8388608,'keys':8,'value_bytes':1024,'connections':320,'seconds':30,'pipeline':1,'client_threads':16,'operation':'RPUSH_LPOP','selection':'Independent uniform key and independent 50/50 push/pop per command; exact final cardinality checks and bounded guard. Fresh server/media/seed for every point.','baseline':'Merged main cc31b3a6; frozen binary from identical c8f128dc tree, documented in versions.json.','exploratory_runs':'../lavik-rpush-lpop-20261008 contains the initial main exploration and rejected combined candidate; excluded from this paired summary.','perf':'Independent 25-second 99Hz DWARF worker profiles, not clean QPS points.'}
(W/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
assert not (W/'pairs.json').exists()
for round_,labels in zip(protocol['rounds'],protocol['orders']):
 for label in labels:
  rows.append(point(label,'list',8388608,'RPUSH_LPOP',round_))
  (W/'pairs.json').write_text(json.dumps(rows,indent=2)+'\n')
profiles=[]
for label in ['main','pushopt']:
 p=point(label,'list',8388608,'RPUSH_LPOP',4,True)
 p['perf']=str(next(Path(p['raw']).glob('*.perf')))
 profiles.append(p)
 (W/'profiles.json').write_text(json.dumps(profiles,indent=2)+'\n')
assert not (R/'spdk-ready.json').exists()
print('ALL_PUSHOPT_PAIRS_AND_PERF_COMPLETE',time.time(),flush=True)
