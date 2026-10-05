"""Build and validate fixed ZSet score-view binaries on the serialized quiet host."""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,time
from host_execution_lock import acquire_host
from native_build_provenance import native_dependency_provenance
W=Path(__file__).parent
S=Path('/mnt/dev/lavik-complex-next-20261004');B=S/'build-spdk'
output=W/'zset-score-views-versions.json'
assert not output.exists()
expected={'parent':'4610d6077e8e32d59639a5ee88dbe8cbd305aab2','candidate':'9d1ffc8572f558cc139b1801488d014c2099dbfd'}
waiters=[]
for pid in [761025,761017,782817,761040,761046,761061]:
    proc=Path('/proc')/str(pid)/'stat'
    waiters.append((pid,proc,proc.read_text().split()[21] if proc.exists() else None))
for pid,proc,identity in waiters:
    print('WAIT_FOR_PRIOR_WORK',pid,identity,time.time(),flush=True)
    while identity is not None and proc.exists():
        try:
            if proc.read_text().split()[21]!=identity:break
        except FileNotFoundError:break
        time.sleep(15)
proof=json.loads(subprocess.check_output(['gh','run','view','37272089111','--repo','thweetkomputer/lavik','--json','headSha,conclusion,jobs,url']))
assert proof['headSha']==expected['candidate'] and proof['conclusion']=='success'
assert len(proof['jobs'])==17 and all(j['conclusion']=='success' for j in proof['jobs'])
(W/'zset-score-views-full-ci.json').write_text(json.dumps(proof,indent=2)+'\n')
_execution_lock=acquire_host('zset-score-views-native-validation')
def terminate(_signal,_frame):raise SystemExit('validation interrupted')
signal.signal(signal.SIGTERM,terminate)
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
versions={}
temporary=W/'compiler-tmp-zset-score-views';temporary.mkdir(exist_ok=True)
assert shutil.disk_usage(temporary).free>10*1024**3
build_environment=dict(os.environ,TMPDIR=str(temporary))
for label,head in expected.items():
    prefix='zset-score-views-'+label
    def run(name,argv,env=None,timeout=1800):
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
    run('build-tests',['cmake','--build','build-spdk','--target','lavik','lavik_unit_tests','lavik_grouped_ordered_write_e2e_test','--parallel','4'])
    run('unit-tests',[str(B/'lavik_unit_tests'),'--gtest_filter=GroupedHashTest.*:HashGroupEdits.*:HashLookupMemoryTest.*:GroupedObjectIndexTest.*:GroupedMetadataArrayTest.*','--gtest_output=json:'+str(W/(prefix+'-unit-tests.json'))])
    driver=Path('/mnt/dev/lavik-benchmark-binaries')/(prefix+'-driver-'+head[:8]+'-20261005')
    assert not driver.exists();shutil.copyfile(B/'lavik_grouped_ordered_write_e2e_test',driver);driver.chmod(0o755)
    run('configure-production',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=OFF','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
    run('build-production',['cmake','--build','build-spdk','--target','lavik','--parallel','4'])
    cache=(B/'CMakeCache.txt').read_text()
    assert 'BUILD_TESTING:BOOL=OFF' in cache and 'LAVIK_ENABLE_TEST_FAULTS:BOOL=OFF' in cache
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==head
    assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
    binary=Path('/mnt/dev/lavik-benchmark-binaries')/('lavik-'+prefix+'-'+head[:8]+'-20261005')
    assert not binary.exists();shutil.copyfile(B/'lavik',binary);binary.chmod(0o755)
    version={'commit':head,'source_repo':str(S),'binary':str(binary),'sha256':sha(binary),'driver':str(driver),'driver_sha256':sha(driver),**native_dependency_provenance(B),'build':'Existing GCC native SPDK build-spdk cache; production tests/faults OFF, separately built test drivers','candidate_ci':proof['url'],'compiler_tmpdir':str(temporary)}
    (W/(prefix+'-CMakeCache.txt')).write_text(cache)
    (W/(prefix+'-build.json')).write_text(json.dumps(version,indent=2)+'\n')
    data=W/(prefix+'-test-data');data.mkdir();env=os.environ.copy();env['LAVIK_TEST_DATA_DIR']=str(data)
    run('native-tests',[str(driver),str(binary),'--gtest_filter=GroupedSortedSetWriteE2e.*:GroupedOrderedWriteE2e.SortedSet*:GroupedOrderedWriteE2e.LargeSortedSetMemberUsesExtents:GroupedDemotionE2e.*:GroupedTransferE2e.*:GroupedRdbStreamE2e.FourTypesMultiPageLargeItemsAndMultipleWorkers:GroupedRdbStreamE2e.RestoreStreamsFourTypesInsideAndOutsideExec:GroupedRdbStreamE2e.BackupStreamsFourTypesThenImportsAndRestarts','--gtest_output=json:'+str(W/(prefix+'-native-tests.json'))],env)
    assert sha(binary)==version['sha256'] and sha(driver)==version['driver_sha256']
    version['tests']={name:json.loads((W/(prefix+'-'+name+'.json')).read_text()) for name in ['unit-tests','native-tests']}
    assert all(x['failures']==0 and x['tests']>0 for x in version['tests'].values())
    versions[label]=version
    (W/'zset-score-views-native-progress.json').write_text(json.dumps(versions,indent=2)+'\n')
output.write_text(json.dumps(versions,indent=2)+'\n')
print('ALL_ZSET_SCORE_VIEWS_NATIVE_TESTS_PASS',time.time(),flush=True)
