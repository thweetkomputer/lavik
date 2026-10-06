"""Validate raw ZSet score-view observations; summarize only complete three-pair scopes."""
from pathlib import Path
import argparse,json,math,statistics,hashlib
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--scope',choices=['large','large-distinct','large-reads','large-writes','small','small-reads','small-writes','all'],default='all')
p.add_argument('--validate-only',action='store_true')
p.add_argument('--input',type=Path,default=Path(__file__).parent/'pr283-repeats.json')
p.add_argument('--output',type=Path,required=True)
p.add_argument('--report-root',type=Path,default=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26'),
               help='Report directory containing raw/lavik-<tag> observations')
a=p.parse_args()
R=a.report_root
data=json.loads(a.input.read_text());versions=data['versions']
assert set(versions)=={'parent','candidate'}
assert versions['parent']['commit']=='5a3903d9b3c0632e3b34e827b779d9daa58455c2'
assert versions['candidate']['commit']=='ace4198b0e1080cbb5116d40817b4dcc38f7ff8c'
scopes={}
for name,size,field,keys in [('large',104857600,1024,8),('small',65536,128,64)]:
    scopes[name]={(size,field,keys,op,c,'distinct') for op in ['ZSCORE','ZINCRBY'] for c in [80,320,2560,5120]}
    scopes[name]|={(size,field,keys,'ZADD',c,layout) for c in [80,5120] for layout in ['distinct','ties']}
scopes['all']=scopes['large']|scopes['small']
scopes['large-distinct']={key for key in scopes['large'] if key[-1]=='distinct'}
# Publish a completed read or write control only after all three pairs and
# every connection level pass the same raw-evidence checks as the full scope.
scopes['large-reads']={key for key in scopes['large'] if key[3]=='ZSCORE'}
scopes['large-writes']={key for key in scopes['large'] if key[3]=='ZINCRBY'}
scopes['small-reads']={key for key in scopes['small'] if key[3]=='ZSCORE'}
scopes['small-writes']={key for key in scopes['small'] if key[3]=='ZINCRBY'}
expected=scopes[a.scope]
fields=['logical_bytes','field_bytes','keys','operation','connections','layout']
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
    for name in ['qps','p99_ms','elapsed_seconds']:assert math.isfinite(row[name]) and row[name]>0
    raw=R/'raw'/('lavik-'+row['tag'])
    matches=[v for path in raw.glob('*.result.json') if tuple((v:=json.loads(path.read_text()))[k] for k in fields[:-1])==key[:-1]]
    assert len(matches)==1 and all(row.get(k)==value for k,value in matches[0].items()),('raw mismatch',row['tag'],key)
    if row['tag'] in proofs:continue
    assert json.loads((raw/'server-exit.json').read_text())['code']==0
    assert json.loads((raw/'complete.json').read_text())['failures_total']==0
    assert not list(raw.glob('*.error.json'))
    version=versions[row['version']]
    source=json.loads(next(raw.glob('provenance-*.json')).read_text())
    workload=json.loads((raw/'workload.json').read_text())
    assert workload['operation']==row['operation'] and workload['layout']==row['layout']
    assert source['seconds']==30 and source['keys']==row['keys'] and source['mode']=='point'
    assert source['levels']==([80,5120] if row['operation']=='ZADD' else [80,320,2560,5120])
    if row['layout']=='ties':
        assert json.loads((raw/f'zset-{row["logical_bytes"]}-{row["field_bytes"]}.validated.json').read_text())['all_members_initial_score']==0

    assert source['source_commit']==version['commit'] and source['sha256']==version['sha256']
    prefix=f'zset-{row["logical_bytes"]}-{row["field_bytes"]}'
    before=json.loads((raw/(prefix+'.validated.json')).read_text())['sample_cardinalities']
    after=json.loads((raw/(prefix+'.after.json')).read_text())['sample_cardinalities']
    names={f'complex_{i}' for i in range(1,row['keys']+1)}
    assert set(before)==names and before==after
    assert all(n==row['entries_per_key'] for n in before.values())
    fill=json.loads((raw/(prefix+'.fill.json')).read_text())
    seed_tag=fill.get('reused_seed_from')
    if row['operation']=='ZSCORE':
        assert seed_tag, 'read must use the parent-seeded population'
        seed=R/'raw'/('lavik-'+seed_tag)
        original=json.loads(next(seed.glob('provenance-*.json')).read_text())
        assert original['source_commit']==versions['parent']['commit'] and original['sha256']==versions['parent']['sha256']
        assert original['reused_seed_from'] is None
        assert json.loads((seed/'server-exit.json').read_text())['code']==0
        assert json.loads((seed/'complete.json').read_text())['failures_total']==0
        assert not list(seed.glob('*.result.json')) and not list(seed.glob('*.error.json'))
        for phase in ['validated','after']:
            assert json.loads((seed/(prefix+'.'+phase+'.json')).read_text())['sample_cardinalities']==before
        claimed=[item for item in data['seeds'] if item['tag']==seed_tag and item['round']==row['round']]
        assert len(claimed)==1 and claimed[0]['cardinalities']==before
    else:assert seed_tag is None, 'write controls must be independently seeded'
    proofs[row['tag']]={'source_commit':source['source_commit'],'sha256':source['sha256'],
                       'seed_tag':seed_tag,'keys_checked':len(before),'cardinality':row['entries_per_key'],'server_exit':0,'failures_total':0}
