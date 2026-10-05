"""Freeze and validate main/combined native binaries without overlapping benchmarks."""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,time
from host_execution_lock import acquire_host
W=Path(__file__).parent
S=Path('/mnt/dev/lavik-complex-next-20261004');B=S/'build-spdk'
output=W/'combined-native-versions.json'
assert not output.exists()
expected={'main':'4610d6077e8e32d59639a5ee88dbe8cbd305aab2','combined':'78e29277618f4ef40ccefab0930cbab667a0a40e'}
waiters=[]
for pid in [760936,760972,738607,719158]:
    proc=Path('/proc')/str(pid)/'stat'
    waiters.append((pid,proc,proc.read_text().split()[21] if proc.exists() else None))
for pid,proc,identity in waiters:
    print('WAIT_FOR_PRIOR_WORK',pid,identity,time.time(),flush=True)
    while identity is not None and proc.exists():
        try:
            if proc.read_text().split()[21]!=identity:break
        except FileNotFoundError:break
        time.sleep(15)
proof=json.loads(subprocess.check_output(['gh','run','view','37260751356','--repo','thweetkomputer/lavik','--json','headSha,conclusion,jobs,url']))
assert proof['headSha']==expected['combined'] and proof['conclusion']=='success'
assert len(proof['jobs'])==17 and all(j['conclusion']=='success' for j in proof['jobs'])
(W/'combined-78e29277-full-ci.json').write_text(json.dumps(proof,indent=2)+'\n')
_execution_lock=acquire_host('combined-native-validation')
def terminate(_signal,_frame):raise SystemExit('validation interrupted')
signal.signal(signal.SIGTERM,terminate)
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
versions={}
temporary=W/'compiler-tmp-combined';temporary.mkdir(exist_ok=True)
assert shutil.disk_usage(temporary).free>10*1024**3
build_environment=dict(os.environ,TMPDIR=str(temporary))
ordered_filter=('GroupedSortedSetWriteE2e.*:GroupedOrderedWriteE2e.SortedSet*:'
 'GroupedOrderedWriteE2e.LargeSortedSetMemberUsesExtents:GroupedDemotionE2e.*:'
 'GroupedStreamE2e.*:GroupedTransferE2e.*:'
 'GroupedRdbStreamE2e.FourTypesMultiPageLargeItemsAndMultipleWorkers:'
 'GroupedRdbStreamE2e.RestoreStreamsFourTypesInsideAndOutsideExec:'
 'GroupedRdbStreamE2e.BackupStreamsFourTypesThenImportsAndRestarts')
blocking_filter=('ListE2eTest.BlockingAndStreamedCommandsDoNotHoldFlushDbGate:'
 'ListE2eTest.StreamBlockingRegistryBroadcastsAndKeepsGroupFifo:'
 'ListE2eTest.DisconnectCancelsActiveBlockingWait:'
 'ListE2eTest.PipelineFlushesRepliesBeforeBlockingCommand:'
 'CollectionE2eTest.SortedSetGeoAndStreamCommandsRecover')
for label,head in expected.items():
    prefix='combined-'+label
    def run(name,argv,env=None,timeout=None):
        print('START',label,name,time.time(),flush=True)
        with (W/(prefix+'-'+name+'.txt')).open('w') as log:
            child=subprocess.Popen(argv,cwd=S,env=build_environment if env is None else dict(env,TMPDIR=str(temporary)),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                code=child.wait(timeout=timeout)
                if code:raise subprocess.CalledProcessError(code,argv)
            except BaseException:
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                child.wait();raise
        print('PASS',label,name,time.time(),flush=True)
    run('checkout',['git','switch','--detach',head])
    run('configure-tests',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=ON','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
    targets=['lavik_grouped_ordered_write_e2e_test','lavik_list_e2e_test','lavik_pubsub_e2e_test']
    run('build-tests',['cmake','--build','build-spdk','--target','lavik','lavik_unit_tests',*targets,'--parallel','4'])
    run('unit-tests',[str(B/'lavik_unit_tests'),'--gtest_filter=GroupedCollectionTest.*:StreamRecords.*:GroupedObjectIndexTest.*:GroupedMetadataArrayTest.*','--gtest_output=json:'+str(W/(prefix+'-unit-tests.json'))],timeout=600)
    drivers={}
    for target in targets:
        path=Path('/mnt/dev/lavik-benchmark-binaries')/(prefix+'-'+target+'-'+head[:8]+'-20261005')
        assert not path.exists();shutil.copyfile(B/target,path);path.chmod(0o755)
        drivers[target]={'path':str(path),'sha256':sha(path)}
    run('configure-production',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=OFF','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
    run('build-production',['cmake','--build','build-spdk','--target','lavik','--parallel','4'])
    cache=(B/'CMakeCache.txt').read_text()
    assert 'BUILD_TESTING:BOOL=OFF' in cache and 'LAVIK_ENABLE_TEST_FAULTS:BOOL=OFF' in cache
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==head
    assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
    binary=Path('/mnt/dev/lavik-benchmark-binaries')/('lavik-'+prefix+'-'+head[:8]+'-20261005')
    assert not binary.exists();shutil.copyfile(B/'lavik',binary);binary.chmod(0o755)
    version={'commit':head,'source_repo':str(S),'binary':str(binary),'sha256':sha(binary),'drivers':drivers,'bycorf_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=S/'bycorf',text=True).strip(),'build':'Existing GCC native SPDK build-spdk cache; production tests/faults OFF, separate test drivers','combined_ci':proof['url'],'compiler_tmpdir':str(temporary)}
    (W/(prefix+'-CMakeCache.txt')).write_text(cache)
    (W/(prefix+'-build.json')).write_text(json.dumps(version,indent=2)+'\n')
    data=W/(prefix+'-test-data');data.mkdir();env=os.environ.copy();env['LAVIK_TEST_DATA_DIR']=str(data)
    for suite,target,filter_ in [('ordered-tests',targets[0],ordered_filter),('blocking-tests',targets[1],blocking_filter)]:
        run(suite,[drivers[target]['path'],str(binary),'--gtest_filter='+filter_,'--gtest_output=json:'+str(W/(prefix+'-'+suite+'.json'))],env,1800)
    run('pubsub-tests',[drivers[targets[2]]['path'],str(binary)],env,600)
    assert sha(binary)==version['sha256']
    assert all(sha(v['path'])==v['sha256'] for v in drivers.values())
    version['tests']={name:json.loads((W/(prefix+'-'+name+'.json')).read_text()) for name in ['unit-tests','ordered-tests','blocking-tests']}
    assert all(x['failures']==0 and x['tests']>0 for x in version['tests'].values())
    version['pubsub_exit']=0;versions[label]=version
    (W/'combined-native-progress.json').write_text(json.dumps(versions,indent=2)+'\n')
output.write_text(json.dumps(versions,indent=2)+'\n')
print('ALL_COMBINED_NATIVE_TESTS_PASS',time.time(),flush=True)
