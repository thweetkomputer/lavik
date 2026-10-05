"""Measure source-page reuse only after exact serial native validation succeeds."""
from pathlib import Path
import json
import os
import subprocess
import time

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
output = W / 'zset-source-reuse-repeats.json'
assert not output.exists(), 'inspect prior measurement before restarting'
# Finish the already queued correctness diagnostics before long throughput
# sweeps acquire the host. Capture both process generations before waiting.
priority_processes=[]
for pid in (718823,719158):
    process=Path('/proc')/str(pid)/'stat'
    generation=process.read_text().split()[21] if process.exists() else None
    priority_processes.append((process,generation))
for process,generation in priority_processes:
    print('WAIT_FOR_PRIORITY_DIAGNOSTIC',str(process),generation,time.time(),flush=True)
    while generation is not None and process.exists():
        try:
            if process.read_text().split()[21]!=generation:break
        except FileNotFoundError:break
        time.sleep(15)
proc = Path('/proc/696099/stat')
identity = proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_PLANNER_FAULT_VALIDATION', identity, time.time(), flush=True)
while proc.exists() and identity is not None:
    try:
        if proc.read_text().split()[21] != identity:
            break
    except FileNotFoundError:
        break
    time.sleep(15)
assert 'ZSET_PLANNER_FAULT_REPRODUCED_AND_FIXED' in (W / 'zset-planner-fault-independent-driver.log').read_text()
proof = json.loads((W / 'zset-planner-fault-validation.json').read_text())
assert proof['fixed']['commit'] == '92906489799d5d65c8315cc87371a14f6b2e384e'
assert proof['original']['tests']['failures'] == 1
assert proof['fixed']['tests']['tests'] >= 27 and proof['fixed']['tests']['failures'] == 0
assert proof['original']['server_sha256'] == proof['fixed']['server_sha256']
assert 'ALL_ZSET_SOURCE_REUSE_NATIVE_TESTS_PASS' in (W / 'zset-source-reuse-validation-driver.log').read_text()
V = json.loads((W / 'zset-source-reuse-versions.json').read_text())
assert V['previous']['commit'] == '067c75891f819831620e277eac0592c360f8b585'
assert V['candidate']['commit'] == 'd012a3013da99344a419bb692f834b17fd6dcad4'
for label in V:
    tests = json.loads((W / f'zset-source-reuse-{label}-native-tests.json').read_text())
    assert tests['tests'] > 0 and tests['failures'] == 0
# The latest commit repairs only a test's pre-fork environment setup. Keep
# the native executable's actual build commit and hash instead of relabeling it.
ci_candidate = '92906489799d5d65c8315cc87371a14f6b2e384e'
changed = subprocess.check_output(['git', 'diff', '--name-only', V['candidate']['commit'], ci_candidate],
                                 cwd=V['candidate']['source_repo'], text=True).splitlines()
assert changed == ['tests/grouped/zset_write_e2e_test.cpp'], changed
V['candidate']['test_validation_commit'] = ci_candidate
V['candidate']['runtime_equivalence'] = {'changed_files': changed,
    'same_fault_enabled_server_sha256': proof['fixed']['server_sha256'],
    'proof': 'zset-planner-fault-validation.json',
    'note': 'Production binary remains the original d012a301 build; only the test driver changes at 92906489.'}
# Native validation and remote CI are independent, but measurements require
# both to have passed on these exact revisions. Pending jobs are not failures.
for label, pr, branch in [('previous', 266, 'perf/zset-member-probe-20261004'),
                          ('candidate', 273, 'perf/zset-source-page-reuse-20261004')]:
    commit = ci_candidate if label == 'candidate' else V[label]['commit']
    while True:
        actual = json.loads(subprocess.check_output(['gh', 'pr', 'view', str(pr), '--repo', 'eloqdata/lavik', '--json', 'headRefOid']))
        assert actual['headRefOid'] == commit, (label, actual, commit)
        runs = json.loads(subprocess.check_output(['gh', 'run', 'list', '--repo', 'eloqdata/lavik', '--branch', branch, '--limit', '5', '--json', 'databaseId,headSha,status,conclusion']))
        run = next(x for x in runs if x['headSha'] == commit)
        ci = json.loads(subprocess.check_output(['gh', 'run', 'view', str(run['databaseId']), '--repo', 'eloqdata/lavik', '--json', 'headSha,status,conclusion,jobs,url']))
        assert ci['headSha'] == commit
        failed = [j for j in ci['jobs'] if j['conclusion'] in ('failure', 'cancelled', 'timed_out', 'action_required')]
        assert not failed, (label, failed)
        if ci['status'] == 'completed':
            assert ci['conclusion'] == 'success', (label, ci)
            shards = [j for j in ci['jobs'] if j['name'].startswith('Test shard (')]
            assert len(shards) == 12 and all(j['conclusion'] == 'success' for j in shards)
            (W / f'zset-source-reuse-{label}-validated-full-ci.json').write_text(json.dumps(ci, indent=2) + '\n')
            V[label]['full_fault_enabled_ci'] = ci['url']
            break
        print('WAIT_FOR_FULL_CI', label, run, time.time(), flush=True)
        time.sleep(60)
