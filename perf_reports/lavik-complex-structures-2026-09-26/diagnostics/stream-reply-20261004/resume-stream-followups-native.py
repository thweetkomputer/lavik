"""Freeze and validate production parent/singleton/window binaries under host lock."""
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
output = W / 'stream-followup-versions.json'
assert not output.exists(), 'inspect prior validation before restarting'
assert 'ALL_ZSET_SOURCE_REUSE_NATIVE_TESTS_PASS' in (W / 'zset-source-reuse-validation-driver.log').read_text()
_execution_lock = acquire_host('native-stream-followups-resume-enospc')
expected = [
    ('parent', 270, 'adec3a3414adf7b18dc304d336253258e228cb02'),
    ('window', 275, 'ac62975fdf1f9dda1783429d523969b737efc98f'),
    ('singleton', 274, '85bc7ad0d7932b27dd6784c023fcbfdbd2dd8b08'),
]
for label, pr, commit in expected:
    actual = json.loads(subprocess.check_output(['gh', 'pr', 'view', str(pr), '--repo', 'eloqdata/lavik', '--json', 'headRefOid']))
    assert actual['headRefOid'] == commit, (label, actual, commit)
assert subprocess.check_output(['git', 'diff', 'HEAD', '--'], cwd=S) == b''
# The later parent commit changes only a fixture, not the runtime baseline of
# the two independent follow-ups. Keep the exact commits in every proof.
assert subprocess.check_output(['git', 'diff', 'cfe76ab2', expected[0][2], '--', 'src', 'include'], cwd=S) == b''
versions = {}
for label, pr, commit in expected:
    def run(name, argv):
        print('START', label, name, time.time(), flush=True)
        with (W / f'stream-followup-{label}-{name}.txt').open('w') as log:
            subprocess.run(argv, cwd=S, stdout=log, stderr=subprocess.STDOUT, check=True)
        print('PASS', label, name, time.time(), flush=True)
    if label != 'parent':
        run('checkout', ['git', 'switch', '--detach', commit])
        run('configure-tests', ['cmake', '-S', '.', '-B', 'build-spdk', '-DBUILD_TESTING=ON', '-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
        run('build-tests', ['cmake', '--build', 'build-spdk', '--target', 'lavik', 'lavik_grouped_ordered_write_e2e_test', 'lavik_list_e2e_test', 'lavik_pubsub_e2e_test', '--parallel', '4'])
        run('configure-production', ['cmake', '-S', '.', '-B', 'build-spdk', '-DBUILD_TESTING=OFF', '-DLAVIK_ENABLE_TEST_FAULTS=OFF'])
        run('build-production', ['cmake', '--build', 'build-spdk', '--target', 'lavik', '--parallel', '4'])
    cache = (B / 'CMakeCache.txt').read_text()
    assert 'BUILD_TESTING:BOOL=OFF' in cache and 'LAVIK_ENABLE_TEST_FAULTS:BOOL=OFF' in cache
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=S, text=True).strip() == commit
    assert subprocess.check_output(['git', 'diff', 'HEAD', '--'], cwd=S) == b''
    binary = Path('/mnt/dev/lavik-benchmark-binaries') / f'lavik-stream-followup-{label}-{commit[:8]}-20261005'
    if label == 'parent':
        assert binary.exists()
        assert hashlib.sha256(binary.read_bytes()).digest() == hashlib.sha256((B / 'lavik').read_bytes()).digest()
    else:
        assert not binary.exists()
        shutil.copyfile(B / 'lavik', binary)
        binary.chmod(0o755)
    version = {**json.loads((W / 'stream-reply-versions.json').read_text())['main'],
               'commit': commit, 'binary': str(binary), 'sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
               'source_repo': str(S), 'pr': pr, 'ci_required_before_performance': True}
    (W / f'stream-followup-{label}-CMakeCache.txt').write_text(cache.rstrip() + '\n')
    filters = ('GroupedStreamE2e.*:GroupedTransferE2e.*:'
               'GroupedRdbStreamE2e.FourTypesMultiPageLargeItemsAndMultipleWorkers:'
               'GroupedRdbStreamE2e.RestoreStreamsFourTypesInsideAndOutsideExec:'
               'GroupedRdbStreamE2e.BackupStreamsFourTypesThenImportsAndRestarts')
    data_dir = W / ('stream-followup-native-data-' + label)
    data_dir.mkdir(exist_ok=True)
    os.environ['LAVIK_TEST_DATA_DIR'] = str(data_dir)
    if label == 'parent':
        initial = W / 'stream-followup-parent-stream-transfer-tests.json'
        evidence = json.loads(initial.read_text())
        failures = [case for suite in evidence['testsuites'] for case in suite['testsuite'] if case.get('failures')]
        assert len(failures) == 1 and failures[0]['name'] == 'LargeRdbRoundTripKeepsMessagesAndDeletedPendingBounded'
        assert 'No space left on device' in initial.with_suffix('.txt').read_text()
        # Preserve the original failed run; only rerun its failing case on the
        # same frozen binary and driver, with large test files off the root FS.
        run('large-rdb-retry', [str(B / 'lavik_grouped_ordered_write_e2e_test'), str(binary),
            '--gtest_filter=GroupedStreamE2e.LargeRdbRoundTripKeepsMessagesAndDeletedPendingBounded',
            '--gtest_output=json:' + str(W / 'stream-followup-parent-large-rdb-retry.json')])
        version['initial_environment_failure'] = str(initial)
        version['failed_case_retry'] = str(W / 'stream-followup-parent-large-rdb-retry.json')
    else:
        run('stream-transfer-tests', [str(B / 'lavik_grouped_ordered_write_e2e_test'), str(binary), '--gtest_filter=' + filters,
                                     '--gtest_output=json:' + str(W / f'stream-followup-{label}-stream-transfer-tests.json')])
    filters = ('ListE2eTest.BlockingAndStreamedCommandsDoNotHoldFlushDbGate:'
               'ListE2eTest.StreamBlockingRegistryBroadcastsAndKeepsGroupFifo:'
               'ListE2eTest.DisconnectCancelsActiveBlockingWait:'
               'ListE2eTest.PipelineFlushesRepliesBeforeBlockingCommand:'
               'CollectionE2eTest.SortedSetGeoAndStreamCommandsRecover')
    run('blocking-tests', [str(B / 'lavik_list_e2e_test'), str(binary), '--gtest_filter=' + filters,
                          '--gtest_output=json:' + str(W / f'stream-followup-{label}-blocking-tests.json')])
    run('pubsub-tests', [str(B / 'lavik_pubsub_e2e_test'), str(binary)])
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == version['sha256']
    versions[label] = version
    (W / 'stream-followup-validation-progress.json').write_text(json.dumps(versions, indent=2) + '\n')
output.write_text(json.dumps(versions, indent=2) + '\n')
print('ALL_STREAM_FOLLOWUP_NATIVE_TESTS_PASS', time.time(), flush=True)
