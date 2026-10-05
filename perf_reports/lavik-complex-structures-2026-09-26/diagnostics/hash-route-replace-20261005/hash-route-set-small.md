# 单路由替换：Set 1 MiB/key / 128 B / 50000 keys

固定 parent `19496654`、candidate `27c65ff9` 生产二进制，三轮 A/B、B/A、A/B；每个版本独立 RESTORE 同一已核对 SHA-256 的 RDB，再重启测量。逐一核对全部 key 基数，30 秒/点、pipeline=1，先读后写；没有并发编译、测试或 perf。不同实例的路由 seed 和物理布局独立。Set QPS 按命令计数，可能包含无实际修改的操作。

[36 点原始观察](hash-route-set-small-observations.json) · [全部配对与来源核验](hash-route-set-small-summary.json) · [依赖来源更正](native-dependency-provenance-correction.json)。负 p99 变化代表改善。配对百分比先逐轮相除再取中位，不等于两个边际中位数的比值，不是置信区间。

| 命令 | 连接数 | Parent QPS 中位 | Candidate QPS 中位 | 配对 QPS 中位变化 | 三轮 QPS 范围 | QPS 改善轮数 | 配对 p99 中位变化 | 三轮 p99 范围 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SADD_SREM | 80 | 193373.91 | 192521.30 | -3.08% | -11.54% … +1.40% | 1/3 | -3.70% | -4.97% … +39.62% |
| SADD_SREM | 320 | 241610.43 | 245342.68 | -3.32% | -10.68% … +3.18% | 1/3 | -9.09% | -9.28% … +25.00% |
| SADD_SREM | 5120 | 196782.89 | 198939.33 | -4.87% | -6.84% … +2.64% | 1/3 | -18.01% | -25.17% … +11.30% |
| SISMEMBER | 80 | 353297.96 | 350442.97 | -0.81% | -1.59% … +0.49% | 1/3 | +0.00% | +0.00% … +0.00% |
| SISMEMBER | 320 | 568824.85 | 565245.37 | -1.32% | -1.74% … +0.66% | 1/3 | +0.81% | -1.59% … +1.63% |
| SISMEMBER | 5120 | 399381.34 | 393146.58 | -1.71% | -2.96% … +1.00% | 1/3 | -7.46% | -23.51% … +6.39% |

## 解读

SADD/SREM 在三个连接数均为两轮 QPS 下降、一轮上升，中位变化 −3.08%/−3.32%/−4.87%。p99 中位改善，但每组也各有一轮变差，最大分别为 +39.62%/+25.00%/+11.30%，没有一致的尾延迟提升。SISMEMBER 的三个 QPS 配对中位也均为负。三轮不能指定回退原因或构成置信区间，#276 继续保持草稿。

c320/c5120 的候选边际 QPS 中位高于父版本，但逐轮配对变化中位为负。这两种统计量不等价：配对中位保留同轮关系，本报告沿用预先固定的配对汇总方式，同时保留所有边际值与每轮比值，不隐去相反方向的统计量。

## 与历史 peer 的差距

严格匹配命令、数据量、元素大小、key 数和连接数，peer 未在本轮重跑，历史单点与此次三轮 30 秒的采样方法不同。Redis/Valkey 关闭持久化；Kvrocks 关闭 WAL 且使用 80 GiB cache；Lavik 保持 SPDK 持久化、无字段/页内容缓存。[来源 CSV 哈希和历史值](hash-route-set-small-historical-context.json)用于定位剩余差距，不代表同等持久性排名或整体达到目标。

| 命令 | 连接数 | Candidate QPS 中位 | Redis 历史 QPS | Valkey 历史 QPS | Kvrocks 历史 QPS | Candidate/最快历史 peer |
|---|---:|---:|---:|---:|---:|---:|
| SADD_SREM | 80 | 192521.30 | 278914.88 | 567348.90 | 379578.36 | 33.93% |
| SADD_SREM | 320 | 245342.68 | 378689.48 | 640820.43 | 422935.77 | 38.29% |
| SADD_SREM | 5120 | 198939.33 | 324321.75 | 504065.64 | 344333.44 | 39.47% |
| SISMEMBER | 80 | 350442.97 | 390185.85 | 422991.08 | 319392.97 | 82.85% |
| SISMEMBER | 320 | 565245.37 | 510672.31 | 554418.07 | 453909.00 | 101.95% |
| SISMEMBER | 5120 | 393146.58 | 441984.88 | 447961.46 | 354628.88 | 87.76% |

## 复算

在当前报告目录执行：

```sh
python3 diagnostics/hash-route-replace-20261005/summarize-hash-route-replace.py --scope set-small --report-root . --input diagnostics/hash-route-replace-20261005/hash-route-set-small-observations.json --versions diagnostics/hash-route-replace-20261005/hash-route-replace-versions.json --output /tmp/hash-route-set-small-verified.json
```
