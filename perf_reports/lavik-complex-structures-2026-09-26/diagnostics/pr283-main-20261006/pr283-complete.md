# PR #283：rebase 后与 main 的完整配对对照

main `5a3903d9` 对比其直接子提交 `ace4198b`。24 个条件各三轮 A/B、B/A、A/B；配置 `--test-time=30`、pipeline=1、12 workers。高延迟时在途请求排空可延长实际运行，逐轮表保留客户端调用总耗时，精确 memtier duration 见命令核验 JSON。QPS 使用 memtier 报告值，不用请求数除以固定 30 秒。

读对共享新建父版本逻辑数据并分别重启，写对分别新建；不是不可变物理快照。ZADD CH 为八个成员的 0/1 分值切换，并发时可包含同分值 no-op，因此这里只报告命令吞吐。

绝对值为各版本三轮中位数，百分比为三轮配对变化的中位数，不能互换。QPS 越高越好，p99 越低越好；三轮不构成统计置信区间。其他系统未重跑；本表不能用于宣称整体追平。

| 数据字节 / 成员字节 / keys / 初始分值 | 命令 / 并发 | main QPS | #283 QPS | 配对变化 | main p99 ms | #283 p99 ms | 配对变化 |
|---|---|---:|---:|---:|---:|---:|---:|
| 65536 / 128 / 64 / distinct | ZADD / 80 | 108725.57 | 106382.39 | -2.16% | 8.511 | 8.959 | +5.26% |
| 65536 / 128 / 64 / ties | ZADD / 80 | 52234.86 | 53973.66 | +3.68% | 15.743 | 15.231 | -4.07% |
| 65536 / 128 / 64 / distinct | ZADD / 5120 | 101847.96 | 102187.98 | +0.67% | 415.743 | 417.791 | -0.49% |
| 65536 / 128 / 64 / ties | ZADD / 5120 | 45393.45 | 47090.58 | +5.21% | 970.751 | 946.175 | -3.80% |
| 65536 / 128 / 64 / distinct | ZINCRBY / 80 | 80315.48 | 82351.22 | +2.53% | 11.839 | 11.455 | -4.32% |
| 65536 / 128 / 64 / distinct | ZINCRBY / 320 | 80419.30 | 81863.37 | +1.80% | 33.791 | 35.071 | +3.01% |
| 65536 / 128 / 64 / distinct | ZINCRBY / 2560 | 77902.28 | 78302.36 | +0.51% | 268.287 | 268.287 | -0.76% |
| 65536 / 128 / 64 / distinct | ZINCRBY / 5120 | 77732.95 | 78952.70 | +1.57% | 544.767 | 528.383 | -3.01% |
| 65536 / 128 / 64 / distinct | ZSCORE / 80 | 357457.45 | 364151.52 | +1.87% | 0.367 | 0.391 | +6.54% |
| 65536 / 128 / 64 / distinct | ZSCORE / 320 | 561131.82 | 354478.00 | -36.12% | 1.143 | 5.119 | +315.15% |
| 65536 / 128 / 64 / distinct | ZSCORE / 2560 | 359131.10 | 376278.56 | +4.77% | 56.575 | 56.575 | +0.91% |
| 65536 / 128 / 64 / distinct | ZSCORE / 5120 | 337656.77 | 355315.18 | +4.45% | 118.783 | 111.103 | -5.31% |
| 104857600 / 1024 / 8 / distinct | ZADD / 80 | 66300.37 | 66321.32 | -0.98% | 5.951 | 6.111 | +2.69% |
| 104857600 / 1024 / 8 / ties | ZADD / 80 | 11.68 | 11.53 | -0.81% | 21626.879 | 22020.095 | +1.82% |
| 104857600 / 1024 / 8 / distinct | ZADD / 5120 | 67067.36 | 67007.29 | +1.22% | 294.911 | 214.015 | -15.04% |
| 104857600 / 1024 / 8 / ties | ZADD / 5120 | 75.44 | 76.45 | +1.34% | 239075.327 | 240123.903 | +0.44% |
| 104857600 / 1024 / 8 / distinct | ZINCRBY / 80 | 38524.27 | 38707.83 | +0.48% | 12.735 | 12.607 | -0.51% |
| 104857600 / 1024 / 8 / distinct | ZINCRBY / 320 | 41494.23 | 41681.96 | +0.45% | 31.615 | 31.487 | -0.40% |
| 104857600 / 1024 / 8 / distinct | ZINCRBY / 2560 | 42252.21 | 42090.51 | -0.48% | 202.751 | 195.583 | -3.47% |
| 104857600 / 1024 / 8 / distinct | ZINCRBY / 5120 | 44102.76 | 44379.92 | +0.53% | 366.591 | 393.215 | -1.54% |
| 104857600 / 1024 / 8 / distinct | ZSCORE / 80 | 294091.53 | 298446.86 | +1.22% | 0.487 | 0.463 | -4.93% |
| 104857600 / 1024 / 8 / distinct | ZSCORE / 320 | 326144.91 | 330515.20 | +0.67% | 3.023 | 2.911 | -3.70% |
| 104857600 / 1024 / 8 / distinct | ZSCORE / 2560 | 214107.86 | 222461.16 | +3.87% | 48.895 | 46.847 | -4.19% |
| 104857600 / 1024 / 8 / distinct | ZSCORE / 5120 | 202051.69 | 204820.73 | +1.06% | 98.303 | 89.599 | -8.85% |

