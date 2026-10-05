"""Validate raw ZSet observations; summarize only complete three-pair scopes."""
from pathlib import Path
import argparse,json,math,statistics
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--scope',choices=['large','small','all'],default='all')
p.add_argument('--validate-only',action='store_true')
p.add_argument('--input',type=Path,default=Path(__file__).parent/'zset-source-reuse-repeats.json')
p.add_argument('--output',type=Path,required=True)
p.add_argument('--report-root',type=Path,default=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26'),
               help='Report directory containing raw/lavik-<tag> observations')
a=p.parse_args()
R=a.report_root
data=json.loads(a.input.read_text());versions={k:data[k] for k in ['previous','candidate']}
assert versions['previous']['commit']=='067c75891f819831620e277eac0592c360f8b585'
assert versions['candidate']['commit']=='d012a3013da99344a419bb692f834b17fd6dcad4'
assert versions['candidate']['test_validation_commit']=='92906489799d5d65c8315cc87371a14f6b2e384e'
scopes={name:{(size,field,keys,op,c) for op in ['ZSCORE','ZINCRBY'] for c in [80,320,2560,5120]}
        for name,size,field,keys in [('large',104857600,1024,8),('small',65536,128,64)]}
scopes['all']=scopes['large']|scopes['small'];expected=scopes[a.scope]
fields=['logical_bytes','field_bytes','keys','operation','connections']
def case(row):return tuple(row[k] for k in fields)
assert all(case(r) in scopes['all'] for r in data['rows'])
rows=[r for r in data['rows'] if case(r) in expected]
assert rows,'no observations available'
proofs={};groups={}
for row in rows:
    assert 'error' not in row,row
    key=case(row);identity=(row['round'],row['version'])
    assert identity in {(n,v) for n in [1,2,3] for v in versions}
    assert identity not in groups.setdefault(key,{}),'duplicate observation'
    groups[key][identity]=row
    assert row['type']=='zset' and row['seconds']==30 and row['requests']>0
    assert row['entries_per_key']==row['logical_bytes']//row['field_bytes']
    for name in ['qps','p99_ms']:assert math.isfinite(row[name]) and row[name]>0
    raw=R/'raw'/('lavik-'+row['tag'])
    matches=[v for path in raw.glob('*.result.json') if case(v:=json.loads(path.read_text()))==key]
    assert len(matches)==1 and all(row.get(k)==value for k,value in matches[0].items()),('raw mismatch',row['tag'],key)
    if row['tag'] in proofs:continue
    assert json.loads((raw/'server-exit.json').read_text())['code']==0
    assert json.loads((raw/'complete.json').read_text())['failures_total']==0
    version=versions[row['version']]
    source=json.loads(next(raw.glob('provenance-*.json')).read_text())
    assert source['source_commit']==version['commit'] and source['sha256']==version['sha256']
    prefix=f'zset-{row["logical_bytes"]}-{row["field_bytes"]}'
    before=json.loads((raw/(prefix+'.validated.json')).read_text())['sample_cardinalities']
    after=json.loads((raw/(prefix+'.after.json')).read_text())['sample_cardinalities']
    names={f'complex_{i}' for i in range(1,row['keys']+1)}
    assert set(before)==names and before==after
    assert all(n==row['entries_per_key'] for n in before.values())
    fill=json.loads((raw/(prefix+'.fill.json')).read_text())
    assert 'reused_seed_from' not in fill
    proofs[row['tag']]={'source_commit':source['source_commit'],'sha256':source['sha256'],
                       'keys_checked':len(before),'cardinality':row['entries_per_key'],'server_exit':0,'failures_total':0}
result={'scope':a.scope,'versions':versions,'observations':len(rows),'expected_observations':len(expected)*6,
        'method':data['method'],'proofs':proofs,'summary':[],
        'limitations':'Three independent fresh-population AB/BA/AB pairs, not confidence intervals. Median paired ratio differs from ratio of marginal medians. Negative p99 change is better. Candidate production source remains d012; 929 changes only the test driver. Historical peers not rerun; incremental performance is not overall parity.'}
if a.validate_only:
    result['status']='raw observations verified; no performance conclusion from incomplete scopes'
else:
    assert len(rows)==len(expected)*6 and groups.keys()==expected,('incomplete scope',len(rows),len(expected)*6)
    for key,observations in sorted(groups.items()):
        assert observations.keys()=={(n,v) for n in [1,2,3] for v in versions}
        pairs=[]
        for n in [1,2,3]:
            previous,candidate=observations[(n,'previous')],observations[(n,'candidate')]
            pairs.append({'round':n,'previous':{k:previous[k] for k in ['tag','qps','p99_ms','requests']},
                          'candidate':{k:candidate[k] for k in ['tag','qps','p99_ms','requests']},
                          'qps_change_percent':(candidate['qps']/previous['qps']-1)*100,
                          'p99_change_percent':(candidate['p99_ms']/previous['p99_ms']-1)*100})
        entry=dict(zip(fields,key));entry['pairs']=pairs
        for metric in ['qps','p99']:
            changes=[pair[metric+'_change_percent'] for pair in pairs]
            entry[metric+'_paired_percent']={'median':statistics.median(changes),'min':min(changes),'max':max(changes),
                                            'positive_pairs':sum(x>0 for x in changes),'negative_pairs':sum(x<0 for x in changes)}
        for version in versions:
            entry[version+'_median_qps']=statistics.median(pair[version]['qps'] for pair in pairs)
            entry[version+'_median_p99_ms']=statistics.median(pair[version]['p99_ms'] for pair in pairs)
        result['summary'].append(entry)
    result['status']='complete three-pair scope verified'
a.output.write_text(json.dumps(result,indent=2)+'\n')
print(result['status'],len(rows),'/',len(expected)*6)
for row in result['summary']:print(case(row),row['qps_paired_percent'],row['p99_paired_percent'])
