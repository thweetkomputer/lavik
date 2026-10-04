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
retain the measurement evidence. These hotspots motivate investigating incremental
validation and index updates for pure tail appends; candidate results will be
reported separately after correctness checks and clean comparative runs.
