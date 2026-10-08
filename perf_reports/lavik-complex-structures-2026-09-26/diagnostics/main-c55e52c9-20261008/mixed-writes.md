# List / ZSet 随机增删：四库对照

[主报告](../../README.zh-CN.md) · [全部图与源数据](../../current-mixed-writes.json) · [逐请求计数及逐 key 长度核验](mixed-command-audit.json)

本轮四库均重新运行：Lavik main `c55e52c9`，Redis 8.8.0、Valkey 9.1.0，Kvrocks 2.16.0（RocksDB 11.1.1，与原报告同一二进制）。各点的 INFO SERVER、二进制 SHA、启动参数、Kvrocks 有效配置和源提交在 raw 目录。

8 个 key，每 key 初始 value/member 逻辑字节为 8 MiB 或 100 MiB，元素 1 KiB。每请求独立均匀选 key，再独立以 50% 概率增或删；每点 30 秒，连接数 80/320/1280/2560，16 客户端线程，pipeline=1。客户端随机种子为 42；每点使用同一客户端二进制并核验 SHA。客户端运行在独立 172.16.0.5，固定 CPU 0–15。

List 对比 LPUSH/RPOP 与 RPUSH/LPOP。ZSet 使用唯一新成员的 ZADD NX，分别与 ZPOPMAX 或 ZPOPMIN 混合：头插分数持续降低，尾插分数持续升高，随机插入在原始分数区间均匀选分数。低分和高分方向按客户端发号分别递减或递增，分数始终低于或高于初始区间；多个连接在服务端的到达顺序可能重排，因此不保证每次都是绝对首位或末位插入。淘汰后随机分数也不代表均匀插入排名。所有 ZADD 必须实际插入，所有 pop 必须非空，计数、响应长度和每个 key 的净变化均核验。

每点单独启动服务并重新预填；Lavik 重新准备授权 scratch 介质，Kvrocks 使用新的数据库目录，避免仅 FLUSHALL 遗留 LSM 工作。List 用 RPUSH 预填，ZSet 按递增分数预填。Lavik 等待事务清理稳定；Kvrocks 等待两次间隔 2 秒的 flush/compaction 空闲快照；Redis/Valkey 预填后空闲 2 秒。预填和等待不计入 QPS。

Lavik 使用与之前 Fenwick 对照相同的固定启动 digest seed，并从进程内存核验；shim 仅在 main 前初始化种子，不挂请求路径，不改动生产二进制。其他系统保留自身内部路由。不同系统的相同逻辑请求不意味着内部物理布局相同。

Redis/Valkey 关闭持久化、12 个 I/O 线程；Kvrocks 使用 16 worker、同组六块 NVMe 的无压缩 RAID0，WAL 关闭、80 GiB block/blob cache；Lavik 12 worker、SPDK 持久化、8 GiB EAL，不缓存字段或页内容。主机总预算均为 16 vCPU；写入排名不代表相同持久性保证。

这是一次完整并发扫描，没有重复样本或置信区间。图中 QPS 统计命令数而非增删对数，p99 为混合请求分布；每个命令各自的 p99 也保存在 client/result JSON。时间驱动负载中吞吐不同会导致周转次数不同；等概率只约束期望，不保证无限期大小有界。

已核对当前选定的 160 点、1,378,577,614 条命令，INFO commandstats 与客户端计数完全一致；最终长度全部等于初始长度 + 实际增 - 实际删。

- 8 MiB/key：纳入曲线点的最大最终长度偏差 45.90%。
- 100 MiB/key：纳入曲线点的最大最终长度偏差 4.30%。

当前选定网格共 159/160 点满足预设长度范围并纳入曲线；1 点触发范围检查，保留原始数据并在图中留空，没有挑选重跑。

- valkey / ZADD_RANDOM_ZPOPMIN / 8 MiB / c320：初始 8192，最终最小 3884、最大 9607，预设范围 [4096, 16384]。客户端和服务器没有命令错误；[原始记录](../../raw/valkey-mainc55e52c9-mixed-zset-8388608-zadd_random_zpopmin-c320-20261008/workload-guard.json)。

