from pathlib import Path
import json,statistics
W=Path(__file__).parent
m=json.loads((W/'stream-write-repeats.json').read_text())
summary=[]
for c in [80,320,2560]:
 pairs=[]
 for r in [1,2,3]:
  a=next(x for x in m['rows'] if x['round']==r and x['connections']==c and x['version']=='main')
  b=next(x for x in m['rows'] if x['round']==r and x['connections']==c and x['version']=='candidate')
  pairs.append({'round':r,'main_qps':a['qps'],'candidate_qps':b['qps'],'change_percent':100*(b['qps']/a['qps']-1),'main_p99_ms':a['p99_ms'],'candidate_p99_ms':b['p99_ms']})
 row={'connections':c,'pairs':pairs,'median_main_qps':statistics.median(x['main_qps'] for x in pairs),'median_candidate_qps':statistics.median(x['candidate_qps'] for x in pairs),'median_paired_change_percent':statistics.median(x['change_percent'] for x in pairs),'paired_change_range_percent':[min(x['change_percent'] for x in pairs),max(x['change_percent'] for x in pairs)]}
 summary.append(row);print(json.dumps(row))
(W/'stream-write-repeat-summary.json').write_text(json.dumps({'main':m['main'],'candidate':m['candidate'],'method':m['method'],'conditions':summary,'limitations':'Three paired repetitions, not a confidence interval; matched workload on one host; historical peer systems are not rerun.'},indent=2)+'\n')
