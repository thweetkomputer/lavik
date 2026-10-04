# Ordered metadata CPU investigation — October 4

The main profile uses commit `5d7d12ec`, 8 Stream keys of 100 MiB payload,
1 KiB values and 80 connections running `XADD MAXLEN ~`. It is a separate
30-second diagnostic load after the clean connection sweep; its QPS is not
plotted as a throughput-comparison point.

[Main build](main-build.json) · [Worker CPU summary](main-workers.json) ·
[Recorder arguments and thread inventory](main/diagnostic-c80/)

The self samples assign 18.03% of recorded worker task-clock to
`OrderedGroupDirectory::Apply`. Metadata-array construction accounts for
6.33% in clearing `RecoveredOrderedGroup` chunks and 4.10% in copying them.
Clearing identity/rank chunks adds roughly 0.75%. These percentages include
polling, background and kernel CPU in the denominator; they are not request
latency fractions. Twelve serving workers are recorded individually at 99 Hz
with 16 KiB DWARF stacks; an additional inactive helper has zero samples.

The candidate constructs checked metadata directly, shares live metadata when
a tail append preserves existing ordinals, and shares unchanged retirement
metadata or appends monotonically ordered tombstones. Complete structural
chain validation and the fallback for shifted ordinals remain in place.
There is no field/page payload cache, durable format change, or new lock.
[Independent clean connection comparison](stream-100m-comparison.json) gives
XADD MAXLEN peak QPS of 10,100.19 on main and 11,217.83 on the candidate
(+11.1%). The 80-connection clean point does not improve. These are single
8-second sweeps, with no confidence intervals. They do not establish parity
with Kvrocks, whose persistence/cache settings differ.

[Candidate worker CPU](candidate-workers.json) assigns 11.25% self CPU to
Apply and 5.56% to direct metadata chunk construction. The candidate still
walks the whole structural chain. Profiles include idle/polling/background
work and are separate from the throughput sweeps.

## Correctness validation

Release and Debug/test compilation completed before running any tests.
[76 targeted unit tests](candidate-unit-tests.json) pass.
[Ordered E2E](candidate-ordered-e2e.json) has 101 passes, no failures and one
normal opt-in skip: the >1 GiB List RDB test requires a private 4 GiB image.
The executed suite covers >512 MiB Stream/ZSet data, restart/recovery,
concurrent pinned reads, RDB/transfer, failed writes and full-disk expiry.
No builds or tests overlap the clean throughput measurements.

The [1 MiB/key, 64-key comparison](stream-1m-comparison.json) uses the same
1 KiB entry size and independent seed. XADD MAXLEN peak rises from 46,163.04
to 50,510.09 QPS (+9.4%); read peaks are effectively unchanged in this sweep.
Both sizes appear in the main report with Redis, Valkey, Kvrocks, main and
[PR #249](https://github.com/eloqdata/lavik/pull/249) in each chart.
