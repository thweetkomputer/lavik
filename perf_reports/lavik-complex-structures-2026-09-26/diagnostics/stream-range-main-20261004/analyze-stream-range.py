from pathlib import Path
from collections import Counter
import json,re
w=Path(__file__).parent;r=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
tag='diagnostic-full-reused-maina565d603-ordered-stream-104857600-k8-f128-20261004';raw=r/'raw'/('lavik-'+tag);p=raw/'diagnostic-c1'
leafs=Counter();callers=Counter();total=0
for f in p.glob('stacks-*.txt'):
 for block in f.read_text().split('\n\n'):
  ls=block.splitlines()
  if len(ls)<2:continue
  m=re.search(r'\s(\d+) task-clock:',ls[0])
  if not m:continue
  weight=int(m[1]);total+=weight
  leaf=re.sub(r'^\s*[0-9a-f]+\s+','',ls[1]);leaf=re.sub(r' \([^()]*\)$','',leaf)
  leafs[leaf]+=weight
  if '__memmove' in leaf or '__memcpy' in leaf:
   for name in ['ExecuteGroupedStreamRange','AppendStream','EncodeStream','DecodeStream','AppendBulk','GroupedCollectionAsCompact','EncodeOrderedCompact','DecodeOrderedCompact']:
    if name in block:callers[name]+=weight
metrics={}
for phase in ('before','after'):
 metrics[phase]={}
 for l in (p/(phase+'.prom')).read_text().splitlines():
  if l and not l.startswith('#'):
   k,value=l.rsplit(' ',1);metrics[phase][k]=float(value)
key='lavik_command_calls_total{command="xrange"}'
n=metrics['after'].get(key,0)-metrics['before'].get(key,0);assert n>0
io={}
for family in ('operations','bytes'):
 for op in ('read','write'):
  key=f'lavik_storage_io_{family}_total{{operation="{op}"}}';delta=metrics['after'].get(key,0)-metrics['before'].get(key,0)
  io[op+'_'+family]={'delta':delta,'per_command':delta/n}
before=json.loads((raw/'stream-104857600-128.validate.json').read_text()) if (raw/'stream-104857600-128.validate.json').exists() else None
result={'profile_tag':tag,'source_commit':'a565d603523467ed7bbb9ed9227ddd6b18a9ca8c','task_clock_seconds':total/1e9,'commands_in_metrics_interval':n,'io':io,'top_self':[{'symbol':k,'percent':100*v/total} for k,v in leafs.most_common(35)],'memmove_caller_self_percent':{k:100*v/total for k,v in callers.items()},'limitations':'All-worker task-clock self samples include polling/background/kernel work and are not latency fractions. Perf spans 25 seconds; command/IO counters span a separate 30-second diagnostic. Reused post-write Stream population has 819207..819284 entries/key (nominal 819200), unchanged across read-only sampling. Not a clean QPS comparison.'}
(w/'stream-range-main-profile.json').write_text(json.dumps(result,indent=2)+'\n')
print('io',io,'commands',n)
for row in result['top_self'][:16]:print(round(row['percent'],2),row['symbol'][:190])
print('memmove callers',result['memmove_caller_self_percent'])
