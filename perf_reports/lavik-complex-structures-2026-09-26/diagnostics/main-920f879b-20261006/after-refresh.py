"""Prepare and audit completed report artifacts; publishing remains explicit."""
from pathlib import Path
import json,subprocess,time
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
launch=json.loads((W/'launch.json').read_text());stat=Path('/proc')/str(launch['pid'])/'stat'
while stat.exists():
 try:
  fields=stat.read_text().split()
  if fields[21]!=str(launch['generation']) or fields[2]=='Z':break
 except FileNotFoundError:break
 time.sleep(10)
assert 'ALL_MAIN_GRIDS_AND_IMPORTS_COMPLETE' in (W/'main-refresh-driver.log').read_text()
for name,args in [('render-main-refresh.py',[]),('build-main-gap-summary.py',[str(R)]),('finalize-report.py',[]),('audit-current.py',[str(R)]),('finalize-report.py',[]),('prepare-main-evidence.py',[])]:
 print('START',name,time.time(),flush=True)
 subprocess.run(['python3',str(W/name),*args],check=True)
 print('COMPLETE',name,time.time(),flush=True)
print('ALL_MAIN_ANALYSIS_COMPLETE',flush=True)
