# Complex structures: Redis, Valkey, Kvrocks and Lavik

[简体中文](README.zh-CN.md)

**2026-10-04: main `5d7d12ec`, including merged #244/#246/#247; 8/28 conditions refreshed.**

Each figure fixes the command, payload bytes per key, entry size and key count. Axes show connections and QPS. Keep the current main and subsequent unmerged PRs; peers retain historical measurements of the same workload.

Pending conditions retain explicitly labeled historical Lavik measurements. Old observations are not relabeled as the new main.

Redis/Valkey disable persistence. Kvrocks uses uncompressed RAID0, disabled WAL and 80 GiB block/blob cache. Lavik persists through six SPDK NVMe devices without caching field/page payloads. Write QPS compares these configurations, not equivalent durability.

Peers are not rerun this round. Lavik uses AMD EPYC 9V74, 16 vCPUs and 12 serving workers. Points last 8 s (10 s for high-key-count LSET), pipeline=1. Each condition is independently seeded and checked key by key. CPU profiles run separately after complete clean grids. Single sweeps have no statistical confidence intervals.

[Plot sources](current-main.json) · [Runner](run.py) · [Build and hardware](diagnostics/main-refresh-20261004/host-and-build.json)

[Hash/Set write profiles](diagnostics/hashset-write-20261004/README.md) · [Ordered metadata optimization and tests](diagnostics/ordered-metadata-20261004/README.md)

