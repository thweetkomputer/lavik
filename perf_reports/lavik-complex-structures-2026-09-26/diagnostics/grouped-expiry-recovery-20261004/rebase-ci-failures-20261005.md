# Rebase 后 CI 失败与处理

[机器可读记录](rebase-ci-failures-20261005.json)。这些是已结束分片的结果，不代表其他分片已经完成；原始失败保留，不以重跑覆盖。

## #267：List 部分启动故障测试的过期断言

`c7c37ff6` 的 [arm64 分片 0](https://github.com/eloqdata/lavik/actions/runs/37297041183/job/111723341243) 在 `RangeReadFailureJoinsStartedPages` 失败。trace 指向 `LAVIK_FAIL_LIST_READ_BATCH_START_KEY`：注入路径已返回 `OOM grouped List read batch admission`，测试仍匹配旧的 `allocation` 文案。其余错误类型、后续 LLEN/SET、持久化退出和恢复值检查未报告失败。

修复提交 `0cc00887` 只改测试：匹配实际 admission 文案，并在断言失败时打印返回文本；不更改生产代码、故障触发或时间限制。clang-format 23.1.1、pre-commit 和 diff 检查通过。[新 CI](https://github.com/eloqdata/lavik/actions/runs/37303614082) 待完成；压测期间没有额外本机编译或测试。更早的巨型 key CI SET 超时仍未解释，此修复不声称解决它。PR 保持草稿。

[分片记录](pr267-rebase-failed-job.json) · [失败摘录](pr267-rebase-failed-job-excerpt.txt)

旧运行在新提交后已无测试执行，仅两个 `always()` 汇总作业排队，修复版仍 pending。保存[原状态](pr267-superseded-ci-before-cancel.json)后发出普通取消，仍未结束；随后使用 GitHub 官方的[强制取消接口](https://docs.github.com/en/rest/actions/workflow-runs#force-cancel-a-workflow-run)终止旧汇总。[请求与条件](pr267-superseded-ci-force-cancel.json) · [最终状态](pr267-superseded-ci-final.json)：旧运行整体 cancelled，但原 arm64 分片的 assertion failure 保留；修复版已转为 queued，不能视为通过。

## #270：Sentinel HA 恢复预算超时，原因未定

`e9714eb3` 的 [arm64 分片 5](https://github.com/eloqdata/lavik/actions/runs/37297041978/job/111730325644) 唯一失败用例是 `meta_integration.sentinel_ha_meta`。minority partition / learned peers 阶段的 30 秒预算超出：python-2 在 18.552 秒恢复，python-3 的成功操作超过预算，go-2/go-3 报 EOF。该预算包含选主、旧 leader 失去权限、旧连接关闭和顺序执行的客户端操作，现有日志未定位具体耗时来源。

同一 main `330738d9` 的[对应分片](https://github.com/eloqdata/lavik/actions/runs/37296400454/job/111722423762)通过。#270 唯一生产改动文件为 `src/redis/stream_command.cpp`，Sentinel/Meta 与该 gate 文件未改；这些事实不足以把失败认定为偶发或证明与 PR 无关。失败 artifact 只有九个 CTest 文件，未包含 gate 日志提到的保留进程目录，限制了后续定位。PR 继续草稿，保留失败；没有放宽预算或直接重跑。

[分片记录](pr270-rebase-failed-job.json) · [失败摘录](pr270-rebase-failed-job-excerpt.txt)


### Sentinel 成功 main 对照的进一步线索

从 main `330738d9` 的成功分片 artifact 取出 `LastTest.log`，其中保留了成功用例输出：[身份与对照](pr270-sentinel-main-comparison.json) · [main 恢复时刻摘录](main330-sentinel-arm64-5-recovery-excerpt.txt)。

| minority partition / learned peers | main 成功运行 | #270 失败运行 |
|---|---:|---:|
| python-2 恢复 | 13.485 秒 | 18.552 秒 |
| python-3 恢复 | 25.510 秒 | 成功操作超过 30 秒 |
| go-2 恢复 | 25.564 秒，重试过 EOF | EOF，截止前未恢复 |
| go-3 恢复 | 25.568 秒，重试过 EOF | EOF，截止前未恢复 |

正常启动阶段，main 的两个 Python 探测同样分别消耗约 13.0 和 11.6 秒；#270 对应约 11.6 和 11.5 秒。Go EOF 并非该失败独有，也不表示驱动进程退出：`GoClient.call` 对收到的命令错误抛 `RuntimeError`，进程退出使用另一条错误。main 在下一轮探测中成功重试，#270 的第二个 Python 探测已越过公共截止点。

失败运行的首次 Python 恢复比 main 晚 5.067 秒，超过 main 最后一个客户端恢复后剩余的 4.432 秒预算。这个非同期对照与“串行探测加恢复前置步骤耗尽共同预算”的解释一致，但仍不能区分服务端恢复、Sentinel 发现、客户端重试各自贡献，不能证明偶发或排除回归。尚无逐次重试时间线；不改变 30 秒约束、不跳过用例，也不把 main 成功当成 #270 通过。


### 已复用的 Sentinel 测试修复

#270 `631e6104` 复用 #271 已有的独立客户端并发探测修复。各客户端仍从同一次故障开始计时，共用原有 30 秒截止点；保留值校验、超时成功拒绝及清理前等待所有探测结束。四项针对探测器的测试及格式检查通过。[新 CI](https://github.com/eloqdata/lavik/actions/runs/37308667273) 待完成；此修复消除测试串行探测对其他客户端预算的消耗，不宣称已证明服务端恢复正常。#275 同步 rebase 为 `38485460`，生产代码和 grouped 测试与其原 head 完全一致，[新 CI](https://github.com/eloqdata/lavik/actions/runs/37308704165) 待完成。

## #272：选主完成后初始化仍占用成员变更入口

`c6956c8b` 的 [amd64 分片 1](https://github.com/eloqdata/lavik/actions/runs/37297692702/job/111730337415) 在 `gate_data_control` 的 mTLS 初始化失败，plaintext 场景已通过。`wait_leader()` 只等 leader 标志；初始身份绑定协调器仍可持有 membership gate，`clustercreate` 因而在任何 proposal 前返回明确的忙碌错误。

`0d36b4a9` 只在测试中对这一精确错误进行最多 10 秒的重试，复用同一请求；其他返回值与传输异常立即失败，不重试提交结果不确定的错误，不改生产代码或整项测试期限。[六项隔离检查](pr272-admission-fixture-checks.json) 覆盖立即成功、忙碌后成功、其他错误、不确定提交、忙碌耗尽预算、传输异常，执行的是实际 helper 的 AST，未启动服务进程。pre-commit 通过；[新 CI](https://github.com/eloqdata/lavik/actions/runs/37308612324) 待完成。

[原分片记录](pr272-rebase-failed-job.json) · [失败摘录](pr272-rebase-failed-job-excerpt.txt)

## #280：满盘过期恢复的 SetIndirect RESTORE 超时

`a5c825e9` 的 [arm64 分片 0](https://github.com/eloqdata/lavik/actions/runs/37297696440/job/111727582470) 中，`AllTypes/GroupedFullDiskExpirationE2e.ReclaimsGraphAndRecovers/SetIndirect` 的 RESTORE 等待响应超时（errno=11）。该 ordered suite 为 102 通过、1 跳过、1 失败。原因尚未确定；已经包含 #268 并不能证明本次失败已解决或与当前 PR 无关。不提高超时、不盲目重跑，保持草稿。[失败摘录](pr280-rebase-failed-job-excerpt.txt)。

[当前各 PR 的 head、依赖与 CI 快照](pr-cleanup-current-state.json)。快照不是后续 CI 成功承诺；原历史失败和原测量二进制身份保留。
