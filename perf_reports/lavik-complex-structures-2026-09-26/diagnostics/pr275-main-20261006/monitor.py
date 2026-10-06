from pathlib import Path
import json,time
W=Path(__file__).parent
p=W/'pr275-rebased-repeats.json';d=json.loads(p.read_text()) if p.exists() else {'rows':[]}
lines=(W/'repeat-driver.log').read_text().splitlines()
starts=[line.split()[1] for line in lines if line.startswith('START ')]
tag=starts[-1] if starts else None
log=W/(tag+'.log') if tag else None
print(json.dumps({'utc':time.strftime('%H:%M:%S',time.gmtime()),'points':len(d['rows']),'expected':60,'current':tag,'phase':log.read_text().splitlines()[-1:] if log and log.exists() else [],'chain':(W/'chain.log').read_text().splitlines()[-1:]}))
for base,file,label in [(W,'current-ci.json','275'),(Path('/mnt/dev/lavik-hashset-write-20261006'),'pr285-current-ci.json','285')]:
 ci=json.loads((base/file).read_text());print(json.dumps({'pr':label,'status':ci['status'],'conclusion':ci['conclusion'],'success':sum(j['conclusion']=='success' for j in ci['jobs']),'running':sum(j['status']=='in_progress' for j in ci['jobs']),'queued':sum(j['status']=='queued' for j in ci['jobs']),'failed':[(j['name'],j['conclusion']) for j in ci['jobs'] if j['conclusion'] not in ['','success']]}))
