# List reply capacity: incremental measurements

This is the second measured stage of [PR #267](https://github.com/eloqdata/lavik/pull/267). The previous production revision is `13041873` (bounded page reads); this candidate is `ff9e36550d3c899011cb07e037f4521273e667ae` (adds reply preallocation). Later branch heads also include the independently submitted recovery repair in [PR #268](https://github.com/eloqdata/lavik/pull/268); these performance measurements remain pinned to `ff9e3655` and predate that repair. [First-stage results](../list-read-window-20261004/README.md) · [binary/build proof](list-reply-versions.json).

## Change and scope

List array replies compute their exact RESP wire size, including an existing outer-array prefix, before appending. A single capacity reservation avoids copying the growing prefix repeatedly. Empty and singleton arrays retain their existing append path; an unrepresentable estimate falls back to normal append behavior without integer wraparound. Large buffers are still released on reset. Storage reads, mutation rules, memory admission, durable format and wire bytes are unchanged by this incremental step.

## Three paired repetitions against the previous candidate

Three independent seed pairs ordered A/B, B/A, A/B; 15-second LRANGE points at 1/4/16 connections and LSET at 2560; previous is PR #267 at 13041873, isolating reply reservation; same baseline workload and settings; no concurrent build, tests or perf.

These comparisons isolate reply reservation; the previous column is **not main**. Three paired repetitions are not a confidence interval. [All observations](list-reply-repeats.json) · [summary and every p99](list-reply-repeat-summary.json).

| Command | Connections | Previous median QPS | Candidate median QPS | Median paired change | Paired change range | Previous / candidate median p99 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LRANGE | 1 | 3.36 | 3.46 | +3.0% | +2.1% to +6.8% | 327.679 / 296.959 |
| LRANGE | 4 | 9.72 | 10.77 | +3.9% | +2.2% to +12.7% | 782.335 / 618.495 |
| LRANGE | 16 | 18.74 | 20.89 | +11.5% | +11.4% to +12.0% | 1843.199 / 1474.559 |
| LSET | 2560 | 46,553.62 | 47,675.50 | +2.8% | +2.4% to +3.9% | 270.335 / 232.447 |

All nine LRANGE pairs improve QPS and lower p99. The LSET control improves QPS in all three pairs, with one worse p99; it does not reproduce the large single-grid throughput drop, but does not establish an improvement in an unchanged command path.

The LSET control was included because the single-grid 2560-connection point fell by 13.8% and its p99 increased from 201.7 to 389.1 ms. LSET does not call the changed array-reply helper. The repetitions preserve both favorable and unfavorable outcomes rather than deleting that original observation.

## Single clean sweeps

[100 MiB / 128 B incremental comparison](list-reply-comparison-104857600-128-k8.json) · [64 KiB / 128 B](list-reply-comparison-65536-128-k64.json) · [64 KiB / 1024 B](list-reply-comparison-65536-1024-k64.json). Each candidate sweep validates cardinalities and exits cleanly with no command errors. Single sweeps have no statistical confidence intervals.

In the large sweep, LRANGE QPS changes by +3.6%/+1.3%/+14.6% at 1/4/16 connections relative to `13041873`. Its p99 improves at one connection but is 12.4% and 7.6% higher at 4 and 16 connections. Small LRANGE throughput is essentially unchanged. Several untargeted point-read/write observations are lower, including −8.2% small LINDEX at 5120 connections; the complete data remain published. These results do not establish a universal improvement.

## Total result against pinned main and historical peers

[Main comparison, 100 MiB / 128 B](comparison-list-104857600-128-k8.json) · [64 KiB / 128 B](comparison-list-65536-128-k64.json) · [64 KiB / 1024 B](comparison-list-65536-1024-k64.json). The current figures use these complete clean grids.

The combined candidate reaches 3.43/9.88/20.70 QPS for the 100 MiB / 128 B / 8-key LRANGE workload at 1/4/16 connections. Pinned main recorded 0.90/3.43 QPS and failed the 16-connection point with OOM. There is no valid QPS ratio for that failed point. Historical Redis gives 5.26/14.10/16.47 QPS, Valkey 4.49/8.09/8.37 and Kvrocks 2.91/12.03/21.86. The 16-connection candidate point is 5.3% below the fastest peer; the lower-concurrency points still miss the provisional 20% target. This does not establish overall parity.

Peers were not rerun. Redis/Valkey disable persistence; Kvrocks disables WAL and uses an 80 GiB cache; Lavik stays durable on six SPDK NVMe devices without field/page payload caching. These are matched commands/data, not equivalent persistence configurations.

## Separate perf evidence

[Profile comparison](list-reply-profile-comparison.json) · [candidate samples and counters](range-profile/) · [recorder](../main-a565d603-20261004/profile-ordered-allworkers.py).

| Version | Self memmove | Self memmove under List array reply | Physical reads / LRANGE | Physical writes / LRANGE |
| --- | ---: | ---: | ---: | ---: |
| previous | 12.02% | 9.36% | 14125 | 0 |
| candidate | 8.12% | 5.30% | 14125 | 0 |

Both versions read 14,125 physical pages and about 124.3 MB per range. Sampled self CPU includes polling, background and kernel work and is not a wall-latency fraction. The 25-second profile and 30-second command/counter interval are diagnostic runs, excluded from clean QPS plots. Stack attribution identifies the reply-copy path but does not classify every growth copy versus required serialization.

## Validation and CI

[Validation record](list-reply-validation.json): seven List/collection integration cases and three grouped cases pass against the exact fault-disabled benchmark binary. Coverage includes large byte-exact replies, transactions, blocking operations, low-memory ranges and real OOM. The test-driver sources are unchanged for this incremental production change; their provenance is recorded. Earlier 289 passing tests belong to `13041873`, not an unperformed full local suite on this revision.

PR #267 and #266 encountered full-disk String expiration recovery startup failures on both architectures. The root cause and locally validated fix are now recorded in [the recovery investigation](../grouped-expiry-recovery-20261004/README.md) and PR #268. Combined-head CI is pending; these earlier QPS observations do not measure the recovery repair.
