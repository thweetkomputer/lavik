"""Wait for clean measurements, then validate the native production binary."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import time

W=Path(__file__).parent
S=Path('/mnt/dev/lavik-complex-next-20261004')
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
commit='1e87107e51d658944998ec74ff05b57d2e8f40c8'
ci=json.loads((W/'pr270-1e-ci.json').read_text())
assert ci['headSha']==commit and ci['conclusion']=='success'
shards=[j for j in ci['jobs'] if j['name'].startswith('Test shard (')]
assert len(shards)==12 and all(j['conclusion']=='success' for j in shards)
pid=537942
proc=Path(f'/proc/{pid}/stat')
identity=proc.read_text().split()[21]
print('WAIT_FOR_CLEAN_BASELINES_AND_IMPORTS',pid,time.time(),flush=True)
while proc.exists():
    try:
        if proc.read_text().split()[21]!=identity: break
    except FileNotFoundError: break
    time.sleep(15)
for name in ['current-main.json','current-imports.json']:
    data=json.loads((R/name).read_text())
    assert all(x['main']['fresh'] for x in data['plots']), f'incomplete {name}; no build started'
assert 'ALL_IMPORTS_COMPLETE' in (W/'continue-list64-and-baselines.log').read_text()
assert not (W/'pause-grid').exists()
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
print('BASELINES_AND_IMPORTS_COMPLETE_START_VALIDATION',time.time(),flush=True)
def run(name,argv):
    print('START',name,time.time(),flush=True)
    with (W/(name+'.txt')).open('w') as f:
        subprocess.run(argv,cwd=S,stdout=f,stderr=subprocess.STDOUT,check=True)
    print('PASS',name,time.time(),flush=True)
run('stream-reply-checkout',['git','switch','-c','perf/stream-reply-build-20261004',commit])
run('stream-reply-configure-tests',['cmake','-S','.', '-B','build-spdk','-DBUILD_TESTING=ON','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
run('stream-reply-build-tests',['cmake','--build','build-spdk','--target','lavik','lavik_grouped_ordered_write_e2e_test','lavik_list_e2e_test','lavik_pubsub_e2e_test','--parallel','4'])
run('stream-reply-configure-production',['cmake','-S','.', '-B','build-spdk','-DBUILD_TESTING=OFF','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
run('stream-reply-build-production',['cmake','--build','build-spdk','--target','lavik','--parallel','4'])
cache=(S/'build-spdk/CMakeCache.txt').read_text()
assert 'BUILD_TESTING:BOOL=OFF' in cache and 'LAVIK_ENABLE_TEST_FAULTS:BOOL=OFF' in cache
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==commit
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
server=Path('/mnt/dev/lavik-benchmark-binaries')/('lavik-stream-reply-'+commit[:8]+'-20261004')
assert not server.exists()
shutil.copyfile(S/'build-spdk/lavik',server)
server.chmod(0o755)
main=json.loads((W/'versions.json').read_text())['main']
candidate={**main,'commit':commit,'binary':str(server),'sha256':hashlib.sha256(server.read_bytes()).hexdigest(),'source_repo':str(S)}
(W/'stream-reply-versions.json').write_text(json.dumps({'main':main,'candidate':candidate},indent=2)+'\n')
(W/'stream-reply-CMakeCache.txt').write_text(cache.rstrip()+'\n')
run('stream-reply-perf-stream-tests',[str(S/'build-spdk/lavik_grouped_ordered_write_e2e_test'),str(server),'--gtest_filter=GroupedStreamE2e.*','--gtest_output=json:'+str(W/'stream-reply-perf-stream-tests.json')])
filters='ListE2eTest.BlockingAndStreamedCommandsDoNotHoldFlushDbGate:ListE2eTest.StreamBlockingRegistryBroadcastsAndKeepsGroupFifo:ListE2eTest.DisconnectCancelsActiveBlockingWait:ListE2eTest.PipelineFlushesRepliesBeforeBlockingCommand:CollectionE2eTest.SortedSetGeoAndStreamCommandsRecover'
run('stream-reply-list-tests',[str(S/'build-spdk/lavik_list_e2e_test'),str(server),'--gtest_filter='+filters,'--gtest_output=json:'+str(W/'stream-reply-list-tests.json')])
run('stream-reply-pubsub-tests',[str(S/'build-spdk/lavik_pubsub_e2e_test'),str(server)])
assert hashlib.sha256(server.read_bytes()).hexdigest()==candidate['sha256']
(W/'stream-reply-local-tests-passed.json').write_text(json.dumps({'candidate':candidate,'time':time.time(),'build_testing':False,'faults':False,'full_fault_enabled_ci':ci['url'],'ci_head':commit,'stream':'stream-reply-perf-stream-tests.json','list':'stream-reply-list-tests.json','pubsub':'stream-reply-pubsub-tests.txt','note':'Native production binary tested directly. Fault-only and opt-in skips are retained in JSON. Full fault-enabled CI passed all12shards on both architectures. Clean throughput and perf remain pending.'},indent=2)+'\n')
v=json.loads((W/'versions.json').read_text())
v['candidate']=candidate
(W/'versions.json').write_text(json.dumps(v,indent=2)+'\n')
print('ALL_STREAM_REPLY_NATIVE_PRODUCTION_TESTS_PASS',time.time(),flush=True)
