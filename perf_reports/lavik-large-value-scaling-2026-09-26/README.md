# Large String connection scaling, 2026-09-26

The five charts show memtier QPS against **connection count**. Each chart has a
GET panel and a SET panel. Points at 2560 and 5120 connections were added where
the earlier sweep left open a possible scaling gain; blank series segments mean
that product was not measured at that level. [Exact QPS, p99 and run source are
in the CSV](results.csv).

| Value | Chart | Peak GET QPS (Redis / Valkey / Lavik) | Peak SET QPS (Redis / Valkey / Lavik) |
| --- | --- | ---: | ---: |
| 2 KiB | [2K](charts/2K.svg) | 817k / 771k / 715k | 716k / 597k / 566k |
| 4 KiB | [4K](charts/4K.svg) | 697k / 633k / 665k | 651k / 528k / 486k |
| 8 KiB | [8K](charts/8K.svg) | 364k / 364k / 364k | 377k / 383k / 400k |
| 32 KiB | [32K](charts/32K.svg) | 91.2k / 91.2k / 91.2k | 93.7k / 93.6k / 11.0k |
| 128 KiB | [128K](charts/128K.svg) | 22.8k / 22.8k / 22.8k | 23.4k / 23.4k / 9.2k |

These are **independent peaks** across the connections tested for each product,
not QPS at a common connection level. The charts and CSV retain each actual
point. Read throughput at 32 and 128 KiB clustered around 2.7 GB/s of observed
server NIC transmit traffic. Raising connections beyond 1280 did not raise
128 KiB Lavik GET throughput; 2 and 4 KiB Lavik throughput declined at 2560
and 5120. The extra connections established that those curves had passed their
peak rather than being client concurrency limited.

At 128 KiB and 1280 connections, the bounded parallel String read experiment
measured 22.4k GET QPS and 243 ms p99, versus 19.6k and 725 ms for the serial
read. At 80–640 connections both versions were about 22.6–22.8k QPS. At 32 KiB
the parallel version did not materially change GET QPS. The serial and parallel
curves are both shown in those two charts. Each point is one 15-second run, so
the high-connection tail-latency difference needs replication before treating
it as a stable gain.

The 32 and 128 KiB SET results expose a separate gap. Redis and Valkey were run
without persistence, while Lavik committed to six SPDK NVMe drives, so the SET
numbers include different durability work. The first unmodified Lavik run could
not finish the 32 KiB fill: outstanding transaction decisions consumed all
segmented-String append capacity. The attached code bounds those decision
leases before starting another standalone String transaction, and the subsequent
large-value fills and sweeps completed without response errors.

## Method

- Server: `172.16.0.4`, pinned to CPUs 0–15. Redis 8.8.0 and Valkey 9.1.0
  used 12 IO threads, no snapshots or AOF. Lavik used 12 pinned workers, SPDK
  on six dedicated NVMe devices, 20 µs busy polling and paused defragmentation.
  Lavik source began at upstream `a23043be`; the report branch contains its
  admission and parallel-read changes. The memtier client ran separately on
  `172.16.0.5`, pinned to CPUs 0–15.
- Each size rebuilt about 8 GiB of logical String values, rounded to a multiple
  of 80 keys: 4,194,240 / 2,097,120 / 1,048,560 / 262,080 / 65,520 keys
  respectively. The harness checked `DBSIZE` and three `STRLEN` samples after
  each fill, and rejected GET misses, server responses with errors and client
  connection errors.
- Each measured point used 16 memtier threads, pipeline depth 1, random keys,
  15 seconds, and either GET-only or SET-only traffic. Standard levels were
  80, 320, 640 and 1280 connections. The extra 2560/5120 levels were measured
  for the small sizes and for Lavik 128 KiB as recorded in the CSV.
- The first Valkey 128 KiB 15-second sweep reported an unrepeatable 74k GET
  QPS point at 640 connections despite no reported misses/errors. Both a
  30-second repeat and a second 15-second sweep measured about 22k; server NIC
  transmit counters corroborated the latter. The charts use the second
  15-second sweep (`valkey-verified128`) for all 128 KiB Valkey points and omit
  the anomalous first sweep.
- The `Lavik` series combines `lavik-baseline` for 2/4/8 KiB standard levels,
  `lavik-parallel` for 32/128 KiB standard levels, and `lavik-high` for extra
  levels. The small-value read path was unchanged by the String parallel-read
  patch. `Lavik serial` is the 32/128 KiB run with the admission fix but before
  parallel reads. The final extra-connection run also included the admission
  recheck under the store lock.

The [harness](run.py), [Lavik runner](run_lavik.py) and [SPDK host setup](spdk_host.py)
are specific to this two-host lab. The host setup checks an exact six-controller
serial/BDF allowlist before wiping or binding any scratch device. Raw logs stay
local; the committed [CSV](results.csv) has every plotted value and source tag.
Regenerate the charts from the CSV with `python3 plot.py`.

## Charts

### 2 KiB

![2 KiB GET and SET QPS by connections](charts/2K.svg)

### 4 KiB

![4 KiB GET and SET QPS by connections](charts/4K.svg)

### 8 KiB

![8 KiB GET and SET QPS by connections](charts/8K.svg)

### 32 KiB

![32 KiB GET and SET QPS by connections](charts/32K.svg)

### 128 KiB

![128 KiB GET and SET QPS by connections](charts/128K.svg)
