# 100 MiB HGETALL admission failure

Both Lavik main and PR #212 returned `OOM grouped operation scratch admission`
at 16 connections for a 100 MiB Hash with 128 B values. The server returned
this error after serving successful requests; this is Lavik's memory admission
check, not evidence that the Linux OOM killer terminated the process. The
[main error](../../raw/lavik-main-20260929-100m/hash-104857600-128-hgetall-c16.error.json)
and [PR error](../../raw/lavik-opt-20260929-100m/hash-104857600-128-hgetall-c16.error.json)
retain the client output. Both builds completed the one- and four-connection
points.

The current HGETALL path selects **all groups of the requested Hash key** in
`src/storage/engine/hash_tree.cpp`, adds each group's physical bytes plus
256 bytes per field to `GroupedScratchBudget`, then reserves four times that
sum before reading the first group. `LoadGroupedHashValue` subsequently
decodes the groups and accumulates every field in one result, which the Redis
command encodes as a full reply. A point HGET selects only the group
containing its requested field. The fourfold multiplier is admission headroom
for temporary allocations, not four physical reads of each group.

The logical 100 MiB / 128 B input has 819,200 fields. Ignoring record framing,
field names, and the budget's 4 KiB base, the reservation is at least
`4 × (100 MiB + 819,200 × 256 B) = 1.172 GiB` per concurrent HGETALL.
The actual reservation is larger. Lavik's default memory limit on this host
is 80% of 125.785 GiB of RAM; its steady admission limit is 90% of that,
or 90.565 GiB. Admission is divided among 12 workers, giving each about
7.547 GiB before retained memory, other pending reservations, and full-sync
reservations. Six concurrent HGETALL operations on one worker consume at
least 7.031 GiB of that allowance. The eight tested keys route to only four
workers, two keys each, so the 16-connection workload can concentrate
reservations on one worker.

The exact retained and pending bytes at the rejected call were not captured.
The error string proves the admission rejection; the calculation and key
mapping explain why the failure is plausible at this concurrency. It does
not prove the precise worker occupancy at the instant of rejection. A
streaming HGETALL implementation that bounds decoded groups and reply
buffering would need a separate design and measurement.
