"""Build and validate fixed ZSet score-view binaries on the serialized quiet host."""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,time
import sys
sys.path.insert(0,'/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
from native_build_provenance import native_dependency_provenance
W=Path(__file__).parent
S=Path('/mnt/dev/lavik-complex-next-20261004');B=S/'build-spdk'
output=W/'pr283-versions.json'
assert not output.exists()
expected={'parent': '5a3903d9b3c0632e3b34e827b779d9daa58455c2', 'candidate': 'ace4198b0e1080cbb5116d40817b4dcc38f7ff8c'}
proof=json.loads((W/'candidate-full-ci.json').read_text())
_execution_lock=acquire_host('pr283-native-validation')
def terminate(_signal,_frame):raise SystemExit('validation interrupted')
signal.signal(signal.SIGTERM,terminate)
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
versions={}
temporary=W/'compiler-tmp-pr283';temporary.mkdir(exist_ok=True)
assert shutil.disk_usage(temporary).free>10*1024**3
build_environment=dict(os.environ,TMPDIR=str(temporary))
for label,head in expected.items():
    prefix='pr283-'+label
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
    run('unit-tests',[str(B/'lavik_unit_tests'),'--gtest_filter=GroupedCollectionTest.*:GroupedHashTest.*:HashGroupEdits.*:HashLookupMemoryTest.*:GroupedObjectIndexTest.*:GroupedMetadataArrayTest.*','--gtest_output=json:'+str(W/(prefix+'-unit-tests.json'))])
    driver=Path('/mnt/dev/lavik-benchmark-binaries')/(prefix+'-driver-'+head[:8]+'-20261006')
    assert not driver.exists();shutil.copyfile(B/'lavik_grouped_ordered_write_e2e_test',driver);driver.chmod(0o755)
    run('configure-production',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=OFF','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
    run('build-production',['cmake','--build','build-spdk','--target','lavik','--parallel','4'])
    cache=(B/'CMakeCache.txt').read_text()
    assert 'BUILD_TESTING:BOOL=OFF' in cache and 'LAVIK_ENABLE_TEST_FAULTS:BOOL=OFF' in cache
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==head
    assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
    binary=Path('/mnt/dev/lavik-benchmark-binaries')/('lavik-'+prefix+'-'+head[:8]+'-20261006')
    assert not binary.exists();shutil.copyfile(B/'lavik',binary);binary.chmod(0o755)
    version={'commit':head,'source_repo':str(S),'binary':str(binary),'sha256':sha(binary),'driver':str(driver),'driver_sha256':sha(driver),**native_dependency_provenance(B),'build':'Existing GCC native SPDK build-spdk cache; production tests/faults OFF, separately built test drivers','ci':json.loads((W/(label+'-full-ci.json')).read_text()),'compiler_tmpdir':str(temporary)}
    (W/(prefix+'-CMakeCache.txt')).write_text(cache)
    (W/(prefix+'-build.json')).write_text(json.dumps(version,indent=2)+'\n')
    data=W/(prefix+'-test-data');data.mkdir();env=os.environ.copy();env['LAVIK_TEST_DATA_DIR']=str(data)
    run('native-tests',[str(driver),str(binary),'--gtest_filter=*','--gtest_output=json:'+str(W/(prefix+'-native-tests.json'))],env)
    assert sha(binary)==version['sha256'] and sha(driver)==version['driver_sha256']
    version['tests']={name:json.loads((W/(prefix+'-'+name+'.json')).read_text()) for name in ['unit-tests','native-tests']}
    assert all(x['failures']==0 and x['tests']>0 for x in version['tests'].values())
    versions[label]=version
    (W/'pr283-native-progress.json').write_text(json.dumps(versions,indent=2)+'\n')
output.write_text(json.dumps(versions,indent=2)+'\n')
print('ALL_PR283_NATIVE_TESTS_PASS',time.time(),flush=True)
