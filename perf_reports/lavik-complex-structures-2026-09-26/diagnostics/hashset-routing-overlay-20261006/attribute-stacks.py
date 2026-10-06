"""Attribute sampled allocator/hash leaf frames to their nearest Lavik caller."""
from pathlib import Path
from collections import Counter
import json,re,sys
source=Path(sys.argv[1]);output=Path(sys.argv[2]);result={}
for label,profile in json.loads(source.read_text())['profiles'].items():
 total=0;categories={'allocator':Counter(),'siphash':Counter(),'routing_inclusive':Counter()}
 for path in Path(profile['directory']).glob('stacks-*.txt'):
  for block in path.read_text().split('\n\n'):
   lines=block.splitlines()
   if len(lines)<2:continue
   event=re.search(r':\s+(\d+) task-clock:',lines[0]);assert event,lines[0]
   weight=int(event[1]);total+=weight
   frames=[line.strip().split(' ',1)[1].split(' (/')[0] for line in lines[1:] if line.strip()]
   for category,match in [('allocator',any(x in frames[0] for x in ['malloc','mi_free'])),('siphash','SipHash12' in frames[0])]:
    if match:
     caller=next((frame for frame in frames[1:] if 'lavik::' in frame),'unresolved');categories[category][caller]+=weight
   if any('HashGroupMap<' in frame for frame in frames):categories['routing_inclusive']['Any HashGroupMap frame']+=weight
 result[label]={'total_event_weight':total,'categories':{cat:[{'caller':k,'event_weight':n,'percent':100*n/total} for k,n in counts.most_common()] for cat,counts in categories.items()}}
output.write_text(json.dumps({'profiles':result,'limits':'Sampled call-stack attribution includes polling/background/kernel in denominator. Allocator category matches malloc/mi_free leaf symbols; it is not every allocation and does not prove zero initialization. DWARF truncation/inlining/unresolved frames can omit callers. Shares are not allocation counts, per-command CPU, or QPS gains.'},indent=2)+'\n')
