# List reply capacity: incremental measurements

当前合并状态：#266/#267/#270/#280 已合并；[#275/#282 的草稿原因及当前验证](../grouped-expiry-recovery-20261004/pr-cleanup-current.md)。以下实验继续引用固定测量版本。

**当前 PR 与 CI：** 见[统一收敛状态](../grouped-expiry-recovery-20261004/pr-cleanup-current.md)。下述原生、CI 和性能数据仍归属各自标注的提交；固定历史版本的测量不能代替当前 head 验证。

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

## 历史 `343e951e` 的 CI 失败

`343e951e` 的 amd64 分片 4 在 `lavik_extent_recovery_e2e` 失败：从 4 workers 恢复到 2 workers 后，覆盖 5009 字节外部 key 的 `SET` 等待回复超时；同分片其余 289 项通过。恢复扫描已完成，但日志不足以区分空间回收停滞与环境因素。保留失败，尚未修改超时或通过重跑排除它。[失败证据与后续复现范围](pr267-current-ci-failure.json)。这不改变历史版本的性能结果，也不代表当前 head 已验证通过。

## 精确 CI 二进制的 extent 复现

原 amd64 CI 二进制和测试驱动在独立文件设备上对照：main `19496654` 第一轮通过（137.54 秒）；候选 `343e951e` 第一轮失败（118.59 秒），随即停止。两份测试驱动 SHA-256 相同，候选 CI 的合成 merge tree 已核对与请求的源码树一致。[完整来源与结果](pr267-extent-native-ci-reproductions.json) · [候选失败日志](pr267-native-candidate-extent-failure.log)。这些耗时不是性能比较。

本机失败是 `GET key_bytes=9437184` 超时，原 CI 是 `SET key_bytes=5009` 超时；都出现在四个 worker 写入、两个 worker 恢复后的阶段，但不能据此认定同一根因。768 MiB 原始数据镜像已保留为只读文件，未加入 Git。[诊断状态](pr267-native-extent-failure-summary.json) · [镜像副本重放脚本](replay-pr267-retained-image.py)。后续镜像重放结果见下节；socket 和关闭超时保持不变。

## 同一故障镜像的独立副本重放

候选 `343e951e` 再次在 9 MiB key 的 GET 等待回复头超过原 60 秒限制，此前 3 个外部 key 和 6 MiB key 的读取均通过。main `19496654` 从另一份相同镜像副本完成全部读取、覆盖和正常关闭，但同一 GET 也耗时 **50.008 秒**。[逐操作结果与来源](pr267-retained-image-replays.json) · [诊断摘要](pr267-retained-replay-summary.json) · [候选日志](pr267-retained-replay-candidate.log) · [main 日志](pr267-retained-replay-main.log)。

候选超时后才附加调试器：三个 worker 的回溯进入 `_io_uring_get_cqe`，内核等待点为 `io_cqring_wait`；liburing 之后的回溯不完整，尚不能识别具体等待的协程。原始镜像前后 SHA-256 一致，保持只读；磁盘镜像和原始线程转储未入库。这一对固定顺序重放不能证明死锁、数据损坏或候选独有回归，也不能证明与 CI 的 SET 超时同源。后续逐操作 CPU、存储进展和 perf 结果见下文。

[长 key perf 驱动](profile-pr267-retained-image.py) 仅对 9 MiB key GET 采集 49 Hz task-clock/DWARF，同时每 0.5 秒记录进程 I/O、各线程 CPU 与等待点，区分发送、回复头和完整响应耗时；调试器仅在采样结束后的失败路径附加。采样和解析均持有主机锁，结果不混入干净 QPS。

## 长 key 重复校验与根记录复用

当时的 main `19496654` 和候选 `343e951e` 的普通 grouped String GET 都逐个读取 8 KiB 分段。每页的 `LoadOrderedGroup` 调用 `FindVerifiedEntry`；索引未保存完整 key 时，后者通过 `LoadOutOfIndexKey` 读取完整原 key 再比较。因此，无重试且每次均走此分支时，9 MiB key、6 MiB value 的 768 个分段可能重复读取 **6.75 GiB** key 内容；6 MiB key、1 MiB value 则为 **0.75 GiB**。这一推导不包含首次校验、记录头及后台 I/O，不是实际设备计数。两者推导量相差 9 倍，main 重放耗时约 50.008/5.518 秒，但相关性不足以证明耗时来源，也不能解释原 CI 的 SET 超时。

