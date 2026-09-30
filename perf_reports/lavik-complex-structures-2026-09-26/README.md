# Complex Redis collection performance: Redis, Valkey, Lavik, and Kvrocks

[简体中文](README.zh-CN.md)

This report compares five Redis-compatible collection types on one server and one
remote memtier client. Each chart fixes the collection type, logical payload per
key, and payload bytes per entry. The horizontal axis is simultaneous
connections; the vertical axis is completed commands per second.

**PR #222 refresh:** rebased onto main `31a1e130`, adding per-leaf edits for SADD/SREM/HSET to reduce temporary strings and repeated hashing. Updated plots identify their measured revisions below; plots awaiting retesting retain their previous measured revisions.

## 2026-09-29 Hash and Set retest

Hash and Set use 50,000 keys at 1 MiB per key and 500 keys at 100 MiB per
key, with 128 B or 1 KiB entries. Every chart compares Redis, Valkey,
Kvrocks, and Lavik under the same workload. Updated plots state their main/PR versions below;
plots awaiting a refresh use `main` after merged
[PR #212](https://github.com/eloqdata/lavik/pull/212), at commit
`d1ce200e174adcb07820b5431c77b024350e85b6`. Its SPDK server binary
has SHA256 `bd3f942e3b7b0f46c23c716197c8cc4ec8ad963e92cede0d9fa2574ff52a74a9`.
**2026-09-30: refreshed 100 MiB/128 B plots compare main with unmerged PR #222.**
Measured main for the 100 MiB/128 B plots: `ebe28dd5a60b083c13826580c93623c6c5686b2d` (including #219 and #223).
PR: `817473b731a1d314080bff3fd2c5fc68d1246099`, pinning merged Bycorf `629dcb9ca737a073735ae4fc62b945a951d7ae69`.
Main and PR binary SHA256 respectively: `e615cacfa119e36f9f2f566e5848ad01ea3909ccb5f77a9237a75ba08a888ec3` and
`bb61cba8c4771bc2c50266a948f02379e2e40680b572a1310b06d9aa804446ea`.
Both versions reuse the same validated 500-key dataset for each type; all 13 points per version complete without errors.

- HSET: main **32.5–48.5k QPS**; PR **79.8–101.0k QPS**, **2.08–2.46×** main at matching connection counts. [Raw Hash main data](raw/lavik-mainebe-hash-100m-k500-f128-20260930/), [PR data](raw/lavik-pr222817-hash-100m-k500-f128-20260930/).
- SADD + SREM: main **62.3–91.3k QPS**; PR **141.5–168.1k QPS**, **1.84–2.27×** main at matching connection counts. [Raw Set main data](raw/lavik-mainebe-set-100m-k500-f128-20260930/), [PR data](raw/lavik-pr222817-set-100m-k500-f128-20260930/).

[PR #222](https://github.com/eloqdata/lavik/pull/222) includes compact physical indexes,
commit notifications, reuse of owner-verified settled transaction admission state, and positional
multi-field SADD/HSET indexes. The merged Bycorf optimization avoids ineffective FLUSH commands
on VWC=0 controllers; data-before-commit ordering is preserved.
These single-field/member commands do not exercise the multi-field index optimization.
Each point is one eight-second run. Kvrocks write throughput has not yet been reached.
All four 1 MiB PR #222 comparisons are complete, with versions and raw data below each plot. The 100 MiB/1 KiB plots do not yet include PR #222.

No data-page cache was added. Earlier main, PR #212, and 256-key raw runs remain in `raw/` but are
not plotted in this retest.

All four Hash/Set 1 MiB figures now use 50,000 keys. The Hash and Set
100 MiB figures at both entry sizes now use 500 keys.
Each new figure states its exact key count in the title.

Point reads and writes use 80/320/1280/2560/5120 connections. Full reads use
16/80 for 1 MiB and 1/4/16 for 100 MiB. Each point runs for eight seconds.
Redis and Valkey disable persistence; Kvrocks uses uncompressed RAID0, WAL
disabled, an 80 GiB block cache and blob cache. Lavik commits to six NVMe
devices via SPDK. These settings affect absolute write throughput. Every point
has one run and no confidence interval. The [raw runs](raw/) and
[plot script](plot_set_hash_high_keys.py) retain the evidence. Earlier
write-path and memory investigations remain available in the
[HSET diagnostic](diagnostics/hset-20260929/README.md) and
[HGETALL memory investigation](diagnostics/hgetall-oom-20260929/README.md).

[Same-block data/commit coalescing trial](diagnostics/hset-coalescing-20260929/README.md) passed correctness checks,
but HSET regressed in both the grid and a 20-second repeat. The change was reverted; main plots show the current NVMe variant.

[I/O counter diagnostics](diagnostics/hset-io-20260929/README.md) record HSET storage traffic, including background cleaning.

## Hash

Each point-read/write chart contains both commands. The 1 MiB and 100 MiB runs use 50,000 and 500 keys, respectively.

### HGET / HSET

#### 1 MiB per key

![Hash 1 MiB per key, 128 B entries: HGET and HSET QPS by connection count](charts/hash-1048576-128-ab.png)

**2026-09-30: main `ebe28dd5` vs PR #222 `817473b7`.** 50,000 keys, 128 B entries; both 12-point grids completed without errors. HSET reached **1.39–3.89×** main at matching connection counts.
[main raw](raw/lavik-mainebe-hash-1m-k50000-f128-hset-20260930/), [PR raw](raw/lavik-pr222817-hash-1m-k50000-f128-hset-20260930/).

![Hash 1 MiB per key, 1 KiB entries: HGET and HSET QPS by connection count](charts/hash-1048576-1024-ab.png)

**2026-09-30: main `ebe28dd5` vs PR #222 `817473b7`.** 50,000 keys, 1024 B entries; both 12-point grids completed without errors. HSET reached **0.57–3.89×** main at matching connection counts.
[main raw](raw/lavik-mainebe-hash-1m-k50000-f1024-hset-20260930/), [PR raw](raw/lavik-pr222817-hash-1m-k50000-f1024-hset-20260930/).

At 5,120 connections HSET regressed: PR **14,027 QPS**, main **24,766 QPS**. The other four connection levels improved. The drop has not been repeated and remains plotted unchanged.

#### 100 MiB per key

![Hash 100 MiB per key, 128 B entries: HGET and HSET QPS by connection count](charts/hash-104857600-128-ab.png)

In this run, PR HGET was about 26%, 19%, and 10% below main at 1280, 2560, and 5120 connections.
The HSET gain is not an across-command improvement. In the reversed-order 20-second repeat at 1280 connections, HGET reached main **395,420** and PR **402,036 QPS**;
the drop did not reproduce. HSET reached main **31,409** and PR **80,592 QPS**. Read performance shows
substantial run-to-run variation. The original eight-second grid remains plotted; individual points are not replaced by repeats.
[Raw main repeat](raw/lavik-repeatebe-hash-100m-k500-f128-c1280-20260930/),
[PR repeat](raw/lavik-repeat817-hash-100m-k500-f128-c1280-20260930/).

![Hash 100 MiB per key, 1 KiB entries: HGET and HSET QPS by connection count](charts/hash-104857600-1024-ab.png)

### HGETALL

#### 1 MiB per key

![Hash 1 MiB per key, 128 B entries: HGETALL QPS by connection count](charts/hash-1048576-128-ab-full.png)

![Hash 1 MiB per key, 1 KiB entries: HGETALL QPS by connection count](charts/hash-1048576-1024-ab-full.png)

#### 100 MiB per key

![Hash 100 MiB per key, 128 B entries: HGETALL QPS by connection count](charts/hash-104857600-128-ab-full.png)

![Hash 100 MiB per key, 1 KiB entries: HGETALL QPS by connection count](charts/hash-104857600-1024-ab-full.png)

### Batched import (HSET)

#### 1 MiB / 1024 B

![Hash batched HSET import](charts/hash-1048576-1024-k50000-fill.png)

All four use HSET, 16 entries per command, eight clients and pipeline 64. Main fill time: **500.3 seconds**. Persistence settings still differ.

#### 1 MiB / 128 B

![Hash batched HSET import](charts/hash-1048576-128-k50000-fill.png)

All four use HSET, 128 entries per command, eight clients and pipeline 64. Main fill time: **1306.3 seconds**. Persistence settings still differ.

### RESTORE

#### 100 MiB

Hash RESTORE was not retimed in this round. Batched HSET import results are recorded separately above.

## Set

Each point-read/write chart contains both commands. The 1 MiB and 100 MiB runs use 50,000 and 500 keys, respectively.

### SISMEMBER / SADD/SREM

#### 1 MiB per key

![Set 1 MiB per key, 128 B entries: SISMEMBER and SADD/SREM QPS by connection count](charts/set-1048576-128-ab.png)

**2026-09-30 leaf-write retest: main `31a1e130` vs PR #222 `d1f6ac34`.** 50,000 keys, 128 B entries, 12 points per version and zero errors. SADD + SREM reached **1.06–4.82×** main at matching connection counts. This seed uses 64 clients, 128 KiB batches and pipeline 8; both versions reuse the same dataset and validate every key. These plots replace the older PR measurements.
[main raw](raw/lavik-main31-set-1m-k50000-f128-leaf-c64-20260930/), [PR raw](raw/lavik-pr222d1f6ac34-set-1m-k50000-f128-leaf-c64-20260930/).

High-concurrency degradation remains: PR falls from **147,933 QPS** at 80 connections to **16,112 QPS** at 5,120 (main: **15,153**), still well below Kvrocks. This change does not resolve that drop; separate diagnostic sampling is in progress.

![Set 1 MiB per key, 1 KiB entries: SISMEMBER and SADD/SREM QPS by connection count](charts/set-1048576-1024-ab.png)

**2026-09-30: main `ebe28dd5` vs PR #222 `817473b7`.** 50,000 keys, 1024 B entries; both 12-point grids completed without errors. SADD + SREM reached **1.37–4.63×** main at matching connection counts.
[main raw](raw/lavik-mainebe-set-1m-k50000-f1024-sadd-20260930/), [PR raw](raw/lavik-pr222817-set-1m-k50000-f1024-sadd-20260930/).

#### 100 MiB per key

![Set 100 MiB per key, 128 B entries: SISMEMBER and SADD/SREM QPS by connection count](charts/set-104857600-128-ab.png)

![Set 100 MiB per key, 1 KiB entries: SISMEMBER and SADD/SREM QPS by connection count](charts/set-104857600-1024-ab.png)

### SMEMBERS

#### 1 MiB per key

![Set 1 MiB per key, 128 B entries: SMEMBERS QPS by connection count](charts/set-1048576-128-ab-full.png)

![Set 1 MiB per key, 1 KiB entries: SMEMBERS QPS by connection count](charts/set-1048576-1024-ab-full.png)

#### 100 MiB per key

![Set 100 MiB per key, 128 B entries: SMEMBERS QPS by connection count](charts/set-104857600-128-ab-full.png)

![Set 100 MiB per key, 1 KiB entries: SMEMBERS QPS by connection count](charts/set-104857600-1024-ab-full.png)

### Batched import (SADD)

#### 1 MiB / 1024 B

![Set batched SADD import](charts/set-1048576-1024-k50000-fill.png)

All four use SADD, 16 entries per command, eight clients and pipeline 64. Main fill time: **517.9 seconds**. Persistence settings still differ.

#### 1 MiB / 128 B

![Set batched SADD import](charts/set-1048576-128-k50000-fill.png)

All four use SADD, 128 entries per command, eight clients and pipeline 64. Main fill time: **1724.2 seconds**. Persistence settings still differ.

The matching 100 MiB SADD import measurement is pending. The previous mixed RESTORE/SADD figure has been removed.

### RESTORE

Main `ebe28dd5` imported 500 × 100 MiB keys with eight concurrent RESTORE clients
in **544.4 seconds**. This standalone measurement is not plotted against SADD fills.
[Raw measurement](raw/lavik-mainebe-set-100m-k500-f128-20260930/set-104857600-128.fill.json).

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
  --main-tag mainebe-set-1m-k50000-f128-sadd-20260930 \
  --main-commit ebe28dd5a60b083c13826580c93623c6c5686b2d \
  --main-sha256 e615cacfa119e36f9f2f566e5848ad01ea3909ccb5f77a9237a75ba08a888ec3 \
  --variant-tag pr222817-set-1m-k50000-f128-sadd-20260930 \
  --variant-label 'Lavik PR #222' \
  --variant-commit 817473b731a1d314080bff3fd2c5fc68d1246099 \
  --variant-sha256 bb61cba8c4771bc2c50266a948f02379e2e40680b572a1310b06d9aa804446ea
```
