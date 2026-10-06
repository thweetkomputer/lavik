from pathlib import Path
import json,statistics
W=Path(__file__).parent
S=json.loads((W/'matched-seed-summary.json').read_text())
assert S['completed_points']==108 and all(len(x['pairs'])==3 for x in S['summary'])
lines=['## 三轮干净吞吐结果','','QPS 为每对候选/main 的变化，p99 负值表示改善。完整三轮原始 QPS 和延迟见 [配对汇总](matched-seed-summary.json)。','','| 负载 | 命令 | QPS 三轮变化 | QPS 变化中位 | p99 变化中位 |','|---|---|---:|---:|---:|']
for x in S['summary']:
 scope=('1 MiB，标准' if x['logical_bytes']==1048576 else '100 MiB，'+('标准' if x['pattern']=='standard' else '64 目标'))
 nums=' / '.join(f"{p['qps_change_percent']:+.2f}%" for p in x['pairs'])
 lines.append(f"| {scope} | {x['operation']} | {nums} | {x['paired_median_qps_change_percent']:+.2f}% | {x['paired_median_p99_change_percent']:+.2f}% |")
lines += ['','## 内存观察','','下表记录 INFO `used_memory` 的候选减基线（字节）；每个单元依次为三轮。该指标是记账内存，不是 RSS 或分配次数。进程 RSS 也保留在原始证据中，不能据此声称整个进程内存相同。','','| 负载 | 写命令 | 写前差值 B | 写后差值 B |','|---|---|---:|---:|']
A={(a['tag'],a['operation']):a for a in json.loads((W/'matched-seed-command-audit.json').read_text())['audits']}
rows=json.loads((W/'matched-seed-repeats.json').read_text())['rows']
for x in S['summary']:
 if x['operation'] not in ['HSET','SADD_SREM']:continue
 points={(r['round'],r['version']):A[r['tag'],r['operation']] for r in rows if all(r[k]==x[k] for k in ['pattern','type','logical_bytes','operation'])}
 diffs={metric:' / '.join(f"{points[n,'candidate'][metric]-points[n,'parent'][metric]:+,}" for n in [1,2,3]) for metric in ['used_memory_before','used_memory_after']}
 scope=('1 MiB，标准' if x['logical_bytes']==1048576 else '100 MiB，'+('标准' if x['pattern']=='standard' else '64 目标'))
 lines.append(f"| {scope} | {x['operation']} | {diffs['used_memory_before']} | {diffs['used_memory_after']} |")
(W/'clean-tables.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
