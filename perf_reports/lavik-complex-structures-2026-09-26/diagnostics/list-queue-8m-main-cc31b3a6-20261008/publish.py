from pathlib import Path
import hashlib,importlib.util,json,re,shutil,subprocess
W=Path(__file__).parent
P=Path('/mnt/dev/lavik-report-c55e52c9-20261008')
REL=Path('perf_reports/lavik-complex-structures-2026-09-26');ROOT=P/REL
R=Path('/mnt/dev/lavik-complex-refresh-20261004')/REL
D=ROOT/'diagnostics/list-queue-8m-main-cc31b3a6-20261008'
assert not subprocess.check_output(['git','-C',str(P),'status','--porcelain'])
assert not D.exists()
paths=set()
def copy(src,dest):
 assert src.is_file() and src.stat().st_size<95*1024**2
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
 assert hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256(dest.read_bytes()).digest()
 paths.add(dest)
experiments=[('combined',Path('/mnt/dev/lavik-rpush-lpop-20261008')),('push-only',Path('/mnt/dev/lavik-rpush-only-20261008')),('pop-only',Path('/mnt/dev/lavik-lpop-only-20261008'))]
allrows=[]
for name,source in experiments:
 assert json.loads((source/'audit.json').read_text())['passed']
 assert json.loads((source/'host-final.json').read_text())['no_servers']
 for src in source.iterdir():
  if src.is_file() and src.suffix in ['.py','.json','.jsonl','.log','.txt','.c','.csv']:
   copy(src,D/name/src.name)
 rows=json.loads((source/'pairs.json').read_text())+json.loads((source/'profiles.json').read_text())
 if (source/'main-repeats.json').exists():rows+=json.loads((source/'main-repeats.json').read_text())
 allrows+=rows
 for row in rows:
  raw=Path(row['raw']);assert raw.is_relative_to(R/'raw')
  result=json.loads(next(raw.glob('*.result.json')).read_text());assert result==row['result'] and result['command_audit']['passed']
  client=json.loads(next(raw.glob('*.client.json')).read_text());assert client['errors']==0
  assert sum(x['count'] for x in client['commands'].values())==result['requests']
  for key,c in client['key_counts'].items():assert result['bounded']['all_final_counts'][key]==8192+c['first']-c['second']
  for src in raw.rglob('*'):
   if not src.is_file() or src.suffix not in ['.json','.txt','.log']:continue
   if any(p.name.endswith('.perf') for p in src.parents if p!=raw) and src.name.startswith(('stacks-','physical-')):continue
   copy(src,ROOT/src.relative_to(R))
for src in W.iterdir():
 if src.is_file() and src.name not in ['publish-paths.json','publication.json'] and src.suffix in ['.md','.py','.json','.patch','.csv']:copy(src,D/src.name)
old=ROOT/'diagnostics/pr289-c8f128dc-20261008/README.md'
text=old.read_text();first,rest=text.split('\n',1)
update='\n> 合并状态补充（2026-10-08）：#289 已合并为 main `cc31b3a6`，其代码树与下文测试的 `c8f128dc` 相同。下文保留原始 PR/base 测量口径；合并后 8 MiB RPUSH/LPOP 的复测与三种优化尝试见 [专项报告](../list-queue-8m-main-cc31b3a6-20261008/README.md)。\n'
assert '合并状态补充' not in text
old.write_text(first+'\n'+update+rest);paths.add(old)
m=json.loads((ROOT/'current-main.json').read_text());link='diagnostics/list-queue-8m-main-cc31b3a6-20261008/README.md'
m['notes']['zh']+=f' · #289 已合并为 main `cc31b3a6`；[8 MiB RPUSH/LPOP：合并后复测及三种优化尝试]({link})（专项测试，未替换全量曲线；候选均因性能取舍未提 PR）。'
m['notes']['en']+=f' · #289 is merged as main `cc31b3a6`; [8 MiB RPUSH/LPOP: merged-main retest and three optimization experiments]({link}) (focused tests; full curves retained; no candidate PR due to throughput/tail-latency tradeoffs).'
(ROOT/'current-main.json').write_text(json.dumps(m,indent=2)+'\n');paths.add(ROOT/'current-main.json')
spec=importlib.util.spec_from_file_location('plot',ROOT/'plot_current_main.py');plot=importlib.util.module_from_spec(spec);spec.loader.exec_module(plot)
for zh,name in [(True,'README.zh-CN.md'),(False,'README.md')]:
 (ROOT/name).write_text(plot.readme(m,zh));paths.add(ROOT/name)
index=D/'evidence-index.json'
index.write_text(json.dumps({'scope':'Merged main cc31b3a6 versus three candidate variants; 18 clean paired observations, 3 exploratory main observations, 6 separate perf observations.','observations':len(allrows),'audited_commands_including_perf':sum(r['result']['requests'] for r in allrows),'files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths)]},indent=2)+'\n');paths.add(index)
# Validate links in the changed Markdown, excluding remote URLs and anchors.
links=0
for p in paths:
 if p.suffix!='.md':continue
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' in target or target.startswith('#'):continue
  target=target.split('#',1)[0]
  assert (p.parent/target).exists(),(p,target)
  links+=1
(W/'publish-paths.json').write_text(json.dumps([str(p.relative_to(P)) for p in sorted(paths)],indent=2)+'\n')
print('PUBLICATION_PREPARED',len(paths),'files',sum(p.stat().st_size for p in paths),'bytes',links,'links')
