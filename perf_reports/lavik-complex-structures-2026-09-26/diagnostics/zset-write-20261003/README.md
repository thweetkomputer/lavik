# ZSet write diagnosis — October 3

Current-main baseline: `6111d0b1`, including #242. The optimization is [PR #246](https://github.com/eloqdata/lavik/pull/246). Each chart and raw run records its exact source revision and binary SHA256; data from an earlier candidate is never relabeled as a later binary.

## Excess work found

The independently sampled twelve-worker ZINCRBY run on main attributes 16.53% of recorded task-clock CPU to `OrderedGroupDirectory::Recover`, 10.92% to `Apply`, 7.68% to sorting unsigned ID pairs and 5.43% to pushing recovered group metadata. The structural fallback copies all directory records and rebuilds the ID map. A neighboring score move can leave two pages at 6+8 entries even though the same entries still fit as 7+7 in two 8 KiB pages.

PR #246 redistributes already-modified adjacent pages when feasible, preserving active IDs and links. Genuine growth, distant moves and oversized members retain the existing split/extent path. This shares the existing sparse directory publication path and introduces no persistent payload cache.

A second pass defers unchanged-neighbor payload reads until a real split/retirement changes their links. Admission still reserves the original selected set before loading; actual loads retain normal logical-view, GC and checksum validation. Tests inject a failure on an untouched neighbor and require success, then inject failure on a required changed-link neighbor and require atomic rollback and successful recovery.

## Measurement and evidence

The 100 MiB/key workload uses 8 keys; the 1 MiB/key workload uses 64 keys. Both use 1 KiB members to match the retained Redis/Valkey/Kvrocks curves. Each binary independently seeds fresh scratch media, validates every key before and after, and runs 80/320/1280/2560/5120 connections for point commands. Full ZRANGE uses 1/4/16 connections at 100 MiB and 16/80 at 1 MiB. Points last eight seconds and are one sweep without a repeated-run confidence interval.

- [Measurements and source proofs](../../zset-write-summary.json)
- [Main build](main-build.json), [PR build](pr-build.json), [test results](tests.json)
- [Main worker summary](main-perworker-summary.json), [candidate worker summary](pr-perworker-summary.json)
- [Main profile inputs](main/), [candidate profile inputs](pr/)

Profiles run separately after the clean sweep on recovered data. Each of the twelve workers is attached independently at 99 Hz task-clock with 16 KiB DWARF callchains for 25 seconds, while diagnostic memtier runs for 30 seconds at 80 connections. An inactive helper has no samples and contributes zero CPU. Percentages include polling, background and kernel work; they are not request-latency percentages, and scheduler boundaries can truncate caller context. Raw perf binaries and full callchains remain on the benchmark host; selected per-thread self reports, metadata and metrics are retained here. The currently retained first-pass candidate profile is `199b08e0`; the subsequent lazy-neighbor candidate is being measured separately before replacing it.

Other product curves are historical. Redis/Valkey do not persist, Kvrocks has WAL disabled with 80 GiB caches, and Lavik persists on six SPDK NVMe devices without payload caching. The NVMe media epoch differs from earlier peer measurements; the main and PR measurements here use the same current host. The retained #244 ZSet curve uses its actual earlier base `44761b91` and cannot establish a causal difference against the new main.
