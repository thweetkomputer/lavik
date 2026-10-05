# 内联页查找与解码摘要：独立对照

**当前 PR 与 CI：** 见[统一收敛状态](../grouped-expiry-recovery-20261004/pr-cleanup-current.md)。下述原生、CI 和性能数据仍归属各自标注的提交；固定历史版本的测量不能代替当前 head 验证。

**处理：** #271/#272 已因完整对照的整体取舍不足关闭，分支保留。[远端关闭记录](grouped-lookup-pr-closures.json)。

[PR #271](https://github.com/eloqdata/lavik/pull/271) 跳过内联页不需要的 extent 清单查找；[PR #272](https://github.com/eloqdata/lavik/pull/272) 复用已解码字段摘要。这两项分别基于 #266，不将收益相加，也没有合并为一个候选。

| 角色 | 固定提交 | 完整 CI |
|---|---|---|
| Parent | `067c75891f819831620e277eac0592c360f8b585` | [17 项通过](https://github.com/eloqdata/lavik/actions/runs/37241392671) |
| Inline (#271) | `2e6e4f3559d284e6fe5d0dddc7eb1de5929761ae` | [17 项通过](https://github.com/eloqdata/lavik/actions/runs/37241742696) |
| Decoded (#272) | `8babe581213f2cd781f13665a45fdbf1012cf449` | [17 项通过](https://github.com/eloqdata/lavik/actions/runs/37241670139) |

## 状态与前置验证

[原生验证](validate-grouped-lookup-native-pinned-after-rebase.py)已完成；[完整 72 点对照](grouped-lookup-complete.md)已完成并通过逐点核验；两项有局部收益及反向结果，本轮决定不继续保留。Inline/Decoded 分别通过 128/129 项单元检查；每个候选另通过 42 项有序结构、5 项阻塞命令、16 项 Hash 进程测试。各有 29 项依赖故障注入的进程测试因生产构建关闭 hooks 而跳过，逐项原因公开。父版本复用先前的 20 项通过、7 项跳过，未声称与候选覆盖完全相同。[精确二进制、构建选项、driver 哈希及逐项结果](grouped-lookup-native-summary.json)。历史固定 head 的 fault-enabled CI 均完整通过；当前 rebased head 仍需单独检查。

吞吐任务已等待原生验证与既有 worker 数实验退出，重新核对所有版本的原生测试、完整 CI、依赖版本、SHA-256 及构建选项（包含 `LAVIK_MARCH=native`），再取得统一主机锁。构建、预置、测试、干净压测及 perf 不并行。脚本在排队时冻结驱动文件 SHA，取得主机锁后再次检查，避免等待期间更换驱动而未记录。

## 测量范围

三个版本按 Parent/Inline/Decoded、Inline/Decoded/Parent、Decoded/Parent/Inline 轮换，使每个版本各占一次运行位置。每个候选仅与同轮的共同父版本配对；三轮不构成置信区间，两个候选不是两组独立父版本样本。

每轮 ZSCORE 在同一份新建的父版本逻辑数据上依次重启三个版本，中间不执行写命令；后台物理变化仍可能发生，不称作不可变磁盘快照。ZINCRBY 为每个版本分别新建数据，路由 seed 和物理布局独立。

条件为 100 MiB/key、1024 B、8 keys 和 64 KiB/key、128 B、64 keys；两个命令分别测 c320/c5120，30 秒、pipeline=1，共 2 × 2 × 2 × 3 × 3 = 72 点。保留全部 key 的前后基数、原始 QPS/p99、错误和退出码，遇到失败保留原始结果并停止。不会根据单个获益点隐藏回退。此轮不重新测 peer，也不证明 Hash、List、Stream 等其他命令的吞吐变化。

[排队记录、固定提交及脚本哈希](queued-protocol.json)。这些脚本保留本机绝对路径和 scratch 设备 allowlist；它们用于复现协议，移机执行需映射工作目录、生产二进制、主机锁和已授权 scratch 设备。原生验证会切换专用构建工作树，不能指向含用户改动的目录。未采集新的候选 perf；本轮去留依据完整干净对照，未声称已验证这些候选的热点变化。


[结果校验器](summarize-grouped-lookup.py)要求完整三轮矩阵才输出配对结论，逐点对照原始 result、来源 SHA、基数、退出码和共享读取 seed，同时检查实际执行顺序符合三个轮换。`--validate-only` 只核验已有观测，不输出不完整范围的性能结论。该脚本已在首批真实完成观测上执行通过；完整 72 点矩阵已通过。命令计数审计另用既有 `audit-zset-score-commands.py`；不会将源码少一次查找直接视为测得收益。

[完整结果与去留依据](grouped-lookup-complete.md)：保留全部大、小对象三轮正向及反向结果，不把局部读取收益当作普遍优化。
