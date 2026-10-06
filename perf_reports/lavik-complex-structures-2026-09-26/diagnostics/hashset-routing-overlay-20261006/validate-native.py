from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,time,sys
sys.path.insert(0,'/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
from native_build_provenance import native_dependency_provenance
W=Path(__file__).parent;S=Path('/mnt/dev/lavik-complex-next-20261004');B=S/'build-spdk'
head=sys.argv[1];lock=acquire_host('hashset-routing-overlay-native')
def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
T=W/'compiler-tmp';T.mkdir(exist_ok=True);(W/'native-tmp').mkdir(exist_ok=True)
env=dict(os.environ,TMPDIR=str(T));prefix='candidate-'+head[:8]
def run(name,args,custom=None,timeout=2400):
 print('START',name,time.time(),flush=True)
 with (W/(prefix+'-'+name+'.log')).open('w') as f:
  child=subprocess.Popen(args,cwd=S,env=custom or env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   code=child.wait(timeout=timeout)
   if code:raise subprocess.CalledProcessError(code,args)
  except BaseException:
   os.killpg(child.pid,signal.SIGKILL);child.wait();raise
 print('PASS',name,time.time(),flush=True)
assert not subprocess.check_output(['git','diff','HEAD','--'],cwd=S)
run('checkout',['git','switch','--detach',head])
run('configure-tests',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=ON','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
run('build-tests',['cmake','--build','build-spdk','--target','lavik','lavik_unit_tests','lavik_grouped_hash_write_e2e_test','lavik_grouped_ordered_write_e2e_test','--parallel','4'])
run('unit-tests',[str(B/'lavik_unit_tests'),'--gtest_filter=GroupedCollectionTest.*:GroupedHashTest.*:HashGroupEdits.*:HashGroupMapTest.*:HashLookupMemoryTest.*:GroupedObjectIndexTest.*:GroupedMetadataArrayTest.*','--gtest_output=json:'+str(W/(prefix+'-unit-tests.json'))])
drivers={}
for kind in ['hash','ordered']:
 target=W/(prefix+'-'+kind+'-driver');shutil.copyfile(B/('lavik_grouped_'+kind+'_write_e2e_test'),target);target.chmod(0o755);drivers[kind]={'path':str(target),'sha256':sha(target),'source_commit':head}
run('configure-production',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=OFF','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
run('build-production',['cmake','--build','build-spdk','--target','lavik','--parallel','4'])
cache=(B/'CMakeCache.txt').read_text();assert 'BUILD_TESTING:BOOL=OFF' in cache and 'LAVIK_ENABLE_TEST_FAULTS:BOOL=OFF' in cache
binary=Path('/mnt/dev/lavik-benchmark-binaries')/('lavik-hashset-overlay-'+head[:8]+'-20261006');assert not binary.exists();shutil.copyfile(B/'lavik',binary);binary.chmod(0o755)
v={'commit':head,'source_repo':str(S),'binary':str(binary),'sha256':sha(binary),**native_dependency_provenance(B),'build':'GCC native SPDK build-spdk; production tests/faults OFF; same cache/toolchain as main5a','drivers':drivers}
(W/(prefix+'-build.json')).write_text(json.dumps(v,indent=2));(W/(prefix+'-CMakeCache.txt')).write_text(cache)
versions={'parent':json.loads((W/'parent.json').read_text()),'candidate':v}
for label,version in versions.items():
 version['hashset_native_tests']={}
 for kind in (['hash'] if label=='parent' else ['hash','ordered']):
  name=label+'-'+kind+'-native';data=W/(name+'-data');data.mkdir(exist_ok=True);custom=dict(env,LAVIK_TEST_DATA_DIR=str(data))
  run(name,['sudo','-n','--preserve-env=TMPDIR,LAVIK_TEST_DATA_DIR','unshare','--mount','--propagation','private','python3',str(W/'private-tmp-exec.py'),str(W/'native-tmp'),str(os.getuid()),str(os.getgid()),drivers[kind]['path'],version['binary'],'--gtest_filter=*','--gtest_output=json:'+str(W/(prefix+'-'+name+'.json'))],custom)
  result=json.loads((W/(prefix+'-'+name+'.json')).read_text());assert result['failures']==0 and result['tests']>0
  version['hashset_native_tests'][kind]=result
 assert sha(version['binary'])==version['sha256']
(W/'validated-versions.json').write_text(json.dumps(versions,indent=2))
print('ALL_HASHSET_OVERLAY_NATIVE_TESTS_PASS',time.time(),flush=True)
