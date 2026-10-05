# 复杂数据结构性能：Redis、Valkey、Kvrocks 与 Lavik

Hash/Set 单路由替换的[全部 144 点对照](diagnostics/hash-route-replace-20261005/hash-route-complete.md)已完成。大 Hash HSET c5120 的 QPS +7.81% 未推广到其他范围：小 Hash HSET 与两种 Set 写入中位均回退，#276 保持草稿。完整 QPS/p99、反向结果和历史 peer 差距均已公开；独立 perf 继续验证。

[English](README.md)

[ZINCRBY worker 分布分析](diagnostics/zset-worker-distribution-20261005/README.md)：现有 8 个 key 在 12 workers 下仅落到 4 个数据 owner；已核对 perf 线程分布，固定二进制的 8/12-worker 配置对照已排队，尚无调参收益结论。

[ZSCORE/ZMSCORE 成员页借用视图](diagnostics/zset-score-views-20261005/README.md)：去掉整页字段/值复制，保留完整校验；fork 与上游 CI 各 17 项通过，[PR #280](https://github.com/eloqdata/lavik/pull/280) 保持草稿；96 点配对及独立读 perf 已排队，尚无性能结论。

长 key 诊断已更新：main 在同镜像无采样重放也触发 60 秒 GET 超时；旧版本 perf 显示 CRC、复制和比较热点，根记录复用候选仍待独立重放。[证据与限制](diagnostics/list-reply-reserve-20261004/README.md)。

**2026-10-04：main `a565d603` 已完成 28/28 组复测，包含已合并的 #244, #246, #247, #249, #258, #259, #260, #262。**

批量 HSET/SADD 导入另计：4/4 组已更新。

吞吐图固定命令、每 key 的 payload 大小、元素大小和 key 数；横轴为连接数，纵轴为 QPS。批量导入图显示完成固定数据量所需的秒数。只保留当前 main 和后续未合并 PR，其他三库保留同负载的历史实测。

Redis/Valkey 关闭持久化；Kvrocks 使用无压缩 RAID0、关闭 WAL、80 GiB block/blob cache；Lavik 使用六块 NVMe SPDK 持久化，不缓存字段或页内容。配置不同，写入 QPS 不代表同等持久性下的排名。

本轮不重跑其他三库。Lavik 使用 AMD EPYC 9V74、16 vCPU、12 个服务 worker。每点 8 秒，较多 key 的 LSET 为 10 秒；pipeline=1。每组独立预置并逐 key 校验，perf 采样在完整连接扫描后单独进行，不混入 QPS 图。单次扫描没有统计置信区间。

本轮固定使用上述 main 提交，已合并优化不再作为独立 PR 曲线显示。历史观察仍保留原始提交号；每完成一组独立复测才替换对应图。

[绘图数据清单](current-main.json) · [复现脚本](run.py) · [上一轮构建与硬件证明](diagnostics/main-refresh-20261004/host-and-build.json)

[完整 main 基线：逐命令差距与优化优先级](diagnostics/main-a565d603-20261004/main-gap-summary.md)

[本轮构建与硬件证明](diagnostics/main-a565d603-20261004/host-and-build.json)

[本轮 perf 分析](diagnostics/main-a565d603-20261004/README.md)

[本轮绘图数据核验](diagnostics/main-a565d603-20261004/report-audit.json)

[上一轮绘图数据核验](diagnostics/main-refresh-20261004/report-audit.json) · [上一轮核验脚本](diagnostics/main-refresh-20261004/audit-report.py)

[Hash/Set 写入 perf 分析](diagnostics/hashset-write-20261004/README.md) · [有序目录优化与测试](diagnostics/ordered-metadata-20261004/README.md)

未合并优化：[PR #265](https://github.com/eloqdata/lavik/pull/265) · [PR #266](https://github.com/eloqdata/lavik/pull/266) · [PR #267](https://github.com/eloqdata/lavik/pull/267) · [PR #269](https://github.com/eloqdata/lavik/pull/269) · [PR #270](https://github.com/eloqdata/lavik/pull/270) · [PR #276：Hash/Set 单路由替换（验证中）](diagnostics/hash-route-replace-20261005/README.md)

main 已更新至 `4610d607`；本页仍使用固定基线 `a565d603`。[组合验证分支及状态](diagnostics/combined-20261005/README.md)。[优化分支的新提交与验证状态](diagnostics/main-a565d603-20261004/pr-main-integration.json)，新提交尚未替换已测量二进制。

[Stream 尾部目录复用：吞吐、交替复测、perf 与测试](diagnostics/stream-suffix-20261004/README.md)

[Stream 回复批处理 PR #270：配对复测、控制项与 perf](diagnostics/stream-reply-20261004/README.md)

后续 singleton PR #274 的 60 点三轮对照已完成，未显示预期收益，已关闭：大/小对象点读 QPS 中位数 −0.39%/−3.18%；小对象两档写入为 −3.36%/−3.31%，三轮全降。四组独立 perf 已完成，完整来源及 CPU/I/O 摘要见上方诊断；不能把源码少一次复制当成已测得的吞吐提升。

[Stream 页内 key 校验复用原型](diagnostics/stream-key-validation-20261005/README.md) 已通过全部 17 个 CI 检查，仍待本机验证和性能对照，尚无 QPS 收益结论。

[ZSet 成员叶页复用：吞吐、交替复测、perf 与测试](diagnostics/zset-member-probe-20261004/README.md)

后续 [PR #271](https://github.com/eloqdata/lavik/pull/271) 消除内联页的重复清单查找；与 #272 的固定父版本原生验证和 [72 点独立对照](diagnostics/grouped-lookup-controls-20261005/README.md)已排队，尚无吞吐收益结论。

[PR #272](https://github.com/eloqdata/lavik/pull/272) 复用解码摘要，减少重复字段检查和路由校验中的哈希计算；仍为草稿，待上述独立对照完成。

[PR #273](https://github.com/eloqdata/lavik/pull/273) 复用单成员写入已经解码的有序源页并转移其内存预算。[大对象 48 点三轮结果](diagnostics/zset-member-probe-20261004/zset-source-reuse-large.md)：ZINCRBY 四档并发 QPS 配对中位数 +2.08%/+1.46%/+1.46%/−0.36%；高并发写 p99 改善，但读控制项 c5120 p99 中位数变差 14.81%。[小对象 48 点结果](diagnostics/zset-member-probe-20261004/zset-source-reuse-small.md)也已完成：写 QPS 中位数 +1.04%–+2.88%，但低两档读 QPS −3.00%/−2.22%、p99 +4.46%/+8.21%。[独立写 perf](diagnostics/zset-member-probe-20261004/zset-source-reuse-perf.md)已完成，未显示数量级成本下降；读回退原因尚待核对，保持草稿。

[List 范围读取：吞吐、内存准入、交替复测与 perf](diagnostics/list-read-window-20261004/README.md)

[List 回复空间预留：增量复测、复制热点与当前结果](diagnostics/list-reply-reserve-20261004/README.md)

[List 字节受限窗口：草稿 PR #269 配对复测、回退与 perf](diagnostics/list-byte-window-20261004/README.md)

[满盘过期恢复与 CI 修复（PR #268；历史观测保留原始二进制）](diagnostics/grouped-expiry-recovery-20261004/README.md)

本轮失败测点（图中留空，错误请求的吞吐不计为成功 QPS）：

- List LRANGE · 100 MiB/key · 128 B · 16 connections: [recorded failure](raw/lavik-maina565d603-ordered-list-104857600-k8-f128-20261004/list-104857600-128-lrange-c16.error.json).

[100 MiB LRANGE 内存准入分析](diagnostics/main-refresh-20261004/list-lrange-admission.md)

## List

### LINDEX

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![List LINDEX 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f128-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![List LINDEX 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f1024-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![List LINDEX 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![List LINDEX 1 MiB/key, 1024 B, 64 keys](charts/list-1048576-1024-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![List LINDEX 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lindex-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f128-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![List LINDEX 100 MiB/key, 1024 B, 8 keys](charts/list-104857600-1024-k8-lindex-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f1024-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f1024-20261004/)

### LSET

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![List LSET 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f128-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![List LSET 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f1024-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![List LSET 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f128-20261004/)

1024 B/entry · 50,000 keys · 本轮 main 基线 `a565d603`

![List LSET 1 MiB/key, 1024 B, 50000 keys](charts/list-1048576-1024-k50000-lset-current.png)

[Redis](raw/redis-lset-matched-1048576-k50000-f1024-20261001/) · [Valkey](raw/valkey-lset-matched-1048576-k50000-f1024-20261001/) · [Kvrocks (80 GiB cache)](raw/kvrocks-lset-matched-1048576-k50000-f1024-20261001/) · [Lavik main a565d603](raw/lavik-maina565d603-lset-list-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![List LSET 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lset-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f128-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f128-20261004/)

1024 B/entry · 500 keys · 本轮 main 基线 `a565d603`

![List LSET 100 MiB/key, 1024 B, 500 keys](charts/list-104857600-1024-k500-lset-current.png)

[Redis](raw/redis-lset-matched-104857600-k500-f1024-20261001/) · [Valkey](raw/valkey-lset-matched-104857600-k500-f1024-20261001/) · [Kvrocks (80 GiB cache)](raw/kvrocks-lset-matched-104857600-k500-f1024-20261001/) · [Lavik main a565d603](raw/lavik-maina565d603-lset-list-104857600-k500-f1024-20261004/)

### LRANGE 0 -1

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![List LRANGE 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f128-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![List LRANGE 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f1024-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![List LRANGE 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![List LRANGE 1 MiB/key, 1024 B, 64 keys](charts/list-1048576-1024-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![List LRANGE 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f128-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![List LRANGE 100 MiB/key, 1024 B, 8 keys](charts/list-104857600-1024-k8-lrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f1024-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f1024-20261004/)

### RPUSH 批量预置

与 LSET 使用同一组独立预置计时：32 客户端、pipeline=4、每命令 128 个 1 KiB 元素，四库使用相同的客户端编码。

#### 1 MiB/key

![List RPUSH fill, 50000 keys](charts/list-1048576-1024-k50000-rpush-fill-current.png)

#### 100 MiB/key

![List RPUSH fill, 500 keys](charts/list-104857600-1024-k500-rpush-fill-current.png)

## Hash

### HGET

#### 1 MiB/key

128 B/entry · 50,000 keys · 本轮 main 基线 `a565d603`

![Hash HGET 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hget-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · 本轮 main 基线 `a565d603`

![Hash HGET 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hget-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · 本轮 main 基线 `a565d603`

![Hash HGET 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hget-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · 本轮 main 基线 `a565d603`

![Hash HGET 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hget-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f1024-20261004/)

### HSET

#### 1 MiB/key

128 B/entry · 50,000 keys · 本轮 main 基线 `a565d603`

![Hash HSET 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hset-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · 本轮 main 基线 `a565d603`

![Hash HSET 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hset-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · 本轮 main 基线 `a565d603`

![Hash HSET 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hset-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · 本轮 main 基线 `a565d603`

![Hash HSET 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hset-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f1024-20261004/)

### HGETALL

#### 1 MiB/key

128 B/entry · 50,000 keys · 本轮 main 基线 `a565d603`

![Hash HGETALL 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hgetall-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · 本轮 main 基线 `a565d603`

![Hash HGETALL 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hgetall-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · 本轮 main 基线 `a565d603`

![Hash HGETALL 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hgetall-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · 本轮 main 基线 `a565d603`

![Hash HGETALL 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hgetall-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f1024-20261004/)

### HSET 批量导入

#### 1 MiB/key

50,000 keys；8 个客户端、pipeline=64、每命令约 16 KiB 元素。使用与历史三库相同的逐命令 RESP 编码方式，耗时包含 Python 客户端编码；不是 RESTORE，也不代表数据库单独的吞吐上限。

1024 B/entry · 本轮 main 基线 `a565d603`

![HSET batched import, 1024 B](charts/hash-1048576-1024-k50000-fill.png)

[Lavik raw](raw/lavik-maina565d603-import-hash-1048576-k50000-f1024-20261004/)

128 B/entry · 本轮 main 基线 `a565d603`

![HSET batched import, 128 B](charts/hash-1048576-128-k50000-fill.png)

[Lavik raw](raw/lavik-maina565d603-import-hash-1048576-k50000-f128-20261004/)

## Set

SADD + SREM 为两个命令等比例混合，QPS 计算完成的命令数，不是命令对数。随机命中相同 key 时可能产生空操作，因此不代表实际持久化修改次数。

### SISMEMBER

#### 1 MiB/key

128 B/entry · 50,000 keys · 本轮 main 基线 `a565d603`

![Set SISMEMBER 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-sismember-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · 本轮 main 基线 `a565d603`

![Set SISMEMBER 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-sismember-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · 本轮 main 基线 `a565d603`

![Set SISMEMBER 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-sismember-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · 本轮 main 基线 `a565d603`

![Set SISMEMBER 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-sismember-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-104857600-k500-f1024-20261004/)

### SADD + SREM

#### 1 MiB/key

128 B/entry · 50,000 keys · 本轮 main 基线 `a565d603`

![Set SADD_SREM 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-sadd_srem-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · 本轮 main 基线 `a565d603`

![Set SADD_SREM 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-sadd_srem-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · 本轮 main 基线 `a565d603`

![Set SADD_SREM 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-sadd_srem-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · 本轮 main 基线 `a565d603`

![Set SADD_SREM 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-sadd_srem-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-104857600-k500-f1024-20261004/)

### SMEMBERS

#### 1 MiB/key

128 B/entry · 50,000 keys · 本轮 main 基线 `a565d603`

![Set SMEMBERS 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-smembers-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · 本轮 main 基线 `a565d603`

![Set SMEMBERS 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-smembers-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · 本轮 main 基线 `a565d603`

![Set SMEMBERS 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-smembers-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · 本轮 main 基线 `a565d603`

![Set SMEMBERS 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-smembers-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-104857600-k500-f1024-20261004/)

### SADD 批量导入

#### 1 MiB/key

50,000 keys；8 个客户端、pipeline=64、每命令约 16 KiB 元素。使用与历史三库相同的逐命令 RESP 编码方式，耗时包含 Python 客户端编码；不是 RESTORE，也不代表数据库单独的吞吐上限。

1024 B/entry · 本轮 main 基线 `a565d603`

![SADD batched import, 1024 B](charts/set-1048576-1024-k50000-fill.png)

[Lavik raw](raw/lavik-maina565d603-import-set-1048576-k50000-f1024-20261004/)

128 B/entry · 本轮 main 基线 `a565d603`

![SADD batched import, 128 B](charts/set-1048576-128-k50000-fill.png)

[Lavik raw](raw/lavik-maina565d603-import-set-1048576-k50000-f128-20261004/)

## Sorted Set

### ZSCORE

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZSCORE 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f128-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZSCORE 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZSCORE 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZSCORE 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZSCORE 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zscore-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZSCORE 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zscore-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f1024-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-104857600-k8-f1024-20261004/)

### ZINCRBY

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZINCRBY 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f128-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZINCRBY 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZINCRBY 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZINCRBY 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZINCRBY 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zincrby-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZINCRBY 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zincrby-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f1024-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-104857600-k8-f1024-20261004/)

### ZRANGE 0 -1 WITHSCORES

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZRANGE 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f128-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZRANGE 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZRANGE 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZRANGE 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZRANGE 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![Sorted Set ZRANGE 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f1024-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-104857600-k8-f1024-20261004/)

## Stream

### XRANGE (one ID)

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Stream XRANGE 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f128-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Stream XRANGE 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f1024-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Stream XRANGE 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Stream XRANGE 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![Stream XRANGE 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f128-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![Stream XRANGE 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-104857600-k8-f1024-20261004/)

### XADD MAXLEN ~

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Stream XADD_MAXLEN 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f128-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Stream XADD_MAXLEN 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f1024-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Stream XADD_MAXLEN 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Stream XADD_MAXLEN 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![Stream XADD_MAXLEN 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xadd_maxlen-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f128-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![Stream XADD_MAXLEN 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xadd_maxlen-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-104857600-k8-f1024-20261004/)

### XRANGE - +

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Stream XRANGE_FULL 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f128-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Stream XRANGE_FULL 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f1024-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Stream XRANGE_FULL 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · 本轮 main 基线 `a565d603`

![Stream XRANGE_FULL 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![Stream XRANGE_FULL 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xrange_full-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f128-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · 本轮 main 基线 `a565d603`

![Stream XRANGE_FULL 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xrange_full-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-104857600-k8-f1024-20261004/)

## 测量与复现

memtier 在独立客户端主机 172.16.0.5 上运行，绑定 CPU 0–15；key 均匀随机。HGET/HSET、SISMEMBER、LINDEX/LSET、ZSCORE/ZINCRBY 和指定 ID 的 XRANGE 在每 key 的八个等距位置间轮换，并非对所有字段均匀采样。SADD/SREM 使用固定测试 member；XADD MAXLEN 追加新 ID。每组按连接数顺序测试，后续写入点继承前面测点改变的值和布局。

Hash/Set：1 MiB/key 使用 50,000 keys，100 MiB/key 使用 500 keys。LSET 的大 key 数负载同样使用 50,000/500 keys。其他有序结构保留既有四库一致的 64/8-key 负载，标题明确区分；不同 key 数的曲线不能直接比较。

Hash/Set 以 RESTORE 独立预置后清理、重启恢复再测；LSET 大 key 数预置使用 32 个连接、128 KiB RPUSH 批次、pipeline=4。预置耗时保存在每组 raw 目录中，不将 RESTORE 与其他系统的 HSET/SADD 导入耗时混比。

读取整个 100 MiB key 的低吞吐测点可能只有少量完成回复，小差异不作性能结论。八秒成功不代表长时间高并发下内存稳定；历史 SMEMBERS 持续负载曾触发内存准入拒绝。失败测点保留断线与说明，不填零、不插值。

历史优化数据保存在 `raw/` 和 `diagnostics/`，不再显示为已合并 PR 的独立曲线。
