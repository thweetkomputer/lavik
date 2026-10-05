# Full-device grouped expiration: CI diagnosis and repair

[PR #268](https://github.com/eloqdata/lavik/pull/268) fixes a main recovery failure encountered while validating the performance PRs. The current head is `cf895883`; [its CI](https://github.com/eloqdata/lavik/actions/runs/37294618671) is pending and **this head is not yet verified for merge**. [Observed head/job state](pr268-cf895883-ci-observation.json) retains the cancelled test shards from the superseded `e4f4da7c` run. Earlier green CI and native results below belong to their recorded commits and do not validate the later changes.

The `e4f4da7c` follow-up covers reclaimed extent identities on both Hash and ordered recovery paths, validates the selected graph before publication or live accounting, and waits for detached-root tombstones to become durable before readiness. Only tagged foreground disk exhaustion permits skipping that repair; admission, I/O and payload-checksum failures remain fatal. Added regressions cover reclaimed Hash/List extents and crash followed by clock rollback. `cf895883` then reorders the transient tombstone fields and their initializers to reduce padding; it does not intentionally change recovery behavior. Full validation of the final head remains pending.

#266 `138d39ac` includes main `741dc326` and the `e4f4da7c` repair. #267 `343e951e` still carries the earlier repair and has a distinct unresolved extent-test SET timeout; it remains draft. The published performance binaries remain `a1b24b60` and `ff9e3655` respectively. No new foreground-QPS result is inferred from recovery changes.

## Root cause

The test reported a startup timeout, but the preserved log shows the server had exited with `ordered root/page count mismatch`. This occurred on arm64 and amd64. The original CI amd64 binary reproduced it on the first local attempt with a regular file-backed 96 MiB device. A main-based diagnostic build reproduces the same failure on the saved image: an expired, unshielded String root declares 113 pages, while only 32 candidate records remain. [Diagnostic log](expiry-image-diagnostic-full.txt).

Full-device expiration can retire an unshielded grouped value without first appending a tombstone. Its children may be reclaimed while the expired root survives in a block shared with live records. Recovery must select that root before considering its expired graph; choosing an older value instead would be wrong.

The repair discards an unreconstructable graph only for an expired, unshielded winner with startup expiration authority. It queues a fresh tombstone after allocator recovery. The current implementation waits for that detached-root deletion to become durable before serving. Live/shielding roots still fail on missing pages, and admission/I/O errors remain failures. Complete expired graphs keep the normal durable-deletion path. The detached-root full-device exception relies on the expiry deadline only for confirmed foreground disk exhaustion.

## Historical verification of the initial repair

- [New fixture against pinned main: expected failure](expiry-fixture-before.txt); [same fixture after repair](expiry-fixture-after.txt). It covers incomplete Hash/List graphs, live/shielding rejection, unrelated data, counters and a subsequent injected recovery-clock rollback.
- [28 recovery tests pass](expiry-fix-recovery-tests.txt).
- [103 grouped command tests pass; one opt-in >1 GiB RDB case skipped](expiry-fix-ordered-tests.txt).
- [TTL suite passes](expiry-fix-ttl-tests.txt), including deferred expiration authority; [shielded older-value regression passes](expiry-fix-shielded-test.txt).
- [Ten file-backed repetitions pass](expiry-recovery-fixed-repeat.txt). The companion JSON records only the last repetition.
- [Actual failed image repaired](expiry-image-repaired.json): the exact 900 KiB replacement is intact, expired keys are absent, and `DBSIZE=1`; clean restart with the recovery clock forced to zero also passes.
- [Build/test proof and fixture rechecks](validation.json).

The Sentinel protocol fixtures now wait for discovery authority, not merely Raft leadership. Discovery checks pass 20 repetitions plus all 15 tests with the original CI amd64 binary. Partition gates allow the existing uncertain-command disconnect only after the explicit fault cut, matching the controlled lease-fence gate; three one-way and one two-way runs pass. Neither fixture change alters service behavior.

The earlier arm64 native-FULL timeout has not recurred in subsequent completed runs. Local amd64 repeats do not establish its arm64 root cause. The historical combined-head CI passed all software shards on both architectures; see the recorded heads below, independently of the current pending run.

## Report provenance repair

The reply-reservation publisher incorrectly reused the first List-stage directory. [Repair record](list-report-layout-repair.json) documents restoring all 67 first-stage files from the commit before that publication and moving second-stage material into its intended directory. Raw QPS data and curves are unchanged. [First stage](../list-read-window-20261004/README.md) and [second stage](../list-reply-reserve-20261004/README.md) now retain distinct comparisons and CPU profiles.

## Historical CI confirmation

[Initial recovery-fix CI](https://github.com/eloqdata/lavik/actions/runs/37229779333) at `89d0b136` passed 11 of 12 software shards, including all six arm64 shards. Both architecture shard-0 jobs passed all 291 tests, including the previously failing grouped ordered suite. The remaining amd64 shard failed `SentinelTest.test_discovery_null_contract_on_bootstrap_leader` with `RESP connection closed`: it sent discovery commands before the elected leader had discovery authority. [Job outcomes](pr268-first-ci.json) retain the failed overall result.

At historical head `5c0deb3e`, PR #268 included the validated Meta test fixture corrections from #266/#267, with recovery implementation `89d0b136`. [Combined-head CI](https://github.com/eloqdata/lavik/actions/runs/37231917942) passed all 12 software shards on amd64/arm64, both builds and formatting. [Recorded job outcomes](pr268-5c0-ci.json).