正式测量的客户端、预填、随机序列与时长未改。第一次长度边界失败后，仅修改执行器以保留这种已完成测量且正常停服的失败，并继续后续点；其余错误仍停止执行。两版执行器、原始失败日志及 SHA 均保留。


连接档位已按用户要求去掉 5120。新增负载此前测完 200 点，其中 40 点只保留在原始存档，不进入当前曲线、汇总或长度偏差统计；当前图表选择 160 点。旧网格已测出的 5120 也只存档，后续扫描已跳过该档。见 [档位调整记录](connection-policy-change.json)。

## c320 截面

只是同一张并发图的 c320 截面，不从不同并发挑各系统最好值。完整曲线同时展示尾延迟。

| MiB/key | 操作 | Redis QPS | Valkey QPS | Kvrocks QPS | Lavik QPS | Lavik / 最快 peer |
|---|---|---:|---:|---:|---:|---:|
| 8 | LPUSH_RPOP | 645,995 | 639,283 | 262,152 | 12,348 | 1.9% |
| 100 | LPUSH_RPOP | 611,082 | 557,017 | 218,927 | 5,603 | 0.9% |
| 8 | RPUSH_LPOP | 627,862 | 681,669 | 262,317 | 54,626 | 8.0% |
| 100 | RPUSH_LPOP | 622,703 | 602,549 | 217,006 | 23,537 | 3.8% |
| 8 | ZADD_HEAD_ZPOPMAX | 488,860 | 482,956 | 2,843 | 9,957 | 2.0% |
| 100 | ZADD_HEAD_ZPOPMAX | 424,360 | 444,824 | 2,715 | 4,878 | 1.1% |
| 8 | ZADD_RANDOM_ZPOPMIN | 537,140 | guard fail | 4,560 | 22,770 | — |
| 100 | ZADD_RANDOM_ZPOPMIN | 399,494 | 400,772 | 4,468 | 4,663 | 1.2% |
| 8 | ZADD_TAIL_ZPOPMIN | 508,348 | 456,625 | 4,267 | 27,133 | 5.3% |
| 100 | ZADD_TAIL_ZPOPMIN | 426,692 | 414,662 | 4,416 | 14,373 | 3.4% |

| MiB/key | 操作 | Redis p99 ms | Valkey p99 ms | Kvrocks p99 ms | Lavik p99 ms |
|---|---|---:|---:|---:|---:|
| 8 | LPUSH_RPOP | 0.982 | 0.921 | 2.262 | 104.508 |
| 100 | LPUSH_RPOP | 1.021 | 0.948 | 2.685 | 192.815 |
| 8 | RPUSH_LPOP | 1.003 | 0.826 | 2.236 | 21.537 |
| 100 | RPUSH_LPOP | 1.007 | 0.922 | 2.815 | 41.553 |
| 8 | ZADD_HEAD_ZPOPMAX | 1.111 | 1.292 | 314.156 | 120.089 |
| 100 | ZADD_HEAD_ZPOPMAX | 1.001 | 1.420 | 315.528 | 228.452 |
| 8 | ZADD_RANDOM_ZPOPMIN | 1.128 | guard fail | 208.918 | 59.063 |
| 100 | ZADD_RANDOM_ZPOPMIN | 1.183 | 1.752 | 207.175 | 276.112 |
| 8 | ZADD_TAIL_ZPOPMIN | 1.118 | 1.651 | 208.667 | 47.657 |
| 100 | ZADD_TAIL_ZPOPMIN | 1.009 | 1.730 | 208.540 | 74.614 |

## 方法范围

当前 List 的满首页 LPUSH 会触发左侧装满的分裂，后续目录序号变化仍需目录重建；Fenwick 主要降低页拓扑不变时的计数更新成本。此处是当前 main 的跨系统实测，不把早先 `78c43ad9` 对 cumulative 的三轮变化比例作为本轮成绩。

[连接档位调整](connection-policy-change.json) · [客户端](random-client.cpp) · [混合运行器](run-random.py) · [执行顺序](run-mixed-suite.py) · [完整协议](protocol.json) · [20 个协议检查点](mixed-smoke-results.json)。短时兼容性检查不纳入图表。
