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

## Large List range diagnosis

The refreshed `a565d603` 8 × 100 MiB List with 128 B elements repeats the historical 16-connection LRANGE failure: [raw error](../../raw/lavik-maina565d603-ordered-list-104857600-k8-f128-20261004/list-104857600-128-lrange-c16.error.json). The server reports `OOM grouped operation scratch admission`; successful responses from that errored point are not plotted as successful QPS. Post-run cardinalities validate and the server exits cleanly. The configured memory limit is about 100.6 GiB, with worker-local shares; this failure does not mean the host exhausted RAM.

Separate diagnostics record LRANGE at one connection and LSET at 80 connections: [range samples](list-range-main-workers.json), [write samples](list-write-main-workers.json), [range recorder and counters](list-100m-128-range-profile/), [write recorder and counters](list-100m-128-write-profile/), and [I/O summary](list-100m-128-io.json). These diagnostic QPS are not curve points.

The range interval completes 25 commands and records 353,125 physical reads (14,125 per command), with no physical writes. All-worker self task-clock assigns 42.22% to Worker::RunOnce and 30.76% to PollStorage, versus 2.09% to memmove. These shares include polling/background work and do not measure I/O-wait latency. Source inspection shows that range pages are loaded sequentially; the evidence motivates testing bounded concurrent page reads before focusing on small copy costs.

The read adapter also reserves four complete payload/entry budgets although it moves decoded strings into the reply without a second string payload copy. Physical read buffers are separately accounted. Read-only admission and bounded read concurrency are the next candidate changes; no improvement is claimed until the candidate is tested and measured.


[Large Stream XRANGE full-range diagnosis](../stream-range-main-20261004/README.md): about 19,507 physical reads per command; bounded read overlap is the next hypothesis to test. This separate profile is excluded from clean QPS curves.