## 调用总耗时的辅助吞吐口径

下面以完成请求数除以外层客户端调用秒数，包含远端启动、SSH 和请求排空，不能视为服务器单独吞吐。memtier 的 Runtime 与外层调用耗时分别保留，不假定二者相同；高排队测点尤其需要结合此表和 p99 审查。这里不更改上表的 memtier QPS 定义。

| 数据字节 / 成员字节 / keys / 初始分值 | 命令 / 并发 | main 请求/调用秒 | 候选请求/调用秒 | 配对变化 |
|---|---|---:|---:|---:|
| 65536 / 128 / 64 / distinct | ZADD / 80 | 103790.77 | 101573.15 | -2.14% |
| 65536 / 128 / 64 / ties | ZADD / 80 | 49871.23 | 51529.62 | +3.68% |
| 65536 / 128 / 64 / distinct | ZADD / 5120 | 90946.08 | 90892.76 | -0.06% |
| 65536 / 128 / 64 / ties | ZADD / 5120 | 40817.83 | 40993.13 | +5.20% |
| 65536 / 128 / 64 / distinct | ZINCRBY / 80 | 76794.41 | 78745.81 | +2.54% |
| 65536 / 128 / 64 / distinct | ZINCRBY / 320 | 76919.61 | 78299.20 | +1.79% |
| 65536 / 128 / 64 / distinct | ZINCRBY / 2560 | 73031.45 | 73412.27 | +0.52% |
| 65536 / 128 / 64 / distinct | ZINCRBY / 5120 | 71287.93 | 72368.65 | +1.52% |
| 65536 / 128 / 64 / distinct | ZSCORE / 80 | 342914.36 | 348165.98 | +1.53% |
| 65536 / 128 / 64 / distinct | ZSCORE / 320 | 536495.93 | 338995.38 | -36.13% |
| 65536 / 128 / 64 / distinct | ZSCORE / 2560 | 336187.01 | 352240.24 | +4.78% |
| 65536 / 128 / 64 / distinct | ZSCORE / 5120 | 308260.06 | 322814.59 | +4.44% |
| 104857600 / 1024 / 8 / distinct | ZADD / 80 | 63299.93 | 63319.41 | -1.46% |
| 104857600 / 1024 / 8 / ties | ZADD / 80 | 8.67 | 8.37 | -3.47% |
| 104857600 / 1024 / 8 / distinct | ZADD / 5120 | 58975.10 | 59250.55 | +1.47% |
| 104857600 / 1024 / 8 / ties | ZADD / 5120 | 38.79 | 38.37 | -1.10% |
| 104857600 / 1024 / 8 / distinct | ZINCRBY / 80 | 36611.11 | 36824.39 | -0.07% |
| 104857600 / 1024 / 8 / distinct | ZINCRBY / 320 | 39693.33 | 39866.20 | +0.44% |
| 104857600 / 1024 / 8 / distinct | ZINCRBY / 2560 | 39543.56 | 39419.83 | -0.41% |
| 104857600 / 1024 / 8 / distinct | ZINCRBY / 5120 | 40391.49 | 40581.34 | +0.52% |
| 104857600 / 1024 / 8 / distinct | ZSCORE / 80 | 279881.55 | 295502.04 | +4.56% |
| 104857600 / 1024 / 8 / distinct | ZSCORE / 320 | 311859.05 | 315986.10 | +0.67% |
| 104857600 / 1024 / 8 / distinct | ZSCORE / 2560 | 200562.32 | 206790.43 | +3.11% |
| 104857600 / 1024 / 8 / distinct | ZSCORE / 5120 | 184445.86 | 185897.11 | +0.97% |

