"""Isolate 5009-byte-key overwrites; never reinterpret this as the original full CI test."""
from pathlib import Path
import hashlib,json,os,signal,socket,subprocess,time
from host_execution_lock import acquire_host
W=Path(__file__).parent
OUTPUT=W/'pr267-overwrite-diagnostics.json'
ROOT=W/'pr267-overwrite-diagnostics'
assert not OUTPUT.exists() and not ROOT.exists()
script_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
versions=json.loads((W/'pr267-extent-native-ci-reproductions.json').read_text())['versions']
assert versions['main']['source_head']=='19496654cc43b21df11fb59be60e174dc4c89dbc'
assert versions['candidate']['source_head']=='343e951e3341593cc46b2cfae42f7d8f9b26304e'
original=W/'pr267-extent-ci-repro/candidate-round1/lavik-extent-recovery-696331.data'
expected_image='b4e0113cf9b7dcbe03175c5e5665be8589ebef9dbc9c2847adc3cd3010b956ae'
method=('Focused diagnostic, two AB/BA rounds on private copies of the retained image. '
        'Skip the prior bulk GET sequence deliberately: test three 5009-byte keys, '
        'overwrite each with small, then restart from2 to3workers and read back all three. '
        'This changes original CI history and cannot prove its SET timeout fixed or compare QPS. '
        'Original60s socket/120s shutdown limits; no perf, timeout increases or retry after a failed operation. '
        'Record INFO at readiness/completion and /proc per operation; additional INFO and debugger stacks follow failure only. '
        'Any failure stops that version and round; remaining independently copied conditions still run. '
        'Host lock covers all hashing, copies, server lifetimes and diagnostics.')
rows=[]
def save():
 OUTPUT.write_text(json.dumps({'versions':versions,'original_image':str(original),'original_sha256':expected_image,
                               'script_sha256':script_sha,'method':method,'rows':rows},indent=2)+'\n')
def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def terminate(_sig,_frame):raise SystemExit('diagnostic interrupted')
signal.signal(signal.SIGTERM,terminate)
lock=acquire_host('pr267-focused-overwrite-diagnosis')
assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==script_sha
assert original.stat().st_mode & 0o222 == 0 and sha(original)==expected_image
for v in versions.values():assert sha(v['binary'])==v['binary_sha256']
ROOT.mkdir()
keys=[bytes([ord('a')+i])*5000+b'-external' for i in range(3)]
class Connection:
 def __init__(self,port,timeout=60):
  self.socket=socket.create_connection(('127.0.0.1',port),timeout=timeout)
  self.socket.settimeout(timeout);self.stream=self.socket.makefile('rb')
 def close(self):
  self.stream.close();self.socket.close()
 def request(self,args):
  frame=b'*'+str(len(args)).encode()+b'\r\n'+b''.join(b'$'+str(len(x)).encode()+b'\r\n'+x+b'\r\n' for x in args)
  self.socket.sendall(frame);f=self.stream;head=f.readline()
  if not head.endswith(b'\r\n'):raise EOFError('incomplete reply header')
  if head.startswith(b'+'):return head[1:-2]
  if head.startswith(b':'):return int(head[1:-2])
  if head.startswith(b'$'):
   size=int(head[1:-2]);assert 0<=size<1024**2,('unexpected reply length',size)
   data=f.read(size+2)
   if len(data)!=size+2 or not data.endswith(b'\r\n'):raise EOFError('incomplete bulk reply')
   return data[:-2]
  raise RuntimeError('unexpected reply '+repr(head))
def request(port,args,timeout=60):
 client=Connection(port,timeout)
 try:return client.request(args)
 finally:client.close()
def process_snapshot(pid):
 snap={}
 for name in ['io','stat','status']:
  try:snap[name]=(Path('/proc')/str(pid)/name).read_text()
  except OSError as exc:snap[name]=repr(exc)
 return snap
