# Hash/Set 单路由替换

[草稿 PR #276](https://github.com/eloqdata/lavik/pull/276) 从 main `19496654` 开始，候选提交 `27c65ff9`。[现有 perf](../hashset-write-20261004/README.md) 的 HSET 采样中，`SetNode` 自身占 3.28%、`Balance` 占 0.67%、目录 `Apply` 占 0.54%；这些比例包含全部 worker 的轮询、后台和内核工作，不是延迟占比或预计收益。

单个活跃叶子的替换现在通过一次 AVL 遍历返回旧元数据并构造新路径。相同前缀区间保证拓扑不变，因此省去独立精确/前驱/退休目录查询和插入平衡检查；旧元数据仍用于核对字段总数、group 总数和 payload 总量。递归辅助函数借用不可变元数据，减少逐层按值复制。它仍分配相同数量的路径节点，旧快照继续持有原节点；多叶拆分与退休保留原覆盖校验。

新增测试保留 32 次非单调替换的所有旧版本，核对 revision、字段数、物理 token 和字节总量，并检查区间变更、缺失路由、溢出及 OOM 失败后的原子性、重试和内存计数恢复。格式检查和 `git diff --check` 通过；[远端 CI](https://github.com/eloqdata/lavik/actions/runs/37255329628) 已全部通过：amd64/arm64 构建、12 个软件测试分片、格式及汇总共 17 个 job（[精确提交记录](pr276-27c65ff9-full-ci.json)）。本地原生验证也已完成，见下文。

原生验证在统一主机锁下完成，覆盖 Hash/元数据单元测试及 Hash/Set 集成驱动，并冻结了两个生产二进制和 SHA-256；候选的构建恢复过程见下文。生产构建关闭测试及故障注入，故障覆盖由完整 CI 补充。原生验证已通过，Hash 的 72 点三轮对照已完成：大 Hash 的 HSET c5120 提升，但较小 Hash 的 HSET 在三个连接数均回退，具体 QPS/p99 见下方完整结果。Set 的 72 点对照仍在运行，独立 perf 等全部对照完成后采集；PR 保持草稿。架构、磁盘格式、durability 和快照所有权没有改变。

## 对照与 perf 调度

[干净对照](repeat-hash-route-replace-resume.py) 已在原生验证完成后取得主机锁开始运行。Hash 和 Set 各覆盖 500 个 100 MiB key（1024 B 元素）及 50,000 个 1 MiB key（128 B 元素），沿用报告对应的数据规模。每个版本独立恢复同一校验过的 RDB 内容并重启，路由种子和物理图分别生成。三轮 A/B、B/A、A/B，各在 c80/320/5120 测 30 秒 HGET/HSET 或 SISMEMBER/SADD_SREM，共 144 个观测，保留 p99、错误、二进制来源和完整基数校验；首个失败条件结束后停止。Set 的添加/删除可能为无操作，统计命令 QPS，不等同于 durable mutation 数。

[独立 perf](profile-hash-route-replace-resume.py) 等上述全部观测成功后，分别为父版本/候选的 HSET 和 SADD/SREM 新建 500 key、100 MiB、1024 B 数据，在 c320 采集 30 秒命令/计数窗口及 25 秒、99 Hz 的逐 worker task-clock/DWARF。[采样驱动](profile-hash-route-allworkers.py) 保留零样本辅助线程。采样 QPS 不混入干净对照；错开的计数和 CPU 窗口不换算成 CPU/命令。原始 perf 与线程栈仅留本地，后续选择小型摘要发布。144 点对照已开始；独立 perf 仍等待完整对照结束。

## 原生验证结果与构建恢复

父版本 `19496654` 通过 80 个单元测试，候选 `27c65ff9` 通过 82 个；两个生产二进制的 Hash/Set 驱动各 36 例，均为 16 通过、20 个 fault-only 跳过、0 失败。完整 fault-enabled CI 补充跳过路径。测试耗时不是吞吐结果。

[固定二进制、驱动 SHA-256 与逐例结果](hash-route-replace-versions.json) · [父单元](hash-route-replace-parent-unit-tests.json) · [父集成](hash-route-replace-parent-native-tests.json) · [候选单元](hash-route-replace-candidate-unit-tests.json) · [候选集成](hash-route-replace-candidate-native-tests.json) · [候选构建配置](hash-route-replace-candidate-CMakeCache.txt)。生产构建均关闭测试和故障注入。

候选的首次 GCC/native LTO 链接因 `/tmp` 空间不足失败，[原错误摘录](candidate-native-enospc.log)保留。[续跑](resume-hash-route-replace-native.py)仅将 `TMPDIR` 移至 `/mnt/dev`，保留源码、编译选项和已通过的父版本，随后完成候选链接、单测与原生验证。没有删除失败记录，也没有把 CI 通过当成本机生产验证。

生产二进制的测试通过情况只说明上述覆盖通过；是否保留这项优化由下方配对性能结果决定。

## 依赖版本记录更正

原脚本在空的 `source_repo/bycorf` 目录执行 `git rev-parse HEAD`，Git 向上查找，错误地把 Lavik 提交号记成了 `bycorf_commit`。归档 CMake 配置实际选择 `/mnt/dev/lavik-set-hash-20260929/bycorf`；该 checkout 当前为 `62509c93`，HEAD reflog 显示最后一次切换发生在 10 月 3 日，早于本次构建。更正后的清单保留原字段为 `bycorf_commit_recorded`，附当前观察时间和嵌套依赖状态；这属于构建后来源核对，不是独立的构建时源码快照，也不宣称递归依赖全部干净。实际二进制、测试驱动 SHA 与所有测试结果没有改变。

[错误字段、配置哈希、源码路径和核对证据](native-dependency-provenance-correction.json)。[来源解析器](native_build_provenance.py)现从 CMake 读取实际依赖目录，并要求它是独立 Git 根目录，避免空子模块目录再次回落到父仓库。原始工作区测量清单保留；后续对照产物若带旧字段，以此更正为准。


## 100 MiB Hash 三轮对照已完成

[完整 36 点配对结果](hash-route-large.md)：HSET c5120 配对 QPS 中位 +7.81%，三轮均提升，p99 中位 −8.19%；c80/c320 收益较弱且混合，HGET 仍有小幅回退。较小 Hash 的完整结果见下一节；Set 和独立 perf 尚未完成，不据单个获益子集把 PR 标为可合并。


## Hash 1 MiB/key / 128 B / 50000 keys 三轮对照已完成

[全部 36 点与历史对照差距](hash-route-hash-small.md)，包含每轮 QPS/p99 变化和原始来源核验；独立 perf 与其余范围的状态单独记录。


较小 Hash 的 HSET 三个连接数 QPS 中位均下降（−0.91%/−2.86%/−2.08%），p99 中位均变差；HGET c5120 三轮吞吐下降、尾延迟改善。[逐轮数据与解读](hash-route-hash-small.md)。因此目前只有部分大 Hash 条件获益，不能据此把 #276 视为普遍优化；Set 和独立 perf 继续验证。
