# PR #283 与当前 main 的配对测试

按用户 rebase 后的版本重新固定比较：main `5a3903d9b3c0632e3b34e827b779d9daa58455c2`，候选 `ace4198b0e1080cbb5116d40817b4dcc38f7ff8c`。候选的直接父提交即本次 main。旧父版本 `838a290f` 的构建已停止，没有产生本轮性能测量。

状态：两边原生构建、grouped 单元测试和 ordered/grouped 集成套件已通过，144 点配对已完成，原始结果、基数、命令计数与干净退出均通过核验；四组独立 perf 也已完成并通过核验；main 全量刷新已完成：28/28 组吞吐、4/4 组导入，见 [本轮 main 测量](../main-5a3903d9-20261006/README.md)。固定 main 与候选的新 CI 均为 17/17 成功，分别见 [main CI](parent-full-ci.json) 和 [候选当前 CI](candidate-current-ci.json)。`candidate-full-ci.json` 保留初次查询时的进行中状态，不作为最终通过证明。

## 完整对照的结论

**有局部小幅收益，但没有稳定的整体写入 QPS 提升；当前不建议直接合并，#283 保持 draft。** 24 个条件各三轮，共 144 个观测，均通过原始 QPS/p99、实际命令、请求计数、全部 key 基数和干净退出核验。[完整绝对值与逐轮结果](pr283-complete.md) · [独立 perf](pr283-perf.md) · [性能证据文件索引](performance-evidence-index.json)。

| 条件 | 配对 QPS 变化中位数 | 轮次与尾延迟限制 |
|---|---|---|
| 大对象 ZINCRBY，c80/320/2560/5120 | +0.48% / +0.45% / −0.48% / +0.53% | 四档 QPS 方向均混合，无稳定收益 |
| 小对象 ZINCRBY，c80/320/2560/5120 | +2.53% / +1.80% / +0.51% / +1.57% | c320/c5120 QPS 三轮均升；c320 p99 中位 +3.01%，c5120 p99 三轮均改善、中位 −3.01% |
| 大对象普通分值 ZADD，c80/5120 | −0.98% / +1.22% | QPS 方向混合；c5120 p99 三轮均改善、中位 −15.04% |
| 大对象全零分值 ZADD，c80/5120 | −0.81% / +1.34% | QPS 方向混合；p99 中位 +1.82% / +0.44%，c5120 约 239–241 秒 |
| 小对象普通分值 ZADD，c80/5120 | −2.16% / +0.67% | QPS 方向混合；c80 p99 中位 +5.26% |
| 小对象全零分值 ZADD，c80/5120 | +3.68% / +5.21% | QPS 方向混合；c80 p99 三轮均改善、中位 −4.07% |

大对象 ZSCORE c2560/c5120 的 QPS 三轮均升，中位 +3.87% / +1.06%；c2560 p99 三轮均改善，中位 −4.19%，c5120 p99 方向混合。其余大对象读取以及小对象 c80/2560/5120 的 QPS 方向混合。

**小对象 ZSCORE c320 是未解释的异常：** QPS 两轮下降 37.32% / 36.12%，一轮增加 1.30%，配对中位 −36.12%；p99 三轮均变差，中位 +315.15%。六个测点的客户端参数完全一致，服务端参数仅二进制和日志路径不同，原始请求及 INFO 计数吻合。较慢的候选出现在 A/B 顺序的两轮，B/A 轮接近 main；这是相关现象，不能确定是代码回退还是顺序效应。[六点配置、绝对结果与限制](small-read-c320-audit.json)。不删除这些观测，也不把当前 CI 通过等同于无性能回退。

`--test-time=30` 是配置时长。大同分值 c5120 的外层客户端调用约需数分钟，memtier 的 Runtime 与外层耗时明显不同。完整表另外给出“请求数 / 外层调用秒数”：该辅助口径在大同分值 c80/c5120 的配对中位为 −3.47% / −1.10%，前者三轮均下降。它含启动、SSH 与请求排空，不是服务器单独吞吐，也不替换原始 memtier QPS。[分析口径补充及加入时间](duration-analysis-amendment.json)说明它是在观察到长排空后添加，全部 24 条件一致计算；测量协议和超时没有改变。

四组 ZINCRBY c80 perf 各有 12 个有样本 worker 和 1 个零样本辅助线程，丢失样本为零。大/小对象 mimalloc 自身 CPU 占比分别从 3.899% → 3.483%、5.207% → 4.570%；memmove 为 2.324% → 2.202%、3.350% → 3.241%。这些小幅变化符合减少临时分配和复制的方向，但不是分配次数或绝对 CPU 节省的测量。大对象 SipHash 占比上升，小对象下降。源码仍保留存储读取和重写编码，独立写入采样的物理 I/O 计数差异不能归因为删除了磁盘读写。这四组写入采样没有覆盖上述 c320 读取异常，不能解释它。

