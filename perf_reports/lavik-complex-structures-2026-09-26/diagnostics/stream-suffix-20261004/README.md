# Stream suffix directory reuse — October 4

Baseline: `a565d603`; candidate: `7586dc6f`. See [exact binaries and hashes](versions.json), [CMake configuration](candidate-CMakeCache.txt) and the source PR linked from the report. The candidate shares validated prefix metadata across small suffix insertions; it changes neither durable formats nor payload caching.

## Clean throughput and latency

8 independently seeded 100 MiB Streams, 1 KiB entries, pipeline 1, 12 workers, six NVMe SPDK devices and a separate client. Each point runs for eight seconds without concurrent builds, tests or perf. Full raw grids and p99 values are linked from the report.

| Connections | Main XADD QPS | Candidate QPS | Change | Main p99 ms | Candidate p99 ms |
| --- | --- | --- | --- | --- | --- |
| 80 | 9209 | 14098 | +53.1% | 32.6 | 22.9 |
| 320 | 10501 | 14354 | +36.7% | 124.4 | 86.0 |
| 1280 | 10151 | 15007 | +47.8% | 491.5 | 405.5 |
| 2560 | 12354 | 14898 | +20.6% | 745.5 | 1163.3 |
| 5120 | 10633 | 13596 | +27.9% | 1081.3 | 1925.1 |

The 2560-connection initial point improves QPS but worsens p99. A single sweep is insufficient to claim a tail-latency improvement. Point reads vary from -0.5% to +4.0%. The separate 64-key × 1 MiB write sweep varies from -2.0% to +2.2%, showing no clear small-directory benefit. See [100 MiB comparison](comparison-stream-104857600-1024-k8.json) and [1 MiB comparison](comparison-stream-1048576-1024-k64.json).

## Independent paired repetitions

Three independent seed pairs ordered A/B, B/A, A/B; 15-second XADD MAXLEN points at 80/320/2560 connections; same baseline workload and settings; no concurrent build, tests or perf.

| Connections | Median main QPS | Median candidate QPS | Median paired change | Paired change range | Median main p99 ms | Median candidate p99 ms |
| --- | --- | --- | --- | --- | --- | --- |
| 80 | 11077 | 16003 | +46.8% | +37.0% to +47.6% | 28.0 | 18.7 |
| 320 | 11204 | 15943 | +42.3% | +41.5% to +46.6% | 111.6 | 84.0 |
| 2560 | 10710 | 16872 | +56.1% | +49.4% to +57.5% | 983.0 | 536.6 |

[All paired observations and raw tags](stream-write-repeats.json) · [Summary](stream-write-repeat-summary.json) · [Runner](repeat-stream.py). Three pairs are not a confidence interval; results apply to this host and workload.

## CPU evidence

[Profile comparison](profile-comparison.json) · [Candidate worker summary](suffix-workers.json) · [Recorder, threads, metrics and self reports](suffix-profile/). Profiles attach independently to all 12 serving workers at 99 Hz for 25 seconds with 16 KiB DWARF stacks. An extra inactive helper has no samples. The diagnostic is separate from plotted throughput.

Apply self CPU falls from 11.36% to 1.17%; metadata chunk construction from 5.19% to 0.55%; temporary metadata-vector copying from 3.25% to 0.34%. Polling, background and kernel work are included in the denominator. These shares are not per-request latency fractions.

The initial pure-tail attempt (`29913acf`) missed insertion before trailing Stream metadata and showed only -3.6% to +7.0% QPS variation. Its [profile](initial-tail-workers.json) and [recorder/self reports](initial-profile/) are retained as an unsuccessful trial; it is not plotted as an optimization result.

## Correctness

With fault injection enabled: [160 unit tests](suffix-unit.json), [103 passed ordered/Stream/ZSet end-to-end tests and one existing opt-in RDB skip](suffix-ordered.json), and [27 recovery tests](suffix-recovery.json). Differential tests verify ranks, identity shifts, byte totals, old pinned views, malformed graphs and admission failure across chunk/Fenwick boundaries. Performance binaries disable fault injection.

## Remaining gap

The candidate reaches about 11–12% of historical Kvrocks XADD throughput and roughly 3–4% of the faster historical Redis/Valkey result at matching connection counts. It has not reached parity. Redis/Valkey persistence is off; Kvrocks WAL is off with 80 GiB block/blob cache; Lavik remains durable on six SPDK NVMe devices without a field/page payload cache. Peers were not rerun, and the configurations do not establish equivalent-durability rankings.