[草稿 PR #282](https://github.com/eloqdata/lavik/pull/282)，验证提交 [`28d7cca4`](https://github.com/thweetkomputer/lavik/commit/28d7cca498655e02f46407adb65335219b10ee6b) 从 main `19496654` 开始，为 `FindVerifiedEntry` 新增独立重载。每页刷新通过已有 `FindCandidateIf`，只有 block、offset、allocation epoch 全部匹配此前已校验的物理根，才能省去间接 key 的完整读取；索引中的完整 key 仍比较全部字节，没有匹配候选时回到原异步校验。数据代次、逻辑版本、页面身份及 GC 检查保留。ordered 远端页读取本来就借用父 key，这里的重复校验不能误写成逐页跨 worker key 复制。

同一 head `28d7cca4` 的 [fork CI](grouped-root-28d7cca4-full-ci.json) 与[上游 PR CI](pr282-upstream-full-ci.json) 均已完整通过各 17 项，包括两架构编译、12 个软件分片和格式检查（[上游运行](https://github.com/eloqdata/lavik/actions/runs/37287121881)）。[首次 arm64 分片 3 的 runner 失联](grouped-root-ci-attempt1-infrastructure-failure.json) 停在依赖安装，尚未运行软件测试；同一源码重跑失败项后通过，原始失败记录保留。[amd64 extent 恢复用例](grouped-verified-root-extent-ci-proof.json) 也通过。下文的候选三轮镜像回放已完成；普通短 key 的 native 回归和全部 72 点配对对照均已完成，收益与回退见下文；长 key 候选 perf 已完成，见下文。

## 长 key 采样：超时期间仍持续读取

main `19496654` 和 #267 候选 `343e951e` 的同镜像独立副本采样均完成，采样驱动正常退出；两者的 9 MiB key GET 都在原 60 秒限制处等待回复头超时。采样前的 3 个外部 key 与 6 MiB key GET 均成功，原始只读镜像 SHA-256 不变。[完整操作及采样来源](pr267-retained-image-profiles.json) · [CPU/I/O 进展汇总](pr267-retained-key-progress-summary.json) · [汇总脚本](summarize-retained-key-progress.py) · [main 原始进展样本](pr267-retained-main-operation-progress.json) · [候选原始进展样本](pr267-retained-candidate-operation-progress.json)。

| 版本 | 有效样本 | 样本跨度 | 进程读取字节增量 | 进程写入字节增量 | 完成 GET |
|---|---:|---:|---:|---:|---|
| main `19496654` | 120 | 59.589 秒 | 9,033,633,792 | 0 | 否 |
| #267 `343e951e` | 120 | 59.592 秒 | 8,741,662,720 | 4,059,136 | 否 |

两者每个约 10 秒的观测区间都仍有大量读取进展；工作线程的多数等待点样本为 `io_cqring_wait`，两条活跃工作线程在整个采样区间合计约 5.7–5.8 秒 CPU。等待点计数不是等待时间占比，进程 I/O 包含后台活动，末端采样也不覆盖整个命令。候选窗口存在少量写入，更不能把全部 I/O 归为 GET。两者都未完成，因此不能以字节数之差比较效率或 QPS。

这补充了重复 key 读取假设所需的实际 I/O 证据；已完成的 perf 解析和候选镜像回放见下文。此前无采样 main 能在约 50 秒完成，本次采样超时说明诊断扰动不可忽略；不能据此宣称死锁、候选独有回归或原 CI 的 SET 超时已解决。原始 perf/调用栈不入库。

## 采样解析返回码修正

原后处理器要求 recorder 返回 0，但主动对 sudo/perf 进程组发 SIGINT 后 sudo 返回了 `-2`，因此后处理器在解码前退出。两个 recorder 日志均包含完整写出摘要，分别写出 271、265 个样本，文件约 2.35/2.29 MB。没有重新采样；[恢复解析脚本](analyze-retained-key-profiles-resume.py) 保留原返回码，要求主动 SIGINT 返回值、完整写出日志及后续 report/script 两种解码成功，才接纳数据。解析已在主机锁内完成；前述 `/proc` 计数不依赖 perf 解码。结果见下节。


## 已完成的采样解析与新的无采样基线失败

两个原始 perf 文件的 report/script 解码均成功，[解码命令与来源](pr267-retained-key-profile-analysis.json) 保留主动 SIGINT 的 `-2` 返回码。以下是进程级 **CPU self** 占比，均在 9 MiB key GET 等待期间采集：

| 符号 | main `19496654`（271 样本） | #267 `343e951e`（265 样本） |
|---|---:|---:|
| CRC32::Extend | 31.00% | 29.81% |
| memmove | 16.24% | 12.83% |
| memcmp | 12.55% | 15.47% |

[逐符号汇总与输入 SHA-256](pr267-retained-key-self-summary.json) · [main 完整 self 表](pr267-retained-main-self.txt) · [候选完整 self 表](pr267-retained-candidate-self.txt)。表中空白被压缩，全部符号行保留。四舍五入后的覆盖合计均为 100.11%，未重新归一化；丢样为 0 不代表调用栈完整。样本较少，含内核、轮询和后台工作，不能据此估计精确优化幅度。两次 GET 均超时，不能把采样耗时当作吞吐对照；这组旧采样没有根记录复用 `28d7cca4` 的样本；后者的独立诊断见[后续报告](grouped-root-candidate-perf.md)。

随后启动的 `19496654` / `28d7cca4` 三轮无采样对照在 **main 第一轮**停止：3 个 5009 字节外部 key 的完整 GET 通过，6 MiB key 的 1 MiB value 也校验通过，但 9 MiB key GET 在原 60 秒 socket 限制处等待回复头超时，收到的 payload 为 0。该配对任务没有执行候选，原定三轮没有完成。[原始操作记录、失败阶段及二进制身份](grouped-verified-root-replays.json)。保留本次失败，不重跑基线来替换它，也不提高超时。

## 根记录复用候选的三轮独立回放

[候选独立重放](replay-grouped-verified-root-candidate.py) 已全部通过：固定 `28d7cca4` 的 CI 二进制，使用相同只读原始镜像的三份独立可写副本、2 workers、原 60 秒 socket/120 秒关闭限制，无 perf 采样。每轮 16 个操作成功且服务正常退出，15 次 GET 均逐字节验证完整 payload。原始镜像前后 SHA-256 均为 `b4e0113cf9b7dcbe03175c5e5665be8589ebef9dbc9c2847adc3cd3010b956ae`。

| 9 MiB key → 6 MiB value GET | 第 1 轮 | 第 2 轮 | 第 3 轮 |
|---|---:|---:|---:|
| 完整响应耗时（秒） | 1.822642 | 1.832467 | 1.819850 |
| 进程读取字节增量 | 18,989,056 | 18,989,056 | 18,989,056 |
| 完整 payload 校验 | 通过 | 通过 | 通过 |

[原始回放和二进制身份](grouped-verified-root-candidate-replays.json) · [逐操作耗时/I/O 汇总](grouped-verified-root-candidate-summary.json) · [可复现校验脚本](summarize-root-candidate-replays.py)。每轮还完成三个 5009 字节 key 的读取、覆盖后 STRLEN，以及 6 MiB/9 MiB key 的 SET 应答；没有覆盖后重启或读回两个大 key 的新值，不能据此宣称完整持久性验证。进程 I/O 包含后台工作，不能把它与先前采样超时的约 9 GB 直接作干净配对比值。

这是三轮候选单侧检查，**不是完成的三轮配对性能比较**。保留 main 的原始 60 秒超时及此前约 50 秒成功记录，不从截断基线算精确加速比，不外推普通 QPS。目前仍不能认定 #267 引入该故障，或原 CI 的 SET 超时与该 GET 同源。普通短 key native 回归与配对性能对照均已完成，普通路径的性能代价见下文。

## 普通短 key 原生验证与 72 点性能对照已完成

[当前原生验证驱动](../grouped-expiry-recovery-20261004/validate-grouped-root-native-reviewed-ci.py)固定父版本 `19496654` 与根复用 `28d7cca4` 的生产配置、依赖和二进制 SHA，使用相同测试驱动检查 Hash/Set、String/List、ZSet、Stream、RDB/跨 worker 和阻塞读路径。候选已通过 128 个相关单元测试，两边集成回归均为 68 通过、28 跳过、零失败；[完整结果及输入哈希](grouped-root-native-complete.md)。原生生产关闭故障注入，候选完整 fault-enabled CI 与父版本已通过的 CI 用例补充覆盖；父版本 CI 整体失败的限制见下文。复用已有测试，没有新增重复磁盘 fixture。

[当前 72 点普通短 key 对照驱动](../grouped-expiry-recovery-20261004/repeat-grouped-root-controls-reviewed-ci.py)已在原生验证通过后完成：Hash/Set 1 MiB / 128 B / 500 keys，List/ZSet 64 KiB / 128 B / 64 keys，Stream 64 KiB / 1024 B / 64 keys；五种类型均在 c320 测点读和写，List/Stream 另测 c80 全量读取。三轮 A/B、B/A、A/B，每点 30 秒、pipeline=1；读对共用新建父版本逻辑数据并分别重启，写对分别新建数据。物理后台变化仍可能存在。Hash/Set 的 500 keys 小于历史图中的 50,000 keys，不能用于更新历史 peer 排名。

[原始固定协议](grouped-root-native-controls-protocol.json)保留；其中“两边 CI 全绿”的前提已在[前置检查修正记录](../grouped-expiry-recovery-20261004/grouped-root-reviewed-ci-preflight.md)中纠正。父版本 CI 的唯一实际失败是外部源 Redis 的 cluster bus 端口占用，整体仍标为失败，不将这一导入场景当作已验证。原任务在编译前停止后，修正后的原生验证已接续组合对照取得主机锁并完成两边回归；72 点对照随后完成。完整配对 QPS/p99 结果见下文；普通点读回退和写入波动保留，#282 继续保持草稿。

## 原 SET 超时：独立覆盖写入诊断已完成

#267 已根据当前 head 的完整 CI 和已有重复配对测量转为非 draft。#282 的长 key GET 回放通过不能解释原 CI 的 `SET key_bytes=5009` 超时；两者的失败阶段不同，原始失败记录继续保留。

[已冻结的诊断协议](pr267-overwrite-diagnostic-protocol.json) · [诊断脚本](diagnose-pr267-overwrites.py)。使用原 `19496654` / `343e951e` 的精确 amd64 CI 二进制，两轮 A/B、B/A，各自从只读 768 MiB 原始镜像复制独立文件。2 workers 下检查并覆盖三个 5009 B key，随后改为 3 workers 重启，逐字节读回三个 `small` 值。保留原 60 秒 socket 和 120 秒关闭限制；每次操作记录进程 I/O，启动/结束记录 INFO，失败后才附加调试器。所有复制、镜像校验和进程运行都受原主机锁串行约束。

该诊断刻意跳过此前的多 MiB key 大 GET，以免读取超时遮住后续覆盖路径，因此改变了原 CI 的命令历史和后台运行时间；INFO/进程快照也有诊断扰动。它用于缩小覆盖写入问题的范围，不是原始完整测试复现、配对吞吐或修复证明。原始失败镜像与完整测试结果不变。该固定协议随后已完成，结果见下方“完成”的诊断记录。

## 根记录复用候选的独立 perf 验证

[固定协议与进程身份](grouped-root-candidate-profile-protocol.json) · [采样驱动](profile-grouped-verified-root-candidate.py)

`28d7cca4` 的三次候选诊断采样已完成并通过核验，完整结果见[候选 perf 报告](grouped-root-candidate-perf.md)。每次使用保留的只读恢复镜像的新副本、固定 CI 二进制、2 workers 和原 60 秒 socket / 120 秒关闭限制，保留此前 16 个命令的顺序。只对 9 MiB key 的完整 GET 采集全进程线程的 49 Hz task-clock / 8192 字节 DWARF，同时记录命令前后进程 I/O、CPU 计数和每 0.5 秒的线程进度。全部 GET payload 逐字节验证；服务退出后仍持锁解码 perf，失败保留并停止。

此检查用于确认重复长 key 校验的 CPU/I/O 是否消失及定位残余成本。早先 main / #267 的超时采样不重跑，不能与本次候选构成同期配对；短请求的样本量、后台工作和调用栈完整性均限制归因。采样耗时不进入 QPS 表，也不替代普通短 key 的 native 与 72 点对照，不证明原 #267 的 SET 超时已修复。

### 覆盖写入诊断结果

固定旧 main `19496654` 与失败候选 `343e951e` 的原 CI 二进制，两轮 A/B、B/A 的四份独立镜像全部通过：48 个操作，包含 12 次覆盖写入、12 次立即读回及 12 次换成 3 workers 后的读回，8 次服务正常退出。每个 key 长 5009 字节；先确认旧 value 长 9 MiB，再写入并逐字节核对 `small`。保持原 60 秒 socket / 120 秒关闭限制，不采样、不提高超时。

[原始结果与进程计数](pr267-overwrite-diagnostics.json) · [核验摘要](pr267-overwrite-diagnostic-summary.json) · [核验脚本](summarize-pr267-overwrites.py) · [日志与 INFO 快照清单](pr267-overwrite-evidence-index.json)。执行驱动 SHA 与原协议一致；原镜像每组前后校验保持不变。

此诊断刻意跳过原先的大 value / 巨型 key GET 序列，改变了命令历史与后台时序；它只说明该保留镜像上的简化覆盖写入及重启读回可通过。未重现原 CI 的 `SET key_bytes=5009` 超时，不能据此确认根因、宣称 #282 修复该 SET 问题或确认 rebased #267 通过。原失败保留；#267 当前 head 的完整 CI 单独通过并已转正式评审，不将这里的诊断当作当前 head 验证或性能比较。

## #282：全部 72 点普通 key 对照与处理结论

[完整绝对值、逐轮变化和原始记录](grouped-root-controls-complete.md)已完成：12 个条件、两版本、三轮 A/B、B/A、A/B；数据基数、源码/二进制身份、命令计数、正常退出和原生回归均核验。变化均为三轮配对百分比的中位数，不是两个版本中位数之比。

| 命令 / 并发 | 配对 QPS 变化 | 配对 p99 变化 | 三轮取舍 |
|---|---:|---:|---|
| HGET / 320 | −0.45% | −0.82% | QPS 三轮均下降；p99 方向混合 |
| SISMEMBER / 320 | −0.27% | −0.83% | QPS 三轮均下降；p99 方向混合 |
| ZSCORE / 320 | −1.13% | +3.57% | QPS 三轮均下降；p99 两轮变差 |
| SADD/SREM / 320 | −3.08% | 0.00% | QPS 三轮为 −3.08%、+3.43%、−9.89%，不能称为稳定收益 |
| ZINCRBY / 320 | −1.64% | 0.00% | QPS 三轮为 +2.37%、−1.64%、−5.09% |
| LSET / 320 | +0.67% | 0.00% | QPS 三轮均提升；p99 一轮相同、一轮改善、一轮变差 |
| XADD_MAXLEN / 320 | +0.22% | −3.21% | QPS 方向混合；p99 三轮均改善 |

HSET、LINDEX、LRANGE、XRANGE 与全量 XRANGE 的完整结果同样保留在 12 行总表和 36 行逐轮表中。普通路径大多接近基线，但不可称为零回退或普遍提升；三轮方向一致也不等于统计置信区间。Set 写入第三轮 QPS 与第二轮 ZINCRBY p99 的不利结果没有剔除。

#282 有明确的长 key 候选回放收益，因此保留候选；但普通点读的持续下降与写入波动尚未解释，暂不建议合并，继续 draft。长 key 的原始基线超时仍保留，不从截断数据推导精确倍数；普通 key 对照不能解释历史 #267 的独立 SET 超时，也不建立与其他系统整体追平。

[冻结与 rebased 补丁对应关系](pr282-frozen-rebased-correspondence.json)：`28d7cca4` 与 `2c94e9da` 的 range-diff 相等；三个读路径文件字节一致，`impl.h` 的差异与两边父版本的差异相同，来自 main 已合入的恢复声明和磁盘空间错误类型。性能结果仍绑定旧父版本与候选，不转记为当前 main 或 rebased head 的吞吐。

[全部观测](grouped-root-controls-complete-observations.json) · [矩阵核验与配对值](grouped-root-controls-complete-summary.json) · [命令计数核验](grouped-root-controls-complete-command-audit.json) · [校验器](summarize-grouped-root-controls.py) · [表格生成器](render-grouped-root-controls.py) · [执行日志](grouped-root-controls-reviewed-ci-driver.log) · [发布输入 SHA256 索引](grouped-root-controls-complete-evidence-index.json)。原始客户端对齐空白、INFO 尾部空行均按原字节保留。