原报告 28 组 main 曲线和 4 组导入单独刷新；三轮 PR 对照不与其 8/10 秒单次扫描混合，也不据此声称追平其他系统。

## 协议与复现

[固定协议](protocol.json) · [原始原生构建和验证](validate-native.py) · [修正临时目录后的完整原生验证](validate-native-private-tmp.py) · [对照驱动](repeat-controls.py) · [实际命令及同分值预置](run-zset-controls.py) · [perf 与 main 刷新顺序](refresh-main.py)。这些脚本保留本次运行的绝对工作路径；共享主机锁和依赖来源来自既有基准工作区。

两边使用相同 GCC/native/SPDK 生产配置，关闭测试故障注入，先执行原生回归，再串行测量。保持原报告 12 个 worker、pipeline=1 和独立客户端。正式 QPS 与 perf 分开运行。

配对测试共 144 个测点：100 MiB/key、1024 B/member、8 keys，以及 64 KiB/key、128 B/member、64 keys。ZSCORE/ZINCRBY 使用 c80/320/2560/5120；ZADD CH 使用 c80/5120，分别预置不同分值和全零分值。每个条件三轮 A/B、B/A、A/B，每点 30 秒。读取对共享父版本新建的逻辑数据并分别重启；写入对各自独立新建。保留全部 QPS、p99、失败和不利结果。

ZADD 对八个成员交替设置分值 0/1；随机 key 和并发可能产生同分值 no-op。因此将报告命令吞吐，不把每个请求计为实际成员修改。全零分值预置在两边均按成员降序插入，避免每批从头扫描越来越长的同分值页；最终成员集合、分值和测量命令不变。此预置调整在任何配对测量开始前完成并记录于协议。全零分值预置逐 key 检查 ZCOUNT；所有条件在测量前后检查 key 和成员基数。

配对测量后，对两种大小各采集 main/候选的 ZINCRBY c80 perf，分别使用新建数据。CPU 采样为每个 worker 独立 99 Hz task-clock / 16 KiB DWARF、25 秒窗口；命令及计数窗口 30 秒，采样占比不等同每命令 CPU 时间或分配次数。

随后以同一个 main 生产二进制刷新报告原有 28 组吞吐和 4 组批量导入。原报告曲线在复测完成前继续保留原始提交标记，不将历史结果改名为新 main。Redis、Valkey、Kvrocks 保留历史匹配负载，持久化及缓存设置差异仍适用。

## 原生验证的临时盘限制

首次 main 完整原生回归中，`LargeRdbRoundTripKeepsMessagesAndDeletedPendingBounded` 的 RDB 导入失败，日志明确为 `RDB scratch file: No space left on device`。当时系统 `/tmp` 所在文件系统仅余约 833 MiB。源码使用 `std::tmpfile()`，独立 glibc 调用确认实际落在 `/tmp`，不会使用构建环境的 `TMPDIR`。原始失败没有改成成功，也不归因于尚未执行的候选。

[原始 GTest 记录](pr283-parent-native-tests.json) · [原始完整日志](pr283-parent-native-tests.txt) · [环境修复记录](scratch-environment-repair.json) · [隔离临时目录启动器](private-tmp-exec.py)。旧 native、配对和 main 刷新队列均已终止，后两者在前置检查停止，没有性能观测；旧日志分别保留。

新的测试进程在独立 mount namespace 中把任务目录映射为 `/tmp`，使用约 143 GiB 空闲的数据盘，宿主机 `/tmp` 和权限保持不变。两边生产二进制及性能驱动使用同一临时盘策略；没有修改生产代码或超时，没有跳过失败测试。main 使用字节相同的二进制重跑完整原生回归，再构建并运行候选。这是本次 ENOSPC 的环境修复，不解释历史 PR #275 的不同超时。

## 本次原生验证范围

| 版本 | 单元测试通过 | 集成测试通过 | 故障注入用例跳过 | 失败 |
|---|---:|---:|---:|---:|
| main `5a3903d9` | 128 | 74 | 34 | 0 |
| #283 `ace4198b` | 128 | 75 | 34 | 0 |

[验证摘要](native-complete-summary.json) · [main 完整集成日志](pr283-parent-native-tests-private-tmp.txt) · [候选完整集成日志](pr283-candidate-native-tests-private-tmp.txt) · [匹配构建证明](matched-build-proof.json) · [二进制与测试版本记录](pr283-versions.json)。两边均关闭故障注入；34 个跳过是该生产配置下的故障注入用例，`lavik_grouped_ordered_write_e2e_test` 使用 `--gtest_filter=*`，未筛选该可执行程序中的测试；这不代表运行了仓库每一个原生集成目标。128 个单元测试选择 `GroupedCollectionTest.*:GroupedHashTest.*:HashGroupEdits.*:HashLookupMemoryTest.*:GroupedObjectIndexTest.*:GroupedMetadataArrayTest.*`。候选多一个页内二进制成员回归用例。原始 ENOSPC 和修复后的通过结果分别保留，不能据此解释其他历史失败。
