# HSET write-path diagnostic, 2026-09-29

This is a diagnostic follow-up, not another code variant in the main/PR charts.
All three runs used the PR #212 binary (`d3f09324`), SPDK, 64 Hash keys of
1 MiB each, 128 B values, 320 connections, pipeline 1, and the same host and
scratch NVMe devices as the report. Each run recreated and filled the dataset.

| Run | HSET duration | TxCleaner during HSET | QPS | p99 |
|---|---:|---|---:|---:|
| `profile-hset` | 30 s | enabled | 9,297 | 284.67 ms |
| `info-hset` | 15 s | enabled | 9,313 | 282.62 ms |
| `cleaner-off-hset` | 15 s | disabled with `CONFIG SET tx-cleaner-cooldown-ms 0` after HGET | 9,327 | 284.67 ms |

The 15-second cleaner-on/off difference is 0.15%, below what one run can
resolve. In `info-hset`, the HSET interval raised `tx_cleaner_rounds` from
488 to 727 and `tx_cleaner_retired_blocks` from 354 to 513. The transaction
commit queue peaked at 52, below its 4096 high watermark, and recorded zero
backpressure waits. The cleaner ran often, but disabling it for this short
measurement did not improve throughput or tail latency. This does not establish
long-run behavior or explain the 100 MiB case.

The 12-second [CPU profile](perf.data) captured 7,682 samples **during the
30-second HSET interval**. Its [symbol report](perf-report.txt) attributes
46.52% of on-CPU samples to `bycorf::Worker::RunOnce` and 18.47% to
`bycorf::Worker::PollStorage`; these include busy polling. CPU sampling does
not measure time waiting for IO or identify a dominant wall-clock HSET stage.

With the same 1 MiB/128 B value and 320 connections, a separate 15-second
`key8-hset` run changed only the hot-key count from 64 to eight. HSET fell to
2,316 QPS (p99 342.01 ms). This is close to the roughly 2.3k QPS measured
for 100 MiB keys with eight hot keys in the main report. Thus the original
1 MiB versus 100 MiB HSET comparison changes both key size and hot-key count;
it cannot attribute that QPS difference to size. The code also waits for a
key's previous grouped commit decision before starting its successor, which
is consistent with the observed sensitivity to hot-key count. One run does not
measure the contribution of every wait stage.

The per-run command, result, provenance, and INFO snapshots are in this
directory. `run.py` was invoked with `--types=hash --sizes=1048576
--fields=128 --mode=point --levels=320`, with the durations, tags, and key
counts shown above. The cleaner-off setting applied only between that run's
HGET and HSET measurements; the server was stopped afterward.
