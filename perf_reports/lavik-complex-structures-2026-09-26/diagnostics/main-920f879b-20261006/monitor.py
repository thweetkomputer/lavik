from pathlib import Path
import datetime,json
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
progress=json.loads((W/'main-refresh-progress.json').read_text()) if (W/'main-refresh-progress.json').exists() else []
chain=(W/'main-refresh-driver.log').read_text().splitlines();native=(W/'native-driver.log').read_text().splitlines()
raws=[p for p in (R/'raw').glob('lavik-main920f879b-*') if '-import-' not in p.name]
counts={'ok':sum(len(list(p.glob('*.result.json'))) for p in raws),'errors':sum(len(list(p.glob('*.error.json'))) for p in raws)}
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'grids':len(progress),'expected_grids':28,'points':counts,'phase':chain[-1:]}))
logs=list(W.glob('main-grid-*.log'))+list(W.glob('main-import-*.log'))
if logs:
 p=max(logs,key=lambda p:p.stat().st_mtime);print(p.name,p.read_text(errors='replace').splitlines()[-2:])
else:
 logs=list(W.glob('refresh-main-*.txt'))
 if logs:
  p=max(logs,key=lambda p:p.stat().st_mtime);print(p.name,p.read_text(errors='replace').splitlines()[-2:])
if (W/'current-ci.json').exists() and not (W/'full-ci.json').exists():
 c=json.loads((W/'current-ci.json').read_text());print('CI',c['status'],c['conclusion'],'success',sum(j['conclusion']=='success' for j in c['jobs']),'failed',[(j['name'],j['conclusion']) for j in c['jobs'] if j['conclusion'] and j['conclusion']!='success'])
