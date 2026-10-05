"""Validate ordinary grouped paths against fixed native parent and root-reuse binaries."""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,time
from host_execution_lock import acquire_host
from native_build_provenance import native_dependency_provenance
from grouped_root_ci_evidence import validate_ci
W=Path(__file__).parent;S=Path('/mnt/dev/lavik-complex-next-20261004');B=S/'build-spdk'
output=W/'grouped-root-native-versions.json';assert not output.exists()
head='28d7cca498655e02f46407adb65335219b10ee6b';parent_head='19496654cc43b21df11fb59be60e174dc4c89dbc'
frozen={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),W/'native_build_provenance.py',W/'host_execution_lock.py',W/'grouped_root_ci_evidence.py']}
# Keep the already scheduled combined comparison ahead of another build.
proc=Path('/proc/851635/stat');identity=proc.read_text().rsplit(')',1)[1].split()[19] if proc.exists() else None
print('WAIT_FOR_COMBINED_CONTROLS',identity,time.time(),flush=True)
while identity is not None and proc.exists():
 try:
  if proc.read_text().rsplit(')',1)[1].split()[19]!=identity:break
 except FileNotFoundError:break
 time.sleep(15)
proofs={}
for label,repo,run_id,expected in [('parent','eloqdata/lavik',37237724710,parent_head),('candidate','thweetkomputer/lavik',37258994628,head)]:
 proof=json.loads(subprocess.check_output(['gh','run','view',str(run_id),'--repo',repo,'--json','headSha,status,conclusion,jobs,url']))
 validate_ci(label,proof,expected)
 proofs[label]=proof;(W/f'grouped-root-{label}-full-ci.json').write_text(json.dumps(proof,indent=2)+'\n')
