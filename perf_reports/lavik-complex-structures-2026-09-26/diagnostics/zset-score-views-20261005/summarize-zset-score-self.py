"""Combine existing small perf self reports without rereading raw captures."""
from collections import defaultdict
from pathlib import Path
import json
import re
W=Path(__file__).parent
# Aggregate existing per-thread reports; do not decode raw perf during other jobs.
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input',type=Path,default=W/'zset-score-views-profiles.json')
parser.add_argument('--prefix',default='zset-score-views')
parser.add_argument('--report-root',type=Path,help='Relocate profile paths to a report checkout')
args=parser.parse_args()
assert re.fullmatch(r'[a-z0-9-]+',args.prefix)
profiles=json.loads(args.input.read_text())
outputs={}
for label,profile in profiles['profiles'].items():
    directory=Path(profile['directory'])
    if args.report_root is not None:
        directory=args.report_root/'raw'/('lavik-'+profile['tag'])/directory.name
    totals=defaultdict(float)
    workers=[]
    total=0
    for tid in profile['attached_tids']:
        path=directory/f'self-{tid}.txt'
        report=path.read_text()
        event=re.search(r'Event count \(approx\.\): (\d+)',report)
        if event is None:
            assert (directory/f'stacks-{tid}.txt').stat().st_size==0
            workers.append({'tid':tid,'event_count':0,'empty_stack_file':True})
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
        workers.append({'tid':tid,'event_count':count,'reported_percent':reported,'lost_samples':lost,'self_symbols':symbols})
    assert total>0
    result={'profile':profile,'workers':workers,'total_approx_event_count':total,
            'reported_coverage_percent':sum(totals.values())/total,
            'self_symbols':[{'mode':mode,'symbol':symbol,'percent':weight/total}
                            for (mode,symbol),weight in sorted(totals.items(),key=lambda x:-x[1])],
            'limits':'Approximate event-count-weighted self shares from existing 0.1% threshold, two-decimal reports. Includes polling/background/kernel CPU, not request-exclusive CPU or latency. Zero-sample helper retained. Raw stacks not reprocessed during another profile.'}
    def metrics(path):
        return {line.rsplit(' ',1)[0]:float(line.rsplit(' ',1)[1])
                for line in path.read_text().splitlines() if line and not line.startswith('#')}
    before,after=metrics(directory/'before.prom'),metrics(directory/'after.prom')
    selected=['lavik_command_calls_total{command="zscore"}',
              'lavik_storage_io_operations_total{operation="read"}',
              'lavik_storage_io_bytes_total{operation="read"}',
              'lavik_storage_io_operations_total{operation="write"}']
    # Command series are absent before the first invocation; an absent initial
    # ZSCORE counter therefore denotes zero. Storage series must exist.
    assert selected[0] in after
    delta={key:after[key]-(before.get(key,0) if key==selected[0] else before[key]) for key in selected}
    assert all(value>=0 for value in delta.values()) and delta[selected[0]]>0
    result['counter_delta']=delta
    result['read_ops_per_zscore']=delta[selected[1]]/delta[selected[0]]
    result['read_bytes_per_zscore']=delta[selected[2]]/delta[selected[0]]
    result['counter_limits']='Server-wide metric window, including background work and commands overlapping scrape boundaries. Independent fresh populations can differ in physical page layout. Not an exact per-request trace or evidence that read-decoder changes reduce storage IO.'
    outputs[label]=result
    (W/f'{args.prefix}-{label}-self-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(label,'coverage',result['reported_coverage_percent'],'top',[(v['symbol'],round(v['percent'],3)) for v in result['self_symbols'][:12]])
(W/f'{args.prefix}-self-comparison.json').write_text(json.dumps(outputs,indent=2)+'\n')
