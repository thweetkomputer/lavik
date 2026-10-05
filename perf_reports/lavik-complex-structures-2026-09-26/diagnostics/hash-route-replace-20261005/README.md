# Hash/Set 单路由替换

[草稿 PR #276](https://github.com/eloqdata/lavik/pull/276) 从 main `19496654` 开始，候选提交 `27c65ff9`。[现有 perf](../hashset-write-20261004/README.md) 的 HSET 采样中，`SetNode` 自身占 3.28%、`Balance` 占 0.67%、目录 `Apply` 占 0.54%；这些比例包含全部 worker 的轮询、后台和内核工作，不是延迟占比或预计收益。

单个活跃叶子的替换现在通过一次 AVL 遍历返回旧元数据并构造新路径。相同前缀区间保证拓扑不变，因此省去独立精确/前驱/退休目录查询和插入平衡检查；旧元数据仍用于核对字段总数、group 总数和 payload 总量。递归辅助函数借用不可变元数据，减少逐层按值复制。它仍分配相同数量的路径节点，旧快照继续持有原节点；多叶拆分与退休保留原覆盖校验。

新增测试保留 32 次非单调替换的所有旧版本，核对 revision、字段数、物理 token 和字节总量，并检查区间变更、缺失路由、溢出及 OOM 失败后的原子性、重试和内存计数恢复。格式检查和 `git diff --check` 通过；[远端 CI](https://github.com/eloqdata/lavik/actions/runs/37255329628) 正在运行，本地测试尚未执行。

[原生验证调度](validate-hash-route-replace-native.py) 等待当前 Stream 对照及独立 perf、精确候选完整 CI，然后取得统一主机锁，依次构建父版本和候选，运行 Hash/元数据单元测试及 Hash/Set 集成驱动，冻结生产二进制和 SHA-256。生产构建关闭测试及故障注入，故障覆盖由完整 CI 补充。未产生此候选的 QPS/p99 或新 perf 结果，PR 保持草稿。架构、磁盘格式、durability 和快照所有权没有改变。
