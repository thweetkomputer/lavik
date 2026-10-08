from pathlib import Path
import subprocess,sys,json,time,socket
W=Path(__file__).parent;R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26');sys.path.insert(0,str(R));import run
run.HOST='127.0.0.1';run.PORT=16379
with socket.socket() as probe:
 assert probe.connect_ex(('127.0.0.1',16379)) != 0, 'smoke port is already occupied'
p=subprocess.Popen(['/mnt/dev/peer-bench/redis/v8.8.0/src/src/redis-server','--bind','127.0.0.1','--port','16379','--save','','--appendonly','no','--dir',str(W)],stdout=(W/'random-client-smoke-server.log').open('w'),stderr=subprocess.STDOUT)
rows=[]
try:
 for _ in range(100):
  try:
   if run.query('PING')==b'PONG':break
  except OSError:time.sleep(.05)
 for kind,ops in [('list',['LPUSH_RPOP','RPUSH_LPOP']),('zset',['ZRANK','ZREVRANK'])]:
  for op in ops:
   assert run.query('FLUSHALL')==b'OK';run.fill(kind,1024,8192,8,1,4,16384)
   result=json.loads(subprocess.check_output([str(W/'random-client'),'127.0.0.1','16379',op,'32','8','8192','1024','1','42'],text=True))
   assert result['errors']==0 and result['totals']['count']>0
   counts={run.name(k):run.query(run.COUNT[kind],run.name(k)) for k in range(1,9)}
   assert all(counts[k]==8192+v['net'] for k,v in result['key_counts'].items())
   result['checked_cardinalities']=counts;rows.append(result)
 (W/'random-client-smoke.json').write_text(json.dumps(rows,indent=2))
finally:p.terminate();p.wait(timeout=20)
print('ALL_4_RANDOM_CLIENT_SMOKE_TESTS_PASS')
