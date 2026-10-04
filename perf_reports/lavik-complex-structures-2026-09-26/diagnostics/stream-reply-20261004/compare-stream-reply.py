from pathlib import Path
import argparse,json
W=Path(__file__).parent;R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
p=argparse.ArgumentParser();p.add_argument('kind');p.add_argument('size',type=int);p.add_argument('field',type=int);p.add_argument('keys',type=int);a=p.parse_args();versions=json.loads((W/'stream-reply-versions.json').read_text())
def load(label):
 v=versions[label];tag=f'{label}{v["commit"][:8]}-ordered-{a.kind}-{a.size}-k{a.keys}-f{a.field}-20261004';d=R/'raw'/('lavik-'+tag)
 assert json.loads((d/'server-exit.json').read_text())['code']==0
 proof=json.loads(next(d.glob('provenance-*.json')).read_text());assert proof['source_commit']==v['commit'] and proof['sha256']==v['sha256']
 values={}
 for f in list(d.glob('*.result.json')) + list(d.glob('*.error.json')):
  r=json.loads(f.read_text());values[(r['operation'],r['connections'])]=r
 return tag,values
main_tag,b=load('main');candidate_tag,c=load('candidate');rows=[]
assert b.keys() == c.keys(), (b.keys() - c.keys(), c.keys() - b.keys())
for k in sorted(b):
 old,new=b[k],c[k]
 if 'error' in old or 'error' in new:
  row={'operation':k[0],'connections':k[1],'main':old,'candidate':new,'qps_change_percent':None,'note':'An error is not a throughput result; no QPS ratio is defined.'};rows.append(row)
  print(k,'main_error' if 'error' in old else old['qps'],'candidate_error' if 'error' in new else new['qps'],flush=True)
  continue
 row={'operation':k[0],'connections':k[1],'main_qps':old['qps'],'candidate_qps':new['qps'],'qps_change_percent':100*(new['qps']/old['qps']-1),'main_p99_ms':old['p99_ms'],'candidate_p99_ms':new['p99_ms']};rows.append(row)
 print(k,round(old['qps']),round(new['qps']),f"{row['qps_change_percent']:+.1f}%",flush=True)
output={'main_tag':main_tag,'candidate_tag':candidate_tag,'main':versions['main'],'candidate':versions['candidate'],'rows':rows,'limitations':'Single independent connection sweeps, no confidence interval. Perf samples are separate diagnostic runs. Paired repeats are required before asserting stable gains; include XRANGE point and XADD_MAXLEN controls. Candidate also includes the independently tested cold-recovery fix; foreground Stream changes are confined to replies.'}
(W/f'stream-reply-comparison-{a.kind}-{a.size}-{a.field}-k{a.keys}.json').write_text(json.dumps(output,indent=2)+'\n')
