# Complex structures: Redis, Valkey, Kvrocks and Lavik

[简体中文](README.zh-CN.md)

**2026-10-04: main `a565d603`, including merged #244, #246, #247, #249, #258, #259, #260, #262; 25/28 conditions refreshed.**

Batched HSET/SADD import is tracked separately: 0/4 conditions refreshed. Pending charts identify their actual historical version.

Throughput figures fix the command, payload bytes per key, entry size and key count; axes show connections and QPS. Batched-import figures show seconds to fill a fixed dataset. Keep the current main and subsequent unmerged PRs; peers retain historical measurements of the same workload.

Pending conditions retain explicitly labeled historical Lavik measurements. Old observations are not relabeled as the new main.

Redis/Valkey disable persistence. Kvrocks uses uncompressed RAID0, disabled WAL and 80 GiB block/blob cache. Lavik persists through six SPDK NVMe devices without caching field/page payloads. Write QPS compares these configurations, not equivalent durability.

Peers are not rerun this round. Lavik uses AMD EPYC 9V74, 16 vCPUs and 12 serving workers. Points last 8 s (10 s for high-key-count LSET), pipeline=1. Each condition is independently seeded and checked key by key. CPU profiles run separately after complete clean grids. Single sweeps have no statistical confidence intervals.

This round pins the main revision above. Merged optimizations are no longer separate PR curves. Historical observations retain their measured commits; each chart is replaced only after its independent rerun completes.

[Plot sources](current-main.json) · [Runner](run.py) · [Previous-round build and hardware](diagnostics/main-refresh-20261004/host-and-build.json)

[Current build and hardware](diagnostics/main-a565d603-20261004/host-and-build.json)

[Current perf analysis](diagnostics/main-a565d603-20261004/README.md)

[Current plot-data audit](diagnostics/main-a565d603-20261004/report-audit.json)

[Previous-round plot-data audit](diagnostics/main-refresh-20261004/report-audit.json) · [Previous-round audit script](diagnostics/main-refresh-20261004/audit-report.py)

[Hash/Set write profiles](diagnostics/hashset-write-20261004/README.md) · [Ordered metadata optimization and tests](diagnostics/ordered-metadata-20261004/README.md)