current_pr=json.loads(subprocess.check_output(['gh','pr','view','282','--repo','eloqdata/lavik','--json','headRefOid']))
(W/'grouped-root-pr-head-at-validation.json').write_text(json.dumps({'current_head':current_pr['headRefOid'],'tested_head':head,'note':'Frozen pre-rebase comparison, not validation of current PR head.'},indent=2)+'\n')
_execution_lock=acquire_host('grouped-root-native-validation')
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in frozen.items())
def terminate(_signal,_frame):raise SystemExit('validation interrupted')
signal.signal(signal.SIGTERM,terminate)
def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
parent=json.loads((W/'hash-route-replace-versions-corrected.json').read_text())['parent']
assert parent['commit']==parent_head and sha(parent['binary'])==parent['sha256']
assert parent['sha256']=='44695167697904ad6a210dd50e6fcdf3634f494fb633eb1267c5e9b568eed552'
assert all(t['failures']==0 and t.get('errors',0)==0 for t in parent['tests'].values())
temporary=W/'compiler-tmp-grouped-root';temporary.mkdir(exist_ok=True)
assert shutil.disk_usage(temporary).free>10*1024**3
environment=dict(os.environ,TMPDIR=str(temporary))
def run(label,name,argv,env=None,timeout=None):
 print('START',label,name,time.time(),flush=True)
 with (W/f'grouped-root-{label}-{name}.txt').open('w') as log:
  child=subprocess.Popen(argv,cwd=S,env=environment if env is None else dict(env,TMPDIR=str(temporary)),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   code=child.wait(timeout=timeout)
   if code:raise subprocess.CalledProcessError(code,argv)
  except BaseException:
   try:os.killpg(child.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   child.wait();raise
 print('PASS',label,name,time.time(),flush=True)
run('candidate','checkout',['git','switch','--detach',head])
run('candidate','configure-tests',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=ON','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
targets=['lavik_grouped_ordered_write_e2e_test','lavik_grouped_hash_write_e2e_test','lavik_list_e2e_test']
run('candidate','build-tests',['cmake','--build','build-spdk','--target','lavik','lavik_unit_tests',*targets,'--parallel','4'])
run('candidate','unit-tests',[str(B/'lavik_unit_tests'),'--gtest_filter=GroupedHashTest.*:HashGroupEdits.*:HashLookupMemoryTest.*:GroupedScratchBudgetTest.*:GroupedCollectionTest.*:StreamRecords.*:GroupedObjectIndexTest.*:GroupedMetadataArrayTest.*','--gtest_output=json:'+str(W/'grouped-root-candidate-unit-tests.json')],timeout=600)
drivers={}
for target in targets:
 path=Path('/mnt/dev/lavik-benchmark-binaries')/f'grouped-root-{target}-{head[:8]}-20261005'
 assert not path.exists();shutil.copyfile(B/target,path);path.chmod(0o755)
 drivers[target]={'path':str(path),'sha256':sha(path)}
run('candidate','configure-production',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=OFF','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
run('candidate','build-production',['cmake','--build','build-spdk','--target','lavik','--parallel','4'])
cache=(B/'CMakeCache.txt').read_text();(W/'grouped-root-candidate-CMakeCache.txt').write_text(cache)
def options(text):return {l.split('=',1)[0].split(':',1)[0]:l.split('=',1)[1] for l in text.splitlines() if l and not l.startswith(('#','//')) and '=' in l}
keys=['CMAKE_BUILD_TYPE','CMAKE_CXX_COMPILER','CMAKE_CXX_FLAGS','CMAKE_CXX_FLAGS_RELWITHDEBINFO','CMAKE_INTERPROCEDURAL_OPTIMIZATION','LAVIK_KERNEL_BYPASS','LAVIK_ENABLE_TEST_FAULTS','BUILD_TESTING','LAVIK_MARCH']
current=options(cache);reference=options((W/'hash-route-replace-parent-CMakeCache.txt').read_text())
assert all(current.get(k)==reference.get(k) for k in keys)
assert current['BUILD_TESTING']==current['LAVIK_ENABLE_TEST_FAULTS']=='OFF' and current['LAVIK_MARCH']=='native'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==head
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
binary=Path('/mnt/dev/lavik-benchmark-binaries')/f'lavik-grouped-root-candidate-{head[:8]}-20261005'
assert not binary.exists();shutil.copyfile(B/'lavik',binary);binary.chmod(0o755)
candidate={'commit':head,'source_repo':str(S),'binary':str(binary),'sha256':sha(binary),**native_dependency_provenance(B),'compiler_tmpdir':str(temporary),'build':'GCC native SPDK; production tests/faults OFF, separately frozen test drivers'}
assert candidate['bycorf_commit']==parent['bycorf_commit']=='62509c93d40c2480f5046b71454db6cf95801b04'
(W/'grouped-root-candidate-build.json').write_text(json.dumps(candidate,indent=2)+'\n')
ordered=('GroupedStringWriteE2e.FixedSegmentsPointWritesTtlAndRecovery:'
 'GroupedOrderedWriteE2e.List*:GroupedOrderedWriteE2e.LargeListItemUsesExtentsWithoutRewritingAllPages:'
 'GroupedSortedSetWriteE2e.*:GroupedOrderedWriteE2e.SortedSet*:'
 'GroupedOrderedWriteE2e.LargeSortedSetMemberUsesExtents:GroupedDemotionE2e.*:'
 'GroupedStreamE2e.*:GroupedTransferE2e.*:'
 'GroupedRdbStreamE2e.FourTypesMultiPageLargeItemsAndMultipleWorkers:'
 'GroupedRdbStreamE2e.RestoreStreamsFourTypesInsideAndOutsideExec:'
 'GroupedRdbStreamE2e.BackupStreamsFourTypesThenImportsAndRestarts')
blocking=('ListE2eTest.BlockingAndStreamedCommandsDoNotHoldFlushDbGate:'
 'ListE2eTest.StreamBlockingRegistryBroadcastsAndKeepsGroupFifo:'
 'ListE2eTest.DisconnectCancelsActiveBlockingWait:'
 'ListE2eTest.PipelineFlushesRepliesBeforeBlockingCommand:'
 'CollectionE2eTest.SortedSetGeoAndStreamCommandsRecover')
versions={}
for label,version in [('parent',parent),('candidate',candidate)]:
 data=W/f'grouped-root-{label}-test-data';data.mkdir();env=dict(os.environ,LAVIK_TEST_DATA_DIR=str(data))
 tests={}
 for name,target,filter_ in [('hash-tests',targets[1],'*'),('ordered-tests',targets[0],ordered),('blocking-tests',targets[2],blocking)]:
  result=W/f'grouped-root-{label}-{name}.json'
  run(label,name,[drivers[target]['path'],version['binary'],'--gtest_filter='+filter_,'--gtest_output=json:'+str(result)],env,1800)
  tests[name]=json.loads(result.read_text());assert tests[name]['tests']>0 and tests[name]['failures']==tests[name].get('errors',0)==0
 if label=='candidate':tests['unit-tests']=json.loads((W/'grouped-root-candidate-unit-tests.json').read_text())
 assert sha(version['binary'])==version['sha256'] and all(sha(v['path'])==v['sha256'] for v in drivers.values())
 version=dict(version,ordinary_tests=tests,ordinary_test_drivers=drivers,comparison_build_options={k:current.get(k) for k in keys},full_fault_enabled_ci=proofs[label]['url'],full_ci_conclusion=proofs[label]['conclusion'],full_ci_limitation=proofs[label].get('reviewed_limitation'),validation_scripts_sha256=frozen)
 versions[label]=version;(W/'grouped-root-native-progress.json').write_text(json.dumps(versions,indent=2)+'\n')
output.write_text(json.dumps(versions,indent=2)+'\n')
print('ALL_GROUPED_ROOT_NATIVE_TESTS_PASS',time.time(),flush=True)