for round_,order in [(1,['main','candidate']),(2,['candidate','main'])]:
 for label in order:
  folder=ROOT/f'{label}-round{round_}';folder.mkdir();data=folder/'working.data'
  subprocess.run(['cp','--reflink=auto',str(original),str(data)],check=True);data.chmod(0o600)
  row={'version':label,'round':round_,'image':str(data),'success':False,'phases':[]};rows.append(row);save()
  try:
   for workers in [2,3]:
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    phase={'workers':workers,'operations':[],'success':False};row['phases'].append(phase)
    argv=[versions[label]['binary'],'--logtostderr','--port',str(port),'--threads',str(workers),
          '--no-pin-workers','--recv-buffers-per-worker','0','--data-file',str(data)]
    phase['argv']=argv;context={'stage':'startup'};client=None
    with (folder/f'server-{workers}.log').open('w') as log:
     server=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
     try:
      deadline=time.monotonic()+120
      while True:
       if server.poll() is not None:raise RuntimeError(f'startup exit {server.returncode}')
       try:
        client=Connection(port,2)
        if client.request([b'PING'])==b'PONG':
         client.socket.settimeout(60);break
       except (OSError,EOFError,RuntimeError):pass
       if client is not None:client.close();client=None
       if time.monotonic()>=deadline:raise TimeoutError('readiness120s')
       time.sleep(.05)
      context={'stage':'ready-info'}
      info=request(port,[b'INFO']);assert isinstance(info,bytes)
      (folder/f'info-{workers}-ready.txt').write_bytes(info)
      for index,key in enumerate(keys):
       operations=[([b'STRLEN',key],9437184),([b'SET',key,b'small'],b'OK'),([b'GET',key],b'small')] if workers==2 else [([b'GET',key],b'small')]
       for args,expected in operations:
        context={'stage':'command','command':args[0].decode(),'key_index':index,'key_bytes':len(key)}
        before=process_snapshot(server.pid)
        phase['inflight']={**context,'proc_before':before};save()
        started=time.monotonic()
        reply=client.request(args)
        elapsed=time.monotonic()-started
        assert reply==expected,('reply mismatch',context,repr(reply))
        phase['operations'].append({**context,'seconds':elapsed,'proc_before':before,'proc_after':process_snapshot(server.pid)})
        phase.pop('inflight',None);save();print('PASS',label,round_,workers,context,elapsed,flush=True)
      context={'stage':'completed-info'}
      (folder/f'info-{workers}-after.txt').write_bytes(request(port,[b'INFO']))
      context={'stage':'shutdown'};server.send_signal(signal.SIGINT)
      phase['server_exit']=server.wait(timeout=120);assert phase['server_exit']==0
      phase['success']=True
     except Exception as exc:
      phase['error']=repr(exc);phase['failed_context']=context;phase['proc_after_failure']=process_snapshot(server.pid);save()
      if server.poll() is None:
       try:(folder/f'info-{workers}-failure.txt').write_bytes(request(port,[b'INFO'],2))
       except Exception as info_error:phase['info_error']=repr(info_error)
       with (folder/f'threads-{workers}.txt').open('w') as out:
        subprocess.run(['ps','-L','-p',str(server.pid),'-o','pid,tid,pcpu,stat,wchan:24,comm'],stdout=out,stderr=subprocess.STDOUT,check=False)
       try:
        with (folder/f'gdb-{workers}.txt').open('w') as out:
         result=subprocess.run(['sudo','-n','gdb','-batch','-ex','set pagination off','-ex','thread apply all bt','-p',str(server.pid)],stdout=out,stderr=subprocess.STDOUT,timeout=45)
        phase['gdb_exit']=result.returncode
       except subprocess.TimeoutExpired:phase['gdb_error']='45-second diagnostic limit'
      raise
     finally:
      if client is not None:client.close()
      if server.poll() is None:
       try:os.killpg(server.pid,signal.SIGKILL)
       except ProcessLookupError:pass
      server.wait();save()
   row['success']=True
  except Exception as exc:
   row['error']=repr(exc);print('FAILED',label,round_,repr(exc),flush=True)
  finally:
   assert sha(original)==expected_image;save()
print('ALL_PR267_OVERWRITE_DIAGNOSTICS_COMPLETE',sum(r['success'] for r in rows),len(rows),time.time(),flush=True)
