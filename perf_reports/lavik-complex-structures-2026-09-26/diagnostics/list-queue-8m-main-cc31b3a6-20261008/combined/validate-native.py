"""Build and validate latest main binary on the serialized quiet host."""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,time
import sys
sys.path.insert(0,'/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
from native_build_provenance import native_dependency_provenance
W=Path(__file__).parent
S=Path('/mnt/dev/lavik-complex-next-20261004');B=S/'build-spdk'
output=W/'versions.json'
resume='--resume-built' in sys.argv
assert set(json.loads(output.read_text())) == {'main'}
expected={'queueopt': '309e2af3762e8c51b8a285892f3b9a66e07f65a3'}
_execution_lock=acquire_host('pr289-c8f128dc-native-validation')
def terminate(_signal,_frame):raise SystemExit('validation interrupted')
signal.signal(signal.SIGTERM,terminate)
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
versions=json.loads(output.read_text())
assert sha(versions['main']['binary'])==versions['main']['sha256']
temporary=W/'compiler-tmp-main';temporary.mkdir(exist_ok=True)
assert shutil.disk_usage(temporary).free>10*1024**3
build_environment=dict(os.environ,TMPDIR=str(temporary))
for label,head in expected.items():
    prefix='refresh-'+label
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
    if not resume:
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==head
        run('configure-tests',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=ON','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
        run('build-tests',['cmake','--build','build-spdk','--target','lavik','lavik_unit_tests','lavik_grouped_ordered_write_e2e_test','lavik_grouped_hash_write_e2e_test','--parallel','4'])
        run('unit-tests',[str(B/'lavik_unit_tests'),'--gtest_filter=*Group*:*CowMap*:*FenwickTree*:*Ordered*:*SortedRewrite*:*StreamDirectory*:*StreamPageMaxKey*:*StreamRecord*:HashLookupMemoryTest.*:CowArrayTest.*:CowArrayDeathTest.*:ListRingTest.*:*LocalSharedPtr*','--gtest_output=json:'+str(W/(prefix+'-unit-tests.json'))])
        driver=Path('/mnt/dev/lavik-benchmark-binaries')/(prefix+'-driver-'+head[:8]+'-20261008')
        assert not driver.exists();shutil.copyfile(B/'lavik_grouped_ordered_write_e2e_test',driver);driver.chmod(0o755)
        hash_driver=driver.with_name(driver.name+'-hash')
        assert not hash_driver.exists();shutil.copyfile(B/'lavik_grouped_hash_write_e2e_test',hash_driver);hash_driver.chmod(0o755)
        run('configure-production',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=OFF','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
        run('build-production',['cmake','--build','build-spdk','--target','lavik','--parallel','4'])
        cache=(B/'CMakeCache.txt').read_text()
        assert 'BUILD_TESTING:BOOL=OFF' in cache and 'LAVIK_ENABLE_TEST_FAULTS:BOOL=OFF' in cache
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==head
        assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
        binary=Path('/mnt/dev/lavik-benchmark-binaries')/('lavik-'+prefix+'-'+head[:8]+'-20261008')
        assert not binary.exists();shutil.copyfile(B/'lavik',binary);binary.chmod(0o755)
        version={'commit':head,'source_repo':str(S),'binary':str(binary),'sha256':sha(binary),'driver':str(driver),'driver_sha256':sha(driver),**native_dependency_provenance(B),'build':'Existing GCC native SPDK build-spdk cache; production tests/faults OFF, separately built test drivers','compiler_tmpdir':str(temporary)}
        (W/(prefix+'-CMakeCache.txt')).write_text(cache)
        (W/(prefix+'-build.json')).write_text(json.dumps(version,indent=2)+'\n')
    else:
        version=json.loads((W/(prefix+'-build.json')).read_text())
        binary=Path(version['binary']);driver=Path(version['driver']);hash_driver=driver.with_name(driver.name+'-hash')
        assert version['commit']==head and sha(binary)==version['sha256'] and sha(driver)==version['driver_sha256']
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==head
        assert json.loads((W/(prefix+'-unit-tests.json')).read_text())['failures']==0
    data=W/(prefix+'-test-data');data.mkdir(exist_ok=True);env=os.environ.copy();env['LAVIK_TEST_DATA_DIR']=str(data)
    run('native-tests-private-tmp',['sudo','-n','--preserve-env=TMPDIR,LAVIK_TEST_DATA_DIR','unshare','--mount','--propagation','private','python3',str(W/'private-tmp-exec.py'),str(W/'native-tmp'),str(os.getuid()),str(os.getgid()),str(driver),str(binary),'--gtest_filter=*','--gtest_output=json:'+str(W/(prefix+'-native-tests-private-tmp.json'))],env)
    run('hash-native-tests-private-tmp',['sudo','-n','--preserve-env=TMPDIR,LAVIK_TEST_DATA_DIR','unshare','--mount','--propagation','private','python3',str(W/'private-tmp-exec.py'),str(W/'native-tmp'),str(os.getuid()),str(os.getgid()),str(hash_driver),str(binary),'--gtest_filter=*','--gtest_output=json:'+str(W/(prefix+'-hash-native-tests-private-tmp.json'))],env)
    version.update(hash_driver=str(hash_driver),hash_driver_sha256=sha(hash_driver))
    assert sha(binary)==version['sha256'] and sha(driver)==version['driver_sha256']
    version['tests']={name:json.loads((W/(prefix+'-'+name+'.json')).read_text()) for name in ['unit-tests','native-tests-private-tmp','hash-native-tests-private-tmp']}
    assert all(x['failures']==0 and x['tests']>0 for x in version['tests'].values())
    version['validation_environment']={'tmp_namespace':str(W/'native-tmp'),'reason':'std::tmpfile uses /tmp, whose host filesystem had only 833MiB free; isolated bind gives the existing data volume capacity. Host /tmp remains unchanged.'}
    versions[label]=version
    (W/'native-progress.json').write_text(json.dumps(versions,indent=2)+'\n')
output.write_text(json.dumps(versions,indent=2)+'\n')
print('ALL_QUEUEOPT_NATIVE_TESTS_PASS',time.time(),flush=True)
