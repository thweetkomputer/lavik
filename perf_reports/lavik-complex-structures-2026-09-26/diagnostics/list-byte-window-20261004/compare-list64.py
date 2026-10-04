from pathlib import Path
import argparse,json
W=Path(__file__).parent;R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26/raw')
p=argparse.ArgumentParser();p.add_argument('size',type=int);p.add_argument('field',type=int);p.add_argument('keys',type=int);a=p.parse_args()
v=json.loads((W/'list64-versions.json').read_text())
def load(label):
 x=v[label];tag=f'candidate{x["commit"][:8]}-ordered-list-{a.size}-k{a.keys}-f{a.field}-20261004';d=R/('lavik-'+tag)
 assert json.loads((d/'server-exit.json').read_text())['code']==0
 proof=json.loads(next(d.glob('provenance-*.json')).read_text());assert proof['source_commit']==x['commit'] and proof['sha256']==x['sha256']
 results={}
 for f in list(d.glob('*.result.json'))+list(d.glob('*.error.json')):
  r=json.loads(f.read_text());results[(r['operation'],r['connections'])]=r
 return tag,results
old_tag,old=load('previous');new_tag,new=load('candidate');assert old.keys()==new.keys()
rows=[]
for k in sorted(old):
 a0,b=old[k],new[k];r={'operation':k[0],'connections':k[1],'previous':a0,'candidate':b}
 if 'error' not in a0 and 'error' not in b:r.update(qps_change_percent=100*(b['qps']/a0['qps']-1),p99_change_percent=100*(b['p99_ms']/a0['p99_ms']-1))
 else:r.update(qps_change_percent=None,p99_change_percent=None)
 rows.append(r);print(k, r['qps_change_percent'],flush=True)
(W/f'list64-comparison-{a.size}-{a.field}-k{a.keys}.json').write_text(json.dumps({'previous_tag':old_tag,'candidate_tag':new_tag,'previous':v['previous'],'candidate':v['candidate'],'rows':rows,'limitations':'Single independent sweeps; repeated matched points required before claiming stable gains. Candidate includes the separate cold recovery repair; foreground List paths differ only in read-window mechanics.'},indent=2)+'\n')
