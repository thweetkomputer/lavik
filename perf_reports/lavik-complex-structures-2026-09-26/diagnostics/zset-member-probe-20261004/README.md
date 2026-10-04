# Sorted Set member-leaf reuse — October 4

[PR #266](https://github.com/eloqdata/lavik/pull/266).

Baseline: `a565d603`; candidate: `a1b24b60`. [Exact binaries and hashes](zset-probe-versions.json) · [CMake configuration](zset-probe-CMakeCache.txt). One-distinct-member writes transfer the checked lookup leaf and its admission into index preparation, avoiding a second load/decode/hash/copy. The data lives only within the command; durable formats and resident payload caching remain unchanged. The existing preparation yield is preserved, with payload and memory credit transferred together before suspension.

## Clean connection sweeps

Twelve workers, six SPDK NVMe devices, an independent client, pipeline 1 and eight seconds per point. Each condition is independently seeded and validated. No concurrent builds, tests or perf run during these sweeps.

| Dataset | Connections | Main ZINCRBY QPS | Candidate QPS | Change | Main p99 ms | Candidate p99 ms |
| --- | --- | --- | --- | --- | --- | --- |
| 8 × 100 MiB, 1 KiB members | 80 | 36795 | 38234 | +3.9% | 13.2 | 12.8 |
| 8 × 100 MiB, 1 KiB members | 320 | 38017 | 41104 | +8.1% | 33.3 | 31.9 |
| 8 × 100 MiB, 1 KiB members | 1280 | 38311 | 40690 | +6.2% | 110.1 | 112.1 |
| 8 × 100 MiB, 1 KiB members | 2560 | 38328 | 41462 | +8.2% | 146.4 | 199.7 |
| 8 × 100 MiB, 1 KiB members | 5120 | 41680 | 41796 | +0.3% | 215.0 | 270.3 |
| 64 × 64 KiB, 128 B members | 80 | 68405 | 78151 | +14.2% | 13.9 | 11.9 |
| 64 × 64 KiB, 128 B members | 320 | 70799 | 82881 | +17.1% | 36.9 | 33.3 |
| 64 × 64 KiB, 128 B members | 1280 | 68863 | 79155 | +14.9% | 148.5 | 133.1 |
| 64 × 64 KiB, 128 B members | 2560 | 72104 | 79277 | +9.9% | 299.0 | 266.2 |
| 64 × 64 KiB, 128 B members | 5120 | 69985 | 81526 | +16.5% | 593.9 | 536.6 |

These are single sweeps, not confidence intervals. The [large comparison](comparison-zset-104857600-1024-k8.json) and [small comparison](comparison-zset-65536-128-k64.json) retain every read/write QPS and p99 point.

## Independent paired write runs

Three independent seed pairs ordered A/B, B/A, A/B; 15-second ZINCRBY points at 80/320/2560 connections; same baseline workload and settings; no concurrent build, tests or perf.

| Connections | Median main QPS | Median candidate QPS | Median paired change | Paired change range | Median main p99 ms | Median candidate p99 ms |
| --- | --- | --- | --- | --- | --- | --- |
| 80 | 37057 | 39047 | +5.8% | +4.3% to +6.4% | 13.4 | 12.6 |
| 320 | 38488 | 40735 | +6.5% | +4.4% to +8.5% | 34.6 | 30.7 |
| 2560 | 40523 | 40741 | +1.0% | -0.7% to +7.4% | 219.1 | 194.6 |

[All paired observations and raw tags](zset-write-repeats.json) · [Summary](zset-write-repeat-summary.json) · [Runner](repeat-zset.py). Three pairs do not provide a confidence interval.

At 80/320 connections all three paired QPS changes are positive and p99 is no worse. At 2560 connections, the median paired QPS change is only +1.0% (range -0.7% to +7.4%); candidate p99 is higher in one pair and lower in two. The earlier single sweep has higher p99 at 2560/5120 connections, so these results do not establish a uniform high-load latency improvement. The small-ZSet ZSCORE sweep also includes a -5.8% point at 5120 connections. Both high-load cases need further repetitions.

## CPU and I/O evidence

[Profile and counter comparison](zset-probe-profile-comparison.json) · [Worker summary](zset-probe-workers.json) · [Recorder, threads, metrics and self reports](candidate-profile/) · [Analyzer](analyze-zset.py). The separate 30-second diagnostic attaches to all 12 serving workers at 99 Hz for 25 seconds, with 16 KiB DWARF stacks. One extra inactive helper has no samples. Diagnostic QPS is excluded from the curves.

SipHash self CPU is 4.98% on main and 3.55% on candidate; memmove is 2.82% and 2.20%. Full-callchain attribution places 3.65% and 1.99% under Hash-leaf loading. Allocator `_mi_theap_malloc_zero` share is 1.74% and 1.57%; these sampled shares do not measure allocation counts.

Physical reads per completed command are 0.195 and 0.165, while read bytes are 18.5 kB and 18.1 kB. These server-wide counters include background work and buffering; logical leaf loads are not physical reads. All CPU percentages include polling/background/kernel work and are not latency fractions.

An earlier immediate-caller grouping overstated the main leaf-loading SipHash share as 3.84%; per-sample full visible stacks give 3.65%. Unknown stacks remain unattributed.

## Correctness and expiry fixture repair

[Validation summary](zset-probe-validation.json) records the final unit, ordered-write and recovery suite results. [Unit](zset-yield-unit.json), [ordered writes](zset-yield-ordered.json), and [recovery](zset-yield-recovery.json) retain the individual test results.

The new point-write fault-injection test disables the second member-index leaf read: point replacement, insertion, deletion and consecutive EXEC writes succeed; a multi-member fallback fails atomically, and restart preserves both indexes.

Validation of the initial candidate exposed an unrelated expiry fixture race. Frozen main reproduced it in 1/5 attempts: defrag can free space before the two-second TTL expires, so replacement success does not imply old keys should be absent on recovery. The fixture now observes expiry first. It passed five times each on [frozen main](expiry-baseline-fixed.txt) and [initial candidate](expiry-candidate-fixed.txt); [baseline reproduction](expiry-baseline-repro.txt) and the [initial validation record](initial/zset-probe-validation.json) are retained. Production String behavior is unchanged.

## Initial candidate and scheduling refinement

The initial `4fe60fee` candidate improved large-ZSet paired QPS by 9–11%, but all three 2560-connection pairs had higher p99 than main. It also removed the preparation yield on the reused-leaf path. The final candidate restores that scheduling opportunity and transfers both payload and its admission before yielding. [Initial paired data](initial/zset-write-repeat-summary.json) and [initial profiles](initial/zset-probe-profile-comparison.json) remain available. The measurements above use the final binary and fresh baseline/candidate pairs; restoring the yield is a scheduling hypothesis, not proof of the cause of every latency variation.

## Remaining gap

This improvement does not reach parity with the three historical peers. Redis/Valkey persistence is disabled; Kvrocks WAL is disabled with an 80 GiB cache; Lavik remains durable without a resident field/page payload cache. Peers were not rerun, and the curves do not compare equivalent durability settings. Ordered source pages are still loaded again during planning and remain a possible follow-up, subject to bounded ownership and new measurements.

## CI investigation

The first CI run at `a1b24b60` failed Sentinel subscriptions, an arm64 native-FULL promotion wait, and an arm64 grouped String server startup. [Investigation record](ci/pr266-ci-investigation.json) distinguishes these failures. The Sentinel EOF reproduced in 1/10 targeted runs with the exact CI amd64 binary; waiting for current-term runtime discovery authority fixes the fixture, with [30 targeted repetitions and 15 complete-suite tests passing](ci/sentinel-rechecks.json). Commit `dffc520b` changes only that fixture, so the performance binary remains `a1b24b60`.

The grouped startup failure subsequently reproduced on amd64 and main; [the recovery investigation and PR #268 repair](../grouped-expiry-recovery-20261004/README.md) supersede that unresolved diagnosis. The current branch also includes the repair and expanded Meta fixture corrections; combined-head CI at `97aeecc8` [passed on both architectures](https://github.com/eloqdata/lavik/actions/runs/37229849221), including all 12 test shards and formatting ([record](pr266-97ae-ci.json)). The earlier native-FULL timeout has not recurred in subsequent completed runs, but amd64 repetitions do not establish its arm64 root cause. Throughput curves remain pinned to the earlier `a1b24b60` binary.
