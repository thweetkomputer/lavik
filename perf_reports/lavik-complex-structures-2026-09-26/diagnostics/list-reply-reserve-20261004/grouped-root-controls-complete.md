# #282 固定版本的完整 72 点普通 key 对照

比较父版本 `19496654` 与根记录复用候选 `28d7cca4`。测量固定历史提交，不代表当前 main 或 rebase 后 head 的整体性能。

12 个条件各执行三轮 A/B、B/A、A/B；每点 30 秒、pipeline=1。读取每轮共享父版本新建的逻辑数据，后台物理变化仍可能发生；写入分别新建数据。全部 key 基数、源码/二进制身份、构建配置、正常退出及实际命令计数已核验。

表中绝对值是各版本三次观测的中位数；变化是三个配对百分比的中位数，两种计算不可互换。QPS 越高越好，p99 越低越好。三轮不是置信区间；逐轮请求数和结果保留在下表及 JSON。

其他三个系统没有重跑，持久化配置也不相同；不据此宣称整体追平，Hash/Set 使用 500 keys，而非历史 50,000-key 条件，不能用于更新历史 peer 排名。

父版本完整 CI 仍因外部 Redis cluster bus 端口冲突而失败，该导入场景不在本对照的验证范围内。两边原生回归均为 68 通过、28 个故障注入用例跳过；候选另有 128 个单元测试通过。这些短 key 控制也不等于长 key 延迟的成对测量，不解释历史 SET 超时。

| 条件（结构 / 字节 / 成员字节 / keys） | 命令 / 并发 | 父版本 QPS | 候选 QPS | 配对 QPS 变化 | 父版本 p99 ms | 候选 p99 ms | 配对 p99 变化 |
|---|---|---:|---:|---:|---:|---:|---:|
| hash / 1048576 / 128 / 500 | HGET / 320 | 658079.37 | 655256.19 | -0.45% | 0.975 | 0.967 | -0.82% |
| hash / 1048576 / 128 / 500 | HSET / 320 | 199193.97 | 200376.65 | +0.00% | 26.495 | 25.855 | -1.46% |
| list / 65536 / 128 / 64 | LINDEX / 320 | 609523.81 | 610131.73 | -0.02% | 2.095 | 2.063 | -2.99% |
| list / 65536 / 128 / 64 | LRANGE / 80 | 42729.27 | 42725.47 | -0.01% | 4.735 | 4.703 | -1.35% |
| list / 65536 / 128 / 64 | LSET / 320 | 158995.01 | 161101.33 | +0.67% | 23.167 | 22.911 | +0.00% |
| set / 1048576 / 128 / 500 | SADD_SREM / 320 | 347280.42 | 335678.86 | -3.08% | 6.975 | 7.231 | +0.00% |
| set / 1048576 / 128 / 500 | SISMEMBER / 320 | 657132.57 | 654667.32 | -0.27% | 0.967 | 0.967 | -0.83% |
| stream / 65536 / 1024 / 64 | XADD_MAXLEN / 320 | 60309.34 | 60440.96 | +0.22% | 55.807 | 54.015 | -3.21% |
| stream / 65536 / 1024 / 64 | XRANGE / 320 | 317534.29 | 317187.57 | -0.11% | 1.879 | 1.863 | -0.85% |
| stream / 65536 / 1024 / 64 | XRANGE_FULL / 80 | 22153.12 | 22264.06 | +0.64% | 5.311 | 5.247 | -3.01% |
| zset / 65536 / 128 / 64 | ZINCRBY / 320 | 74246.52 | 73026.23 | -1.64% | 35.583 | 36.095 | +0.00% |
| zset / 65536 / 128 / 64 | ZSCORE / 320 | 433613.24 | 428732.99 | -1.13% | 2.239 | 2.319 | +3.57% |

## 逐轮变化与请求数

保留所有轮次，包括负收益和尾延迟恶化；原始目录链接保留命令输出与 INFO 快照。

