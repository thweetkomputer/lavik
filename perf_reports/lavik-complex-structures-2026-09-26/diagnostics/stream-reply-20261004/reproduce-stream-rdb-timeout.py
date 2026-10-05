"""Compare the failing RDB case using fixed binaries and a diagnostic-only driver."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import time
from host_execution_lock import acquire_host
W=Path(__file__).parent
S=Path('/mnt/dev/lavik-complex-next-20261004')
B=S/'build-spdk'
output=W/'stream-rdb-timeout-reproductions.json'
assert not output.exists()
_execution_lock=acquire_host('stream-rdb-timeout-reproduction')
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
diagnostic='763d9076c76e5f0985a72c26d62959882043a9f2'
fixed='5b9ebdedecc0cc7a3fea93fb73b1fbbb6b7186c6'
assert subprocess.check_output(['git','diff','--name-only',fixed,diagnostic],cwd=S,text=True).splitlines()==['tests/grouped/stream_e2e_test.cpp']
def run(name,args):
    print('START',name,time.time(),flush=True)
    with (W/f'stream-rdb-diagnostic-{name}.txt').open('w') as log:
        subprocess.run(args,cwd=S,stdout=log,stderr=subprocess.STDOUT,check=True)
    print('PASS',name,time.time(),flush=True)
run('checkout',['git','switch','--detach',diagnostic])
run('configure',['cmake','-S','.','-B','build-spdk','-DBUILD_TESTING=ON','-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
# Build only the independent test driver. Neither frozen production executable
# is rebuilt or modified by the additional phase/failure diagnostics.
run('build',['cmake','--build','build-spdk','--target','lavik_grouped_ordered_write_e2e_test','--parallel','4'])
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==diagnostic
assert subprocess.check_output(['git','diff','HEAD','--'],cwd=S)==b''
driver=Path('/mnt/dev/lavik-benchmark-binaries/lavik-stream-rdb-diagnostic-driver-763d9076-20261005')
assert not driver.exists()
shutil.copyfile(B/'lavik_grouped_ordered_write_e2e_test',driver);driver.chmod(0o755)
versions=json.loads((W/'stream-followup-versions.json').read_text())
versions={label:versions[label] for label in ['parent','window']}
versions['window'].update(commit=fixed,binary='/mnt/dev/lavik-benchmark-binaries/lavik-stream-followup-window-5b9ebded-20261005')
versions['window']['sha256']=hashlib.sha256(Path(versions['window']['binary']).read_bytes()).hexdigest()
rows=[]
for round_,order in enumerate([['parent','window'],['window','parent']],1):
    for label in order:
        v=versions[label]
        assert hashlib.sha256(Path(v['binary']).read_bytes()).hexdigest()==v['sha256']
        data=W/f'stream-rdb-timeout-{label}-{round_}-data';data.mkdir()
        env=dict(os.environ,LAVIK_TEST_DATA_DIR=str(data))
        result=W/f'stream-rdb-timeout-{label}-{round_}.json'
        log=W/f'stream-rdb-timeout-{label}-{round_}.txt'
        print('START_REPRO',label,round_,time.time(),flush=True)
        started=time.time()
        with log.open('w') as stream:
            p=subprocess.run([str(driver),v['binary'],
                '--gtest_filter=GroupedStreamE2e.LargeRdbRoundTripKeepsMessagesAndDeletedPendingBounded',
                '--gtest_output=json:'+str(result)],cwd=S,env=env,stdout=stream,stderr=subprocess.STDOUT)
        rows.append({'version':label,'round':round_,'exit':p.returncode,'elapsed_seconds':time.time()-started,
                     'result':json.loads(result.read_text()) if result.exists() else None,
                     'log':str(log),'data_directory':str(data)})
        output.write_text(json.dumps({'versions':versions,'driver_commit':diagnostic,'driver_sha256':hashlib.sha256(driver.read_bytes()).hexdigest(),
            'method':'Two alternating parent/candidate pairs on independent private files; same immutable production binaries; diagnostic-only test changes identify pre-export vs post-import XREADGROUP and retain images/log/RDB on failure. Original socket15s and import/export180s deadlines unchanged. Stop first failure; all-pass does not explain original timeout.',
            'rows':rows},indent=2)+'\n')
        assert p.returncode==0,(label,round_,str(log),str(data))
        print('PASS_REPRO',label,round_,time.time(),flush=True)
print('ALL_STREAM_RDB_TIMEOUT_REPRODUCTIONS_PASS',time.time(),flush=True)
