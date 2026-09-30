# LSET：增加 key 后的 CPU 与提交路径诊断

本轮比较 main `a8c926d49f056dde97c4a7d12f7d765f2c891c79` 与
[PR #233](https://github.com/eloqdata/lavik/pull/233)
`759832d8a66e7e6b0d16a12da14e963c0a22b505`。曲线和 CSV 见
[报告 List 章节](../../README.zh-CN.md#list)。没有新增生产代码改动。

## 负载与有效范围

- 1 MiB/key × 50,000 key；100 MiB/key × 500 key，均约 48.8 GiB 逻辑内容。
- 元素 1 KiB。32 个导入连接，以 128 KiB RPUSH 命令、pipeline=4 独立重建两版的初始数据。
- LSET 每次修改一个元素，使用随机 key，并轮换每个 List 的八个均匀分布下标。不是随机遍历全部下标。
- memtier：16 个线程、pipeline=1、80/320/1280/2560/5120 连接，各 10 秒。
- 全部干净测点结束后，另跑 30 秒工作负载，在其中以 task-clock / 199 Hz / DWARF 16 KiB 采样 25 秒。诊断 QPS 不进入对照图。
- 两版启用相同指标，逐 key 校验前后元素数量并检查命令错误。没有同时编译或执行测试；本轮没有重测其他数据库。
- 独立灌入保证初始逻辑内容一致，不代表介质物理状态完全相同。连接档位顺序运行，写入量会随吞吐不同；单次 10 秒曲线没有误差区间。
- 普通 RPUSH 导入后未强制等待所有后台清理。存储指标包含清理工作，不能把它们直接当成单条前台命令的读写次数。

最初 100 MiB PR 试跑在 1280 连接后插入了诊断压测，可能改变后续测点状态，因此最终曲线使用另外一次独立灌入、先完成整轮干净测点的重测。原试跑不作为正式曲线。

## 1 MiB × 50,000 key 结果

五档连接数下 main 为 83.7–100.9k QPS，PR 为 115.2–142.0k，逐档比值为
1.375 / 1.408 / 1.364 / 1.342 / 1.316。全部 50,000 key 测前、测后基数一致，零错误。
P99 并非所有档位改善：1280/2560 连接分别从 45.06/67.58 ms 变为 47.62/69.63 ms；
其他三档下降。曲线、延迟与精确版本见 [CSV](../../list-lset-1048576-1024-k50000-main-pr.csv)。

[这组 PR 的 CPU 样本](../../raw/lavik-lset-large-pr233-759832d8-1048576-k50000-f1024-20260930/diagnostic-c1280/self.txt)
中，目录 Apply 仅占 1.63%，明显低于 100 MiB key 初轮的 7.84%；
主要分配符号为 5.55%，memmove 为 2.89%，FindRecord / UpdatePhysical 为 4.14% / 3.01%。
这两组的负载及采样前写入历史不同，百分比差异只用于确定调查重点，不能当成直接 A/B 收益。
1 MiB 组 1280 连接的 task-clock 采样记录约 285.56 CPU 秒 / 25 秒，约为 11.4 个 CPU 核时间（包含轮询）；RunOnce / PollStorage 自身占比为 3.13% / 1.72%。干净曲线在 320 连接达到峰值，增加至 5120 连接没有继续提高吞吐。

[1 MiB 组 I/O 与提交统计](../../raw/lavik-lset-large-pr233-759832d8-1048576-k50000-f1024-20260930/io-summary.json)
中，1280 / 5120 连接的独立诊断平均每提交批次有 **18.65 / 37.35** 笔事务，
提交队列反压计数增量均为零。先前 8 key 实验约为每批 1 笔，
但两组对象大小、访问集合与写入历史也不同，不能把全部差异只归因于 key 数量。

按命令数归一化，1 MiB 组平均每条 LSET 对应约 0.96 次存储读、11.0 KiB 写入字节；
包含后台清理，不能据此认定每条前台命令的准确读写放大。
`fdatasync` 指标表示存储 API 完成，不等同于物理 NVMe FLUSH 次数：
SPDK 在控制器没有易失写缓存时可以延迟完成一个无需硬件 FLUSH 的请求。

## 100 MiB × 500 key 结果

干净重测中 main 为 7.24–7.41k QPS，PR 为 82.15–107.19k，
逐档比值见 [CSV](../../list-lset-104857600-1024-k500-main-pr.csv)，范围为 **11.24–14.53×**。
全部 500 key 前后基数一致、零错误，两版正常退出。
PR 峰值在 80 连接；继续增加连接没有提高吞吐。
导入均使用 RPUSH，本轮没有把 RESTORE 或批量 LSET 混入命令曲线。

整轮干净测点之后的 [1280 连接 CPU 样本](../../raw/lavik-lset-large-pr233-759832d8-104857600-k500-f1024-clean-grid-20260930/diagnostic-c1280/self.txt)
中，目录 Apply 占 8.24%，元数据块指针表释放 1.76%，
主要分配符号 4.39%，memmove 1.95%，FindRecord / UpdatePhysical 为 3.13% / 2.35%。
下节初轮指令标注所定位的目录工作，在最终重测中仍然突出。
[最终 I/O 与提交统计](../../raw/lavik-lset-large-pr233-759832d8-104857600-k500-f1024-clean-grid-20260930/io-summary.json)
与干净测点、采样测点分别保存。

## 已定位的重复工作

500 key 初轮独立诊断的 [self 样本](../../raw/lavik-lset-large-pr233-759832d8-104857600-k500-f1024-20260930/diagnostic-c1280/self.txt)
中，目录 Apply 占整个进程 CPU 自身样本 **7.84%**，元数据块指针表释放 **1.73%**。
[Apply 指令标注](../../raw/lavik-lset-large-pr233-759832d8-104857600-k500-f1024-20260930/diagnostic-c1280/directory-apply-annotate.txt)
有 **85.67% 的函数内部样本**落在块指针复制/引用计数循环的递增指令附近。
[内联调用链](../../raw/lavik-lset-large-pr233-759832d8-104857600-k500-f1024-20260930/diagnostic-c1280/directory-copy-inline-chain.txt)
将它映射至 [`GroupedMetadataArray::Set`](https://github.com/eloqdata/lavik/blob/759832d8a66e7e6b0d16a12da14e963c0a22b505/include/lavik/storage/detail/grouped_metadata_array.h#L156) 的 `chunks_ = storage_->chunks_`。
采样会存在指令归属偏移，不能把该比例解释为单条加法指令的成本。

这与源码吻合：PR 共享未修改的元数据块，但每次修改仍复制整个外层指针表，
增加所有块的引用，释放旧表时再递减。它随一个 List 的分组数量增长。
下一步优先实验让外层指针表也分层共享，减少这些无关块的复制/引用维护；
保留 owner-local 生命周期、快照隔离、失败回滚与内存计费，不增加数据缓存。

同次采样的主要分配符号占 3.45%，memmove 占 1.88%，物理索引 FindRecord / UpdatePhysical
各占 3.00% / 2.32%。目标页仍完整解码、重新编码，单元素等长更新可以进一步评估局部替换；
但不能把所有分配、拷贝或物理索引成本都算作可消除的工作。
这些百分比来自 CPU 采样，既不等于分配次数，也不提供磁盘延迟占比。

上述初轮 profile 自身有效，但它插在干净测点之间，所以其所在试跑不用于最终 QPS 曲线。

## 早期少 key 实验的限制

以下证据用于解释为什么需要增加 key，不能作为 500/50,000 key 的耗时结论。

在 8 个 100 MiB List、1280 连接下，生产版本的独立
[CPU 采样](../../raw/lavik-lset-deep-759832d8-20260930/diagnostic-c1280/self.txt)
显示 RunOnce / PollStorage 占自身样本 36.50% / 16.61%；目录 Apply 为 1.21%，
主要分配符号为 1.13%，memmove 为 0.92%。轮询会占用 CPU，CPU 样本不能度量协程挂起等待。
LTO 也可能合并不同函数的符号，不能仅凭某个分配器符号名判断业务来源。

为了区分执行与等待，临时在 PR 之上加入每 worker 的计时器，127 次调用采样一次，
退出时汇总；[完整补丁](sampled-stages.patch)没有进入生产 PR。
[8 key 计时结果](../../raw/lavik-lset-stages-950148e2-20260930/stage-summary.json)
有 744,482 次 LSET、5,863 次采样，仅分布在 4 个 owner worker。
存储入口函数平均耗时 131.40 微秒，前驱事务决策等待为 99.90 微秒，约占 76%；
prepare 为 10.57 微秒，其中目标页读取/解码为 3.89 微秒；入口状态锁等待为 0.056 微秒。
各阶段嵌套，不能把它们相加。存储入口计时也不包含调用前的 key intent 排队。

[64 key 计时结果](../../raw/lavik-lset-stages-k64-950148e2-20260930/stage-summary.json)
中入口为 171.08 微秒、前驱决策等待 99.23 微秒，prepare 为 36.66 微秒。
增加 key 会改变分布、读取与并发情况，不能把少 key 的“76% 等待”外推至本轮大负载。

前驱决策等待保证事务失败与恢复顺序。不能为了消除等待直接绕过它。

## 复现

[bench-lset-large.py](bench-lset-large.py) 复用报告的 `run.py`，
[profile-lset-deep.py](profile-lset-deep.py) 保存 CPU 栈、指标与 worker 信息。
在与报告相同的专用 SPDK 测试环境、从仓库根目录执行，例如：

```sh
sudo -n env LAVIK_LSET_NO_PERF=0 python3 \
  perf_reports/lavik-complex-structures-2026-09-26/run_with_memory_guard.py \
  --minimum-available-gib=20 -- python3 \
  perf_reports/lavik-complex-structures-2026-09-26/diagnostics/lset-20260930/bench-lset-large.py \
  lavik --types=list --sizes=1048576 --fields=1024 --keys=50000 \
  --levels=80,320,1280,2560,5120 --full-levels=1 --seconds=10 --mode=point \
  --fill-workers=32 --seed-pipeline=4 --seed-command-bytes=131072 \
  --binary=/absolute/path/to/lavik --source-commit=FULL_COMMIT \
  --source-repo=/absolute/path/to/source --tag=UNIQUE_TAG
```

Main 设置 `LAVIK_LSET_NO_PERF=1`；100 MiB 组改为 `--sizes=104857600 --keys=500`。
服务器启动参数、二进制 SHA256 与每个 memtier 命令保存在对应原始目录。
服务器/客户端地址、CPU 绑定和存储设备沿用 `run.py` 的专用环境设置。
`summarize-lset-io.py RAW_DIRECTORY` 计算每个测量区间的 I/O 差值与事务批量；
`summarize-lset-stages.py RAW_DIRECTORY` 汇总临时计时日志。

复现临时计时时，从 `759832d8` 的独立 worktree 应用补丁并单独编译，
再用独立标签运行基准；不要将该二进制的 QPS 混入生产曲线。
CPU 二进制采样文件保留在测试主机，报告保存可读的自身/包含子调用样本、
线程信息、采样参数、指标、原始 memtier JSON 与退出状态。
