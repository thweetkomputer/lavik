"""Validate the existing three-version grouped lookup comparison; summarize complete scopes only."""
from pathlib import Path
import argparse,json,math,statistics
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--scope',choices=['large','small','all'],default='all')
p.add_argument('--validate-only',action='store_true')
p.add_argument('--input',type=Path,default=Path(__file__).parent/'grouped-lookup-repeats.json')
p.add_argument('--output',type=Path,required=True)
p.add_argument('--report-root',type=Path,default=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26'),
               help='Report directory containing raw/lavik-<tag> observations')
a=p.parse_args()
R=a.report_root
data=json.loads(a.input.read_text());versions=data['versions']
expected_heads={
    'parent':'067c75891f819831620e277eac0592c360f8b585',
    'inline':'2e6e4f3559d284e6fe5d0dddc7eb1de5929761ae',
    'decoded':'8babe581213f2cd781f13665a45fdbf1012cf449',
}
assert set(versions)==set(expected_heads)
for label,head in expected_heads.items():
    assert versions[label]['commit']==head
    assert versions[label]['bycorf_commit']=='62509c93d40c2480f5046b71454db6cf95801b04'
    assert all(t['failures']==0 and t['tests']>0 for t in versions[label]['tests'].values())
    options=versions[label]['comparison_build_options']
    assert options==versions['parent']['comparison_build_options']
    assert options['BUILD_TESTING']==options['LAVIK_ENABLE_TEST_FAULTS']=='OFF'
    assert options['LAVIK_MARCH']=='native'
scopes={name:{(size,field,keys,op,c) for op in ['ZSCORE','ZINCRBY'] for c in [320,5120]}
        for name,size,field,keys in [('large',104857600,1024,8),('small',65536,128,64)]}
scopes['all']=scopes['large']|scopes['small']
expected=scopes[a.scope]
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
    assert not list(raw.glob('*.error.json'))
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
    seed_tag=fill.get('reused_seed_from')
    assert source.get('reused_seed_from')==seed_tag
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
result={'scope':a.scope,'versions':versions,'observations':len(rows),'expected_observations':len(expected)*9,
        'method':data['method'],'proofs':proofs,'summary':[],
        'limitations':'Three balanced rotations parent/inline/decoded, inline/decoded/parent, decoded/parent/inline. Each candidate shares the same round parent, not independent parent samples. Reads restart on each rounds shared parent-seeded logical population (not immutable disk snapshot); writes use independent fresh seeds. No confidence intervals. Paired ratio medians differ from ratios of marginal medians. Negative p99 change is better. Historical peers not rerun; incremental gains do not prove overall parity.'}
# Check the executed version order, including the currently available prefix.
orders=[('parent','inline','decoded'),('inline','decoded','parent'),('decoded','parent','inline')]
for size in [104857600,65536]:
    for round_ in [1,2,3]:
        for operation in ['ZSCORE','ZINCRBY']:
            order=list(dict.fromkeys(r['version'] for r in rows if r['logical_bytes']==size and r['round']==round_ and r['operation']==operation))
            assert order==list(orders[round_-1][:len(order)]),(size,round_,operation,order)
if a.validate_only:
    result['status']='Available raw observations verified; no performance conclusion from incomplete scopes'
else:
    assert len(rows)==len(expected)*9 and groups.keys()==expected,('incomplete scope',len(rows),len(expected)*9)
    for key,observations in sorted(groups.items()):
        assert observations.keys()=={(n,v) for n in [1,2,3] for v in versions}
        for label in ['inline','decoded']:
            pairs=[]
            for n in [1,2,3]:
                parent,candidate=observations[(n,'parent')],observations[(n,label)]
                if parent['operation']=='ZSCORE':
                    assert len({proofs[observations[(n,v)]['tag']]['seed_tag'] for v in versions})==1
                pairs.append({'round':n,'parent':{k:parent[k] for k in ['tag','qps','p99_ms','requests']},
                              'candidate':{k:candidate[k] for k in ['tag','qps','p99_ms','requests']},
                              'qps_change_percent':(candidate['qps']/parent['qps']-1)*100,
                              'p99_change_percent':(candidate['p99_ms']/parent['p99_ms']-1)*100})
            entry=dict(zip(fields,key));entry.update(candidate_label=label,pairs=pairs)
            for metric in ['qps','p99']:
                changes=[pair[metric+'_change_percent'] for pair in pairs]
                entry[metric+'_paired_percent']={'median':statistics.median(changes),'min':min(changes),'max':max(changes),
                                                'positive_pairs':sum(x>0 for x in changes),'negative_pairs':sum(x<0 for x in changes)}
            for version in ['parent','candidate']:
                entry[version+'_median_qps']=statistics.median(pair[version]['qps'] for pair in pairs)
                entry[version+'_median_p99_ms']=statistics.median(pair[version]['p99_ms'] for pair in pairs)
            result['summary'].append(entry)
    result['status']='Complete three-version scope verified'
a.output.write_text(json.dumps(result,indent=2)+'\n')
print(result['status'],len(rows),'/',len(expected)*9)
for row in result['summary']:print(row['candidate_label'],case(row),row['qps_paired_percent'],row['p99_paired_percent'])
