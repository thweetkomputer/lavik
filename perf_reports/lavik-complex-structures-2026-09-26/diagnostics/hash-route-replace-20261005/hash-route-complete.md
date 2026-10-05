# Hash/Set 单路由替换：完整 144 点结果

固定 parent `19496654` 与 candidate `27c65ff9` 的 144 点对照全部完成。大 Hash 的 HSET c5120 获益没有推广到其他规模：较小 Hash 的 HSET、两种 Set 的 SADD/SREM 在三个连接数的配对 QPS 中位均下降，读控制也有回退。**当前证据不支持把 #276 作为通用吞吐优化合并；PR 保持草稿，独立 perf 尚待完成。**

每个条件为三轮 A/B、B/A、A/B，各版本独立 RESTORE 并重启，30 秒、pipeline=1。共 24 个条件 × 2 个版本 × 3 轮。全部观测通过原始结果、源码/二进制来源、seed、所有 key 基数及服务端退出核对；测量时没有并行构建、测试或 perf。独立实例的路由 seed 与物理布局可能不同，三轮不构成置信区间，也不能直接指定回退原因。

[全部观测及更正后的依赖身份](hash-route-complete-observations.json) · [24 个条件的全部配对与核验](hash-route-complete-summary.json)。下表按 c80 / c320 / c5120 排列；正 QPS 为提升，负 p99 为改善。百分比先在同轮相除，再取三轮中位，不是两个边际中位数的比值。

| 数据 | 命令 | 配对 QPS 中位变化（c80 / c320 / c5120） | 配对 p99 中位变化（同序） |
|---|---|---|---|
| 100 MiB / 1024 B / 500 keys | HGET | -0.37% / -0.17% / -2.00% | +2.33% / -3.42% / -0.88% |
| 100 MiB / 1024 B / 500 keys | HSET | +0.16% / +2.14% / +7.81% | -8.07% / +1.44% / -8.19% |
| 1 MiB / 128 B / 50,000 keys | HGET | +0.03% / +0.12% / -3.01% | -2.23% / +0.00% / -16.52% |
| 1 MiB / 128 B / 50,000 keys | HSET | -0.91% / -2.86% / -2.08% | +3.25% / +11.67% / +4.14% |
| 100 MiB / 1024 B / 500 keys | SISMEMBER | -0.43% / -0.46% / -1.65% | -2.23% / -2.15% / -3.33% |
| 100 MiB / 1024 B / 500 keys | SADD_SREM | -6.95% / -6.55% / -10.62% | -5.27% / -2.92% / -23.62% |
| 1 MiB / 128 B / 50,000 keys | SISMEMBER | -0.81% / -1.32% / -1.71% | +0.00% / +0.81% / -7.46% |
| 1 MiB / 128 B / 50,000 keys | SADD_SREM | -3.08% / -3.32% / -4.87% | -3.70% / -9.09% / -18.01% |

## 逐项结果与历史 peer

- [大 Hash](hash-route-large.md)：HSET c5120 三轮 QPS 均提升，中位 +7.81%；低连接收益较弱、读控制有回退。
- [小 Hash](hash-route-hash-small.md)：HSET 三个连接数各两轮 QPS 下降、一轮上升，p99 中位均变差。
- [大 Set](hash-route-set-large.md)：SADD/SREM 各两轮 QPS 下降、一轮上升；c320/c5120 的 p99 三轮均改善。
- [小 Set](hash-route-set-small.md)：SADD/SREM 各两轮 QPS 下降、一轮上升；p99 中位改善，但各有一轮变差。

各子报告保留匹配条件的历史 Redis/Valkey/Kvrocks 值和 CSV SHA。peer 没有在本轮重跑，采样时长及持久化/缓存设置不同。小 Set SISMEMBER c320 的候选边际中位达到最快历史 peer 的 101.95%，但与父版本的同轮配对中位仍下降；单个历史比例既不证明这项代码优化有效，也不代表整体达到三个系统的水平。小 Set 写入仅为对应最快历史 peer 的 33.93%–39.47%。

## 回退诊断与采样

[大 Set INFO 分析](hash-route-set-large-counters.md)显示变更/命令比例接近 50%，提交批量与高水位事件因轮次变化。[Hash 的 72 个 INFO 窗口](hash-route-hash-counters.md)显示较小 HSET 变更/命令比例接近 1，且所有写入窗口均无高水位事件。计数保留全部微小差异和窗口限制；不能单靠背压解释回退。

四组独立大 Hash/Set HSET、SADD/SREM c320 perf 已满足 144 点前置条件，等待统一主机锁。另补充两组小 Hash HSET c320 perf，等待原有采样结束。所有 CPU/指标诊断与干净 QPS 分开，固定已验证的二进制，不重新选择有利样本。

## 复算

在报告根目录执行：

```sh
python3 diagnostics/hash-route-replace-20261005/summarize-hash-route-replace.py --scope all --report-root . --input diagnostics/hash-route-replace-20261005/hash-route-complete-observations.json --versions diagnostics/hash-route-replace-20261005/hash-route-replace-versions.json --output /tmp/hash-route-complete-summary.json
```
