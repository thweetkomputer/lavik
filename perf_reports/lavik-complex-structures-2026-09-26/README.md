# Complex Redis collection performance: Redis, Valkey, Lavik, and Kvrocks

[简体中文](README.zh-CN.md)

This report compares five Redis-compatible collection types on one server and one
remote memtier client. Each chart fixes the collection type, logical payload per
key, and payload bytes per entry. The horizontal axis is simultaneous
connections; the vertical axis is completed commands per second.

**Latest main remeasurement: [List chapter](#list), `06562381`, including merged #233.** Each LSET chart includes Redis, Valkey, Kvrocks and Lavik main; the merged PR curve is removed. Hash/Set main/PR comparisons are refreshed incrementally below. [Historical perf diagnosis](diagnostics/lset-20261001/README.md).

**Shared commit-dependency optimization: [PR #235](https://github.com/eloqdata/lavik/pull/235) and main `06562381` share charts with Redis, Valkey and Kvrocks. 7/8 Hash/Set conditions complete; pending charts retain their actual measured versions.**

## 2026-10-01 shared commit pipeline comparison

Baseline main `06562381` includes #228/#233. [PR #235](https://github.com/eloqdata/lavik/pull/235) moves waiting for queued owner-local predecessors to background commit. Hash, Set, List, ZSet, Stream and grouped String share this path, including standalone commands. Cross-coordinator EXEC/Lua predecessors and compact demotion retain the existing wait. Small SET/GET already access pending buffers; no data cache was added.

7/8 matched Hash/Set conditions have independent main/PR measurements. Pending charts retain explicitly documented prior versions. Peers reuse matched-key-count results. Redis/Valkey disable persistence; Kvrocks uses uncompressed RAID0, WAL disabled and 80 GiB block/blob caches; Lavik persists through six SPDK NVMe devices. Persistence and cache settings differ. See [Hash/Set manifest](published-main.json) and [LSET manifest](lset-large-published.json).



[Shared-pipeline CPU and I/O diagnosis](diagnostics/shared-pipeline-20261001/README.md): 100 MiB/1 KiB HSET improves by 10.3%–21.1%, peaking at 154.4k QPS; it has not matched Kvrocks. Profiling is separate from clean curves.


For #235, main and PR each start on fresh media, seed the same RESTORE payload, recover, and run eight-second points without profiling: 32 import clients at 1 MiB, eight at 100 MiB. Logical contents match; physical layouts are independent. Earlier 1 MiB main runs used HSET/SADD import, so changes across rounds are not solely code effects. One run per point, without confidence intervals; peers reuse matched-key-count evidence.

## List

Current baseline: main `06562381`, including merged #233. Each LSET chart fixes key counts, key sizes and entry sizes and includes the matched peer workloads.

### LSET with more independent keys

Use 50,000 keys at 1 MiB/key and 500 keys at 100 MiB/key, with 1 KiB elements. Each version receives independently seeded identical initial data; the October 1 runs additionally clear dedicated benchmark media before each seed. Seeding uses 32 seed clients, 128 KiB RPUSH batches and seed pipeline=4. Measured memtier traffic is single-element LSET with pipeline=1, 10 seconds per point, at 80/320/1280/2560/5120 connections. CPU profiles run after the entire clean grid and are excluded from curves. Earlier peer curves retain their own workloads and key counts.

#### 1 MiB/key × 50,000 keys

![LSET 1 MiB, 50,000 keys: Redis / Valkey / Kvrocks / Lavik main](charts/list-lset-1048576-1024-k50000-main-pr.png)

**Four databases on one chart: Redis, Valkey, Kvrocks and Lavik main `06562381`.** #233 is merged. Main was independently reseeded on freshly cleared media and remeasured; its curve replaces both earlier main and PR curves. Lavik reaches **117.8–142.3k QPS**; all five points passed zero-error and before/after all-key cardinality checks. Peers retain the matched-workload measurements. [Main raw](raw/lavik-lset-main0656-1048576-k50000-f1024-20261001/) · [CSV](list-lset-1048576-1024-k50000-main-pr.csv) · [redis raw](raw/redis-lset-matched-1048576-k50000-f1024-20261001/) · [valkey raw](raw/valkey-lset-matched-1048576-k50000-f1024-20261001/) · [kvrocks raw](raw/kvrocks-lset-matched-1048576-k50000-f1024-20261001/).

#### 100 MiB/key × 500 keys

![LSET 100 MiB, 500 keys: Redis / Valkey / Kvrocks / Lavik main](charts/list-lset-104857600-1024-k500-main-pr.png)

**Four databases on one chart: Redis, Valkey, Kvrocks and Lavik main `06562381`.** #233 is merged. Main was independently reseeded on freshly cleared media and remeasured; its curve replaces both earlier main and PR curves. Lavik reaches **92.6–130.3k QPS**; all five points passed zero-error and before/after all-key cardinality checks. Peers retain the matched-workload measurements. [Main raw](raw/lavik-lset-main0656-104857600-k500-f1024-20261001/) · [CSV](list-lset-104857600-1024-k500-main-pr.csv) · [redis raw](raw/redis-lset-matched-104857600-k500-f1024-20261001/) · [valkey raw](raw/valkey-lset-matched-104857600-k500-f1024-20261001/) · [kvrocks raw](raw/kvrocks-lset-matched-104857600-k500-f1024-20261001/).



<details>
<summary>Historical LINDEX / LSET: earlier revisions with fewer keys (expand)</summary>

### LINDEX / LSET

#### 64 KiB per key

![List 64 KiB per key, 128 B entries: LINDEX / LSET QPS by connection count](charts/list-65536-128.png)

![List 64 KiB per key, 1 KiB entries: LINDEX / LSET QPS by connection count](charts/list-65536-1024.png)

#### 1 MiB per key

![List 1 MiB per key, 128 B entries: LINDEX / LSET QPS by connection count](charts/list-1048576-128.png)

![List 1 MiB per key, 1 KiB entries: LINDEX / LSET QPS by connection count](charts/list-1048576-1024.png)

#### 100 MiB per key

![List 100 MiB per key, 128 B entries: LINDEX / LSET QPS by connection count](charts/list-104857600-128.png)

![List 100 MiB per key, 1 KiB entries: LINDEX / LSET QPS by connection count](charts/list-104857600-1024-ab.png)

**2026-09-30 main `a8c926d4` and [PR #233](https://github.com/eloqdata/lavik/pull/233) `759832d8` measured.** 8 × 100 MiB keys, 1 KiB entries; 13 unprofiled points per version cover point reads/writes at 80–5120 connections and full reads at 1/4/16. Peers retain the original matching workload. Both binaries were seeded independently from the same initial logical data. All points have zero errors; every key passed cardinality validation. [Main raw](raw/lavik-maina8-ordered-list-100m-k8-f1024-20260930/) · [PR raw](raw/lavik-fresh759832d8-list-100m-k8-f1024-20260930/) · [Plot provenance](ordered-published.json). Releasing worker state during grouped List reads at `759832d8` raises LINDEX to 3.67–6.10× main and LRANGE at 16 connections to 2.39×. LSET ratios across the five levels are 1.72, 1.27, 0.97, 0.72 and 0.73; high-concurrency writes still need work, so the PR remains a draft. The earlier reused-data LINDEX speedup is retracted: the same old binary produced 58.7k / 433.2k profiled QPS before/after LSET, which cannot establish a code gain. [Same-binary diagnostic](raw/lavik-diagnostic-list-layout-5b1c3064-20260930/).

</details>

### LRANGE 0 -1

#### 64 KiB per key

![List 64 KiB per key, 128 B entries: LRANGE 0 -1 QPS by connection count](charts/list-65536-128-full.png)

![List 64 KiB per key, 1 KiB entries: LRANGE 0 -1 QPS by connection count](charts/list-65536-1024-full.png)

#### 1 MiB per key

![List 1 MiB per key, 128 B entries: LRANGE 0 -1 QPS by connection count](charts/list-1048576-128-full.png)

![List 1 MiB per key, 1 KiB entries: LRANGE 0 -1 QPS by connection count](charts/list-1048576-1024-full.png)

#### 100 MiB per key

![List 100 MiB per key, 128 B entries: LRANGE 0 -1 QPS by connection count](charts/list-104857600-128-full.png)

![List 100 MiB per key, 1 KiB entries: LRANGE 0 -1 QPS by connection count](charts/list-104857600-1024-ab-full.png)

For 1 MiB `LINDEX`, Lavik peaked near 139k QPS with 128 B entries and 677k with 1 KiB entries. The entry-count difference matters, but the available profiling does not isolate one cause.

## Hash

### HGET / HSET

#### 1 MiB

![Hash 1 MiB, 128 B: HGET / HSET](charts/hash-1048576-128-ab.png)

**Measured main `06562381` and [PR #235](https://github.com/eloqdata/lavik/pull/235) `09871950`.** 50,000 keys × 1 MiB/key; 128 B. All points had zero errors; every key passed before/after cardinality validation. [main raw](raw/lavik-pipeline-main-hash-1048576-k50000-f128-20261001/) · [main seed](raw/lavik-seed-pipeline-main-hash-1048576-k50000-f128-20261001/) · [pr raw](raw/lavik-pipeline-pr-hash-1048576-k50000-f128-20261001/) · [pr seed](raw/lavik-seed-pipeline-pr-hash-1048576-k50000-f128-20261001/).

![Hash 1 MiB, 1024 B: HGET / HSET](charts/hash-1048576-1024-ab.png)

**Measured main `06562381` and [PR #235](https://github.com/eloqdata/lavik/pull/235) `09871950`.** 50,000 keys × 1 MiB/key; 1024 B. All points had zero errors; every key passed before/after cardinality validation. [main raw](raw/lavik-pipeline-main-hash-1048576-k50000-f1024-20261001/) · [main seed](raw/lavik-seed-pipeline-main-hash-1048576-k50000-f1024-20261001/) · [pr raw](raw/lavik-pipeline-pr-hash-1048576-k50000-f1024-20261001/) · [pr seed](raw/lavik-seed-pipeline-pr-hash-1048576-k50000-f1024-20261001/).

#### 100 MiB

![Hash 100 MiB, 128 B: HGET / HSET](charts/hash-104857600-128-ab.png)

**Measured main `06562381` and [PR #235](https://github.com/eloqdata/lavik/pull/235) `09871950`.** 500 keys × 100 MiB/key; 128 B. All points had zero errors; every key passed before/after cardinality validation. [main raw](raw/lavik-pipeline-main-hash-104857600-k500-f128-20261001/) · [main seed](raw/lavik-seed-pipeline-main-hash-104857600-k500-f128-20261001/) · [pr raw](raw/lavik-pipeline-pr-hash-104857600-k500-f128-20261001/) · [pr seed](raw/lavik-seed-pipeline-pr-hash-104857600-k500-f128-20261001/).

![Hash 100 MiB, 1024 B: HGET / HSET](charts/hash-104857600-1024-ab.png)

**Measured main `06562381` and [PR #235](https://github.com/eloqdata/lavik/pull/235) `09871950`.** 500 keys × 100 MiB/key; 1024 B. All points had zero errors; every key passed before/after cardinality validation. [main raw](raw/lavik-pipeline-main-hash-104857600-k500-f1024-20261001/) · [main seed](raw/lavik-seed-pipeline-main-hash-104857600-k500-f1024-20261001/) · [pr raw](raw/lavik-pipeline-pr-hash-104857600-k500-f1024-20261001/) · [pr seed](raw/lavik-seed-pipeline-pr-hash-104857600-k500-f1024-20261001/).

### HGETALL

#### 1 MiB

![Hash 1 MiB, 128 B: HGETALL](charts/hash-1048576-128-ab-full.png)

![Hash 1 MiB, 1024 B: HGETALL](charts/hash-1048576-1024-ab-full.png)

#### 100 MiB

![Hash 100 MiB, 128 B: HGETALL](charts/hash-104857600-128-ab-full.png)

![Hash 100 MiB, 1024 B: HGETALL](charts/hash-104857600-1024-ab-full.png)

### Batched import (HSET)

#### 1 MiB / 1024 B

![Hash batched HSET import](charts/hash-1048576-1024-k50000-fill.png)

Historical import measurement: Lavik main `ebe28dd5`, not repeated during this main refresh.

All four use HSET, 16 entries per command, eight clients and pipeline 64. Main fill time: **500.3 seconds**. Persistence settings still differ.

#### 1 MiB / 128 B

![Hash batched HSET import](charts/hash-1048576-128-k50000-fill.png)

Historical import measurement: Lavik main `ebe28dd5`, not repeated during this main refresh.

All four use HSET, 128 entries per command, eight clients and pipeline 64. Main fill time: **1306.3 seconds**. Persistence settings still differ.

### RESTORE

Seed timings with eight RESTORE clients and 500 × 100 MiB keys. Excludes later cleanup/restart; not compared to other databases using SADD/HSET for import.

- 128 B, main `f1268014`: **272.3 s**. [Raw](raw/lavik-seed-mainf126-hash-104857600-k500-f128-20261001/hash-104857600-128.fill.json).

- 1024 B, main `f1268014`: **116.1 s**. [Raw](raw/lavik-seed-mainf126-hash-104857600-k500-f1024-20261001/hash-104857600-1024.fill.json).

## Set

### SISMEMBER / SADD + SREM

#### 1 MiB

![Set 1 MiB, 128 B: SISMEMBER / SADD + SREM](charts/set-1048576-128-ab.png)

**Refreshed measurement: main `f1268014`.** 50,000 keys × 1 MiB/key; 128 B. [Raw](raw/lavik-mainf126-set-1048576-k50000-f128-20261001/). [Seed provenance](raw/lavik-seed-mainf126-set-1048576-k50000-f128-20261001/).

![Set 1 MiB, 1024 B: SISMEMBER / SADD + SREM](charts/set-1048576-1024-ab.png)

**Measured main `06562381` and [PR #235](https://github.com/eloqdata/lavik/pull/235) `09871950`.** 50,000 keys × 1 MiB/key; 1024 B. All points had zero errors; every key passed before/after cardinality validation. [main raw](raw/lavik-pipeline-main-set-1048576-k50000-f1024-20261001/) · [main seed](raw/lavik-seed-pipeline-main-set-1048576-k50000-f1024-20261001/) · [pr raw](raw/lavik-pipeline-pr-set-1048576-k50000-f1024-20261001/) · [pr seed](raw/lavik-seed-pipeline-pr-set-1048576-k50000-f1024-20261001/).

#### 100 MiB

![Set 100 MiB, 128 B: SISMEMBER / SADD + SREM](charts/set-104857600-128-ab.png)

**Measured main `06562381` and [PR #235](https://github.com/eloqdata/lavik/pull/235) `09871950`.** 500 keys × 100 MiB/key; 128 B. All points had zero errors; every key passed before/after cardinality validation. [main raw](raw/lavik-pipeline-main-set-104857600-k500-f128-20261001/) · [main seed](raw/lavik-seed-pipeline-main-set-104857600-k500-f128-20261001/) · [pr raw](raw/lavik-pipeline-pr-set-104857600-k500-f128-20261001/) · [pr seed](raw/lavik-seed-pipeline-pr-set-104857600-k500-f128-20261001/).

![Set 100 MiB, 1024 B: SISMEMBER / SADD + SREM](charts/set-104857600-1024-ab.png)

**Measured main `06562381` and [PR #235](https://github.com/eloqdata/lavik/pull/235) `09871950`.** 500 keys × 100 MiB/key; 1024 B. All points had zero errors; every key passed before/after cardinality validation. [main raw](raw/lavik-pipeline-main-set-104857600-k500-f1024-20261001/) · [main seed](raw/lavik-seed-pipeline-main-set-104857600-k500-f1024-20261001/) · [pr raw](raw/lavik-pipeline-pr-set-104857600-k500-f1024-20261001/) · [pr seed](raw/lavik-seed-pipeline-pr-set-104857600-k500-f1024-20261001/).

### SMEMBERS

#### 1 MiB

![Set 1 MiB, 128 B: SMEMBERS](charts/set-1048576-128-ab-full.png)

![Set 1 MiB, 1024 B: SMEMBERS](charts/set-1048576-1024-ab-full.png)

#### 100 MiB

![Set 100 MiB, 128 B: SMEMBERS](charts/set-104857600-128-ab-full.png)

![Set 100 MiB, 1024 B: SMEMBERS](charts/set-104857600-1024-ab-full.png)

Historical sustained SMEMBERS repeats at 100 MiB / 128 B and 16 connections encountered memory-admission rejection. Successful eight-second points do not establish sustained stability. [Failure evidence](raw/lavik-fullcheck-maina6d-set-100m-k500-f128-20260930/).

### Batched import (SADD)

#### 1 MiB / 1024 B

![Set batched SADD import](charts/set-1048576-1024-k50000-fill.png)

Historical import measurement: Lavik main `ebe28dd5`, not repeated during this main refresh.

All four use SADD, 16 entries per command, eight clients and pipeline 64. Main fill time: **517.9 seconds**. Persistence settings still differ.

#### 1 MiB / 128 B

![Set batched SADD import](charts/set-1048576-128-k50000-fill.png)

Historical import measurement: Lavik main `ebe28dd5`, not repeated during this main refresh.

All four use SADD, 128 entries per command, eight clients and pipeline 64. Main fill time: **1724.2 seconds**. Persistence settings still differ.

The matching 100 MiB SADD import measurement is pending. The previous mixed RESTORE/SADD figure has been removed.

### RESTORE

Seed timings with eight RESTORE clients and 500 × 100 MiB keys. Excludes later cleanup/restart; not compared to other databases using SADD/HSET for import.

- 128 B, main `f1268014`: **274.1 s**. [Raw](raw/lavik-seed-mainf126-set-104857600-k500-f128-20261001/set-104857600-128.fill.json).

- 1024 B, main `f1268014`: **134.5 s**. [Raw](raw/lavik-seed-mainf126-set-104857600-k500-f1024-20261001/set-104857600-1024.fill.json).

## Workloads

For positional reads and overwrites, memtier cycles through eight evenly spaced
entry positions per key. The earlier 64 KiB and 1 MiB conditions use 64
keys, and the 100 MiB extension uses eight. This Hash/Set retest uses 50,000
keys at 1 MiB and 500 at 100 MiB. Each operation chooses a key uniformly
within its condition. Each field value, member, or element is exactly 128 B
or 1 KiB.
Stream field names and collection metadata are extra. All seeded entries and
sample payloads are checked before measurement. Cardinality is checked after
the write sweep. Set toggle commands can return no-op results when their
randomly chosen key is already in the target state, so their throughput is the
combined command rate, not the rate of durable mutations.

Each refreshed Hash/Set main condition is independently seeded and recovered, then runs full reads, point reads and writes. Writes at successive connection levels change accessed field values and physical layout.

## Test configuration

Bulk imports use a Python client on the server host; point-command QPS uses memtier on the separate client host. New import comparisons share pre-encoded operand bytes while preserving RESP commands, connection counts and pipelines. Kvrocks uses 16 workers.

- Server: 172.16.0.4, 16 vCPUs on AMD EPYC 9V74, CPUs 0–15, 100 Gb/s NIC.
  Redis 8.8.0 and Valkey 9.1.0 use 12 I/O
  threads, with RDB and AOF disabled. Lavik uses 12 workers, kernel TCP, and
  six dedicated SPDK NVMe devices. These are different durability settings.
- List and Sorted Set 100 MiB / 1 KiB samples use the main revisions identified with each figure; other conditions retain early [PR #203](https://github.com/eloqdata/lavik/pull/203)
  binary `646a7b4e`. The Hash/Set and Stream chapters state their merged-main
  versions. Measurements from different versions are not joined into one Lavik curve.
- Kvrocks uses the same cache and compression settings across sizes. The
  List and Sorted Set 64 KiB and 1 MiB points were retested on 2026-09-27;
  Hash and Set were freshly filled with this retest's key counts. The saved
  configuration enables an 80 GiB RocksDB block
  cache and blob caching; its hot-read QPS therefore includes a large memory
  cache, unlike Lavik's data-page path.
- Client: 172.16.0.5, 16 vCPUs on AMD EPYC 9V45, memtier_benchmark 2.5.1,
  pipeline 1, random key selection, and eight seconds per point. Point
  operations use 16 client threads and 80/320/1280/2560/5120 connections.
  Full reads use 16/80 connections for 64 KiB and 1 MiB, and 1/4/16 for
  100 MiB; the client thread count is capped by the connection count.
- Each condition is filled from scratch using concurrent RESP clients on
  disjoint keys. Earlier runs used the default eight; newer provenance records
  the seed-client count, target payload bytes per seed command, and pipeline.
  Reads run before writes, and writes preserve approximately the original
  collection length. The same keys are used at all connection levels within
  a condition. Fill pipelines are bounded; each run's provenance gives its depth.
- Logical sizes describe payload bytes only, not Redis memory usage or Lavik
  disk consumption. The earlier List, Sorted Set, and Stream runs use hot-key
  counts stated in their sections; Hash and Set use 50,000 or 500 keys.
- QPS and latency come from memtier's JSON output. The script rejects
  connection errors, interrupted runs, and server error responses.

## Sorted Set

Each figure identifies its measured revision and key count. The 100 MiB / 1 KiB small-key-count comparison uses main `a8c926d4` and PR #233. Other earlier four-product curves use Lavik `646a7b4e`, as recorded in the [raw CSV](results.csv).

### ZSCORE / ZINCRBY

#### 64 KiB per key

![Sorted Set 64 KiB per key, 128 B entries: ZSCORE / ZINCRBY QPS by connection count](charts/zset-65536-128.png)

![Sorted Set 64 KiB per key, 1 KiB entries: ZSCORE / ZINCRBY QPS by connection count](charts/zset-65536-1024.png)

#### 1 MiB per key

![Sorted Set 1 MiB per key, 128 B entries: ZSCORE / ZINCRBY QPS by connection count](charts/zset-1048576-128.png)

![Sorted Set 1 MiB per key, 1 KiB entries: ZSCORE / ZINCRBY QPS by connection count](charts/zset-1048576-1024.png)

#### 100 MiB per key

![Sorted Set 100 MiB per key, 128 B entries: ZSCORE / ZINCRBY QPS by connection count](charts/zset-104857600-128.png)

![Sorted Set 100 MiB per key, 1 KiB entries: ZSCORE / ZINCRBY QPS by connection count](charts/zset-104857600-1024-ab.png)

**2026-09-30 main `a8c926d4` and [PR #233](https://github.com/eloqdata/lavik/pull/233) `5b1c3064` measured.** 8 × 100 MiB keys, 1 KiB entries; 13 unprofiled points per version cover point reads/writes at 80–5120 connections and full reads at 1/4/16. Peers retain the original matching workload. Both binaries were seeded independently from the same initial logical data. All points have zero errors; every key passed cardinality validation. [Main raw](raw/lavik-maina8-ordered-zset-100m-k8-f1024-20260930/) · [PR raw](raw/lavik-fresh5b1c3064-zset-100m-k8-f1024-20260930/) · [Plot provenance](ordered-published.json). **With independent seeding, ZINCRBY improves about 70–76% at every connection level, peaking at 8,935 QPS; it remains far below Kvrocks. ZSCORE is about 2–8% lower, while full ZRANGE at 16 connections is about 13% higher. Remaining write bottlenecks and point-read regressions need further investigation.**


### ZRANGE WITHSCORES

#### 64 KiB per key

![Sorted Set 64 KiB per key, 128 B entries: ZRANGE WITHSCORES QPS by connection count](charts/zset-65536-128-full.png)

![Sorted Set 64 KiB per key, 1 KiB entries: ZRANGE WITHSCORES QPS by connection count](charts/zset-65536-1024-full.png)

#### 1 MiB per key

![Sorted Set 1 MiB per key, 128 B entries: ZRANGE WITHSCORES QPS by connection count](charts/zset-1048576-128-full.png)

![Sorted Set 1 MiB per key, 1 KiB entries: ZRANGE WITHSCORES QPS by connection count](charts/zset-1048576-1024-full.png)

#### 100 MiB per key

![Sorted Set 100 MiB per key, 128 B entries: ZRANGE WITHSCORES QPS by connection count](charts/zset-104857600-128-full.png)

![Sorted Set 100 MiB per key, 1 KiB entries: ZRANGE WITHSCORES QPS by connection count](charts/zset-104857600-1024-ab-full.png)

## Measurement limits

Each point is one eight-second run, without a repeated-run confidence interval. Redis/Valkey have persistence disabled; Kvrocks has WAL disabled with an 80 GiB block cache; Lavik commits to SPDK. Write rates do not compare equivalent durability. Some 100 MiB full-read points completed fewer than 100 replies, so small differences are fragile.

The [HGETALL memory investigation](diagnostics/hgetall-oom-20260929/README.md) and [HSET write diagnostic](diagnostics/hset-20260929/README.md) retain the analysis. Earlier Hash/Set samples remain under `raw/` and are not presented as current-main values.

## Stream

Stream 100 MiB / 1 KiB now compares main `a8c926d4` with the current optimization PR; smaller cases retain measured merged main `9acd7b6f`. The 64 KiB and 1 MiB cases use 64 hot keys with 128 B or 1 KiB entries; the 100 MiB case uses eight keys with 1 KiB entries. The horizontal axis is connection count and the vertical axis is QPS; each figure contains one Lavik main curve, plus any measured unmerged optimization PR.

Point reads and writes cover 80–5120 connections. Full reads use 16/80 for the smaller sizes and 1/4/16 for 100 MiB. Redis and Valkey have persistence disabled; Kvrocks has WAL disabled with an 80 GiB block cache; Lavik commits to SPDK. Write QPS reflects these configurations.

[Small and historical 100 MiB points](stream-latest.csv), [current 100 MiB points](stream-104857600-1024-current.csv), and [current plot provenance](ordered-published.json); Lavik [small](raw/lavik-main9acd-stream-small-20260929/) and [100 MiB](raw/lavik-main9acd-stream-100m-20260929/) raw runs retain the evidence. Each point is one eight-second run. Older optimization-stage samples remain under `raw/` and are not plotted.

### Exact-ID `XRANGE`

#### 64 KiB per key

![64 KiB per key, 128 B entries: Exact-ID `XRANGE` QPS by connection count](charts/stream-65536-128-xrange-latest.png)

![64 KiB per key, 1 KiB entries: Exact-ID `XRANGE` QPS by connection count](charts/stream-65536-1024-xrange-latest.png)

#### 1 MiB per key

![1 MiB per key, 128 B entries: Exact-ID `XRANGE` QPS by connection count](charts/stream-1048576-128-xrange-latest.png)

![1 MiB per key, 1 KiB entries: Exact-ID `XRANGE` QPS by connection count](charts/stream-1048576-1024-xrange-latest.png)

#### 100 MiB per key

![100 MiB per key, 1 KiB entries: Exact-ID `XRANGE` QPS by connection count](charts/stream-104857600-1024-xrange-latest.png)

### `XADD MAXLEN`

#### 64 KiB per key

![64 KiB per key, 128 B entries: `XADD MAXLEN` QPS by connection count](charts/stream-65536-128-xadd_maxlen-latest.png)

![64 KiB per key, 1 KiB entries: `XADD MAXLEN` QPS by connection count](charts/stream-65536-1024-xadd_maxlen-latest.png)

#### 1 MiB per key

![1 MiB per key, 128 B entries: `XADD MAXLEN` QPS by connection count](charts/stream-1048576-128-xadd_maxlen-latest.png)

![1 MiB per key, 1 KiB entries: `XADD MAXLEN` QPS by connection count](charts/stream-1048576-1024-xadd_maxlen-latest.png)

#### 100 MiB per key

![100 MiB per key, 1 KiB entries: `XADD MAXLEN` QPS by connection count](charts/stream-104857600-1024-xadd_maxlen-latest.png)

**2026-09-30 main `a8c926d4` and [PR #233](https://github.com/eloqdata/lavik/pull/233) `5b1c3064` measured.** 8 × 100 MiB keys, 1 KiB entries; 13 unprofiled points per version cover point reads/writes at 80–5120 connections and full reads at 1/4/16. Peers retain the original matching workload. Both binaries were seeded independently from the same initial logical data. All points have zero errors; every key passed cardinality validation. [Main raw](raw/lavik-maina8-fresh-stream-100m-k8-f1024-20260930/) · [PR raw](raw/lavik-fresh5b1c3064-stream-100m-k8-f1024-20260930/) · [Plot provenance](ordered-published.json). With independent fresh seeds, XADD MAXLEN reaches 1.96–2.49× main across all five connection levels (5.86k–6.32k QPS), still well below Kvrocks. XRANGE ranges from roughly unchanged to 9% lower. This replaces the preliminary reused-data run; differences from that run cannot be attributed solely to code.


### Full `XRANGE - +`

#### 64 KiB per key

![64 KiB per key, 128 B entries: Full `XRANGE - +` QPS by connection count](charts/stream-65536-128-xrange_full-latest.png)

![64 KiB per key, 1 KiB entries: Full `XRANGE - +` QPS by connection count](charts/stream-65536-1024-xrange_full-latest.png)

#### 1 MiB per key

![1 MiB per key, 128 B entries: Full `XRANGE - +` QPS by connection count](charts/stream-1048576-128-xrange_full-latest.png)

![1 MiB per key, 1 KiB entries: Full `XRANGE - +` QPS by connection count](charts/stream-1048576-1024-xrange_full-latest.png)

#### 100 MiB per key

![100 MiB per key, 1 KiB entries: Full `XRANGE - +` QPS by connection count](charts/stream-104857600-1024-xrange_full-latest.png)

## Reproduce

Run from this directory, with an otherwise idle benchmark server and client:

```bash
python3 run.py redis
python3 run.py valkey
python3 run.py redis --levels 16,80 --mode full
python3 run.py valkey --levels 16,80 --mode full
sudo python3 spdk_host.py prepare --discard-scratch
sudo python3 run.py lavik
sudo python3 run.py lavik --levels 16,80 --mode full
sudo python3 run.py lavik --tag backlog64 --types hash --sizes 1048576 \
  --fields 128 --levels 80,320,2560 --backlog-mb 64
sudo python3 spdk_host.py restore
sudo python3 kvrocks_host.py prepare --discard-scratch
python3 run.py kvrocks --sizes 65536,1048576 --fields 128,1024 --keys 64 \
  --mode both --levels 80,320,1280,2560,5120 --full-levels 16,80 \
  --seed-pipeline 64 --seconds 8 --continue-on-error
sudo python3 kvrocks_host.py restore
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python collect_plot.py
```

For the 100 MiB extension, run the four products serially on an idle server.
The six scratch drives are discarded separately for Lavik SPDK and Kvrocks
RAID0; both helpers verify their serial numbers and PCI addresses first.

```bash
large=(--tag 100m --sizes 104857600 --fields 128,1024 --keys 8 \
  --mode both --levels 80,320,1280,2560,5120 --full-levels 1,4,16 \
  --seed-pipeline 64 --seconds 8)
python3 run.py redis "${large[@]}"
python3 run.py valkey "${large[@]}"
sudo python3 spdk_host.py prepare --discard-scratch
sudo python3 run.py lavik "${large[@]}" --continue-on-error
sudo python3 spdk_host.py restore
sudo python3 kvrocks_host.py prepare --discard-scratch
python3 run.py kvrocks "${large[@]}" --continue-on-error
sudo python3 kvrocks_host.py restore
.venv/bin/python collect_plot.py
```

The SPDK preparation helper verifies the six dedicated controller serial
numbers and PCI addresses before discarding their scratch datasets. Do not
prepare devices that contain data to keep. Server commands, binary hashes,
memtier invocations, fill timings, validation checks, and per-run JSON are
committed under `raw/`. Console output is retained locally and omitted from
the branch because the JSON contains the measured data.

The commands above reproduce the earlier 64/8-key figures. This Hash/Set
retest fills one collection type, size, and entry length per run. The tag
matches the raw directory name. For example, Redis Hash at 1 MiB per key,
50,000 keys, and 128 B per field:

```bash
python3 run_with_memory_guard.py --minimum-available-gib=20 -- \
  python3 run.py redis --tag=hash-1m-k50000-f128-20260929 \
  --types=hash --sizes=1048576 --fields=128 --keys=50000 \
  --levels=80,320,1280,2560,5120 --full-levels=16,80 \
  --seconds=8 --mode=both --seed-pipeline=64 --continue-on-error
```

For 100 MiB use `--sizes=104857600 --keys=500 --full-levels=1,4,16`.
Run both 128 B and 1 KiB for Hash and Set. Valkey uses the same arguments.
Run Kvrocks after `kvrocks_host.py prepare --discard-scratch`, then restore
RAID0. After that, prepare the SPDK devices and run Lavik as root with its
`--binary`, `--source-commit`, and a `main<first-eight-commit-digits>-` tag
prefix. Each run's provenance JSON records the exact source revision and
binary SHA256. Most Lavik conditions use
`--fill-workers=64 --seed-command-bytes=65536` to seed disjoint keys with fewer
setup commands. The first Set 1 MiB/1 KiB run used the earlier default of
eight; Set 1 MiB/128 B still used 16 KiB target batches. Newer provenance
gives the actual value for each run.
The new 2026-09-30 1 MiB main/PR comparisons seed with batched HSET/SADD:
`--fill-workers=8 --seed-pipeline=64 --seed-command-bytes=16384`, without `--seed-dump-path`.
Each command contains 128 entries at 128 B or 16 entries at 1 KiB, matching the
recorded peer fills. Main starts on empty benchmark devices; PR uses
`--reuse-seeded-data --seed-source-tag=<main-tag>` to recover the same keys.
Every key's cardinality is validated before and after measurements. Import charts
compare matching commands and batches. The RDB procedure below is only for
standalone RESTORE measurements and the earlier 100 MiB benchmark preparation.

For Lavik's 100 MiB/128 B runs, the [RDB seed generator](make_rdb_seed_dump.py)
creates one 819,200-entry Hash or Set, which `RESTORE` imports into 500 distinct
keys. The generator verifies Redis's checksum and recalculates it for Lavik's
RDB v11 reader. The run records the seed SHA256. Generate the Set seed with:

```bash
python3 make_rdb_seed_dump.py set 104857600 128 /tmp/lavik-set-100m-f128-generated.dump \
  --redis-binary=/mnt/dev/peer-bench/redis/v8.8.0/src/src/redis-server
```

The Lavik run also uses
`--fill-workers=8 --seed-dump-path=/tmp/lavik-set-100m-f128-generated.dump`.
For Hash, change `set` to `hash` and use a separate output file. Formal points
start after validation of every key's cardinality, one content sample, and
settled TxCleaner backlog.

Redraw one condition with:

```bash
.venv/bin/python plot_set_hash_high_keys.py set 1048576 128 \
  --main-tag pr222faef28d9-set-1m-k50000-f128-leaf-c64-20260930 \
  --main-commit faef28d9411fa32ae5f3a39915a6ca2c2b01f191 \
  --main-sha256 b0c664967357b9c648f066b11ff33febb10540bf941c36b6ac0973690d212b8c
```
