# List range reads: bounded I/O and reply admission

PR: [#267](https://github.com/eloqdata/lavik/pull/267). Main: `a565d603523467ed7bbb9ed9227ddd6b18a9ca8c`; candidate: `13041873749206f22329d584778d3096c8e1220a`. [Immutable binary/build proof](list-window-versions.json).

Full List range reads used serial page loads and four-copy mutation scratch admission, despite moving decoded values into one owned reply. The candidate overlaps at most 16 page loads, drains every started child on failure, revalidates population generations after joining, and appends values in logical rank order. Read admission covers one owned payload plus vector headers and the bounded task window; physical read buffers remain separately accounted. Single-page LINDEX keeps its direct loader. No payload cache, persisted-format change or relaxed durability is involved.

## Three paired repetitions

Each independent seed runs 15-second LRANGE points at 1/4/16 connections and LINDEX at 320. Pair order is A/B, B/A, A/B. Builds, tests and perf do not overlap the measurements. Failed observations are retained and are never treated as successful QPS. Three repetitions are not a confidence interval. [Raw summary](list-range-repeat-summary.json) · [all observations](list-range-repeats.json) · [runner](repeat-list-window.py).

| Command | Connections | Main successful-run median QPS | Candidate median QPS | Median paired change | Main failures / 3 | Candidate failures / 3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LRANGE | 1 | 0.91 | 3.35 | +266.3% (3 pairs) | 0 | 0 |
| LRANGE | 4 | 3.41 | 10.07 | +195.3% (3 pairs) | 0 | 0 |
| LRANGE | 16 | — | 18.63 | undefined | 3 | 0 |
| LINDEX | 320 | 355,230.90 | 376,732.19 | +15.3% (3 pairs) | 0 | 0 |

LRANGE improves in all six valid QPS pairs and lowers p99 in all six. Candidate LRANGE p99 medians are 335.871/831.487 ms at 1/4 connections, versus 1269.759/1425.407 ms on main. All three main 16-connection repetitions fail with OOM, whereas all three candidate repetitions succeed (median 18.63 QPS, p99 1507.327 ms); no QPS ratio is defined for that point.

LINDEX paired changes range from −12.8% to +20.2%, with one worse p99 and two better. The initial −6.9% observation does not reproduce as a consistent regression, but these runs also do not establish a stable point-read improvement. All individual p99 observations, including regressions, are retained in the paired summary. The single-grid LINDEX 320 observation was −6.9% with higher p99; the paired LINDEX runs specifically check that concern.

## Clean connection sweeps

All candidate grids validate cardinalities, record no command errors and exit cleanly. These are single independent sweeps, not statistical estimates. [100 MiB / 128 B](comparison-list-104857600-128-k8.json) · [64 KiB / 128 B](comparison-list-65536-128-k64.json) · [64 KiB / 1024 B](comparison-list-65536-1024-k64.json).

| Size / element | Command | QPS changes across measured connections |
| --- | --- | --- |
| 100 MiB / 128 B | LRANGE | c1: +267.8%; c4: +184.3%; c16: main OOM → candidate 18.06 QPS |
| 100 MiB / 128 B | LINDEX | c80: -2.4%; c320: -6.9%; c1280: +2.1%; c2560: -0.1%; c5120: +1.8% |
| 100 MiB / 128 B | LSET | c80: +11.1%; c320: +0.0%; c1280: +2.3%; c2560: +1.1%; c5120: -4.9% |
| 64 KiB / 128 B | LRANGE | c16: +0.0%; c80: +0.2% |
| 64 KiB / 128 B | LINDEX | c80: -1.1%; c320: -0.1%; c1280: +0.9%; c2560: -0.1%; c5120: +10.6% |
| 64 KiB / 128 B | LSET | c80: +4.3%; c320: +0.2%; c1280: +3.3%; c2560: +2.4%; c5120: +5.6% |
| 64 KiB / 1024 B | LRANGE | c16: -0.0%; c80: +0.1% |
| 64 KiB / 1024 B | LINDEX | c80: +2.3%; c320: +0.3%; c1280: +1.7%; c2560: +3.7%; c5120: +13.6% |
| 64 KiB / 1024 B | LSET | c80: +5.8%; c320: -4.2%; c1280: +5.4%; c2560: +2.3%; c5120: +6.7% |

Read changes do not establish write throughput gains. Small-range throughput is essentially unchanged. The full paired data and single-grid p99 values must be considered alongside QPS.

## Historical peer comparison

For the matching 100 MiB / 128 B / 8-key LRANGE workload, the clean candidate sweep gives 3.31, 9.75 and 18.06 QPS at 1, 4 and 16 connections. Historical Redis gives 5.26/14.10/16.47, Valkey 4.49/8.09/8.37, and Kvrocks 2.91/12.03/21.86. The 16-connection candidate point is about 17.4% below the fastest peer, within the provisional 20% target; the 1- and 4-connection points remain about 37% and 31% behind their fastest peer. This is progress in one workload, not overall parity.

Peers were not rerun. Redis/Valkey disable persistence; Kvrocks disables WAL and uses an 80 GiB cache; Lavik remains durable on six SPDK NVMe devices without field/page payload caching. These are matched commands/data, not equivalent persistence configurations. See the report manifest and linked raw peer measurements.

## Separate perf and I/O diagnostics

[Comparison](list-window-profile-comparison.json) · [candidate range samples](range-profile/) · [candidate write samples](write-profile/) · [baseline samples](../main-a565d603-20261004/README.md#large-list-range-diagnosis). All serving workers are sampled; an inactive helper has no samples.

| Version | Command | Self Worker::RunOnce | Self PollStorage | Self memmove | Physical reads / command | Physical writes / command |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| main | LRANGE | 42.22% | 30.76% | 2.09% | 14125.000 | 0.000 |
| main | LSET | 31.37% | 12.80% | 1.80% | 0.017 | 1.332 |
| candidate | LRANGE | 20.40% | 12.51% | 12.02% | 14125.000 | 0.000 |
| candidate | LSET | 31.31% | 12.12% | 1.77% | 0.017 | 1.334 |

Each LRANGE still reads 14,125 physical pages and approximately 124.3 MB, with no physical writes. The improvement overlaps reads rather than bypassing disk. CPU shares include polling, background and kernel work; they are not latency fractions. Perf covers 25 seconds while metrics cover the independent 30-second diagnostic, whose throughput is excluded from clean curves. Reply construction becomes a more visible copy hotspot; further optimization needs separate measurements.

## Correctness validation

[Validation record](list-window-validation.json): 157 focused unit tests, 105 ordered integration tests and 27 recovery tests pass; one pre-existing opt-in >1 GiB RDB test is skipped. Test builds enable faults; benchmark builds disable them. The new low-memory binary/rank-order test [fails on frozen main with scratch OOM](list-range-budget-baseline-repro.txt) and passes on the candidate. Partial launch allocation failure and page-read failure verify draining, metadata access, unrelated writes and recovery. The existing OOM fixture now gives each worker less than one full reply, preserving real exhaustion coverage.

CI is tracked on the PR and is not implied green by these local results.

The candidate range profile attributes 9.36 percentage points of total self CPU to memmove with AppendBulkArray in its stack. [Copy-path attribution](list-window-copy-callers.json) does not distinguish every buffer-growth copy from required serialization. The reply buffer releases capacity above 64 KiB on reset, and List array assembly has no total-size reservation; this is a measured copy path and a source-backed next candidate, not a claimed further speedup.
