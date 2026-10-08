from pathlib import Path
import os,subprocess,sys,json,hashlib,shutil,time
sys.path.insert(0,'/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
from native_build_provenance import native_dependency_provenance
W=Path(__file__).parent;S=Path('/mnt/dev/lavik-complex-next-20261004');B=S/'build-spdk'
lock=acquire_host('pr291-qps-build-production-pair')
env=dict(os.environ,TMPDIR=str(W/'compiler-tmp'),LAVIK_TEST_DATA_DIR=str(W/'test-data'))
versions={}
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(name,cmd):
 print('START',name,time.time(),flush=True)
 with (W/(name+'.log')).open('w') as f:
  subprocess.run(cmd,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=2400)
 print('PASS',name,time.time(),flush=True)
for label,commit in [('main','1dd8a5b35aefc9215e0090204a0680efe9848e4a'),('pr291','74ba1d1ea3af697666b7eeaa06908dd4572eff95')]:
 assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
 run(label+'-checkout',['git','checkout','--detach',commit])
 run(label+'-configure-tests',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=ON','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
 run(label+'-build-tests',['cmake','--build','build-spdk','--target','lavik','lavik_unit_tests','lavik_grouped_ordered_write_e2e_test','lavik_grouped_hash_write_e2e_test','--parallel','4'])
 run(label+'-unit',[str(B/'lavik_unit_tests'),'--gtest_filter=*Group*:*Ordered*:*SortedRewrite*:*Hash*:*List*:*Memory*','--gtest_output=json:'+str(W/(label+'-unit.json'))])
 if label=='pr291':
  for kind,selection in [('ordered','GroupedOrderedWriteE2e.ListReusedPivotAndDeferredNeighboursRecover:GroupedOrderedWriteE2e.SortedSetPopReusesTiedPagesAndRecoversBothIndexes:GroupedOrderedWriteE2e.SortedSetPointUpdateOnlyRewritesNearbyPages:GroupedOrderedWriteE2e.ListEndSplitsWrapGrowAndRetireWithoutRewritingMiddle'),('hash','GroupedHashWriteE2e.*')]:
   run(label+'-'+kind,['sudo','-n','--preserve-env=TMPDIR,LAVIK_TEST_DATA_DIR','unshare','--mount','--propagation','private','python3',str(W/'private-tmp-exec.py'),str(W/'native-tmp'),str(os.getuid()),str(os.getgid()),str(B/('lavik_grouped_'+kind+'_write_e2e_test')),str(B/'lavik'),'--gtest_filter='+selection,'--gtest_output=json:'+str(W/(label+'-'+kind+'.json'))])
 run(label+'-configure-production',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=OFF','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
 run(label+'-build-production',['cmake','--build','build-spdk','--target','lavik','--parallel','4'])
 binary=Path('/mnt/dev/lavik-benchmark-binaries')/('lavik-pr291-qps-'+label+'-'+commit[:8]+'-20261008')
 assert not binary.exists();shutil.copy2(B/'lavik',binary)
 cache=(B/'CMakeCache.txt').read_text();assert 'BUILD_TESTING:BOOL=OFF' in cache and 'LAVIK_ENABLE_TEST_FAULTS:BOOL=OFF' in cache
 (W/(label+'-CMakeCache.txt')).write_text(cache)
 versions[label]={'commit':commit,'source_repo':str(S),'binary':str(binary),'sha256':sha(binary),**native_dependency_provenance(B)}
 (W/'versions.json').write_text(json.dumps(versions,indent=2)+'\n')
run('restore-branch',['git','checkout','bench/pr291-main-1dd8a5b3-20261008'])
assert (W/'main-CMakeCache.txt').read_bytes()==(W/'pr291-CMakeCache.txt').read_bytes()
print('PRODUCTION_PAIR_READY',time.time(),flush=True)