| 条件 / 命令 / 并发 | 轮次 | QPS 变化 | p99 变化 | 父版本请求数 | 候选请求数 | 原始数据 |
|---|---:|---:|---:|---:|---:|---|
| hash / 1048576 / 128 / 500 / HGET / 320 | 1 | -0.39% | +7.83% | 19748750 | 19670306 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-hash-1048576-128-read-repeat1-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-hash-1048576-128-read-repeat1-20261005/) |
| hash / 1048576 / 128 / 500 / HGET / 320 | 2 | -0.45% | -0.82% | 19750561 | 19660074 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-hash-1048576-128-read-repeat2-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-hash-1048576-128-read-repeat2-20261005/) |
| hash / 1048576 / 128 / 500 / HGET / 320 | 3 | -0.52% | -5.47% | 19564338 | 19460964 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-hash-1048576-128-read-repeat3-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-hash-1048576-128-read-repeat3-20261005/) |
| hash / 1048576 / 128 / 500 / HSET / 320 | 1 | +1.84% | -12.02% | 5942616 | 6053229 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-hash-1048576-128-write-repeat1-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-hash-1048576-128-write-repeat1-20261005/) |
| hash / 1048576 / 128 / 500 / HSET / 320 | 2 | -1.94% | -1.46% | 5977015 | 5862243 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-hash-1048576-128-write-repeat2-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-hash-1048576-128-write-repeat2-20261005/) |
| hash / 1048576 / 128 / 500 / HSET / 320 | 3 | +0.00% | +2.90% | 6012755 | 6013320 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-hash-1048576-128-write-repeat3-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-hash-1048576-128-write-repeat3-20261005/) |
| list / 65536 / 128 / 64 / LINDEX / 320 | 1 | -0.09% | -4.96% | 18322823 | 18307473 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-list-65536-128-read-repeat1-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-list-65536-128-read-repeat1-20261005/) |
| list / 65536 / 128 / 64 / LINDEX / 320 | 2 | -0.02% | -1.53% | 18208410 | 18203278 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-list-65536-128-read-repeat2-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-list-65536-128-read-repeat2-20261005/) |
| list / 65536 / 128 / 64 / LINDEX / 320 | 3 | +0.11% | -2.99% | 18291024 | 18310269 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-list-65536-128-read-repeat3-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-list-65536-128-read-repeat3-20261005/) |
| list / 65536 / 128 / 64 / LRANGE / 80 | 1 | -0.01% | -1.35% | 1281968 | 1281860 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-list-65536-128-read-repeat1-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-list-65536-128-read-repeat1-20261005/) |
| list / 65536 / 128 / 64 / LRANGE / 80 | 2 | +0.01% | -0.68% | 1281726 | 1281847 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-list-65536-128-read-repeat2-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-list-65536-128-read-repeat2-20261005/) |
| list / 65536 / 128 / 64 / LRANGE / 80 | 3 | -0.01% | -2.63% | 1281910 | 1281861 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-list-65536-128-read-repeat3-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-list-65536-128-read-repeat3-20261005/) |
| list / 65536 / 128 / 64 / LSET / 320 | 1 | +0.13% | +0.00% | 4857259 | 4864567 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-list-65536-128-write-repeat1-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-list-65536-128-write-repeat1-20261005/) |
| list / 65536 / 128 / 64 / LSET / 320 | 2 | +3.41% | -1.11% | 4675039 | 4834814 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-list-65536-128-write-repeat2-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-list-65536-128-write-repeat2-20261005/) |
| list / 65536 / 128 / 64 / LSET / 320 | 3 | +0.67% | +0.55% | 4771612 | 4803385 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-list-65536-128-write-repeat3-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-list-65536-128-write-repeat3-20261005/) |
| set / 1048576 / 128 / 500 / SADD_SREM / 320 | 1 | -3.08% | +0.00% | 10390603 | 10071618 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-set-1048576-128-write-repeat1-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-set-1048576-128-write-repeat1-20261005/) |
| set / 1048576 / 128 / 500 / SADD_SREM / 320 | 2 | +3.43% | -1.38% | 10420306 | 10778154 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-set-1048576-128-write-repeat2-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-set-1048576-128-write-repeat2-20261005/) |
| set / 1048576 / 128 / 500 / SADD_SREM / 320 | 3 | -9.89% | +11.54% | 10766952 | 9702561 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-set-1048576-128-write-repeat3-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-set-1048576-128-write-repeat3-20261005/) |
| set / 1048576 / 128 / 500 / SISMEMBER / 320 | 1 | -0.38% | +3.42% | 19719108 | 19643109 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-set-1048576-128-read-repeat1-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-set-1048576-128-read-repeat1-20261005/) |
| set / 1048576 / 128 / 500 / SISMEMBER / 320 | 2 | -0.27% | -0.83% | 19755897 | 19700753 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-set-1048576-128-read-repeat2-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-set-1048576-128-read-repeat2-20261005/) |
| set / 1048576 / 128 / 500 / SISMEMBER / 320 | 3 | -0.20% | -1.60% | 19608273 | 19569566 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-set-1048576-128-read-repeat3-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-set-1048576-128-read-repeat3-20261005/) |
| stream / 65536 / 1024 / 64 / XADD_MAXLEN / 320 | 1 | +0.22% | -3.21% | 1809839 | 1814032 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-stream-65536-1024-write-repeat1-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-stream-65536-1024-write-repeat1-20261005/) |
| stream / 65536 / 1024 / 64 / XADD_MAXLEN / 320 | 2 | +1.42% | -5.88% | 1805710 | 1831246 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-stream-65536-1024-write-repeat2-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-stream-65536-1024-write-repeat2-20261005/) |
| stream / 65536 / 1024 / 64 / XADD_MAXLEN / 320 | 3 | -1.77% | -0.93% | 1831054 | 1799371 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-stream-65536-1024-write-repeat3-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-stream-65536-1024-write-repeat3-20261005/) |
| stream / 65536 / 1024 / 64 / XRANGE / 320 | 1 | -0.11% | +2.19% | 9529049 | 9517541 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-stream-65536-1024-read-repeat1-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-stream-65536-1024-read-repeat1-20261005/) |
| stream / 65536 / 1024 / 64 / XRANGE / 320 | 2 | -1.00% | -0.85% | 9552470 | 9458487 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-stream-65536-1024-read-repeat2-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-stream-65536-1024-read-repeat2-20261005/) |
| stream / 65536 / 1024 / 64 / XRANGE / 320 | 3 | +0.63% | -2.54% | 9459952 | 9519574 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-stream-65536-1024-read-repeat3-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-stream-65536-1024-read-repeat3-20261005/) |
| stream / 65536 / 1024 / 64 / XRANGE_FULL / 80 | 1 | +0.85% | -4.65% | 661795 | 667358 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-stream-65536-1024-read-repeat1-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-stream-65536-1024-read-repeat1-20261005/) |
| stream / 65536 / 1024 / 64 / XRANGE_FULL / 80 | 2 | +0.64% | -3.01% | 664699 | 668946 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-stream-65536-1024-read-repeat2-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-stream-65536-1024-read-repeat2-20261005/) |
| stream / 65536 / 1024 / 64 / XRANGE_FULL / 80 | 3 | -0.40% | +3.75% | 670729 | 667967 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-stream-65536-1024-read-repeat3-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-stream-65536-1024-read-repeat3-20261005/) |
| zset / 65536 / 128 / 64 / ZINCRBY / 320 | 1 | +2.37% | +0.00% | 2171971 | 2223530 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-zset-65536-128-write-repeat1-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-zset-65536-128-write-repeat1-20261005/) |
| zset / 65536 / 128 / 64 / ZINCRBY / 320 | 2 | -1.64% | +7.35% | 2228208 | 2191550 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-zset-65536-128-write-repeat2-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-zset-65536-128-write-repeat2-20261005/) |
| zset / 65536 / 128 / 64 / ZINCRBY / 320 | 3 | -5.09% | +0.00% | 2307530 | 2190180 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-zset-65536-128-write-repeat3-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-zset-65536-128-write-repeat3-20261005/) |
| zset / 65536 / 128 / 64 / ZSCORE / 320 | 1 | -1.47% | +13.42% | 12764877 | 12576280 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-zset-65536-128-read-repeat1-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-zset-65536-128-read-repeat1-20261005/) |
| zset / 65536 / 128 / 64 / ZSCORE / 320 | 2 | -1.13% | +3.57% | 13010370 | 12865705 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-zset-65536-128-read-repeat2-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-zset-65536-128-read-repeat2-20261005/) |
| zset / 65536 / 128 / 64 / ZSCORE / 320 | 3 | -0.29% | -12.90% | 14160803 | 14117964 | [父版本](../../raw/lavik-parent19496654-grouped-root-controls-zset-65536-128-read-repeat3-20261005/) / [候选](../../raw/lavik-candidate28d7cca4-grouped-root-controls-zset-65536-128-read-repeat3-20261005/) |

## 可复核输入

观测清单 SHA256：`f1c011081b26cbd1bb29e7aedaa18c0cdbedb025dbb0000053452e00cb0312f7`。

[全部观测](grouped-root-controls-complete-observations.json) · [完整校验与配对值](grouped-root-controls-complete-summary.json) · [实际命令计数](grouped-root-controls-complete-command-audit.json)
