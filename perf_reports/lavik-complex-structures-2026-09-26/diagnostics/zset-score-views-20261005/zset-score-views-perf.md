# ZSCORE score-view perf: completed large and small read comparisons

Four separate captures follow the completed 96-point clean benchmark. Each size uses one fresh parent-seeded logical population, with parent `4610d607` then candidate `9d1ffc85` restarted separately and no intervening writes. Large: 100 MiB/key, 1024 B members, 8 keys, c5120. Small: 64 KiB/key, 128 B members, 64 keys, c320. All captures passed binary/source identity, all-key cardinality, command and clean-exit checks.

Each capture attaches all 13 threads (12 workers plus one zero-sample helper), at 99 Hz task-clock with 16 KiB DWARF stacks for 25 seconds. The before/after metric window spans a separate 30-second workload interval. All sampled threads report zero lost samples. Do not divide sampled CPU by this differently timed command count or treat the instrumented runs as clean QPS measurements.

## Reported CPU self shares

Shares are weighted by each thread’s approximate event count. They include polling, background work and kernel time. Per-thread reports retain symbols above 0.1% and round to two decimals; missing mass is not renormalized. Symbol matching is explicit: `::SipHash12(`, names beginning `__memmove`, and mimalloc names beginning `_mi_` or `mi_`. These are neither allocation counts nor copied-byte counts.

| Scope | Revision | SipHash12 | memmove | mimalloc | Worker::RunOnce | Report coverage |
|---|---|---:|---:|---:|---:|---:|
| Large c5120 | parent | 6.371% | 0.907% | 1.991% | 20.295% | 88.811% |
| Large c5120 | candidate | 3.891% | 0.953% | 1.915% | 17.210% | 89.652% |
| Small c320 | parent | 12.420% | 0.579% | 3.265% | 3.502% | 86.411% |
| Small c320 | candidate | 7.754% | 0.196% | 1.170% | 2.440% | 86.834% |

Small-object results are consistent with the change’s intended reduction in duplicate hashing, owning entries and copies: SipHash self share falls 12.420% → 7.754%, mimalloc 3.265% → 1.170%, and memmove 0.579% → 0.196%. Large-object SipHash also falls 6.371% → 3.891%, but mimalloc is nearly unchanged and memmove slightly increases. The large result does not support a general claim that every copying/allocation hotspot fell. Changes in shares alone do not establish absolute CPU savings or their contribution to QPS.

## Storage counters

| Scope | Revision | ZSCORE calls | Read operations / call | Read bytes / call | Writes in window |
|---|---|---:|---:|---:|---:|
| Large c5120 | parent | 5230863 | 1.000000 | 6471.233 | 0 |
| Large c5120 | candidate | 6125061 | 1.000000 | 6471.349 | 0 |
| Small c320 | parent | 12564876 | 1.000000 | 6783.998 | 0 |
| Small c320 | candidate | 16096986 | 1.000000 | 6783.998 | 0 |

Both versions issue one measured read operation per ZSCORE and nearly identical bytes per call; neither writes during these windows. This supports a CPU/memory-path improvement without a reduction in the measured storage-read demand. These server-wide counters include boundary overlap/background activity and are not exact per-request traces.

Clean throughput conclusions remain in the [96-point paired comparison](zset-score-views-complete.md): read gains are consistent, write controls are mixed, and large c5120 read p99 regresses in two pairs. No overall peer parity is established. #280 remains draft because the rebased-head SetIndirect RESTORE timeout is unresolved.

## Evidence

[Profile identities and methods](zset-score-views-profiles.json) · [Per-thread symbols and counters](zset-score-views-self-comparison.json) · [Selected exact metrics](zset-score-views-perf-metrics.json) · [SHA-256 evidence index](zset-score-views-perf-evidence-index.json)

Run `python3 summarize-zset-score-self.py --input zset-score-views-profiles.json --report-root <report-directory>` beside this report to regenerate the aggregates from committed small self reports and metric scrapes. Raw `.perf` captures and full stacks remain at their recorded local diagnostic paths and are not included in the published file index.
