from pathlib import Path
import json,subprocess,time
W=Path(__file__).parent
launch=json.loads((W/'launch.json').read_text());stat=Path('/proc')/str(launch['pid'])/'stat'
while stat.exists():
 try:
  fields=stat.read_text().split()
  if fields[21]!=str(launch['generation']) or fields[2]=='Z':break
 except FileNotFoundError:break
 time.sleep(10)
assert 'ALL_PR275_REBASED_MEASUREMENTS_COMPLETE' in (W/'chain.log').read_text()
for argv in [
 ['python3',str(W/'summarize-stream-window.py'),'--scope','all','--input',str(W/'pr275-rebased-repeats.json'),'--output',str(W/'complete-summary.json')],
 ['python3',str(W/'collect-evidence.py')]]:
 subprocess.run(argv,check=True)
print('ALL_PR275_ANALYSIS_COMPLETE',flush=True)
