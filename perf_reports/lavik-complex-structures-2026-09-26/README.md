# Complex Redis collection performance: Redis, Valkey, Lavik, and Kvrocks

[简体中文](README.zh-CN.md)

This report compares five Redis-compatible collection types on one server and one
remote memtier client. Each chart fixes the collection type, logical payload per
key, and payload bytes per entry. The horizontal axis is simultaneous
connections; the vertical axis is completed commands per second.

## 2026-09-29 grouped Hash and Set retest

Only `main` after merged [PR #212](https://github.com/eloqdata/lavik/pull/212)
is plotted for Lavik. The 1 MiB run uses commit `bde3120e` and a SPDK
RelWithDebInfo binary with SHA256
`1acecaa40948d473caedce591d1a775d3d910b260a50b38a68f25bf946a4546e`.
The three peers have completed 10 MiB and 100 MiB runs; the merged main has
not yet been measured at those sizes. Those charts currently show peers only,
until Lavik is measured under the same workload. Earlier main and PR #212 raw
runs remain in `raw/` but are not represented as current main results.

The 1 MiB and 10 MiB runs use 64 keys; 100 MiB uses eight. Entry sizes are
128 B and 1 KiB. Point commands use 80/320/1280/2560/5120 connections;
full reads use 16/80 for 1 MiB, 4/16 for 10 MiB, and 1/4/16 for 100 MiB.
Each point runs for eight seconds. Redis and Valkey disable persistence;
Kvrocks uses uncompressed RAID0, WAL disabled, an 80 GiB block cache and
blob cache. Lavik commits to six NVMe devices via SPDK. These settings affect
absolute write throughput.

The 1 MiB/64-key HGET and SISMEMBER points use merged main. Lavik's
larger-key point and full reads are pending. No data-page cache was added.

At 1 MiB/64 keys, merged main HSET is about 9.4–9.6k QPS and mixed
SADD/SREM about 18.8–20.1k QPS; the latter includes no-op replies.
The next section compares a larger hot-key set.

### Write retest with 256 hot keys

All four products were seeded with 256 keys of 1 MiB each, with 128 B and
1 KiB entries. Commands, eight-second measurements, connection counts, and
persistence settings match the 64-key runs above. Only the latest main
(`9acd7b6f`) is plotted for Lavik. With 128 B entries, increasing hot keys
from 64 to 256 raised Lavik's
320-connection HSET from about 9.4k to 19.2k QPS and SADD/SREM from 18.8k
to 36.1k. Both remain far below Kvrocks. At 80 connections, Lavik HSET
reached 29.7k QPS, then fell to 19.2k at 320 connections. The charts use
logarithmic throughput axes to retain the full four-product gap.

The [complete points](write-256.csv), [plot script](plot_write_256.py), and
raw [Redis](raw/redis-1m-k256-write-20260929/),
[Valkey](raw/valkey-1m-k256-write-20260929/),
[Kvrocks](raw/kvrocks-1m-k256-write-20260929/), and
[Lavik](raw/lavik-main9acd-1m-k256-20260929/) runs retain the evidence.

Earlier write-path and HGETALL memory investigations remain available in the [HSET diagnostic](diagnostics/hset-20260929/README.md) and [HGETALL memory investigation](diagnostics/hgetall-oom-20260929/README.md); they are not current-main measurements. Each point has one run, without a confidence interval. The [current CSV](set-hash-ab.csv), [raw runs](raw/), and [plot script](plot_set_hash_ab.py) retain the evidence.

## Hash

Each point-read/write chart contains both commands. The 1 MiB Lavik line is from merged main; the 10 MiB and 100 MiB merged-main points are pending.

### HGET / HSET

#### 1 MiB per key

![Hash 1 MiB per key, 128 B entries: HGET and HSET QPS by connection count](charts/hash-1048576-128-ab.png)

![Hash 1 MiB per key, 1 KiB entries: HGET and HSET QPS by connection count](charts/hash-1048576-1024-ab.png)

#### 10 MiB per key

![Hash 10 MiB per key, 128 B entries: HGET and HSET QPS by connection count](charts/hash-10485760-128-ab.png)

![Hash 10 MiB per key, 1 KiB entries: HGET and HSET QPS by connection count](charts/hash-10485760-1024-ab.png)

#### 100 MiB per key

![Hash 100 MiB per key, 128 B entries: HGET and HSET QPS by connection count](charts/hash-104857600-128-ab.png)

![Hash 100 MiB per key, 1 KiB entries: HGET and HSET QPS by connection count](charts/hash-104857600-1024-ab.png)

### HSET / 256 hot keys

1 MiB per key with 128 B and 1 KiB entries; Lavik is latest main `9acd7b6f`.

![Hash HSET，256 key，四款数据库](charts/hash-hset-1048576-k256.png)

### HGETALL

#### 1 MiB per key

![Hash 1 MiB per key, 128 B entries: HGETALL QPS by connection count](charts/hash-1048576-128-ab-full.png)

![Hash 1 MiB per key, 1 KiB entries: HGETALL QPS by connection count](charts/hash-1048576-1024-ab-full.png)

#### 10 MiB per key

![Hash 10 MiB per key, 128 B entries: HGETALL QPS by connection count](charts/hash-10485760-128-ab-full.png)

![Hash 10 MiB per key, 1 KiB entries: HGETALL QPS by connection count](charts/hash-10485760-1024-ab-full.png)

#### 100 MiB per key

![Hash 100 MiB per key, 128 B entries: HGETALL QPS by connection count](charts/hash-104857600-128-ab-full.png)

![Hash 100 MiB per key, 1 KiB entries: HGETALL QPS by connection count](charts/hash-104857600-1024-ab-full.png)

## Set

Each point-read/write chart contains both commands. The 1 MiB Lavik line is from merged main; the 10 MiB and 100 MiB merged-main points are pending.

### SISMEMBER / SADD/SREM

#### 1 MiB per key

![Set 1 MiB per key, 128 B entries: SISMEMBER and SADD/SREM QPS by connection count](charts/set-1048576-128-ab.png)

![Set 1 MiB per key, 1 KiB entries: SISMEMBER and SADD/SREM QPS by connection count](charts/set-1048576-1024-ab.png)

#### 10 MiB per key

![Set 10 MiB per key, 128 B entries: SISMEMBER and SADD/SREM QPS by connection count](charts/set-10485760-128-ab.png)

![Set 10 MiB per key, 1 KiB entries: SISMEMBER and SADD/SREM QPS by connection count](charts/set-10485760-1024-ab.png)

#### 100 MiB per key

![Set 100 MiB per key, 128 B entries: SISMEMBER and SADD/SREM QPS by connection count](charts/set-104857600-128-ab.png)

![Set 100 MiB per key, 1 KiB entries: SISMEMBER and SADD/SREM QPS by connection count](charts/set-104857600-1024-ab.png)

### SADD/SREM / 256 hot keys

1 MiB per key with 128 B and 1 KiB entries; Lavik is latest main `9acd7b6f`.

![Set SADD/SREM，256 key，四款数据库](charts/set-sadd_srem-1048576-k256.png)

### SMEMBERS

#### 1 MiB per key

![Set 1 MiB per key, 128 B entries: SMEMBERS QPS by connection count](charts/set-1048576-128-ab-full.png)

![Set 1 MiB per key, 1 KiB entries: SMEMBERS QPS by connection count](charts/set-1048576-1024-ab-full.png)

#### 10 MiB per key

![Set 10 MiB per key, 128 B entries: SMEMBERS QPS by connection count](charts/set-10485760-128-ab-full.png)

![Set 10 MiB per key, 1 KiB entries: SMEMBERS QPS by connection count](charts/set-10485760-1024-ab-full.png)

#### 100 MiB per key

![Set 100 MiB per key, 128 B entries: SMEMBERS QPS by connection count](charts/set-104857600-128-ab-full.png)

![Set 100 MiB per key, 1 KiB entries: SMEMBERS QPS by connection count](charts/set-104857600-1024-ab-full.png)

## Workloads

For positional reads and overwrites, memtier cycles through eight evenly spaced
entry positions per key. The 64 KiB, 1 MiB, and new 10 MiB conditions use
64 keys; the 100 MiB extension uses eight keys. Each operation chooses a key uniformly
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
- Kvrocks uses the same configuration at all three sizes. Its 64 KiB and
  1 MiB points were measured on 2026-09-27 in a later pass with identical
  workload settings. The saved configuration enables an 80 GiB RocksDB block
  cache and blob caching; its hot-read QPS therefore includes a large memory
  cache, unlike Lavik's data-page path.
- Client: 172.16.0.5, 16 vCPUs on AMD EPYC 9V45, memtier_benchmark 2.5.1,
  pipeline 1, random key selection, and eight seconds per point. Point
  operations use 16 client threads and 80/320/1280/2560/5120 connections.
  Full reads use 16/80 connections for 64 KiB and 1 MiB, and 1/4/16 for
  100 MiB; the client thread count is capped by the connection count.
- Each condition is filled from scratch using eight concurrent RESP clients.
  Reads run before writes, and writes preserve approximately the original
  collection length. The same keys are used at all connection levels within
  a condition. The 100 MiB fill batches 64 commands per client connection.
- Logical sizes describe payload bytes only, not Redis memory usage or Lavik
  disk consumption. These deliberately hot keys expose contention; they do
  not represent a large key population.
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

Lavik uses merged main `9acd7b6f` with the Stream optimization. Each of 64 hot keys holds 64 KiB or 1 MiB with 128 B or 1 KiB entries. The merged-main 100 MiB retest is pending. The horizontal axis is connection count and the vertical axis is QPS; each figure contains one Lavik main curve.

Point reads and writes cover 80–5120 connections; full reads cover 16/80 connections. Redis and Valkey have persistence disabled; Kvrocks has WAL disabled with an 80 GiB block cache; Lavik commits to SPDK. Write QPS reflects these configurations.

[All points](stream-latest.csv), the [plot script](plot_stream_latest.py), and [Lavik raw run](raw/lavik-main9acd-stream-small-20260929/) retain the evidence. Each point is one eight-second run. Older optimization-stage samples remain under `raw/` and are not plotted.

### Exact-ID `XRANGE`

#### 64 KiB per key

![64 KiB per key, 128 B entries: Exact-ID `XRANGE` QPS by connection count](charts/stream-65536-128-xrange-latest.png)

![64 KiB per key, 1 KiB entries: Exact-ID `XRANGE` QPS by connection count](charts/stream-65536-1024-xrange-latest.png)

#### 1 MiB per key

![1 MiB per key, 128 B entries: Exact-ID `XRANGE` QPS by connection count](charts/stream-1048576-128-xrange-latest.png)

![1 MiB per key, 1 KiB entries: Exact-ID `XRANGE` QPS by connection count](charts/stream-1048576-1024-xrange-latest.png)

### `XADD MAXLEN`

#### 64 KiB per key

![64 KiB per key, 128 B entries: `XADD MAXLEN` QPS by connection count](charts/stream-65536-128-xadd_maxlen-latest.png)

![64 KiB per key, 1 KiB entries: `XADD MAXLEN` QPS by connection count](charts/stream-65536-1024-xadd_maxlen-latest.png)

#### 1 MiB per key

![1 MiB per key, 128 B entries: `XADD MAXLEN` QPS by connection count](charts/stream-1048576-128-xadd_maxlen-latest.png)

![1 MiB per key, 1 KiB entries: `XADD MAXLEN` QPS by connection count](charts/stream-1048576-1024-xadd_maxlen-latest.png)

### Full `XRANGE - +`

#### 64 KiB per key

![64 KiB per key, 128 B entries: Full `XRANGE - +` QPS by connection count](charts/stream-65536-128-xrange_full-latest.png)

![64 KiB per key, 1 KiB entries: Full `XRANGE - +` QPS by connection count](charts/stream-65536-1024-xrange_full-latest.png)

#### 1 MiB per key

![1 MiB per key, 128 B entries: Full `XRANGE - +` QPS by connection count](charts/stream-1048576-128-xrange_full-latest.png)

![1 MiB per key, 1 KiB entries: Full `XRANGE - +` QPS by connection count](charts/stream-1048576-1024-xrange_full-latest.png)

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

For the September 29 follow-up, build the two Lavik commits identified at the
top of this report and run `run.py lavik` for each binary with `--types hash,set`,
`--fields 128,1024`, `--mode both`, `--levels 80,320,1280,2560,5120`, and
`--seconds 8`. Use `--sizes 1048576 --keys 64 --full-levels 16,80` for the
1 MiB runs. For 100 MiB use `--sizes 104857600 --keys 8`,
`--seed-pipeline 64 --full-levels 1,4,16`, and `--continue-on-error`.
The four run tags are
`main-20260929`, `opt-20260929`, and their `-100m` variants. Pass the exact
source revision with `--source-commit`; the per-run provenance JSON records
both that revision and the binary SHA256. After restoring SPDK, regenerate the
new figures and CSV with `.venv/bin/python plot_set_hash_ab.py`.
