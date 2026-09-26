# Complex Redis collection performance: Redis, Valkey, and Lavik

[简体中文](README.zh-CN.md)

This report compares five Redis-compatible collection types on one server and one
remote memtier client. Each chart fixes the collection type, logical payload per
key, and payload bytes per entry. The horizontal axis is simultaneous
connections; the vertical axis is completed commands per second.

## Workloads

| Type | Point read | Write | Full read | Write behavior |
|---|---|---|---|---|
| Hash | HGET | HSET | HGETALL | Overwrite an existing field with a new value |
| Set | SISMEMBER | SADD + SREM | SMEMBERS | Toggle one member; the two commands have an equal ratio |
| List | LINDEX | LSET | LRANGE 0 -1 | Overwrite an existing element |
| Sorted Set | ZSCORE | ZINCRBY | ZRANGE WITHSCORES | Increment the score of an existing member |
| Stream | XRANGE exact ID | XADD MAXLEN ~ N | XRANGE - + | Append and approximately trim to the seeded length |

For positional reads and overwrites, memtier cycles through eight evenly spaced
entry positions per key. Each operation chooses one of 64 keys uniformly. Every
condition starts with 64 keys. Per-key logical payload is either 64 KiB or
1 MiB, and each field value, member, or element is exactly 128 B or 1 KiB.
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
- Lavik binary: source commit `646a7b4e` from [PR #203](https://github.com/eloqdata/lavik/pull/203),
  SHA256 `d98624e48eeac1aa942435f53e3c0f56882022f1f2184ae0bc415dfe5e31870a`;
  the upstream `main` HEAD was `9e31d073` when testing began.
- Client: 172.16.0.5, 16 vCPUs on AMD EPYC 9V45, memtier_benchmark 2.5.1,
  16 client threads, pipeline 1,
  random key selection, 80/320/1280/2560/5120 connections for point operations,
  16/80 connections for full reads, eight seconds per point.
- Each condition is filled from scratch using eight concurrent RESP clients.
  Reads run before writes, and writes preserve approximately the original
  collection length. The same 64 keys are used at all connection levels.
- Logical sizes describe payload bytes only, not Redis memory usage or Lavik
  disk consumption. These deliberately hot keys expose contention; they do
  not represent a large key population.
- QPS and latency come from memtier's JSON output. The script rejects
  connection errors, interrupted runs, and server error responses.

## Results

All 720 planned combinations completed. The source-of-truth measurements are
[results.csv](results.csv), the per-run JSON and command logs under [raw/](raw/),
and the plotting script [collect_plot.py](collect_plot.py). Each point is one
eight-second run; these are measured QPS, not confidence intervals.

For 1 MiB collections, the point-read peak usually occurs by 320 connections
for Lavik, whereas Redis often continues rising to 1280–2560. In the
128 B-element case Lavik reaches 502k HGET, 408k SISMEMBER, 139k LINDEX,
378k ZSCORE, and 44k one-entry XRANGE QPS. The List and Stream gaps are the
largest. At 5120 connections, queueing raises p99 sharply; for example,
Lavik's 1 MiB/128 B HGET falls to 316k QPS with 127 ms p99, versus its
502k-QPS peak with 1.9 ms p99 at 320 connections. Redis's Hash/Set/ZSet
peak points use roughly 15 of the client's 16 CPU cores, so their upper-end
curves also reflect client capacity.

Full reads tell a different story. At 80 connections with 1 MiB/128 B data,
Lavik's HGETALL (1,524 QPS), SMEMBERS (1,544), and ZRANGE WITHSCORES (1,488)
are at or above Redis, while LRANGE (949) and XRANGE - + (251) are lower.
With 1 KiB elements, Lavik and Redis both receive about 2.8 GiB/s on several
1 MiB full-read commands; those points are close to this setup's observed
response-bandwidth plateau. Small elements create many more reply items:
a 1 MiB Stream has 8,192 messages at 128 B but 1,024 at 1 KiB. Lavik's
full XRANGE rises from 251 to 1,526 QPS across those conditions.

Writes should be read with the durability settings in mind: Redis and Valkey
have RDB/AOF disabled, while Lavik commits to SPDK. Lavik's HSET, LSET,
ZINCRBY, and bounded XADD are mostly 5k–7k QPS at 80 connections. More
connections do little for their QPS and bring p99 into seconds. The Set
SADD/SREM row is a command-rate measurement and can include no-op replies.

### Peak point-read QPS; connection count in parentheses

| Type | Element | Command | Redis | Valkey | Lavik |
|---|---:|---|---:|---:|---:|
| Hash | 128 B | HGET | 1,001,626 (2560) | 837,629 (2560) | 502,460 (320) |
| Hash | 1 KiB | HGET | 968,662 (2560) | 931,407 (2560) | 645,839 (320) |
| Set | 128 B | SISMEMBER | 1,038,463 (2560) | 908,383 (1280) | 408,024 (320) |
| Set | 1 KiB | SISMEMBER | 815,565 (1280) | 837,087 (2560) | 501,939 (320) |
| List | 128 B | LINDEX | 753,041 (2560) | 682,135 (320) | 138,566 (80) |
| List | 1 KiB | LINDEX | 795,571 (1280) | 669,135 (1280) | 677,413 (320) |
| Sorted Set | 128 B | ZSCORE | 989,218 (2560) | 857,403 (2560) | 378,358 (320) |
| Sorted Set | 1 KiB | ZSCORE | 800,531 (1280) | 824,607 (1280) | 453,124 (320) |
| Stream | 128 B | XRANGE | 336,558 (2560) | 403,711 (320) | 43,545 (320) |
| Stream | 1 KiB | XRANGE | 349,674 (1280) | 436,291 (320) | 58,595 (320) |

### Write-command QPS at 80 connections

| Type | Element | Command | Redis | Valkey | Lavik |
|---|---:|---|---:|---:|---:|
| Hash | 128 B | HSET | 445,582 | 541,152 | 6,471 |
| Hash | 1 KiB | HSET | 438,749 | 532,240 | 6,436 |
| Set | 128 B | SADD + SREM | 449,673 | 560,382 | 13,287 |
| Set | 1 KiB | SADD + SREM | 436,456 | 537,995 | 13,137 |
| List | 128 B | LSET | 426,554 | 483,039 | 6,319 |
| List | 1 KiB | LSET | 430,357 | 466,391 | 6,575 |
| Sorted Set | 128 B | ZINCRBY | 402,062 | 531,647 | 6,102 |
| Sorted Set | 1 KiB | ZINCRBY | 407,553 | 490,732 | 6,445 |
| Stream | 128 B | XADD MAXLEN | 358,357 | 464,902 | 4,715 |
| Stream | 1 KiB | XADD MAXLEN | 323,761 | 393,696 | 5,576 |

### Full-read QPS at 80 connections

| Type | Element | Command | Redis | Valkey | Lavik |
|---|---:|---|---:|---:|---:|
| Hash | 128 B | HGETALL | 1,137 | 295 | 1,524 |
| Hash | 1 KiB | HGETALL | 2,771 | 1,235 | 2,807 |
| Set | 128 B | SMEMBERS | 999 | 464 | 1,544 |
| Set | 1 KiB | SMEMBERS | 2,847 | 1,252 | 2,846 |
| List | 128 B | LRANGE | 2,322 | 938 | 949 |
| List | 1 KiB | LRANGE | 2,849 | 1,073 | 1,380 |
| Sorted Set | 128 B | ZRANGE | 1,441 | 537 | 1,488 |
| Sorted Set | 1 KiB | ZRANGE | 2,823 | 1,035 | 2,824 |
| Stream | 128 B | XRANGE - + | 424 | 327 | 251 |
| Stream | 1 KiB | XRANGE - + | 1,346 | 885 | 1,526 |

### Focused backlog-limit experiment

The default 8 MiB per-worker Tx backlog was compared with 64 MiB for the
1 MiB Hash, 128 B field value, HSET. The larger limit eliminated measured
backlog waits but did not materially increase throughput. The default remains
8 MiB.

| Connections | 8 MiB QPS | 8 MiB backlog waits | 64 MiB QPS | 64 MiB backlog waits |
|---:|---:|---:|---:|---:|
| 80 | 6,471 | 304 | 6,281 | 0 |
| 320 | 6,446 | 582 | 6,425 | 0 |
| 2,560 | 7,018 | 3,899 | 7,128 | 0 |

The large List point-read gap is worth profiling separately. Current code
binary-searches the ordered page directory by rank, then
[loads and decodes the selected page](../../src/storage/engine/grouped_list.cpp)
into individual strings. It does not scan the entire List for LINDEX. The
8,192-entry 1 MiB/128 B List reaches only 139k peak LINDEX QPS, versus
677k for the 1,024-entry 1 MiB/1 KiB List. Per-page decoding and allocation
are plausible contributors, not a measured root cause.

### Charts

Each cell links to its point-read/write chart and its full-read chart.
Point charts use a logarithmic connection axis and a logarithmic QPS axis
for writes, because persistent Lavik writes are two orders of magnitude
below the memory-only peers. Full-read charts use linear axes.

| Type | 64 KiB / 128 B | 64 KiB / 1 KiB | 1 MiB / 128 B | 1 MiB / 1 KiB |
|---|---|---|---|---|
| Hash | [point](charts/hash-65536-128.png) · [full](charts/hash-65536-128-full.png) | [point](charts/hash-65536-1024.png) · [full](charts/hash-65536-1024-full.png) | [point](charts/hash-1048576-128.png) · [full](charts/hash-1048576-128-full.png) | [point](charts/hash-1048576-1024.png) · [full](charts/hash-1048576-1024-full.png) |
| Set | [point](charts/set-65536-128.png) · [full](charts/set-65536-128-full.png) | [point](charts/set-65536-1024.png) · [full](charts/set-65536-1024-full.png) | [point](charts/set-1048576-128.png) · [full](charts/set-1048576-128-full.png) | [point](charts/set-1048576-1024.png) · [full](charts/set-1048576-1024-full.png) |
| List | [point](charts/list-65536-128.png) · [full](charts/list-65536-128-full.png) | [point](charts/list-65536-1024.png) · [full](charts/list-65536-1024-full.png) | [point](charts/list-1048576-128.png) · [full](charts/list-1048576-128-full.png) | [point](charts/list-1048576-1024.png) · [full](charts/list-1048576-1024-full.png) |
| Sorted Set | [point](charts/zset-65536-128.png) · [full](charts/zset-65536-128-full.png) | [point](charts/zset-65536-1024.png) · [full](charts/zset-65536-1024-full.png) | [point](charts/zset-1048576-128.png) · [full](charts/zset-1048576-128-full.png) | [point](charts/zset-1048576-1024.png) · [full](charts/zset-1048576-1024-full.png) |
| Stream | [point](charts/stream-65536-128.png) · [full](charts/stream-65536-128-full.png) | [point](charts/stream-65536-1024.png) · [full](charts/stream-65536-1024-full.png) | [point](charts/stream-1048576-128.png) · [full](charts/stream-1048576-128-full.png) | [point](charts/stream-1048576-1024.png) · [full](charts/stream-1048576-1024-full.png) |

### Interpretation limits

- The 64 keys are intentionally hot and each point is one eight-second run;
  there are no repeat-based uncertainty bounds or cold-cache measurements.
- Logical sizes count element payload only. Field names, scores, stream metadata,
  protocol framing, allocator overhead, and Lavik page/index bytes are extra.
- Set SADD/SREM uses equal command ratios on independently random keys and may
  return no-op results. Stream XADD uses approximate MAXLEN, so its physical
  write work and retained message count can vary slightly.
- Redis/Valkey persistence is disabled, unlike Lavik. Write QPS is a
  configuration comparison, not equal-durability throughput.
- The 1 MiB/128 B Stream seed requires 524,288 XADD commands for 64 keys;
  filling is outside the memtier timing. See each `*.fill.json` for elapsed time.
  Dataset order was fixed rather than randomized.

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
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python collect_plot.py
```

The SPDK preparation helper verifies the six dedicated controller serial
numbers and PCI addresses before discarding their scratch datasets. Do not
prepare devices that contain data to keep. Server commands, binary hashes,
memtier invocations, fill timings, validation checks, and per-run JSON are
committed under `raw/`. Console output is retained locally and omitted from
the branch because the JSON contains the measured data.
