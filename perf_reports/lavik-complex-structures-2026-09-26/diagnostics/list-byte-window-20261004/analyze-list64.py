from pathlib import Path
from collections import Counter
import json,re
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26/raw')
rows=[]
for label,name in [('previous','list-reply-versions.json'),('candidate','list64-versions.json')]:
 v=json.loads((W/name).read_text())['candidate'];tag=f'diagnostic-full-candidate{v["commit"][:8]}-ordered-list-104857600-k8-f128-20261004';p=R/('lavik-'+tag)/'diagnostic-c1';counts=Counter();total=0
 for f in p.glob('stacks-*.txt'):
  for block in f.read_text().split('\n\n'):
   lines=block.splitlines()
   if len(lines)<2:continue
   m=re.search(r'\s(\d+) task-clock:',lines[0])
   if not m:continue
   weight=int(m[1]);total+=weight
   for kind,needle in [('memmove','__memmove'),('worker_run_once','Worker::RunOnce'),('storage_poll','PollStorage'),('allocator','_mi_theap_malloc_zero')]:
    if needle in lines[1]:counts[kind]+=weight
   if '__memmove' in lines[1] and 'AppendBulkArray' in '\n'.join(lines[2:]):counts['memmove_array_reply']+=weight
 assert total>0
 metrics={}
 for phase in ['before','after']:
  metrics[phase]={}
  for l in (p/(phase+'.prom')).read_text().splitlines():
   if l and not l.startswith('#'):
    k,value=l.rsplit(' ',1);metrics[phase][k]=float(value)
 key='lavik_command_calls_total{command="lrange"}';n=metrics['after'].get(key,0)-metrics['before'].get(key,0);assert n>0
 io={}
 for family in ['operations','bytes']:
  for op in ['read','write']:
   key=f'lavik_storage_io_{family}_total{{operation="{op}"}}';delta=metrics['after'].get(key,0)-metrics['before'].get(key,0);io[op+'_'+family]={'delta':delta,'per_command':delta/n}
 rows.append({'version':label,'commit':v['commit'],'profile_tag':tag,'task_clock_seconds':total/1e9,'self_cpu_percent':{k:100*n/total for k,n in counts.items()},'metric_commands':n,'io':io})
result={'rows':rows,'limitations':'All-worker 25 s sampled task-clock, including polling/background/kernel work, is not a latency fraction. Counters span a separate 30 s diagnostic. Copy stack attribution does not distinguish every growth copy from required serialization. Use clean sweeps/paired repeats for QPS.'}
(W/'list64-profile-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
for r in rows:print(r['version'],r['self_cpu_percent'],r['io'])
