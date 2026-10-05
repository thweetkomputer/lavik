# ZSet score views: complete 96-observation comparison

Frozen parent `4610d607` versus candidate `9d1ffc85`; three A/B, B/A, A/B rounds, 30 seconds per observation, pipeline 1, 12 workers. Large: 100 MiB/key, 1024 B members, 8 keys. Small: 64 KiB/key, 128 B members, 64 keys. Each read pair restarts on the same fresh parent-seeded logical population, not an immutable disk snapshot. Each write condition has its own fresh seed; concurrency levels within a condition run ascending and inherit physical write history.

All 96 observations passed source/binary identity, per-key cardinality, request/result, zero-error and clean-exit checks. INFO command counters account for exactly the reported workload requests, with zero failed/rejected calls; no seed or opposite operation leaked into the measured intervals.

## Paired changes

Percentages below are medians of three within-round ratios, not ratios of independent medians. Negative p99 is better. Counts show positive-QPS pairs / total pairs. No confidence intervals are claimed.

| Size | Command | Clients | QPS median | QPS range | Positive pairs | p99 median | p99 range |
|---|---|---:|---:|---:|---:|---:|---:|
| Small | ZINCRBY | 80 | +1.66% | -2.25% … +9.29% | 2/3 | -3.47% | -11.28% … +2.66% |
| Small | ZINCRBY | 320 | -0.22% | -2.82% … +6.47% | 1/3 | +0.72% | -2.84% … +2.16% |
| Small | ZINCRBY | 2560 | +2.27% | -0.58% … +7.88% | 2/3 | -2.05% | -6.12% … -1.42% |
| Small | ZINCRBY | 5120 | +2.87% | +1.02% … +8.90% | 3/3 | -1.34% | -8.16% … +0.71% |
| Small | ZSCORE | 80 | +12.61% | +9.05% … +12.82% | 3/3 | -11.35% | -11.57% … -8.02% |
| Small | ZSCORE | 320 | +27.27% | +22.95% … +28.21% | 3/3 | -44.88% | -54.01% … -43.90% |
| Small | ZSCORE | 2560 | +31.98% | +24.64% … +32.42% | 3/3 | -23.05% | -24.82% … -21.38% |
| Small | ZSCORE | 5120 | +22.21% | +17.32% … +25.23% | 3/3 | -20.00% | -22.70% … -18.15% |
| Large | ZINCRBY | 80 | -1.10% | -3.02% … +2.94% | 1/3 | -0.48% | -0.95% … +0.48% |
| Large | ZINCRBY | 320 | +0.24% | -3.70% … +2.68% | 2/3 | -1.49% | -1.49% … +2.24% |
| Large | ZINCRBY | 2560 | -0.76% | -2.19% … +1.76% | 1/3 | +6.67% | -14.80% … +33.71% |
| Large | ZINCRBY | 5120 | -1.62% | -5.49% … +1.27% | 1/3 | -4.23% | -9.68% … +35.07% |
| Large | ZSCORE | 80 | +16.27% | +11.96% … +17.13% | 3/3 | -16.70% | -17.84% … -15.97% |
| Large | ZSCORE | 320 | +19.82% | +17.08% … +23.45% | 3/3 | -13.87% | -25.43% … -7.11% |
| Large | ZSCORE | 2560 | +17.08% | +12.52% … +20.37% | 3/3 | -15.24% | -17.41% … -9.57% |
| Large | ZSCORE | 5120 | +14.45% | +12.71% … +18.32% | 3/3 | +2.40% | -21.98% … +3.11% |

## Disposition

ZSCORE gains QPS in all three pairs at every tested size and concurrency. Small-object QPS medians improve 12.61%–31.98%, with p99 improving in every pair. Large-object QPS improves 14.45%–19.82%; large c5120 p99 worsens in two pairs (median +2.40%). These read gains justify retaining #280 as a candidate.

Writes do not show a general improvement or prove neutrality. Large-object ZINCRBY QPS medians are −1.10%/+0.24%/−0.76%/−1.62%; large c2560 p99 worsens +6.67%. Small-object write QPS medians are +1.66%/−0.22%/+2.27%/+2.87%; only c5120 gains QPS in every pair. Small c320 p99 worsens in two pairs (median +0.72%).

#280 remains draft. The rebased head `a5c825e9` has an unresolved SetIndirect RESTORE timeout in arm64 CI; the historical binary comparison does not validate that head. [Failure evidence](../grouped-expiry-recovery-20261004/rebase-ci-failures-20261005.md). [All four independent ZSCORE perf captures](zset-score-views-perf.md) are complete.

[Historical large-read peer comparison](zset-score-views-large-reads.md): candidate reaches 25.52%–55.88% of the fastest peer at corresponding concurrencies. Peers were not rerun and durability/cache configurations differ; no overall parity claim.

## Reproduction and evidence

[Immutable observations](zset-score-views-complete-observations.json) · [All pairs and exact binary hashes](zset-score-views-complete-summary.json) · [Command-counter audit](zset-score-views-complete-command-audit.json) · [File SHA-256 index](zset-score-views-complete-evidence-index.json)

Run `python3 summarize-zset-score-views.py --scope all --input zset-score-views-complete-observations.json --output /tmp/score-summary.json --report-root <report-directory>` and `python3 audit-zset-score-commands.py --input zset-score-views-complete-observations.json --output /tmp/score-commands.json --report-root <report-directory>` from this directory. Raw files in the index are included in the report branch.
