"""Verify raw observations and summarize complete three-pair Hash/Set scopes."""
from pathlib import Path
import argparse,json,math,statistics
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--scope',choices=['hash-large','hash-small','set-large','set-small','all'],default='all')
p.add_argument('--validate-only',action='store_true')
p.add_argument('--input',type=Path,default=Path(__file__).parent/'hash-route-replace-repeats.json')
p.add_argument('--versions',type=Path,default=Path(__file__).parent/'hash-route-replace-versions-corrected.json')
p.add_argument('--report-root',type=Path,default=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26'))
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();data=json.loads(a.input.read_text());versions=json.loads(a.versions.read_text());R=a.report_root
for label,head in [('parent','19496654cc43b21df11fb59be60e174dc4c89dbc'),('candidate','27c65ff9c2ceaaacea4c93f42ffed01dce529b8f')]:
 assert versions[label]['commit']==head
 assert versions[label]['bycorf_commit']=='62509c93d40c2480f5046b71454db6cf95801b04'
 for key in ['commit','sha256','driver_sha256','binary','driver']:
  assert data['versions'][label][key]==versions[label][key]
 assert data['versions'][label]['bycorf_commit'] in (versions[label]['bycorf_commit'],versions[label]['bycorf_commit_recorded'])
scopes={}
for kind,ops in [('hash',['HGET','HSET']),('set',['SISMEMBER','SADD_SREM'])]:
 for size_label,size,field,keys in [('large',104857600,1024,500),('small',1048576,128,50000)]:
  scopes[kind+'-'+size_label]={(kind,size,field,keys,op,c) for op in ops for c in [80,320,5120]}
scopes['all']=set.union(*scopes.values());expected=scopes[a.scope]
fields=['type','logical_bytes','field_bytes','keys','operation','connections']
def case(r):return tuple(r[k] for k in fields)
assert all(case(r) in scopes['all'] for r in data['rows'])
rows=[r for r in data['rows'] if case(r) in expected];assert rows
proofs={};groups={}
for row in rows:
 assert 'error' not in row
 key=case(row);identity=(row['round'],row['version'])
 assert identity in {(n,v) for n in [1,2,3] for v in versions}
 assert identity not in groups.setdefault(key,{})
 groups[key][identity]=row
 assert row['seconds']==30 and row['requests']>0 and row['entries_per_key']==row['logical_bytes']//row['field_bytes']
 assert all(math.isfinite(row[k]) and row[k]>0 for k in ['qps','p99_ms'])
 raw=R/'raw'/('lavik-'+row['tag'])
 matches=[v for f in raw.glob('*.result.json') if case(v:=json.loads(f.read_text()))==key]
 assert len(matches)==1 and all(row.get(k)==v for k,v in matches[0].items())
 if row['tag'] in proofs:continue
 v=versions[row['version']];prefix=f'{row["type"]}-{row["logical_bytes"]}-{row["field_bytes"]}'
 seed_tag=json.loads((raw/(prefix+'.fill.json')).read_text())['reused_seed_from']
 assert seed_tag=='seed-'+row['tag']
 seed=R/'raw'/('lavik-'+seed_tag)
 for current in [raw,seed]:
  assert not list(current.glob('*.error.json'))
  assert json.loads((current/'server-exit.json').read_text())['code']==0
  assert json.loads((current/'complete.json').read_text())['failures_total']==0
  provs=list(current.glob('provenance-*.json'));assert len(provs)==1
  prov=json.loads(provs[0].read_text())
  assert prov['source_commit']==v['commit'] and prov['sha256']==v['sha256']
  if current==raw:assert prov['seconds']==30 and prov['levels']==[80,320,5120] and prov['mode']=='point'
  else:
   assert prov['reused_seed_from'] is None
   fixture=data['fixtures'][prefix]
   assert prov['seed_dump_sha256']==fixture['sha256'] and prov['seed_dump_path']==fixture['path']
  names={f'complex_{i}' for i in range(1,row['keys']+1)}
  before=json.loads((current/(prefix+'.validated.json')).read_text())['sample_cardinalities']
  after=json.loads((current/(prefix+'.after.json')).read_text())['sample_cardinalities']
  assert set(before)==names and set(after)==names
  assert all(n==row['entries_per_key'] for n in before.values())
  if row['type']=='hash' or current==seed:assert before==after
  else:assert all(after[k] in (before[k],before[k]+1) for k in before)
 fill=json.loads((seed/(prefix+'.fill.json')).read_text())
 assert fill['method']=='restore' and fill['commands']==row['keys']
 proofs[row['tag']]={'source_commit':v['commit'],'binary_sha256':v['sha256'],'keys_checked':row['keys'],'initial_cardinality':row['entries_per_key'],'fixture_sha256':fixture['sha256'],'seed_tag':seed_tag,'server_exit':0,'failures_total':0}
result={'scope':a.scope,'versions':versions,'observations':len(rows),'expected_observations':len(expected)*6,'method':data['method'],'proofs':proofs,'summary':[],
'limitations':'Three fresh-RESTORE AB/BA/AB population pairs, independent persisted hash seeds and physical layout. Median paired ratios are not ratios of marginal medians or confidence intervals. Negative p99 change is better. Set QPS includes no-ops. Dependency metadata corrected from CMake source evidence after validation; binary/driver identities unchanged. No new historical peer measurement.'}
if a.validate_only:result['status']='raw observations verified; no conclusion from incomplete scopes'
else:
 assert len(rows)==len(expected)*6 and groups.keys()==expected,('incomplete scope',len(rows),len(expected)*6)
 for key,observations in sorted(groups.items()):
  assert observations.keys()=={(n,v) for n in [1,2,3] for v in versions}
  pairs=[]
  for n in [1,2,3]:
   old,new=observations[n,'parent'],observations[n,'candidate']
   pairs.append({'round':n,'parent':{k:old[k] for k in ['tag','qps','p99_ms','requests']},'candidate':{k:new[k] for k in ['tag','qps','p99_ms','requests']},'qps_change_percent':(new['qps']/old['qps']-1)*100,'p99_change_percent':(new['p99_ms']/old['p99_ms']-1)*100})
  entry=dict(zip(fields,key));entry['pairs']=pairs
  for metric in ['qps','p99']:
   changes=[p[metric+'_change_percent'] for p in pairs]
   entry[metric+'_paired_percent']={'median':statistics.median(changes),'min':min(changes),'max':max(changes),'positive_pairs':sum(v>0 for v in changes),'negative_pairs':sum(v<0 for v in changes)}
  for version in versions:
   for metric in ['qps','p99_ms']:entry[version+'_median_'+metric]=statistics.median(p[version][metric] for p in pairs)
  result['summary'].append(entry)
 result['status']='complete three-pair scope verified'
a.output.write_text(json.dumps(result,indent=2)+'\n')
print(result['status'],len(rows),'/',len(expected)*6)
for r in result['summary']:print(case(r),r['qps_paired_percent'],r['p99_paired_percent'])
