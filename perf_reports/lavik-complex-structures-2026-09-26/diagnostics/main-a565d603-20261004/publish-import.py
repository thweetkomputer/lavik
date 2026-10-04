from pathlib import Path
import json,shutil,subprocess,sys
W=Path(__file__).parent;REPO=Path('/mnt/dev/lavik-complex-refresh-20261004');R=REPO/'perf_reports/lavik-complex-structures-2026-09-26';REL=R.relative_to(REPO)
v=json.loads((W/'versions.json').read_text())['main'];kind,field=sys.argv[1:];field=int(field)
tag=f'main{v["commit"][:8]}-import-{kind}-1048576-k50000-f{field}-20261004'
raw=R/'raw'/('lavik-'+tag)
assert json.loads((raw/'server-exit.json').read_text())['code']==0
assert json.loads((raw/'complete.json').read_text())['failures_total']==0
proof=json.loads(next(raw.glob('provenance-*.json')).read_text());assert proof['source_commit']==v['commit'] and proof['sha256']==v['sha256']
p=R/'current-imports.json';m=json.loads(p.read_text());row=next(x for x in m['plots'] if x['kind']==kind and x['field']==field)
row['main']={'tag':tag,'commit':v['commit'],'sha256':v['sha256'],'fresh':True};p.write_text(json.dumps(m,indent=2)+'\n')
D=R/'diagnostics'/('main-'+v['commit'][:8]+'-20261004')
for f in [W/(tag+'-host.json'),W/'run-import.py',W/'publish-import.py']:shutil.copyfile(f,D/f.name)
subprocess.run(['/mnt/dev/peer-bench/release-retest-2026-09-17/analysis-venv/bin/python',str(R/'plot_current_main.py'),'--condition','imports-only'],cwd=REPO,check=True)
subprocess.run(['/mnt/dev/peer-bench/release-retest-2026-09-17/analysis-venv/bin/python',str(W/'audit-current.py')],cwd=REPO,check=True)
subprocess.run(['git','add','-u','--',str(REL)],cwd=REPO,check=True)
subprocess.run(['git','add','--',*[str(p.relative_to(REPO)) for p in [*raw.glob('*.json'),*D.glob('*')] if p.is_file()]],cwd=REPO,check=True)
subprocess.run(['/tmp/lavik-precommit-env/bin/pre-commit','run'],cwd=REPO,check=True)
subprocess.run(['git','diff','--cached','--check'],cwd=REPO,check=True)
subprocess.run(['git','commit','-m',f'perf: refresh main {v["commit"][:8]} batched {kind} import {field}B'],cwd=REPO,check=True)
subprocess.run(['git','push','https://github.com/thweetkomputer/lavik','HEAD:refs/heads/bench/complex-structures-2026-09-26'],cwd=REPO,check=True)
print('PUBLISHED_IMPORT',kind,field,flush=True)
