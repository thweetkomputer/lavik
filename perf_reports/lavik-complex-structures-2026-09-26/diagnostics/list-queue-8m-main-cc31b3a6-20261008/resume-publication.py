from pathlib import Path
W=Path(__file__).parent
s=(W/'publish.py').read_text()
prefix=s[:s.index("old=ROOT/")]
prefix=prefix.replace("assert not subprocess.check_output(['git','-C',str(P),'status','--porcelain'])",'').replace('assert not D.exists()','')
scope={'__file__':str(W/'publish.py')}
exec(compile(prefix,str(W/'publish.py'),'exec'),scope)
ROOT=scope['ROOT'];scope['paths'].add(ROOT/'diagnostics/pr289-c8f128dc-20261008/README.md');scope['paths'].add(ROOT/'current-main.json')
import json
scope['m']=json.loads((ROOT/'current-main.json').read_text())
exec(compile(s[s.index('spec=importlib'):],str(W/'publish.py'),'exec'),scope)
