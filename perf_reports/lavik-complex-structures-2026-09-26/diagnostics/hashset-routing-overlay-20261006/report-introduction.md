# Hash/Set routing metadata：固定 digest seed 的写入对照

本轮优化已有 hash-prefix 的路由元数据替换：大目录暂存最多 8 个不可变覆盖项，反复修改同一前缀不再逐次复制 AVL 路径；覆盖项满时合并复制共享路径。目录少于 1024 项时沿用原路径，避免小对象额外分配。这里只缓存路由元数据，不缓存字段值或磁盘页；持久化格式、提交与恢复顺序不变。

基线为 main `5a3903d9b3c0632e3b34e827b779d9daa58455c2`，候选为 `caba8203c1ec03c7413895053281713fc62ed379`。测量期间 main 前进到 `d88a5e8f`；本报告没有把旧基线重新标作最新 main。Bycorf 实际源码提交、嵌套依赖状态、生产二进制 SHA256 和构建选项见 [构建证据](validated-versions.json)。

## 方法与边界

- 6 个负载范围 × 读/写/写后读 × 两个版本 × 三轮 = 108 个观测点。每点 30 秒，320 连接，pipeline=1，12 workers；AB/BA/AB 顺序。
- 标准负载包括 1 MiB/key、128 B/entry、50,000 keys，以及 100 MiB/key、1024 B/entry、500 keys。每组逻辑 payload 合计 50,000 MiB（48.83 GiB）。HSET 循环 8 个字段；SADD/SREM 循环一个测试成员。
- 额外大对象对照循环 64 个 Hash 字段或 64 个 Set 成员，用来暴露覆盖项频繁折叠的代价。Set 吞吐按所有命令计数，包含可能的无操作命令。
- 每个版本独立 RESTORE、重启后按读→写→写后读运行。每对使用同一 fixture 和同一 digest seed，三轮使用三个不同 seed。逐 key 检查基数，逐命令检查 INFO 计数、拒绝和失败，核验进程、二进制与种子身份及正常退出。
- 固定 seed 仅用于基准启动：两份未修改的生产二进制都使用相同的 LD_PRELOAD 启动 shim，在原 main 前设定 seed，经 `/proc/PID/mem` 核验。请求路径没有额外 hook。这不是产品配置，也不随 PR 发布。
- 六块独占 scratch NVMe、SPDK 持久化；客户端通过 TCP 连接。测试和编译不与压测或 perf 并行。完整配置及命令见 [协议](matched-seed-protocol.json) 和 [原始结果](matched-seed-repeats.json)。
- 以下为三次配对变化的中位数，不是汇总 QPS 的比例。三轮不能提供可靠的置信区间；本轮没有重测 80/5120 连接或另外三个系统，也不证明已达到同等性能。

## 为什么重跑

早期候选 `258c216c` 的 54 个唯一测点、4 份独立 seed 的 perf 全部保留，但不纳入最终估计。最初宽矩阵的 42 点与小 Set 对照的 18 点重叠 6 点，不能算成 60 点。

重新 RESTORE 会通过 `CurrentDigestSeed` 选择新的 Hash 分布。同一数据内容因 seed 不同，叶页布局和物理读取工作也会改变。早期小 Set 配对的每命令读取字节相差约 40%，因此不能将 QPS 或 perf 差异全部归因于代码。此前一次预置后内存差被猜测为每 key 固定开销，这个归因也没有得到证明。

最终候选把覆盖启用门槛从 64 提到 1024，并在固定布局的条件下重测。小对象作为无覆盖项对照保留；不能将其微小波动解释成覆盖机制的收益。旧候选、停止记录和第一次启动 shim 修正均在证据中保留。

## 验证

候选的原生单元测试 131 项通过；Hash E2E 16 项通过、20 项故障注入用例在生产构建跳过；有序结构 E2E 74 项通过、34 项故障注入用例跳过。故障注入另由同一 head 的 [完整 CI](https://github.com/eloqdata/lavik/actions/runs/37436501005) 覆盖，17/17 jobs 成功。

新增测试检查持久快照、Get/Floor/查找/遍历、擦除后重插、覆盖满后的合并，以及内存准入失败时原对象不变。小目录测试检查无覆盖分配。

[逐点命令与内存核验](matched-seed-command-audit.json) · [完整来源核验](matched-seed-final-audit.json) · [证据文件索引](evidence-index.json)
