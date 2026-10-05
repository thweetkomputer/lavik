# 固定二进制：8/12 workers 的完整三轮配置对照

24 点已完成，全部原始结果、源码/二进制身份、八个 key 基数、零错误、退出码及 INFO 命令计数核验通过。使用 `067c7589` 同一个原生二进制，100 MiB/key、1024 B/member、8 keys，30 秒、pipeline=1，按 12/8、8/12、12/8 顺序做三轮独立重新预置。

这组数据支持保留配置诊断结论，不产生新的优化 PR，也不改写报告原有 12-worker 曲线。只改变 `--threads`；各次日志目录属于记录差异。每 worker 资源池、线程放置和 key owner 映射随 worker 数一起变化，不能把全部效果单独归因于 owner 数量。

## 配对结果

以下为每轮 8 workers 相对 12 workers 的变化，再对三轮取中位；不是两组独立中位数相除。负的 p99 变化表示改善，不声称统计置信区间。

| 命令 | 并发 | QPS 配对中位 | 三轮 QPS 范围 | p99 配对中位 | 三轮 p99 范围 |
|---|---:|---:|---:|---:|---:|
| ZSCORE | 80 | +19.16% | +15.69% … +34.16% | -21.83% | -29.31% … -17.36% |
| ZSCORE | 320 | +31.70% | +26.20% … +43.03% | -62.67% | -64.83% … -62.52% |
| ZINCRBY | 80 | +39.88% | +36.03% … +41.99% | +21.54% | +20.81% … +22.22% |
| ZINCRBY | 320 | +40.75% | +37.13% … +43.44% | +24.90% | +24.00% … +32.78% |

四个测量点的 QPS 三轮均提升。ZSCORE 两档 p99 三轮均改善；ZINCRBY 两档 p99 则三轮均退化，不能据吞吐提升建议全面切换到 8 workers。

| 命令 | 并发 | 12 workers QPS 中位 | 8 workers QPS 中位 | 12 workers p99 中位（ms） | 8 workers p99 中位（ms） |
|---|---:|---:|---:|---:|---:|
| ZSCORE | 80 | 248,249.59 | 295,814.69 | 0.623 | 0.487 |
| ZSCORE | 320 | 263,951.62 | 347,634.25 | 3.855 | 1.439 |
| ZINCRBY | 80 | 38,730.08 | 54,174.43 | 12.607 | 15.231 |
| ZINCRBY | 320 | 41,321.91 | 58,192.60 | 31.359 | 39.679 |

## CPU 计数与限制

每点在 `measure()` 前后读取 `/proc` 的 user/system ticks，验证 PID、TID 集合和线程起始时间不变，计数非负。窗口包含客户端启动、结果收集以及内核、网络、轮询和后台 CPU；不是命令独占 CPU，不计算 CPU/请求。没有 TID 到具体 owner 的直接映射。

| 命令 | 并发 | 12 workers 进程 CPU 秒中位 | 8 workers 进程 CPU 秒中位 | 12 workers 平均占用核数中位 | 8 workers 平均占用核数中位 |
|---|---:|---:|---:|---:|---:|
| ZSCORE | 80 | 297.20 | 239.28 | 9.344 | 7.523 |
| ZSCORE | 320 | 290.04 | 239.30 | 9.118 | 7.524 |
| ZINCRBY | 80 | 162.08 | 207.12 | 5.131 | 6.534 |
| ZINCRBY | 320 | 166.67 | 219.29 | 5.262 | 6.899 |

读负载的进程 CPU 总量下降，写负载则上升，进一步说明两类命令的取舍不同。由源码计算，这八个 key 在 12 workers 下集中到四个数据 owner，在 8 workers 下分布到八个 owner；资源池、放置和并发变化仍是共同因素。

## 历史 peer 差距

仅作为背景：其他三库未重跑，Redis/Valkey 关闭持久化，Kvrocks 关闭 WAL 且使用 80 GiB cache；Lavik 使用 SPDK 持久化。不能据此宣称等持久性排名或整体追平。

| 命令 | 并发 | 8 workers / 同负载历史最快 peer |
|---|---:|---:|
| ZSCORE | 80 | 56.16% |
| ZSCORE | 320 | 49.78% |
| ZINCRBY | 80 | 11.79% |
| ZINCRBY | 320 | 9.92% |

该配置没有与 #280 的 score-view 候选一起测量，不能将两者百分比相乘得到组合收益。仍按当前指示收敛现有 PR，不扩大为新的配置搜索。

## 复算证据

[固定观测](zset-worker-count-complete-observations.json) · [全部配对与逐线程计数](zset-worker-count-complete-summary.json) · [命令计数核验](zset-worker-count-complete-command-audit.json) · [历史 peer 来源](zset-worker-count-historical-context.json) · [文件哈希清单](zset-worker-count-evidence-index.json)

在本目录执行 `python3 summarize-zset-worker-count.py --input zset-worker-count-complete-observations.json --output /tmp/worker-summary.json --report-root <report-directory>`，以及 `python3 audit-zset-score-commands.py --input zset-worker-count-complete-observations.json --output /tmp/worker-commands.json --report-root <report-directory>`。原始 JSON、CPU snapshots 和 INFO 文件均随报告发布。
