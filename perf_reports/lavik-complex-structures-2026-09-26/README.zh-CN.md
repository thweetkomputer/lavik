# 复杂数据结构性能：Redis、Valkey、Lavik 与 Kvrocks

[English](README.md)

本报告在同一台服务端和一台独立的 memtier 客户端上比较五类
Redis 兼容数据结构。每张图固定数据结构、每个 key 的逻辑数据量和
每个元素的字节数。横轴为连接数，纵轴为每秒完成的命令数。

## 2026-09-30 main 与 PR #228

[PR #222](https://github.com/eloqdata/lavik/pull/222) 已合并，当前 main 为 `a6e93d3d`。图中已移除已合并 PR 的独立曲线；本轮新优化 [PR #228](https://github.com/eloqdata/lavik/pull/228) 只在完成 A/B 的条件下叠加显示。

**最新 main 已复测：Hash/1 MiB/128 B, Hash/1 MiB/1024 B, Hash/100 MiB/128 B, Hash/100 MiB/1024 B, Set/1 MiB/128 B, Set/1 MiB/1024 B, Set/100 MiB/128 B, Set/100 MiB/1024 B。** 精确版本、二进制摘要和未合并 PR 来源见 [绘图来源](published-main.json)。Stream、List、Sorted Set 的结果和图继续保留。

PR #228 当前代码为 `80792c41`。已发布的 PR 曲线均对应此提交。

本轮先用 perf 找分配、拷贝和重复工作，PR #228 减少临时容器、元数据查询和额外调度，没有增加数据缓存或改变落盘格式。**尚未在所有写入负载上达到 Kvrocks 水平。** 图中主测点不运行 perf，30 秒工作负载中的 20 秒采样另存原始目录；[采样脚本](profile_grouped_writes.py)可复现相同流程。

点查和写入测 80/320/1280/2560/5120 连接，完整读取测 1 MiB 档的
16/80、100 MiB 档的 1/4/16 连接；每点八秒。Redis、Valkey 不持久化，
Kvrocks 使用无压缩 RAID0、关闭 WAL、启用 80 GiB block cache 和 blob
cache；Lavik 在六块 NVMe 上用 SPDK 提交。这些配置影响绝对写入 QPS。
每点仅测一次，没有置信区间。原始运行记录见 [raw/](raw/)，绘图代码见
[plot_set_hash_high_keys.py](plot_set_hash_high_keys.py)；早期写入与内存调查
分别见 [HSET 诊断](diagnostics/hset-20260929/README.md)和
[HGETALL 内存调查](diagnostics/hgetall-oom-20260929/README.md)。

[同块数据与 Commit 合并刷盘试验](diagnostics/hset-coalescing-20260929/README.md)的正确性检查通过，
但 HSET 的下降经 20 秒复测确认，该改动已撤回；主图显示当前 NVMe 优化版本。

[I/O 计数诊断](diagnostics/hset-io-20260929/README.md)记录了 HSET 的存储读写量（包含后台清理）。

### 本轮写入结果

全部八种 Hash/Set 条件已完成最新 main 与 PR #228 对比，共 **200 个八秒测点，零错误**，测前测后逐 key 校验通过。同连接数下，SADD + SREM 为 **+7.7% 至 +35.9%**，HSET 为 **+0.7% 至 +19.4%**；这是本轮单次测量范围，不代表每种负载都有同等收益。逐点比值和四库峰值见 [计算结果](pr-228-comparison.json)，下方保留完整曲线。

100 MiB Set、128 B 元素的额外持续 SMEMBERS 检查在 main 和 PR 都出现了内存准入错误；**八秒测点零错误不等于持续并发稳定**。失败原始记录、原因和完整读取复测结果见 SMEMBERS/HGETALL 小节，不计入有效吞吐对比。

### perf：已消除的工作与剩余开销

在 1,280 连接的独立写入诊断中，Set/128 B 的分配和释放函数占 CPU 自身样本 **12.19% → 10.72%**，Hash/1 KiB 为 **16.80% → 14.53%**。活动分组查找分别为 **2.01% → 0.19%**、**2.43% → 0.93%**。这些是全部符号的 CPU 采样占比，不是分配次数；内联操作可能计入调用者，不能据此计算全部拷贝字节数。

PR 将单页写入的临时数组放进协程帧，取消临时树容器和重复的 extent 查询；未改变路由的更新直接替换节点；物理索引单槽替换直接复制紧凑数组，省去展开旧坐标再重新编码的中间向量。旧快照、内存准入和提交依赖仍保留。

已命名拷贝/清零函数仍占约 **2%–3%**，物理记录查找约 **4%–5%**。写入提升尚不足以补齐与 Kvrocks 的差距；后续应继续核对同一次修改在读、发布、回收阶段的重复查找和临时对象，再评估元数据更新算法。当前证据不足以把全部差距归因于读盘或分配器；四库持久化和缓存配置也不同。

[Set main 采样](raw/lavik-maina6d-set-1m-k50000-f128-20260930/diagnostic-c1280/cpu-categories.json)、[Set PR 采样](raw/lavik-worktrim8079-set-1m-k50000-f128-20260930/diagnostic-c1280/cpu-categories.json)、[Hash main 采样](raw/lavik-maina6d-hash-1m-k50000-f1024-20260930/diagnostic-c1280/cpu-categories.json)、[Hash PR 采样](raw/lavik-worktrim8079-hash-1m-k50000-f1024-20260930/diagnostic-c1280/cpu-categories.json)。同目录保留全部符号、采样参数及吞吐结果。

## Hash

下列点查/写入图每张包含两个命令；1 MiB 和 100 MiB 档分别使用 50,000 和 500 个 key。

### HGET / HSET

#### 1 MiB

![Hash 1 MiB、128 B：HGET 与 HSET QPS 随连接数变化](charts/hash-1048576-128-ab.png)

**最新 main `a6e93d3d` 与 [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41` 实测。** 50,000 × 1 MiB key，128 B 元素，各 12 个测点、零错误，测量前后逐 key 校验。HSET 同连接数下为 main 的 **1.01–1.16 倍**。曲线使用无采样的八秒测点；单次差异不能视为稳定收益，perf 诊断在有采样的条件下单独保存。
[main raw](raw/lavik-maina6d-hash-1m-k50000-f128-20260930/), [PR raw](raw/lavik-worktrim8079-hash-1m-k50000-f128-20260930/).

![Hash 1 MiB、1 KiB：HGET 与 HSET QPS 随连接数变化](charts/hash-1048576-1024-ab.png)

**最新 main `a6e93d3d` 与 [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41` 实测。** 50,000 × 1 MiB key，1024 B 元素，各 12 个测点、零错误，测量前后逐 key 校验。HSET 同连接数下为 main 的 **1.02–1.19 倍**。曲线使用无采样的八秒测点；单次差异不能视为稳定收益，perf 诊断在有采样的条件下单独保存。
[main raw](raw/lavik-maina6d-hash-1m-k50000-f1024-20260930/), [PR raw](raw/lavik-worktrim8079-hash-1m-k50000-f1024-20260930/).

#### 100 MiB

![Hash 100 MiB、128 B：HGET 与 HSET QPS 随连接数变化](charts/hash-104857600-128-ab.png)

**最新 main `a6e93d3d` 与 [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41` 实测。** 500 × 100 MiB key，128 B 元素，各 13 个测点、零错误，测量前后逐 key 校验。HSET 同连接数下为 main 的 **1.11–1.12 倍**。曲线使用无采样的八秒测点；单次差异不能视为稳定收益，perf 诊断在有采样的条件下单独保存。
[main raw](raw/lavik-maina6d-hash-100m-k500-f128-20260930/), [PR raw](raw/lavik-worktrim8079-hash-100m-k500-f128-20260930/).

数据仅用 RESTORE 预置，待事务清理完成后，main 与 PR 均重启恢复再测；不与批量 SADD/HSET 导入耗时混比。 [Seed provenance](raw/lavik-seedmaina6d-hash-100m-k500-f128-20260930/).

![Hash 100 MiB、1 KiB：HGET 与 HSET QPS 随连接数变化](charts/hash-104857600-1024-ab.png)

**最新 main `a6e93d3d` 与 [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41` 实测。** 500 × 100 MiB key，1024 B 元素，各 13 个测点、零错误，测量前后逐 key 校验。HSET 同连接数下为 main 的 **1.06–1.16 倍**。曲线使用无采样的八秒测点；单次差异不能视为稳定收益，perf 诊断在有采样的条件下单独保存。
[main raw](raw/lavik-maina6d-hash-100m-k500-f1024-20260930/), [PR raw](raw/lavik-worktrim8079-hash-100m-k500-f1024-20260930/).

数据仅用 RESTORE 预置，待事务清理完成后，main 与 PR 均重启恢复再测；不与批量 SADD/HSET 导入耗时混比。 [Seed provenance](raw/lavik-seedmaina6d-hash-100m-k500-f1024-20260930/).

**HGET 固定数据长测核对：** 原八秒曲线中，PR 在 1,280 / 2,560 连接下比 main 低约 23% / 20%，这些点保留。之后在同一份数据上、无写入和 perf，按 main → PR 顺序各做三次 30 秒、1,280 连接 HGET：main 为 **417,998 / 417,250 / 441,911 QPS**，PR 为 **412,563 / 405,788 / 411,345 QPS**，PR 均值仍低 **3.7%**。500 个 key 的基数测前测后完全一致，零错误。约 20% 的差距未在这组固定数据复测中重现，但这几次顺序重复也不能排除较小的回退，不能声称读性能提升。 [Results](hash-104857600-1024-point-read-repeats.json), [main raw](raw/lavik-pointcheck-maina6d-hash-100m-k500-f1024-20260930/), [PR raw](raw/lavik-pointcheck-worktrim8079-hash-100m-k500-f1024-20260930/), [script](repeat_grouped_point_reads.py).

### HGETALL

#### 1 MiB

![Hash 1 MiB、128 B：HGETALL QPS 随连接数变化](charts/hash-1048576-128-ab-full.png)

**80 连接长测核对：** 每个版本连续三次 30 秒、不启用 perf，main 为 **1,830, 1,815, 1,797 QPS**，PR 为 **1,861, 1,857, 1,842 QPS**；均值比为 **1.022×**。两端使用同一份已恢复数据，50,000 个 key 测前测后基数完全一致，零错误。以上曲线仍使用原八秒测点；长测按版本先后执行，仅三次重复，不提供置信区间。 [Results](hash-1048576-128-full-read-repeats.json), [main raw](raw/lavik-fullcheck-maina6d-hash-1m-k50000-f128-20260930/), [PR raw](raw/lavik-fullcheck-worktrim8079-hash-1m-k50000-f128-20260930/), [script](repeat_grouped_full_reads.py).

**返回 main 核对：** PR 之后保留同一份数据，再运行 main 三次，得到 **1,842, 1,838, 1,842 QPS**；PR / 返回 main 的均值比为 **1.007×**，逐 key 校验通过、零错误。这组检查未确认 HGETALL 的稳定回退。 [Raw](raw/lavik-fullcheck-returnmaina6d-hash-1m-k50000-f128-20260930/).

独立 HGETALL 诊断（不计入上述三次重复）中，main / PR 的内存搬运函数占自身 CPU 样本约 **16.63% / 15.89%**，Hash 元素向量追加约 **9.68% / 9.18%**。两版均存在这些热点。源码中 `LoadGroupedHashValue` 按元素追加而未按已知总数预留向量容量，是待实验验证的优化候选；追加函数的全部采样不能等同于可消除的扩容成本。[main profile](raw/lavik-fullcheck-maina6d-hash-1m-k50000-f128-20260930/diagnostic-full/self.txt)、[PR profile](raw/lavik-fullcheck-worktrim8079-hash-1m-k50000-f128-20260930/diagnostic-full/self.txt)。复现时给重复脚本加 `--profile-full-read`，采样在三次干净重复之后单独运行。


![Hash 1 MiB、1 KiB：HGETALL QPS 随连接数变化](charts/hash-1048576-1024-ab-full.png)

#### 100 MiB

![Hash 100 MiB、128 B：HGETALL QPS 随连接数变化](charts/hash-104857600-128-ab-full.png)

![Hash 100 MiB、1 KiB：HGETALL QPS 随连接数变化](charts/hash-104857600-1024-ab-full.png)

### 批量导入（HSET）

#### 1 MiB / 1024 B

![Hash batched HSET import](charts/hash-1048576-1024-k50000-fill.png)

历史导入测量：Lavik main `ebe28dd5`，不是本轮 `a6e93d3d` / PR #228 的复测。

四库统一用 HSET，每条 16 个元素、8 个连接、pipeline 64；main 灌入耗时 **500.3 秒**。持久化配置仍不同。

#### 1 MiB / 128 B

![Hash batched HSET import](charts/hash-1048576-128-k50000-fill.png)

历史导入测量：Lavik main `ebe28dd5`，不是本轮 `a6e93d3d` / PR #228 的复测。

四库统一用 HSET，每条 128 个元素、8 个连接、pipeline 64；main 灌入耗时 **1306.3 秒**。持久化配置仍不同。

### RESTORE

main `a6e93d3d`，8 个并发 RESTORE 客户端，各导入 500 个 100 MiB key，逐 key 校验通过。以下是预置数据的独立计时，不含后续清理等待和恢复，不与其他数据库的批量 SADD/HSET 导入混比。

- 128 B: **288.4 秒**. [Raw](raw/lavik-seedmaina6d-hash-100m-k500-f128-20260930/hash-104857600-128.fill.json).
- 1024 B: **111.5 秒**. [Raw](raw/lavik-seedmaina6d-hash-100m-k500-f1024-20260930/hash-104857600-1024.fill.json).

## Set

下列点查/写入图每张包含两个命令；1 MiB 和 100 MiB 档分别使用 50,000 和 500 个 key。

### SISMEMBER / SADD/SREM

#### 1 MiB

![Set 1 MiB、128 B：SISMEMBER 与 SADD/SREM QPS 随连接数变化](charts/set-1048576-128-ab.png)

**最新 main `a6e93d3d` 与 [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41` 实测。** 50,000 × 1 MiB key，128 B 元素，各 12 个测点、零错误，测量前后逐 key 校验。SADD + SREM 同连接数下为 main 的 **1.08–1.18 倍**。曲线使用无采样的八秒测点；单次差异不能视为稳定收益，perf 诊断在有采样的条件下单独保存。
[main raw](raw/lavik-maina6d-set-1m-k50000-f128-20260930/), [PR raw](raw/lavik-worktrim8079-set-1m-k50000-f128-20260930/).

![Set 1 MiB、1 KiB：SISMEMBER 与 SADD/SREM QPS 随连接数变化](charts/set-1048576-1024-ab.png)

**最新 main `a6e93d3d` 与 [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41` 实测。** 50,000 × 1 MiB key，1024 B 元素，各 12 个测点、零错误，测量前后逐 key 校验。SADD + SREM 同连接数下为 main 的 **1.12–1.19 倍**。曲线使用无采样的八秒测点；单次差异不能视为稳定收益，perf 诊断在有采样的条件下单独保存。
[main raw](raw/lavik-maina6r-set-1m-k50000-f1024-20260930/), [PR raw](raw/lavik-worktrim8079-set-1m-k50000-f1024-20260930/).

#### 100 MiB

![Set 100 MiB、128 B：SISMEMBER 与 SADD/SREM QPS 随连接数变化](charts/set-104857600-128-ab.png)

**最新 main `a6e93d3d` 与 [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41` 实测。** 500 × 100 MiB key，128 B 元素，各 13 个测点、零错误，测量前后逐 key 校验。SADD + SREM 同连接数下为 main 的 **1.16–1.36 倍**。曲线使用无采样的八秒测点；单次差异不能视为稳定收益，perf 诊断在有采样的条件下单独保存。
[main raw](raw/lavik-maina6d-set-100m-k500-f128-20260930/), [PR raw](raw/lavik-worktrim8079-set-100m-k500-f128-20260930/).

数据仅用 RESTORE 预置，待事务清理完成后，main 与 PR 均重启恢复再测；不与批量 SADD/HSET 导入耗时混比。 [Seed provenance](raw/lavik-seedmaina6d-set-100m-k500-f128-20260930/).

![Set 100 MiB、1 KiB：SISMEMBER 与 SADD/SREM QPS 随连接数变化](charts/set-104857600-1024-ab.png)

**最新 main `a6e93d3d` 与 [PR #228](https://github.com/eloqdata/lavik/pull/228) `80792c41` 实测。** 500 × 100 MiB key，1024 B 元素，各 13 个测点、零错误，测量前后逐 key 校验。SADD + SREM 同连接数下为 main 的 **1.08–1.25 倍**。曲线使用无采样的八秒测点；单次差异不能视为稳定收益，perf 诊断在有采样的条件下单独保存。
[main raw](raw/lavik-maina6d-set-100m-k500-f1024-20260930/), [PR raw](raw/lavik-worktrim8079-set-100m-k500-f1024-20260930/).

数据仅用 RESTORE 预置，待事务清理完成后，main 与 PR 均重启恢复再测；不与批量 SADD/HSET 导入耗时混比。 [Seed provenance](raw/lavik-seedmaina6d-set-100m-k500-f1024-20260930/).

### SMEMBERS

#### 1 MiB

![Set 1 MiB、128 B：SMEMBERS QPS 随连接数变化](charts/set-1048576-128-ab-full.png)

**80 连接长测核对：** 每个版本连续三次 30 秒、不启用 perf，main 为 **1,966, 1,967, 1,945 QPS**，PR 为 **1,909, 1,922, 1,941 QPS**；均值比为 **0.982×**。两端使用同一份已恢复数据，50,000 个 key 测前测后基数完全一致，零错误。以上曲线仍使用原八秒测点；长测按版本先后执行，仅三次重复，不提供置信区间。 [Results](set-1048576-128-full-read-repeats.json), [main raw](raw/lavik-fullcheck-maina6d-set-1m-k50000-f128-20260930/), [PR raw](raw/lavik-fullcheck-worktrim8079-set-1m-k50000-f128-20260930/), [script](repeat_grouped_full_reads.py).


![Set 1 MiB、1 KiB：SMEMBERS QPS 随连接数变化](charts/set-1048576-1024-ab-full.png)

#### 100 MiB

![Set 100 MiB、128 B：SMEMBERS QPS 随连接数变化](charts/set-104857600-128-ab-full.png)

**16 连接持续负载未通过无错误检查。** 补测每版三次 30 秒时，main 第三次、PR 第二次均出现 `OOM grouped operation scratch admission`，进程随后正常退出。这些失败重复不纳入吞吐比较，八秒图不能证明该档持续运行稳定。准入按 worker 分配限额；100 MiB / 128 B 完整读取根据页字节、元素开销和多份临时空间保守预留约 1.2 GiB，集中在同一 worker 的请求可能超过约 8.4 GiB 的份额。main 失败后临时预留回到 0、RSS 约 7.3 GiB；这是本地预留拒绝，并非 OS OOM 或进程崩溃。该准入模型在 main 和 PR 中相同。 [main raw](raw/lavik-fullcheck-maina6d-set-100m-k500-f128-20260930/), [PR raw](raw/lavik-fullcheck-worktrim8079-set-100m-k500-f128-20260930/).


![Set 100 MiB、1 KiB：SMEMBERS QPS 随连接数变化](charts/set-104857600-1024-ab-full.png)

### 批量导入（SADD）

#### 1 MiB / 1024 B

![Set batched SADD import](charts/set-1048576-1024-k50000-fill.png)

历史导入测量：Lavik main `ebe28dd5`，不是本轮 `a6e93d3d` / PR #228 的复测。

四库统一用 SADD，每条 16 个元素、8 个连接、pipeline 64；main 灌入耗时 **517.9 秒**。持久化配置仍不同。

#### 1 MiB / 128 B

![Set batched SADD import](charts/set-1048576-128-k50000-fill.png)

历史导入测量：Lavik main `ebe28dd5`，不是本轮 `a6e93d3d` / PR #228 的复测。

四库统一用 SADD，每条 128 个元素、8 个连接、pipeline 64；main 灌入耗时 **1724.2 秒**。持久化配置仍不同。


100 MiB 的同命令 SADD 导入尚无本轮完整结果。
此前 Lavik RESTORE 与其他数据库 SADD 混用的对比图已撤下。

### RESTORE

main `a6e93d3d`，8 个并发 RESTORE 客户端，各导入 500 个 100 MiB key，逐 key 校验通过。以下是预置数据的独立计时，不含后续清理等待和恢复，不与其他数据库的批量 SADD/HSET 导入混比。

- 128 B: **291.1 秒**. [Raw](raw/lavik-seedmaina6d-set-100m-k500-f128-20260930/set-104857600-128.fill.json).
- 1024 B: **136.8 秒**. [Raw](raw/lavik-seedmaina6d-set-100m-k500-f1024-20260930/set-104857600-1024.fill.json).

## 工作负载

按位置读取和覆盖时，memtier 轮流访问每个 key 内均匀分布的八个位置。
原先的 64 KiB、1 MiB 条件使用 64 个 key；100 MiB 条件使用八个 key。
本轮 Hash/Set 使用 1 MiB/50,000 key、100 MiB/500 key。每个命令在当前条件的 key 中均匀随机选取一个。每个 field
value、member 或元素为 128 B 或 1 KiB。Stream 的字段名和各结构元数据
不计入逻辑 payload。测量前检查元素数量和抽样内容，写入后再次检查元素
数量。Set 的增删在随机命中相同 key 时可能产生空操作，因此该项目报告
两种命令合计的 QPS，而不是实际持久化修改的 QPS。

本轮八秒主测按 main、PR 顺序复用数据，每版依次执行完整读取、点查和写入。中间的写入会改变被访问字段的值和物理布局，因此不能把短测读 QPS 的差异全部归因于代码版本。额外的只读复测不穿插写入，在同一份固定数据上切换二进制。

## 测试配置

- 服务端 172.16.0.4，AMD EPYC 9V74 的 16 个 vCPU（0–15），100 Gb/s 网卡。
  Redis 8.8.0 与 Valkey 9.1.0 使用
  12 个 I/O 线程，关闭 RDB/AOF；Lavik 使用 12 个 worker、内核 TCP
  和六块专用 SPDK NVMe。三者的持久化配置不同。
- List 和 Sorted Set 的 100 MiB / 1 KiB 已更新为 main `a6e93d3d`；其余条件仍是早期 [PR #203](https://github.com/eloqdata/lavik/pull/203) 的
  `646a7b4e` 二进制；Hash/Set 与 Stream 的当前 main 版本在各自章节注明。
  不同版本的数据不组成一条 Lavik 曲线。
- Kvrocks 使用 16 个 worker，各大小档位使用相同缓存与压缩配置。List、Sorted Set 的 64 KiB 与
  1 MiB 于 2026-09-27 后补测；Hash/Set 使用本轮 key 数重新填充。
  保存的配置启用了 80 GiB RocksDB
  block cache 和 blob cache；它的热读 QPS 因而包含大容量内存缓存的收益，
  与 Lavik 的数据页读取路径不同。
- 批量导入由服务端本机的 Python 客户端发送；点查和写命令的 QPS 使用下面独立主机上的 memtier。新的导入对比共用预编码的元素字节，仍保持相同 RESP 命令、连接数和 pipeline。
- 客户端 172.16.0.5，AMD EPYC 9V45 的 16 个 vCPU，memtier_benchmark 2.5.1，
  pipeline 1、随机选 key，每个点测八秒。点查和写入用 16 个客户端线程、
  80/320/1280/2560/5120 个连接；64 KiB 和 1 MiB 完整读取用 16/80
  个连接，100 MiB 完整读取用 1/4/16 个连接，客户端线程数不超过连接数。
- 每种条件由访问不同 key 的并发 RESP 客户端重新填充；旧运行默认八个，
  新运行的并发数、每条预填充命令的目标字节数与 pipeline 保存在 provenance JSON 中。
  先读后写，写入过程使结构长度
  基本保持在初始水平；同一条件下不同连接数访问相同的 key。100 MiB 条件
  的每个预填充连接使用有界 pipeline，准确深度见各次 provenance。
- 这里的大小只计算 payload 字节，不等于 Redis 内存占用或 Lavik 磁盘用量。
  List、Sorted Set 和 Stream 的早期 64-key 图会显露单对象竞争；Hash/Set 使用本轮标注的 key 数。
- QPS 和延迟来自 memtier JSON；脚本拒绝连接错误、中断和服务端错误。

## List

这一章保留早期完整四产品对照：Lavik 使用 `646a7b4e` 版本，尚未在最新 main 上复测。图仅代表该版本，原始数据见 [results.csv](results.csv)。

### LINDEX / LSET

#### 64 KiB

![List 64 KiB、128 B：LINDEX / LSET QPS 随连接数变化](charts/list-65536-128.png)

![List 64 KiB、1 KiB：LINDEX / LSET QPS 随连接数变化](charts/list-65536-1024.png)

#### 1 MiB

![List 1 MiB、128 B：LINDEX / LSET QPS 随连接数变化](charts/list-1048576-128.png)

![List 1 MiB、1 KiB：LINDEX / LSET QPS 随连接数变化](charts/list-1048576-1024.png)

#### 100 MiB

![List 100 MiB、128 B：LINDEX / LSET QPS 随连接数变化](charts/list-104857600-128.png)

![List 100 MiB、1 KiB：LINDEX / LSET QPS 随连接数变化](charts/list-104857600-1024-ab.png)

**2026-09-30 最新 main `a6e93d3d` 复测。** 8 × 100 MiB key、1 KiB 元素，读写及全量读取共 13 个无采样测点；其他数据库保留同负载的原始结果，未重跑。 所有测点零错误，逐 key 校验通过。 [Raw data](raw/lavik-maina6-ordered-list-100m-k8-f1024-20260930/) · [Plot provenance](ordered-published.json).


### LRANGE 0 -1

#### 64 KiB

![List 64 KiB、128 B：LRANGE 0 -1 QPS 随连接数变化](charts/list-65536-128-full.png)

![List 64 KiB、1 KiB：LRANGE 0 -1 QPS 随连接数变化](charts/list-65536-1024-full.png)

#### 1 MiB

![List 1 MiB、128 B：LRANGE 0 -1 QPS 随连接数变化](charts/list-1048576-128-full.png)

![List 1 MiB、1 KiB：LRANGE 0 -1 QPS 随连接数变化](charts/list-1048576-1024-full.png)

#### 100 MiB

![List 100 MiB、128 B：LRANGE 0 -1 QPS 随连接数变化](charts/list-104857600-128-full.png)

![List 100 MiB、1 KiB：LRANGE 0 -1 QPS 随连接数变化](charts/list-104857600-1024-ab-full.png)

1 MiB/128 B 的 `LINDEX` 中，Lavik 峰值约 139k QPS；1 KiB 元素时约 677k。该差距与页内元素个数相关，但尚无足够剖析证据把它归因于单一操作。

## Sorted Set

这一章保留早期完整四产品对照：Lavik 使用 `646a7b4e` 版本，尚未在最新 main 上复测。图仅代表该版本，原始数据见 [results.csv](results.csv)。

### ZSCORE / ZINCRBY

#### 64 KiB

![Sorted Set 64 KiB、128 B：ZSCORE / ZINCRBY QPS 随连接数变化](charts/zset-65536-128.png)

![Sorted Set 64 KiB、1 KiB：ZSCORE / ZINCRBY QPS 随连接数变化](charts/zset-65536-1024.png)

#### 1 MiB

![Sorted Set 1 MiB、128 B：ZSCORE / ZINCRBY QPS 随连接数变化](charts/zset-1048576-128.png)

![Sorted Set 1 MiB、1 KiB：ZSCORE / ZINCRBY QPS 随连接数变化](charts/zset-1048576-1024.png)

#### 100 MiB

![Sorted Set 100 MiB、128 B：ZSCORE / ZINCRBY QPS 随连接数变化](charts/zset-104857600-128.png)

![Sorted Set 100 MiB、1 KiB：ZSCORE / ZINCRBY QPS 随连接数变化](charts/zset-104857600-1024-ab.png)

**2026-09-30 最新 main `a6e93d3d` 复测。** 8 × 100 MiB key、1 KiB 元素，读写及全量读取共 13 个无采样测点；其他数据库保留同负载的原始结果，未重跑。 所有测点零错误，逐 key 校验通过。 [Raw data](raw/lavik-maina6-ordered-zset-100m-k8-f1024-20260930/) · [Plot provenance](ordered-published.json).


### ZRANGE WITHSCORES

#### 64 KiB

![Sorted Set 64 KiB、128 B：ZRANGE WITHSCORES QPS 随连接数变化](charts/zset-65536-128-full.png)

![Sorted Set 64 KiB、1 KiB：ZRANGE WITHSCORES QPS 随连接数变化](charts/zset-65536-1024-full.png)

#### 1 MiB

![Sorted Set 1 MiB、128 B：ZRANGE WITHSCORES QPS 随连接数变化](charts/zset-1048576-128-full.png)

![Sorted Set 1 MiB、1 KiB：ZRANGE WITHSCORES QPS 随连接数变化](charts/zset-1048576-1024-full.png)

#### 100 MiB

![Sorted Set 100 MiB、128 B：ZRANGE WITHSCORES QPS 随连接数变化](charts/zset-104857600-128-full.png)

![Sorted Set 100 MiB、1 KiB：ZRANGE WITHSCORES QPS 随连接数变化](charts/zset-104857600-1024-ab-full.png)

## 测量边界

每点运行八秒、只测一次，QPS 没有重复测量置信区间。Redis/Valkey 关闭持久化，Kvrocks 关闭 WAL 并使用 80 GiB block cache，Lavik 向 SPDK 提交；写入曲线不可解释为同等持久性下的排名。100 MiB 的全量读取有些测点不足 100 次完成回复，小差异不宜过度解释。

[HGETALL 内存调查](diagnostics/hgetall-oom-20260929/README.md)和 [HSET 写入诊断](diagnostics/hset-20260929/README.md)保存了问题分析；Hash/Set 的旧版测点仍在 `raw/`，不作为当前 main 的曲线。

## Stream

Stream 的 100 MiB / 1 KiB 已更新为 main `a6e93d3d`；小档保留已合并优化后的 main `9acd7b6f` 实测。64 KiB 和 1 MiB 档使用 64 个热 key、128 B 或 1 KiB 元素；100 MiB 档使用八个 key、1 KiB 元素。横轴为连接数，纵轴为 QPS；每图只画一条 Lavik main 曲线。

点查和写入覆盖 80–5120 连接；小档完整读取覆盖 16/80 连接，100 MiB 档覆盖 1/4/16 连接。Redis 和 Valkey 关闭持久化，Kvrocks 关闭 WAL 且启用 80 GiB block cache，Lavik 提交到 SPDK；写入结果反映这些具体配置。

[小档测点及历史 100 MiB 测点](stream-latest.csv)、[当前 100 MiB 测点](stream-104857600-1024-current.csv)、[当前绘图来源](ordered-published.json)；Lavik [小档](raw/lavik-main9acd-stream-small-20260929/)与 [100 MiB 档](raw/lavik-main9acd-stream-100m-20260929/)的原始记录可复核各点。每点八秒、只测一次；旧优化阶段的结果保留在 `raw/`，不参与当前图表。

### 指定 ID `XRANGE`

#### 64 KiB

![64 KiB、128 B：指定 ID `XRANGE`，四款数据库 QPS 随连接数变化](charts/stream-65536-128-xrange-latest.png)

![64 KiB、1 KiB：指定 ID `XRANGE`，四款数据库 QPS 随连接数变化](charts/stream-65536-1024-xrange-latest.png)

#### 1 MiB

![1 MiB、128 B：指定 ID `XRANGE`，四款数据库 QPS 随连接数变化](charts/stream-1048576-128-xrange-latest.png)

![1 MiB、1 KiB：指定 ID `XRANGE`，四款数据库 QPS 随连接数变化](charts/stream-1048576-1024-xrange-latest.png)

#### 100 MiB

![100 MiB、1 KiB：指定 ID `XRANGE`，四款数据库 QPS 随连接数变化](charts/stream-104857600-1024-xrange-latest.png)

### `XADD MAXLEN`

#### 64 KiB

![64 KiB、128 B：`XADD MAXLEN`，四款数据库 QPS 随连接数变化](charts/stream-65536-128-xadd_maxlen-latest.png)

![64 KiB、1 KiB：`XADD MAXLEN`，四款数据库 QPS 随连接数变化](charts/stream-65536-1024-xadd_maxlen-latest.png)

#### 1 MiB

![1 MiB、128 B：`XADD MAXLEN`，四款数据库 QPS 随连接数变化](charts/stream-1048576-128-xadd_maxlen-latest.png)

![1 MiB、1 KiB：`XADD MAXLEN`，四款数据库 QPS 随连接数变化](charts/stream-1048576-1024-xadd_maxlen-latest.png)

#### 100 MiB

![100 MiB、1 KiB：`XADD MAXLEN`，四款数据库 QPS 随连接数变化](charts/stream-104857600-1024-xadd_maxlen-latest.png)

**2026-09-30 最新 main `a6e93d3d` 复测。** 8 × 100 MiB key、1 KiB 元素，读写及全量读取共 13 个无采样测点；其他数据库保留同负载的原始结果，未重跑。 所有测点零错误，逐 key 校验通过。 [Raw data](raw/lavik-maina6-ordered-stream-100m-k8-f1024-20260930/) · [Plot provenance](ordered-published.json).


### 全范围 `XRANGE - +`

#### 64 KiB

![64 KiB、128 B：全范围 `XRANGE - +`，四款数据库 QPS 随连接数变化](charts/stream-65536-128-xrange_full-latest.png)

![64 KiB、1 KiB：全范围 `XRANGE - +`，四款数据库 QPS 随连接数变化](charts/stream-65536-1024-xrange_full-latest.png)

#### 1 MiB

![1 MiB、128 B：全范围 `XRANGE - +`，四款数据库 QPS 随连接数变化](charts/stream-1048576-128-xrange_full-latest.png)

![1 MiB、1 KiB：全范围 `XRANGE - +`，四款数据库 QPS 随连接数变化](charts/stream-1048576-1024-xrange_full-latest.png)

#### 100 MiB

![100 MiB、1 KiB：全范围 `XRANGE - +`，四款数据库 QPS 随连接数变化](charts/stream-104857600-1024-xrange_full-latest.png)

## 复现

确保服务端和客户端没有其他压测，然后在本目录执行：

```bash
python3 run.py redis
python3 run.py valkey
python3 run.py redis --levels 16,80 --mode full
python3 run.py valkey --levels 16,80 --mode full
sudo python3 spdk_host.py prepare --discard-scratch
sudo python3 run.py lavik
sudo python3 run.py lavik --levels 16,80 --mode full
sudo python3 run.py lavik --tag backlog64 --types hash --sizes 1048576 \
  --fields 128 --levels 80,320,2560 --backlog-mb 64
sudo python3 spdk_host.py restore
sudo python3 kvrocks_host.py prepare --discard-scratch
python3 run.py kvrocks --sizes 65536,1048576 --fields 128,1024 --keys 64 \
  --mode both --levels 80,320,1280,2560,5120 --full-levels 16,80 \
  --seed-pipeline 64 --seconds 8 --continue-on-error
sudo python3 kvrocks_host.py restore
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python collect_plot.py
```

100 MiB 扩展按 Redis、Valkey、Lavik、Kvrocks 的顺序串行执行。Lavik 的 SPDK
和 Kvrocks 的 RAID0 分别丢弃六块临时盘上的旧数据；两个准备脚本都会先核对
序列号和 PCI 地址。

```bash
large=(--tag 100m --sizes 104857600 --fields 128,1024 --keys 8 \
  --mode both --levels 80,320,1280,2560,5120 --full-levels 1,4,16 \
  --seed-pipeline 64 --seconds 8)
python3 run.py redis "${large[@]}"
python3 run.py valkey "${large[@]}"
sudo python3 spdk_host.py prepare --discard-scratch
sudo python3 run.py lavik "${large[@]}" --continue-on-error
sudo python3 spdk_host.py restore
sudo python3 kvrocks_host.py prepare --discard-scratch
python3 run.py kvrocks "${large[@]}" --continue-on-error
sudo python3 kvrocks_host.py restore
.venv/bin/python collect_plot.py
```

SPDK 准备脚本在丢弃临时数据前，会核对六块专用控制器的序列号和 PCI
地址。不要对需要保留数据的设备执行准备命令。服务端命令、二进制哈希、
memtier 命令、填充耗时、校验结果与各次运行的 JSON 已提交到 `raw/`。
控制台输出留在本机，分支中的 JSON 已包含测量数据，因此没有提交重复日志。

上面的命令保留了早期 64/8-key 图的复现方式。本轮 Hash/Set 每次运行只填充
一种数据结构、大小和元素长度；`--tag` 依照原始目录命名。例如 1 MiB、
50,000 key、128 B Hash 的 Redis 运行：

```bash
python3 run_with_memory_guard.py --minimum-available-gib=20 -- \
  python3 run.py redis --tag=hash-1m-k50000-f128-20260929 \
  --types=hash --sizes=1048576 --fields=128 --keys=50000 \
  --levels=80,320,1280,2560,5120 --full-levels=16,80 \
  --seconds=8 --mode=both --seed-pipeline=64 --continue-on-error
```

100 MiB 档将 `--sizes` 改成 `104857600`、`--keys` 改成 `500`，
`--full-levels` 改成 `1,4,16`；依次运行 128 B、1 KiB 的 Hash 与 Set。
Valkey 使用同样参数。Kvrocks 在 `kvrocks_host.py prepare --discard-scratch` 后
运行，并在全部结束后调用 `restore`。Lavik 则在恢复 RAID0、调用
`spdk_host.py prepare --discard-scratch` 后，以 root 运行 `run.py lavik`，
加上 `--binary`、`--source-commit`，并在 tag 前加 `main<提交前八位>-`。
Lavik 大部分条件用 `--fill-workers=64 --seed-command-bytes=65536`
提高不同 key 的预填充并发并减少预填充命令数；第一组 Set 1 MiB/1 KiB
使用旧默认值八个，Set 1 MiB/128 B 仍使用 16 KiB 目标批次；后续每次实际值以原始
provenance 为准。
每次运行的 provenance JSON 保存了准确提交和二进制 SHA256。

2026-09-30 新增的 1 MiB main/PR 对比统一用批量 HSET/SADD 预填充：
`--fill-workers=8 --seed-pipeline=64 --seed-command-bytes=16384`，不传 `--seed-dump-path`。
128 B 元素每条命令 128 个，1 KiB 元素每条 16 个，与三库已有导入测点一致。
main 从空的基准盘灌入；PR 使用 `--reuse-seeded-data --seed-source-tag=<main-tag>`
恢复同一批 key，前后都逐 key 校验数量。批量导入图只比较同命令、同批大小的结果。
下面的 RDB 步骤仅用于独立的 RESTORE 测量和先前的 100 MiB 压测预填充。

100 MiB/128 B 的 Lavik 预填充使用 [RDB 种子生成器](make_rdb_seed_dump.py)
创建单个 819,200 元素的 Hash 或 Set，再用 `RESTORE` 写入 500 个不同 key。
生成器核对 Redis 原始校验和，并为 Lavik 的 RDB v11 读取器重新计算校验和；
运行记录保存种子 SHA256。生成 Set 种子的命令为：

```bash
python3 make_rdb_seed_dump.py set 104857600 128 /tmp/lavik-set-100m-f128-generated.dump \
  --redis-binary=/mnt/dev/peer-bench/redis/v8.8.0/src/src/redis-server
```

相应的 Lavik 运行在上述公共参数之外使用
`--fill-workers=8 --seed-dump-path=/tmp/lavik-set-100m-f128-generated.dump`；
Hash 将 `set` 改成 `hash` 并使用单独生成的文件。正式测点在全部 key 的数量和样本内容校验、
以及 TxCleaner 积压稳定后才开始。

重绘单一条件图：

```bash
.venv/bin/python plot_set_hash_high_keys.py set 1048576 128 \
  --main-tag pr222faef28d9-set-1m-k50000-f128-leaf-c64-20260930 \
  --main-commit faef28d9411fa32ae5f3a39915a6ca2c2b01f191 \
  --main-sha256 b0c664967357b9c648f066b11ff33febb10540bf941c36b6ac0973690d212b8c
```
