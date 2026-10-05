# Sorted Set member-leaf reuse — October 4

## Current version status — October 5

PR #266 is at `067c7589` with full CI and native production tests passing. The
published baseline/member-leaf figures below remain measurements of `a565d603`
and `a1b24b60`, not of that updated head.

PR #273's planner-fixture repair `92906489` [passes full CI](pr273-92906489-full-ci.json).
Its [96-observation comparison](zset-source-reuse-complete-summary.json) is complete:
[100 MiB / 1024 B / 8 keys](zset-source-reuse-large.md) and
[64 KiB / 128 B / 64 keys](zset-source-reuse-small.md), each with three independent
AB/BA/AB pairs. Large-object ZINCRBY median paired QPS changes at
80/320/2560/5120 connections are +2.08%/+1.46%/+1.46%/−0.36%; small-object
changes are +2.79%/+1.04%/+2.19%/+2.88%. High-load write p99 improves, but the
large c5120 read-control p99 has a +14.81% median regression. Small read QPS at
c80/c320 has −3.00%/−2.22% median changes and p99 +4.46%/+8.21%, worse in two
of three pairs. All observations passed raw-data, cardinality, provenance and
server-exit checks. [Separate ZINCRBY perf](zset-source-reuse-perf.md) is complete; it shows similar
copy/allocator self shares and about 19 KB read / 22 KB written per command.
It does not diagnose ZSCORE latency. The PR stays a draft while the read-control
cause remains unresolved.

The candidate reaches only 5.91–8.71% (large) and 9.07–16.06% (small) of the
matching fastest historical peer's ZINCRBY throughput. Settings and sampling
differ, and the peers were not rerun. Independent fresh populations may have
different member-page layouts; the per-instance read grid precedes its writes.
Three pairs do not identify the cause of a regression or provide confidence intervals.

These measurements use the frozen production binary built at `d012a301`;
`92906489` changes only the test fixture and is recorded separately as test
validation. [All observations](zset-source-reuse-repeats.json) and the linked
scope reports retain every result, including regressions. The failure history below
keeps the original evidence separate from the completed validation.

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

This improvement does not reach parity with the three historical peers. Redis/Valkey persistence is disabled; Kvrocks WAL is disabled with an 80 GiB cache; Lavik remains durable without a resident field/page payload cache. Peers were not rerun, and the curves do not compare equivalent durability settings. The independently measured #273 source-page reuse follow-up reduces some of that repeated work but does not close this gap; its complete results are linked above.

## CI investigation

The first CI run at `a1b24b60` failed Sentinel subscriptions, an arm64 native-FULL promotion wait, and an arm64 grouped String server startup. [Investigation record](ci/pr266-ci-investigation.json) distinguishes these failures. The Sentinel EOF reproduced in 1/10 targeted runs with the exact CI amd64 binary; waiting for current-term runtime discovery authority fixes the fixture, with [30 targeted repetitions and 15 complete-suite tests passing](ci/sentinel-rechecks.json). Commit `dffc520b` changes only that fixture, so the performance binary remains `a1b24b60`.

