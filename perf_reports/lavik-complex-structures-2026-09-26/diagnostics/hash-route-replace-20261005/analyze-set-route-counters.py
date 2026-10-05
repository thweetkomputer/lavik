"""Audit retained INFO windows for a complete Hash/Set paired comparison."""
from pathlib import Path
import argparse,hashlib,json
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--report-root',type=Path,default=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26'))
p.add_argument('--scope',choices=['set-large','hash-large','hash-small'],default='set-large')
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();r=a.report_root
prefix={'set-large':'hash-route-set-large','hash-large':'hash-route-large','hash-small':'hash-route-hash-small'}[a.scope]
kind=a.scope.split('-')[0]
operations=['SISMEMBER','SADD_SREM'] if kind=='set' else ['HGET','HSET']
observation=r/'diagnostics/hash-route-replace-20261005'/(prefix+'-observations.json')
data=json.loads(observation.read_text());assert len(data['rows'])==36
counters=['rdb_changes_since_last_save','tx_commit_batches','tx_commit_batch_transactions',
          'tx_commit_backpressure_waits','tx_fastpath_runs','tx_queued_runs','tx_schedule_retries',
          'oom_rejected_commands','tx_cleaner_failures']

def snapshot(path):
    result={}
    for line in path.read_text().splitlines():
        if not line or line.startswith('#'):continue
        key,value=line.split(':',1);assert key not in result
        result[key]=value
    return result

def calls(info,command):
    # INFO omits a command whose cumulative call count is zero.
    value=info.get('cmdstat_'+command)
    if value is None:return 0
    return int(dict(part.split('=',1) for part in value.split(','))['calls'])

rows=[];seen=set()
for row in data['rows']:
    identity=(row['round'],row['version'],row['operation'],row['connections'])
    assert identity not in seen;seen.add(identity)
    raw=r/'raw'/('lavik-'+row['tag'])
    source=json.loads(next(raw.glob('provenance-*.json')).read_text())
    assert source['sha256']==data['versions'][row['version']]['sha256']
    assert source['source_commit']==data['versions'][row['version']]['commit']
    assert row['type']==kind
    stem=f'{kind}-{row["logical_bytes"]}-{row["field_bytes"]}-{row["operation"].lower()}-c{row["connections"]}'
    result=json.loads((raw/(stem+'.result.json')).read_text())
    assert all(row[k]==v for k,v in result.items())
    paths=[raw/(stem+'.info-'+phase+'.txt') for phase in ['before','after']]
    before,after=map(snapshot,paths)
    for key in ['process_id','run_id','worker_threads','rdb_last_save_time']:
        assert before[key]==after[key]
    assert before['worker_threads']=='12'
    assert before['rdb_bgsave_in_progress']==after['rdb_bgsave_in_progress']=='0'
    assert before['tomb_raider_enabled']==after['tomb_raider_enabled']=='0'
    assert before['defrag_paused']==after['defrag_paused']=='1'
    command_names=['sadd','srem'] if row['operation']=='SADD_SREM' else [row['operation'].lower()]
    command_delta={c:calls(after,c)-calls(before,c) for c in command_names}
    count=sum(command_delta.values());assert count==row['requests'] and count>0
    delta={k:int(after[k])-int(before[k]) for k in counters}
    assert all(v>=0 for v in delta.values())
    assert delta['oom_rejected_commands']==delta['tx_cleaner_failures']==0
    batch=delta['tx_commit_batches'];transactions=delta['tx_commit_batch_transactions']
    scheduled=delta['tx_fastpath_runs']+delta['tx_queued_runs'];assert scheduled>0
    rows.append({**{k:row[k] for k in ['round','version','tag','operation','connections','qps','p99_ms','requests','elapsed_seconds']},
                 'source_commit':source['source_commit'],'binary_sha256':source['sha256'],
                 'info_files':[{'path':str(path.relative_to(r)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths],
                 'run_id':before['run_id'],'command_calls_delta':command_delta,'counter_delta':delta,
                 'changes_per_measured_call':delta['rdb_changes_since_last_save']/count,
                 'commit_transactions_per_batch':transactions/batch if batch else None,
                 'queued_fraction_of_tx_runs':delta['tx_queued_runs']/scheduled,
                 # Queue peak is a lifetime gauge: preserve snapshots, do not difference it.
                 'queue_peak_before':int(before['tx_commit_queue_peak']),
                 'queue_peak_after':int(after['tx_commit_queue_peak'])})
assert seen=={(n,v,op,c) for n in [1,2,3] for v in ['parent','candidate'] for op in operations for c in [80,320,5120]}
write=[v for v in rows if v['operation'] in ['SADD_SREM','HSET']]
summary=[]
for c in [80,320,5120]:
    for version in ['parent','candidate']:
        values=sorted((v for v in write if v['connections']==c and v['version']==version),key=lambda row:row['round'])
        summary.append({'connections':c,'version':version,
            'changes_per_call_range':[min(v['changes_per_measured_call'] for v in values),max(v['changes_per_measured_call'] for v in values)],
            'batches_mean_transactions_each_round':[v['commit_transactions_per_batch'] for v in values],
            'backpressure_events_each_round':[v['counter_delta']['tx_commit_backpressure_waits'] for v in values]})
out={'observations_sha256':hashlib.sha256(observation.read_bytes()).hexdigest(),'rows':rows,'summary':summary,
     'limitations':'Retained before/after INFO windows enclose client startup and completion. Per-command call deltas exactly equal measured requests. Server-wide counters may include background or carried-over commits and are not causal per-command traces. Dataset changes are committed-key change accounting, not direct reply inspection or proof of synchronous durability. Backpressure increments when enqueue reaches its worker queue high watermark; it is not wait duration. Batch transactions/batches is an interval average, not a distribution. No new CPU/IO sample, no causal attribution, no change to QPS or peer baselines.'}
a.output.write_text(json.dumps(out,indent=2)+'\n')
print('verified',len(rows),'INFO windows; write change/call range',min(v['changes_per_measured_call'] for v in write),max(v['changes_per_measured_call'] for v in write))
for s in summary:print(s)
