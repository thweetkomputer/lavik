from pathlib import Path
from collections import Counter
import json,re
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26/raw')
V=json.loads((W/'stream-reply-versions.json').read_text())
tags={'main':'diagnostic-full-reused-maina565d603-ordered-stream-104857600-k8-f128-20261004','candidate':f'diagnostic-full-candidate{V["candidate"]["commit"][:8]}-ordered-stream-104857600-k8-f128-20261004'}
rows=[]
for label,tag in tags.items():
    raw=R/('lavik-'+tag);d=raw/'diagnostic-c1'
    proof=json.loads(next(raw.glob('provenance-*.json')).read_text())
    assert proof['source_commit']==V[label]['commit'] and proof['sha256']==V[label]['sha256']
    assert json.loads((raw/'server-exit.json').read_text())['code']==0
    total=0;leaves=Counter();named=Counter();copy_context=Counter();sampled_by_tid={}
    attachment=json.loads((d/'profile-provenance.json').read_text())['argv_by_tid']
    expected={str(tid) for tid in attachment}
    assert {p.stem.removeprefix('stacks-') for p in d.glob('stacks-*.txt')}==expected
    for p in d.glob('stacks-*.txt'):
        tid=p.stem.removeprefix('stacks-');sampled_by_tid[tid]=0
        for block in p.read_text().split('\n\n'):
            lines=block.splitlines()
            if len(lines)<2:continue
            match=re.search(r'\s(\d+) task-clock:',lines[0])
            if not match:continue
            weight=int(match[1]);total+=weight;sampled_by_tid[tid]+=weight
            leaf=re.sub(r'^\s*[0-9a-f]+\s+','',lines[1]);leaf=re.sub(r' \([^()]*\)$','',leaf)
            leaves[leaf]+=weight
            for category,needle in [('worker_run_once','Worker::RunOnce'),('worker_poll_storage','Worker::PollStorage'),('allocator_entry','_mi_theap_malloc_zero'),('tcp_sendmsg','tcp_sendmsg'),('stream_reply_next','StreamRangeReplyState::Next'),('syscall_entry','do_syscall_64')]:
                if needle in leaf:named[category]+=weight
            if '__memmove' in leaf or '__memcpy' in leaf:
                named['memcpy_memmove']+=weight
                for category,needle in [('stream_reply_next','StreamRangeReplyState::Next'),('append_bulk','AppendBulk')]:
                    if needle in block:copy_context[category]+=weight
    assert total>0
    metrics={}
    for phase in ['before','after']:
        metrics[phase]={}
        for line in (d/(phase+'.prom')).read_text().splitlines():
            if line and not line.startswith('#'):
                key,value=line.rsplit(' ',1);metrics[phase][key]=float(value)
    key='lavik_command_calls_total{command="xrange"}'
    commands=metrics['after'].get(key,0)-metrics['before'].get(key,0);assert commands>0
    io={}
    for family in ['operations','bytes']:
        for operation in ['read','write']:
            key=f'lavik_storage_io_{family}_total{{operation="{operation}"}}'
            delta=metrics['after'][key]-metrics['before'][key]
            io[operation+'_'+family]={'delta':delta,'per_command':delta/commands}
    rows.append({'version':label,'source_commit':V[label]['commit'],'profile_tag':tag,'task_clock_seconds':total/1e9,'recorded_tids':sorted(expected),'sampled_task_clock_seconds_by_tid':{k:n/1e9 for k,n in sampled_by_tid.items()},'zero_sample_tids':[k for k,n in sampled_by_tid.items() if n==0],'commands_in_metrics_interval':commands,'io':io,'self_cpu_percent':{k:100*n/total for k,n in named.items()},'copy_context_self_percent':{k:100*n/total for k,n in copy_context.items()},'top_self':[{'symbol':k,'percent':100*n/total} for k,n in leaves.most_common(35)]})
result={'rows':rows,'limitations':'Separate diagnostics, never throughput-comparison points. Per-worker 25s task-clock includes polling/background/kernel work; percentages are self CPU shares, not latency fractions. The command/IO window is30s and is not aligned to task-clock, so no CPU-per-command ratio is computed. IO includes all server storage work. Each profile reuses its own bounded post-XADD population; before/after exact cardinalities are retained and checked by the runner. Attached tids with zero samples are recorded explicitly; they contribute no observed task-clock and must not be mistaken for failed attachment. The runner requires every perf record/script command to exit successfully. Copy caller categories can overlap and stack ancestry can end at coroutine scheduling boundaries.'}
(W/'stream-reply-profile-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
for row in rows:print(row['version'],row['self_cpu_percent'],row['io'],flush=True)
