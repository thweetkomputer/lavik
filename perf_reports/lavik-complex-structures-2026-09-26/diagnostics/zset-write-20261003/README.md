# ZSet write diagnosis — October 3

Measured main `6111d0b1` and [PR #246](https://github.com/eloqdata/lavik/pull/246) `c9519328`. Each raw run records its actual source revision and binary SHA; earlier candidates remain excluded from the current curves.

## Removed work

- Redistribute already modified adjacent pages when feasible, preserving IDs and links. Real growth, distant moves and oversized members retain splitting/extent behavior.
- Decode unchanged neighbors only when their links change; admission and logical-view/GC/checksum checks remain required.
- Typed ZSet writers use checked member/old-score changes to prepare the prefix index, avoiding a second ordered before-image decode and a map entry for every unchanged member in replacement pages. Old membership and score checks in the prefix leaves, aggregate cardinality checks, encoder preflight and atomic dual-index publication remain required.
- Finish member preparation while command/pop/range names are alive. The returned private plan owns its page strings and admission; it retains no borrowed selected member names. Full-image callbacks/import keep complete before/after derivation. No payload cache, shared mutex or fixed batch cap is added.

## Clean results

- 100 MiB/key × 8 keys: ZINCRBY peak **9,423.92 → 37,565.19 QPS (+298.6%)**.
- 1 MiB/key × 64 keys: ZINCRBY peak **60,105.12 → 79,523.69 QPS (+32.3%)**.

These are one independently seeded eight-second sweep per version, without confidence intervals. Every key is checked before/after and every formal run exits cleanly with zero errors. ZSCORE and full ZRANGE remain plotted; no universal read improvement is claimed. The ZINCRBY throughput is still below historical Kvrocks (about 196k/211k QPS), whose persistence/cache settings differ. Shared typed-path coverage includes ZADD/ZINCRBY, ZREM, pop, range removal, GEO and EXEC. Their separate throughput gains have not all been measured; ZSTORE/full-image writers retain their distinct path.

[Source and per-connection comparisons](../../zset-write-summary.json), [main build](main-build.json), [PR build](pr-build.json), [tests](tests.json), [main worker summary](main-perworker-summary.json), [PR worker summary](pr-perworker-summary.json).

Final validation: pre-commit passed; Release and fault-enabled Debug builds completed before tests. The verified new binary passed 130 grouped/unit and 36 ordered/ZSet/import/crash-recovery tests, including a gate that fails old ordered-page member-diff reads: changed adds, score updates, removals, pop and EXEC range removal still succeed and recover. Compilation, tests, clean benchmarks and profiles run separately. Source overlays refresh modification times to force compilation; source byte equality is supplemented by a new-path binary marker check. A skipped-rebuild attempt was detected and discarded before any candidate data was published.

Profiles attach all 12 worker TIDs separately at 99 Hz task-clock with 16 KiB DWARF stacks for 25 seconds during a separate 30-second, 80-connection diagnostic load. Percentages include polling/background/kernel work and are not request-latency attribution; scheduler boundaries can truncate callers. Recover has no self samples on the candidate; Apply self is about 0.50%, versus 10.92% on main. Raw self reports, recorder arguments, thread inventories and metrics are in [main/](main/) and [pr/](pr/); full perf binaries/stacks remain on the host.

Workloads match existing peers: 1 MiB uses 64 keys, 100 MiB uses 8 keys, 1 KiB members, point connections 80/320/1280/2560/5120. Full reads use 16/80 and 1/4/16 respectively. Redis/Valkey do not persist; Kvrocks has WAL disabled and 80 GiB caches; Lavik persists on six SPDK NVMe devices without payload caching. Peer media epochs differ. PR #244 retains its measured older base `44761b91`; PR #247 is independently based on main `6111d0b1`.
