from pathlib import Path
from collections import defaultdict
import json,statistics
W=Path(__file__).parent;R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
p=W/'matched-seed-repeats.json'
if not p.exists():raise SystemExit('No clean points yet')
data=json.loads(p.read_text());groups=defaultdict(dict);audits=[]
def info(path):return dict(l.split(':',1) for l in path.read_text().splitlines() if ':' in l and not l.startswith('#'))
def cmd(d,c):return {k:float(v) for k,v in (x.split('=',1) for x in d.get('cmdstat_'+c,'calls=0,rejected_calls=0,failed_calls=0').split(','))}
for row in data['rows']:
 key=(row['pattern'],row['type'],row['logical_bytes'],row['field_bytes'],row['operation'],row['connections'])
 groups[key][(row['round'],row['version'])]=row
 raw=R/'raw'/('lavik-'+row['tag']);stem=f"{row['type']}-{row['logical_bytes']}-{row['field_bytes']}-{row['operation'].lower()}-c{row['connections']}"
 proof=json.loads((raw/'fixed-digest-seed.json').read_text());assert proof['verified_via_proc_mem'] and proof['seed_hex']==row['digest_seed']
 b=info(raw/(stem+'.info-before.txt'));a=info(raw/(stem+'.info-after.txt'))
 commands=['sadd','srem'] if row['operation']=='SADD_SREM' else [row['operation'].removesuffix('_AFTER_WRITE').lower()]
 counts={}
 for c in commands:
  cb,ca=cmd(b,c),cmd(a,c);counts[c]=ca['calls']-cb['calls'];assert ca['rejected_calls']==cb['rejected_calls'] and ca['failed_calls']==cb['failed_calls']
 assert sum(counts.values())==row['requests']>0,(stem,counts,row['requests'])
 assert all(a.get(k)==b.get(k) for k in ['run_id','process_id','worker_threads'])
 audits.append({'tag':row['tag'],'operation':row['operation'],'requests':row['requests'],'command_deltas':counts,'used_memory_before':int(b['used_memory']),'used_memory_after':int(a['used_memory']),'used_memory_rss_after':int(a['used_memory_rss']),'transaction_deltas':{k:int(a[k])-int(b[k]) for k in ['tx_commit_batches','tx_commit_batch_transactions','tx_fastpath_runs','tx_queued_runs','tx_schedule_retries'] if k in a and k in b}})
summary=[]
for key,points in groups.items():
 pairs=[]
 for n in (1,2,3):
  if (n,'parent') not in points or (n,'candidate') not in points:continue
  b,a=points[n,'parent'],points[n,'candidate']
  assert b['digest_seed']==a['digest_seed']
  pairs.append({'round':n,'main_qps':b['qps'],'candidate_qps':a['qps'],'qps_change_percent':100*(a['qps']/b['qps']-1),'main_p99_ms':b['p99_ms'],'candidate_p99_ms':a['p99_ms'],'p99_change_percent':100*(a['p99_ms']/b['p99_ms']-1)})
 if pairs:
  summary.append(dict(zip(['pattern','type','logical_bytes','field_bytes','operation','connections'],key),pairs=pairs,paired_median_qps_change_percent=statistics.median(x['qps_change_percent'] for x in pairs),paired_median_p99_change_percent=statistics.median(x['p99_change_percent'] for x in pairs)))
  print(key,'pairs',len(pairs),'QPS%',round(summary[-1]['paired_median_qps_change_percent'],2),'p99%',round(summary[-1]['paired_median_p99_change_percent'],2),'each',[round(x['qps_change_percent'],2) for x in pairs])
(W/'matched-seed-summary.json').write_text(json.dumps({'completed_points':len(data['rows']),'expected_points':108,'summary':summary},indent=2)+'\n')
(W/'matched-seed-command-audit.json').write_text(json.dumps({'points':len(audits),'all_command_counts_match':True,'audits':audits},indent=2)+'\n')
