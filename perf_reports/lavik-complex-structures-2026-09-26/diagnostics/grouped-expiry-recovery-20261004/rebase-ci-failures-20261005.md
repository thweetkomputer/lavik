# Rebase 后 CI 失败与处理

[机器可读记录](rebase-ci-failures-20261005.json)。这些是已结束分片的结果，不代表其他分片已经完成；原始失败保留，不以重跑覆盖。

## #267：List 部分启动故障测试的过期断言

`c7c37ff6` 的 [arm64 分片 0](https://github.com/eloqdata/lavik/actions/runs/37297041183/job/111723341243) 在 `RangeReadFailureJoinsStartedPages` 失败。trace 指向 `LAVIK_FAIL_LIST_READ_BATCH_START_KEY`：注入路径已返回 `OOM grouped List read batch admission`，测试仍匹配旧的 `allocation` 文案。其余错误类型、后续 LLEN/SET、持久化退出和恢复值检查未报告失败。

修复提交 `0cc00887` 只改测试：匹配实际 admission 文案，并在断言失败时打印返回文本；不更改生产代码、故障触发或时间限制。clang-format 23.1.1、pre-commit 和 diff 检查通过。[新 CI](https://github.com/eloqdata/lavik/actions/runs/37303614082) 待完成；压测期间没有额外本机编译或测试。更早的巨型 key CI SET 超时仍未解释，此修复不声称解决它。PR 保持草稿。

[分片记录](pr267-rebase-failed-job.json) · [失败摘录](pr267-rebase-failed-job-excerpt.txt)

## #270：Sentinel HA 恢复预算超时，原因未定

`e9714eb3` 的 [arm64 分片 5](https://github.com/eloqdata/lavik/actions/runs/37297041978/job/111730325644) 唯一失败用例是 `meta_integration.sentinel_ha_meta`。minority partition / learned peers 阶段的 30 秒预算超出：python-2 在 18.552 秒恢复，python-3 的成功操作超过预算，go-2/go-3 报 EOF。该预算包含选主、旧 leader 失去权限、旧连接关闭和顺序执行的客户端操作，现有日志未定位具体耗时来源。

同一 main `330738d9` 的[对应分片](https://github.com/eloqdata/lavik/actions/runs/37296400454/job/111722423762)通过。#270 唯一生产改动文件为 `src/redis/stream_command.cpp`，Sentinel/Meta 与该 gate 文件未改；这些事实不足以把失败认定为偶发或证明与 PR 无关。失败 artifact 只有九个 CTest 文件，未包含 gate 日志提到的保留进程目录，限制了后续定位。PR 继续草稿，保留失败；没有放宽预算或直接重跑。

[分片记录](pr270-rebase-failed-job.json) · [失败摘录](pr270-rebase-failed-job-excerpt.txt)
