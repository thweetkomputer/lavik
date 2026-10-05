"""Preserve original suite order while adding failure phase/retained artifacts."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time
from host_execution_lock import acquire_host
W=Path(__file__).parent
output=W/'stream-window-suite-order-diagnostics.json'
assert not output.exists()
proc=Path('/proc/716418/stat')
identity=proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_STREAM_PROFILES',identity,time.time(),flush=True)
while identity is not None and proc.exists():
    try:
        if proc.read_text().split()[21]!=identity:break
    except FileNotFoundError:break
    time.sleep(15)
_execution_lock=acquire_host('stream-window-suite-order-diagnosis')
previous=json.loads((W/'stream-rdb-timeout-reproductions.json').read_text())
driver=Path('/mnt/dev/lavik-benchmark-binaries/lavik-stream-rdb-diagnostic-driver-763d9076-20261005')
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert sha(driver)==previous['driver_sha256']
filters=('GroupedStreamE2e.*:GroupedTransferE2e.*:'
         'GroupedRdbStreamE2e.FourTypesMultiPageLargeItemsAndMultipleWorkers:'
         'GroupedRdbStreamE2e.RestoreStreamsFourTypesInsideAndOutsideExec:'
         'GroupedRdbStreamE2e.BackupStreamsFourTypesThenImportsAndRestarts')
rows=[]
for label in ['window','parent']:
    v=previous['versions'][label];assert sha(v['binary'])==v['sha256']
    prefix=f'stream-window-suite-order-{label}'
    data=W/(prefix+'-data');data.mkdir()
    env=os.environ.copy();env['LAVIK_TEST_DATA_DIR']=str(data)
    result=W/(prefix+'.json')
    argv=[str(driver),v['binary'],'--gtest_filter='+filters,'--gtest_output=json:'+str(result)]
    print('START',label,time.time(),flush=True);start=time.monotonic()
    with (W/(prefix+'.txt')).open('w') as log:
        run=subprocess.Popen(argv,cwd='/mnt/dev/lavik-complex-next-20261004',env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:run.wait(timeout=1200)
        except BaseException:
            try:os.killpg(run.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            run.wait()
            raise
    tests=json.loads(result.read_text()) if result.exists() else None
    row={'version':label,'argv':argv,'returncode':run.returncode,'seconds':time.monotonic()-start,'tests':tests,'data':str(data)}
    rows.append(row)
    output.write_text(json.dumps({'versions':previous['versions'],'driver':str(driver),'driver_commit':previous['driver_commit'],'driver_sha256':previous['driver_sha256'],'method':'Original selected Stream/transfer/RDB suite order, unchanged frozen production executables and deadlines; only diagnostic phase context/artifact retention. Window then parent on independent file devices, serialized with all benchmark-host work. Subsequent passes do not explain original failure. No throughput claim.','rows':rows},indent=2)+'\n')
    assert sha(v['binary'])==v['sha256']
    print('RESULT',label,run.returncode,time.time(),flush=True)
    if run.returncode:raise SystemExit('Failure retained; inspect phase and image before further runs')
print('ALL_STREAM_WINDOW_SUITE_ORDER_DIAGNOSTICS_PASS',time.time(),flush=True)
