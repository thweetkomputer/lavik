# #271 / #272：完整 72 点对照与去留结论

大、小对象各 36 点均已完成：两个候选分别对同轮父版本比较。全部 72 点通过原始测量、精确源码/二进制、全部 key 基数、正常退出、运行顺序、读取 seed 和命令计数核验。

本轮决定不保留 #271/#272：两者有局部收益，但整体取舍不足以继续推进；不是“所有条件都没有提升”。当前任务不寻找新优化，不追加实验来挑选有利结果。远端关闭状态见[现有 PR 收敛表](../grouped-expiry-recovery-20261004/pr-cleanup-current.md)。

- #271：小对象 c5120 读 QPS +5.48%、p99 -6.39%，三轮均改善；大对象 c320 读 QPS +2.87%，三轮均提升。但小对象写 c320/c5120 QPS 中位为 -0.19%/-2.29%（各两轮下降），大对象 c5120 写 p99 三轮均恶化，中位 +19.89%。没有稳定写 QPS 收益。
- #272：大对象 c320 和小对象两档读取的 QPS/p99 三轮均改善，QPS 中位 +4.33%/+2.70%/+1.73%。但大对象 c5120 读 QPS 三轮下降，中位 -0.67%；大对象 c5120 写 p99 中位 +15.07%，两轮恶化。四个写条件的 QPS 方向均混合，中位仅 +0.05%–1.06%。

这是针对当前候选的工程取舍，不是统计显著性判定或其他命令上的零收益证明。对照覆盖 ZSCORE/ZINCRBY，不能证明 Hash/List/Stream 的性能；两项未组合测试，也未与 #280 组合测试，不能据此断言相互替代或将增益相加。

| 对象 | 候选 | 命令 | c | QPS 配对中位变化 | QPS 提升轮数 | p99 配对中位变化 | p99 变差轮数 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 64 KiB / 128 B / 64 keys | #271 | ZINCRBY | 320 | -0.19% | 1/3 | -1.47% | 0/3 |
| 64 KiB / 128 B / 64 keys | #272 | ZINCRBY | 320 | +0.10% | 2/3 | -2.24% | 1/3 |
| 64 KiB / 128 B / 64 keys | #271 | ZINCRBY | 5120 | -2.29% | 1/3 | +0.00% | 1/3 |
| 64 KiB / 128 B / 64 keys | #272 | ZINCRBY | 5120 | +1.06% | 2/3 | -2.31% | 1/3 |
| 64 KiB / 128 B / 64 keys | #271 | ZSCORE | 320 | +0.32% | 3/3 | -2.03% | 1/3 |
| 64 KiB / 128 B / 64 keys | #272 | ZSCORE | 320 | +2.70% | 3/3 | -19.26% | 0/3 |
| 64 KiB / 128 B / 64 keys | #271 | ZSCORE | 5120 | +5.48% | 3/3 | -6.39% | 0/3 |
| 64 KiB / 128 B / 64 keys | #272 | ZSCORE | 5120 | +1.73% | 3/3 | -3.76% | 0/3 |
| 100 MiB / 1024 B / 8 keys | #271 | ZINCRBY | 320 | +0.07% | 2/3 | -1.55% | 1/3 |
| 100 MiB / 1024 B / 8 keys | #272 | ZINCRBY | 320 | +0.82% | 2/3 | -4.89% | 1/3 |
| 100 MiB / 1024 B / 8 keys | #271 | ZINCRBY | 5120 | +0.15% | 2/3 | +19.89% | 3/3 |
| 100 MiB / 1024 B / 8 keys | #272 | ZINCRBY | 5120 | +0.05% | 2/3 | +15.07% | 2/3 |
| 100 MiB / 1024 B / 8 keys | #271 | ZSCORE | 320 | +2.87% | 3/3 | -5.63% | 0/3 |
| 100 MiB / 1024 B / 8 keys | #272 | ZSCORE | 320 | +4.33% | 3/3 | -6.09% | 0/3 |
| 100 MiB / 1024 B / 8 keys | #271 | ZSCORE | 5120 | +1.20% | 2/3 | +3.15% | 2/3 |
| 100 MiB / 1024 B / 8 keys | #272 | ZSCORE | 5120 | -0.67% | 0/3 | +2.73% | 2/3 |

负 p99 变化表示改善。所有中位数均先计算同轮候选/父版本的变化率，再取三轮中位；不等同于两个边际中位数之比。逐轮原始数值、范围和零变化保留在 JSON，三轮不构成置信区间。

固定历史提交为 Parent `067c7589`、Inline `2e6e4f35`、Decoded `8babe581`；完整二进制身份、native 构建参数、依赖与测试记录见[原生验证](grouped-lookup-native-summary.json)。新 rebase head 的 CI 单独记录，不把历史二进制吞吐改记成当前 head 结果。

每个条件三个版本按 Parent/Inline/Decoded、Inline/Decoded/Parent、Decoded/Parent/Inline 轮换；两候选共用同轮父样本。读取在每轮新建的父版本逻辑数据上重启各版本，中间无写命令，但不是不可变物理快照；写入每个版本分别新建数据，先 c320 后 c5120。每点 30 秒、pipeline=1、12 workers；没有并行构建、原生测试或 perf。所有测量窗口的目标命令数等于请求数，失败/拒绝为零，除 INFO 外没有其他命令。其他系统没有重测，本对照不证明整体追平。

[72 条观测](grouped-lookup-complete-observations.json) · [完整三轮逐对结果](grouped-lookup-complete-summary.json) · [小对象 36 点](grouped-lookup-small-summary.json) · [命令计数审计](grouped-lookup-complete-command-audit.json) · [输入 SHA-256](grouped-lookup-complete-evidence-index.json)

复算时将 `REPORT_ROOT` 替换为包含 `raw/` 的报告目录：

```bash
python3 summarize-grouped-lookup.py --scope all --input grouped-lookup-complete-observations.json --output /tmp/lookup-complete-summary.json --report-root REPORT_ROOT
python3 audit-zset-score-commands.py --input grouped-lookup-complete-observations.json --output /tmp/lookup-complete-audit.json --report-root REPORT_ROOT
```
