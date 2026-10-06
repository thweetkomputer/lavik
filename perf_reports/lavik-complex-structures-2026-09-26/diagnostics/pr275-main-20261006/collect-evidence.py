"""Collect the complete rebased Stream comparison without altering host-state files."""
from pathlib import Path
import json,hashlib,shutil
W=Path(__file__).parent
REPO=Path('/mnt/dev/lavik-complex-refresh-20261004')
R=REPO/'perf_reports/lavik-complex-structures-2026-09-26'
D=R/'diagnostics/pr275-main-20261006'
assert 'ALL_PR275_REBASED_MEASUREMENTS_COMPLETE' in (W/'chain.log').read_text()
data=json.loads((W/'pr275-rebased-repeats.json').read_text())
assert len(data['rows'])==60
summary=json.loads((W/'complete-summary.json').read_text());assert summary['observations']==60
D.mkdir(exist_ok=True);paths=set()
# Keep the initial rebased CI failure and its precise fixture repair alongside
# the final evidence. Logs are data: retain them without whitespace rewriting.
for p in W.iterdir():
 if not p.is_file() or p.suffix not in ['.py','.json','.log','.txt']:continue
 if p.name in ['prepare-runners.py','publish-paths.json'] or p.name.startswith('pr-'):continue
 shutil.copyfile(p,D/p.name);paths.add(D/p.name)
for name in ['full-ci.json.eccea5c7','current-ci.json.eccea5c7','watch-ci.log.eccea5c7']:
 p=W/name;shutil.copyfile(p,D/name);paths.add(D/name)
tags={x['tag'] for x in data['rows']}|{x['tag'] for x in data['seeds']}
for tag in tags:
 raw=R/'raw'/('lavik-'+tag)
 assert json.loads((raw/'server-exit.json').read_text())['code']==0
 assert json.loads((raw/'complete.json').read_text())['failures_total']==0
 for p in raw.rglob('*'):
  if p.is_file() and p.suffix in ['.json','.txt','.log','.prom']:paths.add(p)
index={'scope':'60 clean observations, three paired rounds against main d88a5e8f, final candidate fd2972b0; both production binaries built and tested afresh. Original rebased-head Python fixture failures retained. Historical pre-rebase performance and recovery failures remain in the older Stream report.','files':[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths)]}
(D/'evidence-index.json').write_text(json.dumps(index,indent=2)+'\n');paths.add(D/'evidence-index.json')
(W/'publish-paths.json').write_text(json.dumps([str(p.relative_to(REPO)) for p in sorted(paths)],indent=2)+'\n')
print('Collected',len(paths),'files; publication remains explicit.')
