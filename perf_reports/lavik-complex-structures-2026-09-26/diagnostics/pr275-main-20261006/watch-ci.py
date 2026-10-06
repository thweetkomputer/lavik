from pathlib import Path
import json,subprocess,time
W=Path(__file__).parent
while True:
 r=json.loads(subprocess.check_output(['gh','run','view','37457923836','--repo','eloqdata/lavik','--json','headSha,status,conclusion,jobs,url']))
 assert r['headSha']=='fd2972b0f9ea9ccda5d231dd0d4984d9ee1b44e5'
 (W/'current-ci.json').write_text(json.dumps(r,indent=2)+'\n')
 print(time.time(),r['status'],r['conclusion'],[(x['name'],x['conclusion']) for x in r['jobs'] if x['conclusion'] and x['conclusion']!='success'],flush=True)
 if r['status']=='completed':
  (W/'full-ci.json').write_text(json.dumps(r,indent=2)+'\n')
  break
 time.sleep(60)
