"""Reproduce the exact planner fault fixture, then validate pre-start fault configuration."""
from pathlib import Path
import json
import hashlib
import os
import subprocess
import time
from host_execution_lock import acquire_host
W = Path(__file__).parent
S = Path('/mnt/dev/lavik-complex-next-20261004')
B = S / 'build-spdk'
output = W / 'zset-planner-fault-validation.json'
assert not output.exists()
proc = Path('/proc/673760/stat')
identity = proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_CORRECTED_STREAM_PRODUCTION', identity, time.time(), flush=True)
while identity is not None and proc.exists():
    try:
        if proc.read_text().split()[21] != identity: break
    except FileNotFoundError: break
    time.sleep(15)
assert 'ALL_CORRECTED_STREAM_PRODUCTION_TESTS_PASS' in (W / 'stream-window-corrected-production-driver.log').read_text()
_execution_lock = acquire_host('zset-planner-fault-fault-reproduction')
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S) == b''
data = W / 'zset-planner-fault-fault-data'
data.mkdir(exist_ok=True)
os.environ['LAVIK_TEST_DATA_DIR'] = str(data)
old = 'd012a3013da99344a419bb692f834b17fd6dcad4'
fixed = '92906489799d5d65c8315cc87371a14f6b2e384e'
def run(label, args, expected=0):
    print('START', label, time.time(), flush=True)
    with (W / ('zset-planner-fault-' + label + '.txt')).open('w') as log:
        result = subprocess.run(args, cwd=S, stdout=log, stderr=subprocess.STDOUT)
    assert result.returncode == expected, (label, result.returncode, expected)
    print('EXPECTED_EXIT', label, expected, time.time(), flush=True)
for label, commit in [('original',old),('fixed',fixed)]:
    run(label+'-checkout',['git','switch','--detach',commit])
    run(label+'-configure',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=ON','-DLAVIK_ENABLE_TEST_FAULTS=ON'])
    run(label+'-build',['cmake','--build','build-spdk','--target','lavik','lavik_grouped_ordered_write_e2e_test','--parallel','4'])
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==commit
    assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
    result_path = W / ('zset-planner-fault-' + label + '-tests.json')
    filters = 'GroupedSortedSetWriteE2e.PointWritesReuseMemberLeafAndKeepBatchFailureAtomic'
    if label == 'fixed':
        filters = ('GroupedSortedSetWriteE2e.*:GroupedOrderedWriteE2e.SortedSet*:'
                   'GroupedOrderedWriteE2e.LargeSortedSetMemberUsesExtents:GroupedDemotionE2e.*')
    run(label+'-tests',[str(B/'lavik_grouped_ordered_write_e2e_test'),str(B/'lavik'),
         '--gtest_filter='+filters,'--gtest_output=json:'+str(result_path)],expected=1 if label=='original' else 0)
    result=json.loads(result_path.read_text())
    if label=='original':
        assert result['tests']==1 and result['failures']==1
        assert 'plan page read failure' in (W/'zset-planner-fault-original-tests.txt').read_text()
    else:
        assert result['tests'] >= 27 and result['failures']==0
    proof=json.loads(output.read_text()) if output.exists() else {}
    proof[label]={'commit':commit,'tests':result,'fault_enabled':True,'build':'GCC13 native LTO SPDK; correctness only, never a performance binary','data_directory':str(data),'server_sha256':hashlib.sha256((B/'lavik').read_bytes()).hexdigest()}
    output.write_text(json.dumps(proof,indent=2)+'\n')
assert proof['original']['server_sha256'] == proof['fixed']['server_sha256']
assert subprocess.check_output(['git','diff','--name-only',old,fixed],cwd=S,text=True).splitlines() == ['tests/grouped/zset_write_e2e_test.cpp']
print('ZSET_PLANNER_FAULT_REPRODUCED_AND_FIXED', time.time(), flush=True)