from host_execution_lock import acquire_host
_execution_lock = acquire_host('clean-zset-pairs')

rows = []
method = ('Three independent fresh-seed pairs A/B, B/A, A/B per workload: '
          '100MiB/1024B/8keys and 64KiB/128B/64keys; 30-second ZSCORE and '
          'ZINCRBY at 80/320/2560/5120 connections. Previous PR266 head 067c7589 '
          'versus PR273 d012a301, both include main194 allocation policy. '
          'Production binaries passed native tests; parent067 full CI and candidate929 '
          'full CI plus verified tests-only diff from binary commitd012 pass before measurements. '
          'The same fault-enabled server reproduces the original fixture failure and passes '
          'all corrected27cases. No concurrent builds/tests/perf. All errors retained.')
for size, field, keys in [(104857600, 1024, 8), (65536, 128, 64)]:
    for round_, labels in enumerate([['previous', 'candidate'], ['candidate', 'previous'], ['previous', 'candidate']], 1):
        for label in labels:
            v = V[label]
            tag = f'{label}{v["commit"][:8]}-zset-source-reuse-{size}-{field}-repeat{round_}-20261005'
            raw = R / 'raw' / ('lavik-' + tag)
            assert not raw.exists(), raw
            argv = ['sudo', '-n', 'env', 'LAVIK_BENCH_ROOT=' + str(R), 'python3',
                    str(R / 'run_with_memory_guard.py'), '--minimum-available-gib=20', '--',
                    'python3', str(R / 'run.py'), 'lavik', '--binary=' + v['binary'],
                    '--source-repo=' + v['source_repo'], '--source-commit=' + v['commit'],
                    '--types=zset', '--sizes=' + str(size), '--fields=' + str(field),
                    '--keys=' + str(keys), '--tag=' + tag, '--mode=point',
                    '--levels=80,320,2560,5120', '--seconds=30', '--continue-on-error']
            subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'prepare'], check=True)
            try:
                print('START', tag, time.time(), flush=True)
                with (W / (tag + '.log')).open('w') as f:
                    subprocess.run(argv, cwd=R.parents[1], stdout=f, stderr=subprocess.STDOUT, check=True)
            finally:
                subprocess.run(['sudo', '-n', 'python3', str(W / 'host.py'), 'restore'], check=True)
            subprocess.run(['sudo', '-n', 'chown', '-R', f'{os.getuid()}:{os.getgid()}', str(raw)], check=True)
            assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
            assert (raw / 'complete.json').exists()
            proof = json.loads(next(raw.glob('provenance-*.json')).read_text())
            assert proof['source_commit'] == v['commit'] and proof['sha256'] == v['sha256']
            prefix = f'zset-{size}-{field}'
            before = json.loads((raw / (prefix + '.validated.json')).read_text())['sample_cardinalities']
            after = json.loads((raw / (prefix + '.after.json')).read_text())['sample_cardinalities']
            assert before == after
            results = [json.loads(p.read_text()) for p in list(raw.glob('*.result.json')) + list(raw.glob('*.error.json'))]
            expected = {(op, c) for op in ('ZSCORE', 'ZINCRBY') for c in (80, 320, 2560, 5120)}
            assert len(results) == 8 and {(x['operation'], x['connections']) for x in results} == expected
            rows.extend({'round': round_, 'version': label, 'tag': tag, **x} for x in results)
            output.write_text(json.dumps({**V, 'rows': rows, 'method': method}, indent=2) + '\n')
            print('COMPLETE', tag, time.time(), flush=True)
assert len(rows) == 96
print('ALL_ZSET_SOURCE_REUSE_REPEATS_COMPLETE', time.time(), flush=True)
