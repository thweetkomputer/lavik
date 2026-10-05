# Hash 回退检查与小对象 perf 调度

已核对两种 Hash 规模的全部 72 个已完成测量窗口，命令计数差分均与客户端请求数完全一致；INFO 前后进程/run_id、worker 数和最后保存时间不变，没有 BGSAVE、OOM 或 cleaner failure。

[大 Hash 的 36 个窗口](hash-route-large-counters.json) · [小 Hash 的 36 个窗口](hash-route-hash-small-counters.json) · [相同的计数源码定义](hash-route-counter-source.json)。全部 144 份 INFO 原始快照及 SHA 在 JSON 中列出。复用[原 Set 分析器](analyze-set-route-counters.py)增加 `--scope`，默认 Set 输出逐字段复算一致，没有复制第二套计数逻辑。

大 Hash 的 18 个 HSET 窗口，dataset-change 计数/命令数均为 1；小 Hash 范围为 **0.999998253272–1**。该计数接近每命令一次变更，而不是完全无变化的 HSET 压测。源码已跳过相同值编辑；测量命令使用 `__data__` 与 `--random-data`。微小计数差异仍保留：INFO 窗口含客户端启动、收尾和可能跨窗口的后台提交，不能将聚合计数当作逐命令返回值或同步持久化审计。

## 提交计数

每格为第 1/2/3 轮。批量是 `tx_commit_batch_transactions / tx_commit_batches` 的窗口平均；高水位是 `tx_commit_backpressure_waits` 增量，不是等待时长。

| 规模 | c | Parent 事务/批 | Candidate 事务/批 | Parent 高水位事件 | Candidate 高水位事件 |
|---|---:|---|---|---|---|
| 100 MiB / 500 keys | 80 | 4.10 / 4.50 / 4.37 | 4.78 / 4.42 / 4.42 | 0 / 0 / 0 | 0 / 0 / 0 |
| 100 MiB / 500 keys | 320 | 9.12 / 10.03 / 10.17 | 10.96 / 10.19 / 9.07 | 0 / 0 / 0 | 0 / 0 / 0 |
| 100 MiB / 500 keys | 5120 | 2.95 / 2.99 / 2.76 | 3.34 / 3.48 / 3.16 | 6 / 3 / 0 | 1 / 9 / 9 |
| 1 MiB / 50,000 keys | 80 | 3.78 / 3.82 / 3.91 | 3.80 / 3.80 / 3.75 | 0 / 0 / 0 | 0 / 0 / 0 |
| 1 MiB / 50,000 keys | 320 | 13.42 / 12.90 / 12.79 | 13.28 / 12.96 / 12.92 | 0 / 0 / 0 | 0 / 0 / 0 |
| 1 MiB / 50,000 keys | 5120 | 56.49 / 58.61 / 59.33 | 58.54 / 57.33 / 46.33 | 0 / 0 / 0 | 0 / 0 / 0 |

小 Hash 的全部 HSET 窗口都没有高水位事件，其已发布的三个连接数 QPS 中位仍回退、p99 中位仍变差。平均提交批量、内存布局和调度差异不能单靠这些计数确定因果；这组观察不支持把回退简单归为队列高水位。大 Hash 的 c5120 获益与小 Hash 的回退也不能相互抵消。

## 补充小 Hash 采样

[两组小 Hash HSET c320 perf](profile-hash-route-small-hash.py)已排队，等待原 144 点干净对照和四组大对象 perf 全部完成，再争用统一主机锁。选择 c320 是因为小 Hash 此条件已观测到 QPS 中位 −2.86%、p99 中位 +11.67%，原待采样协议仅覆盖大对象。

两个固定生产二进制分别新建 50,000 个 1 MiB key（128 B 值），重启后以 30 秒命令/指标窗口及 25 秒、99 Hz、16 KiB DWARF 逐 worker 采样。保留全部 key 基数、服务端退出码、命令结果、INFO/Prometheus 与脚本/二进制 SHA；使用已更正的 Bycorf 来源清单。各实例物理布局独立，CPU 包含轮询/后台/内核，采样 QPS 不混入干净配对。

[排队身份与脚本 SHA](small-hash-perf-queued.json)。当前尚无这两组新采样结果。原始 perf/调用栈留本地，完成后发布小型摘要并结合提交计数解释；不把大对象的热点直接视为小对象回退原因。脚本保留本机绝对路径和 scratch 设备约束，移机需适配。

## 复算计数

在报告根目录执行：

```sh
python3 diagnostics/hash-route-replace-20261005/analyze-set-route-counters.py --scope hash-large --report-root . --output /tmp/hash-route-large-counters.json
python3 diagnostics/hash-route-replace-20261005/analyze-set-route-counters.py --scope hash-small --report-root . --output /tmp/hash-route-hash-small-counters.json
```
