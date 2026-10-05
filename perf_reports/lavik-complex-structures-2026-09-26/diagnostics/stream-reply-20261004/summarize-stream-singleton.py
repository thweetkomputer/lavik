"""Summarize complete paired scopes; never infer gains from partial rounds."""
from pathlib import Path
import argparse,json,math,statistics
p=argparse.ArgumentParser()
p.add_argument('--scope',choices=['large-reads','large-writes','small-controls','all'],required=True)
p.add_argument('--input',type=Path,default=Path(__file__).parent/'stream-singleton-followup-repeats.json')
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
v=json.loads(a.input.read_text());versions=v['versions']
assert versions['parent']['commit']=='adec3a3414adf7b18dc304d336253258e228cb02'
assert versions['singleton']['commit']=='85bc7ad0d7932b27dd6784c023fcbfdbd2dd8b08'
large={(104857600,128,8,'XRANGE_FULL',c) for c in [1,4,16]}|{(104857600,128,8,'XRANGE',2560)}
scopes={
    'large-reads':large,
    'large-writes':{(104857600,128,8,'XADD_MAXLEN',c) for c in [320,5120]},
    'small-controls':{(65536,1024,64,'XRANGE_FULL',80),(65536,1024,64,'XRANGE',5120)}|{(65536,1024,64,'XADD_MAXLEN',c) for c in [2560,5120]},
}
scopes['all']=set.union(*scopes.values())
expected=scopes[a.scope]
def case(row):
    return tuple(row[x] for x in ['logical_bytes','field_bytes','keys','operation','connections'])
rows=[r for r in v['rows'] if case(r) in expected]
assert len(rows)==len(expected)*6, f'incomplete scope: {len(rows)}/{len(expected)*6}'
groups={};proofs={}
for r in rows:
    assert 'error' not in r,r
    key=case(r)
    assert key in expected,key
    identity=(r['round'],r['version']);assert identity not in groups.setdefault(key,{}),'duplicate observation'
    groups[key][identity]=r
    for metric in ['qps','p99_ms']:assert math.isfinite(r[metric]) and r[metric]>0
    raw=R/'raw'/('lavik-'+r['tag'])
    # Pair metadata may select observations, but cannot replace their raw
    # measurements. Cross-check every point before trusting a shared run proof.
    raw_points=[json.loads(f.read_text()) for f in raw.glob('*.result.json')]
    matching=[point for point in raw_points if case(point)==key]
    assert len(matching)==1, ('missing or duplicate raw point',r['tag'],key)
    assert all(r.get(k)==value for k,value in matching[0].items()), ('raw point changed',r['tag'],key)
    assert r['seconds']==30 and r['requests']>0
    if r['tag'] in proofs:continue
    assert json.loads((raw/'server-exit.json').read_text())['code']==0
    assert json.loads((raw/'complete.json').read_text())['failures_total']==0
    proof=json.loads(next(raw.glob('provenance-*.json')).read_text())
    version=versions[r['version']]
    assert proof['source_commit']==version['commit'] and proof['sha256']==version['sha256']
    prefix=f'stream-{r["logical_bytes"]}-{r["field_bytes"]}'
    before=json.loads((raw/(prefix+'.validated.json')).read_text())['sample_cardinalities']
    after=json.loads((raw/(prefix+'.after.json')).read_text())['sample_cardinalities']
    entries=r['entries_per_key']
    names={f'complex_{i}' for i in range(1,r['keys']+1)}
    assert set(before)==set(after)==names
    assert all(count==entries for count in before.values())
    fill=json.loads((raw/(prefix+'.fill.json')).read_text())
    if r['operation']!='XADD_MAXLEN':
        assert before==after
        seed_tag=fill['reused_seed_from']
        seed=next(s for s in v['seeds'] if s['tag']==seed_tag)
        assert seed['round']==r['round'] and seed['cardinalities']==before
    else:
        # These runs only append with MAXLEN ~. Trimming cannot drop below
        # the requested length; permit the existing 100-entry overshoot bound.
        assert all(entries<=count<=entries+100 for count in after.values())
        assert 'reused_seed_from' not in fill
        seed_tag=None
    proofs[r['tag']]={'source_commit':proof['source_commit'],'sha256':proof['sha256'],'seed_tag':seed_tag,'server_exit':0,'failures_total':0,'keys_checked':len(before),'before_cardinality_range':[min(before.values()),max(before.values())],'after_cardinality_range':[min(after.values()),max(after.values())]}
assert set(groups)==expected
summary=[]
for key,observations in sorted(groups.items()):
    assert set(observations)=={(n,label) for n in [1,2,3] for label in versions}
    pairs=[]
    for n in [1,2,3]:
        parent=observations[(n,'parent')];candidate=observations[(n,'singleton')]
        if key[3]!='XADD_MAXLEN':assert proofs[parent['tag']]['seed_tag']==proofs[candidate['tag']]['seed_tag']
        pairs.append({'round':n,'parent':{k:parent[k] for k in ['tag','qps','p99_ms','requests']},'singleton':{k:candidate[k] for k in ['tag','qps','p99_ms','requests']},'qps_change_percent':(candidate['qps']/parent['qps']-1)*100,'p99_change_percent':(candidate['p99_ms']/parent['p99_ms']-1)*100})
    entry=dict(zip(['logical_bytes','field_bytes','keys','operation','connections'],key));entry['pairs']=pairs
    for metric in ['qps','p99']:
        changes=[pair[metric+'_change_percent'] for pair in pairs]
        entry[metric+'_paired_percent']={'median':statistics.median(changes),'min':min(changes),'max':max(changes),'positive_pairs':sum(x>0 for x in changes),'negative_pairs':sum(x<0 for x in changes)}
    for label in versions:
        entry[label+'_median_qps']=statistics.median(pair[label]['qps'] for pair in pairs)
        entry[label+'_median_p99_ms']=statistics.median(pair[label]['p99_ms'] for pair in pairs)
    summary.append(entry)
result={'scope':a.scope,'versions':versions,'observations':len(rows),'method':v['method'],'limitations':'Three paired changes, not confidence intervals. Median paired ratio is not the ratio of marginal medians. Full reads have few commands and rounded QPS. Negative p99 change is better. Historical peers not rerun; this is incremental parent-versus-singleton evidence, not overall parity.','proofs':proofs,'summary':summary}
a.output.write_text(json.dumps(result,indent=2)+'\n')
for r in summary:print(r['logical_bytes'],r['operation'],r['connections'],r['qps_paired_percent'],r['p99_paired_percent'])
