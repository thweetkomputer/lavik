# Rechecking small eight-second write differences

Each condition was seeded once with main on fresh media, then recovered in main → PR → PR → main order at 320 connections for 30 seconds per point. Writes change the data and physical layout between runs; ABBA reduces simple order drift but does not provide confidence intervals. These diagnostic repeats do not replace the independent fresh-seed eight-second main/PR curves.

## Set: 50,000 × 1 MiB keys, 1024 B entries

Main: 214.6–215.4k QPS. PR: 213.3–214.9k QPS. The ratio of their two-run means is 0.9959. The small decline in the fresh-seed eight-second grid was not reproduced here; this also does not establish an improvement.

[0: main raw](../../raw/lavik-recheck-abba-0-main-set1m-k50000-f1024-20261001/) · [1: pr raw](../../raw/lavik-recheck-abba-1-pr-set1m-k50000-f1024-20261001/) · [2: pr raw](../../raw/lavik-recheck-abba-2-pr-set1m-k50000-f1024-20261001/) · [3: main raw](../../raw/lavik-recheck-abba-3-main-set1m-k50000-f1024-20261001/) · [Seed](../../raw/lavik-recheck-seed-main-set1m-k50000-f1024-20261001/).

## Hash: 50,000 × 1 MiB keys, 128 B entries

Main: 148.1–150.3k QPS. PR: 148.8–149.1k QPS. The ratio of their two-run means is 0.9988. The small decline in the fresh-seed eight-second grid was not reproduced here; this also does not establish an improvement.

[0: main raw](../../raw/lavik-recheck-abba-0-main-hash1m-k50000-f128-20261001/) · [1: pr raw](../../raw/lavik-recheck-abba-1-pr-hash1m-k50000-f128-20261001/) · [2: pr raw](../../raw/lavik-recheck-abba-2-pr-hash1m-k50000-f128-20261001/) · [3: main raw](../../raw/lavik-recheck-abba-3-main-hash1m-k50000-f128-20261001/) · [Seed](../../raw/lavik-recheck-seed-main-hash1m-k50000-f128-20261001/).
