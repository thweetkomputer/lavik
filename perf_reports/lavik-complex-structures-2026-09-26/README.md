# Complex structures: Redis, Valkey, Kvrocks and Lavik

**Rebase CI update:** #267 fixes a stale List fault-test message assertion in `0cc00887`; new CI is pending. #270 has an unresolved Sentinel HA recovery-budget failure. [Evidence and disposition](diagnostics/grouped-expiry-recovery-20261004/rebase-ci-failures-20261005.md).

**2026-10-05 PR consolidation:** #268 is merged as main `330738d9`. #266/#267/#270/#280/#282 are rebased onto it; #271/#272 follow rebased #266 and #275 follows rebased #270. #269/#273/#276 are closed for insufficient overall benefit or control regressions; #274 was already closed. New optimization exploration is suspended while retained candidates finish validation and CI. [Commits, dependencies and checks](diagnostics/grouped-expiry-recovery-20261004/prs-rebased-after268.json). Historical measurements and closed-candidate curves remain evidence, not validation of the rebased heads.

[Stream read-window #275: all 24 large-read observations](diagnostics/stream-reply-20261004/stream-window-large-reads.md) are complete. For 100 MiB / 128 B / 8 keys, median paired full-read QPS changes at c1/4/16 are **+327.45% / +233.85% / +128.49%**; point reads at c2560 change **−1.07%**. Full-read QPS medians are 2.18 / 6.41 / 16.28, above the corresponding historical peer measurements. Peers were not rerun and durability differs; this does not establish overall parity. [All 12 large-write controls](diagnostics/stream-reply-20261004/stream-window-large-writes.md) are also complete: XADD c320/c5120 median paired QPS changes are **−4.39%/+2.15%**, with mixed directions across rounds. [All 24 small-object controls](diagnostics/stream-reply-20261004/stream-window-small-controls.md) are complete: both XADD levels lose QPS in all three pairs (medians **−3.80%/−1.65%**); full-read QPS is nearly unchanged while p99 worsens in all three pairs (median **+40.44%**). All 60 observations are complete, but this is not a general improvement. Independent [full-read](diagnostics/stream-reply-20261004/stream-window-full-perf.md) and [point-read](diagnostics/stream-reply-20261004/stream-window-point-perf.md) perf are complete; rebased-head CI remains pending; the original RDB timeout is unexplained and the PR stays draft.

All [144 Hash/Set route-replacement observations](diagnostics/hash-route-replace-20261005/hash-route-complete.md) are complete. Large-Hash HSET c5120 gains +7.81% QPS, but smaller-Hash HSET and both Set write scopes have negative paired medians. #276 is closed; all QPS/p99 tradeoffs and historical peer gaps are retained. [Four large-object perf captures](diagnostics/hash-route-replace-20261005/hash-route-large-perf.md) are complete; the unstarted small-Hash sampling was cancelled and the regressions are not yet explained.

[简体中文](README.zh-CN.md)

[ZINCRBY worker-distribution analysis](diagnostics/zset-worker-distribution-20261005/README.md): the fixed eight keys map to four data owners with 12 workers. Existing perf thread distribution is documented; fixed-binary 8/12-worker controls are queued, with no tuning gain claimed.

[Borrowed member-page score reads](diagnostics/zset-score-views-20261005/README.md): avoids owning every field/value while retaining full validation. All 17 jobs pass in both fork and upstream CI; [PR #280](https://github.com/eloqdata/lavik/pull/280) remains draft; 96 paired observations and independent ZSCORE perf are queued, with no measured gain yet.

[Draft PR #282](https://github.com/eloqdata/lavik/pull/282): long-key root reuse now passes three independent retained-image replays: the 9 MiB-key GET returns and verifies its full 6 MiB value in **1.823 / 1.832 / 1.820 s**. The failed 60-second baseline is retained; these are candidate-only checks, not paired QPS or an exact speedup. Both fork and upstream CI pass all 17 jobs at `28d7cca4`; ordinary short-key native regression and 72 paired controls remain pending. [Evidence and limitations](diagnostics/list-reply-reserve-20261004/README.md).

**2026-10-04: main `a565d603`, including merged #244, #246, #247, #249, #258, #259, #260, #262; 28/28 conditions refreshed.**

Batched HSET/SADD import is tracked separately: 4/4 conditions refreshed.

Throughput figures fix the command, payload bytes per key, entry size and key count; axes show connections and QPS. Batched-import figures show seconds to fill a fixed dataset. Figures retain the fixed main baseline and historical candidates, including closed PRs; peers retain historical measurements of the same workload.

Redis/Valkey disable persistence. Kvrocks uses uncompressed RAID0, disabled WAL and 80 GiB block/blob cache. Lavik persists through six SPDK NVMe devices without caching field/page payloads. Write QPS compares these configurations, not equivalent durability.

Peers are not rerun this round. Lavik uses AMD EPYC 9V74, 16 vCPUs and 12 serving workers. Points last 8 s (10 s for high-key-count LSET), pipeline=1. Each condition is independently seeded and checked key by key. CPU profiles run separately after complete clean grids. Single sweeps have no statistical confidence intervals.

This round pins the main revision above. Merged optimizations are no longer separate PR curves. Historical observations retain their measured commits; each chart is replaced only after its independent rerun completes.

[Plot sources](current-main.json) · [Runner](run.py) · [Previous-round build and hardware](diagnostics/main-refresh-20261004/host-and-build.json)

[Complete main baseline: per-command gaps and optimization priorities](diagnostics/main-a565d603-20261004/main-gap-summary.md)

[Current build and hardware](diagnostics/main-a565d603-20261004/host-and-build.json)

[Current perf analysis](diagnostics/main-a565d603-20261004/README.md)

[Current plot-data audit](diagnostics/main-a565d603-20261004/report-audit.json)

[Previous-round plot-data audit](diagnostics/main-refresh-20261004/report-audit.json) · [Previous-round audit script](diagnostics/main-refresh-20261004/audit-report.py)

[Hash/Set write profiles](diagnostics/hashset-write-20261004/README.md) · [Ordered metadata optimization and tests](diagnostics/ordered-metadata-20261004/README.md)

Unmerged optimizations: [PR #266](https://github.com/eloqdata/lavik/pull/266) · [PR #267](https://github.com/eloqdata/lavik/pull/267) · [PR #270](https://github.com/eloqdata/lavik/pull/270)

Integration branches include newer main revisions; this report retains pinned baseline `a565d603`. [Combined validation branch and status](diagnostics/combined-20261005/README.md). [Integrated PR heads and validation status](diagnostics/main-a565d603-20261004/pr-main-integration.json) remain separate from the measured binaries.

[Stream suffix directory reuse: throughput, paired runs, perf and tests](diagnostics/stream-suffix-20261004/README.md) — #265 merged on 2026-10-05; its measurements retain their original commits and are not a fresh main rerun.

[Stream reply batching PR #270: paired checks, controls and perf](diagnostics/stream-reply-20261004/README.md)

The subsequent singleton PR #274 completed all 60 observations in three paired rounds without the intended gain and has been closed: large/small point-read QPS medians −0.39%/−3.18%; small writes −3.36%/−3.31%, declining in all three pairs at both levels. All four separate profiles are complete; the linked diagnosis includes provenance and CPU/IO summaries. Removing a source-level copy is not itself a measured throughput gain.

The [Stream page-key validation prototype](diagnostics/stream-key-validation-20261005/README.md) passes all 17 CI checks. Native validation and paired performance measurements remain pending; no QPS gain is claimed.

[ZSet member-leaf reuse: throughput, paired runs, perf and tests](diagnostics/zset-member-probe-20261004/README.md)

Follow-up [PR #271](https://github.com/eloqdata/lavik/pull/271) removes redundant inline-page manifest lookups. Native validation and [72 observations against the common parent](diagnostics/grouped-lookup-controls-20261005/README.md) for #271/#272 are queued; no throughput gain is established.

[PR #272](https://github.com/eloqdata/lavik/pull/272) reuses decoded hashes in duplicate and route validation; it remains an unmeasured draft.

[PR #273](https://github.com/eloqdata/lavik/pull/273) reuses an admitted ordered source page for point writes. [All 48 large-object observations](diagnostics/zset-member-probe-20261004/zset-source-reuse-large.md) show median paired ZINCRBY QPS changes of +2.08%/+1.46%/+1.46%/−0.36% at the four concurrency levels. High-load write p99 improves, but the c5120 read control has a +14.81% median p99 regression. [All 48 small-object controls](diagnostics/zset-member-probe-20261004/zset-source-reuse-small.md) are also complete: write QPS medians improve +1.04% to +2.88%, but low-concurrency read QPS changes are −3.00%/−2.22% and p99 +4.46%/+8.21%. [Separate write perf](diagnostics/zset-member-probe-20261004/zset-source-reuse-perf.md) is complete and shows no order-of-magnitude cost reduction. The overall benefit is insufficient to justify the complexity; #273 is closed.

[List range reads: throughput, memory admission, paired runs and perf](diagnostics/list-read-window-20261004/README.md)

[List reply reservation: incremental repeats, copy hotspots and current results](diagnostics/list-reply-reserve-20261004/README.md)

[List byte-bounded window: closed PR #269 paired repeats, regressions and perf](diagnostics/list-byte-window-20261004/README.md)

[Full-device expiration recovery and CI repair (PR #268; historical observations retain their original binaries)](diagnostics/grouped-expiry-recovery-20261004/README.md)

Failed observations in this run (gaps in figures; errored requests are not successful QPS):

- List LRANGE · 100 MiB/key · 128 B · 16 connections: [recorded failure](raw/lavik-maina565d603-ordered-list-104857600-k8-f128-20261004/list-104857600-128-lrange-c16.error.json).

[100 MiB LRANGE admission analysis](diagnostics/main-refresh-20261004/list-lrange-admission.md)

## List

### LINDEX

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![List LINDEX 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f128-20261004/) · [Lavik closed PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![List LINDEX 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f1024-20261004/) · [Lavik closed PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![List LINDEX 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![List LINDEX 1 MiB/key, 1024 B, 64 keys](charts/list-1048576-1024-k64-lindex-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![List LINDEX 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lindex-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f128-20261004/) · [Lavik closed PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![List LINDEX 100 MiB/key, 1024 B, 8 keys](charts/list-104857600-1024-k8-lindex-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f1024-20261004/) · [Lavik closed PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f1024-20261004/)

### LSET

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![List LSET 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f128-20261004/) · [Lavik closed PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![List LSET 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f1024-20261004/) · [Lavik closed PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![List LSET 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lset-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f128-20261004/)

1024 B/entry · 50,000 keys · Measured main baseline `a565d603`

![List LSET 1 MiB/key, 1024 B, 50000 keys](charts/list-1048576-1024-k50000-lset-current.png)

[Redis](raw/redis-lset-matched-1048576-k50000-f1024-20261001/) · [Valkey](raw/valkey-lset-matched-1048576-k50000-f1024-20261001/) · [Kvrocks (80 GiB cache)](raw/kvrocks-lset-matched-1048576-k50000-f1024-20261001/) · [Lavik main a565d603](raw/lavik-maina565d603-lset-list-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![List LSET 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lset-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f128-20261004/) · [Lavik closed PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f128-20261004/)

1024 B/entry · 500 keys · Measured main baseline `a565d603`

![List LSET 100 MiB/key, 1024 B, 500 keys](charts/list-104857600-1024-k500-lset-current.png)

[Redis](raw/redis-lset-matched-104857600-k500-f1024-20261001/) · [Valkey](raw/valkey-lset-matched-104857600-k500-f1024-20261001/) · [Kvrocks (80 GiB cache)](raw/kvrocks-lset-matched-104857600-k500-f1024-20261001/) · [Lavik main a565d603](raw/lavik-maina565d603-lset-list-104857600-k500-f1024-20261004/)

### LRANGE 0 -1

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![List LRANGE 64 KiB/key, 128 B, 64 keys](charts/list-65536-128-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f128-20261004/) · [Lavik closed PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![List LRANGE 64 KiB/key, 1024 B, 64 keys](charts/list-65536-1024-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-65536-k64-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-65536-k64-f1024-20261004/) · [Lavik closed PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![List LRANGE 1 MiB/key, 128 B, 64 keys](charts/list-1048576-128-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![List LRANGE 1 MiB/key, 1024 B, 64 keys](charts/list-1048576-1024-k64-lrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![List LRANGE 100 MiB/key, 128 B, 8 keys](charts/list-104857600-128-k8-lrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f128-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f128-20261004/) · [Lavik closed PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![List LRANGE 100 MiB/key, 1024 B, 8 keys](charts/list-104857600-1024-k8-lrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-list-104857600-k8-f1024-20261004/) · [Lavik PR #267 ff9e3655](raw/lavik-candidateff9e3655-ordered-list-104857600-k8-f1024-20261004/) · [Lavik closed PR #269 4863c98d](raw/lavik-candidate4863c98d-ordered-list-104857600-k8-f1024-20261004/)

### RPUSH batched seeding

Independent LSET seeding timings: 32 clients, pipeline=4, 128 one-KiB entries per command, with the same client encoder across all four databases.

#### 1 MiB/key

![List RPUSH fill, 50000 keys](charts/list-1048576-1024-k50000-rpush-fill-current.png)

#### 100 MiB/key

![List RPUSH fill, 500 keys](charts/list-104857600-1024-k500-rpush-fill-current.png)

## Hash

### HGET

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Hash HGET 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hget-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Hash HGET 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hget-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `a565d603`

![Hash HGET 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hget-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · Measured main baseline `a565d603`

![Hash HGET 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hget-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f1024-20261004/)

### HSET

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Hash HSET 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hset-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Hash HSET 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hset-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `a565d603`

![Hash HSET 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hset-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · Measured main baseline `a565d603`

![Hash HSET 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hset-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f1024-20261004/)

### HGETALL

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Hash HGETALL 1 MiB/key, 128 B, 50000 keys](charts/hash-1048576-128-k50000-hgetall-current.png)

[Redis](raw/redis-hash-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Hash HGETALL 1 MiB/key, 1024 B, 50000 keys](charts/hash-1048576-1024-k50000-hgetall-current.png)

[Redis](raw/redis-hash-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-hash-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `a565d603`

![Hash HGETALL 100 MiB/key, 128 B, 500 keys](charts/hash-104857600-128-k500-hgetall-current.png)

[Redis](raw/redis-hash-100m-k500-f128-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · Measured main baseline `a565d603`

![Hash HGETALL 100 MiB/key, 1024 B, 500 keys](charts/hash-104857600-1024-k500-hgetall-current.png)

[Redis](raw/redis-hash-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-hash-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-hash-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-hash-104857600-k500-f1024-20261004/)

### HSET batched import

#### 1 MiB/key

50,000 keys; 8 clients, pipeline=64, about 16 KiB entries/command. Per-command RESP encoding matches the historical peer workload; elapsed time includes Python client encoding. This is not RESTORE or a server-only throughput ceiling.

1024 B/entry · Measured main baseline `a565d603`

![HSET batched import, 1024 B](charts/hash-1048576-1024-k50000-fill.png)

[Lavik raw](raw/lavik-maina565d603-import-hash-1048576-k50000-f1024-20261004/)

128 B/entry · Measured main baseline `a565d603`

![HSET batched import, 128 B](charts/hash-1048576-128-k50000-fill.png)

[Lavik raw](raw/lavik-maina565d603-import-hash-1048576-k50000-f128-20261004/)

## Set

SADD + SREM mixes the two commands equally; QPS counts commands, not pairs. Random concurrent access can produce no-op additions/removals, so this is not the rate of durable changes.

### SISMEMBER

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Set SISMEMBER 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-sismember-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Set SISMEMBER 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-sismember-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `a565d603`

![Set SISMEMBER 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-sismember-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · Measured main baseline `a565d603`

![Set SISMEMBER 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-sismember-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-104857600-k500-f1024-20261004/)

### SADD + SREM

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Set SADD_SREM 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-sadd_srem-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Set SADD_SREM 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-sadd_srem-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `a565d603`

![Set SADD_SREM 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-sadd_srem-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · Measured main baseline `a565d603`

![Set SADD_SREM 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-sadd_srem-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-104857600-k500-f1024-20261004/)

### SMEMBERS

#### 1 MiB/key

128 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Set SMEMBERS 1 MiB/key, 128 B, 50000 keys](charts/set-1048576-128-k50000-smembers-current.png)

[Redis](raw/redis-set-1m-k50000-f128-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f128-20261004/)

1024 B/entry · 50,000 keys · Measured main baseline `a565d603`

![Set SMEMBERS 1 MiB/key, 1024 B, 50000 keys](charts/set-1048576-1024-k50000-smembers-current.png)

[Redis](raw/redis-set-1m-k50000-f1024-20260929/) · [Valkey](raw/valkey-set-1m-k50000-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-1m-k50000-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-1048576-k50000-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 500 keys · Measured main baseline `a565d603`

![Set SMEMBERS 100 MiB/key, 128 B, 500 keys](charts/set-104857600-128-k500-smembers-current.png)

[Redis](raw/redis-set-100m-k500-f128-20260929/) · [Valkey](raw/valkey-set-100m-k500-f128-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f128-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-104857600-k500-f128-20261004/)

1024 B/entry · 500 keys · Measured main baseline `a565d603`

![Set SMEMBERS 100 MiB/key, 1024 B, 500 keys](charts/set-104857600-1024-k500-smembers-current.png)

[Redis](raw/redis-set-100m-k500-f1024-20260929/) · [Valkey](raw/valkey-set-100m-k500-f1024-20260929/) · [Kvrocks (80 GiB cache)](raw/kvrocks-set-100m-k500-f1024-20260929/) · [Lavik main a565d603](raw/lavik-maina565d603-hashset-set-104857600-k500-f1024-20261004/)

### SADD batched import

#### 1 MiB/key

50,000 keys; 8 clients, pipeline=64, about 16 KiB entries/command. Per-command RESP encoding matches the historical peer workload; elapsed time includes Python client encoding. This is not RESTORE or a server-only throughput ceiling.

1024 B/entry · Measured main baseline `a565d603`

![SADD batched import, 1024 B](charts/set-1048576-1024-k50000-fill.png)

[Lavik raw](raw/lavik-maina565d603-import-set-1048576-k50000-f1024-20261004/)

128 B/entry · Measured main baseline `a565d603`

![SADD batched import, 128 B](charts/set-1048576-128-k50000-fill.png)

[Lavik raw](raw/lavik-maina565d603-import-set-1048576-k50000-f128-20261004/)

## Sorted Set

### ZSCORE

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZSCORE 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f128-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZSCORE 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZSCORE 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZSCORE 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zscore-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![Sorted Set ZSCORE 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zscore-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![Sorted Set ZSCORE 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zscore-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f1024-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-104857600-k8-f1024-20261004/)

### ZINCRBY

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZINCRBY 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f128-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZINCRBY 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZINCRBY 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZINCRBY 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zincrby-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![Sorted Set ZINCRBY 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zincrby-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![Sorted Set ZINCRBY 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zincrby-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f1024-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-104857600-k8-f1024-20261004/)

### ZRANGE 0 -1 WITHSCORES

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZRANGE 64 KiB/key, 128 B, 64 keys](charts/zset-65536-128-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f128-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZRANGE 64 KiB/key, 1024 B, 64 keys](charts/zset-65536-1024-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZRANGE 1 MiB/key, 128 B, 64 keys](charts/zset-1048576-128-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Sorted Set ZRANGE 1 MiB/key, 1024 B, 64 keys](charts/zset-1048576-1024-k64-zrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![Sorted Set ZRANGE 100 MiB/key, 128 B, 8 keys](charts/zset-104857600-128-k8-zrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![Sorted Set ZRANGE 100 MiB/key, 1024 B, 8 keys](charts/zset-104857600-1024-k8-zrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-zset-104857600-k8-f1024-20261004/) · [Lavik PR #266 a1b24b60](raw/lavik-candidatea1b24b60-ordered-zset-104857600-k8-f1024-20261004/)

## Stream

### XRANGE (one ID)

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f128-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f1024-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xrange-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![Stream XRANGE 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f128-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![Stream XRANGE 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xrange-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-104857600-k8-f1024-20261004/)

### XADD MAXLEN ~

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XADD_MAXLEN 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f128-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XADD_MAXLEN 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f1024-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XADD_MAXLEN 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XADD_MAXLEN 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xadd_maxlen-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![Stream XADD_MAXLEN 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xadd_maxlen-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f128-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![Stream XADD_MAXLEN 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xadd_maxlen-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-104857600-k8-f1024-20261004/)

### XRANGE - +

#### 64 KiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE_FULL 64 KiB/key, 128 B, 64 keys](charts/stream-65536-128-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f128-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-65536-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE_FULL 64 KiB/key, 1024 B, 64 keys](charts/stream-65536-1024-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-65536-k64-f1024-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-65536-k64-f1024-20261004/)

#### 1 MiB/key

128 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE_FULL 1 MiB/key, 128 B, 64 keys](charts/stream-1048576-128-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f128-20261004/)

1024 B/entry · 64 keys · Measured main baseline `a565d603`

![Stream XRANGE_FULL 1 MiB/key, 1024 B, 64 keys](charts/stream-1048576-1024-k64-xrange_full-current.png)

[Redis](raw/redis/) · [Valkey](raw/valkey/) · [Kvrocks (80 GiB cache)](raw/kvrocks/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-1048576-k64-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-1048576-k64-f1024-20261004/)

#### 100 MiB/key

128 B/entry · 8 keys · Measured main baseline `a565d603`

![Stream XRANGE_FULL 100 MiB/key, 128 B, 8 keys](charts/stream-104857600-128-k8-xrange_full-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f128-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-104857600-k8-f128-20261004/)

1024 B/entry · 8 keys · Measured main baseline `a565d603`

![Stream XRANGE_FULL 100 MiB/key, 1024 B, 8 keys](charts/stream-104857600-1024-k8-xrange_full-current.png)

[Redis](raw/redis-100m/) · [Valkey](raw/valkey-100m/) · [Kvrocks (80 GiB cache)](raw/kvrocks-100m/) · [Lavik main a565d603](raw/lavik-maina565d603-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik PR #265 7586dc6f](raw/lavik-candidate7586dc6f-ordered-stream-104857600-k8-f1024-20261004/) · [Lavik draft PR #270 1e87107e](raw/lavik-candidate1e87107e-ordered-stream-104857600-k8-f1024-20261004/)

## Measurement and reproduction

memtier runs on the separate client 172.16.0.5 pinned to CPUs 0–15, with uniformly random keys. HGET/HSET, SISMEMBER, LINDEX/LSET, ZSCORE/ZINCRBY and one-ID XRANGE rotate through eight evenly spaced positions per key, not all fields uniformly. SADD/SREM uses a fixed test member; XADD MAXLEN appends new IDs. Connection points run sequentially within a condition, so later writes inherit values/layout changed by earlier points.

Hash/Set use 50,000 keys at 1 MiB/key and 500 at 100 MiB/key; high-key-count LSET uses the same counts. Other ordered-structure conditions retain the matched 64/8-key peer workloads, explicitly identified in titles. Different key counts are not interchangeable.

Hash/Set use independent RESTORE seeding, transaction cleanup and recovery before measurement. High-key-count LSET seeds with 32 clients, 128 KiB RPUSH batches and pipeline=4. Fill timings remain in raw directories; RESTORE timings are not equated with peer HSET/SADD import timings.

Low-throughput whole-key reads can complete few replies in eight seconds; small differences are not performance conclusions. Eight successful seconds do not establish sustained memory stability: an earlier sustained SMEMBERS run exhausted memory admission. Failed points remain gaps with annotations, never zeroes or interpolated values.

Historical optimization evidence remains in raw/ and diagnostics/; merged PRs are not shown as separate series.
