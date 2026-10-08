from pathlib import Path
import json,time
W=Path(__file__).parent
assert 'PRODUCTION_PAIR_READY' in (W/'build-driver.log').read_text()
assert 'CLIENT_READY' in (W/'client-build.log').read_text()
from benchmark import point,R
operations=[('list','LPUSH_RPOP'),('list','RPUSH_LPOP'),('list','LSET_RESIZE'),('zset','ZINCRBY'),('zset','ZADD_MIDDLE_ZPOPMIN'),('hash','HSET'),('set','SADD_SREM')]
protocol={'versions':json.loads((W/'versions.json').read_text()),'operations':operations,'rounds':[1,2,3],'orders':[['main','pr291'],['pr291','main'],['main','pr291']],'size_per_key':8388608,'keys':8,'field_bytes':1024,'connections':320,'seconds':30,'pipeline':1,'client_threads':16,'selection':'Uniform random key; independently equal-probability mixed operation choice. Set chooses uniformly from 2N members with N initially present; exact cardinality deltas use actual SADD/SREM reply counts. List resize alternates 1008/1024 byte replacements across clients. HSET replaces seeded fields; ZINCRBY adds 1 to existing members. Point operations choose among eight seeded positions.','isolation':'Fresh server and fresh allowlisted scratch NVMe for each point; deterministic process/client seeds matched per pair; wait for transaction cleanup after seed. Same native production flags, Bycorf, worker CPUs and devices.','comparison':'Latest main 1dd8a5b3 versus main plus both PR291 commits (local integration 74ba1d1e). PR291 source head 79bdbfeda remains unchanged.','limits':'320 connections and 8 MiB/key only. Time-based closed-loop load; throughput and p99 are reported separately, not matched-throughput causality. No 5120 connections. Three paired repetitions, not statistical proof.'}
(W/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
rows=json.loads((W/'pairs.json').read_text()) if (W/'pairs.json').exists() else []
for round_,labels in zip(protocol['rounds'],protocol['orders']):
 for kind,op in operations:
  for label in labels:
   if any(x['round']==round_ and x['version']==label and x['operation']==op for x in rows):continue
   rows.append(point(label,kind,8388608,op,round_))
   (W/'pairs.json').write_text(json.dumps(rows,indent=2)+'\n')
assert len(rows)==42 and not (R/'spdk-ready.json').exists()
print('ALL_PR291_QPS_PAIRS_COMPLETE',time.time(),flush=True)
