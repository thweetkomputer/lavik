from pathlib import Path
from collections import Counter
import json,re
W=Path(__file__).parent;R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26/raw');V=json.loads((W/'zset-probe-versions.json').read_text())
rows=[]
for label,v in V.items():
 tag=f'{label}{v["commit"][:8]}-ordered-zset-104857600-k8-f1024-20261004';p=R/('lavik-diagnostic-'+tag)/'diagnostic-c80'
 counts=Counter();callers=Counter();total=0
 for f in p.glob('stacks-*.txt'):
  for b in f.read_text().split('\n\n'):
   ls=b.splitlines()
   if len(ls)<2:continue
   m=re.search(r'\s(\d+) task-clock:',ls[0])
   if not m:continue
   weight=int(m[1]);total+=weight;leaf=ls[1]
   for name,needle in [('siphash','SipHash12'),('memmove','__memmove'),('allocator','_mi_theap_malloc_zero')]:
    if needle in leaf:counts[name]+=weight
   if 'SipHash12' in leaf:
    context='\n'.join(ls[2:]);caller='other'
    for category,needle in [('leaf_loading','LoadHashGroupSnapshot'),('split_validation','ValidateFields'),('routing','HashGroupDirectory::Find')]:
     if needle in context:caller=category;break
    callers[caller]+=weight
 metrics={}
 for phase in ['before','after']:
  metrics[phase]={}
  for l in (p/(phase+'.prom')).read_text().splitlines():
   if l and not l.startswith('#'):
    k,value=l.rsplit(' ',1);metrics[phase][k]=float(value)
 command='lavik_command_calls_total{command="zincrby"}'
 n=metrics['after'].get(command,0)-metrics['before'].get(command,0);assert n>0
 io={}
 for family in ['operations','bytes']:
  for operation in ['read','write']:
   k=f'lavik_storage_io_{family}_total{{operation="{operation}"}}';delta=metrics['after'][k]-metrics['before'][k]
   io[operation+'_'+family]={'delta':delta,'per_command':delta/n}
 rows.append({'version':label,'commit':v['commit'],'profile_tag':'diagnostic-'+tag,'profile_task_clock_seconds':total/1e9,'self_cpu_percent':{k:100*x/total for k,x in counts.items()},'siphash_caller_cpu_percent':{k:100*x/total for k,x in callers.items()},'completed_zincrby_commands_during_metrics_interval':n,'io':io})
out={'rows':rows,'limitations':'25-second sampled task-clock includes polling, background and kernel CPU; shares are not latency fractions. Metrics span the separate 30-second diagnostic and include all server storage work; physical read counts are not logical leaf loads. Clean sweeps and independent paired runs are the throughput evidence.'}
(W/'zset-probe-profile-comparison.json').write_text(json.dumps(out,indent=2)+'\n')
for row in rows:print(row['version'],row['self_cpu_percent'],row['siphash_caller_cpu_percent'],{k:round(v['per_command'],3) for k,v in row['io'].items()})
