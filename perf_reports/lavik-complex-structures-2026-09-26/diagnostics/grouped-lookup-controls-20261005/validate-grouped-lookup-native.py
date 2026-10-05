"""Freeze and validate existing grouped lookup candidates native binaries without overlapping benchmarks."""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,time
from host_execution_lock import acquire_host
from native_build_provenance import native_dependency_provenance
W=Path(__file__).parent
S=Path('/mnt/dev/lavik-complex-next-20261004');B=S/'build-spdk'
output=W/'grouped-lookup-native-versions.json'
assert not output.exists()
expected={'inline':'2e6e4f3559d284e6fe5d0dddc7eb1de5929761ae','decoded':'8babe581213f2cd781f13665a45fdbf1012cf449'}
proc=Path('/proc/790686/stat');identity=proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_PRIOR_SCORE_WORK',identity,time.time(),flush=True)
while identity is not None and proc.exists():
    try:
        if proc.read_text().split()[21]!=identity:break
    except FileNotFoundError:break
    time.sleep(15)
proofs={}
for label,pr,run_id in [('inline',271,37241742696),('decoded',272,37241670139)]:
    actual=json.loads(subprocess.check_output(['gh','pr','view',str(pr),'--repo','eloqdata/lavik','--json','headRefOid']))
    assert actual['headRefOid']==expected[label]
    proof=json.loads(subprocess.check_output(['gh','run','view',str(run_id),'--repo','eloqdata/lavik','--json','headSha,conclusion,jobs,url']))
    assert proof['headSha']==expected[label] and proof['conclusion']=='success'
    assert len(proof['jobs'])==17 and all(j['conclusion']=='success' for j in proof['jobs'])
    proofs[label]=proof
    (W/f'grouped-lookup-{label}-full-ci.json').write_text(json.dumps(proof,indent=2)+'\n')
_execution_lock=acquire_host('grouped-lookup-native-validation')
def terminate(_signal,_frame):raise SystemExit('validation interrupted')
signal.signal(signal.SIGTERM,terminate)
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
baseline=json.loads((W/'zset-source-reuse-versions.json').read_text())['previous']
assert baseline['commit']=='067c75891f819831620e277eac0592c360f8b585'
assert baseline['sha256']=='656b990fa10c001194208082caecff584556fad572fd7dbcc74f061c3dd97ec3'
assert sha(baseline['binary'])==baseline['sha256']
baseline_ci=json.loads(subprocess.check_output(['gh','run','view','37241392671','--repo','eloqdata/lavik','--json','headSha,conclusion,jobs,url']))
assert baseline_ci['headSha']==baseline['commit'] and baseline_ci['conclusion']=='success'
assert len(baseline_ci['jobs'])==17 and all(j['conclusion']=='success' for j in baseline_ci['jobs'])
baseline_tests=json.loads((W/'zset-source-reuse-previous-native-tests.json').read_text())
assert baseline_tests['failures']==0 and baseline_tests['tests']>0
baseline['tests']={'native-tests':baseline_tests}
baseline['full_fault_enabled_ci']=baseline_ci['url']
baseline['provenance_note']='Reuse previously frozen exact parent067 binary; native test and CI evidence retained under zset-source-reuse, not a new parent build.'
versions={'parent':baseline}

def cache_values(text):
    return {line.split('=',1)[0].split(':',1)[0]:line.split('=',1)[1] for line in text.splitlines() if line and not line.startswith(('#','//')) and '=' in line}
baseline_cache=cache_values((W/'zset-source-reuse-previous-CMakeCache.txt').read_text())
temporary=W/'compiler-tmp-grouped-lookup';temporary.mkdir(exist_ok=True)
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
    prefix='grouped-lookup-'+label
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
    targets=['lavik_grouped_ordered_write_e2e_test','lavik_list_e2e_test','lavik_grouped_hash_write_e2e_test']
    run('build-tests',['cmake','--build','build-spdk','--target','lavik','lavik_unit_tests',*targets,'--parallel','4'])
    run('unit-tests',[str(B/'lavik_unit_tests'),'--gtest_filter=GroupedHashTest.*:HashGroupEdits.*:HashLookupMemoryTest.*:GroupedScratchBudgetTest.*:GroupedCollectionTest.*:StreamRecords.*:GroupedObjectIndexTest.*:GroupedMetadataArrayTest.*','--gtest_output=json:'+str(W/(prefix+'-unit-tests.json'))],timeout=600)
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
    version={'commit':head,'source_repo':str(S),'binary':str(binary),'sha256':sha(binary),'drivers':drivers,**native_dependency_provenance(B),'build':'Existing GCC native SPDK build-spdk cache; production tests/faults OFF, separate test drivers','full_fault_enabled_ci':proofs[label]['url'],'compiler_tmpdir':str(temporary)}
    (W/(prefix+'-CMakeCache.txt')).write_text(cache)
    (W/(prefix+'-build.json')).write_text(json.dumps(version,indent=2)+'\n')
    data=W/(prefix+'-test-data');data.mkdir();env=os.environ.copy();env['LAVIK_TEST_DATA_DIR']=str(data)
    for suite,target,filter_ in [('ordered-tests',targets[0],ordered_filter),('blocking-tests',targets[1],blocking_filter)]:
        run(suite,[drivers[target]['path'],str(binary),'--gtest_filter='+filter_,'--gtest_output=json:'+str(W/(prefix+'-'+suite+'.json'))],env,1800)
    run('hash-tests',[drivers[targets[2]]['path'],str(binary),'--gtest_output=json:'+str(W/(prefix+'-hash-tests.json'))],env,1800)
    assert sha(binary)==version['sha256']
    assert all(sha(v['path'])==v['sha256'] for v in drivers.values())
    version['tests']={name:json.loads((W/(prefix+'-'+name+'.json')).read_text()) for name in ['unit-tests','ordered-tests','blocking-tests','hash-tests']}
    assert all(x['failures']==0 and x['tests']>0 for x in version['tests'].values())
    compared_keys=['CMAKE_BUILD_TYPE','CMAKE_CXX_COMPILER','CMAKE_CXX_FLAGS','CMAKE_CXX_FLAGS_RELWITHDEBINFO','CMAKE_INTERPROCEDURAL_OPTIMIZATION','LAVIK_KERNEL_BYPASS','LAVIK_ENABLE_TEST_FAULTS','BUILD_TESTING']
    current_cache=cache_values(cache)
    assert all(current_cache.get(k)==baseline_cache.get(k) for k in compared_keys)
    assert version['bycorf_commit']==baseline['bycorf_commit']
    version['parent_build_options_compared']={k:current_cache.get(k) for k in compared_keys}
    versions[label]=version
    (W/'grouped-lookup-native-progress.json').write_text(json.dumps(versions,indent=2)+'\n')
output.write_text(json.dumps(versions,indent=2)+'\n')
print('ALL_GROUPED_LOOKUP_NATIVE_TESTS_PASS',time.time(),flush=True)
