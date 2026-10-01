# Shared transaction pipeline: CPU diagnosis

PR #235 `09871950`, Hash 500 × 100 MiB, 1 KiB fields, 1,280 connections. The clean grid completed before this separate 30-second diagnostic. It reuses that warmed PR layout and is not a throughput-comparison point. Profiles include worker polling and kernel networking; percentages are not a decomposition of request latency.

The task-clock profile has no lost samples. Selected self costs: worker RunOnce 10.47%, PollStorage 4.50%, mimalloc allocation/free symbols at least 6.22%, FindRecord 3.64%, directory Find 2.49%, logical-map SetNode 2.20%, physical-index UpdatePhysical 2.04%, and memmove 1.50%. Inclusive symbols overlap and must not be added together. These identify places to investigate; they do not establish that each allocation or index update is unnecessary.

The separate run completed 3,536,765 HSET commands. Within the accompanying metrics window, Lavik issued 5,318,141 storage writes (38,193,233,920 bytes) and 835,504 reads (30,849,493,504 bytes): approximately 1.50 writes and 0.24 reads per command. Metrics include background work in the window, and the final shutdown drain lies outside it. The fdatasync-labelled SPDK durability metrics overlap those writes and must not be counted as additional data writes.

The matched clean 100 MiB / 1 KiB HSET points improve by 10.3%–21.1%; peak QPS rises from 130,749 to 154,378. Kvrocks peaks at 344,461 on its documented WAL-disabled, 80 GiB cache configuration. The optimization has not closed that gap. No data cache was added.

[Clean main](../../raw/lavik-pipeline-main-hash-104857600-k500-f1024-20261001/) · [Clean PR](../../raw/lavik-pipeline-pr-hash-104857600-k500-f1024-20261001/) · [CPU and metrics evidence](../../raw/lavik-diagnostic-pipeline-pr235-hash-100m-f1024-20261001/). Raw perf binary remains in the benchmark workspace; the report includes self/inclusive/thread summaries and exact profiling arguments.


## Follow-up: complete worker callchains

[HSET work and sampling audit](hset-deep-diagnosis.md) identifies the original callchain-coverage limit, supplies a validated separate recording for all 12 workers, and distinguishes CPU candidates from unmeasured coroutine waits. Original self costs remain valid; original inclusive summaries do not represent complete user callchains.
