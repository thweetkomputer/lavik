# Hash/Set write CPU profiles — October 4

[Main build](main-build.json): `5d7d12ec`, 12 workers, six SPDK NVMe devices.
Each profile uses 500 independently restored keys of 100 MiB payload,
1 KiB fields/members, 320 connections, pipeline 1 and a 30-second workload.
The 25-second, 99 Hz task-clock/DWARF captures attach to serving workers
individually. An additional inactive helper has zero samples.
Diagnostic QPS is excluded from the clean 8-second comparison curves.

## HSET

[Worker summary](hash-workers.json) · [Recorder, threads, metrics and raw self reports](hash/diagnostic-c320/)

Routing lookup (`HashGroupDirectory::Find`) accounts for 3.69% of all recorded
worker task-clock; persistent AVL path reconstruction (`SetNode`) for 3.28%.
Allocator work whose stacks contain the routing map accounts for 2.99%.
Whole-profile memmove is 2.16%, memset 0.81%, and kernel samples are 30.74%.
The implementation retains old directory views and copies the immutable AVL
search path on replacement, even when the route interval and field count do
not change. The sequence/location metadata does change, so simply mutating
the existing node would violate pinned-reader isolation.

## SADD/SREM

[Worker summary](set-workers.json) · [Recorder, threads, metrics and raw self reports](set/diagnostic-c320/)

SipHash12 accounts for 6.21%, memmove 2.91%, routing lookup 1.38%, AVL SetNode
1.16%, and kernel samples 40.51%. Members are 1 KiB; their bytes are hashed
for routing and leaf validation. This workload mixes additions/removals of
one member and can perform no-op commands; its QPS counts commands, not
actual durable changes.

These are sampled CPU shares, not request-latency fractions or an I/O wait
breakdown. Polling, background and kernel work are included. Allocator caller
attribution can be incomplete across coroutine boundaries and optimized code.
The observations identify remaining costs; they do not by themselves prove
an optimization's throughput benefit or quantify the durability/cache gap to
historical peer configurations.
