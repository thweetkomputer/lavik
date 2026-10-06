"""Validate every controlled observation against its raw run and seed evidence."""
from pathlib import Path
import hashlib,json
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
data=json.loads((W/'matched-seed-repeats.json').read_text());V=json.loads((W/'validated-versions.json').read_text());P=json.loads((W/'matched-seed-protocol.json').read_text())
assert len(data['rows'])==108
seen=set();checked=set();files=[]
def read(p):
 files.append({'path':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 return json.loads(p.read_text())
for row in data['rows']:
 key=(row['pattern'],row['type'],row['logical_bytes'],row['operation'],row['round'],row['version'])
 assert key not in seen;seen.add(key)
 assert row['seconds']==30 and row['connections']==320 and row['requests']>0 and 'error' not in row
 v=V[row['version']];raw=R/'raw'/('lavik-'+row['tag'])
 stem=f"{row['type']}-{row['logical_bytes']}-{row['field_bytes']}-{row['operation'].lower()}-c320"
 original=read(raw/(stem+'.result.json'))
 assert all(row[k]==x for k,x in original.items())
 if row['tag'] in checked:continue
 checked.add(row['tag'])
 for directory in [raw,R/'raw'/('lavik-seed-'+row['tag'])]:
  assert read(directory/'complete.json')['failures_total']==0
  assert read(directory/'server-exit.json')['code']==0
  proof=read(next(directory.glob('provenance-*.json')))
  assert proof['source_commit']==v['commit'] and proof['sha256']==v['sha256']
  seed=read(directory/'fixed-digest-seed.json')
  assert seed['verified_via_proc_mem'] and seed['seed_hex']==row['digest_seed']==P['seeds'][str(row['round'])]
  assert seed['sha256']==v['sha256'] and seed['source_commit']==v['commit']
 prefix=f"{row['type']}-{row['logical_bytes']}-{row['field_bytes']}"
 before=read(raw/(prefix+'.validated.json'))['sample_cardinalities'];after=read(raw/(prefix+'.after.json'))['sample_cardinalities']
 assert set(before)==set(after)=={f'complex_{i}' for i in range(1,row['keys']+1)}
 assert set(before.values())=={row['entries_per_key']}
 assert all(after[k]==n if row['type']=='hash' else n<=after[k]<=n+(64 if row['pattern']=='dispersed64' else 1) for k,n in before.items())
assert len(checked)==36 and len(set(P['seeds'].values()))==3
command=json.loads((W/'matched-seed-command-audit.json').read_text());assert command['points']==108 and command['all_command_counts_match']
summary=json.loads((W/'matched-seed-summary.json').read_text());assert len(summary['summary'])==18 and all(len(s['pairs'])==3 for s in summary['summary'])
(W/'matched-seed-final-audit.json').write_text(json.dumps({'observations':108,'conditions':18,'pairs_per_condition':3,'populations':36,'all_raw_results_match':True,'all_command_counts_match':True,'all_key_cardinalities_valid':True,'all_binary_and_seed_proofs_match':True,'all_exits_clean':True,'files':files},indent=2)+'\n')
print('PASS:108observations,18conditions,36freshpopulations;rawresults,commands,allkeys,source/binary/seedidentitiesandcleanexits.')
