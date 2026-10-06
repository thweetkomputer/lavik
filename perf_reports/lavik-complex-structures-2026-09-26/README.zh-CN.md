# 复杂数据结构性能：Redis、Valkey、Kvrocks 与 Lavik

[English](README.md)

**2026-10-06：main `5a3903d9` 已完成 28/28 组复测，包含已合并的 #244, #246, #247, #249, #258, #259, #260, #262, #265, #266, #267, #268, #270, #280。**

批量 HSET/SADD 导入另计：4/4 组已更新。

[#283 对 rebase 后 main 的三轮配对](diagnostics/pr283-main-20261006/README.md)已完成：小对象 ZINCRBY c320/c5120 分别 +1.80% / +1.57%，但整体写入收益不稳定；小对象 ZSCORE c320 出现未解释下降（配对中位 −36.12%，p99 +315.15%）。目前保持 draft，详细结果包含不利观测和独立 perf。

[Hash/Set 大目录元数据覆盖优化](diagnostics/hashset-routing-overlay-20261006/README.md)：固定 seed 的 108 点对照，大对象标准 HSET / SADD-SREM 中位 +11.25% / +6.19%；小对象基本持平，分散 Hash 写入无稳定收益，写后 HGET 有回退。完整结果包含四份独立 perf。

吞吐图固定命令、每 key 的 payload 大小、元素大小和 key 数；横轴为连接数，纵轴为 QPS。批量导入图显示完成固定数据量所需的秒数。只保留当前 main 和后续未合并 PR，其他三库保留同负载的历史实测。

Redis/Valkey 关闭持久化；Kvrocks 使用无压缩 RAID0、关闭 WAL、80 GiB block/blob cache；Lavik 使用六块 NVMe SPDK 持久化，不缓存字段或页内容。配置不同，写入 QPS 不代表同等持久性下的排名。

本轮不重跑其他三库。Lavik 使用 AMD EPYC 9V74、16 vCPU、12 个服务 worker。每点 8 秒，较多 key 的 LSET 为 10 秒；pipeline=1。每组独立预置并逐 key 校验，perf 另行采集，不混入 QPS 图。单次扫描没有统计置信区间。

本轮固定使用上述 main 提交，已合并优化不再作为独立 PR 曲线显示。历史观察仍保留原始提交号；每完成一组独立复测才替换对应图。

[绘图数据清单](current-main.json) · [复现脚本](run.py) · [上一轮构建与硬件证明](diagnostics/main-refresh-20261004/host-and-build.json)

[完整 main 基线：逐命令差距](diagnostics/main-5a3903d9-20261006/main-gap-summary.md)

[本轮构建与硬件证明](diagnostics/main-5a3903d9-20261006/host-and-build.json)

[本轮测量与验证](diagnostics/main-5a3903d9-20261006/README.md)

[本轮绘图数据核验](diagnostics/main-5a3903d9-20261006/report-audit.json)

[上一轮绘图数据核验](diagnostics/main-refresh-20261004/report-audit.json) · [上一轮核验脚本](diagnostics/main-refresh-20261004/audit-report.py)

[Hash/Set 写入 perf 分析](diagnostics/hashset-write-20261004/README.md) · [有序目录优化与测试](diagnostics/ordered-metadata-20261004/README.md)

[rebase 后 #283 与 main：配对结果、perf 及验证](diagnostics/pr283-main-20261006/README.md)

[PR 去留与原始失败记录](diagnostics/grouped-expiry-recovery-20261004/pr-cleanup-current.md)

[历史固定组合：完整结果与取舍](diagnostics/combined-20261005/README.md)

[历史 #280 测量与 perf](diagnostics/zset-score-views-20261005/README.md)

[Stream 回复与读取窗口证据](diagnostics/stream-reply-20261004/README.md)

[List 回复与 grouped 根记录读取证据](diagnostics/list-reply-reserve-20261004/README.md)

[历史 100 MiB LRANGE 内存准入分析](diagnostics/main-refresh-20261004/list-lrange-admission.md)

## List

### LINDEX

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![List LINDEX 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![List LINDEX 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![List LINDEX 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![List LINDEX 1 MiB/key, 1024 B, 64 keys](charts/list-1048576-1024-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![List LINDEX 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lindex-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![List LINDEX 100 MiB/key, 1024 B, 8 keys](charts/list-104857600-1024-k8-lindex-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-104857600-k8-f1024-20261006/)

### LSET

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![List LSET 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![List LSET 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![List LSET 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-1048576-k64-f128-20261006/)

1024 B/entry · 50,000 keys · 本轮 main 基线 `5a3903d9`

![List LSET 1 MiB/key, 1024 B, 50000 keys](charts/list-1048576-1024-k50000-lset-current.png)

[Redis](raw/redis-lset-matched-1048576-k50000-f1024-20261001/) · [Valkey](raw/valkey-lset-matched-1048576-k50000-f1024-20261001/) · [Kvrocks (80 GiB cache)](raw/kvrocks-lset-matched-1048576-k50000-f1024-20261001/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-lset-list-1048576-k50000-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![List LSET 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lset-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-104857600-k8-f128-20261006/)

1024 B/entry · 500 keys · 本轮 main 基线 `5a3903d9`

![List LSET 100 MiB/key, 1024 B, 500 keys](charts/list-104857600-1024-k500-lset-current.png)

[Redis](raw/redis-lset-matched-104857600-k500-f1024-20261001/) · [Valkey](raw/valkey-lset-matched-104857600-k500-f1024-20261001/) · [Kvrocks (80 GiB cache)](raw/kvrocks-lset-matched-104857600-k500-f1024-20261001/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-lset-list-104857600-k500-f1024-20261006/)

### LRANGE 0 -1

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![List LRANGE 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![List LRANGE 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![List LRANGE 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![List LRANGE 1 MiB/key, 1024 B, 64 keys](charts/list-1048576-1024-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![List LRANGE 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![List LRANGE 100 MiB/key, 1024 B, 8 keys](charts/list-104857600-1024-k8-lrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-104857600-k8-f1024-20261006/)

### RPUSH 批量预置

与 LSET 使用同一组独立预置计时：32 客户端、pipeline=4、每命令 128 个 1 KiB 元素，四库使用相同的客户端编码。

#### 1 MiB/key

![List RPUSH fill, 50000 keys](charts/list-1048576-1024-k50000-rpush-fill-current.png)

#### 100 MiB/key

![List RPUSH fill, 500 keys](charts/list-104857600-1024-k500-rpush-fill-current.png)

## Hash

### HGET

#### 1 MiB/key

128 B/entry · 50,000 keys · 本轮 main 基线 `5a3903d9`

![Hash HGET 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hget-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-1048576-k50000-f128-20261006/)

1024 B/entry · 50,000 keys · 本轮 main 基线 `5a3903d9`

![Hash HGET 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hget-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-1048576-k50000-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 500 keys · 本轮 main 基线 `5a3903d9`

![Hash HGET 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hget-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-104857600-k500-f128-20261006/)

1024 B/entry · 500 keys · 本轮 main 基线 `5a3903d9`

![Hash HGET 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hget-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-104857600-k500-f1024-20261006/)

### HSET

#### 1 MiB/key

128 B/entry · 50,000 keys · 本轮 main 基线 `5a3903d9`

![Hash HSET 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hset-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-1048576-k50000-f128-20261006/)

1024 B/entry · 50,000 keys · 本轮 main 基线 `5a3903d9`

![Hash HSET 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hset-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-1048576-k50000-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 500 keys · 本轮 main 基线 `5a3903d9`

![Hash HSET 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hset-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-104857600-k500-f128-20261006/)

1024 B/entry · 500 keys · 本轮 main 基线 `5a3903d9`

![Hash HSET 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hset-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-104857600-k500-f1024-20261006/)

### HGETALL

#### 1 MiB/key

128 B/entry · 50,000 keys · 本轮 main 基线 `5a3903d9`

![Hash HGETALL 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hgetall-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-1048576-k50000-f128-20261006/)

1024 B/entry · 50,000 keys · 本轮 main 基线 `5a3903d9`

![Hash HGETALL 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hgetall-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-1048576-k50000-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 500 keys · 本轮 main 基线 `5a3903d9`

![Hash HGETALL 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hgetall-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-104857600-k500-f128-20261006/)

1024 B/entry · 500 keys · 本轮 main 基线 `5a3903d9`

![Hash HGETALL 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hgetall-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-104857600-k500-f1024-20261006/)

### HSET 批量导入

#### 1 MiB/key

50,000 keys；8 个客户端、pipeline=64、每命令约 16 KiB 元素。使用与历史三库相同的逐命令 RESP 编码方式，耗时包含 Python 客户端编码；不是 RESTORE，也不代表数据库单独的吞吐上限。

1024 B/entry · 本轮 main 基线 `5a3903d9`

![HSET batched import, 1024 B](charts/hash-1048576-1024-k50000-fill.png)

[Lavik raw](raw/lavik-main5a3903d9-import-hash-1048576-k50000-f1024-20261006/)

128 B/entry · 本轮 main 基线 `5a3903d9`

![HSET batched import, 128 B](charts/hash-1048576-128-k50000-fill.png)

[Lavik raw](raw/lavik-main5a3903d9-import-hash-1048576-k50000-f128-20261006/)

## Set

SADD + SREM 为两个命令等比例混合，QPS 计算完成的命令数，不是命令对数。随机命中相同 key 时可能产生空操作，因此不代表实际持久化修改次数。

### SISMEMBER

#### 1 MiB/key

128 B/entry · 50,000 keys · 本轮 main 基线 `5a3903d9`

![Set SISMEMBER 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-sismember-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-1048576-k50000-f128-20261006/)

1024 B/entry · 50,000 keys · 本轮 main 基线 `5a3903d9`

![Set SISMEMBER 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-sismember-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-1048576-k50000-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 500 keys · 本轮 main 基线 `5a3903d9`

![Set SISMEMBER 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-sismember-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-104857600-k500-f128-20261006/)

1024 B/entry · 500 keys · 本轮 main 基线 `5a3903d9`

![Set SISMEMBER 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-sismember-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-104857600-k500-f1024-20261006/)

### SADD + SREM

#### 1 MiB/key

128 B/entry · 50,000 keys · 本轮 main 基线 `5a3903d9`

![Set SADD_SREM 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-sadd_srem-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-1048576-k50000-f128-20261006/)

1024 B/entry · 50,000 keys · 本轮 main 基线 `5a3903d9`

![Set SADD_SREM 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-sadd_srem-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-1048576-k50000-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 500 keys · 本轮 main 基线 `5a3903d9`

![Set SADD_SREM 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-sadd_srem-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-104857600-k500-f128-20261006/)

1024 B/entry · 500 keys · 本轮 main 基线 `5a3903d9`

![Set SADD_SREM 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-sadd_srem-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-104857600-k500-f1024-20261006/)

### SMEMBERS

#### 1 MiB/key

128 B/entry · 50,000 keys · 本轮 main 基线 `5a3903d9`

![Set SMEMBERS 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-smembers-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-1048576-k50000-f128-20261006/)

1024 B/entry · 50,000 keys · 本轮 main 基线 `5a3903d9`

![Set SMEMBERS 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-smembers-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-1048576-k50000-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 500 keys · 本轮 main 基线 `5a3903d9`

![Set SMEMBERS 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-smembers-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-104857600-k500-f128-20261006/)

1024 B/entry · 500 keys · 本轮 main 基线 `5a3903d9`

![Set SMEMBERS 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-smembers-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-104857600-k500-f1024-20261006/)

### SADD 批量导入

#### 1 MiB/key

50,000 keys；8 个客户端、pipeline=64、每命令约 16 KiB 元素。使用与历史三库相同的逐命令 RESP 编码方式，耗时包含 Python 客户端编码；不是 RESTORE，也不代表数据库单独的吞吐上限。

1024 B/entry · 本轮 main 基线 `5a3903d9`

![SADD batched import, 1024 B](charts/set-1048576-1024-k50000-fill.png)

[Lavik raw](raw/lavik-main5a3903d9-import-set-1048576-k50000-f1024-20261006/)

128 B/entry · 本轮 main 基线 `5a3903d9`

![SADD batched import, 128 B](charts/set-1048576-128-k50000-fill.png)

[Lavik raw](raw/lavik-main5a3903d9-import-set-1048576-k50000-f128-20261006/)

## Sorted Set

### ZSCORE

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZSCORE 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZSCORE 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZSCORE 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZSCORE 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZSCORE 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zscore-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZSCORE 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zscore-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-104857600-k8-f1024-20261006/)

### ZINCRBY

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZINCRBY 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZINCRBY 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZINCRBY 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZINCRBY 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZINCRBY 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zincrby-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZINCRBY 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zincrby-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-104857600-k8-f1024-20261006/)

### ZRANGE 0 -1 WITHSCORES

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZRANGE 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZRANGE 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZRANGE 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZRANGE 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZRANGE 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![Sorted Set ZRANGE 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-104857600-k8-f1024-20261006/)

## Stream

### XRANGE (one ID)

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Stream XRANGE 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Stream XRANGE 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Stream XRANGE 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Stream XRANGE 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![Stream XRANGE 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![Stream XRANGE 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-104857600-k8-f1024-20261006/)

### XADD MAXLEN ~

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Stream XADD_MAXLEN 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Stream XADD_MAXLEN 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Stream XADD_MAXLEN 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Stream XADD_MAXLEN 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![Stream XADD_MAXLEN 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xadd_maxlen-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![Stream XADD_MAXLEN 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xadd_maxlen-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-104857600-k8-f1024-20261006/)

### XRANGE - +

#### 64 KiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Stream XRANGE_FULL 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Stream XRANGE_FULL 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Stream XRANGE_FULL 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · 本轮 main 基线 `5a3903d9`

![Stream XRANGE_FULL 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![Stream XRANGE_FULL 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xrange_full-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · 本轮 main 基线 `5a3903d9`

![Stream XRANGE_FULL 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xrange_full-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-104857600-k8-f1024-20261006/)

## 测量与复现

memtier 在独立客户端主机 172.16.0.5 上运行，绑定 CPU 0–15；key 均匀随机。HGET/HSET、SISMEMBER、LINDEX/LSET、ZSCORE/ZINCRBY 和指定 ID 的 XRANGE 在每 key 的八个等距位置间轮换，并非对所有字段均匀采样。SADD/SREM 使用固定测试 member；XADD MAXLEN 追加新 ID。每组按连接数顺序测试，后续写入点继承前面测点改变的值和布局。

Hash/Set：1 MiB/key 使用 50,000 keys，100 MiB/key 使用 500 keys。LSET 的大 key 数负载同样使用 50,000/500 keys。其他有序结构保留既有四库一致的 64/8-key 负载，标题明确区分；不同 key 数的曲线不能直接比较。

Hash/Set 以 RESTORE 独立预置后清理、重启恢复再测；LSET 大 key 数预置使用 32 个连接、128 KiB RPUSH 批次、pipeline=4。预置耗时保存在每组 raw 目录中，不将 RESTORE 与其他系统的 HSET/SADD 导入耗时混比。

读取整个 100 MiB key 的低吞吐测点可能只有少量完成回复，小差异不作性能结论。八秒成功不代表长时间高并发下内存稳定；历史 SMEMBERS 持续负载曾触发内存准入拒绝。失败测点保留断线与说明，不填零、不插值。

历史优化数据保存在 `raw/` 和 `diagnostics/`，不再显示为已合并 PR 的独立曲线。
