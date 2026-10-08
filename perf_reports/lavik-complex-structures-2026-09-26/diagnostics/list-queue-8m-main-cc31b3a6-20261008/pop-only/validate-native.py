from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
sys.path.insert(0,'/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
from native_build_provenance import native_dependency_provenance
W=Path(__file__).parent;S=Path('/mnt/dev/lavik-complex-next-20261004');B=S/'build-spdk'
lock=acquire_host('lpop-only-native-validation')
head='6d74a5fb0'
head=subprocess.check_output(['git','rev-parse',head],cwd=S,text=True).strip()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==head
assert not subprocess.check_output(['git','diff','HEAD','--'],cwd=S)
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(name,args):
 print('START',name,time.time(),flush=True)
 with (W/(name+'.log')).open('w') as log:subprocess.run(args,cwd=S,env=dict(os.environ,TMPDIR=str(W/'compiler-tmp-main')),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1800)
 print('PASS',name,time.time(),flush=True)
run('build-production',['cmake','--build','build-spdk','--target','lavik','--parallel','4'])
cache=(B/'CMakeCache.txt').read_text();assert 'BUILD_TESTING:BOOL=OFF' in cache and 'LAVIK_ENABLE_TEST_FAULTS:BOOL=OFF' in cache
assert cache==Path('/mnt/dev/lavik-rpush-lpop-20261008/refresh-queueopt-CMakeCache.txt').read_text()
(W/'CMakeCache.txt').write_text(cache)
binary=Path('/mnt/dev/lavik-benchmark-binaries')/('lavik-popopt-'+head[:8]+'-20261008');assert not binary.exists()
shutil.copyfile(B/'lavik',binary);binary.chmod(0o755)
prior=json.loads(Path('/mnt/dev/lavik-rpush-lpop-20261008/versions.json').read_text())['queueopt']
assert sha(prior['driver'])==prior['driver_sha256']
args=['sudo','-n','unshare','--mount','--propagation','private','python3',str(W/'private-tmp-exec.py'),str(W/'native-tmp'),str(os.getuid()),str(os.getgid()),prior['driver'],str(binary),'--gtest_filter=GroupedOrderedWriteE2e.*:GroupedListWriteE2e.*','--gtest_output=json:'+str(W/'native-tests.json')]
run('native-tests',args)
tests=json.loads((W/'native-tests.json').read_text());assert tests['failures']==0 and tests['tests']>0
v={'commit':head,'source_repo':str(S),'binary':str(binary),'sha256':sha(binary),'driver':prior['driver'],'driver_sha256':prior['driver_sha256'],**native_dependency_provenance(B),'tests':tests,'validation':'Runtime ordered/List integration suite rerun. Planner/containers source and tests identical to 309e2af3: reuse its 244 passing unit tests and broader validation, documented in prior-validation.json.'}
versions=json.loads((W/'versions.json').read_text());assert set(versions)=={'main'};versions['popopt']=v
(W/'versions.json').write_text(json.dumps(versions,indent=2)+'\n')
print('ALL_POPOPT_NATIVE_TESTS_PASS',flush=True)
