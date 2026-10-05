"""Verify the completed focused overwrite diagnostic without changing CI-failure claims."""
from pathlib import Path
import hashlib,json,math,statistics
W=Path(__file__).parent
source=W/'pr267-overwrite-diagnostics.json';j=json.loads(source.read_text())
driver=W/'diagnose-pr267-overwrites.py'
assert hashlib.sha256(driver.read_bytes()).hexdigest()==j['script_sha256']
assert j['original_sha256']=='b4e0113cf9b7dcbe03175c5e5665be8589ebef9dbc9c2847adc3cd3010b956ae'
assert [(r['version'],r['round']) for r in j['rows']]==[('main',1),('candidate',1),('candidate',2),('main',2)]
heads={'main':'19496654cc43b21df11fb59be60e174dc4c89dbc','candidate':'343e951e3341593cc46b2cfae42f7d8f9b26304e'}
for label,head in heads.items():assert j['versions'][label]['source_head']==head
assert j['versions']['main']['test_sha256']==j['versions']['candidate']['test_sha256']
files=[];summary=[]
for row in j['rows']:
 assert row['success'] and 'error' not in row
 assert [p['workers'] for p in row['phases']]==[2,3]
 folder=Path(row['image']).parent;commands=[];writes=[]
 for phase in row['phases']:
  assert phase['success'] and phase['server_exit']==0 and 'error' not in phase and 'inflight' not in phase
  workers=phase['workers'];argv=phase['argv'];assert argv[0]==j['versions'][row['version']]['binary']
  assert argv[argv.index('--threads')+1]==str(workers) and argv[argv.index('--data-file')+1]==row['image']
  expected=[(command,key) for key in range(3) for command in (['STRLEN','SET','GET'] if workers==2 else ['GET'])]
  assert [(o['command'],o['key_index']) for o in phase['operations']]==expected
  for op in phase['operations']:
   assert op['key_bytes']==5009 and math.isfinite(op['seconds']) and op['seconds']>=0
   assert set(op['proc_before'])==set(op['proc_after'])=={'io','stat','status'}
   commands.append(op['command'])
   if op['command']=='SET':writes.append(op['seconds'])
  for name in [f'server-{workers}.log',f'info-{workers}-ready.txt',f'info-{workers}-after.txt']:
   path=folder/name;assert path.exists() and 0<path.stat().st_size<3*1024**2
   files.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 assert commands.count('STRLEN')==3 and commands.count('SET')==3 and commands.count('GET')==6
 summary.append({'version':row['version'],'round':row['round'],'operations':len(commands),'overwrites':3,'immediate_readbacks':3,'restart_readbacks':3,'clean_exits':2,'set_seconds':writes})
result={'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'driver_sha256':j['script_sha256'],'original_image_sha256':j['original_sha256'],'rows':summary,'totals':{'conditions':4,'operations':48,'overwrites':12,'readbacks':24,'restart_readbacks':12,'clean_exits':8},'retained_files':files,'limitation':'Focused changed-history diagnostic passes on both old exact CI artifacts; not a reproduction or resolution of the original full CI SET timeout, and not evidence for rebased PR267 head or QPS.'}
(W/'pr267-overwrite-diagnostic-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['totals']))
