# Full-device grouped expiration: CI diagnosis and repair

[PR #268](https://github.com/eloqdata/lavik/pull/268) 已于 2026-10-05 合并到 main，合并提交 `330738d9`。[合并记录](pr268-merged.json)。合并是远端状态，不等于最终 head 的全部 CI 已完成；历史测试与失败仍按原提交保留。

The `e4f4da7c` follow-up covers reclaimed extent identities on both Hash and ordered recovery paths, validates the selected graph before publication or live accounting, and waits for detached-root tombstones to become durable before readiness. Only tagged foreground disk exhaustion permits skipping that repair; admission, I/O and payload-checksum failures remain fatal. Added regressions cover reclaimed Hash/List extents and crash followed by clock rollback. `cf895883` then reorders the transient tombstone fields and their initializers to reduce padding; it does not intentionally change recovery behavior. The final-head CI was still pending when the PR was merged; no old pass is relabeled as current validation.

[本轮 rebase 记录](prs-rebased-after268.json)：#266/#267/#270/#280/#282 直接基于 main `330738d9`；#271/#272 基于新 #266，#275 基于新 #270。相关恢复代码与 main 一致，不再携带独立 #268 提交。全部变更通过格式及差异检查，新 CI 待完成；#267 历史 `343e951e` 的 SET 超时仍未解释。既有性能测量和排队对照保留固定源码、二进制和 CI 身份，不转记为新 head 的结果。

## Root cause

The test reported a startup timeout, but the preserved log shows the server had exited with `ordered root/page count mismatch`. This occurred on arm64 and amd64. The original CI amd64 binary reproduced it on the first local attempt with a regular file-backed 96 MiB device. A main-based diagnostic build reproduces the same failure on the saved image: an expired, unshielded String root declares 113 pages, while only 32 candidate records remain. [Diagnostic log](expiry-image-diagnostic-full.txt).

Full-device expiration can retire an unshielded grouped value without first appending a tombstone. Its children may be reclaimed while the expired root survives in a block shared with live records. Recovery must select that root before considering its expired graph; choosing an older value instead would be wrong.

The repair discards an unreconstructable graph only for an expired, unshielded winner with startup expiration authority. It queues a fresh tombstone after allocator recovery. The current implementation waits for that detached-root deletion to become durable before serving. Live/shielding roots still fail on missing pages, and admission/I/O errors remain failures. Complete expired graphs keep the normal durable-deletion path. The detached-root full-device exception relies on the expiry deadline only for confirmed foreground disk exhaustion.

## Historical verification of the initial repair

- [New fixture against pinned main: expected failure](expiry-fixture-before.txt); [same fixture after repair](expiry-fixture-after.txt). It covers incomplete Hash/List graphs, live/shielding rejection, unrelated data, counters and a subsequent injected recovery-clock rollback.
- [28 recovery tests pass](expiry-fix-recovery-tests.txt).
- [103 grouped command tests pass; one opt-in >1 GiB RDB case skipped](expiry-fix-ordered-tests.txt).
- [TTL suite passes](expiry-fix-ttl-tests.txt), including deferred expiration authority; [shielded older-value regression passes](expiry-fix-shielded-test.txt).
- [Ten file-backed repetitions pass](expiry-recovery-fixed-repeat.txt). The companion JSON records only the last repetition.
- [Actual failed image repaired](expiry-image-repaired.json): the exact 900 KiB replacement is intact, expired keys are absent, and `DBSIZE=1`; clean restart with the recovery clock forced to zero also passes.
- [Build/test proof and fixture rechecks](validation.json).

The Sentinel protocol fixtures now wait for discovery authority, not merely Raft leadership. Discovery checks pass 20 repetitions plus all 15 tests with the original CI amd64 binary. Partition gates allow the existing uncertain-command disconnect only after the explicit fault cut, matching the controlled lease-fence gate; three one-way and one two-way runs pass. Neither fixture change alters service behavior.

The earlier arm64 native-FULL timeout has not recurred in subsequent completed runs. Local amd64 repeats do not establish its arm64 root cause. The historical combined-head CI passed all software shards on both architectures; see the recorded heads below, independently of the current pending run.

## Report provenance repair

The reply-reservation publisher incorrectly reused the first List-stage directory. [Repair record](list-report-layout-repair.json) documents restoring all 67 first-stage files from the commit before that publication and moving second-stage material into its intended directory. Raw QPS data and curves are unchanged. [First stage](../list-read-window-20261004/README.md) and [second stage](../list-reply-reserve-20261004/README.md) now retain distinct comparisons and CPU profiles.

## Historical CI confirmation

[Initial recovery-fix CI](https://github.com/eloqdata/lavik/actions/runs/37229779333) at `89d0b136` passed 11 of 12 software shards, including all six arm64 shards. Both architecture shard-0 jobs passed all 291 tests, including the previously failing grouped ordered suite. The remaining amd64 shard failed `SentinelTest.test_discovery_null_contract_on_bootstrap_leader` with `RESP connection closed`: it sent discovery commands before the elected leader had discovery authority. [Job outcomes](pr268-first-ci.json) retain the failed overall result.

At historical head `5c0deb3e`, PR #268 included the validated Meta test fixture corrections from #266/#267, with recovery implementation `89d0b136`. [Combined-head CI](https://github.com/eloqdata/lavik/actions/runs/37231917942) passed all 12 software shards on amd64/arm64, both builds and formatting. [Recorded job outcomes](pr268-5c0-ci.json).

## 当前保留 PR

| PR | 新 head | 基础分支 | 本轮 CI |
|---|---|---|---|
| #266 | `3acb7fd2` | `main` | [新 CI](https://github.com/eloqdata/lavik/actions/runs/37297041275)，待完成 |
| #267 | `c7c37ff6` | `main` | [新 CI](https://github.com/eloqdata/lavik/actions/runs/37297041183)，待完成 |
| #270 | `e9714eb3` | `main` | [新 CI](https://github.com/eloqdata/lavik/actions/runs/37297041978)，待完成 |
| #271 | `d471dd65` | `perf/zset-member-probe-20261004` | [新 CI](https://github.com/eloqdata/lavik/actions/runs/37297692802)，待完成 |
| #272 | `c6956c8b` | `perf/zset-member-probe-20261004` | [新 CI](https://github.com/eloqdata/lavik/actions/runs/37297692702)，待完成 |
| #275 | `291cbcb7` | `perf/stream-reply-batching-20261004` | [新 CI](https://github.com/eloqdata/lavik/actions/runs/37297694693)，待完成 |
| #280 | `a5c825e9` | `main` | [新 CI](https://github.com/eloqdata/lavik/actions/runs/37297696440)，待完成 |
| #282 | `2c94e9da` | `main` | [新 CI](https://github.com/eloqdata/lavik/actions/runs/37297697141)，待完成 |

#269/#273/#276 因实测整体收益不足或控制回退已关闭，#274 此前已关闭。暂停寻找新优化；#271/#272/#280 的收益尚未验证，保持草稿，不能据此称为无效或推荐合并。

[调度调整记录](pr-cleanup-requeued-processes.json)：仅重启尚未取得主机锁的等待任务，允许 PR rebase 后继续测量原固定提交；原始等待日志保留，未重跑或覆盖任何观测。源提交、完整 CI、二进制 SHA 和构建配置检查保留。#276 的未开始补充采样已[取消](pr276-unstarted-perf-cancelled.json)。
