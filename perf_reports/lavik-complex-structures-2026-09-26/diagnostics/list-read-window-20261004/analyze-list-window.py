from pathlib import Path
from collections import Counter
import json, re
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26/raw')
V=json.loads((W/'list-window-versions.json').read_text())
rows=[]
for label,v in V.items():
 for kind,command,connections,prefix in [('range','lrange',1,'diagnostic-full-'),('write','lset',80,'diagnostic-')]:
  tag=f'{prefix}{label}{v["commit"][:8]}-ordered-list-104857600-k8-f128-20261004'
  p=R/('lavik-'+tag)/f'diagnostic-c{connections}'
  counts=Counter();total=0
  for f in p.glob('stacks-*.txt'):
   for b in f.read_text().split('\n\n'):
    ls=b.splitlines()
    if len(ls)<2:continue
    m=re.search(r'\s(\d+) task-clock:',ls[0])
    if not m:continue
    weight=int(m[1]);total+=weight;leaf=ls[1]
    for name,needle in [('worker_run_once','Worker::RunOnce'),('storage_poll','PollStorage'),('memmove','__memmove'),('allocator','_mi_theap_malloc_zero'),('crc','crc32_iscsi')]:
     if needle in leaf:counts[name]+=weight
  assert total>0, p
  metrics={}
  for phase in ['before','after']:
   metrics[phase]={}
   for l in (p/(phase+'.prom')).read_text().splitlines():
    if l and not l.startswith('#'):
     k,value=l.rsplit(' ',1);metrics[phase][k]=float(value)
  key=f'lavik_command_calls_total{{command="{command}"}}'
  n=metrics['after'].get(key,0)-metrics['before'].get(key,0);assert n>0
  io={}
  for family in ['operations','bytes']:
   for op in ['read','write']:
    key=f'lavik_storage_io_{family}_total{{operation="{op}"}}'
    delta=metrics['after'].get(key,0)-metrics['before'].get(key,0)
    io[op+'_'+family]={'delta':delta,'per_command':delta/n}
  rows.append({'version':label,'commit':v['commit'],'operation':command.upper(),'connections':connections,'profile_tag':tag,'profile_task_clock_seconds':total/1e9,'self_cpu_percent':{k:100*x/total for k,x in counts.items()},'completed_commands_in_metrics_interval':n,'io':io})
result={'rows':rows,'limitations':'Task-clock self CPU includes polling, background and kernel work and is not a latency fraction. Perf spans 25 s; command and I/O counters span the separate 30 s diagnostic. Diagnostic throughput is excluded from clean curves. Physical I/O includes all server work.'}
(W/'list-window-profile-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
for row in rows:print(row['version'],row['operation'],row['self_cpu_percent'],row['io'])
