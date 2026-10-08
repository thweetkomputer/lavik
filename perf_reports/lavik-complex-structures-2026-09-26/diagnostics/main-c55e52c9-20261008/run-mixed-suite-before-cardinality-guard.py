"""Fresh-server mixed writes across Lavik, Redis, Valkey, and Kvrocks."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time

sys.path.insert(0, '/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
from process_helpers import execute

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
sys.path.insert(0, str(R))
import run as common

lock = acquire_host('main-c55e52c9-four-system-mixed-writes')
v = json.loads((W / 'versions.json').read_text())['main']
assert v['commit'] == 'c55e52c98d785dec9603d33ddcf55eab299eb11e'
resume = '--resume' in sys.argv
assert resume or not (W / 'mixed-results.json').exists(), 'Preserve partial runs; resume explicitly'

def interrupted(_signal, _frame):
    raise SystemExit('mixed benchmark interrupted')

signal.signal(signal.SIGTERM, interrupted)

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

assert sha(v['binary']) == v['sha256']
client = '/mnt/dev/random-client-main-c55e52c9-20261008'
execute(['scp', '-q', str(W / 'random-client'), '172.16.0.5:' + client])
remote_sha = subprocess.check_output(['ssh', '-o', 'BatchMode=yes', '172.16.0.5', 'sha256sum', client], text=True).split()[0]
assert remote_sha == sha(W / 'random-client')
(W / 'mixed-client-provenance.json').write_text(json.dumps({
    'binary_sha256': remote_sha, 'source_sha256': sha(W / 'random-client.cpp'),
    'source': 'random-client.cpp', 'remote_binary': client,
    'client_seed': 42, 'server': common.HOST, 'client': common.CLIENT,
    'compiler_origin': '/mnt/dev/lavik-fenwick-20261008/client-provenance.json'
}, indent=2) + '\n')

ops = {'list': ['LPUSH_RPOP', 'RPUSH_LPOP'],
       'zset': ['ZADD_HEAD_ZPOPMAX', 'ZADD_RANDOM_ZPOPMIN', 'ZADD_TAIL_ZPOPMIN']}
products = ['lavik', 'redis', 'valkey', 'kvrocks']
seed = hashlib.sha256(b'lavik-fenwick-round-1').hexdigest()[:32]
rows = json.loads((W / 'mixed-results.json').read_text()) if resume and (W / 'mixed-results.json').exists() else []
smokes = json.loads((W / 'mixed-smoke-results.json').read_text()) if resume else []
if resume: assert len(smokes) == 20

def host(product, action):
    if product == 'lavik':
        execute(['sudo', '-n', 'python3', str(W / 'host.py'), action])
    elif product == 'kvrocks':
        execute(['sudo', '-n', 'python3', str(R / 'kvrocks_host.py'), action,
                 *(['--discard-scratch'] if action == 'prepare' else [])])

def one(product, kind, op, size, connections, smoke=False):
    existing = [x for x in (smokes if smoke else rows) if x['system'] == product and (x['result']['type'], x['result']['operation'], x['result']['logical_bytes'], x['result']['connections']) == (kind, op, size, connections)]
    if existing:
        assert len(existing) == 1 and existing[0]['result']['command_audit']['passed']
        print('RETAIN_COMPLETED', product, kind, op, size, connections, flush=True)
        return
    tag = f'mainc55e52c9-mixed-{kind}-{size}-{op.lower()}-c{connections}-20261008'
    if smoke:
        tag = 'smoke-' + tag
    raw = R / 'raw' / (product + '-' + tag)
    assert not raw.exists(), raw
    seconds = 1 if smoke else 30
    args = [str(W / 'run-random.py'), product,
            '--types=' + kind, '--sizes=' + str(size), '--fields=1024', '--keys=8',
            '--mode=point', '--levels=' + str(connections), '--seconds=' + str(seconds),
            '--tag=' + tag, '--writes-only', '--only-op', op]
    if product == 'lavik':
        args += ['--binary=' + v['binary'], '--source-repo=' + v['source_repo'],
                 '--source-commit=' + v['commit']]
        # This startup-only seed shim has no request-path hook. Every point
        # verifies the actual process seed and frozen production binary SHA.
        args = [str(W / 'fixed-seed-exec.py'), seed, str(W / 'versions.json'), *args]
    guard = ['sudo', '-n', 'env', 'LAVIK_BENCH_ROOT=' + str(R), 'BENCH_CLIENT_SEED=42',
             'unshare', '--mount', '--propagation', 'private', 'python3',
             str(W / 'private-tmp-exec.py'), str(W / 'benchmark-tmp'), '0', '0',
             'python3', str(R / 'run_with_memory_guard.py'), '--minimum-available-gib=20',
             '--', 'python3', *args]
    print('START', product, tag, time.time(), flush=True)
    if product == 'lavik':
        host(product, 'prepare')
    try:
        with (W / (product + '-' + tag + '.log')).open('w') as log:
            execute(guard, log)
    finally:
        if product == 'lavik' and (R / 'spdk-ready.json').exists():
            host(product, 'restore')
    execute(['sudo', '-n', 'chown', '-R', f'{os.getuid()}:{os.getgid()}', str(raw)])
    assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
    assert json.loads((raw / 'complete.json').read_text())['failures_total'] == 0
    results = list(raw.glob('*.result.json'))
    assert len(results) == 1
    result = json.loads(results[0].read_text())
    assert result['command_audit']['passed'] and result['seconds'] == seconds
    proof = json.loads(next(raw.glob('provenance-*.json')).read_text())
    assert proof['sha256'] == sha(v['binary'] if product == 'lavik' else common.PEERS[product])
    if product == 'lavik':
        fixed = json.loads((raw / 'fixed-digest-seed.json').read_text())
        assert fixed['seed_hex'] == seed and fixed['verified_via_proc_mem']
        assert proof['source_commit'] == v['commit']
    row = {'system': product, 'tag': tag, 'raw': str(raw), 'provenance': proof,
           'version': json.loads((raw / 'version.json').read_text()), 'result': result}
    target = smokes if smoke else rows
    target.append(row)
    name = 'mixed-smoke-results.json' if smoke else 'mixed-results.json'
    temp = W / (name + '.tmp')
    temp.write_text(json.dumps(target, indent=2) + '\n')
    temp.replace(W / name)
    print('COMPLETE', product, op, size, connections, 'POINTS', len(target), time.time(), flush=True)

# Smoke-test every operation on every protocol implementation before freezing
# the full measurement harness. These one-second checks never enter charts.
if not smokes:
    for product in products:
        if product == 'kvrocks':
            host(product, 'prepare')
        try:
            for kind, names in ops.items():
                for op in names:
                    one(product, kind, op, 8388608, 16, smoke=True)
        finally:
            if product == 'kvrocks' and (R / 'kvrocks-raid-ready.json').exists():
                host(product, 'restore')
assert len(smokes) == 20
files = ['run-random.py', 'run-mixed-suite.py', 'random-client.cpp', 'random-client',
         'fixed-seed-exec.py', 'fixed-digest-seed.c', 'fixed-digest-seed.so', 'host.py', 'private-tmp-exec.py']
(W / 'mixed-harness-provenance.json').write_text(json.dumps({name: sha(W / name) for name in files}, indent=2) + '\n')
print('ALL_MIXED_SMOKES_PASS', flush=True)

for product in products:
    if product == 'kvrocks':
        host(product, 'prepare')
    try:
        for size in [8388608, 104857600]:
            for kind, names in ops.items():
                for op in names:
                    for connections in [80, 320, 1280, 2560, 5120]:
                        one(product, kind, op, size, connections)
    finally:
        if product == 'kvrocks' and (R / 'kvrocks-raid-ready.json').exists():
            host(product, 'restore')
assert len(rows) == 200
print('ALL_FOUR_SYSTEM_MIXED_WRITES_COMPLETE', time.time(), flush=True)
