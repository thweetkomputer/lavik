"""Reproduce the recovery timeout with exact amd64 CI binaries on private files."""
from pathlib import Path
import hashlib
import json
import os
import resource
import signal
import subprocess
import time
import zipfile

W = Path(__file__).parent
output = W / 'pr267-extent-native-ci-reproductions.json'
assert not output.exists(), 'inspect previous reproduction before restarting'
# A large artifact download or decompression must not overlap clean measurements.
from host_execution_lock import acquire_host
_execution_lock = acquire_host('extent-ci-reproduction')

root = W / 'pr267-extent-ci-repro'
root.mkdir()
versions = {}
for label, run_id, artifact_id, expected in [
    ('main', 37237724710, 11316029042, '19496654cc43b21df11fb59be60e174dc4c89dbc'),
    ('candidate', 37241591043, 11317164871, '343e951e3341593cc46b2cfae42f7d8f9b26304e'),
]:
    run = json.loads(subprocess.check_output(['gh', 'run', 'view', str(run_id), '--repo', 'eloqdata/lavik', '--json', 'headSha,url']))
    assert run['headSha'] == expected
    metadata = json.loads(subprocess.check_output(['gh', 'api', f'repos/eloqdata/lavik/actions/artifacts/{artifact_id}']))
    assert metadata['name'] == 'ci-build-amd64' and not metadata['expired']
    assert metadata['workflow_run']['id'] == run_id
    directory = root / label
    directory.mkdir()
    archive = directory / 'ci-build.zip'
    print('DOWNLOAD', label, artifact_id, time.time(), flush=True)
    with archive.open('wb') as f:
        subprocess.run(['gh', 'api', f'repos/eloqdata/lavik/actions/artifacts/{artifact_id}/zip'], stdout=f, check=True)
    with zipfile.ZipFile(archive) as z:
        assert z.namelist() == ['ci-build.tar.zst'], z.namelist()
        z.extract('ci-build.tar.zst', directory)
    subprocess.run(['tar', '--zstd', '-xf', str(directory / 'ci-build.tar.zst'), '-C', str(directory),
                    'build_ci/lavik', 'build_ci/lavik_extent_recovery_e2e_test', 'build_ci/ci-build-bundle.json'], check=True)
    build = directory / 'build_ci'
    manifest = json.loads((build / 'ci-build-bundle.json').read_text())
    assert manifest['architecture'] == 'x86_64'
    # PR Actions may package the synthetic merge revision. Require its tree to
    # equal the requested main-integrated head, and retain both identities.
    built = json.loads(subprocess.check_output(['gh', 'api', f'repos/eloqdata/lavik/git/commits/{manifest["revision"]}']))
    source = json.loads(subprocess.check_output(['gh', 'api', f'repos/eloqdata/lavik/git/commits/{expected}']))
    assert built['tree']['sha'] == source['tree']['sha'], (label, manifest, built['tree'], source['tree'])
    binary = build / 'lavik'
    test = build / 'lavik_extent_recovery_e2e_test'
    versions[label] = {'source_head': expected, 'built_revision': manifest['revision'], 'tree': built['tree']['sha'],
                       'ci_run': run['url'], 'artifact_id': artifact_id, 'binary': str(binary), 'test': str(test),
                       'binary_sha256': hashlib.file_digest(binary.open('rb'), 'sha256').hexdigest(),
                       'test_sha256': hashlib.file_digest(test.open('rb'), 'sha256').hexdigest()}
    (directory / 'provenance.json').write_text(json.dumps(versions[label], indent=2) + '\n')

soft, _ = resource.getrlimit(resource.RLIMIT_MEMLOCK)
assert soft == resource.RLIM_INFINITY or soft >= 1024**3, ('insufficient memlock', soft)
results = []
for round_, labels in enumerate([['main', 'candidate'], ['candidate', 'main'], ['main', 'candidate']], 1):
    for label in labels:
        v = versions[label]
        data = root / f'{label}-round{round_}'
        data.mkdir()
        env = dict(os.environ, LAVIK_TEST_DATA_DIR=str(data))
        print('START_REPRO', label, round_, time.time(), flush=True)
        start = time.time()
        # Preserve the original internal socket and shutdown bounds and the
        # suite's 600-second outer timeout. No concurrent tests or perf.
        with (data / 'driver.log').open('w') as log:
            child = subprocess.Popen([v['test'], v['binary']], env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = child.wait(timeout=600)
            except subprocess.TimeoutExpired:
                code = 'outer_timeout'
            finally:
                # Own the entire fixture process group, including a server
                # child if the outer timeout bypasses C++ destructors.
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
        record = {'version': label, 'round': round_, 'exit_code': code, 'seconds': time.time() - start, 'directory': str(data),
                  'retained_files': [str(p) for p in data.iterdir()]}
        results.append(record)
        output.write_text(json.dumps({'versions': versions, 'rows': results, 'method': 'Exact amd64 CI test/server binaries, verified source-tree identity, three alternating pairs on independent private file devices; original internal timeouts and 600-second CTest bound. No performance measurements overlap. Stop at first failure and retain its image/log for diagnosis. Passing here does not identify the cause of the original CI timeout.'}, indent=2) + '\n')
        print('REPRO_RESULT', record, flush=True)
        assert code == 0, 'reproduced failure: inspect retained image and log before any retry'
print('ALL_PR267_EXTENT_CI_REPRODUCTIONS_PASS', time.time(), flush=True)
