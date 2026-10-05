"""Correct the old live validator's dependency label using its saved CMake caches."""
from pathlib import Path
from datetime import datetime,timezone
import copy,hashlib,json,shutil,subprocess
from native_build_provenance import native_dependency_provenance
W=Path(__file__).resolve().parent
assert 'ALL_COMBINED_NATIVE_TESTS_PASS' in (W/'combined-native-driver.log').read_text()
original_path=W/'combined-native-versions.json'
original=json.loads(original_path.read_text());assert set(original)=={'main','combined'}
output=W/'combined-native-versions-corrected.json';evidence_path=W/'combined-native-dependency-correction.json'
assert not output.exists() and not evidence_path.exists()
corrected=copy.deepcopy(original);records={}
for label,head in [('main','4610d6077e8e32d59639a5ee88dbe8cbd305aab2'),('combined','78e29277618f4ef40ccefab0930cbab667a0a40e')]:
    value=corrected[label];assert value['commit']==head
    assert value['bycorf_commit']==head, 'inspect any different provenance failure before correcting'
    assert all(t['tests']>0 and t['failures']==0 for t in value['tests'].values())
    assert value['pubsub_exit']==0
    cache=W/f'combined-{label}-CMakeCache.txt';assert cache.exists()
    saved=W/'combined-cmake-provenance-caches'/label;saved.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(cache,saved/'CMakeCache.txt')
    resolution=native_dependency_provenance(saved)
    assert resolution['bycorf_commit']=='62509c93d40c2480f5046b71454db6cf95801b04'
    source=resolution['bycorf_source_repo']
    reflog=subprocess.check_output(['git','-C',source,'reflog','-1','--date=iso','--format=%H %gd %gs'],text=True).strip()
    status=subprocess.run(['git','-C',source,'diff','--quiet','--ignore-submodules=all','HEAD'],check=False)
    assert status.returncode in [0,1]
    value['bycorf_commit_recorded']=value['bycorf_commit']
    value.update(resolution)
    value['dependency_correction']='Saved CMake source path plus post-validation Git/reflog observation; original version label retained. Not an independent build-time snapshot; nested dirty state preserved.'
    assert value['sha256']==original[label]['sha256'] and value['drivers']==original[label]['drivers']
    records[label]={'lavik_commit':head,'recorded_bycorf_commit':original[label]['bycorf_commit'],
                    'resolution':resolution,'cache_source':cache.name,'cache_sha256':hashlib.sha256(cache.read_bytes()).hexdigest(),
                    'head_reflog_latest':reflog,'top_level_tracked_changes_excluding_dirty_submodules':status.returncode!=0,
                    'binary_sha256_unchanged':value['sha256'],'driver_sha256_unchanged':{k:v['sha256'] for k,v in value['drivers'].items()}}
evidence={'observed_at':datetime.now(timezone.utc).isoformat(),
          'error':'The validator was already running when its source file was fixed; its loaded code queried empty source_repo/bycorf and Git returned the enclosing Lavik commit.',
          'original_manifest':original_path.name,'original_manifest_sha256':hashlib.sha256(original_path.read_bytes()).hexdigest(),
          'scope_limit':'Uses each archived production CMake cache and a later dependency checkout observation. Does not claim recursive cleanliness or replace build-time source snapshots. No binary, test, driver, compiler option or measurement changed; exact binary hashes are checked again under the host lock by performance drivers.',
          'versions':records}
evidence_path.write_text(json.dumps(evidence,indent=2)+'\n')
output.write_text(json.dumps(corrected,indent=2)+'\n')
print('COMBINED_DEPENDENCY_LABELS_CORRECTED',output)
