# 现有 PR 收敛状态

核验时间：2026-10-05T14:05:38.239057+00:00。暂停寻找新优化，仅处理已有 PR、失败诊断及已排队验证。

全部保留分支均包含已合并 #268 的 main `330738d9`。#275 保留对 #270 的功能依赖；没有保留分支继续以 #268 为基底。本次没有自动合并。表中也保留本轮新关闭的 #271/#272，避免把关闭与 CI 失败混为一谈。

| PR | 当前 head | 基底 | 当前 head CI | 处理 |
| --- | --- | --- | --- | --- |
| [#266](https://github.com/eloqdata/lavik/pull/266) | `3acb7fd2` | main | [17/17 通过](https://github.com/eloqdata/lavik/actions/runs/37297041275) | 保留：历史大 ZINCRBY 配对中位 +1.0%–6.5%，p99 有混合结果。 |
| [#267](https://github.com/eloqdata/lavik/pull/267) | `0cc00887` | main | [17/17 通过](https://github.com/eloqdata/lavik/actions/runs/37303614082) | 草稿：大 List 全量读取有收益；原巨型 key SET 超时仍未解释。 |
| [#270](https://github.com/eloqdata/lavik/pull/270) | `631e6104` | main | [17/17 通过](https://github.com/eloqdata/lavik/actions/runs/37308667273) | 草稿：大 Stream 全量读取有收益；点读控制有回退。Sentinel 测试修复后的当前 CI 全绿。 |
| [#271](https://github.com/eloqdata/lavik/pull/271) | `a27637f0` | #266 | [已取消：6 项通过、9 分片取消，2 汇总项因此失败](https://github.com/eloqdata/lavik/actions/runs/37312155267) | 已关闭：完整 72 点有局部读收益，但小对象写 QPS 回退、大对象高并发写 p99 三轮恶化。 |
| [#272](https://github.com/eloqdata/lavik/pull/272) | `0d36b4a9` | #266 | [17/17 通过](https://github.com/eloqdata/lavik/actions/runs/37308612324) | 已关闭：CI 全绿；完整 72 点有局部读收益，但大对象高并发读 QPS 三轮下降，写收益不稳定。 |
| [#275](https://github.com/eloqdata/lavik/pull/275) | `38485460` | #270 | [12/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37308704165) | 草稿：大 Stream 全量读取 +128%–327%；小对象写及尾延迟回退，原 RDB 超时未解释。 |
| [#280](https://github.com/eloqdata/lavik/pull/280) | `253ab6a9` | main | [5/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37312803218) | 草稿：96 点完成，ZSCORE 各条件三轮 QPS 均提升；写收益不稳定，原 RESTORE 超时未解释。当前仅追加诊断。 |
| [#282](https://github.com/eloqdata/lavik/pull/282) | `2c94e9da` | main | [17/17 通过](https://github.com/eloqdata/lavik/actions/runs/37297697141) | 草稿：长 key 候选回放通过；普通短 key 原生回归及 72 点对照待完成，尚无配对 QPS 结论。 |

CI 与原生性能实验是不同证据：上表只使用与当前远端 head 完全匹配的 CI。历史基准及队列中的实验继续使用其冻结提交和二进制，不能转记成 rebase 后版本的性能。通过 CI 也不代表已排除报告中尚未复现的历史超时。

已关闭 [#269](https://github.com/eloqdata/lavik/pull/269)、[#271](https://github.com/eloqdata/lavik/pull/271)、[#272](https://github.com/eloqdata/lavik/pull/272)、[#273](https://github.com/eloqdata/lavik/pull/273)、[#276](https://github.com/eloqdata/lavik/pull/276)：有些条件有收益，但整体取舍不足或控制条件出现回退。[#274](https://github.com/eloqdata/lavik/pull/274) 此前已关闭。保留原始正向及反向结果，未删除分支。

[远端状态与完整 job 列表](pr-cleanup-current-validation.json) · [#267 当前 CI 完整证明](pr267-rebased-full-ci.json) · [#270 当前 CI 完整证明](pr270-rebased-full-ci.json) · [#272 当前 CI 完整证明](pr272-rebased-full-ci.json) · [#282 当前 CI 完整证明](pr282-rebased-full-ci.json) · [原失败、修复和限制](rebase-ci-failures-20261005.md) · [初次 rebase 记录](prs-rebased-after268.json)

[#271/#272 完整去留依据](../grouped-lookup-controls-20261005/grouped-lookup-complete.md) · [远端关闭记录](../grouped-lookup-controls-20261005/grouped-lookup-pr-closures.json) · [#271 关闭后 CI 取消申请与此前状态](../grouped-lookup-controls-20261005/pr271-closure-ci-cancel.json)

[#271 CI 取消终态](../grouped-lookup-controls-20261005/pr271-closure-ci-terminal.json)：关闭性能候选后取消未完成测试，汇总项因缺少完整分片而失败；不是新测试失败，也不视作通过。
