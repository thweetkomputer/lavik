"""Build and validate fixed Hash-route binaries on the serialized quiet host."""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,time
from host_execution_lock import acquire_host
from native_build_provenance import native_dependency_provenance
W=Path(__file__).parent
S=Path('/mnt/dev/lavik-complex-next-20261004');B=S/'build-spdk'
output=W/'hash-route-replace-versions.json'
assert not output.exists()
commit=subprocess.check_output(['git','rev-parse','perf/hash-route-replace-20261005'],cwd=S,text=True).strip()
expected={'candidate':commit}
proc=Path('/proc/716418/stat');identity=proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_STREAM_PROFILES',identity,time.time(),flush=True)
while identity is not None and proc.exists():
    try:
        if proc.read_text().split()[21]!=identity:break
    except FileNotFoundError:break
    time.sleep(15)
while True:
    pr=json.loads(subprocess.check_output(['gh','pr','view','276','--repo','eloqdata/lavik','--json','headRefOid']))
    assert pr['headRefOid']==commit,pr
    runs=json.loads(subprocess.check_output(['gh','run','list','--repo','eloqdata/lavik','--branch','perf/hash-route-replace-20261005','--limit','5','--json','headSha,databaseId,status,conclusion']))
    ci=next((r for r in runs if r['headSha']==commit),None)
    if ci and ci['status']=='completed':
        assert ci['conclusion']=='success',ci
        break
    print('WAIT_FOR_CI',ci,time.time(),flush=True);time.sleep(30)
proof=json.loads(subprocess.check_output(['gh','run','view',str(ci['databaseId']),'--repo','eloqdata/lavik','--json','headSha,conclusion,jobs,url']))
assert len(proof['jobs'])==17 and all(j['conclusion']=='success' for j in proof['jobs'])
(W/'hash-route-replace-full-ci.json').write_text(json.dumps(proof,indent=2)+'\n')
_execution_lock=acquire_host('hash-route-replace-native-validation')
def terminate(_signal,_frame):raise SystemExit('validation interrupted')
signal.signal(signal.SIGTERM,terminate)
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
versions=json.loads((W/'hash-route-replace-native-progress.json').read_text())
assert versions.keys()=={'parent'} and versions['parent']['commit']=='19496654cc43b21df11fb59be60e174dc4c89dbc'
assert all(v['failures']==0 and v['tests']>0 for v in versions['parent']['tests'].values())
temporary=W/'compiler-tmp-hash-route';temporary.mkdir(exist_ok=True)
assert shutil.disk_usage(temporary).free>10*1024**3
build_environment=dict(os.environ,TMPDIR=str(temporary))
for label,head in expected.items():
    prefix='hash-route-replace-'+label
    def run(name,argv,env=None):
        print('START',label,name,time.time(),flush=True)
        with (W/(prefix+'-'+name+'.txt')).open('w') as log:
            child=subprocess.Popen(argv,cwd=S,env=build_environment if env is None else dict(env,TMPDIR=str(temporary)),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                code=child.wait()
                if code:raise subprocess.CalledProcessError(code,argv)
            except BaseException:
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                child.wait();raise
        print('PASS',label,name,time.time(),flush=True)
    run('checkout',['git','switch','--detach',head])
    run('configure-tests',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=ON','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
    run('build-tests',['cmake','--build','build-spdk','--target','lavik','lavik_unit_tests','lavik_grouped_hash_write_e2e_test','--parallel','4'])
    run('unit-tests',[str(B/'lavik_unit_tests'),'--gtest_filter=GroupedHashTest.*:HashGroupMapTest.*:GroupedObjectIndexTest.*:GroupedMetadataArrayTest.*','--gtest_output=json:'+str(W/(prefix+'-unit-tests.json'))])
    driver=Path('/mnt/dev/lavik-benchmark-binaries')/(prefix+'-driver-'+head[:8]+'-20261005')
    assert not driver.exists();shutil.copyfile(B/'lavik_grouped_hash_write_e2e_test',driver);driver.chmod(0o755)
    run('configure-production',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=OFF','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
    run('build-production',['cmake','--build','build-spdk','--target','lavik','--parallel','4'])
    cache=(B/'CMakeCache.txt').read_text()
    assert 'BUILD_TESTING:BOOL=OFF' in cache and 'LAVIK_ENABLE_TEST_FAULTS:BOOL=OFF' in cache
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==head
    assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
    binary=Path('/mnt/dev/lavik-benchmark-binaries')/('lavik-'+prefix+'-'+head[:8]+'-20261005')
    assert not binary.exists();shutil.copyfile(B/'lavik',binary);binary.chmod(0o755)
    version={'commit':head,'source_repo':str(S),'binary':str(binary),'sha256':sha(binary),'driver':str(driver),'driver_sha256':sha(driver),**native_dependency_provenance(B),'build':'Existing GCC native SPDK build-spdk cache; production tests/faults OFF, separately built test drivers','candidate_ci':proof['url'],'compiler_tmpdir':str(temporary),'native_build_retry':'Original candidate LTO failed ENOSPC under /tmp; only TMPDIR moved to /mnt/dev. Original logs retained; source and compiler flags unchanged.'}
    (W/(prefix+'-CMakeCache.txt')).write_text(cache)
    (W/(prefix+'-build.json')).write_text(json.dumps(version,indent=2)+'\n')
    data=W/(prefix+'-test-data');data.mkdir();env=os.environ.copy();env['LAVIK_TEST_DATA_DIR']=str(data)
    run('native-tests',[str(driver),str(binary),'--gtest_output=json:'+str(W/(prefix+'-native-tests.json'))],env)
    assert sha(binary)==version['sha256'] and sha(driver)==version['driver_sha256']
    version['tests']={name:json.loads((W/(prefix+'-'+name+'.json')).read_text()) for name in ['unit-tests','native-tests']}
    assert all(x['failures']==0 and x['tests']>0 for x in version['tests'].values())
    versions[label]=version
    (W/'hash-route-replace-native-progress.json').write_text(json.dumps(versions,indent=2)+'\n')
output.write_text(json.dumps(versions,indent=2)+'\n')
print('ALL_HASH_ROUTE_REPLACE_NATIVE_TESTS_PASS',time.time(),flush=True)
