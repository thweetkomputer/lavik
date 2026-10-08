from pathlib import Path
import csv,hashlib,json,statistics,subprocess
W=Path(__file__).parent
V=json.loads((W/'versions.json').read_text())
rows=json.loads((W/'pairs.json').read_text())
assert len(rows)==6
assert {(r['round'],r['version']) for r in rows}=={(i,v) for i in [4,5,6] for v in ['main','queueopt']}
for v in V.values():
 with open(v['binary'],'rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==v['sha256']
observations=[]
for row in rows+json.loads((W/'main-repeats.json').read_text()):
 d=Path(row['raw']);r=json.loads(next(d.glob('*.result.json')).read_text())
 assert r==row['result'] and r['command_audit']['passed']
 client=json.loads(next(d.glob('*.client.json')).read_text())
 assert client['errors']==0 and r['requests']==sum(c['count'] for c in client['commands'].values())
 assert client['connections']==320 and client['seconds']==30
 assert r['bounded']['baseline']==8192
 assert .48<=client['commands']['RPUSH']['count']/r['requests']<=.52
 for key, counts in client['key_counts'].items():
  assert counts['net']==counts['first']-counts['second']
  assert r['bounded']['all_final_counts'][key]==8192+counts['net']
  assert 4096<=r['bounded']['all_final_counts'][key]<=16384
 assert json.loads((d/'server-exit.json').read_text())['code']==0
 assert json.loads((d/'complete.json').read_text())['failures_total']==0
 proof=json.loads(next(d.glob('provenance-*.json')).read_text())
 assert proof['source_commit']==V[row['version']]['commit'] and proof['sha256']==V[row['version']]['sha256']
 seed=json.loads((d/'fixed-digest-seed.json').read_text());assert seed['seed_hex']==row['digest_seed'] and seed['verified_via_proc_mem']
 def info(label):return dict(s.split(':',1) for s in next(d.glob('*.info-'+label+'.txt')).read_text().splitlines() if ':' in s)
 b,a=info('before'),info('after')
 observations.append({'round':row['round'],'version':row['version'],'qps':r['qps'],'p99_ms':r['p99_ms'],'requests':r['requests'],'queue_peak_before':int(b['tx_commit_queue_peak']),'queue_peak_after':int(a['tx_commit_queue_peak']),'backlog_after':int(a['tx_backlog_bytes_total']),'raw':row['raw'],'exploratory':row['round']<4})
pairs=[]
for i in [4,5,6]:
 m,c=[next(r for r in rows if r['round']==i and r['version']==v) for v in ['main','queueopt']]
 assert m['digest_seed']==c['digest_seed'] and m['client_seed']==c['client_seed']
 pairs.append({'round':i,'qps_ratio':c['result']['qps']/m['result']['qps'],'p99_ratio':c['result']['p99_ms']/m['result']['p99_ms']})
summary={'pairs':pairs,'qps_ratio_median':statistics.median(p['qps_ratio'] for p in pairs),'p99_ratio_median':statistics.median(p['p99_ratio'] for p in pairs),'versions':{v:{metric:statistics.median(r['result'][metric] for r in rows if r['version']==v) for metric in ['qps','p99_ms']} for v in V},'audited_commands':sum(x['requests'] for x in observations),'clean_paired_commands':sum(r['result']['requests'] for r in rows),'exploratory':3,'paired_observations':6}
assert Path('/mnt/dev/lavik-pr289-20261008/refresh-pr289-CMakeCache.txt').read_bytes()==(W/'refresh-queueopt-CMakeCache.txt').read_bytes()
(W/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with (W/'observations.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=list(observations[0]));writer.writeheader();writer.writerows(observations)
(W/'audit.json').write_text(json.dumps({'passed':True,'checks':['binary SHA256','source commit','identical production CMakeCache','same per-pair process/client seeds','zero client failures','client/server command counts','exact per-key final cardinality','50/50 command mix','bounded sizes','clean server shutdown'],'summary':summary},indent=2)+'\n')
print(json.dumps(summary,indent=2))
