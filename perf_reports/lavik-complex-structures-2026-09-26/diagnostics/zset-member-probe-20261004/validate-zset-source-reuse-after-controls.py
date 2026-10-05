"""Validate native parent/candidate binaries after all Stream controls finish."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import time

W = Path(__file__).parent
S = Path('/mnt/dev/lavik-complex-next-20261004')
B = S / 'build-spdk'
expected = {
    'previous': (266, '067c75891f819831620e277eac0592c360f8b585', 'perf/zset-member-probe-20261004'),
    'candidate': (273, 'd012a301', 'perf/zset-source-page-reuse-20261004'),
}
# Resolve the abbreviated candidate once, before waiting or mutating checkout.
expected['candidate'] = (273, subprocess.check_output(['git', 'rev-parse', 'd012a301'], cwd=S, text=True).strip(), expected['candidate'][2])
output = W / 'zset-source-reuse-versions.json'
assert not output.exists(), 'inspect prior validation before restarting'
proc = Path('/proc/586587/stat')
identity = proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_STREAM_CONTROLS', identity, time.time(), flush=True)
while proc.exists() and identity is not None:
    try:
        if proc.read_text().split()[21] != identity:
            break
    except FileNotFoundError:
        break
    time.sleep(15)
assert 'ALL_STREAM_REPLY_CONTROL_REPEATS_COMPLETE' in (W / 'stream-reply-control-repeat-driver.log').read_text()
assert len(json.loads((W / 'stream-reply-control-repeats.json').read_text())['rows']) == 36
proofs = {}
for label, (pr, commit, branch) in expected.items():
    actual = json.loads(subprocess.check_output(['gh', 'pr', 'view', str(pr), '--repo', 'eloqdata/lavik', '--json', 'headRefOid']))
    assert actual['headRefOid'] == commit, (label, actual, commit)
    runs = json.loads(subprocess.check_output(['gh', 'run', 'list', '--repo', 'eloqdata/lavik', '--branch', branch, '--limit', '5', '--json', 'databaseId,headSha,status,conclusion']))
    run = next(x for x in runs if x['headSha'] == commit)
    ci = json.loads(subprocess.check_output(['gh', 'run', 'view', str(run['databaseId']), '--repo', 'eloqdata/lavik', '--json', 'headSha,conclusion,jobs,url']))
    assert ci['headSha'] == commit
    proofs[label] = ci
    (W / f'zset-source-reuse-{label}-ci-at-native-start.json').write_text(json.dumps(ci, indent=2) + '\n')

# Native validation uses the quiet local host after the benchmark driver
# restores it. Remote CI can progress concurrently; the measurement driver
# separately requires full CI success on both exact revisions before seeding.
assert subprocess.check_output(['git', 'diff', 'HEAD', '--'], cwd=S) == b''
versions = {}
for label, (_, commit, _) in expected.items():
    def run(name, argv):
        print('START', label, name, time.time(), flush=True)
        with (W / f'zset-source-reuse-{label}-{name}.txt').open('w') as f:
            subprocess.run(argv, cwd=S, stdout=f, stderr=subprocess.STDOUT, check=True)
        print('PASS', label, name, time.time(), flush=True)
    run('checkout', ['git', 'switch', '--detach', commit])
    run('configure-tests', ['cmake', '-S', '.', '-B', 'build-spdk', '-DBUILD_TESTING=ON', '-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
    run('build-tests', ['cmake', '--build', 'build-spdk', '--target', 'lavik', 'lavik_grouped_ordered_write_e2e_test', '--parallel', '4'])
    run('configure-production', ['cmake', '-S', '.', '-B', 'build-spdk', '-DBUILD_TESTING=OFF', '-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
    run('build-production', ['cmake', '--build', 'build-spdk', '--target', 'lavik', '--parallel', '4'])
    cache = (B / 'CMakeCache.txt').read_text()
    assert 'BUILD_TESTING:BOOL=OFF' in cache and 'LAVIK_ENABLE_TEST_FAULTS:BOOL=OFF' in cache
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=S, text=True).strip() == commit
    assert subprocess.check_output(['git', 'diff', 'HEAD', '--'], cwd=S) == b''
    binary = Path('/mnt/dev/lavik-benchmark-binaries') / f'lavik-zset-source-{label}-{commit[:8]}-20261004'
    assert not binary.exists()
    shutil.copyfile(B / 'lavik', binary)
    binary.chmod(0o755)
    version = {**json.loads((W / 'stream-reply-versions.json').read_text())['main'],
               'commit': commit, 'binary': str(binary), 'sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
               'source_repo': str(S), 'ci_run_at_native_start': proofs[label]['url'],
               'ci_required_before_performance': True}
    (W / f'zset-source-reuse-{label}-CMakeCache.txt').write_text(cache.rstrip() + '\n')
    filters = ('GroupedSortedSetWriteE2e.*:GroupedOrderedWriteE2e.SortedSet*:'
               'GroupedOrderedWriteE2e.LargeSortedSetMemberUsesExtents:GroupedDemotionE2e.*')
    run('native-tests', [str(B / 'lavik_grouped_ordered_write_e2e_test'), str(binary),
                         '--gtest_filter=' + filters,
                         '--gtest_output=json:' + str(W / f'zset-source-reuse-{label}-native-tests.json')])
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == version['sha256']
    versions[label] = version
    (W / 'zset-source-reuse-validation-progress.json').write_text(json.dumps(versions, indent=2) + '\n')
output.write_text(json.dumps(versions, indent=2) + '\n')
print('ALL_ZSET_SOURCE_REUSE_NATIVE_TESTS_PASS', time.time(), flush=True)
