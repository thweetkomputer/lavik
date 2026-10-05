# List reply capacity: incremental measurements

This is the second measured stage of [PR #267](https://github.com/eloqdata/lavik/pull/267). The previous production revision is `13041873` (bounded page reads); this candidate is `ff9e36550d3c899011cb07e037f4521273e667ae` (adds reply preallocation). Later branch heads also include the independently submitted recovery repair in [PR #268](https://github.com/eloqdata/lavik/pull/268); these performance measurements remain pinned to `ff9e3655` and predate that repair. [First-stage results](../list-read-window-20261004/README.md) · [binary/build proof](list-reply-versions.json).

## Change and scope

List array replies compute their exact RESP wire size, including an existing outer-array prefix, before appending. A single capacity reservation avoids copying the growing prefix repeatedly. Empty and singleton arrays retain their existing append path; an unrepresentable estimate falls back to normal append behavior without integer wraparound. Large buffers are still released on reset. Storage reads, mutation rules, memory admission, durable format and wire bytes are unchanged by this incremental step.

## Three paired repetitions against the previous candidate

Three independent seed pairs ordered A/B, B/A, A/B; 15-second LRANGE points at 1/4/16 connections and LSET at 2560; previous is PR #267 at 13041873, isolating reply reservation; same baseline workload and settings; no concurrent build, tests or perf.

These comparisons isolate reply reservation; the previous column is **not main**. Three paired repetitions are not a confidence interval. [All observations](list-reply-repeats.json) · [summary and every p99](list-reply-repeat-summary.json).

| Command | Connections | Previous median QPS | Candidate median QPS | Median paired change | Paired change range | Previous / candidate median p99 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LRANGE | 1 | 3.36 | 3.46 | +3.0% | +2.1% to +6.8% | 327.679 / 296.959 |
| LRANGE | 4 | 9.72 | 10.77 | +3.9% | +2.2% to +12.7% | 782.335 / 618.495 |
| LRANGE | 16 | 18.74 | 20.89 | +11.5% | +11.4% to +12.0% | 1843.199 / 1474.559 |
| LSET | 2560 | 46,553.62 | 47,675.50 | +2.8% | +2.4% to +3.9% | 270.335 / 232.447 |

All nine LRANGE pairs improve QPS and lower p99. The LSET control improves QPS in all three pairs, with one worse p99; it does not reproduce the large single-grid throughput drop, but does not establish an improvement in an unchanged command path.

The LSET control was included because the single-grid 2560-connection point fell by 13.8% and its p99 increased from 201.7 to 389.1 ms. LSET does not call the changed array-reply helper. The repetitions preserve both favorable and unfavorable outcomes rather than deleting that original observation.

## Single clean sweeps

[100 MiB / 128 B incremental comparison](list-reply-comparison-104857600-128-k8.json) · [64 KiB / 128 B](list-reply-comparison-65536-128-k64.json) · [64 KiB / 1024 B](list-reply-comparison-65536-1024-k64.json). Each candidate sweep validates cardinalities and exits cleanly with no command errors. Single sweeps have no statistical confidence intervals.

In the large sweep, LRANGE QPS changes by +3.6%/+1.3%/+14.6% at 1/4/16 connections relative to `13041873`. Its p99 improves at one connection but is 12.4% and 7.6% higher at 4 and 16 connections. Small LRANGE throughput is essentially unchanged. Several untargeted point-read/write observations are lower, including −8.2% small LINDEX at 5120 connections; the complete data remain published. These results do not establish a universal improvement.

## Total result against pinned main and historical peers

[Main comparison, 100 MiB / 128 B](comparison-list-104857600-128-k8.json) · [64 KiB / 128 B](comparison-list-65536-128-k64.json) · [64 KiB / 1024 B](comparison-list-65536-1024-k64.json). The current figures use these complete clean grids.

The combined candidate reaches 3.43/9.88/20.70 QPS for the 100 MiB / 128 B / 8-key LRANGE workload at 1/4/16 connections. Pinned main recorded 0.90/3.43 QPS and failed the 16-connection point with OOM. There is no valid QPS ratio for that failed point. Historical Redis gives 5.26/14.10/16.47 QPS, Valkey 4.49/8.09/8.37 and Kvrocks 2.91/12.03/21.86. The 16-connection candidate point is 5.3% below the fastest peer; the lower-concurrency points still miss the provisional 20% target. This does not establish overall parity.

Peers were not rerun. Redis/Valkey disable persistence; Kvrocks disables WAL and uses an 80 GiB cache; Lavik stays durable on six SPDK NVMe devices without field/page payload caching. These are matched commands/data, not equivalent persistence configurations.

## Separate perf evidence

[Profile comparison](list-reply-profile-comparison.json) · [candidate samples and counters](range-profile/) · [recorder](../main-a565d603-20261004/profile-ordered-allworkers.py).

| Version | Self memmove | Self memmove under List array reply | Physical reads / LRANGE | Physical writes / LRANGE |
| --- | ---: | ---: | ---: | ---: |
| previous | 12.02% | 9.36% | 14125 | 0 |
| candidate | 8.12% | 5.30% | 14125 | 0 |

Both versions read 14,125 physical pages and about 124.3 MB per range. Sampled self CPU includes polling, background and kernel work and is not a wall-latency fraction. The 25-second profile and 30-second command/counter interval are diagnostic runs, excluded from clean QPS plots. Stack attribution identifies the reply-copy path but does not classify every growth copy versus required serialization.

## Validation and CI

[Validation record](list-reply-validation.json): seven List/collection integration cases and three grouped cases pass against the exact fault-disabled benchmark binary. Coverage includes large byte-exact replies, transactions, blocking operations, low-memory ranges and real OOM. The test-driver sources are unchanged for this incremental production change; their provenance is recorded. Earlier 289 passing tests belong to `13041873`, not an unperformed full local suite on this revision.

PR #267 and #266 encountered full-disk String expiration recovery startup failures on both architectures. The root cause and locally validated fix are now recorded in [the recovery investigation](../grouped-expiry-recovery-20261004/README.md) and PR #268. PR #267 combined-head CI at `a672d2e7` [passed on both architectures](https://github.com/eloqdata/lavik/actions/runs/37229865721), including all 12 test shards and formatting ([record](pr267-a672-ci.json)). PR #266 also [passed combined-head CI](../zset-member-probe-20261004/pr266-97ae-ci.json). These earlier QPS observations do not measure the recovery repair.

## Additional 100 MiB / 1024 B sweep

The clean 8-key sweep uses the same immutable `ff9e3655` binary. [All points and p99](comparison-list-104857600-1024-k8.json) are retained, including point-operation regressions. This is a single independent sweep, not a paired improvement estimate.

| Operation | Connections | Main QPS | PR QPS | Change |
|---|---:|---:|---:|---:|
| LINDEX | 80 | 359035.12 | 348621.27 | -2.9% |
| LINDEX | 320 | 451016.79 | 444320.18 | -1.5% |
| LINDEX | 1280 | 315330.10 | 320095.73 | +1.5% |
| LINDEX | 2560 | 291125.29 | 290946.04 | -0.1% |
| LINDEX | 5120 | 256346.62 | 261638.82 | +2.1% |
| LRANGE | 1 | 0.95 | 4.17 | +338.9% |
| LRANGE | 4 | 3.72 | 13.86 | +272.6% |
| LRANGE | 16 | 13.52 | 26.74 | +97.8% |
| LSET | 80 | 52356.29 | 48920.66 | -6.6% |
| LSET | 320 | 46202.71 | 47864.89 | +3.6% |
| LSET | 1280 | 46997.25 | 46220.43 | -1.7% |
| LSET | 2560 | 47316.22 | 45169.72 | -4.5% |
| LSET | 5120 | 46461.04 | 45639.81 | -1.8% |

## 后续 main 同步

main 已前进至 `19496654`。List 分支已解决冲突，并把批量启动失败的测试故障点改成显式 admission 错误，保留所有已启动读取的 join；实际 C++ 分配异常遵循 main 的终止策略。[新提交及待完成的 CI](../main-a565d603-20261004/pr-main-integration.json)。本页吞吐、perf 与旧 CI 仍对应各自记录的冻结提交，不代表新提交已完成测量；64 页版本已有的尾延迟和写入退化结论仍然保留。

## 当前 main 整合版本的 CI 失败

`343e951e` 的 amd64 分片 4 在 `lavik_extent_recovery_e2e` 失败：从 4 workers 恢复到 2 workers 后，覆盖 5009 字节外部 key 的 `SET` 等待回复超时；同分片其余 289 项通过。恢复扫描已完成，但日志不足以区分空间回收停滞与环境因素。保留失败，尚未修改超时或通过重跑排除它。[失败证据与后续复现范围](pr267-current-ci-failure.json)。这不改变历史版本的性能结果，也不代表当前 head 已验证通过。

## 精确 CI 二进制的 extent 复现

原 amd64 CI 二进制和测试驱动在独立文件设备上对照：main `19496654` 第一轮通过（137.54 秒）；候选 `343e951e` 第一轮失败（118.59 秒），随即停止。两份测试驱动 SHA-256 相同，候选 CI 的合成 merge tree 已核对与请求的源码树一致。[完整来源与结果](pr267-extent-native-ci-reproductions.json) · [候选失败日志](pr267-native-candidate-extent-failure.log)。这些耗时不是性能比较。

本机失败是 `GET key_bytes=9437184` 超时，原 CI 是 `SET key_bytes=5009` 超时；都出现在四个 worker 写入、两个 worker 恢复后的阶段，但不能据此认定同一根因。768 MiB 原始数据镜像已保留为只读文件，未加入 Git。[诊断状态](pr267-native-extent-failure-summary.json) · [镜像副本重放脚本](replay-pr267-retained-image.py)。后续镜像重放结果见下节；socket 和关闭超时保持不变。

## 同一故障镜像的独立副本重放

候选 `343e951e` 再次在 9 MiB key 的 GET 等待回复头超过原 60 秒限制，此前 3 个外部 key 和 6 MiB key 的读取均通过。main `19496654` 从另一份相同镜像副本完成全部读取、覆盖和正常关闭，但同一 GET 也耗时 **50.008 秒**。[逐操作结果与来源](pr267-retained-image-replays.json) · [诊断摘要](pr267-retained-replay-summary.json) · [候选日志](pr267-retained-replay-candidate.log) · [main 日志](pr267-retained-replay-main.log)。

候选超时后才附加调试器：三个 worker 的回溯进入 `_io_uring_get_cqe`，内核等待点为 `io_cqring_wait`；liburing 之后的回溯不完整，尚不能识别具体等待的协程。原始镜像前后 SHA-256 一致，保持只读；磁盘镜像和原始线程转储未入库。这一对固定顺序重放不能证明死锁、数据损坏或候选独有回归，也不能证明与 CI 的 SET 超时同源。下一步在干净压测结束后采集逐操作 CPU、存储和协程进展。
