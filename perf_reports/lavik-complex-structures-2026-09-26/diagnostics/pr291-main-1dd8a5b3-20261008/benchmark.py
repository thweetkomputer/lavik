"""Three paired clean runs, then separate perf samples, on one exclusive host."""
from pathlib import Path
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
sys.path.insert(0, '/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
from process_helpers import execute

V = json.loads((W / 'versions.json').read_text())
lock = acquire_host('pr291-qps-main-1dd8a5b3')
def stop(_signal, _frame):
    raise SystemExit('PR289 benchmark interrupted')
signal.signal(signal.SIGTERM, stop)

def verify_inputs():
    for path, expected in json.loads((W / 'harness-provenance.json').read_text()).items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
    for v in V.values():
        with Path(v['binary']).open('rb') as f:
            assert hashlib.file_digest(f, 'sha256').hexdigest() == v['sha256']
        assert v['bycorf_commit'] == '62509c93d40c2480f5046b71454db6cf95801b04'


def run(argv, log=None):
    with (W / 'commands.jsonl').open('a') as f:
        f.write(json.dumps({'time': time.time(), 'argv': argv}) + '\n')
    execute(argv, log)

def point(label, kind, size, op, round_, profiling=False):
    verify_inputs()
    v = V[label]
    seed = hashlib.sha256(f'lavik-pr289-round-{round_}'.encode()).hexdigest()[:32]
    client_seed = str(int(seed[:8], 16))
    tag = f'{"perf-" if profiling else ""}{label}{v["commit"][:8]}-pr291full-{kind}-{size}-{op.lower()}-r{round_}-20261008'
    raw = R / 'raw' / ('lavik-' + tag)
    assert not raw.exists(), raw
    guard = ['sudo', '-n', 'env', 'LAVIK_BENCH_ROOT=' + str(R),
             'BENCH_CLIENT_SEED=' + client_seed, 'unshare', '--mount', '--propagation', 'private',
             'python3', str(W / 'private-tmp-exec.py'), str(W / 'benchmark-tmp'), '0', '0',
             'python3', str(R / 'run_with_memory_guard.py'), '--minimum-available-gib=20', '--',
             'python3', str(W / 'fixed-seed-exec.py'), seed, str(W / 'versions.json')]
    args = [str(W / 'run-random.py'), 'lavik', '--binary=' + v['binary'],
            '--source-repo=' + v['source_repo'], '--source-commit=' + v['commit'],
            '--types=' + kind, '--sizes=' + str(size), '--fields=1024', '--keys=8',
            '--mode=point', '--levels=320', '--seconds=30', '--tag=' + tag, '--only-op', op]
    if profiling:
        args += ['--profile']
    print('START', tag, time.time(), flush=True)
    run(['sudo', '-n', 'python3', str(W / 'host.py'), 'prepare'])
    try:
        with (W / (tag + '.log')).open('w') as log:
            run(guard + args, log)
    finally:
        if (R / 'spdk-ready.json').exists():
            run(['sudo', '-n', 'python3', str(W / 'host.py'), 'restore'])
    run(['sudo', '-n', 'chown', '-R', f'{os.getuid()}:{os.getgid()}', str(raw)])
    assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
    assert json.loads((raw / 'complete.json').read_text())['failures_total'] == 0
    proof = json.loads(next(raw.glob('provenance-*.json')).read_text())
    assert proof['source_commit'] == v['commit'] and proof['sha256'] == v['sha256']
    seeded = json.loads((raw / 'fixed-digest-seed.json').read_text())
    assert seeded['seed_hex'] == seed and seeded['verified_via_proc_mem']
    results = list(raw.glob('*.result.json'))
    assert len(results) == 1
    result = json.loads(results[0].read_text())
    assert result['operation'] == op and result['command_audit']['passed']
    print('COMPLETE', tag, round(result['qps'], 2), round(result['p99_ms'], 3), time.time(), flush=True)
    return {'round': round_, 'version': label, 'kind': kind, 'size': size, 'operation': op,
            'digest_seed': seed, 'client_seed': client_seed, 'tag': tag, 'raw': str(raw), 'result': result}

if __name__ == '__main__':
    label=sys.argv[1]; rounds=[int(x) for x in sys.argv[2].split(',')]
    profiling='--profile' in sys.argv
    output=W/(label+('-profiles' if profiling else '-repeats')+'.json')
    rows=json.loads(output.read_text()) if output.exists() else []
    for round_ in rounds:
        rows.append(point(label,'list',8388608,'RPUSH_LPOP',round_,profiling))
        output.write_text(json.dumps(rows,indent=2)+'\n')
    print('MEASUREMENTS_COMPLETE',flush=True)