Unmerged optimizations: [PR #265](https://github.com/eloqdata/lavik/pull/265) · [PR #266](https://github.com/eloqdata/lavik/pull/266) · [PR #267](https://github.com/eloqdata/lavik/pull/267) · [PR #269](https://github.com/eloqdata/lavik/pull/269)

[Stream suffix directory reuse: throughput, paired runs, perf and tests](diagnostics/stream-suffix-20261004/README.md)

[ZSet member-leaf reuse: throughput, paired runs, perf and tests](diagnostics/zset-member-probe-20261004/README.md)

[List range reads: throughput, memory admission, paired runs and perf](diagnostics/list-read-window-20261004/README.md)

[List reply reservation: incremental repeats, copy hotspots and current results](diagnostics/list-reply-reserve-20261004/README.md)

[List byte-bounded window: draft PR #269 initial results and perf](diagnostics/list-byte-window-20261004/README.md)

[Full-device expiration recovery and CI repair (PR #268; historical observations retain their original binaries)](diagnostics/grouped-expiry-recovery-20261004/README.md)

Failed observations in this run (gaps in figures; errored requests are not successful QPS):

- List LRANGE · 100 MiB/key · 128 B · 16 connections: [recorded failure](raw/lavik-maina565d603-ordered-list-104857600-k8-f128-20261004/list-104857600-128-lrange-c16.error.json).

[100 MiB LRANGE admission analysis](diagnostics/main-refresh-20261004/list-lrange-admission.md)

## List

### LINDEX

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![List LINDEX 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f128-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![List LINDEX 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f1024-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![List LINDEX 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![List LINDEX 1 MiB/key, 1024 B, 64 keys](charts/list-1048576-1024-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![List LINDEX 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lindex-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f128-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![List LINDEX 100 MiB/key, 1024 B, 8 keys](charts/list-104857600-1024-k8-lindex-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f1024-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f1024-20261004/)

### LSET

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![List LSET 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f128-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![List LSET 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f1024-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![List LSET 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f128-20261004/)

1024 B/entry · 50,000 keys · Measured main baseline `a565d603`

![List LSET 1 MiB/key, 1024 B, 50000 keys](charts/list-1048576-1024-k50000-lset-current.png)

[Redis](raw/redis-lset-matched-1048576-k50000-f1024-20261001/) · [Valkey](raw/valkey-lset-matched-1048576-k50000-f1024-20261001/) · [Kvrocks (80 GiB cache)](raw/kvrocks-lset-matched-1048576-k50000-f1024-20261001/) · [Lavik main a565d603](raw/lavik-maina565d603-lset-list-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![List LSET 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lset-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f128-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f128-20261004/)

1024 B/entry · 500 keys · Historical measurement; refresh pending `5d7d12ec`

![List LSET 100 MiB/key, 1024 B, 500 keys](charts/list-104857600-1024-k500-lset-current.png)

[Redis](raw/redis-lset-matched-104857600-k500-f1024-20261001/) · [Valkey](raw/valkey-lset-matched-104857600-k500-f1024-20261001/) · [Kvrocks (80 GiB cache)](raw/kvrocks-lset-matched-104857600-k500-f1024-20261001/) · [Lavik (previous measurement) 5d7d12ec](raw/lavik-main5d7d12ec-lset-list-104857600-k500-f1024-20261004/)

### LRANGE 0 -1

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![List LRANGE 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f128-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![List LRANGE 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f1024-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![List LRANGE 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![List LRANGE 1 MiB/key, 1024 B, 64 keys](charts/list-1048576-1024-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![List LRANGE 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f128-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![List LRANGE 100 MiB/key, 1024 B, 8 keys](charts/list-104857600-1024-k8-lrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f1024-20261004/) · [Lavik draft PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f1024-20261004/)

### RPUSH batched seeding

Independent LSET seeding timings: 32 clients, pipeline=4, 128 one-KiB entries per command, with the same client encoder across all four databases.

#### 1 MiB/key

![List RPUSH fill, 50000 keys](charts/list-1048576-1024-k50000-rpush-fill-current.png)

#### 100 MiB/key

![List RPUSH fill, 500 keys](charts/list-104857600-1024-k500-rpush-fill-current.png)

## Hash

### HGET

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Hash HGET 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hget-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Hash HGET 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hget-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `a565d603`

![Hash HGET 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hget-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · Measured main baseline `a565d603`

![Hash HGET 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hget-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f1024-20261004/)

### HSET

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Hash HSET 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hset-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Hash HSET 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hset-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `a565d603`

![Hash HSET 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hset-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · Measured main baseline `a565d603`

![Hash HSET 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hset-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f1024-20261004/)

### HGETALL

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Hash HGETALL 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hgetall-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Hash HGETALL 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hgetall-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `a565d603`

![Hash HGETALL 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hgetall-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · Measured main baseline `a565d603`

![Hash HGETALL 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hgetall-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f1024-20261004/)

### HSET batched import

#### 1 MiB/key

50,000 keys; 8 clients, pipeline=64, about 16 KiB entries/command. Per-command RESP encoding matches the historical peer workload; elapsed time includes Python client encoding. This is not RESTORE or a server-only throughput ceiling.

1024 B/entry · Historical measurement; import refresh pending `5d7d12ec`

![HSET batched import, 1024 B](charts/hash-1048576-1024-k50000-fill.png)

[Lavik raw](raw/lavik-main5d7d12ec-import-hash-1048576-k50000-f1024-20261004/)

128 B/entry · Historical measurement; import refresh pending `5d7d12ec`

![HSET batched import, 128 B](charts/hash-1048576-128-k50000-fill.png)

[Lavik raw](raw/lavik-main5d7d12ec-import-hash-1048576-k50000-f128-20261004/)

## Set

SADD + SREM mixes the two commands equally; QPS counts commands, not pairs. Random concurrent access can produce no-op additions/removals, so this is not the rate of durable changes.

### SISMEMBER

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Set SISMEMBER 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-sismember-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Set SISMEMBER 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-sismember-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Historical measurement; refresh pending `5d7d12ec`

![Set SISMEMBER 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-sismember-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik (previous measurement) 5d7d12ec](raw/lavik-main5d7d12ec-hashset-set-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · Historical measurement; refresh pending `5d7d12ec`

![Set SISMEMBER 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-sismember-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik (previous measurement) 5d7d12ec](raw/lavik-main5d7d12ec-hashset-set-104857600-k500-f1024-20261004/)

### SADD + SREM

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Set SADD_SREM 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-sadd_srem-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Set SADD_SREM 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-sadd_srem-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Historical measurement; refresh pending `5d7d12ec`

![Set SADD_SREM 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-sadd_srem-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik (previous measurement) 5d7d12ec](raw/lavik-main5d7d12ec-hashset-set-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · Historical measurement; refresh pending `5d7d12ec`

![Set SADD_SREM 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-sadd_srem-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik (previous measurement) 5d7d12ec](raw/lavik-main5d7d12ec-hashset-set-104857600-k500-f1024-20261004/)

### SMEMBERS

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Set SMEMBERS 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-smembers-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Set SMEMBERS 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-smembers-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Historical measurement; refresh pending `5d7d12ec`

![Set SMEMBERS 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-smembers-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik (previous measurement) 5d7d12ec](raw/lavik-main5d7d12ec-hashset-set-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · Historical measurement; refresh pending `5d7d12ec`

![Set SMEMBERS 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-smembers-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik (previous measurement) 5d7d12ec](raw/lavik-main5d7d12ec-hashset-set-104857600-k500-f1024-20261004/)

### SADD batched import

#### 1 MiB/key

50,000 keys; 8 clients, pipeline=64, about 16 KiB entries/command. Per-command RESP encoding matches the historical peer workload; elapsed time includes Python client encoding. This is not RESTORE or a server-only throughput ceiling.

1024 B/entry · Historical measurement; import refresh pending `5d7d12ec`

![SADD batched import, 1024 B](charts/set-1048576-1024-k50000-fill.png)

[Lavik raw](raw/lavik-main5d7d12ec-import-set-1048576-k50000-f1024-20261004/)

128 B/entry · Historical measurement; import refresh pending `5d7d12ec`

![SADD batched import, 128 B](charts/set-1048576-128-k50000-fill.png)

[Lavik raw](raw/lavik-main5d7d12ec-import-set-1048576-k50000-f128-20261004/)

## Sorted Set

### ZSCORE

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZSCORE 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f128-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZSCORE 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZSCORE 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZSCORE 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![Sorted Set ZSCORE 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zscore-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![Sorted Set ZSCORE 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zscore-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f1024-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-104857600-k8-f1024-20261004/)

### ZINCRBY

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZINCRBY 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f128-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZINCRBY 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZINCRBY 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZINCRBY 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![Sorted Set ZINCRBY 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zincrby-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![Sorted Set ZINCRBY 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zincrby-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f1024-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-104857600-k8-f1024-20261004/)

### ZRANGE 0 -1 WITHSCORES

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZRANGE 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f128-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZRANGE 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZRANGE 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZRANGE 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![Sorted Set ZRANGE 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![Sorted Set ZRANGE 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f1024-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-104857600-k8-f1024-20261004/)

## Stream

### XRANGE (one ID)

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![Stream XRANGE 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![Stream XRANGE 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-104857600-k8-f1024-20261004/)

### XADD MAXLEN ~

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XADD_MAXLEN 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XADD_MAXLEN 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XADD_MAXLEN 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XADD_MAXLEN 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![Stream XADD_MAXLEN 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xadd_maxlen-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![Stream XADD_MAXLEN 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xadd_maxlen-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-104857600-k8-f1024-20261004/)

### XRANGE - +

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE_FULL 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE_FULL 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE_FULL 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE_FULL 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![Stream XRANGE_FULL 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xrange_full-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![Stream XRANGE_FULL 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xrange_full-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-104857600-k8-f1024-20261004/)

## Measurement and reproduction

memtier runs on the separate client 172.16.0.5 pinned to CPUs 0–15, with uniformly random keys. HGET/HSET, SISMEMBER, LINDEX/LSET, ZSCORE/ZINCRBY and one-ID XRANGE rotate through eight evenly spaced positions per key, not all fields uniformly. SADD/SREM uses a fixed test member; XADD MAXLEN appends new IDs. Connection points run sequentially within a condition, so later writes inherit values/layout changed by earlier points.

Hash/Set use 50,000 keys at 1 MiB/key and 500 at 100 MiB/key; high-key-count LSET uses the same counts. Other ordered-structure conditions retain the matched 64/8-key peer workloads, explicitly identified in titles. Different key counts are not interchangeable.

Hash/Set use independent RESTORE seeding, transaction cleanup and recovery before measurement. High-key-count LSET seeds with 32 clients, 128 KiB RPUSH batches and pipeline=4. Fill timings remain in raw directories; RESTORE timings are not equated with peer HSET/SADD import timings.

Low-throughput whole-key reads can complete few replies in eight seconds; small differences are not performance conclusions. Eight successful seconds do not establish sustained memory stability: an earlier sustained SMEMBERS run exhausted memory admission. Failed points remain gaps with annotations, never zeroes or interpolated values.

Historical optimization evidence remains in raw/ and diagnostics/; merged PRs are not shown as separate series.
