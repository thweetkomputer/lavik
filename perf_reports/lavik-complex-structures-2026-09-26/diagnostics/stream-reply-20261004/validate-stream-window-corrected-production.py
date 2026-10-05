"""Freeze the corrected production binary only after fault reproduction passes."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import time
from host_execution_lock import acquire_host
W = Path(__file__).parent
S = Path('/mnt/dev/lavik-complex-next-20261004')
B = S / 'build-spdk'
output = W / 'stream-followup-corrected-versions.json'
assert not output.exists()
proc = Path('/proc/660324/stat')
identity = proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_WINDOW_FAULT_VALIDATION', identity, time.time(), flush=True)
while identity is not None and proc.exists():
    try:
        if proc.read_text().split()[21] != identity: break
    except FileNotFoundError: break
    time.sleep(15)
assert 'STREAM_WINDOW_BOUNDARY_FAULT_REPRODUCED_AND_FIXED' in (W / 'stream-window-boundary-validation-driver.log').read_text()
proof = json.loads((W / 'stream-window-boundary-validation.json').read_text())
commit = '5b9ebdedecc0cc7a3fea93fb73b1fbbb6b7186c6'
assert proof['fixed']['commit'] == commit and proof['fixed']['tests']['failures'] == 0
_execution_lock = acquire_host('stream-window-corrected-production')
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S) == b''
prefix = 'stream-window-boundary-fixed-production'
def run(name, args):
    print('START', name, time.time(), flush=True)
    with (W / f'{prefix}-{name}.txt').open('w') as log:
        subprocess.run(args, cwd=S, stdout=log, stderr=subprocess.STDOUT, check=True)
    print('PASS', name, time.time(), flush=True)
run('checkout',['git','switch','--detach',commit])
run('configure-tests',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=ON','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
run('build-tests',['cmake','--build','build-spdk','--target','lavik','lavik_grouped_ordered_write_e2e_test','lavik_list_e2e_test','lavik_pubsub_e2e_test','--parallel','4'])
run('configure-production',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=OFF','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
run('build-production',['cmake','--build','build-spdk','--target','lavik','--parallel','4'])
cache = (B/'CMakeCache.txt').read_text()
assert 'BUILD_TESTING:BOOL=OFF' in cache and 'LAVIK_ENABLE_TEST_FAULTS:BOOL=OFF' in cache
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==commit
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
binary = Path('/mnt/dev/lavik-benchmark-binaries/lavik-stream-followup-window-5b9ebded-20261005')
assert not binary.exists()
shutil.copyfile(B/'lavik',binary);binary.chmod(0o755)
sha = hashlib.sha256(binary.read_bytes()).hexdigest()
(W/f'{prefix}-CMakeCache.txt').write_text(cache)
data = W/'stream-window-boundary-production-data';data.mkdir(exist_ok=True)
os.environ['LAVIK_TEST_DATA_DIR']=str(data)
filters = ('GroupedStreamE2e.*:GroupedTransferE2e.*:'
           'GroupedRdbStreamE2e.FourTypesMultiPageLargeItemsAndMultipleWorkers:'
           'GroupedRdbStreamE2e.RestoreStreamsFourTypesInsideAndOutsideExec:'
           'GroupedRdbStreamE2e.BackupStreamsFourTypesThenImportsAndRestarts')
run('stream-transfer-tests',[str(B/'lavik_grouped_ordered_write_e2e_test'),str(binary),
    '--gtest_filter='+filters,'--gtest_output=json:'+str(W/f'{prefix}-stream-transfer-tests.json')])
filters = ('ListE2eTest.BlockingAndStreamedCommandsDoNotHoldFlushDbGate:'
           'ListE2eTest.StreamBlockingRegistryBroadcastsAndKeepsGroupFifo:'
           'ListE2eTest.DisconnectCancelsActiveBlockingWait:'
           'ListE2eTest.PipelineFlushesRepliesBeforeBlockingCommand:'
           'CollectionE2eTest.SortedSetGeoAndStreamCommandsRecover')
run('blocking-tests',[str(B/'lavik_list_e2e_test'),str(binary),'--gtest_filter='+filters,
    '--gtest_output=json:'+str(W/f'{prefix}-blocking-tests.json')])
run('pubsub-tests',[str(B/'lavik_pubsub_e2e_test'),str(binary)])
assert hashlib.sha256(binary.read_bytes()).hexdigest()==sha
versions=json.loads((W/'stream-followup-versions.json').read_text())
versions['window'].update(commit=commit,binary=str(binary),sha256=sha)
versions['window']['fault_path_validation']='stream-window-boundary-validation.json'
output.write_text(json.dumps(versions,indent=2)+'\n')
print('ALL_CORRECTED_STREAM_PRODUCTION_TESTS_PASS', time.time(), flush=True)
