"""Check the candidate under unchanged limits after retaining a failed baseline."""
from pathlib import Path
import hashlib,json,os,signal,socket,subprocess,time
from host_execution_lock import acquire_host
W=Path(__file__).parent
output=W/'grouped-verified-root-candidate-replays.json'
assert not output.exists()
prior=json.loads((W/'grouped-verified-root-replays.json').read_text())
assert len(prior['rows'])==1 and prior['rows'][0]['version']=='main'
assert not prior['rows'][0]['success'] and prior['rows'][0]['failed_phase']['key_bytes']==9437184
assert prior['rows'][0]['error']=="TimeoutError('timed out')"
_execution_lock=acquire_host('grouped-verified-root-candidate-replays')
def terminate(_signal,_frame):raise SystemExit('replay interrupted')
signal.signal(signal.SIGTERM,terminate)
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
versions=prior['versions']
expected='28d7cca498655e02f46407adb65335219b10ee6b'
assert versions['candidate']['source_head']==expected and versions['candidate']['built_revision']==expected
assert versions['candidate']['binary_sha256']=='3b3dbc5482bf6586b0f06e00d92a6c5e589f58528b13105d01ea3b8a226e5090'
manifest=json.loads((W/'grouped-verified-root-ci/build_ci/ci-build-bundle.json').read_text())
assert manifest['revision']==expected and manifest['architecture']=='x86_64'
original=Path(prior['original_image']);original_sha=prior['original_sha256']
assert original_sha=='b4e0113cf9b7dcbe03175c5e5665be8589ebef9dbc9c2847adc3cd3010b956ae'
assert original.stat().st_mode & 0o222 == 0 and sha(original)==original_sha
root=W/'grouped-verified-root-replay'
assert root.is_dir() and all(not (root/f'candidate-round{n}').exists() for n in [1,2,3])
rows=[]

for round_,label in [(1,'candidate'),(2,'candidate'),(3,'candidate')]:
    v=versions[label];assert sha(v['binary'])==v['binary_sha256']
    d=root/f'{label}-round{round_}';d.mkdir();data=d/'working.data'
    subprocess.run(['cp','--reflink=auto',str(original),str(data)],check=True)
    data.chmod(0o600)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    argv=[v['binary'],'--logtostderr','--port',str(port),'--threads','2',
          '--no-pin-workers','--recv-buffers-per-worker','0','--data-file',str(data)]
    record={'version':label,'round':round_,'port':port,'argv':argv,'operations':[],'success':False,'image':str(data)}
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
                io_before=(Path('/proc')/str(server.pid)/'io').read_text()
                started=time.monotonic()
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
                elapsed=time.monotonic()-started
                io_after=(Path('/proc')/str(server.pid)/'io').read_text()
                record['operations'].append({**phase,'seconds':elapsed,'proc_io_before':io_before,'proc_io_after':io_after})
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
        'method':'Three candidate-only replays on independent writable copies of the same retained image, after main194 timed out under the original60s socket limit. Preserve the original failed baseline in grouped-verified-root-replays.json; this is not a completed paired comparison. Exact root-reuse28 CI binary,2workers, original60s socket and120s shutdown. Verify all reply bytes, overwrites and clean shutdown. Process IO includes background work. No perf sampling or general QPS claim; stop at first failure.'},indent=2)+'\n')
    assert record['success'], 'inspect failure before retrying'
print('ALL_GROUPED_VERIFIED_ROOT_CANDIDATE_REPLAYS_FINISHED',time.time(),flush=True)
