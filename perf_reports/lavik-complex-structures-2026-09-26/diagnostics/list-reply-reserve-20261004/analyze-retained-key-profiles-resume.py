"""Serialize perf decoding with benchmarks after the retained-image capture."""
from pathlib import Path
import hashlib
import json
import os
import signal
import subprocess
import time
from host_execution_lock import acquire_host

W=Path(__file__).parent
output=W/'pr267-retained-key-profile-analysis.json'
assert not output.exists()
process=Path('/proc/718823/stat')
generation=process.read_text().split()[21] if process.exists() else None
print('WAIT_FOR_RETAINED_KEY_CAPTURE',generation,time.time(),flush=True)
while generation is not None and process.exists():
    try:
        if process.read_text().split()[21]!=generation:break
    except FileNotFoundError:break
    time.sleep(1)
assert 'ALL_PR267_RETAINED_IMAGE_PROFILES_FINISHED' in (W/'pr267-retained-image-profile-driver.log').read_text()
data=json.loads((W/'pr267-retained-image-profiles.json').read_text())
assert len(data['rows'])==2
_execution_lock=acquire_host('retained-key-perf-analysis')

def terminate(_signal,_frame):raise SystemExit('analysis interrupted')
signal.signal(signal.SIGTERM,terminate)

def run(argv,destination):
    with destination.open('w') as stream:
        child=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            code=child.wait()
            if code:raise subprocess.CalledProcessError(code,argv)
        except BaseException:
            try:os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            child.wait()
            raise

summary=W/'pr267-retained-key-progress-summary.json'
subprocess.run(['python3',str(W/'summarize-retained-key-progress.py'),'--output',str(summary)],check=True)
records=[]
for row in data['rows']:
    label=row['version'];version=data['versions'][label]
    with Path(version['binary']).open('rb') as binary:
        assert hashlib.file_digest(binary,'sha256').hexdigest()==version['binary_sha256']
    directory=Path(row['image']).parent
    perf=directory/'long-key.perf'
    # The recorder was deliberately interrupted via its sudo process group.
    # sudo can report SIGINT even when perf completed its data/header flush.
    # Preserve that exit value and validate completed output plus both decoders.
    assert row.get('perf_exit') in (0,-signal.SIGINT,128+signal.SIGINT), (label,row.get('perf_exit'))
    assert perf.stat().st_size>0
    recorder_log=(directory/'perf-record.log').read_text()
    assert 'Captured and wrote' in recorder_log and 'samples)' in recorder_log
    assert 'Error:' not in recorder_log and 'failed' not in recorder_log.lower()
    print('ANALYZE',label,time.time(),flush=True)
    report=directory/'self.txt';stacks=directory/'stacks.txt'
    report_argv=['sudo','-n','perf','report','--stdio','--no-inline','--no-children','--call-graph','none','--sort','symbol','--percent-limit','0.1','-i',str(perf)]
    stack_argv=['sudo','-n','perf','script','--no-inline','-F','comm,pid,tid,time,period,event,ip,sym,dso','-i',str(perf)]
    run(report_argv,report);run(stack_argv,stacks)
    records.append({'version':label,'source':version,'report':str(report),'stacks_local_only':str(stacks),'report_argv':report_argv,'stack_argv':stack_argv,'recorder_exit':row.get('perf_exit'),'recording_validation':'Intentional SIGINT; completed perf write summary; successful report and script decoding required','get_completed':any(op['command']=='GET' and op['key_bytes']==9437184 for op in row['operations'])})
    output.write_text(json.dumps({'rows':records,'progress_summary':str(summary),'limits':'Diagnosis only: sampled CPU includes kernel, polling and background work; process IO is not command-exclusive. Interpret incomplete GETs separately. Raw perf and stack dumps stay local. No clean throughput is measured here.'},indent=2)+'\n')
print('ALL_RETAINED_KEY_PROFILE_ANALYSIS_COMPLETE',time.time(),flush=True)
