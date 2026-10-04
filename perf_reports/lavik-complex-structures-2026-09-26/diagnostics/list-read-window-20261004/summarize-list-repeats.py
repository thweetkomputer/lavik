from pathlib import Path
import json, statistics
W=Path(__file__).parent
m=json.loads((W/'list-range-repeats.json').read_text())
summary=[]
for operation,c in [('LRANGE',1),('LRANGE',4),('LRANGE',16),('LINDEX',320)]:
 pairs=[]
 for r in [1,2,3]:
  a=next(x for x in m['rows'] if x['operation']==operation and x['round']==r and x['connections']==c and x['version']=='main')
  b=next(x for x in m['rows'] if x['operation']==operation and x['round']==r and x['connections']==c and x['version']=='candidate')
  pair={'round':r}
  for name,result in [('main',a),('candidate',b)]:
   pair[name+'_status']='error' if 'error' in result else 'success'
   if 'error' in result:pair[name+'_error']=result['error']
   else:pair[name+'_qps']=result['qps'];pair[name+'_p99_ms']=result['p99_ms']
  if 'error' not in a and 'error' not in b:pair['change_percent']=100*(b['qps']/a['qps']-1)
  pairs.append(pair)
 good=[p['change_percent'] for p in pairs if 'change_percent' in p]
 row={'operation':operation,'connections':c,'pairs':pairs,'valid_paired_ratios':len(good)}
 for name in ['main','candidate']:
  vals=[p for p in pairs if p[name+'_status']=='success']
  row[name+'_failed_runs']=3-len(vals)
  if vals:
   for metric in ['qps','p99_ms']:row['median_'+name+'_'+metric]=statistics.median(p[name+'_'+metric] for p in vals)
 if good:row['median_paired_change_percent']=statistics.median(good);row['paired_change_range_percent']=[min(good),max(good)]
 summary.append(row)
 print(json.dumps({k:v for k,v in row.items() if k!='pairs'}))
(W/'list-range-repeat-summary.json').write_text(json.dumps({'main':m['main'],'candidate':m['candidate'],'method':m['method'],'conditions':summary,'limitations':'Three repetitions, not a confidence interval. Failed observations are retained and excluded from QPS ratios. Historical peers are not rerun and use different persistence/cache configurations.'},indent=2)+'\n')