## 全部逐轮结果

| 数据字节 / 成员字节 / keys / 初始分值 / 命令 / 并发 | 轮次 | QPS 变化 | p99 变化 | main 请求数 | 候选请求数 | main 调用秒数 | 候选调用秒数 | 原始记录 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 65536 / 128 / 64 / distinct / ZADD / 80 | 1 | -7.02% | +6.02% | 3321906 | 3088890 | 31.428 | 31.429 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zadd-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zadd-distinct-repeat1-20261006/) |
| 65536 / 128 / 64 / distinct / ZADD / 80 | 2 | -2.16% | +5.26% | 3261921 | 3192168 | 31.428 | 31.427 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zadd-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zadd-distinct-repeat2-20261006/) |
| 65536 / 128 / 64 / distinct / ZADD / 80 | 3 | +4.01% | -4.20% | 3123985 | 3249551 | 31.428 | 31.426 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zadd-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zadd-distinct-repeat3-20261006/) |
| 65536 / 128 / 64 / ties / ZADD / 80 | 1 | +3.68% | -4.07% | 1576564 | 1634616 | 31.425 | 31.425 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zadd-ties-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zadd-ties-repeat1-20261006/) |
| 65536 / 128 / 64 / ties / ZADD / 80 | 2 | +6.32% | -6.30% | 1523161 | 1619350 | 31.426 | 31.426 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zadd-ties-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zadd-ties-repeat2-20261006/) |
| 65536 / 128 / 64 / ties / ZADD / 80 | 3 | -1.86% | -0.41% | 1567237 | 1538072 | 31.426 | 31.425 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zadd-ties-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zadd-ties-repeat3-20261006/) |
| 65536 / 128 / 64 / distinct / ZADD / 5120 | 1 | -2.07% | +1.48% | 3092616 | 3026492 | 33.835 | 33.784 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zadd-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zadd-distinct-repeat1-20261006/) |
| 65536 / 128 / 64 / distinct / ZADD / 5120 | 2 | +0.67% | -0.49% | 3056715 | 3079654 | 34.786 | 33.784 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zadd-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zadd-distinct-repeat2-20261006/) |
| 65536 / 128 / 64 / distinct / ZADD / 5120 | 3 | +3.07% | -0.49% | 3072510 | 3161809 | 33.784 | 34.786 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zadd-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zadd-distinct-repeat3-20261006/) |
| 65536 / 128 / 64 / ties / ZADD / 5120 | 1 | +6.06% | -4.15% | 1349731 | 1427984 | 34.834 | 34.835 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zadd-ties-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zadd-ties-repeat1-20261006/) |
| 65536 / 128 / 64 / ties / ZADD / 5120 | 2 | +5.21% | -3.80% | 1378829 | 1450605 | 33.780 | 33.782 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zadd-ties-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zadd-ties-repeat2-20261006/) |
| 65536 / 128 / 64 / ties / ZADD / 5120 | 3 | -3.41% | +3.88% | 1406744 | 1360892 | 33.831 | 34.783 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zadd-ties-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zadd-ties-repeat3-20261006/) |
| 65536 / 128 / 64 / distinct / ZINCRBY / 80 | 1 | -0.35% | +1.12% | 2482497 | 2473854 | 31.376 | 31.377 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zincrby-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zincrby-distinct-repeat1-20261006/) |
| 65536 / 128 / 64 / distinct / ZINCRBY / 80 | 2 | +2.53% | -4.32% | 2409563 | 2470857 | 31.377 | 31.378 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zincrby-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zincrby-distinct-repeat2-20261006/) |
| 65536 / 128 / 64 / distinct / ZINCRBY / 80 | 3 | +5.22% | -5.79% | 2337793 | 2459976 | 31.377 | 31.376 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zincrby-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zincrby-distinct-repeat3-20261006/) |
| 65536 / 128 / 64 / distinct / ZINCRBY / 320 | 1 | +0.60% | -3.03% | 2444310 | 2459053 | 31.378 | 31.378 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zincrby-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zincrby-distinct-repeat1-20261006/) |
| 65536 / 128 / 64 / distinct / ZINCRBY / 320 | 2 | +1.80% | +3.01% | 2413544 | 2456859 | 31.377 | 31.378 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zincrby-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zincrby-distinct-repeat2-20261006/) |
| 65536 / 128 / 64 / distinct / ZINCRBY / 320 | 3 | +2.95% | +7.03% | 2347290 | 2416597 | 31.378 | 31.378 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zincrby-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zincrby-distinct-repeat3-20261006/) |
| 65536 / 128 / 64 / distinct / ZINCRBY / 2560 | 1 | -0.17% | +1.53% | 2356510 | 2352686 | 32.080 | 33.083 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zincrby-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zincrby-distinct-repeat1-20261006/) |
| 65536 / 128 / 64 / distinct / ZINCRBY / 2560 | 2 | +0.51% | -0.76% | 2342757 | 2355065 | 32.079 | 32.080 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zincrby-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zincrby-distinct-repeat2-20261006/) |
| 65536 / 128 / 64 / distinct / ZINCRBY / 2560 | 3 | +5.84% | -5.76% | 2248210 | 2377120 | 32.079 | 32.080 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zincrby-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zincrby-distinct-repeat3-20261006/) |
| 65536 / 128 / 64 / distinct / ZINCRBY / 5120 | 1 | +1.57% | -3.01% | 2344126 | 2379628 | 32.883 | 32.882 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zincrby-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zincrby-distinct-repeat1-20261006/) |
| 65536 / 128 / 64 / distinct / ZINCRBY / 5120 | 2 | +0.37% | -0.75% | 2368852 | 2378897 | 32.931 | 32.882 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zincrby-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zincrby-distinct-repeat2-20261006/) |
| 65536 / 128 / 64 / distinct / ZINCRBY / 5120 | 3 | +4.96% | -5.88% | 2273132 | 2383986 | 32.881 | 32.882 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zincrby-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zincrby-distinct-repeat3-20261006/) |
| 65536 / 128 / 64 / distinct / ZSCORE / 80 | 1 | +2.08% | +6.54% | 10816122 | 11041222 | 30.373 | 31.277 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zscore-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zscore-distinct-repeat1-20261006/) |
| 65536 / 128 / 64 / distinct / ZSCORE / 80 | 2 | +1.87% | -2.18% | 10724609 | 10924731 | 31.275 | 31.378 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zscore-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zscore-distinct-repeat2-20261006/) |
| 65536 / 128 / 64 / distinct / ZSCORE / 80 | 3 | -0.93% | +8.53% | 10469973 | 10372784 | 31.378 | 30.275 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zscore-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zscore-distinct-repeat3-20261006/) |
| 65536 / 128 / 64 / distinct / ZSCORE / 320 | 1 | -37.32% | +347.86% | 16971833 | 10637283 | 31.382 | 31.379 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zscore-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zscore-distinct-repeat1-20261006/) |
| 65536 / 128 / 64 / distinct / ZSCORE / 320 | 2 | +1.30% | +0.71% | 16836892 | 17057388 | 31.383 | 31.381 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zscore-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zscore-distinct-repeat2-20261006/) |
| 65536 / 128 / 64 / distinct / ZSCORE / 320 | 3 | -36.12% | +315.15% | 15738893 | 10052489 | 31.382 | 31.379 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zscore-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zscore-distinct-repeat3-20261006/) |
| 65536 / 128 / 64 / distinct / ZSCORE / 2560 | 1 | +8.82% | +0.91% | 10826399 | 11778404 | 32.086 | 32.137 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zscore-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zscore-distinct-repeat1-20261006/) |
| 65536 / 128 / 64 / distinct / ZSCORE / 2560 | 2 | +4.77% | -4.98% | 10787092 | 11302275 | 32.087 | 32.087 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zscore-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zscore-distinct-repeat2-20261006/) |
| 65536 / 128 / 64 / distinct / ZSCORE / 2560 | 3 | -5.39% | +14.78% | 10309030 | 9752816 | 32.085 | 32.136 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zscore-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zscore-distinct-repeat3-20261006/) |
| 65536 / 128 / 64 / distinct / ZSCORE / 5120 | 1 | +7.90% | -5.31% | 10153779 | 10956834 | 32.939 | 33.942 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zscore-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zscore-distinct-repeat1-20261006/) |
| 65536 / 128 / 64 / distinct / ZSCORE / 5120 | 2 | +4.45% | -6.47% | 10230749 | 10684665 | 32.939 | 32.939 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zscore-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zscore-distinct-repeat2-20261006/) |
| 65536 / 128 / 64 / distinct / ZSCORE / 5120 | 3 | -2.74% | +13.33% | 9896942 | 9624095 | 33.941 | 32.938 | [main](../../raw/lavik-parent5a3903d9-pr283-65536-128-zscore-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-65536-128-zscore-distinct-repeat3-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZADD / 80 | 1 | +1.44% | -5.10% | 1974476 | 2002817 | 31.423 | 31.577 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zadd-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zadd-distinct-repeat1-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZADD / 80 | 2 | -2.52% | +2.69% | 2041178 | 1989868 | 31.575 | 31.426 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zadd-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zadd-distinct-repeat2-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZADD / 80 | 3 | -0.98% | +9.24% | 1989210 | 1969551 | 31.425 | 31.575 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zadd-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zadd-distinct-repeat3-20261006/) |
| 104857600 / 1024 / 8 / ties / ZADD / 80 | 1 | -0.81% | +6.96% | 456 | 456 | 52.381 | 54.413 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zadd-ties-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zadd-ties-repeat1-20261006/) |
| 104857600 / 1024 / 8 / ties / ZADD / 80 | 2 | -1.28% | +0.00% | 454 | 455 | 52.378 | 54.383 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zadd-ties-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zadd-ties-repeat2-20261006/) |
| 104857600 / 1024 / 8 / ties / ZADD / 80 | 3 | +0.70% | +1.82% | 454 | 455 | 53.432 | 54.430 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zadd-ties-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zadd-ties-repeat3-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZADD / 5120 | 1 | +1.96% | -40.00% | 2021006 | 2061075 | 34.786 | 34.786 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zadd-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zadd-distinct-repeat1-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZADD / 5120 | 2 | +1.22% | -14.93% | 1995326 | 2021648 | 33.833 | 33.784 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zadd-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zadd-distinct-repeat2-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZADD / 5120 | 3 | -6.93% | -15.04% | 2067633 | 1927297 | 34.835 | 34.785 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zadd-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zadd-distinct-repeat3-20261006/) |
| 104857600 / 1024 / 8 / ties / ZADD / 5120 | 1 | +4.99% | -0.43% | 10949 | 10952 | 286.292 | 281.317 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zadd-ties-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zadd-ties-repeat1-20261006/) |
| 104857600 / 1024 / 8 / ties / ZADD / 5120 | 2 | +1.34% | +0.44% | 10953 | 10950 | 282.320 | 285.382 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zadd-ties-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zadd-ties-repeat2-20261006/) |
| 104857600 / 1024 / 8 / ties / ZADD / 5120 | 3 | -3.58% | +0.44% | 10952 | 10952 | 282.326 | 289.294 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zadd-ties-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zadd-ties-repeat3-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZINCRBY / 80 | 1 | +0.56% | -2.48% | 1146879 | 1153476 | 31.374 | 31.576 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zincrby-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zincrby-distinct-repeat1-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZINCRBY / 80 | 2 | +0.48% | +0.00% | 1155960 | 1161284 | 31.574 | 31.377 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zincrby-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zincrby-distinct-repeat2-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZINCRBY / 80 | 3 | -1.26% | -0.51% | 1177612 | 1162674 | 31.372 | 31.573 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zincrby-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zincrby-distinct-repeat3-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZINCRBY / 320 | 1 | +0.45% | -3.66% | 1245299 | 1250936 | 31.373 | 31.378 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zincrby-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zincrby-distinct-repeat1-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZINCRBY / 320 | 2 | +1.32% | -0.40% | 1233999 | 1250280 | 31.374 | 31.376 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zincrby-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zincrby-distinct-repeat2-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZINCRBY / 320 | 3 | -0.32% | -0.40% | 1256576 | 1252522 | 31.374 | 31.376 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zincrby-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zincrby-distinct-repeat3-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZINCRBY / 2560 | 1 | -0.48% | -3.54% | 1270440 | 1263660 | 32.128 | 32.130 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zincrby-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zincrby-distinct-repeat1-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZINCRBY / 2560 | 2 | +0.73% | -3.47% | 1260075 | 1269638 | 32.128 | 32.079 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zincrby-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zincrby-distinct-repeat2-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZINCRBY / 2560 | 3 | -0.52% | +19.87% | 1271741 | 1264553 | 32.128 | 32.079 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zincrby-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zincrby-distinct-repeat3-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZINCRBY / 5120 | 1 | +0.53% | -1.54% | 1328084 | 1335109 | 32.880 | 32.882 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zincrby-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zincrby-distinct-repeat1-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZINCRBY / 5120 | 2 | +3.69% | -17.88% | 1321731 | 1369828 | 32.881 | 33.882 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zincrby-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zincrby-distinct-repeat2-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZINCRBY / 5120 | 3 | -0.56% | +14.20% | 1344093 | 1336359 | 32.930 | 32.930 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zincrby-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zincrby-distinct-repeat3-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZSCORE / 80 | 1 | +4.34% | -7.95% | 8581609 | 8954313 | 31.526 | 30.279 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zscore-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zscore-distinct-repeat1-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZSCORE / 80 | 2 | +1.22% | -4.93% | 8868297 | 8976041 | 31.379 | 30.376 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zscore-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zscore-distinct-repeat2-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZSCORE / 80 | 3 | -1.85% | +6.79% | 8823579 | 8660113 | 31.526 | 31.330 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zscore-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zscore-distinct-repeat3-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZSCORE / 320 | 1 | +1.56% | -4.81% | 9787876 | 9940142 | 31.386 | 31.382 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zscore-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zscore-distinct-repeat1-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZSCORE / 320 | 2 | -0.26% | -3.70% | 9943092 | 9916897 | 31.385 | 31.384 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zscore-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zscore-distinct-repeat2-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZSCORE / 320 | 3 | +0.67% | +0.00% | 9688650 | 9753465 | 31.383 | 31.381 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zscore-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zscore-distinct-repeat3-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZSCORE / 2560 | 1 | +3.87% | -3.68% | 6438083 | 6680927 | 32.086 | 32.136 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zscore-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zscore-distinct-repeat1-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZSCORE / 2560 | 2 | +5.06% | -5.21% | 6434624 | 6755284 | 32.084 | 33.137 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zscore-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zscore-distinct-repeat2-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZSCORE / 2560 | 3 | +3.19% | -4.19% | 6434868 | 6634658 | 32.084 | 32.084 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zscore-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zscore-distinct-repeat3-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZSCORE / 5120 | 1 | +1.37% | -15.98% | 6075228 | 6158039 | 32.938 | 32.937 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zscore-distinct-repeat1-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zscore-distinct-repeat1-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZSCORE / 5120 | 2 | +0.51% | +18.79% | 6177593 | 6212723 | 32.886 | 33.941 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zscore-distinct-repeat2-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zscore-distinct-repeat2-20261006/) |
| 104857600 / 1024 / 8 / distinct / ZSCORE / 5120 | 3 | +1.06% | -8.85% | 6063675 | 6122719 | 32.935 | 32.936 | [main](../../raw/lavik-parent5a3903d9-pr283-104857600-1024-zscore-distinct-repeat3-20261006/) / [候选](../../raw/lavik-candidateace4198b-pr283-104857600-1024-zscore-distinct-repeat3-20261006/) |

观测文件 SHA256：`594ebd36aec77fa7cfdcf376da42f574c9870933afee9b7082a9ae89aa96c70e`。

[全部观测](pr283-repeats.json) · [基数与配对核验](controls-validation.json) · [命令计数核验](controls-command-audit.json)
