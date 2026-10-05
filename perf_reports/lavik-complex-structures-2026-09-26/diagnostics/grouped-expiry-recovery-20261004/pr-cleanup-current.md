# 现有 PR 收敛状态

核验时间：2026-10-05T13:37:07.674471+00:00。暂停寻找新优化，仅处理已有 PR、失败诊断及已排队验证。

全部保留分支均包含已合并 #268 的 main `330738d9`。#271/#272 保留对 #266 的功能依赖，#275 保留对 #270 的功能依赖；没有分支继续以 #268 为基底。本次没有自动合并。

| PR | 当前 head | 基底 | 当前 head CI | 处理 |
| --- | --- | --- | --- | --- |
| [#266](https://github.com/eloqdata/lavik/pull/266) | `3acb7fd2` | main | [17/17 通过](https://github.com/eloqdata/lavik/actions/runs/37297041275) | [17/17 通过](https://github.com/eloqdata/lavik/actions/runs/37297041275)
| [#267](https://github.com/eloqdata/lavik/pull/267) | `0cc00887` | main | [16/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37303614082) | [17/17 通过](https://github.com/eloqdata/lavik/actions/runs/37303614082)
| [#270](https://github.com/eloqdata/lavik/pull/270) | `631e6104` | main | [3/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37308667273) | [4/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37308667273)
| [#271](https://github.com/eloqdata/lavik/pull/271) | `a27637f0` | #266 | [3/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37312155267) | [3/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37312155267)
| [#272](https://github.com/eloqdata/lavik/pull/272) | `0d36b4a9` | #266 | [11/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37308612324) | [14/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37308612324)
| [#275](https://github.com/eloqdata/lavik/pull/275) | `38485460` | #270 | [4/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37308704165) | [4/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37308704165)
| [#280](https://github.com/eloqdata/lavik/pull/280) | `253ab6a9` | main | [3/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37312803218) | [3/17 通过，其余待完成](https://github.com/eloqdata/lavik/actions/runs/37312803218)
| [#282](https://github.com/eloqdata/lavik/pull/282) | `2c94e9da` | main | [17/17 通过](https://github.com/eloqdata/lavik/actions/runs/37297697141) | [17/17 通过](https://github.com/eloqdata/lavik/actions/runs/37297697141)

CI 与原生性能实验是不同证据：上表只使用与当前远端 head 完全匹配的 CI。历史基准及队列中的实验继续使用其冻结提交和二进制，不能转记成 rebase 后版本的性能。通过 CI 也不代表已排除报告中尚未复现的历史超时。

已关闭 [#269](https://github.com/eloqdata/lavik/pull/269)、[#273](https://github.com/eloqdata/lavik/pull/273)、[#276](https://github.com/eloqdata/lavik/pull/276)：整体收益不足，或控制条件出现稳定回退。[#274](https://github.com/eloqdata/lavik/pull/274) 此前已关闭。保留原始结果与反向结果，未删除分支。

[远端状态与完整 job 列表](pr-cleanup-current-validation.json) · [#267 当前 CI 完整证明](pr267-rebased-full-ci.json) · [#282 当前 CI 完整证明](pr282-rebased-full-ci.json) · [原失败、修复和限制](rebase-ci-failures-20261005.md) · [初次 rebase 记录](prs-rebased-after268.json)
