from pathlib import Path
import json,subprocess,time
W=Path(__file__).parent
while True:
 r=json.loads(subprocess.check_output(['gh','run','view','37452841525','--repo','eloqdata/lavik','--json','headSha,status,conclusion,jobs,url']))
 assert r['headSha']=='eccea5c79d4e71e39ae1e1217aecb226f4ff75e9'
 (W/'current-ci.json').write_text(json.dumps(r,indent=2)+'\n')
 print(time.time(),r['status'],r['conclusion'],[(x['name'],x['conclusion']) for x in r['jobs'] if x['conclusion'] and x['conclusion']!='success'],flush=True)
 if r['status']=='completed':
  (W/'full-ci.json').write_text(json.dumps(r,indent=2)+'\n')
  break
 time.sleep(60)
