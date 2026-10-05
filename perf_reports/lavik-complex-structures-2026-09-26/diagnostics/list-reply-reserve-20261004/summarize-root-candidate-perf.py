"""Validate already decoded candidate perf; do not treat short diagnostics as paired QPS."""
from pathlib import Path
import hashlib,json,re,math
W=Path(__file__).parent
source=W/'grouped-verified-root-candidate-profiles.json';v=json.loads(source.read_text())
assert len(v['rows'])==3 and [r['round'] for r in v['rows']]==[1,2,3]
assert v['script_sha256']==hashlib.sha256((W/'profile-grouped-verified-root-candidate.py').read_bytes()).hexdigest()
assert v['versions']['candidate']['source_head']=='28d7cca498655e02f46407adb65335219b10ee6b'
assert v['versions']['candidate']['binary_sha256']=='3b3dbc5482bf6586b0f06e00d92a6c5e589f58528b13105d01ea3b8a226e5090'
assert v['original_sha256']=='b4e0113cf9b7dcbe03175c5e5665be8589ebef9dbc9c2847adc3cd3010b956ae'
rows=[];files=[];aggregate={}
def io(s):return {a:int(b) for a,b in (line.split(':') for line in s.splitlines())}
def cpu(s):
 fields=s.rsplit(')',1)[1].split();return int(fields[11])+int(fields[12])
for row in v['rows']:
 assert row['success'] and row['server_exit']==0 and row['perf_exit'] in [0,-2,130] and 'error' not in row and 'perf_error' not in row
 assert len(row['operations'])==16
 gets=[op for op in row['operations'] if op['command']=='GET'];assert len(gets)==5
 assert sorted((op['key_bytes'],op['received_payload_bytes']) for op in gets)==sorted([(5009,9437184)]*3+[(6291456,1048576),(9437184,6291456)])
 op=next(op for op in gets if op['key_bytes']==9437184)
 assert op['header']=='$6291456\r\n' and math.isfinite(op['seconds']) and 0<op['seconds']<60
 folder=Path(row['image']).parent
 report=(folder/'self.txt').read_text();log=(folder/'perf-record.log').read_text()
 count=int(re.search(r"# Samples: (\d+)  of event 'task-clock'",report)[1])
 period=int(re.search(r'# Event count \(approx.\): (\d+)',report)[1])
 lost=int(re.search(r'# Total Lost Samples: (\d+)',report)[1])
 assert f'({count} samples)' in log and 'Captured and wrote' in log
 symbols=[]
 for line in report.splitlines():
  if not re.match(r'^\s*[0-9.]+%',line):continue
  m=re.fullmatch(r'\s*([0-9.]+)%\s+(\d+)\s+(\d+)\s+\[([^]]+)\]\s+(.+?)\s+-\s+-\s*',line);assert m,line
  percent,n,p,mode,name=m.groups();n=int(n);p=int(p)
  symbols.append({'symbol':name,'mode':mode,'percent':float(percent),'samples':n,'period':p})
  aggregate[name]=aggregate.get(name,0)+p
 assert sum(x['samples'] for x in symbols)==count and sum(x['period'] for x in symbols)==period
 a,b=io(op['proc_io_before']),io(op['proc_io_after']);delta={k:b[k]-a[k] for k in a};assert all(x>=0 for x in delta.values())
 assert all(Path(row['decode_commands'][name][-1]).name=='long-key.perf' for name in ['self.txt','stacks.txt'])
 for name in ['self.txt','self.txt.stderr','stacks.txt','stacks.txt.stderr','server.log','perf-record.log','operation-progress.json','progress.json']:
  path=folder/name;assert path.exists() and path.stat().st_size<2*1024**2
  if name in ['self.txt','stacks.txt','perf-record.log']:assert path.stat().st_size>0
  files.append({'round':row['round'],'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'publish':name!='stacks.txt'})
 rows.append({'round':row['round'],'get_seconds':op['seconds'],'received_payload_bytes':op['received_payload_bytes'],'process_io_delta':delta,'process_cpu_seconds':(cpu(op['proc_stat_after'])-cpu(op['proc_stat_before']))/v['clock_ticks_per_second'],'samples':count,'perf_task_clock_seconds':period/1e9,'lost_samples':lost,'reported_percent_sum':sum(x['percent'] for x in symbols),'self_symbols':symbols,'perf_sha256':row['perf_sha256'],'recorder_exit':row['perf_exit']})
total=sum(aggregate.values());output={'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_head':v['versions']['candidate']['source_head'],'binary_sha256':v['versions']['candidate']['binary_sha256'],'rows':rows,'total_samples':sum(r['samples'] for r in rows),'combined_self_by_period':[{'symbol':k,'period':p,'percent':100*p/total} for k,p in sorted(aggregate.items(),key=lambda x:-x[1])],'files':files,'limitations':['Candidate-only diagnostic, not a matched contemporaneous baseline or a QPS result.','Each capture has only22-23samples; absent symbols are not proof of zero work.','Zero lost samples does not establish complete unwinding.','Process IO and CPU include background work; perf includes recorder startup overlap.','This does not explain PR267 original SET timeout or validate rebased head2c94e9da.']}
(W/'grouped-root-candidate-perf-summary.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps({'samples':output['total_samples'],'rows':[{k:r[k] for k in ['round','get_seconds','process_cpu_seconds','samples','lost_samples','process_io_delta']} for r in rows]},indent=2))
