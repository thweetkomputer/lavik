"""Four-system random-key mixed writes with independently seeded points."""
import os,sys,json,subprocess,shlex,time,re,hashlib
from pathlib import Path
sys.path.insert(0,os.environ['LAVIK_BENCH_ROOT'])
import run
W=Path(__file__).parent
product=sys.argv[1]
measurements=0
profiling='--profile' in sys.argv
if profiling:sys.argv.remove('--profile')
run.OPS['list']=('LINDEX','LSET','LPUSH_RPOP','RPUSH_LPOP')
run.OPS['zset']=('ZRANK','ZSCORE','ZADD_HEAD_ZPOPMAX','ZADD_RANDOM_ZPOPMIN','ZADD_TAIL_ZPOPMIN')
if '--writes-only' in sys.argv:
 sys.argv.remove('--writes-only')
 for kind in ('list','zset'):run.OPS[kind]=tuple(x for x in run.OPS[kind] if '_' in x)

original_validate=run.validate
def validate(kind,field_bytes,entries,keys,product,after=False):
 if not after:return original_validate(kind,field_bytes,entries,keys,product,after)
 if product=='kvrocks':
  assert set(run.query('KEYS','*'))=={run.name(i).encode() for i in range(1,keys+1)}
 else:assert run.query('DBSIZE')==keys
 counts={run.name(i):run.query(run.COUNT[kind],run.name(i)) for i in range(1,keys+1)}
 assert all(entries//2<=n<=entries*2 for n in counts.values()),counts
 return {'keys':keys,'entries_per_key':entries,'field_bytes':field_bytes,'sample_cardinalities':counts}
run.validate=validate


def settle():
 if product=='lavik':return run.wait_for_tx_cleanup()
 started=time.monotonic()
 if product=='kvrocks':
  fields=['num_running_flushes','memtable_flush_pending','compaction_pending','num_running_compactions']
  stable=0
  while time.monotonic()-started<300:
   info=dict(line.split(':',1) for line in run.query('INFO','ALL').decode().splitlines() if ':' in line)
   state={name:int(info[name]) for name in fields}
   stable=stable+1 if not any(state.values()) else 0
   if stable==2:return {'seconds':time.monotonic()-started,'method':'two idle RocksDB background snapshots two seconds apart','state':state}
   time.sleep(2)
  raise TimeoutError('Kvrocks seed compaction/flush did not settle')
 time.sleep(2)
 return {'seconds':time.monotonic()-started,'method':'two seconds idle after synchronous fill'}

def counters(info):
 result={}
 for line in info.decode().splitlines():
  if not line.startswith('cmdstat_'):continue
  key,values=line.split(':',1)
  result[key.removeprefix('cmdstat_')]={k:float(v) for k,v in (x.split('=',1) for x in values.split(','))}
 return result

def measure(directory,kind,size,field_bytes,entries,keys,op,conns,seconds,client_threads):
 stem=f'{kind}-{size}-{field_bytes}-{op.lower()}-c{conns}'
 global measurements
 # Every random mutation starts from the same deterministic seeded population;
 # previous time-based operators must not determine the next operator's layout.
 if '_' in op and measurements:
  assert run.query(*(['FLUSHALL'] if product=='kvrocks' else ['FLUSHALL','SYNC']))==b'OK'
  run.save(directory/(stem+'.fill.json'),run.fill(kind,field_bytes,entries,keys,1,8,16384))
 run.save(directory/(stem+'.settled.json'),settle())
 measurements+=1
 before_counts=run.validate(kind,field_bytes,entries,keys,product,after=True)
 assert set(before_counts['sample_cardinalities'].values())=={entries}
 run.save(directory/(stem+'.before-cardinality.json'),before_counts)
 argv=['taskset','-c','0-15','/mnt/dev/random-client-main-c55e52c9-20261008',run.HOST,str(run.PORT),op,str(conns),str(keys),str(entries),str(field_bytes),str(seconds),os.environ.get('BENCH_CLIENT_SEED','42')]
 run.save(directory/(stem+'.command.json'),argv)
 ssh=(['sudo','-u','azureuser'] if os.geteuid()==0 else [])+['ssh','-o','BatchMode=yes',run.CLIENT]
 finish_profile=None
 if profiling:
  import profile_capture
  finish_profile=profile_capture.start(directory,stem)
 before=run.query('INFO','ALL'); start=time.monotonic()
 with (directory/(stem+'.client.json')).open('w') as out,(directory/(stem+'.client-errors.txt')).open('w') as err:
  subprocess.run([*ssh,'ulimit -n 65535; exec /usr/bin/time -v '+shlex.join(argv)],stdout=out,stderr=err,timeout=seconds+180,check=True)
 elapsed=time.monotonic()-start;after=run.query('INFO','ALL')
 if finish_profile:finish_profile()
 for label,info in [('before',before),('after',after)]:
  (directory/(stem+'.info-'+label+'.txt')).write_bytes(info.replace(b'\r\n',b'\n'))
 raw=json.loads((directory/(stem+'.client.json')).read_text());assert raw['errors']==0 and raw['seconds']==seconds and raw['connections']==conns
 commands=raw['commands'];a,b=counters(before),counters(after);delta={}
 for name in set(a)|set(b):
  calls=b.get(name,{}).get('calls',0)-a.get(name,{}).get('calls',0)
  failed=b.get(name,{}).get('failed_calls',0)-a.get(name,{}).get('failed_calls',0)
  rejected=b.get(name,{}).get('rejected_calls',0)-a.get(name,{}).get('rejected_calls',0)
  assert min(calls,failed,rejected)>=0 and failed==rejected==0,(name,calls,failed,rejected)
  if calls:delta[name]=calls
 assert set(delta)<=set(x.lower() for x in commands)|{'info'},delta
 assert all(delta.get(name.lower(),0)==v['count'] for name,v in commands.items()),(delta,commands)
 assert sum(v['count'] for v in commands.values())==raw['totals']['count']
 after_cardinality=run.validate(kind,field_bytes,entries,keys,product,after=True)
 run.save(directory/(stem+'.after-cardinality.json'),after_cardinality)
 assert all(after_cardinality['sample_cardinalities'][k]==before_counts['sample_cardinalities'][k]+v['net'] for k,v in raw['key_counts'].items())
 assert sum(v['first'] for v in raw['key_counts'].values())==commands[next(iter(commands))]['count']
 if '_' in op:
  assert sum(v['second'] for v in raw['key_counts'].values())==list(commands.values())[1]['count']
  assert .48<=list(commands.values())[0]['count']/raw['totals']['count']<=.52
 row={'product':directory.name,'type':kind,'logical_bytes':size,'field_bytes':field_bytes,'entries_per_key':entries,'keys':keys,'operation':op,'connections':conns,'qps':raw['totals']['qps'],'p50_ms':raw['totals']['p50_ms'],'p99_ms':raw['totals']['p99_ms'],'p999_ms':raw['totals']['p999_ms'],'requests':raw['totals']['count'],'seconds':seconds,'elapsed_seconds':elapsed,'commands':commands,'key_counts':raw['key_counts'],'client_elapsed_seconds':raw['elapsed_seconds'],'command_audit':{'passed':True,'server_counts':delta,'client_counts':{k:v['count'] for k,v in commands.items()}},'bounded':{'baseline':entries,'maximum_guard':entries*2,'minimum_guard':entries//2,'observed_push_min':raw['observed_push_min'],'observed_push_max':raw['observed_push_max'],'all_final_counts':after_cardinality['sample_cardinalities']}}
 run.save(directory/(stem+'.result.json'),row)
 print(time.strftime('%F %T',time.gmtime()),directory.name,stem,f'{row["qps"]:.0f} QPS p99={row["p99_ms"]:.3f} ms COUNTS_VERIFIED',flush=True)
run.measure=measure
if '--only-op' in sys.argv:
 index=sys.argv.index('--only-op');only=sys.argv[index+1];del sys.argv[index:index+2]
 for kind in ('list','zset'):run.OPS[kind]=(only,)
run.main()
