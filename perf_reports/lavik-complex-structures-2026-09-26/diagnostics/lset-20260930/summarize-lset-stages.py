import collections,json,re,sys
from pathlib import Path
root=Path(sys.argv[1]);result=collections.defaultdict(lambda:dict(calls=0,samples=0,ns=0,max_ns=0,workers=[]))
for m in re.finditer(r'LSET_PROFILE tid=(\d+) stage=(\w+) calls=(\d+) samples=(\d+) ns=(\d+) max_ns=(\d+)',(root/'server.log').read_text()):
 tid,stage,calls,samples,ns,max_ns=m.groups();s=result[stage]
 for k,v in [('calls',calls),('samples',samples),('ns',ns)]:s[k]+=int(v)
 s['max_ns']=max(s['max_ns'],int(max_ns));s['workers'].append(int(tid))
assert result
for s in result.values():s['mean_us']=s['ns']/s['samples']/1000
calls={s['calls'] for s in result.values()};samples={s['samples'] for s in result.values()};assert len(calls)==len(samples)==1
(root/'stage-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:round(v['mean_us'],3) for k,v in result.items()}))
