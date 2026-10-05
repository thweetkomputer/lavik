"""Summarize completed Hash/Set perf self reports and command-window counters."""
from collections import defaultdict
from pathlib import Path
import argparse,hashlib,json,re
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--profiles',type=Path,required=True)
p.add_argument('--versions',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();profiles=json.loads(a.profiles.read_text());versions=json.loads(a.versions.read_text())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def metrics(path):
 return {line.rsplit(' ',1)[0]:float(line.rsplit(' ',1)[1]) for line in path.read_text().splitlines() if line and not line.startswith('#')}
def info(path):return dict(line.split(':',1) for line in path.read_text().splitlines() if ':' in line and not line.startswith('#'))
outputs={}
for label,profile in profiles['profiles'].items():
 version=versions[label.split('-')[0]];original=profile['version']
 assert (version['commit'],version['sha256'])==(original['commit'],original['sha256'])
 directory=Path(profile['directory']);raw=directory.parent
 assert json.loads((raw/'complete.json').read_text())['failures_total']==0
 assert json.loads((raw/'server-exit.json').read_text())['code']==0
 proof=json.loads(next(raw.glob('provenance-*.json')).read_text())
 assert proof['source_commit']==version['commit'] and proof['sha256']==version['sha256']
 result_path,=directory.glob('*.result.json');result=json.loads(result_path.read_text())
 kind=result['type'];assert kind in ('hash','set') and result['seconds']==30 and result['connections']==320
 commands=['hset'] if kind=='hash' else ['sadd','srem']
 assert result['operation']==('HSET' if kind=='hash' else 'SADD_SREM')
 prefix=f"{kind}-{result['logical_bytes']}-{result['field_bytes']}"
 before_cards=json.loads((raw/(prefix+'.validated.json')).read_text())['sample_cardinalities']
 after_cards=json.loads((raw/(prefix+'.after.json')).read_text())['sample_cardinalities']
 assert set(before_cards)==set(after_cards)=={f'complex_{i}' for i in range(1,result['keys']+1)}
 assert set(before_cards.values())=={result['entries_per_key']}
 assert all(after_cards[k] in ([v] if kind=='hash' else [v,v+1]) for k,v in before_cards.items())
 totals=defaultdict(float);workers=[];total=0
 for tid in profile['attached_tids']:
  path=directory/f'self-{tid}.txt';report=path.read_text();event=re.search(r'Event count \(approx\.\): (\d+)',report)
  if event is None:
   assert (directory/f'stacks-{tid}.txt').stat().st_size==0
   workers.append({'tid':tid,'event_count':0,'empty_stack_file':True,'report_sha256':digest(path)});continue
  count=int(event[1]);assert count>0;total+=count
  lost=int(re.search(r'Total Lost Samples: (\d+)',report)[1]);assert lost==0
  reported=0;symbols=[]
  for line in report.splitlines():
   match=re.match(r'\s*([0-9.]+)%\s+\[(.)\]\s+(.*?)\s{2,}',line)
   assert match or not line.strip() or line.startswith('#'),(path,line)
   if match:
    percentage=float(match[1]);reported+=percentage;totals[(match[2],match[3])]+=count*percentage
    symbols.append({'mode':match[2],'symbol':match[3],'percent':percentage})
  assert 0<reported<101
  workers.append({'tid':tid,'event_count':count,'reported_percent':reported,'lost_samples':lost,'self_symbols':symbols,'report_sha256':digest(path)})
 assert total>0
 before,after=metrics(directory/'before.prom'),metrics(directory/'after.prom')
 names=[f'lavik_command_calls_total{{command="{c}"}}' for c in commands]
 # The restored population is restarted before measurement. These write
 # command counters are absent before their first invocation; storage
 # counters still must exist at both boundaries.
 assert not any(n in before for n in names)
 calls={c:after[n]-before.get(n,0) for c,n in zip(commands,names)}
 completed=sum(calls.values());assert completed==result['requests']>0
 counters={f'{operation}_{family}':f'lavik_storage_io_{family}_total{{operation="{operation}"}}' for family in ['operations','bytes'] for operation in ['read','write']}
 delta={k:after[n]-before[n] for k,n in counters.items()};assert min(delta.values())>=0
 ibpath,=directory.glob('*.info-before.txt');iapath,=directory.glob('*.info-after.txt');ib,ia=info(ibpath),info(iapath)
 for c in commands:
  key='cmdstat_'+c;assert key not in ib
  values=dict(item.split('=',1) for item in ia[key].split(','));assert int(values['calls'])==calls[c]
  assert int(values['failed_calls'])==int(values['rejected_calls'])==0
 for field in ['run_id','process_id','worker_threads','rdb_last_save_time']:
  if field in ib:assert ib[field]==ia[field]
 counter_fields=['tx_commit_batches','tx_commit_changes','tx_commit_backpressure_waits','tx_fastpath_runs','tx_queued_runs','tx_schedule_retries']
 info_delta={k:int(ia[k])-int(ib[k]) for k in counter_fields if k in ib and k in ia};assert min(info_delta.values())>=0
 outputs[label]={'version':{k:version[k] for k in ['commit','binary','sha256','bycorf_commit']},
  'original_recorded_bycorf_commit':original['bycorf_commit'],'profile_directory':str(directory),'diagnostic_result':result,
  'workers':workers,'total_approx_event_count':total,'reported_coverage_percent':sum(totals.values())/total,
  'self_symbols':[{'mode':m,'symbol':s,'percent':v/total} for (m,s),v in sorted(totals.items(),key=lambda x:-x[1])],
  'completed_commands':calls,'counter_delta':delta,'io_per_completed_command':{k:v/completed for k,v in delta.items()},'info_counter_delta':info_delta,
  'evidence_sha256':{str(x.relative_to(raw)):digest(x) for x in [result_path,ibpath,iapath,directory/'before.prom',directory/'after.prom',directory/'profile-provenance.json']}}
 print(label,'coverage',round(outputs[label]['reported_coverage_percent'],4),'io',outputs[label]['io_per_completed_command'],'top',[(s['symbol'],round(s['percent'],3)) for s in outputs[label]['self_symbols'][:10]])
output={'profiles_sha256':digest(a.profiles),'corrected_versions_sha256':digest(a.versions),'profiles':outputs,
 'limits':'Independent diagnostic populations, fixed parent/candidate order; not clean throughput controls. CPU self shares weighted by per-thread approximate task-clock event counts; 0.1% input cutoff and two-decimal rounding leave missing mass unnormalized. Includes polling, background and kernel CPU; zero lost samples does not prove complete unwinding. Command and IO counters cover30seconds, CPU25seconds; do not deriveCPU/command. Process-wide storage includes background and scrape boundary effects; counts are not exact command-owned IO. Set denominator includes no-op requests. Corrected dependency metadata derives from saved CMake provenance; original label is retained, binaries unchanged.'}
a.output.write_text(json.dumps(output,indent=2)+'\n')
