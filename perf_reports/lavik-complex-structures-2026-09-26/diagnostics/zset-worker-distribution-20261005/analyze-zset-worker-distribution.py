"""Explain fixed benchmark-key ownership and recorded per-thread task-clock."""
from pathlib import Path
import argparse,binascii,collections,hashlib,json,subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--report-root',type=Path,default=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26'))
p.add_argument('--source-repo',type=Path,default=Path('/mnt/dev/lavik-zset-score-views-20261005'))
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();r=a.report_root;d=r/'diagnostics/zset-member-probe-20261004'
heads={'previous':'067c75891f819831620e277eac0592c360f8b585','candidate':'d012a3013da99344a419bb692f834b17fd6dcad4'}
sources={}
for label,head in heads.items():
 files={name:subprocess.check_output(['git','show',head+':'+name],cwd=a.source_repo,text=True) for name in ['src/storage/format.cpp','src/storage/engine/impl.h']}
 assert 'return StorageShardForKey(key) % worker_count_;' in files['src/storage/engine/impl.h']
 assert 'RedisCrc16(HashTag(key)) & 0x3fffU' in files['src/storage/format.cpp']
 assert 'std::uint32_t StorageShardForKey(std::string_view key) noexcept {\n  return RedisSlot(key);' in files['src/storage/format.cpp']
 assert 'std::uint16_t crc = 0;' in files['src/storage/format.cpp'] and '^ 0x1021U' in files['src/storage/format.cpp']
 sources[label]={'commit':head,'source_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in files.items()}}
# Independent bitwise implementation matches the source polynomial/initial
# state, then cross-check against Python's CRC-CCITT routine for every key.
def slot(key):
 crc=0
 for b in key.encode():
  crc^=b<<8
  for _ in range(8):crc=((crc<<1)^ (0x1021 if crc&0x8000 else 0))&0xffff
 assert crc==binascii.crc_hqx(key.encode(),0)
 return crc&0x3fff
keys=[{'key':f'complex_{i}','slot':slot(f'complex_{i}')} for i in range(1,9)]
ownership={str(n):{str(owner):[k['key'] for k in keys if k['slot']%n==owner] for owner in range(n)} for n in [8,12,16]}
profiles={}
for label in heads:
 path=d/f'zset-source-reuse-{label}-self-summary.json';data=json.loads(path.read_text());workers=sorted(data['workers'],key=lambda x:x.get('event_count',0),reverse=True)
 total=data['total_approx_event_count'];assert total==sum(v.get('event_count',0) for v in workers)
 profiles[label]={'summary':str(path.relative_to(r)),'summary_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source':sources[label],
                  'thread_count':len(workers),'sampled_thread_count':sum(v.get('event_count',0)>0 for v in workers),'total_approx_task_clock_seconds':total/1e9,
                  'four_busiest_share':sum(v.get('event_count',0) for v in workers[:4])/total,
                  'threads':[{'tid':v['tid'],'approx_task_clock_seconds':v.get('event_count',0)/1e9,'share':v.get('event_count',0)/total} for v in workers]}
result={'keys':keys,'ownership_by_worker_count':ownership,'measured_worker_count':12,'profiles':profiles,
        'source_model':'RedisSlot=CRC16-CCITT(initial0,poly0x1021,hash-taggedkey)&16383; storage shard equals slot; worker=slot%worker_count. These keys contain no hash tags. Owning worker selection is independent of the random SipHash seed used by field routing and indexes.',
        'limits':'The workload has eight equally selectable keys; actual per-key request counts were not traced. CPU profiles are independent ZINCRBY c80 diagnostics (25s sampling,30s command/counter window). Includes network/background/kernel/polling. No direct TID-to-worker-ID trace was captured, so four busy threads are consistent with the source ownership mapping, not an individually verified binding. Eight/16-worker mappings are source-derived only; no throughput at those worker counts was measured. Existing comparable baselines stay at12 workers.'}
a.output.write_text(json.dumps(result,indent=2)+'\n')
print('12worker owners',{k:v for k,v in ownership['12'].items() if v})
for k,v in profiles.items():print(k,'top4CPUshare',v['four_busiest_share'],'task-clock s',v['total_approx_task_clock_seconds'])
