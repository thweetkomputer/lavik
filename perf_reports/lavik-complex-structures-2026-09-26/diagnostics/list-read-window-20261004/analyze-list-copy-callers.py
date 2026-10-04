from pathlib import Path
from collections import Counter
import json,re
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26/raw')
v=json.loads((W/'list-window-versions.json').read_text())['candidate']
p=R/f'lavik-diagnostic-full-candidate{v["commit"][:8]}-ordered-list-104857600-k8-f128-20261004/diagnostic-c1'
counts=Counter();total=0;copies=0
for f in p.glob('stacks-*.txt'):
 for block in f.read_text().split('\n\n'):
  lines=block.splitlines()
  if len(lines)<2:continue
  m=re.search(r'\s(\d+) task-clock:',lines[0])
  if not m:continue
  weight=int(m[1]);total+=weight
  if '__memmove' not in lines[1]:continue
  copies+=weight;context='\n'.join(lines[2:]);category='other'
  for name,needle in [('resp_bulk_array','AppendBulkArray'),('list_decode','DecodeOrderedListRange'),('storage_payload','ReadValue')]:
   if needle in context:category=name;break
  counts[category]+=weight
result={'candidate_commit':v['commit'],'all_task_clock_seconds':total/1e9,'memmove_self_cpu_percent':100*copies/total,'caller_self_cpu_percent':{k:100*n/total for k,n in counts.items()},'limitation':'Full-stack attribution of sampled memmove self CPU. This distinguishes command paths, not every realloc copy from payload serialization; no inferred wall-latency fractions.'}
(W/'list-window-copy-callers.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