result={'input_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),'validator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':a.scope,'versions':versions,'observations':len(rows),'expected_observations':len(expected)*6,
        'method':data['method'],'proofs':proofs,'summary':[],
        'limitations':'ZADD CH toggles scores0/1; concurrent same-score requests may be no-ops, so throughput is not an actual modification count. Three AB/BA/AB pairs; reads restart on each rounds shared parent-seeded logical population (not immutable disk snapshot); writes use independent fresh seeds. No confidence intervals. Paired ratio medians differ from ratios of marginal medians. Negative p99 change is better. Historical peers not rerun; incremental gains do not prove overall parity.'}
if a.validate_only:
    result['status']='raw observations verified; no performance conclusion from incomplete scopes'
else:
    assert len(rows)==len(expected)*6 and groups.keys()==expected,('incomplete scope',len(rows),len(expected)*6)
    for key,observations in sorted(groups.items()):
        assert observations.keys()=={(n,v) for n in [1,2,3] for v in versions}
        pairs=[]
        for n in [1,2,3]:
            parent,candidate=observations[(n,'parent')],observations[(n,'candidate')]
            if parent['operation']=='ZSCORE':
                assert proofs[parent['tag']]['seed_tag']==proofs[candidate['tag']]['seed_tag']
            pairs.append({'round':n,'parent':{k:parent[k] for k in ['tag','qps','p99_ms','requests','elapsed_seconds']},
                          'candidate':{k:candidate[k] for k in ['tag','qps','p99_ms','requests','elapsed_seconds']},
                          'qps_change_percent':(candidate['qps']/parent['qps']-1)*100,
                          'p99_change_percent':(candidate['p99_ms']/parent['p99_ms']-1)*100})
            for label in ('parent','candidate'):
                point=pairs[-1][label]
                point['client_call_rate']=point['requests']/point['elapsed_seconds']
            pairs[-1]['client_call_rate_change_percent']=(pairs[-1]['candidate']['client_call_rate']/pairs[-1]['parent']['client_call_rate']-1)*100
        entry=dict(zip(fields,key));entry['pairs']=pairs
        for metric in ['qps','p99','client_call_rate']:
            changes=[pair[metric+'_change_percent'] for pair in pairs]
            entry[metric+'_paired_percent']={'median':statistics.median(changes),'min':min(changes),'max':max(changes),
                                            'positive_pairs':sum(x>0 for x in changes),'negative_pairs':sum(x<0 for x in changes)}
        for version in versions:
            entry[version+'_median_qps']=statistics.median(pair[version]['qps'] for pair in pairs)
            entry[version+'_median_p99_ms']=statistics.median(pair[version]['p99_ms'] for pair in pairs)
            entry[version+'_median_client_call_rate']=statistics.median(pair[version]['client_call_rate'] for pair in pairs)
        result['summary'].append(entry)
    result['status']='complete three-pair scope verified'
a.output.write_text(json.dumps(result,indent=2)+'\n')
print(result['status'],len(rows),'/',len(expected)*6)
for row in result['summary']:print(case(row),row['qps_paired_percent'],row['p99_paired_percent'])
