# Main a565d603 refresh and Stream write profile

The current baseline includes merged PRs #249, #258, #259, #260 and #262.
Each refreshed curve retains the exact binary hash and source commit. Conditions
not yet rerun keep explicitly labeled historical results; peers are historical
matched-workload observations with the persistence/cache differences stated in
the report. No parity with the other systems is established by this refresh.

The independent 100 MiB/key, 1 KiB-entry, 8-key XADD MAXLEN diagnostic records
all 12 serving workers at 99 Hz with 16 KiB DWARF stacks. One extra inactive
helper has no samples. It runs after the clean connection sweep on the recovered
dataset and is not a plotted throughput observation.

[Worker summary](main-stream-workers.json) assigns 11.36% self task-clock to
OrderedGroupDirectory::Apply, 5.19% to metadata chunk construction and 3.25%
to copying records into the temporary metadata vector. The denominator includes
polling, background work and kernel CPU; these are not request latency fractions.
[Recorder arguments, thread inventory and per-thread self profiles](stream-100m-profile/)
retain the measurement evidence. These hotspots motivate incremental validation
and index updates around Stream message insertion, which precedes trailing
node/group metadata. Candidate results are reported separately with correctness
checks and clean comparative runs.

## Large Sorted Set writes

The 100 MiB/key, 1 KiB-member, 8-key ZINCRBY diagnostic uses the same all-worker
method at 80 connections after its clean sweep. The [worker summary](zset-main-workers.json)
attributes 4.98% self task-clock to SipHash12, 2.82% to memmove and 2.66% to CRC.
[Recorded callchains](zset-siphash-callers.json) place 3.65% of total task-clock
in SipHash below Hash-leaf loading/decoding. These percentages include kernel,
background and polling CPU, and do not measure request latency or I/O waits.

The source first loads a requested member-index leaf for its old score, then
loads it again while preparing the updated leaf. Reusing a checked command-local
leaf may avoid decoding, hashing and copying the same members twice. That
hypothesis requires separate correctness and clean throughput validation.

[Server counter deltas](zset-main-io.json) cover 1,137,092 ZINCRBY commands and
include background storage work. They show 0.195 completed storage reads and
1.846 writes per command, with about 18.5 kB read and 21.6 kB written per
command (decimal byte ratios). These physical counters do not count logical
leaf loads: reads can be served from live write buffers or share larger reads.
They cannot establish how many disk operations a reused leaf would save.

[Recorder arguments, threads, metrics and self reports](zset-100m-profile/)
retain the diagnostic evidence. Diagnostic QPS is excluded from throughput curves.
