"""Publish the final retained INFO scope without rerunning measurements."""
from pathlib import Path
import hashlib,json,shutil,subprocess
W=Path(__file__).parent
repo=Path('/mnt/dev/lavik-complex-refresh-20261004')
R=repo/'perf_reports/lavik-complex-structures-2026-09-26'
D=R/'diagnostics/hash-route-replace-20261005'
v=json.loads((W/'hash-route-set-small-counters.json').read_text())
assert len(v['rows'])==36
paths=[]
for row in v['rows']:
 for source in row['info_files']:
  p=R/source['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==source['sha256'];paths.append(p)
assert len(set(paths))==72
for name in ['hash-route-set-small-counters.json','analyze-set-route-counters.py','publish-small-set-counters.py']:
 shutil.copyfile(W/name,D/name);paths.append(D/name)
lines=['# 小 Set：保留 INFO 窗口的计数核对','',
 '[完整 36 点计数及来源哈希](hash-route-set-small-counters.json) · [完整 QPS/p99 对照](hash-route-set-small.md) · [核对脚本](analyze-set-route-counters.py)','',
 '固定 `19496654` / `27c65ff9`，50,000 个 1 MiB key、128 B 元素。读取和写入各三个并发档、三个轮次、两个版本，共 36 个窗口。所有窗口的命令计数差分与客户端请求数一致；进程身份、worker 数和保存时间未变，无 BGSAVE、OOM 拒绝或 cleaner 失败。这里只分析已经完成的干净测量，没有启动新的服务端、采样或压测。','',
 '全部 18 个写入窗口的变更/命令计数比为 **49.971%～50.044%**，父版本和候选的提交队列高水位事件均为零；c80/320/5120 的配对 QPS 中位数仍为 **−3.08% / −3.32% / −4.87%**。这些计数没有显示空操作占比或高水位事件能够解释回退，也不能识别每条命令的等待或 CPU 原因。','',
 '| 并发 | 版本 | 变更/命令范围 | 三轮每批平均事务数 | 三轮高水位事件 |','|---|---|---|---|---|']
for s in v['summary']:
 lo,hi=s['changes_per_call_range'];batches=' / '.join(f'{n:.2f}' for n in s['batches_mean_transactions_each_round']);events=' / '.join(map(str,s['backpressure_events_each_round']))
 lines.append(f'| {s["connections"]} | {s["version"]} | {lo:.3%}～{hi:.3%} | {batches} | {events} |')
lines+=['',
 '计数窗口包围客户端启动和结束，包含后台工作及边界重叠提交。变更计数不是逐条返回值，也不是同步落盘完成数；每批事务数是窗口平均值，不是批大小分布。高水位计数记录入队事件，不是等待时间；零事件不能证明没有其他调度、锁或 I/O 等待。保留队列峰值的前后快照，不把生命周期 gauge 相减。','',
 '结合此前大 Set 与两种 Hash 的 108 点核对，全部 144 点 INFO 窗口已核验。#276 仍没有通用吞吐收益；减少一次树遍历并未减少持久化 AVL 路径的节点分配数量，不能据源码或 CPU 占比下降宣称实际分配次数或耗时同比下降。四组大对象 perf 已完成，小 Hash perf 仍待执行，现有证据尚未解释回退。','']
p=D/'hash-route-set-small-counters.md';assert not p.exists();p.write_text('\n'.join(lines));paths.append(p)
p=D/'README.md';s=p.read_text();section='\n[小 Set 的 36 个 INFO 窗口](hash-route-set-small-counters.md)也已核验，至此全部 144 点计数核对完成。小 Set 的变更/命令比例为 49.971%～50.044%，所有写入窗口均无高水位事件；QPS 回退仍未解释，不能归因于这两项计数。\n';assert section not in s;p.write_text(s+section);paths.append(p)
assert all(p.stat().st_size<3*1024**2 for p in paths)
relative=[str(p.relative_to(repo)) for p in dict.fromkeys(paths)]
subprocess.run(['git','diff','--check','--',*relative],cwd=repo,check=True)
subprocess.run(['git','add','-f','--',*relative],cwd=repo,check=True)
(W/'hash-route-set-small-counters-publication-files.json').write_text(json.dumps(relative,indent=2)+'\n')
print('staged',len(relative),'files',sum(p.stat().st_size for p in paths),'bytes')
