# 现有 PR 收敛状态

核验时间：2026-10-05T13:48:34.522069+00:00。暂停寻找新优化，仅处理已有 PR、失败诊断及已排队验证。

全部保留分支均包含已合并 #268 的 main `330738d9`。#271/#272 保留对 #266 的功能依赖，#275 保留对 #270 的功能依赖；没有分支继续以 #268 为基底。本次没有自动合并。

| PR | 当前 head | 基底 | 当前 head CI | 处理 |
| --- | --- | --- | --- | --- |
| [#266](https://github.com/eloqdata/lavik/pull/266) | `3acb7fd2` | main | [17/17 通过](https://github.com/eloqdata/lavik/actions/runs/37297041275) | 保留：历史大 ZINCRBY 配对中位 +1.0%–6.5%，p99 有混合结果。 |
| [#267](https://github.com/eloqdata/lavik/pull/267) | `0cc00887` | main | [17/17 通过](https://github.com/eloqdata/lavik/actions/runs/37303614082) | 草稿：大 List 全量读取有收益；原巨型 key SET 超时仍未解释。 |
| [#270](https://github.com/eloqdata/lavik/pull/270) | `631e6104` | main | [12/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37308667273) | 草稿：大 Stream 全量读取有收益；点读控制有回退，Sentinel 测试修复待 CI。 |
| [#271](https://github.com/eloqdata/lavik/pull/271) | `a27637f0` | #266 | [5/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37312155267) | 草稿：已完成固定历史版本原生测试，72 点吞吐对照进行中。 |
| [#272](https://github.com/eloqdata/lavik/pull/272) | `0d36b4a9` | #266 | [17/17 通过](https://github.com/eloqdata/lavik/actions/runs/37308612324) | 草稿：已完成固定历史版本原生测试，72 点吞吐对照进行中。 |
| [#275](https://github.com/eloqdata/lavik/pull/275) | `38485460` | #270 | [9/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37308704165) | 草稿：大 Stream 全量读取 +128%–327%；小对象写及尾延迟回退，原 RDB 超时未解释。 |
| [#280](https://github.com/eloqdata/lavik/pull/280) | `253ab6a9` | main | [3/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37312803218) | 草稿：96 点完成，ZSCORE 各条件三轮 QPS 均提升；写收益不稳定，原 RESTORE 超时未解释。当前仅追加诊断。 |
| [#282](https://github.com/eloqdata/lavik/pull/282) | `2c94e9da` | main | [17/17 通过](https://github.com/eloqdata/lavik/actions/runs/37297697141) | 草稿：长 key 候选回放通过；普通短 key 原生回归及 72 点对照待完成，尚无配对 QPS 结论。 |

CI 与原生性能实验是不同证据：上表只使用与当前远端 head 完全匹配的 CI。历史基准及队列中的实验继续使用其冻结提交和二进制，不能转记成 rebase 后版本的性能。通过 CI 也不代表已排除报告中尚未复现的历史超时。

已关闭 [#269](https://github.com/eloqdata/lavik/pull/269)、[#273](https://github.com/eloqdata/lavik/pull/273)、[#276](https://github.com/eloqdata/lavik/pull/276)：整体收益不足，或控制条件出现稳定回退。[#274](https://github.com/eloqdata/lavik/pull/274) 此前已关闭。保留原始结果与反向结果，未删除分支。

[远端状态与完整 job 列表](pr-cleanup-current-validation.json) · [#267 当前 CI 完整证明](pr267-rebased-full-ci.json) · [#272 当前 CI 完整证明](pr272-rebased-full-ci.json) · [#282 当前 CI 完整证明](pr282-rebased-full-ci.json) · [原失败、修复和限制](rebase-ci-failures-20261005.md) · [初次 rebase 记录](prs-rebased-after268.json)
