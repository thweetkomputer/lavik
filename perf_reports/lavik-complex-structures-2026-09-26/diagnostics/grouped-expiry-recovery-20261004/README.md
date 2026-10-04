# Full-device grouped expiration: CI diagnosis and repair

[PR #268](https://github.com/eloqdata/lavik/pull/268) fixes a main recovery failure encountered while validating the performance PRs. Current #266 and #267 heads also include the repair and the shared Meta test-fixture corrections. Combined-head CI passed for all three PRs; the published performance binaries remain `a1b24b60` and `ff9e3655` respectively.

## Root cause

The test reported a startup timeout, but the preserved log shows the server had exited with `ordered root/page count mismatch`. This occurred on arm64 and amd64. The original CI amd64 binary reproduced it on the first local attempt with a regular file-backed 96 MiB device. A main-based diagnostic build reproduces the same failure on the saved image: an expired, unshielded String root declares 113 pages, while only 32 candidate records remain. [Diagnostic log](expiry-image-diagnostic-full.txt).

Full-device expiration can retire an unshielded grouped value without first appending a tombstone. Its children may be reclaimed while the expired root survives in a block shared with live records. Recovery must select that root before considering its expired graph; choosing an older value instead would be wrong.

The repair discards an unreconstructable graph only for an expired, unshielded winner with startup expiration authority. It queues a fresh tombstone after allocator recovery. Live/shielding roots still fail on missing pages, and admission/I/O errors remain failures. Complete expired graphs keep the normal durable-deletion path. The pre-existing full-device exception still relies on the expiry deadline if no tombstone can be written.

## Verification

- [New fixture against pinned main: expected failure](expiry-fixture-before.txt); [same fixture after repair](expiry-fixture-after.txt). It covers incomplete Hash/List graphs, live/shielding rejection, unrelated data, counters and a subsequent injected recovery-clock rollback.
- [28 recovery tests pass](expiry-fix-recovery-tests.txt).
- [103 grouped command tests pass; one opt-in >1 GiB RDB case skipped](expiry-fix-ordered-tests.txt).
- [TTL suite passes](expiry-fix-ttl-tests.txt), including deferred expiration authority; [shielded older-value regression passes](expiry-fix-shielded-test.txt).
- [Ten file-backed repetitions pass](expiry-recovery-fixed-repeat.txt). The companion JSON records only the last repetition.
- [Actual failed image repaired](expiry-image-repaired.json): the exact 900 KiB replacement is intact, expired keys are absent, and `DBSIZE=1`; clean restart with the recovery clock forced to zero also passes.
- [Build/test proof and fixture rechecks](validation.json).

The Sentinel protocol fixtures now wait for discovery authority, not merely Raft leadership. Discovery checks pass 20 repetitions plus all 15 tests with the original CI amd64 binary. Partition gates allow the existing uncertain-command disconnect only after the explicit fault cut, matching the controlled lease-fence gate; three one-way and one two-way runs pass. Neither fixture change alters service behavior.

The earlier arm64 native-FULL timeout has not recurred in subsequent completed runs. Local amd64 repeats do not establish its arm64 root cause. The subsequent combined-head CI passes all software shards on both architectures.

## Report provenance repair

The reply-reservation publisher incorrectly reused the first List-stage directory. [Repair record](list-report-layout-repair.json) documents restoring all 67 first-stage files from the commit before that publication and moving second-stage material into its intended directory. Raw QPS data and curves are unchanged. [First stage](../list-read-window-20261004/README.md) and [second stage](../list-reply-reserve-20261004/README.md) now retain distinct comparisons and CPU profiles.

## CI confirmation

[Initial recovery-fix CI](https://github.com/eloqdata/lavik/actions/runs/37229779333) at `89d0b136` passed 11 of 12 software shards, including all six arm64 shards. Both architecture shard-0 jobs passed all 291 tests, including the previously failing grouped ordered suite. The remaining amd64 shard failed `SentinelTest.test_discovery_null_contract_on_bootstrap_leader` with `RESP connection closed`: it sent discovery commands before the elected leader had discovery authority. [Job outcomes](pr268-first-ci.json) retain the failed overall result.

PR #268 now includes the already validated Meta test fixture corrections from #266/#267 at head `5c0deb3e`; the recovery implementation remains `89d0b136`. [Combined-head CI](https://github.com/eloqdata/lavik/actions/runs/37231917942) passed all 12 software shards on amd64/arm64, both builds and formatting. [Recorded job outcomes](pr268-5c0-ci.json).
