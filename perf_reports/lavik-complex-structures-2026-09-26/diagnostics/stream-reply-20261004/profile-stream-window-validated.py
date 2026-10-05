"""Independent perf diagnostics after all clean Stream follow-up rounds finish."""
from pathlib import Path
import json
import os
import signal
import subprocess
import time

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
output = W / 'stream-window-followup-profiles.json'
assert not output.exists(), 'inspect prior profile before restarting'
proc = Path('/proc/761046/stat')
identity = proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_CLEAN_STREAM_ROUNDS', identity, time.time(), flush=True)
while proc.exists() and identity is not None:
    try:
        if proc.read_text().split()[21] != identity:
            break
    except FileNotFoundError:
        break
    time.sleep(15)
assert 'ALL_STREAM_WINDOW_FOLLOWUP_REPEATS_COMPLETE' in (W / 'stream-window-validated-repeat-driver.log').read_text()
repeats = json.loads((W / 'stream-window-followup-repeats.json').read_text())
assert len(repeats['rows']) == 60
assert not any('error' in row for row in repeats['rows']), 'investigate clean benchmark errors before profiling'
from host_execution_lock import acquire_host
_execution_lock = acquire_host('stream-window-perf')

old=json.loads((W/'stream-singleton-followup-profiles.json').read_text())['profiles']
profiles={key:value for key,value in old.items() if key.startswith('parent-')}
assert profiles.keys()=={'parent-full','parent-point'}
assert all(v['version']['commit']=='adec3a3414adf7b18dc304d336253258e228cb02' for v in profiles.values())
assert all(v['version']['sha256']==repeats['versions']['parent']['sha256'] for v in profiles.values())
def terminate(_signal,_frame):raise SystemExit('profile interrupted')
signal.signal(signal.SIGTERM,terminate)
def execute(argv,log=None):
    child=subprocess.Popen(argv,cwd=R.parents[1],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        code=child.wait()
        if code:raise subprocess.CalledProcessError(code,argv)
    except BaseException:
        # The memory guard starts a separate session for its runner/server.
        # Remember descendant groups before interrupting the guard, so fallback
        # cleanup cannot leave that separate session holding an SPDK device.
        owned={child.pid};groups={child.pid}
        processes={}
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():continue
            try:
                fields=(entry/'stat').read_text().rsplit(')',1)[1].split()
                processes[int(entry.name)]=(int(fields[1]),int(fields[2]))
            except (FileNotFoundError,PermissionError,ProcessLookupError):continue
        while True:
            more={pid for pid,(parent,_) in processes.items() if parent in owned}-owned
            if not more:break
            owned.update(more)
        groups.update(group for pid,(_,group) in processes.items() if pid in owned)
        groups.discard(os.getpgrp())
        if child.poll() is None:
            subprocess.run(['sudo','-n','kill','-INT','--',f'-{child.pid}'],check=False)
            try:child.wait(timeout=45)
            except subprocess.TimeoutExpired:pass
        for group in groups:
            subprocess.run(['sudo','-n','kill','-KILL','--',f'-{group}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        child.wait();raise

for mode, connections in [('full', 1), ('point', 2560)]:
    for label in ['window']:
        v = repeats['versions'][label]
        tag = f'diagnostic-{label}{v["commit"][:8]}-stream-window-followup-{mode}-104857600-128-20261005'
        raw = R / 'raw' / ('lavik-' + tag)
        assert not raw.exists(), raw
        argv = ['sudo', '-n', 'env', 'LAVIK_BENCH_ROOT=' + str(R), 'python3',
                str(R / 'run_with_memory_guard.py'), '--minimum-available-gib=20', '--',
                'python3', str(W / 'profile-stream-followup-allworkers.py'), 'lavik',
                '--binary=' + v['binary'], '--source-repo=' + v['source_repo'],
                '--source-commit=' + v['commit'], '--types=stream', '--sizes=104857600',
                '--fields=128', '--keys=8', '--tag=' + tag, '--mode=' + mode,
                '--levels=' + str(connections), '--seconds=30']
        subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'prepare'], check=True)
        try:
            print('START', tag, time.time(), flush=True)
            with (W / (tag + '.log')).open('w') as log:
                execute(argv,log)
        finally:
            subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'restore'], check=True)
        subprocess.run(['sudo', '-n', 'chown', '-R', f'{os.getuid()}:{os.getgid()}', str(raw)], check=True)
        assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
        assert json.loads((raw / 'complete.json').read_text())['failures_total'] == 0
        proof = json.loads(next(raw.glob('provenance-*.json')).read_text())
        assert proof['source_commit'] == v['commit'] and proof['sha256'] == v['sha256']
        prefix = 'stream-104857600-128'
        assert json.loads((raw / (prefix + '.validated.json')).read_text())['sample_cardinalities'] == json.loads((raw / (prefix + '.after.json')).read_text())['sample_cardinalities']
        diagnostic = raw / f'diagnostic-c{connections}'
        evidence = json.loads((diagnostic / 'profile-provenance.json').read_text())
        assert evidence['source_commit'] == v['commit'] and evidence['binary'] == v['binary']
        assert len(evidence['argv_by_tid']) >= 12
        # Keep every attached thread, including a valid zero-sample helper. Raw
        # stacks/perf stay local; later publication selects small reports explicitly.
        profiles[f'{label}-{mode}'] = {'version': v, 'tag': tag, 'directory': str(diagnostic), 'attached_tids': list(evidence['argv_by_tid'])}
        output.write_text(json.dumps({'profiles': profiles, 'method': 'Reuse the two completed exact-parent adec profiles from the singleton investigation; parent/candidate captures are not contemporaneous. New window5b profiles use the identical settings on independent fresh populations. Stream XRANGE_FULL c1 or point XRANGE c2560, 30-second counter window and 25-second 99Hz task-clock/DWARF recording on each serving thread. Not a clean QPS point. CPU shares include polling/background/kernel work; IO counters are server-wide. No concurrent benchmark/build/tests.'}, indent=2) + '\n')
        print('COMPLETE', tag, time.time(), flush=True)
print('ALL_STREAM_WINDOW_FOLLOWUP_PROFILES_COMPLETE', time.time(), flush=True)