Unmerged optimizations: [PR #249](https://github.com/eloqdata/lavik/pull/249)

## List

### LINDEX

#### 64 KiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![List LINDEX 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

1024 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![List LINDEX 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

#### 1 MiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![List LINDEX 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

1024 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![List LINDEX 1 MiB/key, 1024 B, 64 keys](charts/list-1048576-1024-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

#### 100 MiB/key

128 B/entry · 8 keys · Historical measurement; refresh pending `646a7b4e`

![List LINDEX 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lindex-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik (previous measurement) 646a7b4e](raw/lavik-100m/)

1024 B/entry · 8 keys · Historical measurement; refresh pending `44761b91`

![List LINDEX 100 MiB/key, 1024 B, 8 keys](charts/list-104857600-1024-k8-lindex-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik (previous measurement) 44761b91](raw/lavik-main44761-ordered-list-104857600-k8-f1024-20261003/)

### LSET

#### 64 KiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![List LSET 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

1024 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![List LSET 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

#### 1 MiB/key

1024 B/entry · 50,000 keys · Historical measurement; refresh pending `44761b91`

![List LSET 1 MiB/key, 1024 B, 50000 keys](charts/list-1048576-1024-k50000-lset-current.png)

[Redis](raw/redis-lset-matched-1048576-k50000-f1024-20261001/) · [Valkey](raw/valkey-lset-matched-1048576-k50000-f1024-20261001/) · [Kvrocks (80 GiB cache)](raw/kvrocks-lset-matched-1048576-k50000-f1024-20261001/) · [Lavik (previous measurement) 44761b91](raw/lavik-main44761-lset-list-1048576-k50000-f1024-20261003/)

#### 100 MiB/key

1024 B/entry · 500 keys · Historical measurement; refresh pending `44761b91`

![List LSET 100 MiB/key, 1024 B, 500 keys](charts/list-104857600-1024-k500-lset-current.png)

[Redis](raw/redis-lset-matched-104857600-k500-f1024-20261001/) · [Valkey](raw/valkey-lset-matched-104857600-k500-f1024-20261001/) · [Kvrocks (80 GiB cache)](raw/kvrocks-lset-matched-104857600-k500-f1024-20261001/) · [Lavik (previous measurement) 44761b91](raw/lavik-main44761-lset-list-104857600-k500-f1024-20261003/)

### LRANGE 0 -1

#### 64 KiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![List LRANGE 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

1024 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![List LRANGE 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

#### 1 MiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![List LRANGE 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

1024 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![List LRANGE 1 MiB/key, 1024 B, 64 keys](charts/list-1048576-1024-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

#### 100 MiB/key

128 B/entry · 8 keys · Historical measurement; refresh pending `646a7b4e`

![List LRANGE 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik (previous measurement) 646a7b4e](raw/lavik-100m/)

1024 B/entry · 8 keys · Historical measurement; refresh pending `44761b91`

![List LRANGE 100 MiB/key, 1024 B, 8 keys](charts/list-104857600-1024-k8-lrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik (previous measurement) 44761b91](raw/lavik-main44761-ordered-list-104857600-k8-f1024-20261003/)

## Hash

### HGET

#### 1 MiB/key

128 B/entry · 50,000 keys · Current main `5d7d12ec`

![Hash HGET 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hget-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-hash-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Current main `5d7d12ec`

![Hash HGET 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hget-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-hash-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Historical measurement; refresh pending `44761b91`

![Hash HGET 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hget-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik (previous measurement) 44761b91](raw/lavik-main44761-hashset-hash-104857600-k500-f128-20261003/)

1024 B/entry · 500 keys · Current main `5d7d12ec`

![Hash HGET 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hget-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-hash-104857600-k500-f1024-20261004/)

### HSET

#### 1 MiB/key

128 B/entry · 50,000 keys · Current main `5d7d12ec`

![Hash HSET 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hset-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-hash-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Current main `5d7d12ec`

![Hash HSET 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hset-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-hash-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Historical measurement; refresh pending `44761b91`

![Hash HSET 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hset-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik (previous measurement) 44761b91](raw/lavik-main44761-hashset-hash-104857600-k500-f128-20261003/)

1024 B/entry · 500 keys · Current main `5d7d12ec`

![Hash HSET 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hset-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-hash-104857600-k500-f1024-20261004/)

### HGETALL

#### 1 MiB/key

128 B/entry · 50,000 keys · Current main `5d7d12ec`

![Hash HGETALL 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hgetall-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-hash-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Current main `5d7d12ec`

![Hash HGETALL 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hgetall-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-hash-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Historical measurement; refresh pending `44761b91`

![Hash HGETALL 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hgetall-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik (previous measurement) 44761b91](raw/lavik-main44761-hashset-hash-104857600-k500-f128-20261003/)

1024 B/entry · 500 keys · Current main `5d7d12ec`

![Hash HGETALL 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hgetall-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-hash-104857600-k500-f1024-20261004/)

## Set

SADD + SREM mixes the two commands equally; QPS counts commands, not pairs. Random concurrent access can produce no-op additions/removals, so this is not the rate of durable changes.

### SISMEMBER

#### 1 MiB/key

128 B/entry · 50,000 keys · Historical measurement; refresh pending `44761b91`

![Set SISMEMBER 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-sismember-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik (previous measurement) 44761b91](raw/lavik-main44761-hashset-set-1048576-k50000-f128-20261003/)

1024 B/entry · 50,000 keys · Current main `5d7d12ec`

![Set SISMEMBER 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-sismember-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-set-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Historical measurement; refresh pending `44761b91`

![Set SISMEMBER 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-sismember-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik (previous measurement) 44761b91](raw/lavik-main44761-hashset-set-104857600-k500-f128-20261003/)

1024 B/entry · 500 keys · Current main `5d7d12ec`

![Set SISMEMBER 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-sismember-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-set-104857600-k500-f1024-20261004/)

### SADD + SREM

#### 1 MiB/key

128 B/entry · 50,000 keys · Historical measurement; refresh pending `44761b91`

![Set SADD_SREM 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-sadd_srem-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik (previous measurement) 44761b91](raw/lavik-main44761-hashset-set-1048576-k50000-f128-20261003/)

1024 B/entry · 50,000 keys · Current main `5d7d12ec`

![Set SADD_SREM 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-sadd_srem-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-set-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Historical measurement; refresh pending `44761b91`

![Set SADD_SREM 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-sadd_srem-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik (previous measurement) 44761b91](raw/lavik-main44761-hashset-set-104857600-k500-f128-20261003/)

1024 B/entry · 500 keys · Current main `5d7d12ec`

![Set SADD_SREM 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-sadd_srem-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-set-104857600-k500-f1024-20261004/)

### SMEMBERS

#### 1 MiB/key

128 B/entry · 50,000 keys · Historical measurement; refresh pending `44761b91`

![Set SMEMBERS 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-smembers-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik (previous measurement) 44761b91](raw/lavik-main44761-hashset-set-1048576-k50000-f128-20261003/)

1024 B/entry · 50,000 keys · Current main `5d7d12ec`

![Set SMEMBERS 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-smembers-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-set-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Historical measurement; refresh pending `44761b91`

![Set SMEMBERS 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-smembers-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik (previous measurement) 44761b91](raw/lavik-main44761-hashset-set-104857600-k500-f128-20261003/)

1024 B/entry · 500 keys · Current main `5d7d12ec`

![Set SMEMBERS 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-smembers-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-hashset-set-104857600-k500-f1024-20261004/)

## Sorted Set

### ZSCORE

#### 64 KiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![Sorted Set ZSCORE 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

1024 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![Sorted Set ZSCORE 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

#### 1 MiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![Sorted Set ZSCORE 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

1024 B/entry · 64 keys · Historical measurement; refresh pending `6111d0b1`

![Sorted Set ZSCORE 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 6111d0b1](raw/lavik-zset-main6111d0b1-k64-1048576-f1024-20261003/)

#### 100 MiB/key

128 B/entry · 8 keys · Historical measurement; refresh pending `646a7b4e`

![Sorted Set ZSCORE 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zscore-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik (previous measurement) 646a7b4e](raw/lavik-100m/)

1024 B/entry · 8 keys · Current main `5d7d12ec`

![Sorted Set ZSCORE 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zscore-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-ordered-zset-104857600-k8-f1024-20261004/)

### ZINCRBY

#### 64 KiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![Sorted Set ZINCRBY 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

1024 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![Sorted Set ZINCRBY 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

#### 1 MiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![Sorted Set ZINCRBY 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

1024 B/entry · 64 keys · Historical measurement; refresh pending `6111d0b1`

![Sorted Set ZINCRBY 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 6111d0b1](raw/lavik-zset-main6111d0b1-k64-1048576-f1024-20261003/)

#### 100 MiB/key

128 B/entry · 8 keys · Historical measurement; refresh pending `646a7b4e`

![Sorted Set ZINCRBY 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zincrby-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik (previous measurement) 646a7b4e](raw/lavik-100m/)

1024 B/entry · 8 keys · Current main `5d7d12ec`

![Sorted Set ZINCRBY 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zincrby-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-ordered-zset-104857600-k8-f1024-20261004/)

### ZRANGE 0 -1 WITHSCORES

#### 64 KiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![Sorted Set ZRANGE 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

1024 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![Sorted Set ZRANGE 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

#### 1 MiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `646a7b4e`

![Sorted Set ZRANGE 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 646a7b4e](raw/lavik/)

1024 B/entry · 64 keys · Historical measurement; refresh pending `6111d0b1`

![Sorted Set ZRANGE 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 6111d0b1](raw/lavik-zset-main6111d0b1-k64-1048576-f1024-20261003/)

#### 100 MiB/key

128 B/entry · 8 keys · Historical measurement; refresh pending `646a7b4e`

![Sorted Set ZRANGE 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik (previous measurement) 646a7b4e](raw/lavik-100m/)

1024 B/entry · 8 keys · Current main `5d7d12ec`

![Sorted Set ZRANGE 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-ordered-zset-104857600-k8-f1024-20261004/)

## Stream

### XRANGE (one ID)

#### 64 KiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `9acd7b6f`

![Stream XRANGE 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 9acd7b6f](raw/lavik-main9acd-stream-small-20260929/)

1024 B/entry · 64 keys · Historical measurement; refresh pending `9acd7b6f`

![Stream XRANGE 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 9acd7b6f](raw/lavik-main9acd-stream-small-20260929/)

#### 1 MiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `9acd7b6f`

![Stream XRANGE 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 9acd7b6f](raw/lavik-main9acd-stream-small-20260929/)

1024 B/entry · 64 keys · Current main `5d7d12ec`

![Stream XRANGE 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-ordered-stream-1048576-k64-f1024-20261004/) · [Lavik PR #249 97f81cd6](raw/lavik-candidate97f81cd6-ordered-stream-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Historical measurement; refresh pending `646a7b4e`

![Stream XRANGE 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik (previous measurement) 646a7b4e](raw/lavik-100m/)

1024 B/entry · 8 keys · Current main `5d7d12ec`

![Stream XRANGE 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik PR #249 97f81cd6](raw/lavik-candidate97f81cd6-ordered-stream-104857600-k8-f1024-20261004/)

### XADD MAXLEN ~

#### 64 KiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `9acd7b6f`

![Stream XADD_MAXLEN 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 9acd7b6f](raw/lavik-main9acd-stream-small-20260929/)

1024 B/entry · 64 keys · Historical measurement; refresh pending `9acd7b6f`

![Stream XADD_MAXLEN 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 9acd7b6f](raw/lavik-main9acd-stream-small-20260929/)

#### 1 MiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `9acd7b6f`

![Stream XADD_MAXLEN 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 9acd7b6f](raw/lavik-main9acd-stream-small-20260929/)

1024 B/entry · 64 keys · Current main `5d7d12ec`

![Stream XADD_MAXLEN 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-ordered-stream-1048576-k64-f1024-20261004/) · [Lavik PR #249 97f81cd6](raw/lavik-candidate97f81cd6-ordered-stream-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Historical measurement; refresh pending `646a7b4e`

![Stream XADD_MAXLEN 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xadd_maxlen-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik (previous measurement) 646a7b4e](raw/lavik-100m/)

1024 B/entry · 8 keys · Current main `5d7d12ec`

![Stream XADD_MAXLEN 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xadd_maxlen-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik PR #249 97f81cd6](raw/lavik-candidate97f81cd6-ordered-stream-104857600-k8-f1024-20261004/)

### XRANGE - +

#### 64 KiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `9acd7b6f`

![Stream XRANGE_FULL 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 9acd7b6f](raw/lavik-main9acd-stream-small-20260929/)

1024 B/entry · 64 keys · Historical measurement; refresh pending `9acd7b6f`

![Stream XRANGE_FULL 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 9acd7b6f](raw/lavik-main9acd-stream-small-20260929/)

#### 1 MiB/key

128 B/entry · 64 keys · Historical measurement; refresh pending `9acd7b6f`

![Stream XRANGE_FULL 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik (previous measurement) 9acd7b6f](raw/lavik-main9acd-stream-small-20260929/)

1024 B/entry · 64 keys · Current main `5d7d12ec`

![Stream XRANGE_FULL 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-ordered-stream-1048576-k64-f1024-20261004/) · [Lavik PR #249 97f81cd6](raw/lavik-candidate97f81cd6-ordered-stream-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Historical measurement; refresh pending `646a7b4e`

![Stream XRANGE_FULL 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xrange_full-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik (previous measurement) 646a7b4e](raw/lavik-100m/)

1024 B/entry · 8 keys · Current main `5d7d12ec`

![Stream XRANGE_FULL 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xrange_full-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main 5d7d12ec](raw/lavik-main5d7d12ec-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik PR #249 97f81cd6](raw/lavik-candidate97f81cd6-ordered-stream-104857600-k8-f1024-20261004/)

## Measurement and reproduction

Hash/Set use 50,000 keys at 1 MiB/key and 500 at 100 MiB/key; high-key-count LSET uses the same counts. Other ordered-structure conditions retain the matched 64/8-key peer workloads, explicitly identified in titles. Different key counts are not interchangeable.

Hash/Set use independent RESTORE seeding, transaction cleanup and recovery before measurement. High-key-count LSET seeds with 32 clients, 128 KiB RPUSH batches and pipeline=4. Fill timings remain in raw directories; RESTORE timings are not equated with peer HSET/SADD import timings.

Low-throughput whole-key reads can complete few replies in eight seconds; small differences are not performance conclusions. Eight successful seconds do not establish sustained memory stability: an earlier sustained SMEMBERS run exhausted memory admission. Failed points remain gaps with annotations, never zeroes or interpolated values.

Historical optimization evidence remains in raw/ and diagnostics/; merged PRs are not shown as separate series.
