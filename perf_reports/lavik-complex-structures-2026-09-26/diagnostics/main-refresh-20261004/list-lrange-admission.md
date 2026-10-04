# List full-range admission failure

Measured main `5d7d12ec`, 8 keys of 100 MiB payload, 128-byte entries.
`LRANGE 0 -1` completes at 1 and 4 connections. At 16 connections, memtier
records `-OOM grouped operation scratch admission`; that observation is a
failure, even though memtier also reports throughput from completed replies.

- [Raw failure](../../raw/lavik-main5d7d12ec-ordered-list-104857600-k8-f128-20261004/list-104857600-128-lrange-c16.error.json)
- [Client output](../../raw/lavik-main5d7d12ec-ordered-list-104857600-k8-f128-20261004/list-104857600-128-lrange-c16.txt)
- [INFO after the observation](../../raw/lavik-main5d7d12ec-ordered-list-104857600-k8-f128-20261004/list-104857600-128-lrange-c16.info-after.txt)

The source explains how admission can reject before exhausting host RAM:

1. [Grouped List execution](https://github.com/eloqdata/lavik/blob/5d7d12ec064d562955531cfc1fabf1e13d779f02/src/storage/engine/grouped_list.cpp#L277) budgets every selected page and requests four copies of that scratch estimate. Full-range reads select all pages. The implementation then retains decoded pages and copies selected values into the reply.
2. [Scratch estimation](https://github.com/eloqdata/lavik/blob/5d7d12ec064d562955531cfc1fabf1e13d779f02/include/lavik/storage/detail/grouped_scratch.h#L105) includes payload bytes plus 256 bytes per entry, before that multiplier. An 819,200-entry list therefore has a much larger temporary reservation than its 100 MiB payload alone.
3. [Worker admission](https://github.com/eloqdata/lavik/blob/5d7d12ec064d562955531cfc1fabf1e13d779f02/src/memory.cpp#L240) compares retained and pending bytes against the worker's equal share of 90% of maxmemory. Other workers' unused shares are not borrowed here. Concurrent requests assigned to the same owner can exhaust its reservation budget.

The post-observation INFO has maxmemory 100.63 GiB and process RSS 4.39 GiB;
it is not an instantaneous sample of the rejected reservation or peak RSS.
These observations establish a worker-budget rejection, not an OS OOM kill.
Exact per-worker pending bytes at the rejection were not sampled, so the
number and overlap of reservations remain an inference from the code.

The server exits normally. [Continuation provenance](../../raw/lavik-main5d7d12ec-ordered-list-104857600-k8-f128-20261004/resume.json) records a restart on the same retained dataset, validation of all 8 keys, and execution of only the missing LINDEX/LSET points. Both successful LRANGE observations and its failure remain unchanged. The report draws a gap at 16 connections.
