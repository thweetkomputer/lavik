# 单路由替换：Set 100 MiB/key / 1024 B / 500 keys

固定 parent `19496654`、candidate `27c65ff9` 生产二进制，三轮 A/B、B/A、A/B；每个版本独立 RESTORE 同一已核对 SHA-256 的 RDB，再重启测量。逐一核对全部 key 基数，30 秒/点、pipeline=1，先读后写；没有并发编译、测试或 perf。不同实例的路由 seed 和物理布局独立。Set QPS 按命令计数，可能包含无实际修改的操作。

[36 点原始观察](hash-route-set-large-observations.json) · [全部配对与来源核验](hash-route-set-large-summary.json) · [依赖来源更正](native-dependency-provenance-correction.json)。负 p99 变化代表改善。配对百分比先逐轮相除再取中位，不等于两个边际中位数的比值，不是置信区间。

| 命令 | 连接数 | Parent QPS 中位 | Candidate QPS 中位 | 配对 QPS 中位变化 | 三轮 QPS 范围 | QPS 改善轮数 | 配对 p99 中位变化 | 三轮 p99 范围 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SADD_SREM | 80 | 304790.30 | 283952.55 | -6.95% | -7.28% … +0.93% | 1/3 | -5.27% | -16.54% … +3.16% |
| SADD_SREM | 320 | 339763.76 | 318150.21 | -6.55% | -6.56% … +4.86% | 1/3 | -2.92% | -11.54% … -2.89% |
| SADD_SREM | 5120 | 239880.92 | 215367.75 | -10.62% | -15.06% … +10.19% | 1/3 | -23.62% | -25.62% … -8.46% |
| SISMEMBER | 80 | 352542.12 | 351017.84 | -0.43% | -0.56% … -0.01% | 0/3 | -2.23% | -2.23% … +2.28% |
| SISMEMBER | 320 | 553315.30 | 547779.73 | -0.46% | -1.12% … +0.92% | 1/3 | -2.15% | -10.72% … +0.00% |
| SISMEMBER | 5120 | 343319.51 | 334033.49 | -1.65% | -5.58% … +3.03% | 1/3 | -3.33% | -9.13% … +2.61% |

## 解读

SADD/SREM 的三个连接数均为两轮 QPS 下降、一轮上升，配对中位下降 6.95%/6.55%/10.62%。c320/c5120 的 p99 三轮均改善；这属于观测到的吞吐与尾延迟取舍，不能据此宣称写入加速。c5120 QPS 的逐轮范围为 −15.06% 至 +10.19%，三轮仍不足以判断回退原因。

SISMEMBER 的配对 QPS 中位也均为负，c80 三轮均小幅下降，其余连接数方向混合。每个实例独立生成路由 seed 和物理布局，Set 写入可能为无操作；这些观测不直接等于代码路径的因果成本。小 Set 与独立 perf 尚未完成。目前已完成的 Hash/大 Set 结果不支持把 #276 当作通用吞吐优化，PR 保持草稿。

[已保存 INFO 的后续核对](hash-route-set-large-counters.md)：变更计数/命令数接近 50%，提交批量与高水位事件有明显轮次差异；不能仅用背压解释所有回退。

## 与历史 peer 的差距

严格匹配命令、数据量、元素大小、key 数和连接数，peer 未在本轮重跑，历史单点与此次三轮 30 秒的采样方法不同。Redis/Valkey 关闭持久化；Kvrocks 关闭 WAL 且使用 80 GiB cache；Lavik 保持 SPDK 持久化、无字段/页内容缓存。[来源 CSV 哈希和历史值](hash-route-set-large-historical-context.json)用于定位剩余差距，不代表同等持久性排名或整体达到目标。

| 命令 | 连接数 | Candidate QPS 中位 | Redis 历史 QPS | Valkey 历史 QPS | Kvrocks 历史 QPS | Candidate/最快历史 peer |
|---|---:|---:|---:|---:|---:|---:|
| SADD_SREM | 80 | 283952.55 | 434828.97 | 533374.38 | 297558.22 | 53.24% |
| SADD_SREM | 320 | 318150.21 | 676788.79 | 636075.71 | 130706.46 | 47.01% |
| SADD_SREM | 5120 | 215367.75 | 601809.21 | 553223.32 | 132633.62 | 35.79% |
| SISMEMBER | 80 | 351017.84 | 271138.06 | 520043.88 | 383918.43 | 67.50% |
| SISMEMBER | 320 | 547779.73 | 592198.46 | 599792.34 | 490274.33 | 91.33% |
| SISMEMBER | 5120 | 334033.49 | 464937.41 | 452963.62 | 371316.83 | 71.84% |

## 复算

在当前报告目录执行：

```sh
python3 diagnostics/hash-route-replace-20261005/summarize-hash-route-replace.py --scope set-large --report-root . --input diagnostics/hash-route-replace-20261005/hash-route-set-large-observations.json --versions diagnostics/hash-route-replace-20261005/hash-route-replace-versions.json --output /tmp/hash-route-set-large-verified.json
```
