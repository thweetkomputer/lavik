from pathlib import Path
import json,re,collections,subprocess
W=Path(__file__).parent
profiles=json.loads((W/'profiles.json').read_text());out=[]
patterns={'directory_apply':['OrderedGroupDirectory::Apply','OrderedGroupDirectory::ReplacePages'],
          'directory_build':['OrderedGroupDirectory::Build','OrderedGroupDirectory::From'],
          'rank_lookup':['FenwickTree::Prefix','FenwickTree::LowerBound','OrderedGroupDirectory::CountBefore'],
          'cow_array':['CowArray<'], 'copy':['memcpy','memmove'],
          'allocate':['malloc','AllocateRetained','operator new'],
          'release':['operator delete','DeallocateRetained'],
          'ordered_page_read':['LoadOrderedPage','LoadOrderedListRange','LoadSortedSetPage'],
          'member_lookup':['LoadHashGroupPayload']}
# Generic inlined names such as Apply or Build are ambiguous. Classify only
# qualified symbols or the specific directory helper names below.
inline_aliases={'directory_apply':{'ApplyList','ReplacePages','AnalyzeChanges'},
                'directory_build':{'BuildListSlots'},'rank_lookup':{'CountBefore'}}
def matched(category,symbol):
 return any(m in symbol for m in patterns[category]) or symbol in inline_aliases.get(category,set())

def physical_summary(directory):
 # Decode only after every profiling run has ended, so this extra symbolization
 # cannot contend with a measured server. Physical frames retain the enclosing
 # qualified function when a method such as directory Apply was inlined.
 total=0;samples=0;self_weight=collections.Counter();inclusive=collections.Counter();categories=collections.Counter()
 for file in directory.glob('cpu-*.perf'):
  decoded=directory/('physical-'+file.stem[4:]+'.txt')
  if not decoded.exists():
   with decoded.open('w') as out:
    subprocess.run(['perf','script','--no-inline','-F','comm,pid,tid,time,period,event,ip,sym,dso','-i',str(file)],stdout=out,stderr=subprocess.DEVNULL,check=True)
  period=0;stack=[]
  def flush():
   nonlocal total,samples
   if not period or not stack:return
   total+=period;samples+=1;self_weight[stack[0]]+=period
   for symbol in set(stack):inclusive[symbol]+=period
   for cat,match in patterns.items():
    if any(any(m in s for m in match) for s in stack):categories[cat]+=period
  with decoded.open() as f:
   for line in f:
    if not line.strip():flush();period=0;stack=[];continue
    m=re.search(r'\s(\d+) task-clock:',line)
    if m:flush();period=int(m[1]);stack=[];continue
    if line.startswith('\t'):
     parts=line.strip().split(None,1)
     if len(parts)==2:stack.append(parts[1].rsplit(' (',1)[0])
  flush()
 def top(c):return [{'symbol':s,'sampled_ns':v,'share_pct':100*v/total} for s,v in c.most_common(30)]
 return {'samples':samples,'sampled_worker_ns':total,'inclusive_categories_pct':{k:100*v/total for k,v in categories.items()},'top_self':top(self_weight),'top_inclusive':top(inclusive)}
for p in profiles:
 total=0;samples=0;self_weight=collections.Counter();inclusive=collections.Counter();categories=collections.Counter();cats_self=collections.Counter();threads={}
 for file in Path(p['perf']).glob('stacks-*.txt'):
  period=0;stack=[];thread_samples=0
  def flush():
   global total,samples,thread_samples
   if not period or not stack:return
   total+=period;samples+=1;thread_samples+=1;self_weight[stack[0]]+=period
   for sym in set(stack):inclusive[sym]+=period
   for cat,match in patterns.items():
    if any(matched(cat,s) for s in stack):categories[cat]+=period
    if matched(cat,stack[0]):cats_self[cat]+=period
  with file.open() as f:
   for line in f:
    if not line.strip():flush();period=0;stack=[];continue
    m=re.search(r'\s(\d+) task-clock:',line)
    if m:flush();period=int(m[1]);stack=[];continue
    if line.startswith('\t'):
     parts=line.strip().split(None,1)
     if len(parts)==2:stack.append(parts[1].rsplit(' (',1)[0])
  flush();threads[file.name]=thread_samples
 assert total>0 and samples>0
 def top(c):return [{'symbol':s,'sampled_ns':v,'share_pct':100*v/total} for s,v in c.most_common(30)]
 result={'size':p['size'],'kind':p['kind'],'operation':p['operation'],'version':p['version'],'samples':samples,'sampled_worker_ns':total,'samples_per_thread':threads,'inclusive_categories_pct':{k:100*v/total for k,v in categories.items()},'self_categories_pct':{k:100*v/total for k,v in cats_self.items()},'top_self':top(self_weight),'top_inclusive':top(inclusive),'raw':p['raw'],'notes':'25-second 99Hz task-clock samples across existing workers, with inline frames. Shares include polling, kernel and background work; inclusive categories overlap. Independent diagnostic run, not clean-QPS comparison.'}
 result['physical']=physical_summary(Path(p['perf']))
 assert result['physical']['samples']==samples and result['physical']['sampled_worker_ns']==total
 result['notes']+=' Qualified enclosing functions are retained separately in physical; inline index categories recognize unique unqualified DWARF names.'
 out.append(result)
 print(p['kind'],p['operation'],p['version'],'samples',samples,'inclusive',result['inclusive_categories_pct'],'self',result['self_categories_pct'])
(W/'perf-summary.json').write_text(json.dumps(out,indent=2)+'\n')
