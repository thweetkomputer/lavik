"""Reproduce the exact COUNT fault, then validate the upper-bound correction."""
from pathlib import Path
import json
import os
import subprocess
import time
from host_execution_lock import acquire_host
W = Path(__file__).parent
S = Path('/mnt/dev/lavik-complex-next-20261004')
B = S / 'build-spdk'
output = W / 'stream-window-boundary-validation.json'
assert not output.exists()
proc = Path('/proc/640828/stat')
identity = proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_STREAM_NATIVE', identity, time.time(), flush=True)
while identity is not None and proc.exists():
    try:
        if proc.read_text().split()[21] != identity: break
    except FileNotFoundError: break
    time.sleep(15)
assert 'ALL_STREAM_FOLLOWUP_NATIVE_TESTS_PASS' in (W / 'stream-followup-native-resume-driver.log').read_text()
_execution_lock = acquire_host('stream-window-boundary-fault-reproduction')
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S) == b''
data = W / 'stream-window-boundary-fault-data'
data.mkdir(exist_ok=True)
os.environ['LAVIK_TEST_DATA_DIR'] = str(data)
old = 'ac62975fdf1f9dda1783429d523969b737efc98f'
fixed = '5b9ebdedecc0cc7a3fea93fb73b1fbbb6b7186c6'
def run(label, args, expected=0):
    print('START', label, time.time(), flush=True)
    with (W / ('stream-window-boundary-' + label + '.txt')).open('w') as log:
        result = subprocess.run(args, cwd=S, stdout=log, stderr=subprocess.STDOUT)
    assert result.returncode == expected, (label, result.returncode, expected)
    print('EXPECTED_EXIT', label, expected, time.time(), flush=True)
for label, commit in [('original',old),('fixed',fixed)]:
    run(label+'-checkout',['git','switch','--detach',commit])
    run(label+'-configure',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=ON','-DLAVIK_ENABLE_TEST_FAULTS=ON'])
    run(label+'-build',['cmake','--build','build-spdk','--target','lavik','lavik_grouped_ordered_write_e2e_test','--parallel','4'])
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==commit
    assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
    result_path = W / ('stream-window-boundary-' + label + '-tests.json')
    filters = 'GroupedStreamE2e.ReadWindowsRespectCountAndJoinFailedStarts'
    if label == 'fixed':
        filters = ('GroupedStreamE2e.*:GroupedTransferE2e.*:'
                   'GroupedRdbStreamE2e.FourTypesMultiPageLargeItemsAndMultipleWorkers:'
                   'GroupedRdbStreamE2e.RestoreStreamsFourTypesInsideAndOutsideExec:'
                   'GroupedRdbStreamE2e.BackupStreamsFourTypesThenImportsAndRestarts')
    run(label+'-tests',[str(B/'lavik_grouped_ordered_write_e2e_test'),str(B/'lavik'),
         '--gtest_filter='+filters,'--gtest_output=json:'+str(result_path)],expected=1 if label=='original' else 0)
    result=json.loads(result_path.read_text())
    if label=='original':
        assert result['tests']==1 and result['failures']==1
        assert 'XREVRANGE: connection closed before response completed' in (W/'stream-window-boundary-original-tests.txt').read_text()
    else:
        assert result['tests'] >= 26 and result['failures']==0
    proof=json.loads(output.read_text()) if output.exists() else {}
    proof[label]={'commit':commit,'tests':result,'fault_enabled':True,'build':'GCC13 native LTO SPDK; correctness only, never a performance binary','data_directory':str(data)}
    output.write_text(json.dumps(proof,indent=2)+'\n')
print('STREAM_WINDOW_BOUNDARY_FAULT_REPRODUCED_AND_FIXED', time.time(), flush=True)
