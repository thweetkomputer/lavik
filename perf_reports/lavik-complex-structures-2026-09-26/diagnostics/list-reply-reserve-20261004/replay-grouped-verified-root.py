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
output=W/'grouped-verified-root-replays.json'
assert not output.exists()
# Do not overlap the scheduled Stream or original failure diagnosis.
waiters=[]
for pid in [716418, 718823, 733834, 719158]:
    proc=Path('/proc')/str(pid)/'stat'
    identity=proc.read_text().split()[21] if proc.exists() else None
    waiters.append((pid,proc,identity))
for pid,proc,identity in waiters:
    print('WAIT_FOR_DIAGNOSTIC',pid,identity,time.time(),flush=True)
    while identity is not None and proc.exists():
        try:
            if proc.read_text().split()[21]!=identity:break
        except FileNotFoundError:break
        time.sleep(5)
_execution_lock=acquire_host('grouped-verified-root-retained-image')
import zipfile
run_id=37258994628
artifact_id=11323789590
expected='28d7cca498655e02f46407adb65335219b10ee6b'
repo='thweetkomputer/lavik'
run=json.loads(subprocess.check_output(['gh','run','view',str(run_id),'--repo',repo,'--json','headSha,url,jobs']))
assert run['headSha']==expected
# A failed-shard retry may omit reused build jobs from the latest attempt.
# Verify the exact immutable job that produced this artifact instead.
build_job=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/actions/jobs/111602005480']))
assert build_job['run_id']==run_id and build_job['head_sha']==expected
assert build_job['name']=='Build tests (amd64)' and build_job['conclusion']=='success'
metadata=json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/actions/artifacts/{artifact_id}']))
assert metadata['name']=='ci-build-amd64' and not metadata['expired']
assert metadata['workflow_run']['id']==run_id
artifact_dir=W/'grouped-verified-root-ci';artifact_dir.mkdir()
archive=artifact_dir/'ci-build.zip'
print('DOWNLOAD_ARTIFACT',artifact_id,time.time(),flush=True)
with archive.open('wb') as f:
    subprocess.run(['gh','api',f'repos/{repo}/actions/artifacts/{artifact_id}/zip'],stdout=f,check=True)
with zipfile.ZipFile(archive) as z:
    assert z.namelist()==['ci-build.tar.zst']
    z.extract('ci-build.tar.zst',artifact_dir)
subprocess.run(['tar','--zstd','-xf',str(artifact_dir/'ci-build.tar.zst'),'-C',str(artifact_dir),'build_ci/lavik','build_ci/lavik_extent_recovery_e2e_test','build_ci/ci-build-bundle.json'],check=True)
build=artifact_dir/'build_ci'
manifest=json.loads((build/'ci-build-bundle.json').read_text())
assert manifest['architecture']=='x86_64' and manifest['revision']==expected

original=W/'pr267-extent-ci-repro/candidate-round1/lavik-extent-recovery-696331.data'
assert original.exists() and original.stat().st_mode & 0o222 == 0

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
original_sha=sha(original)
assert original_sha=='b4e0113cf9b7dcbe03175c5e5665be8589ebef9dbc9c2847adc3cd3010b956ae'
versions=json.loads((W/'pr267-extent-native-ci-reproductions.json').read_text())['versions']
versions={'main':versions['main'],'candidate':{
    'source_head':expected,'built_revision':manifest['revision'],
    'ci_run':run['url'],'artifact_id':artifact_id,
    'binary':str(build/'lavik'),'binary_sha256':sha(build/'lavik'),
    'test':str(build/'lavik_extent_recovery_e2e_test'),
    'test_sha256':sha(build/'lavik_extent_recovery_e2e_test')}}
(artifact_dir/'provenance.json').write_text(json.dumps(versions,indent=2)+'\n')
root=W/'grouped-verified-root-replay';root.mkdir()
rows=[]

for round_,label in [(1,'main'),(1,'candidate'),(2,'candidate'),(2,'main'),(3,'main'),(3,'candidate')]:
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
        'method':'Three AB/BA/AB pairs on independent writable copies of the same retained image. Exact main194 and root-reuse28 CI binaries; 2workers, original60s socket and120s shutdown. Verify complete reply payloads then overwrites and clean shutdown. Process IO counters bracket each operation and include background IO. No perf sampling and no general QPS claim. Stop at first failure and retain diagnostics. Original image remains read-only and SHA checked after each run.'},indent=2)+'\n')
    assert record['success'], 'inspect failure before retrying'
print('ALL_GROUPED_VERIFIED_ROOT_REPLAYS_FINISHED',time.time(),flush=True)
