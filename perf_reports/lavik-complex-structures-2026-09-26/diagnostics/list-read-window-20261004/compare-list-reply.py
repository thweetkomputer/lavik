from pathlib import Path
import json, argparse
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26/raw')
p=argparse.ArgumentParser();p.add_argument('size',type=int);p.add_argument('field',type=int);p.add_argument('keys',type=int);options=p.parse_args()
def load(name):
 v=json.loads((W/name).read_text())['candidate'];tag=f'candidate{v["commit"][:8]}-ordered-list-{options.size}-k{options.keys}-f{options.field}-20261004';d=R/('lavik-'+tag)
 assert json.loads((d/'server-exit.json').read_text())['code']==0
 assert json.loads((d/'complete.json').read_text())['failures_total']==0
 proof=json.loads(next(d.glob('provenance-*.json')).read_text());assert proof['source_commit']==v['commit'] and proof['sha256']==v['sha256']
 values={}
 for f in d.glob('*.result.json'):
  x=json.loads(f.read_text());values[(x['operation'],x['connections'])]=x
 return v,tag,values
old,old_tag,previous=load('list-window-versions.json');new,new_tag,candidate=load('list-reply-versions.json');assert previous.keys()==candidate.keys();rows=[]
for k in sorted(previous):
 a,b=previous[k],candidate[k]
 r={'operation':k[0],'connections':k[1],'previous_qps':a['qps'],'candidate_qps':b['qps'],'qps_change_percent':100*(b['qps']/a['qps']-1),'previous_p99_ms':a['p99_ms'],'candidate_p99_ms':b['p99_ms']};rows.append(r)
 print(k,r['qps_change_percent'],r['previous_qps'],r['candidate_qps'])
(W/f'list-reply-comparison-{options.size}-{options.field}-k{options.keys}.json').write_text(json.dumps({'previous':old,'candidate':new,'previous_tag':old_tag,'candidate_tag':new_tag,'rows':rows,'limitations':'Single independent sweeps. Previous is PR #267, isolating the reply-reservation change; no confidence interval.'},indent=2)+'\n')
