# Main XRANGE full-range profile

Pinned main `a565d603`, 100 MiB nominal payload/key, 128-byte values, eight keys, one connection. This is a separate diagnostic after the clean throughput grid; its throughput is not included in QPS figures.

[Weighted profile analysis](stream-range-main-profile.json) · [samples, command result and counters](profile/) · [binary proof](source-build-verification.json) · [host restoration](stream-range-main-host.json).

The 30-second diagnostic counter interval completes eight XRANGE commands with 156,058 physical reads and no physical writes: about **19,507 reads and 168.4 MB read per command**. The separate 25-second task-clock sample contains 30.54 aggregate CPU-seconds across worker threads. These different intervals must not be divided to claim exact CPU cost per command.

| Sampled self CPU | Share |
| --- | ---: |
| Worker::RunOnce | 29.97% |
| Worker::PollStorage | 11.02% |
| _mi_theap_malloc_zero | 1.39% |

Shares include polling, background activity and kernel work; they are not latency fractions. Source inspection shows that the range loop awaits each selected page before starting the next. Together with the read count, this motivates testing bounded overlapping reads and reducing repeated per-page scheduling/admission work. It is a hypothesis for the next optimization, not a measured speedup.

## Retained population and validation

The source grid finishes with `XADD MAXLEN ~`, so its retained keys contain 819,207–819,284 entries rather than the initial 819,200. Both [before](stream-104857600-128.validated.json) and [after](stream-104857600-128.after.json) cardinalities are identical. The first diagnostic attempt exposed a runner inconsistency: it accepted the bounded post-write population before a reused read-only run, then demanded the exact original seed afterward. The runner now applies the same bounded admission and requires unchanged actual counts for read-only reuse. This successful rerun records all provenance and exits cleanly.

SPDK was rebound without discarding the preceding dataset and restored afterward. No build, tests, clean throughput run, or other profiler ran concurrently. Raw perf recordings and stacks remain local; only summaries, self reports, counters and structured provenance are published.

## Reply-path follow-up

The sampled `StreamRangeReplyState::Next` uses the pinned collection reader. For small messages it returns one encoded message fragment per call; `WriteReplyContinuation` performs a separate awaited socket write for each fragment. Grouped fields are first copied into owned strings, and the per-entry reply builder is then copied into `pending_`. This identifies repeated reply construction and scheduling in addition to page-read work. It is not the aggregate `ExecuteGroupedStreamRange` callback path.

[Draft PR #270](https://github.com/eloqdata/lavik/pull/270) at `1e87107e` proposes bounded 64 KiB coalescing, borrowed-field serialization and moving the builder buffer. Its follow-up tightens the wire-size reservation, accounts for tiny string capacity growth and removes the unused grouped field container. [Full CI](https://github.com/eloqdata/lavik/actions/runs/37234787576) passes both builds, all 12 software shards on amd64/arm64 and formatting ([recorded outcomes](pr270-1e-ci.json)). CI enables test faults; both architecture shard-0 jobs pass all 291 tests, including the grouped ordered suite. [Native production-binary validation](stream-reply-local-tests-passed.json) now passes: 14 Stream cases (including the large RDB round trip), one fault-only skip, five List/Stream blocking and recovery cases, and the pubsub/RESP3 driver. [The tested binary](stream-reply-versions.json) is the exact immutable candidate used for throughput. Four initial candidate sweeps and separate perf are recorded in the [reply-batching follow-up](../stream-reply-20261004/README.md). Paired stability checks remain pending. The measurements above remain main `a565d603`.
