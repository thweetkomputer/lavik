# PR #291 扩展优化：与 main 1dd8a5b3 的 QPS 对照

比较 [PR #291](https://github.com/eloqdata/lavik/pull/291) 的完整两笔改动与已合并 #290 的 main。所有结果均为本次重新测量，未复用早期 push/pop 单独优化的结果。

本次主要吞吐收益为 RPUSH/LPOP **+9.3%**、变长 LSET **+20.8%** 和 HSET **+5.1%**，取三轮配对增幅中位数。前两项的 p99 同时明显上升。HSET 三轮为 +5.1%、+6.9%、-1.2%，尚不是每轮稳定收益。其余测量只出现小幅 QPS 变化，完整范围见表；这些结果只适用于下述 8 MiB/key、320 连接负载。

## 测量范围

- main：`1dd8a5b35aefc9215e0090204a0680efe9848e4a`。
- 候选：在上述 main 上顺序应用 PR 的 `309e2af3`、`79bdbfeda`，得到 `74ba1d1ea3af697666b7eeaa06908dd4572eff95`。PR 原始 head 仍为 `79bdbfeda`；此处专门排除 main 新增 #290 的干扰。集成分支为 [`bench/pr291-main-1dd8a5b3-20261008`](https://github.com/thweetkomputer/lavik/tree/bench/pr291-main-1dd8a5b3-20261008)。
- 每个 key 初始 8192 个 1 KiB 元素/值，名义 8 MiB，共 8 个 key。Hash 字段和编码有额外空间；LSET 更新后值长为 1008 或 1024 B。320 连接、16 个客户端线程、pipeline 1，每点 30 秒。QPS 是完成的命令数/客户端实际运行时间，混合操作不按一对命令计数。
- 七项负载各三组配对，共 42 个观测。版本顺序为 main→候选、候选→main、main→候选。同轮同操作的两边使用相同进程 digest seed 和客户端随机种子，跨轮更换种子。固定种子的 shim 仅在进入 main 前初始化种子，不挂请求路径；运行时读进程内存核对种子。
- 每点重新启动服务、清空允许使用的六块独立 scratch NVMe、重新填充并等待提交队列和 cleaner 空闲。继承既有基准的 settle 判据：间隔两秒的两次检查均满足队列为空、cleaner 不运行、总 backlog ≤16 MiB。各点残留 backlog 保存在 observations.csv，不假设全部为零。
- 服务端 12 workers，CPU 0–15，kernel TCP + SPDK；关闭 defrag 和定时 Tomb Raider，其他参数见原始 server-command.json。两边 CMake cache 完全相同：RelWithDebInfo、`-O2 -g -DNDEBUG`、`-march=native`、BUILD_TESTING=OFF、LAVIK_ENABLE_TEST_FAULTS=OFF，Bycorf 与依赖相同。
- 不含 5120 连接，不替换现有四系统全量并发曲线。本次没有 perf 采样；结果是端到端固定连接闭环测量。

## 结果

绝对值列分别取三轮中位数；增幅列取三个 **候选/main 配对比值的中位数**，因此增幅不必等于两列中位数之比。p99 是每次运行的 p99 再做同样聚合，没有合并各轮延迟样本。

|操作|main QPS|候选 QPS|配对 QPS 变化|三轮增幅范围|main p99 ms|候选 p99 ms|配对 p99 变化|
|---|---:|---:|---:|---:|---:|---:|---:|
|LPUSH / RPOP|45,956|46,436|+0.6%|+0.4% 至 +1.7%|30.16|30.93|+2.5%|
|RPUSH / LPOP|57,302|62,981|+9.3%|+8.9% 至 +13.5%|21.54|44.35|+104.3%|
|LSET（1008/1024 B）|39,513|46,742|+20.8%|+15.7% 至 +50.6%|31.72|86.89|+172.7%|
|ZINCRBY|51,810|52,534|+1.4%|+1.1% 至 +2.1%|27.26|27.18|-1.7%|
|随机分数 ZADD / ZPOPMIN|23,827|23,983|+0.7%|-0.5% 至 +1.1%|54.21|50.92|-7.1%|
|HSET（替换已有字段）|31,954|33,379|+5.1%|-1.2% 至 +6.9%|224.18|177.86|-10.6%|
|SADD / SREM|50,491|50,656|+0.5%|-0.2% 至 +0.6%|23.13|23.84|+3.4%|

## 负载语义与边界

- List push/pop：每条命令独立均匀选 key，再独立以 50/50 概率选 push 或 pop；两种方向分开测。每次 push 返回长度检查 [4096,16384]，每次 pop 必须非空且 1024 B；最终逐 key 校验初值 + push − pop。
- LSET：每条命令随机选 key，再从八个分散位置选一处，写入唯一内容。不同连接分别写 1008/1024 B，产生长短变化；并非每一条命令都保证长度变化。
- ZINCRBY：随机 key、八个已有成员之一，每次加 1，保证实际改变分数；持续更新会改变分数分布和所在页，因此不是静态布局的查找微基准。
- ZADD/ZPOPMIN：独立随机 key、50/50 操作；ZADD NX 使用唯一 1 KiB member，分数均匀抽取初始分数范围，ZPOPMIN 每次删一个。最终逐 key 检查初值 + 成功新增 − pop。运行中分数分布会变化，不能把全部 ZADD 描述为当前集合的中间插入。
- HSET：随机 key、八个分散的已有字段之一，每次换成唯一 1 KiB 值；HSET 返回 0 表示没有新增字段，不表示值没有变化。此点不覆盖新字段插入、HSETNX 或 HDEL。
- Set：独立随机 key 和 50/50 SADD/SREM，从 16384 个成员的固定池均匀选一个，初始存在 8192 个。返回 0 的空操作保留在 QPS 中，返回 1 才计入实际增删；用真实返回值校验最终数量。

|Set 轮次|版本|真正增删占请求比例|最终每 key 数量范围|
|---:|---|---:|---:|
|1|main|50.07%|8150–8321|
|1|pr291|50.06%|8125–8281|
|2|pr291|49.99%|8131–8272|
|2|main|50.01%|8160–8250|
|3|main|50.03%|8116–8289|
|3|pr291|50.03%|8149–8297|

## 逐轮数据

|操作|轮次|main QPS|候选 QPS|QPS 变化|main p99 ms|候选 p99 ms|p99 变化|
|---|---:|---:|---:|---:|---:|---:|---:|
|LPUSH / RPOP|1|45,678|46,473|+1.7%|31.53|30.93|-1.9%|
|LPUSH / RPOP|2|46,268|46,436|+0.4%|29.88|30.64|+2.5%|
|LPUSH / RPOP|3|45,956|46,251|+0.6%|30.16|31.89|+5.7%|
|RPUSH / LPOP|1|57,302|62,658|+9.3%|21.13|45.03|+113.1%|
|RPUSH / LPOP|2|57,818|62,981|+8.9%|21.71|44.35|+104.3%|
|RPUSH / LPOP|3|56,803|64,461|+13.5%|21.54|40.44|+87.8%|
|LSET（1008/1024 B）|1|30,373|45,728|+50.6%|65.48|104.03|+58.9%|
|LSET（1008/1024 B）|2|40,400|46,742|+15.7%|31.72|86.89|+173.9%|
|LSET（1008/1024 B）|3|39,513|47,739|+20.8%|28.81|78.55|+172.7%|
|ZINCRBY|1|51,810|52,368|+1.1%|27.26|27.81|+2.0%|
|ZINCRBY|2|51,927|52,997|+2.1%|27.22|26.74|-1.7%|
|ZINCRBY|3|51,803|52,534|+1.4%|28.13|27.18|-3.4%|
|随机分数 ZADD / ZPOPMIN|1|23,839|23,713|-0.5%|53.29|54.27|+1.8%|
|随机分数 ZADD / ZPOPMIN|2|23,827|23,996|+0.7%|54.21|47.46|-12.5%|
|随机分数 ZADD / ZPOPMIN|3|23,718|23,983|+1.1%|54.82|50.92|-7.1%|
|HSET（替换已有字段）|1|31,954|33,587|+5.1%|228.07|177.86|-22.0%|
|HSET（替换已有字段）|2|29,339|31,356|+6.9%|224.18|232.88|+3.9%|
|HSET（替换已有字段）|3|33,772|33,379|-1.2%|176.68|157.88|-10.6%|
|SADD / SREM|1|50,491|50,753|+0.5%|22.97|23.75|+3.4%|
|SADD / SREM|2|50,637|50,535|-0.2%|23.13|24.03|+3.9%|
|SADD / SREM|3|50,348|50,656|+0.6%|23.19|23.84|+2.8%|

## 验证与解读

42 个观测均检查客户端响应、客户端/服务端命令计数、操作比例、最终逐 key 基数、允许范围、二进制 SHA256、种子及正常退出。新增客户端先对独立模拟 RESP 服务检查四项新操作的请求语义、计数和返回值处理；该检查不计入性能数据。

同一 main 集成后的普通构建：main 281 项相关单元测试通过；候选 282 项单元测试、4 项有序集合/冷恢复用例和 10 项 Hash 集成用例通过，10 项需要故障注入的 Hash 用例因关闭注入而跳过。PR 原分支的完整故障注入验证另见 PR 描述，不与本次计数混加。

三组配对仍是有限样本。表中范围暴露波动；不能仅据中位数断言小幅变化是稳定收益。只测试 8 MiB/key、320 连接，以及以上指定操作；没有覆盖全范围 LTRIM、LINSERT、HSETNX/HDEL、ZREM/ZPOPMAX 或其他并发。固定连接负载在吞吐提高时也增加请求速率，p99 的变化不能单凭此实验归因于吞吐提高；尚无相同 QPS 的延迟对照。新增实现的减少读取/分配意图与端到端 QPS 收益需要分开判断。

测试中仅修正一次测量后的审计条件：按实际命令种类数判断是否为混合操作，避免把带下划线的单命令标签 LSET_RESIZE 误判。修正发生于首组 LPUSH/RPOP 的候选点准备阶段，基线已完成；未改变负载、种子或测量，LPUSH/RPOP 的新旧检查等价。两版脚本及 SHA 均保留于 harness-audit-correction.json 与 harness-provenance-v1.json。

测试结束已检查六块设备恢复 nvme 驱动、hugepages 和 VFIO no-IOMMU 设置恢复、无遗留服务器，详见 host-restored.json。

[完整分析 JSON](analysis.json) · [摘要 CSV](summary.csv) · [逐点 CSV](observations.csv) · [版本/二进制](versions.json) · [测量协议](protocol.json) · [宿主与工具链](host-and-toolchain.json) · [校验脚本](analyze.py) · [文件校验清单](artifact-manifest.json)

脚本保留实测时的绝对路径和专用设备允许清单，复现时应先映射工作目录并审查设备清单，不可直接照搬设备操作到其他主机。

## 原始数据索引

|操作|轮次|版本|结果|客户端|运行来源|
|---|---:|---|---|---|---|
|LPUSH / RPOP|1|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lpush_rpop-r1-20261008/list-8388608-1024-lpush_rpop-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lpush_rpop-r1-20261008/list-8388608-1024-lpush_rpop-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lpush_rpop-r1-20261008/provenance-point-list-320.json)|
|LPUSH / RPOP|1|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lpush_rpop-r1-20261008/list-8388608-1024-lpush_rpop-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lpush_rpop-r1-20261008/list-8388608-1024-lpush_rpop-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lpush_rpop-r1-20261008/provenance-point-list-320.json)|
|RPUSH / LPOP|1|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-rpush_lpop-r1-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-rpush_lpop-r1-20261008/list-8388608-1024-rpush_lpop-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-rpush_lpop-r1-20261008/provenance-point-list-320.json)|
|RPUSH / LPOP|1|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-rpush_lpop-r1-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-rpush_lpop-r1-20261008/list-8388608-1024-rpush_lpop-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-rpush_lpop-r1-20261008/provenance-point-list-320.json)|
|LSET（1008/1024 B）|1|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lset_resize-r1-20261008/list-8388608-1024-lset_resize-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lset_resize-r1-20261008/list-8388608-1024-lset_resize-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lset_resize-r1-20261008/provenance-point-list-320.json)|
|LSET（1008/1024 B）|1|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lset_resize-r1-20261008/list-8388608-1024-lset_resize-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lset_resize-r1-20261008/list-8388608-1024-lset_resize-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lset_resize-r1-20261008/provenance-point-list-320.json)|
|ZINCRBY|1|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zincrby-r1-20261008/zset-8388608-1024-zincrby-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zincrby-r1-20261008/zset-8388608-1024-zincrby-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zincrby-r1-20261008/provenance-point-zset-320.json)|
|ZINCRBY|1|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zincrby-r1-20261008/zset-8388608-1024-zincrby-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zincrby-r1-20261008/zset-8388608-1024-zincrby-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zincrby-r1-20261008/provenance-point-zset-320.json)|
|随机分数 ZADD / ZPOPMIN|1|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zadd_middle_zpopmin-r1-20261008/zset-8388608-1024-zadd_middle_zpopmin-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zadd_middle_zpopmin-r1-20261008/zset-8388608-1024-zadd_middle_zpopmin-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zadd_middle_zpopmin-r1-20261008/provenance-point-zset-320.json)|
|随机分数 ZADD / ZPOPMIN|1|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zadd_middle_zpopmin-r1-20261008/zset-8388608-1024-zadd_middle_zpopmin-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zadd_middle_zpopmin-r1-20261008/zset-8388608-1024-zadd_middle_zpopmin-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zadd_middle_zpopmin-r1-20261008/provenance-point-zset-320.json)|
|HSET（替换已有字段）|1|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-hash-8388608-hset-r1-20261008/hash-8388608-1024-hset-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-hash-8388608-hset-r1-20261008/hash-8388608-1024-hset-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-hash-8388608-hset-r1-20261008/provenance-point-hash-320.json)|
|HSET（替换已有字段）|1|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-hash-8388608-hset-r1-20261008/hash-8388608-1024-hset-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-hash-8388608-hset-r1-20261008/hash-8388608-1024-hset-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-hash-8388608-hset-r1-20261008/provenance-point-hash-320.json)|
|SADD / SREM|1|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-set-8388608-sadd_srem-r1-20261008/set-8388608-1024-sadd_srem-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-set-8388608-sadd_srem-r1-20261008/set-8388608-1024-sadd_srem-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-set-8388608-sadd_srem-r1-20261008/provenance-point-set-320.json)|
|SADD / SREM|1|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-set-8388608-sadd_srem-r1-20261008/set-8388608-1024-sadd_srem-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-set-8388608-sadd_srem-r1-20261008/set-8388608-1024-sadd_srem-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-set-8388608-sadd_srem-r1-20261008/provenance-point-set-320.json)|
|LPUSH / RPOP|2|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lpush_rpop-r2-20261008/list-8388608-1024-lpush_rpop-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lpush_rpop-r2-20261008/list-8388608-1024-lpush_rpop-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lpush_rpop-r2-20261008/provenance-point-list-320.json)|
|LPUSH / RPOP|2|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lpush_rpop-r2-20261008/list-8388608-1024-lpush_rpop-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lpush_rpop-r2-20261008/list-8388608-1024-lpush_rpop-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lpush_rpop-r2-20261008/provenance-point-list-320.json)|
|RPUSH / LPOP|2|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-rpush_lpop-r2-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-rpush_lpop-r2-20261008/list-8388608-1024-rpush_lpop-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-rpush_lpop-r2-20261008/provenance-point-list-320.json)|
|RPUSH / LPOP|2|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-rpush_lpop-r2-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-rpush_lpop-r2-20261008/list-8388608-1024-rpush_lpop-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-rpush_lpop-r2-20261008/provenance-point-list-320.json)|
|LSET（1008/1024 B）|2|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lset_resize-r2-20261008/list-8388608-1024-lset_resize-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lset_resize-r2-20261008/list-8388608-1024-lset_resize-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lset_resize-r2-20261008/provenance-point-list-320.json)|
|LSET（1008/1024 B）|2|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lset_resize-r2-20261008/list-8388608-1024-lset_resize-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lset_resize-r2-20261008/list-8388608-1024-lset_resize-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lset_resize-r2-20261008/provenance-point-list-320.json)|
|ZINCRBY|2|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zincrby-r2-20261008/zset-8388608-1024-zincrby-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zincrby-r2-20261008/zset-8388608-1024-zincrby-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zincrby-r2-20261008/provenance-point-zset-320.json)|
|ZINCRBY|2|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zincrby-r2-20261008/zset-8388608-1024-zincrby-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zincrby-r2-20261008/zset-8388608-1024-zincrby-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zincrby-r2-20261008/provenance-point-zset-320.json)|
|随机分数 ZADD / ZPOPMIN|2|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zadd_middle_zpopmin-r2-20261008/zset-8388608-1024-zadd_middle_zpopmin-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zadd_middle_zpopmin-r2-20261008/zset-8388608-1024-zadd_middle_zpopmin-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zadd_middle_zpopmin-r2-20261008/provenance-point-zset-320.json)|
|随机分数 ZADD / ZPOPMIN|2|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zadd_middle_zpopmin-r2-20261008/zset-8388608-1024-zadd_middle_zpopmin-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zadd_middle_zpopmin-r2-20261008/zset-8388608-1024-zadd_middle_zpopmin-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zadd_middle_zpopmin-r2-20261008/provenance-point-zset-320.json)|
|HSET（替换已有字段）|2|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-hash-8388608-hset-r2-20261008/hash-8388608-1024-hset-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-hash-8388608-hset-r2-20261008/hash-8388608-1024-hset-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-hash-8388608-hset-r2-20261008/provenance-point-hash-320.json)|
|HSET（替换已有字段）|2|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-hash-8388608-hset-r2-20261008/hash-8388608-1024-hset-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-hash-8388608-hset-r2-20261008/hash-8388608-1024-hset-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-hash-8388608-hset-r2-20261008/provenance-point-hash-320.json)|
|SADD / SREM|2|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-set-8388608-sadd_srem-r2-20261008/set-8388608-1024-sadd_srem-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-set-8388608-sadd_srem-r2-20261008/set-8388608-1024-sadd_srem-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-set-8388608-sadd_srem-r2-20261008/provenance-point-set-320.json)|
|SADD / SREM|2|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-set-8388608-sadd_srem-r2-20261008/set-8388608-1024-sadd_srem-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-set-8388608-sadd_srem-r2-20261008/set-8388608-1024-sadd_srem-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-set-8388608-sadd_srem-r2-20261008/provenance-point-set-320.json)|
|LPUSH / RPOP|3|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lpush_rpop-r3-20261008/list-8388608-1024-lpush_rpop-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lpush_rpop-r3-20261008/list-8388608-1024-lpush_rpop-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lpush_rpop-r3-20261008/provenance-point-list-320.json)|
|LPUSH / RPOP|3|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lpush_rpop-r3-20261008/list-8388608-1024-lpush_rpop-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lpush_rpop-r3-20261008/list-8388608-1024-lpush_rpop-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lpush_rpop-r3-20261008/provenance-point-list-320.json)|
|RPUSH / LPOP|3|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-rpush_lpop-r3-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-rpush_lpop-r3-20261008/list-8388608-1024-rpush_lpop-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-rpush_lpop-r3-20261008/provenance-point-list-320.json)|
|RPUSH / LPOP|3|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-rpush_lpop-r3-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-rpush_lpop-r3-20261008/list-8388608-1024-rpush_lpop-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-rpush_lpop-r3-20261008/provenance-point-list-320.json)|
|LSET（1008/1024 B）|3|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lset_resize-r3-20261008/list-8388608-1024-lset_resize-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lset_resize-r3-20261008/list-8388608-1024-lset_resize-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-list-8388608-lset_resize-r3-20261008/provenance-point-list-320.json)|
|LSET（1008/1024 B）|3|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lset_resize-r3-20261008/list-8388608-1024-lset_resize-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lset_resize-r3-20261008/list-8388608-1024-lset_resize-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-list-8388608-lset_resize-r3-20261008/provenance-point-list-320.json)|
|ZINCRBY|3|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zincrby-r3-20261008/zset-8388608-1024-zincrby-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zincrby-r3-20261008/zset-8388608-1024-zincrby-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zincrby-r3-20261008/provenance-point-zset-320.json)|
|ZINCRBY|3|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zincrby-r3-20261008/zset-8388608-1024-zincrby-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zincrby-r3-20261008/zset-8388608-1024-zincrby-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zincrby-r3-20261008/provenance-point-zset-320.json)|
|随机分数 ZADD / ZPOPMIN|3|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zadd_middle_zpopmin-r3-20261008/zset-8388608-1024-zadd_middle_zpopmin-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zadd_middle_zpopmin-r3-20261008/zset-8388608-1024-zadd_middle_zpopmin-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-zset-8388608-zadd_middle_zpopmin-r3-20261008/provenance-point-zset-320.json)|
|随机分数 ZADD / ZPOPMIN|3|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zadd_middle_zpopmin-r3-20261008/zset-8388608-1024-zadd_middle_zpopmin-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zadd_middle_zpopmin-r3-20261008/zset-8388608-1024-zadd_middle_zpopmin-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-zset-8388608-zadd_middle_zpopmin-r3-20261008/provenance-point-zset-320.json)|
|HSET（替换已有字段）|3|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-hash-8388608-hset-r3-20261008/hash-8388608-1024-hset-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-hash-8388608-hset-r3-20261008/hash-8388608-1024-hset-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-hash-8388608-hset-r3-20261008/provenance-point-hash-320.json)|
|HSET（替换已有字段）|3|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-hash-8388608-hset-r3-20261008/hash-8388608-1024-hset-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-hash-8388608-hset-r3-20261008/hash-8388608-1024-hset-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-hash-8388608-hset-r3-20261008/provenance-point-hash-320.json)|
|SADD / SREM|3|main|[结果](../../raw/lavik-main1dd8a5b3-pr291full-set-8388608-sadd_srem-r3-20261008/set-8388608-1024-sadd_srem-c320.result.json)|[客户端](../../raw/lavik-main1dd8a5b3-pr291full-set-8388608-sadd_srem-r3-20261008/set-8388608-1024-sadd_srem-c320.client.json)|[来源](../../raw/lavik-main1dd8a5b3-pr291full-set-8388608-sadd_srem-r3-20261008/provenance-point-set-320.json)|
|SADD / SREM|3|pr291|[结果](../../raw/lavik-pr29174ba1d1e-pr291full-set-8388608-sadd_srem-r3-20261008/set-8388608-1024-sadd_srem-c320.result.json)|[客户端](../../raw/lavik-pr29174ba1d1e-pr291full-set-8388608-sadd_srem-r3-20261008/set-8388608-1024-sadd_srem-c320.client.json)|[来源](../../raw/lavik-pr29174ba1d1e-pr291full-set-8388608-sadd_srem-r3-20261008/provenance-point-set-320.json)|
