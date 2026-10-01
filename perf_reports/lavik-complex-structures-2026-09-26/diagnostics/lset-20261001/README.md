# LSET metadata pointer-tree follow-up — 2026-10-01

Measured main: `f1268014` (includes merged #228 and #232). Candidate: PR #233 `0af92a14`. Exact commits and binary SHA256 values are in [the plot manifest](../../lset-large-published.json).

## Protocol

Each binary is seeded independently from identical logical data after clearing the six dedicated benchmark NVMe devices. This removes older benchmark history; it is a different physical-layout starting condition from the September 30 runs. Use the current paired curves to compare main and PR, rather than attributing cross-date changes exclusively to the pointer tree.

Payloads are 1 KiB. The workloads are 500 × 100 MiB and 50,000 × 1 MiB keys. Seed with 32 clients, 128 KiB RPUSH batches, pipeline 4. Clean LSET points use pipeline 1, 80/320/1280/2560/5120 connections and ten seconds each. Validate every key's cardinality before and after measurement. One sample per point; no confidence intervals.

Only after the entire clean grid, run independent 30-second diagnostics at 1,280 and 5,120 connections. Perf records 25 seconds of task-clock at 199 Hz with DWARF stacks. No compilation or tests overlap measurements. [Runner](bench-lset-large.py), [profiling helper](profile-lset-deep.py), and [counter summarizer](../lset-20260930/summarize-lset-io.py).

## 500 × 100 MiB results

Main: **7.20–7.36k QPS**; PR: **92.09–129.39k QPS**. The PR peaks at 320 connections; more connections do not improve throughput. All ten clean points passed, every key retained its expected length, and both servers exited normally. [Embedded chart](../../README.zh-CN.md#lset增加独立-key).

At 1,280 connections, PR's self CPU samples include directory Apply **2.36%**, the major allocator symbol **3.45%**, memmove **2.12%**, physical record lookup **3.33%**, and physical index update **1.93%**. These are sample shares, not time saved or allocation counts. The earlier 500-key diagnostic put Apply at 8.24%, but its different code base and storage history prevent treating that ratio as an isolated speedup. [Full symbols](../../raw/lavik-lset-radix-104857600-k500-f1024-20261001/diagnostic-c1280/self.txt).

The pointer-tree change removes the full outer pointer-table copy on point writes. Unit tests independently establish that modifying a 262,144-entry metadata view charges less than 16 KiB of new retained allocations, while retaining an unchanged prior snapshot. Allocation rejection during partial path detachment preserves values and can be retried.

The two diagnostic intervals average about **1.64 transactions per commit batch** and **2.20–2.21 write submissions per LSET**, including background work. Additional connections increase command mean latency from about 14 ms to 56 ms without throughput growth. These counters do not isolate dependency wait time or physical media latency. Do not sum the write and fdatasync byte counters as independent physical traffic. [Counter deltas](../../raw/lavik-lset-radix-104857600-k500-f1024-20261001/io-summary.json).

## 50,000 × 1 MiB results

Main: **85.98–101.53k QPS**; PR: **115.19–137.03k QPS**, or **1.27–1.35×** at matching connection counts. All ten clean points passed cardinality/error checks and both servers exited normally. This is the combined PR versus latest main, not an isolated test of the pointer-tree addition. [Symbols at 1,280 connections](../../raw/lavik-lset-radix-1048576-k50000-f1024-20261001/diagnostic-c1280/self.txt), [counter deltas](../../raw/lavik-lset-radix-1048576-k50000-f1024-20261001/io-summary.json).

## Matched peer curves

Both large-key charts now include Redis, Valkey, Kvrocks, Lavik main and PR #233 on the same axes. The three peers were separately measured with 50,000 × 1 MiB and 500 × 100 MiB keys, using the same 1 KiB entries, RPUSH seed batches, connection grid and ten-second clean LSET points. All 30 new peer points passed zero-error and all-key cardinality checks; every server exited normally. The existing 20 Lavik points are reused unchanged. Each point is one run, so the curves do not establish confidence intervals.

Redis/Valkey persistence is disabled. Kvrocks uses a six-device RAID0 XFS filesystem, no compression, WAL disabled and an 80 GiB block/blob cache. Lavik uses persistent SPDK storage. These configuration differences remain relevant to the comparison. Exact commits, binary hashes and raw-run directories are recorded in [the plot manifest](../../lset-large-published.json). [Peer runner](../../bench_lset_peers.py); [chart renderer](../../plot_lset_large_keys.py).

## Transaction dependency investigation

The current code waits for the previous grouped version's decision before staging a successor. Reads already support records in pending write buffers. Multiple in-memory versions are therefore possible; the foreground wait is not intrinsically required just because data is unflushed.

A safe pipelined implementation must preserve ancestor-before-successor durable commit ordering and propagate ancestor failure to every dependent published version. The existing commit queue batches decisions; when ancestor and successor are in one batch, simply waiting for the ancestor within that batch can deadlock, and allowing unrelated block flushes to race can reverse durability order. Local standalone writes are the narrowest initial case; EXEC/Lua and cross-worker decisions require separate ordering/lifetime checks. **This PR does not change transaction dependency waiting.**

## Validation

Release and fault-enabled Debug builds finished before tests. 80 metadata/index/planning/admission unit tests, ten Stream-record tests, 52 ordered/Stream/cross-worker E2E tests and two deterministic dependency-wakeup E2E tests passed. The first large Stream RDB run failed because the system temporary filesystem was full; moving old benchmark binaries to the workspace disk (preserving original paths with symlinks) allowed that single test to pass without a code change. Pre-commit passed for the modified C++ files.
