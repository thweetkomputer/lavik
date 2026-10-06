"""Collect reviewed Hash/Set evidence; publication and conclusions stay explicit."""
from pathlib import Path
import hashlib,json,shutil
W=Path(__file__).parent
REPO=Path('/mnt/dev/lavik-complex-refresh-20261004')
R=REPO/'perf_reports/lavik-complex-structures-2026-09-26'
D=R/'diagnostics/hashset-routing-overlay-20261006'
assert 'ALL_MATCHED_SEED_MEASUREMENTS_COMPLETE' in (W/'matched-seed-chain.log').read_text()
observations=json.loads((W/'matched-seed-repeats.json').read_text())
assert len(observations['rows'])==108
assert json.loads((W/'matched-seed-command-audit.json').read_text())['points']==108
versions=json.loads((W/'validated-versions.json').read_text())
ci=json.loads((W/'candidate-current-ci.json').read_text())
assert ci['headSha']==versions['candidate']['commit'] and ci['conclusion']=='success'
assert len(ci['jobs'])==17 and all(j['conclusion']=='success' for j in ci['jobs'])
D.mkdir(exist_ok=True);paths=set()
names=['audit-final.py','matched-seed-final-audit.json','matched-seed-startup-repair.json','validated-versions.json','matched-seed-protocol.json','matched-seed-repeats.json','matched-seed-summary.json','matched-seed-command-audit.json','matched-seed-profiles.json','matched-seed-perf-summary.json','matched-seed-attribution.json','candidate-current-ci.json','native-driver.log','matched-seed-chain.log','repeat-matched-seed-driver.log','profile-matched-seed-driver.log','repeat-matched-seed.py','profile-matched-seed.py','summarize-matched-seed.py','attribute-stacks.py','validate-native.py','fixed-seed-exec.py','fixed-digest-seed.c','run-overlay-controls.py','profile-hash-route-allworkers.py','private-tmp-exec.py','host.py','prepare-evidence.py','overlay-repeats.json','paired-summary.json','command-audit.json','small-set-repeats.json','small-set-paired-summary.json','small-set-command-audit.json','small-set-profiles.json','small-set-perf-summary.json','small-set-perf-attribution.json','small-set-first-pair-counters.json','main-profiles.json','main-summary.json','main-attribution.json','priority-diagnostic-stop.json','paired-protocol.json','small-set-protocol.json','repeat-overlay.py','repeat-small-set.py','profile-small-set.py','profile-main.py','repeat-overlay-driver.log','repeat-small-set-driver.log','profile-small-set-driver.log','profile-main-driver.log']
for prefix in ['candidate-caba8203','candidate-258c216c']:
 names += [p.name for p in W.glob(prefix+'-*.json')]
 names += [p.name for p in W.glob(prefix+'-*.log')]
for name in names:
 assert (W/name).exists(),name
 shutil.copyfile(W/name,D/name);paths.add(D/name)
for source,target in [('validated-versions.json.258c216c','exploratory-versions.json'),('candidate-full-ci.json.258c216c','exploratory-ci.json')]:
 shutil.copyfile(W/source,D/target);paths.add(D/target)
tags=set()
for source in ['matched-seed-repeats.json','overlay-repeats.json','small-set-repeats.json']:
 tags.update(r['tag'] for r in json.loads((W/source).read_text())['rows'])
for source in ['matched-seed-profiles.json','main-profiles.json','small-set-profiles.json']:
 tags.update(r['tag'] for r in json.loads((W/source).read_text())['profiles'].values())
tags |= {'seed-'+tag for tag in tags.copy()}
for tag in sorted(tags):
 raw=R/'raw'/('lavik-'+tag)
 assert json.loads((raw/'server-exit.json').read_text())['code']==0
 assert json.loads((raw/'complete.json').read_text())['failures_total']==0
 for p in raw.rglob('*'):
  if not p.is_file() or p.suffix not in ['.json','.txt','.log','.prom']:continue
  if p.name.startswith('stacks-') and p.stat().st_size:continue
  paths.add(p)
 if not tag.startswith('seed-'):
  p=W/(tag+'.log');assert p.exists(),p
  shutil.copyfile(p,D/p.name);paths.add(D/p.name)
index={'scope':'108 same-seed paired clean observations and four separate same-seed profiles. Earlier54 unique clean observations and four independent-seed profiles retained as exploratory, excluded from matched-seed estimates. Rawperf binaries and nonempty full stacks remain local. Incomplete deliberately interrupted seed is recorded by stop metadata, not a completed observation.','files':[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths)]}
(D/'evidence-index.json').write_text(json.dumps(index,indent=2)+'\n');paths.add(D/'evidence-index.json')
(W/'publish-paths.json').write_text(json.dumps([str(p.relative_to(REPO)) for p in sorted(paths)],indent=2)+'\n')
print('Prepared',len(paths),'files,',sum(p.stat().st_size for p in paths),'bytes; no staging or publication performed.')
