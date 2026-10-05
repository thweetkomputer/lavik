# #271 / #272：完整大对象对照

100 MiB/key、1024 B、8 keys，ZSCORE / ZINCRBY 的 c320 / c5120，三个版本、三个轮换，共 36 点完成。原始结果、二进制身份、全部 key 基数、正常退出及命令计数均通过核验。小对象 36 点仍在进行，尚未作最终去留决定。

这两项没有普遍收益：ZSCORE c320 两个候选三轮都提升；c5120 的 decoded 读 QPS 三轮均回退。写 QPS 各条件方向混合，inline 的 c5120 写 p99 三轮均变差。不能用 c320 的读收益覆盖其余结果。

| 候选 | 命令 | c | QPS 配对中位变化 | QPS 提升轮数 | p99 配对中位变化 | p99 变差轮数 |
| --- | --- | --- | --- | --- | --- | --- |
| #271 inline | ZINCRBY | 320 | +0.07% | 2/3 | -1.55% | 1/3 |
| #272 decoded | ZINCRBY | 320 | +0.82% | 2/3 | -4.89% | 1/3 |
| #271 inline | ZINCRBY | 5120 | +0.15% | 2/3 | +19.89% | 3/3 |
| #272 decoded | ZINCRBY | 5120 | +0.05% | 2/3 | +15.07% | 2/3 |
| #271 inline | ZSCORE | 320 | +2.87% | 3/3 | -5.63% | 0/3 |
| #272 decoded | ZSCORE | 320 | +4.33% | 3/3 | -6.09% | 0/3 |
| #271 inline | ZSCORE | 5120 | +1.20% | 2/3 | +3.15% | 2/3 |
| #272 decoded | ZSCORE | 5120 | -0.67% | 0/3 | +2.73% | 2/3 |

数值为同轮候选/父版本变化率的中位数，不是两个边际中位数之比；负 p99 变化表示改善。三轮不提供置信区间。两个候选共用同轮父样本，收益不能相加。

固定历史提交：Parent `067c7589`，Inline `2e6e4f35`，Decoded `8babe581`。它们的生产二进制、native 构建参数及依赖身份见 [原生验证](grouped-lookup-native-summary.json)；当前 PR head / CI 见[收敛状态](../grouped-expiry-recovery-20261004/pr-cleanup-current.md)，不能将旧二进制实验当作新 head 性能。

运行顺序为 Parent/Inline/Decoded、Inline/Decoded/Parent、Decoded/Parent/Inline。每轮读取在同一新建父版本逻辑数据上重启三个版本，中间不执行写命令，但不是不可变物理快照；每个写版本独立预置，c320 后运行 c5120。30 秒、pipeline=1、12 workers。全部测量窗口的目标命令数与压测请求数相等，无失败/拒绝，除 INFO 外没有其他命令。其他三个系统没有重测，本结果不证明整体追平。

[36 条观测](grouped-lookup-large-observations.json) · [三轮逐对结果](grouped-lookup-large-summary.json) · [命令计数审计](grouped-lookup-large-command-audit.json) · [输入 SHA-256](grouped-lookup-large-evidence-index.json)

复算：在本目录运行以下命令，将 `REPORT_ROOT` 替换为包含 `raw/` 的报告目录。

```bash
python3 summarize-grouped-lookup.py --scope large --input grouped-lookup-large-observations.json --output /tmp/lookup-large-summary.json --report-root REPORT_ROOT
python3 audit-zset-score-commands.py --input grouped-lookup-large-observations.json --output /tmp/lookup-large-audit.json --report-root REPORT_ROOT
```