The grouped startup failure subsequently reproduced on amd64 and main; [the recovery investigation and PR #268 repair](../grouped-expiry-recovery-20261004/README.md) supersede that unresolved diagnosis. The current branch also includes the repair and expanded Meta fixture corrections; combined-head CI at `97aeecc8` [passed on both architectures](https://github.com/eloqdata/lavik/actions/runs/37229849221), including all 12 test shards and formatting ([record](pr266-97ae-ci.json)). The earlier native-FULL timeout has not recurred in subsequent completed runs, but amd64 repetitions do not establish its arm64 root cause. Throughput curves remain pinned to the earlier `a1b24b60` binary.


## Inline-page lookup follow-up (unmeasured)

[Draft PR #271](https://github.com/eloqdata/lavik/pull/271), current source `2e6e4f35` (earlier prototype `274508f0`), skips extent-manifest lookups for inline pages in 12 scratch-admission call sites and the ordered-page loader. The existing candidate profile attributes 0.54% of sampled self CPU to `ExtentsFor`; that share motivates the experiment and is not a QPS estimate. External pages still retain their manifests and use the existing size checks. Full CI passes. Native validation and [72 observations shared with the independent #272 candidate](../grouped-lookup-controls-20261005/README.md) are queued; new throughput and perf evidence remain pending. The draft extends the existing mixed inline/external fixture to compare admission bytes against the physical envelope.

At `274508f0`, both builds and 11/12 software shards passed; arm64 shard 5 failed `meta_integration.sentinel_ha_meta` ([CI](https://github.com/eloqdata/lavik/actions/runs/37236308753)). Four independent stock clients were probed serially against one 30-second fault deadline: the last client completed after the deadline. `e6ae3d78` runs those probes concurrently, retains the original fault deadline and checks actual completion time before accepting success. New harness regressions cover concurrent starts, late completion, an expired budget and retry. All four [local harness regressions](pr271-recovery-probe-tests.txt) pass after the clean imports finished. That intermediate CI was superseded by the main-integrated head; its completed validation is recorded below. No native performance result is implied. See [failure and follow-up provenance](pr271-ci-followup.json).

[Existing clean-sweep commit counters](write-commit-counter-inventory.json) cover 100 MiB / 1024 B / 8-key XADD_MAXLEN and ZINCRBY at 80–5120 connections, for main and their respective measured candidates. None of these intervals increments `tx_commit_backpressure_waits`; average commit batches contain roughly 3–6 transactions. This does not support attributing their throughput gap to the queue high-watermark wait. INFO snapshots include background work and possible work carried over from preceding commands; queue peaks are lifetime values. The counters do not measure causal-decision flush latency and do not justify weakening commit ordering.


## Decoded-hash validation follow-up (unmeasured)

[Draft PR #272](https://github.com/eloqdata/lavik/pull/272), current source `8babe581`, independently builds on #266. The owned Hash decoder already reconstructs process-seed field digests; the draft reuses them for duplicate detection, using smaller pointer keys with complete-field equality. Encoder/planner inputs may contain stale digests and still hash their field bytes. Routed decoding additionally reuses the fresh digest only when the persisted routing seed equals the process seed; other seeds retain explicit hashing and all fields still undergo route validation.

The existing candidate profile attributes 1.99% of sampled self CPU to SipHash in member-leaf loading. This motivates removing repeated hashing, not a predicted speedup. A new codec regression covers current/distinct persisted seeds, wrong seeds, a misplaced later field, binary bytes and process-seed output digests. The existing duplicate-field fixture already edits names while retaining stale cached digests. Full CI passes; native validation and the linked common-parent comparisons are queued. No new throughput or perf conclusion is available. No format, commit-order, or cache change is introduced.

## Ordered source-page follow-up

[Draft PR #273](https://github.com/eloqdata/lavik/pull/273), production source `d012a301` with tests-only repair `92906489`, reuses one already admitted ordered source page for a same-page point update or deletion. Source inspection identifies a second read/decode between membership verification and after-image planning; the existing profile records 0.87% planner self CPU, excluding callees, which is not a speedup estimate. Cross-page moves, maximum-score ties and batch operations keep the bounded existing path. The retained credit is subtracted from the complete plan reservation and both credits survive prepared publication. The existing point-write fixture now covers successful reuse, required-read failure atomicity, EXEC and restart; a budget unit covers credit lifetime and failed admission. Native validation, corrected full CI, all 96 clean observations and separate write perf are complete as linked above. Read regressions remain unresolved. The draft is based on #266 independently of #271/#272.

## Integration and retained failures

These candidates incorporated main `19496654` after the original `a565d603` baseline was frozen; the [integration record](../main-a565d603-20261004/pr-main-integration.json) preserves that earlier state, not current main. The original member-probe QPS/perf remains attributed to `a1b24b60`. The later source-page comparison uses parent `067c7589` and production candidate `d012a301`, with the tests-only validation commit recorded separately.

Pre-integration #272 at `ace193a2` [passed both builds and all 12 software shards](pr272-ace-pre-main-ci.json). Integrated #271 `2e6e4f35` [passes all 17 CI jobs](pr271-2e6e4f35-full-ci.json), as does #272 `8babe581` [independently](pr272-8babe581-full-ci.json). Their native and performance gates are described in the [queued common-parent protocol](../grouped-lookup-controls-20261005/README.md).

For #273, `d5ca3a1b` failed two fixtures: native full-tail assertions ran before all live replica flows resumed, and Sentinel client probes exhausted a shared deadline when run serially. The follow-up waits for live-flow readiness before one-shot collection assertions and runs independent probes concurrently under the original deadline. [Failure evidence and fixes](pr273-ci-followup.json).

## Native production validation for source-page reuse

The frozen parent `067c7589` and candidate `d012a301` each pass 20 Sorted Set/demotion cases; seven fault-only cases per binary are skipped with fault injection disabled. Exercised cases include point/batch changes, cross-page score moves, large members, range/removal, recovery and demotion. [Exact binary hashes and per-case results](zset-source-reuse-native-validation.json) · [parent full CI](zset-source-reuse-previous-full-ci.json). Candidate fault-enabled validation is recorded below, rather than attributed to the skipped production cases. Test elapsed times are not throughput results.

All local builds, tests, clean seeding/measurements and perf diagnostics use the same [host execution lock](host_execution_lock.py). Remote CI can progress concurrently. The persistent lock file is not a success marker and is never unlinked while tasks exist.

## Planner fault fixture failure and verified repair

[CI at `d012a301`](pr273-d012-full-ci-failure.json) failed `PointWritesReuseMemberLeafAndKeepBatchFailureAtomic` in both architectures' shard 0; aggregate failures refer to those same failures. A cross-page ZINCRBY succeeded where the fixture expected a planner read error. The planner-fault environment variables were set after the server child started, so the child did not receive them; the earlier member-leaf fault remained active. [Original investigation](pr273-planner-fault-fixture.json).

The original fixture reproduces locally. Tests-only commit `92906489` starts separate server phases after setting the required faults, preserving cross-page/batch failure, both-index score, EXEC and restart assertions. The corrected driver passes all 27 selected fault-enabled Sorted Set/ordered/demotion cases with zero skips. The server has exactly the same SHA-256 in both runs, and the source diff changes only `tests/grouped/zset_write_e2e_test.cpp`. [Failure and corrected results with server hashes](zset-planner-fault-validation.json) · [validation driver](validate-zset-planner-fault.py). The corrected commit also [passes all 17 CI jobs](pr273-92906489-full-ci.json).

The original clean runner stopped before seeding when the CI gate failed. The [resumed 96-observation runner](repeat-zset-after-planner-fault-fix.py) subsequently completed using the unchanged production binary `d012a301`, explicitly retaining `92906489` as a separate test-validation identity. [Independent perf](profile-zset-after-planner-fix.py) completed after those clean observations. Results, regressions and historical peer gaps are linked at the top of this report; the successful test repair does not itself imply any throughput gain.
