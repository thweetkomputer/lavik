# HSET phase timing, 2026-09-29

Diagnostic only: 500 keys × 100 MiB, 128 B values, 320 connections, pipeline 1,
12 workers, SPDK. The 25-second HSET run reached 43,817 QPS with zero errors.
It reused the validated `write-seed-hash-100m-k500-f128-20260929` dataset.

The diagnostic binary is PR #222's packed-index implementation (`4da91675`)
plus timing scopes, source `f2ca39f144a1694d1f00460f8087b030f619a28b`, SHA256
`8a92a4abacfbd2608adc93bb2d10b3fb8ea7b8f309805a5ff4d2cf66204c646a`.
The source is preserved on [the diagnostic branch](https://github.com/thweetkomputer/lavik/tree/bench/grouped-write-stages-20260929).
Run `run.py` with `LAVIK_WRITE_STAGES=1`; the committed provenance and command JSON
record the remaining arguments. These measurements are excluded from the formal QPS charts.

Weighted averages from each worker's last 4096-call checkpoint:

- Storage command interval: 728.5 µs; grouped commit interval within it: 669.7 µs.
- Predecessor decision check: 316.8 µs per call. This path checks twice per command,
  with the first check carrying the wait: approximately 0.63 ms per command.
- Selected-page read/decode: 34.4 µs; mutation planning: 5.3 µs.
- Foreground space-pressure coordination: 5.5 µs; auxiliary staging: 6.0 µs;
  root append/publication: 18.9 µs.

Scopes include coroutine suspension and measure wall time, not CPU cost. They
nest and have different checkpoint tails, so these averages must not be added
as an exact partition. The command interval starts inside storage after request
routing and key-lock acquisition; it excludes client/network and key-lock queue
latency. At this workload the predecessor-decision wait dominates the measured
storage interval. It does not establish that every wait is caused by the timer:
commit IO and scheduling also contribute. Local completion notifications are the
next experiment; the durable predecessor requirement stays in place.

[Stage samples](stages.txt) and [weighted summary](stage-summary.json) retain the
per-worker counts and maximum wall times for inspection.
