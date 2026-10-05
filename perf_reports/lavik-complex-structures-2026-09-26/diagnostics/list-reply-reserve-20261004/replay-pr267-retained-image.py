"""Replay recovery reads on copies of the retained image, capturing live hangs."""
from pathlib import Path
import hashlib
import json
import os
import signal
import socket
import subprocess
import time
from host_execution_lock import acquire_host
W=Path(__file__).parent
output=W/'pr267-retained-image-replays.json'
assert not output.exists()
_execution_lock=acquire_host('extent-retained-image-diagnosis')
original=W/'pr267-extent-ci-repro/candidate-round1/lavik-extent-recovery-696331.data'
assert original.exists() and original.stat().st_mode & 0o222 == 0

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
original_sha=sha(original)
versions=json.loads((W/'pr267-extent-native-ci-reproductions.json').read_text())['versions']
root=W/'pr267-retained-image-replay';root.mkdir()
rows=[]

for label in ['candidate','main']:
    v=versions[label];assert sha(v['binary'])==v['binary_sha256']
    d=root/label;d.mkdir();data=d/'working.data'
    subprocess.run(['cp','--reflink=auto',str(original),str(data)],check=True)
    data.chmod(0o600)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    argv=[v['binary'],'--logtostderr','--port',str(port),'--threads','2',
          '--no-pin-workers','--recv-buffers-per-worker','0','--data-file',str(data)]
    record={'version':label,'port':port,'argv':argv,'operations':[],'success':False,'image':str(data)}
    with (d/'server.log').open('w') as log:
        server=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        client=None
        phase={}
        try:
            deadline=time.monotonic()+120
            while True:
                if server.poll() is not None:raise RuntimeError(f'startup exit {server.returncode}')
                try:
                    client=socket.create_connection(('127.0.0.1',port),timeout=1)
                    client.settimeout(2);client.sendall(b'*1\r\n$4\r\nPING\r\n')
                    response=b''
                    while not response.endswith(b'\r\n'):
                        part=client.recv(1)
                        if not part:raise ConnectionError('startup connection closed')
                        response+=part
                    if response==b'+PONG\r\n':break
                except (OSError,TimeoutError):pass
                if client is not None:client.close();client=None
                if time.monotonic()>=deadline:raise TimeoutError('startup readiness120s')
                time.sleep(.05)
            client.settimeout(60)
            def command(args,expected,fill=None):
                phase.clear();phase.update(command=args[0].decode(),key_bytes=len(args[1]),stage='send',received_payload_bytes=0)
                started=time.monotonic()
                frame=b'*'+str(len(args)).encode()+b'\r\n'+b''.join(b'$'+str(len(a)).encode()+b'\r\n'+a+b'\r\n' for a in args)
                client.sendall(frame)
                phase['stage']='reply header';head=b''
                while not head.endswith(b'\r\n'):
                    part=client.recv(1)
                    if not part:raise RuntimeError('closed before reply header')
                    head+=part
                phase['header']=head.decode(errors='replace')
                if fill is None:
                    assert head==expected,(phase,expected)
                else:
                    assert head==b'$'+str(expected).encode()+b'\r\n',(phase,expected)
                    phase['stage']='reply payload'
                    remaining=expected
                    while remaining:
                        part=client.recv(min(65536,remaining))
                        if not part:raise RuntimeError('closed during payload')
                        assert part==fill*len(part),'payload changed'
                        remaining-=len(part);phase['received_payload_bytes']+=len(part)
                    tail=b''
                    while len(tail)<2:
                        part=client.recv(2-len(tail))
                        if not part:raise RuntimeError('closed before bulk trailer')
                        tail+=part
                    assert tail==b'\r\n'
                record['operations'].append({**phase,'seconds':time.monotonic()-started})
                (d/'progress.json').write_text(json.dumps(record,indent=2)+'\n')
                print('OP_PASS',label,args[0].decode(),len(args[1]),time.time(),flush=True)
            external=[bytes([ord('a')+i])*5000+b'-external' for i in range(3)]
            for key in external:
                command([b'STRLEN',key],b':9437184\r\n')
                command([b'GET',key],9437184,b'X')
            command([b'GET',b'i'*(6*1024*1024)],1024*1024,b'I')
            command([b'GET',b's'*(9*1024*1024)],6*1024*1024,b'S')
            for key in external:
                command([b'SET',key,b'small'],b'+OK\r\n')
                command([b'STRLEN',key],b':5\r\n')
            command([b'SET',b'i'*(6*1024*1024),b'small'],b'+OK\r\n')
            command([b'SET',b's'*(9*1024*1024),b'small'],b'+OK\r\n')
            phase={'stage':'shutdown'}
            server.send_signal(signal.SIGINT)
            record['server_exit']=server.wait(timeout=120)
            assert record['server_exit']==0
            record['success']=True
        except Exception as error:
            record['error']=repr(error);record['failed_phase']=dict(phase)
            # Capture only after the original timeout, so debugger pauses do
            # not create the measured failure. This is diagnosis, never QPS.
            print('REPLAY_FAILURE',label,record['failed_phase'],repr(error),flush=True)
            if server.poll() is None:
                with (d/'threads.txt').open('w') as out:
                    subprocess.run(['ps','-L','-p',str(server.pid),'-o','pid,tid,pcpu,stat,wchan:24,comm'],stdout=out,stderr=subprocess.STDOUT)
                try:
                    with (d/'gdb-backtraces.txt').open('w') as out:
                        gdb=subprocess.run(['sudo','-n','gdb','-batch','-ex','set pagination off','-ex','thread apply all bt','-p',str(server.pid)],stdout=out,stderr=subprocess.STDOUT,timeout=45)
                    record['gdb_exit']=gdb.returncode
                except subprocess.TimeoutExpired:record['gdb_error']='45-second diagnostic bound'
        finally:
            if client is not None:client.close()
            try:os.killpg(server.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            server.wait()
    rows.append(record)
    assert sha(original)==original_sha,'original image changed'
    output.write_text(json.dumps({'original_image':str(original),'original_sha256':original_sha,'versions':versions,'rows':rows,
        'method':'Writable independent copies of the same failed image; candidate then main; original2workers,60s socket and120s stop. Replay recovery GETs then overwrites. Capture thread stacks only after an observed failure; original image remains read-only. No throughput claim.'},indent=2)+'\n')
print('ALL_PR267_RETAINED_IMAGE_REPLAYS_FINISHED',time.time(),flush=True)
