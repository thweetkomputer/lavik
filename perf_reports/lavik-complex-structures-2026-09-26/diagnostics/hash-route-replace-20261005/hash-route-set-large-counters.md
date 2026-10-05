# 大 Set 回退：已保存 INFO 窗口的计数核对

[完整 36 点 QPS/p99](hash-route-set-large.md) · [36 个 INFO 窗口及 SHA-256](hash-route-set-large-counters.json) · [复算脚本](analyze-set-route-counters.py) · [父/候选相同的计数源码身份](hash-route-counter-source.json)。所有命令计数差分都与 memtier 报告的请求数完全相等；INFO 前后服务端 run_id、进程、worker 数、最后保存时间一致，没有 BGSAVE、OOM 或 cleaner failure。未重新运行压测或 perf。

18 个 SADD/SREM 窗口的 dataset-change 计数/命令数范围为 **49.9217%–50.0759%**，符合该随机添加/删除负载约半数命令产生变更的预期，没有足以直接解释 6%–11% QPS 回退的粗粒度变更比例偏移。该计数记录提交中的 key 变更，窗口可含后台或前序待提交工作；它不是逐命令返回值审计，也不等于同步持久化次数。不能据此排除页布局、每次变更成本或调度差异。

## 提交批量与高水位

下表每格按第 1/2/3 轮排列。平均批量为窗口内 `tx_commit_batch_transactions / tx_commit_batches`；高水位事件为 `tx_commit_backpressure_waits` 差分。源码在入队后达到 worker 队列高水位时增加该计数，它不是等待时长。

| 连接数 | Parent 平均事务/批 | Candidate 平均事务/批 | Parent 高水位事件 | Candidate 高水位事件 |
|---|---|---|---|---|
| 80 | 5.19 / 4.59 / 3.15 | 3.11 / 3.27 / 3.29 | 0 / 0 / 0 | 0 / 0 / 0 |
| 320 | 8.93 / 9.91 / 11.93 | 12.12 / 14.38 / 13.71 | 60033 / 36979 / 0 | 0 / 0 / 0 |
| 5120 | 4.77 / 8.70 / 42.94 | 52.21 / 50.44 / 55.96 | 4865 / 5499 / 3 | 0 / 0 / 6 |

父版本在 c320 前两轮有 60,033/36,979 次高水位事件，第三轮为零；c5120 平均批量也从前两轮的 4.77/8.70 变为第三轮的 42.94。候选的 c5120 平均批量为 50.44–55.96。不同轮次存在明显的提交行为差异，因此单个新 perf 样本也需同时检查其计数，不能直接推广到所有配对结果。

c80 的父/候选三轮均无高水位事件，但 QPS 中位仍下降 6.95%；高水位计数并不能单独解释全部回退。较少事件与较好 p99 的同时出现也不是因果证明。累计队列峰值保留原始前后值，不将峰值差分当作测量窗口峰值。

这里的 500-key Set 负载与此前 8-key ZINCRBY/XADD 计数范围不同；此前对应窗口没有高水位事件的结论仍只适用于那些窗口。下一步仍是既定的独立 HSET/SADD_SREM c320 perf，结合这些计数检查 CPU、分配和提交行为，不修改 durable 顺序或队列阈值来迁就压测。

## 复算

从报告根目录执行：

```sh
python3 diagnostics/hash-route-replace-20261005/analyze-set-route-counters.py --report-root . --output /tmp/hash-route-set-large-counters.json
```
