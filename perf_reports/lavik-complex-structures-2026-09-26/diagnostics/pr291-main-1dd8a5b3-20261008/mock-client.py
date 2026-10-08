from pathlib import Path
import json,socketserver,threading,subprocess
W=Path(__file__).parent
class Server(socketserver.ThreadingTCPServer):
 allow_reuse_address=True;daemon_threads=True
class Handler(socketserver.StreamRequestHandler):
 def handle(self):
  while True:
   line=self.rfile.readline()
   if not line:return
   assert line.startswith(b'*');args=[]
   for i in range(int(line[1:])):
    n=int(self.rfile.readline()[1:]);args.append(self.rfile.read(n));assert self.rfile.read(2)==b'\r\n'
   op,key,*tail=args
   with self.server.lock:
    self.server.counts[op.decode()]=self.server.counts.get(op.decode(),0)+1
    if op in (b'SADD',b'SREM'):
     pos=int(tail[0][:8]);present=pos in self.server.members[key]
     reply=int(not present) if op==b'SADD' else int(present)
     if op==b'SADD':self.server.members[key].add(pos)
     else:self.server.members[key].discard(pos)
     wire=f':{reply}\r\n'.encode()
    elif op==b'HSET':
     assert tail[0].startswith(b'f') and len(tail[1])==64;wire=b':0\r\n'
    elif op==b'LSET':
     assert 0<=int(tail[0])<8192 and len(tail[1]) in (48,64);wire=b'+OK\r\n'
    elif op==b'ZINCRBY':
     assert tail[0]==b'1';pos=int(tail[1][:8]);index=(key,pos);score=self.server.scores.get(index,pos)+1;self.server.scores[index]=score;data=str(score).encode();wire=b'$'+str(len(data)).encode()+b'\r\n'+data+b'\r\n'
    else:raise ValueError(op)
   self.wfile.write(wire)
results=[]
for op in ['HSET','SADD_SREM','LSET_RESIZE','ZINCRBY']:
 with Server(('127.0.0.1',0),Handler) as server:
  server.lock=threading.Lock();server.counts={};server.scores={};server.members={f'complex_{i}'.encode():set(range(8192)) for i in [1,2]}
  worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
  p=subprocess.run([str(W/'random-client'),'127.0.0.1',str(server.server_address[1]),op,'4','2','8192','64','1','42'],capture_output=True,text=True,check=True)
  result=json.loads(p.stdout);assert result['errors']==0
  assert {k:v['count'] for k,v in result['commands'].items()}==server.counts
  if op=='SADD_SREM':
   for k,v in result['key_counts'].items():assert 8192+v['net']==len(server.members[k.encode()])
  server.shutdown();worker.join()
  results.append({'operation':op,'passed':True,'server_counts':server.counts,'client_counts':{k:v['count'] for k,v in result['commands'].items()}})
(W/'mock-client-validation.json').write_text(json.dumps(results,indent=2)+'\n')
print('CLIENT_PROTOCOL_VALIDATED')
