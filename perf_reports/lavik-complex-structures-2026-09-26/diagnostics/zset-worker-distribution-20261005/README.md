# 八个 key 的 worker 分布与 ZINCRBY perf

这不是新增吞吐结果。固定 12 workers 的原始基线和 PR 对照保持不变；这里只解释已有 perf 的线程分布，并记录后续配置诊断。

报告使用 `complex_1` 到 `complex_8`。在实际采样提交 `067c7589` 和 `d012a301`，`StorageShardForKey` 等于 Redis CRC16 slot，`OwnerForKey` 为 slot `% worker_count`；这与字段路由使用的随机 SipHash seed 无关。[候选来源公式](https://github.com/thweetkomputer/lavik/blob/d012a3013da99344a419bb692f834b17fd6dcad4/src/storage/engine/impl.h#L1977) · [slot 计算](https://github.com/thweetkomputer/lavik/blob/d012a3013da99344a419bb692f834b17fd6dcad4/src/storage/format.cpp#L356)。

| 数据 owner（12 workers） | key | Redis slot |
|---:|---|---|
| 1 | complex_1, complex_5 | 9133, 9001 |
| 6 | complex_2, complex_6 | 5070, 4938 |
| 8 | complex_4, complex_8 | 13064, 12932 |
| 11 | complex_3, complex_7 | 1007, 875 |

因此，12 个服务 worker 下，这八个 key 只有 **4 个数据 owner，每个持有 2 个 key**。这不表示其他线程没有工作：网络、轮询、后台和跨 worker 请求仍可使用它们。也不能据此推导吞吐随 owner 数线性增长。

独立 ZINCRBY c80 采样中，两版本均有 4 条线程的 task-clock 估算值明显高于其余线程：

| 版本 | 总 task-clock 估算秒 | 最忙四线程估算秒范围 | 其余有样本线程估算秒范围 | 最忙四线程占比 |
|---|---:|---:|---:|---:|
| previous `067c7589` | 131.990 | 22.253–22.576 | 4.929–5.970 | 67.86% |
| candidate `d012a301` | 133.919 | 22.323–22.828 | 5.091–6.131 | 67.42% |

这些来自已有的 25 秒逐线程 task-clock 采样，命令/服务指标窗口为 30 秒；不相除计算 CPU/命令。没有捕获 TID 到 worker ID 的直接绑定，四条忙线程与源码的四个 owner 分布一致，但不能逐条对应。均保留零样本辅助线程，CPU 包含网络、内核、轮询和后台工作；并非纯粹的 ZINCRBY 执行时间。这里没有任何 ZSCORE 的采样结论。

[完整 key/slot 映射、逐线程数据及来源哈希](zset-worker-distribution.json) · [可复算脚本](analyze-zset-worker-distribution.py) · [原 perf 来源和限制](../zset-member-probe-20261004/zset-source-reuse-perf.md)。脚本逐提交核对路由公式，以独立逐位 CRC 实现和 Python CRC 实现交叉核对所有八个 key，再核对每线程事件数之和。

## 已排队的配置对照

同样八个 key 在 8 workers 下对应 8 个不同数据 owner；这是源码计算，还没有吞吐证据。[对照驱动](repeat-zset-worker-count.py) 固定已通过原生回归和完整 CI 的 `067c7589` 二进制，按 12/8、8/12、12/8 三轮独立重新预置。固定 100 MiB/key、1024 B/member、8 keys，ZSCORE 和 ZINCRBY 均测 c80/c320、30 秒、pipeline=1，共 24 点。

[运行适配器](run-zset-worker-controls.py) 只改变标准 server 命令的 `--threads`；同一硬件、CPU 集合、数据设备、EAL 内存和其他选项保持。每 worker 资源池和线程放置自然随 worker 数变化，因此任何效果都属于配置对照，不能只归因于 owner 分布，也不能记作实现优化收益。所有 key 基数、来源、错误和退出码继续核对。

每点前后各读取一次 `/proc` 线程 CPU 计数；这包括客户端启动、收取结果及后台 CPU，不能当作命令独占 CPU。实验排在现有 ZSCORE 验证/对照/采样之后，独占同一主机锁；没有同步编译、测试或 perf。待完整三轮结果后判断该配置是否有用，不修改当前报告的 12-worker 对照曲线。
