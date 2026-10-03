# Stream write diagnosis, October 3

Measured main `6111d0b1` and PR #247 `6562e3b8`, both independently built with Bycorf `62509c93`. No payload cache, durable format or shared mutex is added.

1. Main rebuilds and re-adjudicates the whole ordered candidate population on structural updates. It also re-sorts the complete identity/retirement indexes. Foreground Apply can instead validate the full chain against an adjudicated predecessor and only the command's replacements, merging existing identity order and retirement order with new records.
2. Stream trim plus append changes counts on distant pages. Runtime rank metadata uses persistent Fenwick partial sums, replacing only logarithmic cells per changed count. Full topology reconstruction still scales with page count. Unchanged page replacements retain the rank index; List/Sorted Set cumulative ranks keep their existing representation.

[Clean connection comparisons](../../stream-write-summary.json), [main build](main-build.json), [PR build](pr-build.json), [final tests](tests.json), [first-stage full ordered tests](first-stage-tests.json). Every plotted run verifies all keys before/after and exits cleanly with zero errors. Individual PNGs remain embedded in the bilingual report alongside Redis, Valkey and Kvrocks; 1 MiB uses 64 keys and 100 MiB uses 8 keys to match historical peer workloads.

[Main worker CPU summary](main-perworker-summary.json), [PR worker CPU summary](pr-perworker-summary.json). Each of the 12 worker TIDs was recorded separately at 99 Hz task-clock with a 16 KiB DWARF stack; an inactive helper may have zero samples. Percentages use all recorded worker task-clock, including polling, background and kernel work. They do not represent request latency. These 30-second diagnostic loads are separate from the clean 8-second curves. Raw self reports, thread inventories, exact recorder arguments, provenance and before/after metrics are in `main/` and `pr/`; large perf binaries/full stacks remain on the benchmark host.

These are single sweeps without confidence intervals. Historical peers have different persistence/cache/media settings; Kvrocks retains an 80 GiB cache. This does not establish parity under matched durability.

The current PR head includes a [documentation-only successor](documentation-successor.json); all measured code inputs are unchanged and curves retain their original `6562e3b8` source attribution.
