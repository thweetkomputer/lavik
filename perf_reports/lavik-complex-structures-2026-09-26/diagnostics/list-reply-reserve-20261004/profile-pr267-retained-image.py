"""Replay recovery reads on copies of the retained image, capturing live hangs."""
from pathlib import Path
import hashlib
import json
import os
import signal
import socket
import subprocess
import time
import threading
from host_execution_lock import acquire_host
W=Path(__file__).parent
output=W/'pr267-retained-image-profiles.json'
assert not output.exists()
# Wait for the already scheduled clean Stream pairs and their separate perf.
# The common host lock also serializes against the independent ZSet queue.
proc=Path('/proc/716418/stat')
identity=proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_STREAM_PROFILE_EXIT',identity,time.time(),flush=True)
while proc.exists() and identity is not None:
    try:
        if proc.read_text().split()[21]!=identity:break
    except FileNotFoundError:break
    time.sleep(15)
_execution_lock=acquire_host('extent-retained-image-perf')
original=W/'pr267-extent-ci-repro/candidate-round1/lavik-extent-recovery-696331.data'
assert original.exists() and original.stat().st_mode & 0o222 == 0

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
original_sha=sha(original)
versions=json.loads((W/'pr267-extent-native-ci-reproductions.json').read_text())['versions']
root=W/'pr267-retained-image-profile';root.mkdir()
rows=[]

for label in ['main','candidate']:
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
        profile=None
        sampler=None
        sampling_stop=threading.Event()
        samples=[]
        def sample_progress():
            while not sampling_stop.is_set():
                sample={'monotonic':time.monotonic(),'phase':dict(phase)}
                try:
                    base=Path('/proc')/str(server.pid)
                    sample['io']=(base/'io').read_text()
                    sample['tasks']={}
                    for task in (base/'task').iterdir():
                        sample['tasks'][task.name]={'stat':(task/'stat').read_text(),'wchan':(task/'wchan').read_text(),'schedstat':(task/'schedstat').read_text()}
                except (FileNotFoundError,PermissionError) as error:
                    sample['sample_error']=repr(error)
                samples.append(sample)
                sampling_stop.wait(.5)
        def stop_profile():
            sampling_stop.set()
            if sampler is not None:sampler.join(timeout=2)
            (d/'operation-progress.json').write_text(json.dumps(samples,indent=2)+'\n')
            if profile is not None:
                if profile.poll() is None:
                    subprocess.run(['sudo','-n','kill','-INT','--',f'-{profile.pid}'],check=True)
                try:record['perf_exit']=profile.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    subprocess.run(['sudo','-n','kill','-KILL','--',f'-{profile.pid}'],check=True)
                    profile.wait();record['perf_error']='recorder did not exit within30s'
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
                global profile,sampler
                if args[0]==b'GET' and len(args[1])==9437184:
                    argv=['sudo','-n','perf','record','-e','task-clock','-F','49','--call-graph','dwarf,8192','-p',str(server.pid),'-o',str(d/'long-key.perf')]
                    record['perf_argv']=argv
                    with (d/'perf-record.log').open('w') as perf_log:
                        profile=subprocess.Popen(argv,stdout=perf_log,stderr=subprocess.STDOUT,start_new_session=True)
                    time.sleep(.3)
                    if profile.poll() is not None:raise RuntimeError('perf recorder exited before GET')
                    sampler=threading.Thread(target=sample_progress,daemon=True);sampler.start()
                started=time.monotonic()
                phase['started_monotonic']=started
                frame=b'*'+str(len(args)).encode()+b'\r\n'+b''.join(b'$'+str(len(a)).encode()+b'\r\n'+a+b'\r\n' for a in args)
                client.sendall(frame)
                phase['send_seconds']=time.monotonic()-started
                phase['stage']='reply header';head=b''
                while not head.endswith(b'\r\n'):
                    part=client.recv(1)
                    if not part:raise RuntimeError('closed before reply header')
                    head+=part
                phase['header']=head.decode(errors='replace')
                phase['header_seconds']=time.monotonic()-started
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
                if args[0]==b'GET' and len(args[1])==9437184:stop_profile()
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
            stop_profile()
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
            stop_profile()
            if client is not None:client.close()
            try:os.killpg(server.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            server.wait()
    rows.append(record)
    assert sha(original)==original_sha,'original image changed'
    output.write_text(json.dumps({'original_image':str(original),'original_sha256':original_sha,'versions':versions,'rows':rows,
        'method':'Diagnostic perf on independently writable copies of retained image, main then candidate. Original2workers,60s socket and120s stop. Only9MiBkey GET is sampled:49Hz task-clock/DWARF on all process threads; proc IO/task CPU/wchan/schedstat every0.5s. Record send/header/full response times. Stop recorder before any failure debugger attachment. Sampling overhead prevents direct latency/QPS comparison. Original image SHA remains unchanged; rawperf/stacks stay local.'},indent=2)+'\n')
print('ALL_PR267_RETAINED_IMAGE_PROFILES_FINISHED',time.time(),flush=True)
