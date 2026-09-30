# Complex Redis collection performance: Redis, Valkey, Lavik, and Kvrocks

[简体中文](README.zh-CN.md)

This report compares five Redis-compatible collection types on one server and one
remote memtier client. Each chart fixes the collection type, logical payload per
key, and payload bytes per entry. The horizontal axis is simultaneous
connections; the vertical axis is completed commands per second.

## 2026-09-30 main and PR #228

[PR #222](https://github.com/eloqdata/lavik/pull/222) is merged; current main is `a6e93d3d`. Merged PR curves have been removed. The new [PR #228](https://github.com/eloqdata/lavik/pull/228) is overlaid only where its A/B measurement is complete.

**Fresh main measurements: Hash/1 MiB/128 B, Hash/1 MiB/1024 B, Hash/100 MiB/128 B, Hash/100 MiB/1024 B, Set/1 MiB/128 B, Set/1 MiB/1024 B, Set/100 MiB/128 B, Set/100 MiB/1024 B.** Exact versions, binary hashes and unmerged PR sources are in the [plot manifest](published-main.json). Stream, List and Sorted Set results and charts remain available.

PR #228 currently contains `80792c41`. All published PR curves measure this commit.

This round uses perf first to identify allocations, copies and repeated work. PR #228 trims temporary containers, metadata queries and extra scheduling, without adding a data cache or changing the durable format. **Parity with Kvrocks across all write workloads has not been achieved.** Clean chart runs do not run perf; separate 30-second diagnostic workloads include 20 seconds of perf sampling, retained in raw directories. The [profiling script](profile_grouped_writes.py) reproduces the process.

Point reads and writes use 80/320/1280/2560/5120 connections; full reads use 16/80 for 1 MiB and 1/4/16 for 100 MiB. Each point runs for eight seconds. Redis/Valkey persistence is disabled. Kvrocks uses uncompressed RAID0, WAL disabled, and an 80 GiB cache; Lavik uses durable SPDK on six NVMe drives. These settings affect absolute write QPS. Single runs have no confidence intervals. Raw evidence is in [raw/](raw/).

### Write results from this round

All eight Hash/Set conditions now compare current main and PR #228: **200 eight-second points, zero errors**, with every key validated before/after. At matching connection counts, SADD + SREM measures **+7.7% to +35.9%** and HSET **+0.7% to +19.4%**. These are single-run ranges, not equal gains for every workload. [Calculated results](pr-228-comparison.json) retain each ratio and the four-database peaks; complete curves follow below.

Additional sustained SMEMBERS checks for 100 MiB Sets with 128 B members returned scratch-admission errors on both main and PR. **Zero errors in eight-second points does not establish sustained concurrency stability.** Failed raw runs, the cause and full-read repeat checks are disclosed in the SMEMBERS/HGETALL sections and excluded from valid throughput comparisons.

### Perf: removed work and remaining cost

In separate 1,280-connection write diagnostics, allocator/free symbols account for **12.19% → 10.72%** of self CPU samples for Set/128 B and **16.80% → 14.53%** for Hash/1 KiB. Active-group lookup decreases from **2.01% → 0.19%** and **2.43% → 0.93%**, respectively. These include all reported symbols and measure CPU shares, not allocation counts. Inlined work may be attributed to callers; the numbers do not measure all bytes copied.

The PR inlines single-page temporary arrays in coroutine frames, removes temporary tree containers and redundant extent queries, replaces unchanged routing intervals directly, and copies compact physical-index arrays without expanding and re-encoding unchanged coordinates through an intermediate vector. Snapshot ownership, memory admission and commit dependencies remain intact.

Named copy/zero routines still account for about **2%–3%**, and physical-record lookup about **4%–5%**. The write gains do not close the Kvrocks gap. Further investigation should trace repeated lookups and temporary objects across read, publication and retirement before changing metadata-update algorithms. Current evidence does not attribute the entire gap to disk reads or allocators; peer durability and cache settings also differ.

[Set main samples](raw/lavik-maina6d-set-1m-k50000-f128-20260930/diagnostic-c1280/cpu-categories.json), [Set PR samples](raw/lavik-worktrim8079-set-1m-k50000-f128-20260930/diagnostic-c1280/cpu-categories.json), [Hash main samples](raw/lavik-maina6d-hash-1m-k50000-f1024-20260930/diagnostic-c1280/cpu-categories.json), [Hash PR samples](raw/lavik-worktrim8079-hash-1m-k50000-f1024-20260930/diagnostic-c1280/cpu-categories.json). Each directory includes all-symbol reports, sampling parameters and throughput.

## Hash

Each point-read/write chart contains both commands. The 1 MiB and 100 MiB runs use 50,000 and 500 keys, respectively.

### HGET / HSET

#### 1 MiB per key

![Hash 1 MiB per key, 128 B entries: HGET and HSET QPS by connection count](charts/hash-1048576-128-ab.png)

**Fresh main `a6e93d3d` vs [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41`.** 50,000 × 1 MiB keys, 128 B entries; 12 points per version, zero errors, every key validated before/after. HSET is **1.01–1.16×** main at matching connections. Curves use unprofiled eight-second runs; single-run differences are not established gains. Where sampled, perf diagnostics are retained separately.
[main raw](raw/lavik-maina6d-hash-1m-k50000-f128-20260930/), [PR raw](raw/lavik-worktrim8079-hash-1m-k50000-f128-20260930/).

![Hash 1 MiB per key, 1 KiB entries: HGET and HSET QPS by connection count](charts/hash-1048576-1024-ab.png)

**Fresh main `a6e93d3d` vs [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41`.** 50,000 × 1 MiB keys, 1024 B entries; 12 points per version, zero errors, every key validated before/after. HSET is **1.02–1.19×** main at matching connections. Curves use unprofiled eight-second runs; single-run differences are not established gains. Where sampled, perf diagnostics are retained separately.
[main raw](raw/lavik-maina6d-hash-1m-k50000-f1024-20260930/), [PR raw](raw/lavik-worktrim8079-hash-1m-k50000-f1024-20260930/).

#### 100 MiB per key

![Hash 100 MiB per key, 128 B entries: HGET and HSET QPS by connection count](charts/hash-104857600-128-ab.png)

**Fresh main `a6e93d3d` vs [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41`.** 500 × 100 MiB keys, 128 B entries; 13 points per version, zero errors, every key validated before/after. HSET is **1.11–1.12×** main at matching connections. Curves use unprofiled eight-second runs; single-run differences are not established gains. Where sampled, perf diagnostics are retained separately.
[main raw](raw/lavik-maina6d-hash-100m-k500-f128-20260930/), [PR raw](raw/lavik-worktrim8079-hash-100m-k500-f128-20260930/).

RESTORE only prepares the dataset; after cleanup settles, both main and PR restart/recover before measurement. This is not an import-speed comparison with batched SADD/HSET. [Seed provenance](raw/lavik-seedmaina6d-hash-100m-k500-f128-20260930/).

![Hash 100 MiB per key, 1 KiB entries: HGET and HSET QPS by connection count](charts/hash-104857600-1024-ab.png)

**Fresh main `a6e93d3d` vs [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41`.** 500 × 100 MiB keys, 1024 B entries; 13 points per version, zero errors, every key validated before/after. HSET is **1.06–1.16×** main at matching connections. Curves use unprofiled eight-second runs; single-run differences are not established gains. Where sampled, perf diagnostics are retained separately.
[main raw](raw/lavik-maina6d-hash-100m-k500-f1024-20260930/), [PR raw](raw/lavik-worktrim8079-hash-100m-k500-f1024-20260930/).

RESTORE only prepares the dataset; after cleanup settles, both main and PR restart/recover before measurement. This is not an import-speed comparison with batched SADD/HSET. [Seed provenance](raw/lavik-seedmaina6d-hash-100m-k500-f1024-20260930/).

**HGET drop under investigation:** In this eight-second grid, PR is about 23% / 20% below main at 1,280 / 2,560 connections. These points remain in the curves. Longer read-only repeats on one fixed dataset are running; the PR remains draft.

### HGETALL

#### 1 MiB per key

![Hash 1 MiB per key, 128 B entries: HGETALL QPS by connection count](charts/hash-1048576-128-ab-full.png)

**80-connection long-run check:** three consecutive unprofiled 30-second repetitions per version: main **1,830, 1,815, 1,797 QPS**, PR **1,861, 1,857, 1,842 QPS**; mean ratio **1.022×**. Both recover the same dataset; all 50,000 key cardinalities are unchanged and runs have zero errors. The chart retains its original eight-second points. Versions run sequentially; three repetitions do not provide confidence intervals. [Results](hash-1048576-128-full-read-repeats.json), [main raw](raw/lavik-fullcheck-maina6d-hash-1m-k50000-f128-20260930/), [PR raw](raw/lavik-fullcheck-worktrim8079-hash-1m-k50000-f128-20260930/), [script](repeat_grouped_full_reads.py).

**Return-to-main check:** retaining the same dataset after PR, main produces **1,842, 1,838, 1,842 QPS** over three more repetitions; PR / return-main mean ratio is **1.007×**, with every key validated and zero errors. These checks do not establish a stable HGETALL regression. [Raw](raw/lavik-fullcheck-returnmaina6d-hash-1m-k50000-f128-20260930/).

Separate HGETALL diagnostics, excluded from the three clean repetitions, put memory-move self samples at **16.63% / 15.89%** for main / PR, and Hash-entry vector append at **9.68% / 9.18%**. Both versions have these hotspots. `LoadGroupedHashValue` appends entries without reserving the known total, a candidate for a further experiment; not all append samples are avoidable growth cost. [main profile](raw/lavik-fullcheck-maina6d-hash-1m-k50000-f128-20260930/diagnostic-full/self.txt), [PR profile](raw/lavik-fullcheck-worktrim8079-hash-1m-k50000-f128-20260930/diagnostic-full/self.txt). Add `--profile-full-read` to reproduce the separate profile after the three clean repetitions.


![Hash 1 MiB per key, 1 KiB entries: HGETALL QPS by connection count](charts/hash-1048576-1024-ab-full.png)

#### 100 MiB per key

![Hash 100 MiB per key, 128 B entries: HGETALL QPS by connection count](charts/hash-104857600-128-ab-full.png)

![Hash 100 MiB per key, 1 KiB entries: HGETALL QPS by connection count](charts/hash-104857600-1024-ab-full.png)

### Batched import (HSET)

#### 1 MiB / 1024 B

![Hash batched HSET import](charts/hash-1048576-1024-k50000-fill.png)

Historical import measurement: Lavik main `ebe28dd5`, not a fresh run of `a6e93d3d` or PR #228.

All four use HSET, 16 entries per command, eight clients and pipeline 64. Main fill time: **500.3 seconds**. Persistence settings still differ.

#### 1 MiB / 128 B

![Hash batched HSET import](charts/hash-1048576-128-k50000-fill.png)

Historical import measurement: Lavik main `ebe28dd5`, not a fresh run of `a6e93d3d` or PR #228.

All four use HSET, 128 entries per command, eight clients and pipeline 64. Main fill time: **1306.3 seconds**. Persistence settings still differ.

### RESTORE

Main `a6e93d3d`, eight concurrent RESTORE clients, 500 × 100 MiB keys per condition, every key validated. These standalone seed timings exclude subsequent cleanup waits and recovery; they are not compared with peer batched SADD/HSET import.

- 128 B: **288.4 seconds**. [Raw](raw/lavik-seedmaina6d-hash-100m-k500-f128-20260930/hash-104857600-128.fill.json).
- 1024 B: **111.5 seconds**. [Raw](raw/lavik-seedmaina6d-hash-100m-k500-f1024-20260930/hash-104857600-1024.fill.json).

## Set

Each point-read/write chart contains both commands. The 1 MiB and 100 MiB runs use 50,000 and 500 keys, respectively.

### SISMEMBER / SADD/SREM

#### 1 MiB per key

![Set 1 MiB per key, 128 B entries: SISMEMBER and SADD/SREM QPS by connection count](charts/set-1048576-128-ab.png)

**Fresh main `a6e93d3d` vs [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41`.** 50,000 × 1 MiB keys, 128 B entries; 12 points per version, zero errors, every key validated before/after. SADD + SREM is **1.08–1.18×** main at matching connections. Curves use unprofiled eight-second runs; single-run differences are not established gains. Where sampled, perf diagnostics are retained separately.
[main raw](raw/lavik-maina6d-set-1m-k50000-f128-20260930/), [PR raw](raw/lavik-worktrim8079-set-1m-k50000-f128-20260930/).

![Set 1 MiB per key, 1 KiB entries: SISMEMBER and SADD/SREM QPS by connection count](charts/set-1048576-1024-ab.png)

**Fresh main `a6e93d3d` vs [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41`.** 50,000 × 1 MiB keys, 1024 B entries; 12 points per version, zero errors, every key validated before/after. SADD + SREM is **1.12–1.19×** main at matching connections. Curves use unprofiled eight-second runs; single-run differences are not established gains. Where sampled, perf diagnostics are retained separately.
[main raw](raw/lavik-maina6r-set-1m-k50000-f1024-20260930/), [PR raw](raw/lavik-worktrim8079-set-1m-k50000-f1024-20260930/).

#### 100 MiB per key

![Set 100 MiB per key, 128 B entries: SISMEMBER and SADD/SREM QPS by connection count](charts/set-104857600-128-ab.png)

**Fresh main `a6e93d3d` vs [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41`.** 500 × 100 MiB keys, 128 B entries; 13 points per version, zero errors, every key validated before/after. SADD + SREM is **1.16–1.36×** main at matching connections. Curves use unprofiled eight-second runs; single-run differences are not established gains. Where sampled, perf diagnostics are retained separately.
[main raw](raw/lavik-maina6d-set-100m-k500-f128-20260930/), [PR raw](raw/lavik-worktrim8079-set-100m-k500-f128-20260930/).

RESTORE only prepares the dataset; after cleanup settles, both main and PR restart/recover before measurement. This is not an import-speed comparison with batched SADD/HSET. [Seed provenance](raw/lavik-seedmaina6d-set-100m-k500-f128-20260930/).

![Set 100 MiB per key, 1 KiB entries: SISMEMBER and SADD/SREM QPS by connection count](charts/set-104857600-1024-ab.png)

**Fresh main `a6e93d3d` vs [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41`.** 500 × 100 MiB keys, 1024 B entries; 13 points per version, zero errors, every key validated before/after. SADD + SREM is **1.08–1.25×** main at matching connections. Curves use unprofiled eight-second runs; single-run differences are not established gains. Where sampled, perf diagnostics are retained separately.
[main raw](raw/lavik-maina6d-set-100m-k500-f1024-20260930/), [PR raw](raw/lavik-worktrim8079-set-100m-k500-f1024-20260930/).

RESTORE only prepares the dataset; after cleanup settles, both main and PR restart/recover before measurement. This is not an import-speed comparison with batched SADD/HSET. [Seed provenance](raw/lavik-seedmaina6d-set-100m-k500-f1024-20260930/).

### SMEMBERS

#### 1 MiB per key

![Set 1 MiB per key, 128 B entries: SMEMBERS QPS by connection count](charts/set-1048576-128-ab-full.png)

**80-connection long-run check:** three consecutive unprofiled 30-second repetitions per version: main **1,966, 1,967, 1,945 QPS**, PR **1,909, 1,922, 1,941 QPS**; mean ratio **0.982×**. Both recover the same dataset; all 50,000 key cardinalities are unchanged and runs have zero errors. The chart retains its original eight-second points. Versions run sequentially; three repetitions do not provide confidence intervals. [Results](set-1048576-128-full-read-repeats.json), [main raw](raw/lavik-fullcheck-maina6d-set-1m-k50000-f128-20260930/), [PR raw](raw/lavik-fullcheck-worktrim8079-set-1m-k50000-f128-20260930/), [script](repeat_grouped_full_reads.py).


![Set 1 MiB per key, 1 KiB entries: SMEMBERS QPS by connection count](charts/set-1048576-1024-ab-full.png)

#### 100 MiB per key

![Set 100 MiB per key, 128 B entries: SMEMBERS QPS by connection count](charts/set-104857600-128-ab-full.png)

**The 16-connection sustained workload did not pass the zero-error check.** In three planned 30-second repetitions per binary, main failed in repetition 3 and PR in repetition 2 with `OOM grouped operation scratch admission`; both server processes subsequently exited normally. Failed repetitions are excluded from throughput comparisons; the eight-second chart does not establish sustained stability. Admission partitions the limit across workers. This full read conservatively reserves about 1.2 GiB from page bytes, per-entry overhead and temporary copies, so concentrated requests can exceed one worker’s roughly 8.4 GiB share. After main’s failure, pending admission returned to zero and RSS was about 7.3 GiB. This is local reservation rejection, not an OS OOM or process crash; the admission model is unchanged between main and PR. [main raw](raw/lavik-fullcheck-maina6d-set-100m-k500-f128-20260930/), [PR raw](raw/lavik-fullcheck-worktrim8079-set-100m-k500-f128-20260930/).


![Set 100 MiB per key, 1 KiB entries: SMEMBERS QPS by connection count](charts/set-104857600-1024-ab-full.png)

### Batched import (SADD)

#### 1 MiB / 1024 B

![Set batched SADD import](charts/set-1048576-1024-k50000-fill.png)

Historical import measurement: Lavik main `ebe28dd5`, not a fresh run of `a6e93d3d` or PR #228.

All four use SADD, 16 entries per command, eight clients and pipeline 64. Main fill time: **517.9 seconds**. Persistence settings still differ.

#### 1 MiB / 128 B

![Set batched SADD import](charts/set-1048576-128-k50000-fill.png)

Historical import measurement: Lavik main `ebe28dd5`, not a fresh run of `a6e93d3d` or PR #228.

All four use SADD, 128 entries per command, eight clients and pipeline 64. Main fill time: **1724.2 seconds**. Persistence settings still differ.

The matching 100 MiB SADD import measurement is pending. The previous mixed RESTORE/SADD figure has been removed.

### RESTORE

Main `a6e93d3d`, eight concurrent RESTORE clients, 500 × 100 MiB keys per condition, every key validated. These standalone seed timings exclude subsequent cleanup waits and recovery; they are not compared with peer batched SADD/HSET import.

- 128 B: **291.1 seconds**. [Raw](raw/lavik-seedmaina6d-set-100m-k500-f128-20260930/set-104857600-128.fill.json).
- 1024 B: **136.8 seconds**. [Raw](raw/lavik-seedmaina6d-set-100m-k500-f1024-20260930/set-104857600-1024.fill.json).

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

## Test configuration

Bulk imports use a Python client on the server host; point-command QPS uses memtier on the separate client host. New import comparisons share pre-encoded operand bytes while preserving RESP commands, connection counts and pipelines. Kvrocks uses 16 workers.

- Server: 172.16.0.4, 16 vCPUs on AMD EPYC 9V74, CPUs 0–15, 100 Gb/s NIC.
  Redis 8.8.0 and Valkey 9.1.0 use 12 I/O
  threads, with RDB and AOF disabled. Lavik uses 12 workers, kernel TCP, and
  six dedicated SPDK NVMe devices. These are different durability settings.
- List and Sorted Set Lavik samples used early [PR #203](https://github.com/eloqdata/lavik/pull/203)
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

## List

This chapter retains the earlier complete four-product comparison. Lavik used `646a7b4e` and has not been retested on the latest main for these commands. The [raw CSV](results.csv) identifies the measured version.

### LINDEX / LSET

#### 64 KiB per key

![List 64 KiB per key, 128 B entries: LINDEX / LSET QPS by connection count](charts/list-65536-128.png)

![List 64 KiB per key, 1 KiB entries: LINDEX / LSET QPS by connection count](charts/list-65536-1024.png)

#### 1 MiB per key

![List 1 MiB per key, 128 B entries: LINDEX / LSET QPS by connection count](charts/list-1048576-128.png)

![List 1 MiB per key, 1 KiB entries: LINDEX / LSET QPS by connection count](charts/list-1048576-1024.png)

#### 100 MiB per key

![List 100 MiB per key, 128 B entries: LINDEX / LSET QPS by connection count](charts/list-104857600-128.png)

![List 100 MiB per key, 1 KiB entries: LINDEX / LSET QPS by connection count](charts/list-104857600-1024.png)

### LRANGE 0 -1

#### 64 KiB per key

![List 64 KiB per key, 128 B entries: LRANGE 0 -1 QPS by connection count](charts/list-65536-128-full.png)

![List 64 KiB per key, 1 KiB entries: LRANGE 0 -1 QPS by connection count](charts/list-65536-1024-full.png)

#### 1 MiB per key

![List 1 MiB per key, 128 B entries: LRANGE 0 -1 QPS by connection count](charts/list-1048576-128-full.png)

![List 1 MiB per key, 1 KiB entries: LRANGE 0 -1 QPS by connection count](charts/list-1048576-1024-full.png)

#### 100 MiB per key

![List 100 MiB per key, 128 B entries: LRANGE 0 -1 QPS by connection count](charts/list-104857600-128-full.png)

![List 100 MiB per key, 1 KiB entries: LRANGE 0 -1 QPS by connection count](charts/list-104857600-1024-full.png)

For 1 MiB `LINDEX`, Lavik peaked near 139k QPS with 128 B entries and 677k with 1 KiB entries. The entry-count difference matters, but the available profiling does not isolate one cause.

## Sorted Set

This chapter retains the earlier complete four-product comparison. Lavik used `646a7b4e` and has not been retested on the latest main for these commands. The [raw CSV](results.csv) identifies the measured version.

### ZSCORE / ZINCRBY

#### 64 KiB per key

![Sorted Set 64 KiB per key, 128 B entries: ZSCORE / ZINCRBY QPS by connection count](charts/zset-65536-128.png)

![Sorted Set 64 KiB per key, 1 KiB entries: ZSCORE / ZINCRBY QPS by connection count](charts/zset-65536-1024.png)

#### 1 MiB per key

![Sorted Set 1 MiB per key, 128 B entries: ZSCORE / ZINCRBY QPS by connection count](charts/zset-1048576-128.png)

![Sorted Set 1 MiB per key, 1 KiB entries: ZSCORE / ZINCRBY QPS by connection count](charts/zset-1048576-1024.png)

#### 100 MiB per key

![Sorted Set 100 MiB per key, 128 B entries: ZSCORE / ZINCRBY QPS by connection count](charts/zset-104857600-128.png)

![Sorted Set 100 MiB per key, 1 KiB entries: ZSCORE / ZINCRBY QPS by connection count](charts/zset-104857600-1024.png)

### ZRANGE WITHSCORES

#### 64 KiB per key

![Sorted Set 64 KiB per key, 128 B entries: ZRANGE WITHSCORES QPS by connection count](charts/zset-65536-128-full.png)

![Sorted Set 64 KiB per key, 1 KiB entries: ZRANGE WITHSCORES QPS by connection count](charts/zset-65536-1024-full.png)

#### 1 MiB per key

![Sorted Set 1 MiB per key, 128 B entries: ZRANGE WITHSCORES QPS by connection count](charts/zset-1048576-128-full.png)

![Sorted Set 1 MiB per key, 1 KiB entries: ZRANGE WITHSCORES QPS by connection count](charts/zset-1048576-1024-full.png)

#### 100 MiB per key

![Sorted Set 100 MiB per key, 128 B entries: ZRANGE WITHSCORES QPS by connection count](charts/zset-104857600-128-full.png)

![Sorted Set 100 MiB per key, 1 KiB entries: ZRANGE WITHSCORES QPS by connection count](charts/zset-104857600-1024-full.png)

## Measurement limits

Each point is one eight-second run, without a repeated-run confidence interval. Redis/Valkey have persistence disabled; Kvrocks has WAL disabled with an 80 GiB block cache; Lavik commits to SPDK. Write rates do not compare equivalent durability. Some 100 MiB full-read points completed fewer than 100 replies, so small differences are fragile.

The [HGETALL memory investigation](diagnostics/hgetall-oom-20260929/README.md) and [HSET write diagnostic](diagnostics/hset-20260929/README.md) retain the analysis. Earlier Hash/Set samples remain under `raw/` and are not presented as current-main values.

## Stream

Lavik uses merged main `9acd7b6f` with the Stream optimization. The 64 KiB and 1 MiB cases use 64 hot keys with 128 B or 1 KiB entries; the 100 MiB case uses eight keys with 1 KiB entries. The horizontal axis is connection count and the vertical axis is QPS; each figure contains one Lavik main curve.

Point reads and writes cover 80–5120 connections. Full reads use 16/80 for the smaller sizes and 1/4/16 for 100 MiB. Redis and Valkey have persistence disabled; Kvrocks has WAL disabled with an 80 GiB block cache; Lavik commits to SPDK. Write QPS reflects these configurations.

[All points](stream-latest.csv), the [plot script](plot_stream_latest.py), and Lavik [small](raw/lavik-main9acd-stream-small-20260929/) and [100 MiB](raw/lavik-main9acd-stream-100m-20260929/) raw runs retain the evidence. Each point is one eight-second run. Older optimization-stage samples remain under `raw/` and are not plotted.

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
