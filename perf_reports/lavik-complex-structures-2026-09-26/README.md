# Complex structures: Redis, Valkey, Kvrocks and Lavik

[简体中文](README.zh-CN.md)


[PR #275: 60 observations after rebasing onto main](diagnostics/pr275-main-20261006/README.md): large full XRANGE gains +325.49% / +238.95% / +130.87% at c1/c4/c16. Small full-read QPS is flat, but p99 regresses in all three pairs (median +39.07%). The PR remains draft; merging is not recommended yet.

[Hash/Set routing metadata overlay](diagnostics/hashset-routing-overlay-20261006/README.md): 108 matched-seed observations; large standard HSET / SADD-SREM median +11.25% / +6.19%. Small controls are near flat; dispersed Hash writes show no reliable gain and post-write HGET regresses. All controls and four independent perf profiles are retained.

**2026-10-06: main `5a3903d9`, including merged #244, #246, #247, #249, #258, #259, #260, #262, #265, #266, #267, #268, #270, #280; 28/28 conditions refreshed.**

Batched HSET/SADD import is tracked separately: 4/4 conditions refreshed.

[Three paired rounds of #283 versus its rebased main](diagnostics/pr283-main-20261006/README.md) are complete: small ZINCRBY c320/c5120 gain +1.80% / +1.57%, but overall write gains are inconsistent. Small ZSCORE c320 has an unresolved slowdown (paired median −36.12%, p99 +315.15%). The PR remains draft; full results retain unfavorable observations and separate perf evidence.

Throughput figures fix the command, payload bytes per key, entry size and key count; axes show connections and QPS. Batched-import figures show seconds to fill a fixed dataset. Keep the current main and subsequent unmerged PRs; peers retain historical measurements of the same workload.

Redis/Valkey disable persistence. Kvrocks uses uncompressed RAID0, disabled WAL and 80 GiB block/blob cache. Lavik persists through six SPDK NVMe devices without caching field/page payloads. Write QPS compares these configurations, not equivalent durability.

Peers are not rerun this round. Lavik uses AMD EPYC 9V74, 16 vCPUs and 12 serving workers. Points last 8 s (10 s for high-key-count LSET), pipeline=1. Each condition is independently seeded and checked key by key. CPU profiles run separately from the plotted throughput measurements. Single sweeps have no statistical confidence intervals.

This round pins the main revision above. Merged optimizations are no longer separate PR curves. Historical observations retain their measured commits; each chart is replaced only after its independent rerun completes.

[Plot sources](current-main.json) · [Runner](run.py) · [Previous-round build and hardware](diagnostics/main-refresh-20261004/host-and-build.json)

[Complete main baseline: per-command gaps](diagnostics/main-5a3903d9-20261006/main-gap-summary.md)

[Current build and hardware](diagnostics/main-5a3903d9-20261006/host-and-build.json)

[Current measurements and validation](diagnostics/main-5a3903d9-20261006/README.md)

[Current plot-data audit](diagnostics/main-5a3903d9-20261006/report-audit.json)

[Previous-round plot-data audit](diagnostics/main-refresh-20261004/report-audit.json) · [Previous-round audit script](diagnostics/main-refresh-20261004/audit-report.py)

[Hash/Set write profiles](diagnostics/hashset-write-20261004/README.md) · [Ordered metadata optimization and tests](diagnostics/ordered-metadata-20261004/README.md)

[Rebased PR #283 versus main: paired results, perf and validation](diagnostics/pr283-main-20261006/README.md)

[PR disposition and retained failure records](diagnostics/grouped-expiry-recovery-20261004/pr-cleanup-current.md)

[Historical fixed combination: full results and tradeoffs](diagnostics/combined-20261005/README.md)

[Historical #280 measurements and perf](diagnostics/zset-score-views-20261005/README.md)

[Stream reply and read-window evidence](diagnostics/stream-reply-20261004/README.md)

[List replies and grouped root-read evidence](diagnostics/list-reply-reserve-20261004/README.md)

[Historical 100 MiB LRANGE admission analysis](diagnostics/main-refresh-20261004/list-lrange-admission.md)

## List

### LINDEX

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![List LINDEX 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![List LINDEX 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![List LINDEX 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![List LINDEX 1 MiB/key, 1024 B, 64 keys](charts/list-1048576-1024-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `5a3903d9`

![List LINDEX 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lindex-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · Measured main baseline `5a3903d9`

![List LINDEX 100 MiB/key, 1024 B, 8 keys](charts/list-104857600-1024-k8-lindex-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-104857600-k8-f1024-20261006/)

### LSET

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![List LSET 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![List LSET 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![List LSET 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-1048576-k64-f128-20261006/)

1024 B/entry · 50,000 keys · Measured main baseline `5a3903d9`

![List LSET 1 MiB/key, 1024 B, 50000 keys](charts/list-1048576-1024-k50000-lset-current.png)

[Redis](raw/redis-lset-matched-1048576-k50000-f1024-20261001/) · [Valkey](raw/valkey-lset-matched-1048576-k50000-f1024-20261001/) · [Kvrocks (80 GiB cache)](raw/kvrocks-lset-matched-1048576-k50000-f1024-20261001/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-lset-list-1048576-k50000-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `5a3903d9`

![List LSET 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lset-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-104857600-k8-f128-20261006/)

1024 B/entry · 500 keys · Measured main baseline `5a3903d9`

![List LSET 100 MiB/key, 1024 B, 500 keys](charts/list-104857600-1024-k500-lset-current.png)

[Redis](raw/redis-lset-matched-104857600-k500-f1024-20261001/) · [Valkey](raw/valkey-lset-matched-104857600-k500-f1024-20261001/) · [Kvrocks (80 GiB cache)](raw/kvrocks-lset-matched-104857600-k500-f1024-20261001/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-lset-list-104857600-k500-f1024-20261006/)

### LRANGE 0 -1

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![List LRANGE 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![List LRANGE 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![List LRANGE 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![List LRANGE 1 MiB/key, 1024 B, 64 keys](charts/list-1048576-1024-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `5a3903d9`

![List LRANGE 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · Measured main baseline `5a3903d9`

![List LRANGE 100 MiB/key, 1024 B, 8 keys](charts/list-104857600-1024-k8-lrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-list-104857600-k8-f1024-20261006/)

### RPUSH batched seeding

Independent LSET seeding timings: 32 clients, pipeline=4, 128 one-KiB entries per command, with the same client encoder across all four databases.

#### 1 MiB/key

![List RPUSH fill, 50000 keys](charts/list-1048576-1024-k50000-rpush-fill-current.png)

#### 100 MiB/key

![List RPUSH fill, 500 keys](charts/list-104857600-1024-k500-rpush-fill-current.png)

## Hash

### HGET

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `5a3903d9`

![Hash HGET 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hget-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-1048576-k50000-f128-20261006/)

1024 B/entry · 50,000 keys · Measured main baseline `5a3903d9`

![Hash HGET 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hget-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-1048576-k50000-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `5a3903d9`

![Hash HGET 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hget-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-104857600-k500-f128-20261006/)

1024 B/entry · 500 keys · Measured main baseline `5a3903d9`

![Hash HGET 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hget-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-104857600-k500-f1024-20261006/)

### HSET

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `5a3903d9`

![Hash HSET 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hset-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-1048576-k50000-f128-20261006/)

1024 B/entry · 50,000 keys · Measured main baseline `5a3903d9`

![Hash HSET 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hset-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-1048576-k50000-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `5a3903d9`

![Hash HSET 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hset-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-104857600-k500-f128-20261006/)

1024 B/entry · 500 keys · Measured main baseline `5a3903d9`

![Hash HSET 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hset-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-104857600-k500-f1024-20261006/)

### HGETALL

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `5a3903d9`

![Hash HGETALL 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hgetall-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-1048576-k50000-f128-20261006/)

1024 B/entry · 50,000 keys · Measured main baseline `5a3903d9`

![Hash HGETALL 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hgetall-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-1048576-k50000-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `5a3903d9`

![Hash HGETALL 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hgetall-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-104857600-k500-f128-20261006/)

1024 B/entry · 500 keys · Measured main baseline `5a3903d9`

![Hash HGETALL 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hgetall-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-hash-104857600-k500-f1024-20261006/)

### HSET batched import

#### 1 MiB/key

50,000 keys; 8 clients, pipeline=64, about 16 KiB entries/command. Per-command RESP encoding matches the historical peer workload; elapsed time includes Python client encoding. This is not RESTORE or a server-only throughput ceiling.

1024 B/entry · Measured main baseline `5a3903d9`

![HSET batched import, 1024 B](charts/hash-1048576-1024-k50000-fill.png)

[Lavik raw](raw/lavik-main5a3903d9-import-hash-1048576-k50000-f1024-20261006/)

128 B/entry · Measured main baseline `5a3903d9`

![HSET batched import, 128 B](charts/hash-1048576-128-k50000-fill.png)

[Lavik raw](raw/lavik-main5a3903d9-import-hash-1048576-k50000-f128-20261006/)

## Set

SADD + SREM mixes the two commands equally; QPS counts commands, not pairs. Random concurrent access can produce no-op additions/removals, so this is not the rate of durable changes.

### SISMEMBER

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `5a3903d9`

![Set SISMEMBER 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-sismember-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-1048576-k50000-f128-20261006/)

1024 B/entry · 50,000 keys · Measured main baseline `5a3903d9`

![Set SISMEMBER 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-sismember-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-1048576-k50000-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `5a3903d9`

![Set SISMEMBER 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-sismember-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-104857600-k500-f128-20261006/)

1024 B/entry · 500 keys · Measured main baseline `5a3903d9`

![Set SISMEMBER 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-sismember-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-104857600-k500-f1024-20261006/)

### SADD + SREM

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `5a3903d9`

![Set SADD_SREM 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-sadd_srem-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-1048576-k50000-f128-20261006/)

1024 B/entry · 50,000 keys · Measured main baseline `5a3903d9`

![Set SADD_SREM 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-sadd_srem-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-1048576-k50000-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `5a3903d9`

![Set SADD_SREM 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-sadd_srem-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-104857600-k500-f128-20261006/)

1024 B/entry · 500 keys · Measured main baseline `5a3903d9`

![Set SADD_SREM 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-sadd_srem-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-104857600-k500-f1024-20261006/)

### SMEMBERS

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `5a3903d9`

![Set SMEMBERS 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-smembers-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-1048576-k50000-f128-20261006/)

1024 B/entry · 50,000 keys · Measured main baseline `5a3903d9`

![Set SMEMBERS 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-smembers-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-1048576-k50000-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `5a3903d9`

![Set SMEMBERS 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-smembers-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-104857600-k500-f128-20261006/)

1024 B/entry · 500 keys · Measured main baseline `5a3903d9`

![Set SMEMBERS 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-smembers-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-hashset-set-104857600-k500-f1024-20261006/)

### SADD batched import

#### 1 MiB/key

50,000 keys; 8 clients, pipeline=64, about 16 KiB entries/command. Per-command RESP encoding matches the historical peer workload; elapsed time includes Python client encoding. This is not RESTORE or a server-only throughput ceiling.

1024 B/entry · Measured main baseline `5a3903d9`

![SADD batched import, 1024 B](charts/set-1048576-1024-k50000-fill.png)

[Lavik raw](raw/lavik-main5a3903d9-import-set-1048576-k50000-f1024-20261006/)

128 B/entry · Measured main baseline `5a3903d9`

![SADD batched import, 128 B](charts/set-1048576-128-k50000-fill.png)

[Lavik raw](raw/lavik-main5a3903d9-import-set-1048576-k50000-f128-20261006/)

## Sorted Set

### ZSCORE

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Sorted Set ZSCORE 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Sorted Set ZSCORE 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Sorted Set ZSCORE 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Sorted Set ZSCORE 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `5a3903d9`

![Sorted Set ZSCORE 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zscore-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · Measured main baseline `5a3903d9`

![Sorted Set ZSCORE 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zscore-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-104857600-k8-f1024-20261006/)

### ZINCRBY

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Sorted Set ZINCRBY 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Sorted Set ZINCRBY 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Sorted Set ZINCRBY 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Sorted Set ZINCRBY 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `5a3903d9`

![Sorted Set ZINCRBY 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zincrby-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · Measured main baseline `5a3903d9`

![Sorted Set ZINCRBY 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zincrby-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-104857600-k8-f1024-20261006/)

### ZRANGE 0 -1 WITHSCORES

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Sorted Set ZRANGE 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Sorted Set ZRANGE 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Sorted Set ZRANGE 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Sorted Set ZRANGE 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `5a3903d9`

![Sorted Set ZRANGE 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · Measured main baseline `5a3903d9`

![Sorted Set ZRANGE 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-zset-104857600-k8-f1024-20261006/)

## Stream

### XRANGE (one ID)

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Stream XRANGE 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Stream XRANGE 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Stream XRANGE 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Stream XRANGE 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `5a3903d9`

![Stream XRANGE 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · Measured main baseline `5a3903d9`

![Stream XRANGE 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-104857600-k8-f1024-20261006/)

### XADD MAXLEN ~

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Stream XADD_MAXLEN 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Stream XADD_MAXLEN 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Stream XADD_MAXLEN 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Stream XADD_MAXLEN 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `5a3903d9`

![Stream XADD_MAXLEN 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xadd_maxlen-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · Measured main baseline `5a3903d9`

![Stream XADD_MAXLEN 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xadd_maxlen-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-104857600-k8-f1024-20261006/)

### XRANGE - +

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Stream XRANGE_FULL 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-65536-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Stream XRANGE_FULL 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-65536-k64-f1024-20261006/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Stream XRANGE_FULL 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-1048576-k64-f128-20261006/)

1024 B/entry · 64 keys · Measured main baseline `5a3903d9`

![Stream XRANGE_FULL 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-1048576-k64-f1024-20261006/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `5a3903d9`

![Stream XRANGE_FULL 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xrange_full-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-104857600-k8-f128-20261006/)

1024 B/entry · 8 keys · Measured main baseline `5a3903d9`

![Stream XRANGE_FULL 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xrange_full-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5a3903d9](raw/lavik-main5a3903d9-ordered-stream-104857600-k8-f1024-20261006/)

## Measurement and reproduction

memtier runs on the separate client 172.16.0.5 pinned to CPUs 0–15, with uniformly random keys. HGET/HSET, SISMEMBER, LINDEX/LSET, ZSCORE/ZINCRBY and one-ID XRANGE rotate through eight evenly spaced positions per key, not all fields uniformly. SADD/SREM uses a fixed test member; XADD MAXLEN appends new IDs. Connection points run sequentially within a condition, so later writes inherit values/layout changed by earlier points.

Hash/Set use 50,000 keys at 1 MiB/key and 500 at 100 MiB/key; high-key-count LSET uses the same counts. Other ordered-structure conditions retain the matched 64/8-key peer workloads, explicitly identified in titles. Different key counts are not interchangeable.

Hash/Set use independent RESTORE seeding, transaction cleanup and recovery before measurement. High-key-count LSET seeds with 32 clients, 128 KiB RPUSH batches and pipeline=4. Fill timings remain in raw directories; RESTORE timings are not equated with peer HSET/SADD import timings.

Low-throughput whole-key reads can complete few replies in eight seconds; small differences are not performance conclusions. Eight successful seconds do not establish sustained memory stability: an earlier sustained SMEMBERS run exhausted memory admission. Failed points remain gaps with annotations, never zeroes or interpolated values.

Historical optimization evidence remains in raw/ and diagnostics/; merged PRs are not shown as separate series.
