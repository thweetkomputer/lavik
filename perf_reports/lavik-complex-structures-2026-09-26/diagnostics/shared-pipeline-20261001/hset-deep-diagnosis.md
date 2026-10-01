# HSET: work remaining after commit pipelining

## Scope and sampling quality

PR #235 `09871950`, 500 × 100 MiB Hash keys, 1 KiB values, 1,280 connections. This is a separate CPU/I/O diagnostic on recovered data previously mutated by the same binary. Its 110.4k sampled QPS is **not** a replacement for the clean main/PR curves, and the difference from the earlier diagnostic cannot establish a code change. No code changed and no peer server was rerun.

The first process-wide DWARF profile retained valid self symbols, but 68.8% of weighted samples had no decoded callchain; only one worker provided user stacks. Zero lost samples did not imply complete unwinding. A second explicit multi-thread recording reproduced that limitation. The first second-pass run also hit an offline `perf script` TIME-field export error after measurement; it is not used as a validated benchmark. Recording each worker separately at 99 Hz for 25 seconds resolves attribution on all **12 active workers**: 74.6% of task clock has user stacks and 25.4% has kernel stacks, with no missing callchains in the decoded output. One idle helper has no samples. Original perf binaries and full stacks remain in the benchmark workspace.

[Original coverage audit](hset-unwind-coverage.json) · [Per-worker CPU/caller summary](hset-perworker-summary.json) · [Validated per-worker run](../../raw/lavik-diagnostic-perworker-pr235-hash100m-k500-f1024-20261001/).

## Concrete CPU costs

Percentages below are mutually distinct self-symbol samples where described, using all-thread task clock. Ancestor attribution is inclusive and must not be added to self costs. Coroutine scheduler boundaries and compiler folding can obscure a caller; generic allocation symbols with unrelated demangled aliases are not evidence of executing those libraries.

- Hash route lookup: 2.34%; physical record lookup (`FindRecord`): 3.59%; routing-map `SetNode`: 2.02%; physical-index `UpdatePhysical`: 2.02%. These four self symbols total about **10.0%**.
- Mimalloc-family symbols, including allocation/free/maintenance: about **8.2%**. Recorded ancestors associate **2.61%** of all CPU with physical-index allocation and **1.85%** with routing-map allocation. This is about 4.5% of total CPU inside those allocator samples, not an additional charge on top of 8.2%.
- Of physical record lookup, foreground Hash execution accounts for 1.76% of total CPU, relocation for 1.17%, and old-record retirement for 0.48%. Thus relocation/retirement explain about **46% of this lookup hotspot**, not 46% of the complete workload.
- `memmove`: 1.70%; worker `RunOnce`: 10.76%; `PollStorage`: 4.92%. Polling is not a disk-wait duration measurement. The profile does not support saying copies of the complete 100 MiB Hash dominate HSET.

## Work performed by one changed field

Lavik already avoids materializing the complete Hash. [Hash command path](https://github.com/eloqdata/lavik/blob/09871950738abb3909eb3706a5ee8f17a69f8ed5/src/storage/engine/hash_tree.cpp) routes requested fields and loads the affected leaf. The leaf editor scans/validates that leaf, builds temporary entry/position state, and encodes a complete replacement leaf; ordinary targets are at most 8 KiB before indivisible-entry/collision exceptions. The old and new pages are not a value cache.

Publication still applies the routing metadata through a persistent AVL update, then copies the affected physical-index paths and creates a new immutable object view. Routing entries currently also contain per-page revision and transaction metadata. An overwrite with unchanged field count and byte length therefore still updates that metadata path; blindly sharing the previous path would violate existing physical/route validation. See [leaf edit](https://github.com/eloqdata/lavik/blob/09871950738abb3909eb3706a5ee8f17a69f8ed5/src/storage/engine/grouped_hash.cpp), [persistent map update](https://github.com/eloqdata/lavik/blob/09871950738abb3909eb3706a5ee8f17a69f8ed5/include/lavik/storage/detail/grouped_hash.h), and [physical publication](https://github.com/eloqdata/lavik/blob/09871950738abb3909eb3706a5ee8f17a69f8ed5/src/storage/engine/grouped_object_index.cpp).

The read/admission/publication path also performs repeated physical lookups. Some rechecks protect relocation while I/O suspends; a safe fast path must preserve the captured allocation epoch, logical-version validation, failure propagation and pinned snapshot lifetimes. These are candidates for reducing work, not proof that all checks are redundant.

Kvrocks' measured source is `28440b5cba12a791b058713cbbae4ef86fbf37a2`: [Hash::MSet](https://github.com/apache/kvrocks/blob/28440b5cba12a791b058713cbbae4ef86fbf37a2/src/types/redis_hash.cc) checks requested fields and writes their individual internal keys. For a persistent existing field update with unchanged TTL, Hash metadata need not be rewritten. It does not rebuild a Lavik-style Hash group snapshot. Its measured WAL-disabled/cache configuration and deferred LSM flushes differ from Lavik's durable acknowledgement; the complete QPS gap cannot be assigned to CPU costs alone.

## I/O and remaining uncertainty

The validated diagnostic completed 3,316,367 HSET commands. The metrics window records 5,252,163 writes / 39,852,228,608 bytes and 824,306 reads / 32,680,593,920 bytes: approximately **1.58 writes, 12.0 KB written, 0.25 reads and 9.9 KB read per completed command**. These include background cleanup/relocation and omit the final shutdown drain. They are device totals divided by completed commands, not a foreground-only write-amplification or read-latency decomposition. SPDK fdatasync-labelled counters cover the same writes; do not add them again. [I/O calculations](hset-perworker-io.json).

Commit pipelining removes an earlier foreground dependency wait. It does not remove group read/modify/rewrite, persistent metadata paths, retirement, cleanup, or durability work. CPU stacks do not measure coroutine suspension time. The CPU evidence prioritizes repeated physical lookup and routing/physical metadata allocation; attributing the rest of the gap requires command-stage timing for page read, publication, admission and commit completion, plus separate foreground/background I/O counters. No specific share of the gap is claimed for unmeasured waits.
