"""Finish production-window blocking checks with unchanged CI test sources."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time
from host_execution_lock import acquire_host
W=Path(__file__).parent
output=W/'stream-window-blocking-validation.json';assert not output.exists()
proc=Path('/proc/719158/stat');generation=proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_SUITE_ORDER',generation,time.time(),flush=True)
while generation is not None and proc.exists():
    try:
        if proc.read_text().split()[21]!=generation:break
    except FileNotFoundError:break
    time.sleep(5)
suite=json.loads((W/'stream-window-suite-order-diagnostics.json').read_text())
assert len(suite['rows'])==2 and all(r['returncode']==0 for r in suite['rows'])
version=suite['versions']['window']
assert version['commit']=='5b9ebdedecc0cc7a3fea93fb73b1fbbb6b7186c6'
_execution_lock=acquire_host('stream-window-blocking-validation')
def terminate(_signal,_frame):raise SystemExit('validation interrupted')
signal.signal(signal.SIGTERM,terminate)
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert sha(version['binary'])==version['sha256']
source='19496654cc43b21df11fb59be60e174dc4c89dbc'
repo='/mnt/dev/lavik-complex-combined-20261005'
sources=['tests/list_e2e_test.cpp','tests/pubsub_e2e_test.cpp','tests/support/test_data_path.h']
assert subprocess.check_output(['git','diff',source,version['commit'],'--',*sources],cwd=repo)==b''
directory=W/'stream-window-blocking-ci-drivers';directory.mkdir()
subprocess.run(['tar','--zstd','-xf',str(W/'pr267-extent-ci-repro/main/ci-build.tar.zst'),'-C',str(directory),'build_ci/lavik_list_e2e_test','build_ci/lavik_pubsub_e2e_test','build_ci/ci-build-bundle.json'],check=True)
manifest=json.loads((directory/'build_ci/ci-build-bundle.json').read_text())
assert manifest['revision']==source and manifest['architecture']=='x86_64'
filters=('ListE2eTest.BlockingAndStreamedCommandsDoNotHoldFlushDbGate:'
 'ListE2eTest.StreamBlockingRegistryBroadcastsAndKeepsGroupFifo:'
 'ListE2eTest.DisconnectCancelsActiveBlockingWait:'
 'ListE2eTest.PipelineFlushesRepliesBeforeBlockingCommand:'
 'CollectionE2eTest.SortedSetGeoAndStreamCommandsRecover')
data=W/'stream-window-blocking-data';data.mkdir();env=dict(os.environ,LAVIK_TEST_DATA_DIR=str(data))
rows=[]
for name,driver,args,timeout in [('blocking','lavik_list_e2e_test',['--gtest_filter='+filters,'--gtest_output=json:'+str(W/'stream-window-blocking-tests.json')],600),('pubsub','lavik_pubsub_e2e_test',[],120)]:
    executable=directory/'build_ci'/driver
    argv=[str(executable),version['binary'],*args]
    print('START',name,time.time(),flush=True)
    start=time.monotonic()
    with (W/f'stream-window-{name}-tests.txt').open('w') as log:
        child=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:code=child.wait(timeout=timeout)
        except BaseException:
            try:os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            child.wait();raise
    rows.append({'suite':name,'argv':argv,'test_sha256':sha(executable),'exit_code':code,'seconds':time.monotonic()-start})
    output.write_text(json.dumps({'version':version,'driver_source':source,'driver_artifact':11316029042,'driver_ci':'https://github.com/eloqdata/lavik/actions/runs/37237724710','identical_test_sources':sources,'rows':rows,'method':'Unchanged main194 CI protocol test drivers run against the frozen native production window5b binary. Shared benchmark-host lock; original commands and internal timeouts. Test driver build differs from server build and is recorded separately. No performance claim.'},indent=2)+'\n')
    assert code==0,(name,code)
result=json.loads((W/'stream-window-blocking-tests.json').read_text())
assert result['tests']==5 and result['failures']==0
assert sha(version['binary'])==version['sha256']
print('ALL_STREAM_WINDOW_BLOCKING_TESTS_PASS',time.time(),flush=True)
