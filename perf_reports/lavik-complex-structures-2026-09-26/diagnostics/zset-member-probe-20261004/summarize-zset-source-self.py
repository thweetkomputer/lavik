"""Combine existing small perf self reports without rereading raw captures."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import re
W=Path(__file__).parent
assert 'ALL_ZSET_SOURCE_REUSE_PROFILES_COMPLETE' in (W/'zset-planner-fixed-profile-driver.log').read_text()
profiles=json.loads((W/'zset-source-reuse-profiles.json').read_text())
assert profiles['profiles'].keys()=={'previous','candidate'}
outputs={}
for label,profile in profiles['profiles'].items():
    directory=Path(profile['directory'])
    totals=defaultdict(float)
    workers=[]
    total=0
    for tid in profile['attached_tids']:
        path=directory/f'self-{tid}.txt'
        report=path.read_text()
        event=re.search(r'Event count \(approx\.\): (\d+)',report)
        if event is None:
            assert (directory/f'stacks-{tid}.txt').stat().st_size==0
            workers.append({'tid':tid,'event_count':0,'empty_stack_file':True,'report_sha256':hashlib.sha256(report.encode()).hexdigest()})
            continue
        count=int(event[1]);total+=count
        lost=int(re.search(r'Total Lost Samples: (\d+)',report)[1])
        assert lost==0
        reported=0
        symbols=[]
        for line in report.splitlines():
            match=re.match(r'\s*([0-9.]+)%\s+\[(.)\]\s+(.*?)\s{2,}',line)
            assert match or not line.strip() or line.startswith('#'), ('unparsed report row',path,line)
            if match:
                percentage=float(match[1]);reported+=percentage
                totals[(match[2],match[3])]+=count*percentage
                symbols.append({'mode':match[2],'symbol':match[3],'percent':percentage})
        # Point workloads spread CPU over many symbols below the input's
        # 0.1% cutoff. Keep missing mass explicit; never renormalize it away.
        assert 0<reported<101,(label,tid,reported)
        workers.append({'tid':tid,'event_count':count,'reported_percent':reported,'lost_samples':lost,'self_symbols':symbols,'report_sha256':hashlib.sha256(report.encode()).hexdigest()})
    assert total>0
    result={'profile':profile,'workers':workers,'total_approx_event_count':total,
            'reported_coverage_percent':sum(totals.values())/total,
            'self_symbols':[{'mode':mode,'symbol':symbol,'percent':weight/total}
                            for (mode,symbol),weight in sorted(totals.items(),key=lambda x:-x[1])],
            'limits':'Approximate event-count-weighted self shares from existing 0.1% threshold, two-decimal reports. Includes polling/background/kernel CPU, not request-exclusive CPU or latency. Zero-sample helper retained. Raw captures not reprocessed; only completed self reports are combined.'}
    def metrics(path):
        return {line.rsplit(' ',1)[0]:float(line.rsplit(' ',1)[1])
                for line in path.read_text().splitlines() if line and not line.startswith('#')}
    before,after=metrics(directory/'before.prom'),metrics(directory/'after.prom')
    command='lavik_command_calls_total{command="zincrby"}'
    counters={f'{operation}_{family}':f'lavik_storage_io_{family}_total{{operation="{operation}"}}'
              for family in ['operations','bytes'] for operation in ['read','write']}
    selected=[command,*counters.values()]
    # Command families omit never-executed commands. The fresh seed uses
    # ZADD, so absent ZINCRBY before its first measurement means zero calls.
    # Storage counters must still exist in both snapshots.
    delta={key:after[key]-(before.get(key,0) if key==command else before[key]) for key in selected}
    assert all(value>=0 for value in delta.values()) and delta[command]>0
    result['counter_delta']=delta
    result['io_per_completed_zincrby']={key:delta[counter]/delta[command] for key,counter in counters.items()}
    result['counter_limits']='Server-wide 30-second metric window includes background work and overlapping commands. CPU window is separate25seconds; do not divide CPU time by this command count. Fresh populations may differ in physical layout; counts are not exact per-request traces or logical page-load counts.'
    outputs[label]=result
    (W/f'zset-source-reuse-{label}-self-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(label,'io',result['io_per_completed_zincrby'],'coverage',result['reported_coverage_percent'],'top',[(v['symbol'],round(v['percent'],3)) for v in result['self_symbols'][:12]])
(W/'zset-source-reuse-self-comparison.json').write_text(json.dumps(outputs,indent=2)+'\n')
