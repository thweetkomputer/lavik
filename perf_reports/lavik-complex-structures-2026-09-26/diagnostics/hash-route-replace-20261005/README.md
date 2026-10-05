# Hash/Set 单路由替换

[草稿 PR #276](https://github.com/eloqdata/lavik/pull/276) 从 main `19496654` 开始，候选提交 `27c65ff9`。[现有 perf](../hashset-write-20261004/README.md) 的 HSET 采样中，`SetNode` 自身占 3.28%、`Balance` 占 0.67%、目录 `Apply` 占 0.54%；这些比例包含全部 worker 的轮询、后台和内核工作，不是延迟占比或预计收益。

单个活跃叶子的替换现在通过一次 AVL 遍历返回旧元数据并构造新路径。相同前缀区间保证拓扑不变，因此省去独立精确/前驱/退休目录查询和插入平衡检查；旧元数据仍用于核对字段总数、group 总数和 payload 总量。递归辅助函数借用不可变元数据，减少逐层按值复制。它仍分配相同数量的路径节点，旧快照继续持有原节点；多叶拆分与退休保留原覆盖校验。

新增测试保留 32 次非单调替换的所有旧版本，核对 revision、字段数、物理 token 和字节总量，并检查区间变更、缺失路由、溢出及 OOM 失败后的原子性、重试和内存计数恢复。格式检查和 `git diff --check` 通过；[远端 CI](https://github.com/eloqdata/lavik/actions/runs/37255329628) 正在运行，本地测试尚未执行。

[原生验证调度](validate-hash-route-replace-native.py) 等待当前 Stream 对照及独立 perf、精确候选完整 CI，然后取得统一主机锁，依次构建父版本和候选，运行 Hash/元数据单元测试及 Hash/Set 集成驱动，冻结生产二进制和 SHA-256。生产构建关闭测试及故障注入，故障覆盖由完整 CI 补充。未产生此候选的 QPS/p99 或新 perf 结果，PR 保持草稿。架构、磁盘格式、durability 和快照所有权没有改变。

## 对照与 perf 调度

[干净对照](repeat-hash-route-replace.py) 已排队，等待原生验证全部完成后取得主机锁。Hash 和 Set 各覆盖 500 个 100 MiB key（1024 B 元素）及 50,000 个 1 MiB key（128 B 元素），沿用报告对应的数据规模。每个版本独立恢复同一校验过的 RDB 内容并重启，路由种子和物理图分别生成。三轮 A/B、B/A、A/B，各在 c80/320/5120 测 30 秒 HGET/HSET 或 SISMEMBER/SADD_SREM，共 144 个观测，保留 p99、错误、二进制来源和完整基数校验；首个失败条件结束后停止。Set 的添加/删除可能为无操作，统计命令 QPS，不等同于 durable mutation 数。

[独立 perf](profile-hash-route-replace.py) 等上述全部观测成功后，分别为父版本/候选的 HSET 和 SADD/SREM 新建 500 key、100 MiB、1024 B 数据，在 c320 采集 30 秒命令/计数窗口及 25 秒、99 Hz 的逐 worker task-clock/DWARF。[采样驱动](profile-hash-route-allworkers.py) 保留零样本辅助线程。采样 QPS 不混入干净对照；错开的计数和 CPU 窗口不换算成 CPU/命令。原始 perf 与线程栈仅留本地，后续选择小型摘要发布。上述任务均未开始测量。
