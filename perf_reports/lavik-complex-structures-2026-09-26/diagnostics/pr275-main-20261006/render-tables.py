from pathlib import Path
import json
W=Path(__file__).parent
S=json.loads((W/'complete-summary.json').read_text())
assert S['observations']==60 and len(S['summary'])==10
lines=['## 三轮配对结果','','main 与候选的 QPS 列各取三轮中位；变化列取三次配对比值的中位，两种统计不能互相代替。p99 负值为改善。','','| 负载 | 命令 | 连接数 | main QPS 中位 | #275 QPS 中位 | 配对 QPS 变化 | 配对 p99 变化 |','|---|---|---:|---:|---:|---:|---:|---:|']
# Seven columns; keep the delimiter row aligned with the header.
lines[-1]='|---|---|---:|---:|---:|---:|---:|'
for r in S['summary']:
 size='100 MiB / 128 B / 8 keys' if r['logical_bytes']==104857600 else '64 KiB / 1024 B / 64 keys'
 lines.append(f"| {size} | {r['operation']} | {r['connections']} | {r['parent_median_qps']:,.2f} | {r['window_median_qps']:,.2f} | {r['qps_paired_percent']['median']:+.2f}% | {r['p99_paired_percent']['median']:+.2f}% |")
lines += ['','## 每轮变化','','| 负载 / 命令 / 连接数 | QPS 变化，第 1 / 2 / 3 轮 | p99 变化，第 1 / 2 / 3 轮 |','|---|---:|---:|']
for r in S['summary']:
 size='100 MiB' if r['logical_bytes']==104857600 else '64 KiB'
 q=' / '.join(f"{p['qps_change_percent']:+.2f}%" for p in r['pairs']);t=' / '.join(f"{p['p99_change_percent']:+.2f}%" for p in r['pairs'])
 lines.append(f"| {size} / {r['operation']} / c{r['connections']} | {q} | {t} |")
(W/'tables.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
