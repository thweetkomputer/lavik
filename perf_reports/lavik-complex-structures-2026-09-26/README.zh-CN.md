# 复杂数据结构性能：Redis、Valkey、Lavik 与 Kvrocks

[English](README.md)

本报告在同一台服务端和一台独立的 memtier 客户端上比较五类
Redis 兼容数据结构。每张图固定数据结构、每个 key 的逻辑数据量和
每个元素的字节数。横轴为连接数，纵轴为每秒完成的命令数。

## 2026-09-30 main 更新

[PR #222](https://github.com/eloqdata/lavik/pull/222) 已合并；当前 main 为 `a6e93d3d`。Hash/Set 图已删除旧 main 与已合并 PR 的重复曲线，保留 Redis、Valkey、Kvrocks 和一条 Lavik 曲线。

1 MiB/key × 50,000 key 暂沿用合并实现的 `faef28d9` 实测数据（四组各 12 点，零错误），图例归为 main；**这不是 `a6e93d3d` 的新运行**。新 main 复测完成后逐图替换。100 MiB/key × 500 key 暂保留最新历史测量，并明确标为历史结果，不冒充最新 main。精确版本与二进制摘要见 [绘图来源](published-main.json)。Stream、List、Sorted Set 的结果和图继续保留。

接下来先对最新 main 的 Set/Hash 写入进行 perf 采样，检查分配、拷贝和重复工作，再考虑算法调整；新优化有实测后再增加未合并 PR 曲线。

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

## Hash

下列点查/写入图每张包含两个命令；1 MiB 和 100 MiB 档分别使用 50,000 和 500 个 key。

### HGET / HSET

#### 1 MiB

![Hash 1 MiB、128 B：HGET 与 HSET QPS 随连接数变化](charts/hash-1048576-128-ab.png)

已合并实现的实测结果：`faef28d9`，50,000 key，128 B 元素。[原始数据](raw/lavik-pr222faef28d9-hash-1m-k50000-f128-leaf-c64-20260930/)。

![Hash 1 MiB、1 KiB：HGET 与 HSET QPS 随连接数变化](charts/hash-1048576-1024-ab.png)

已合并实现的实测结果：`faef28d9`，50,000 key，1024 B 元素。[原始数据](raw/lavik-pr222faef28d9-hash-1m-k50000-f1024-leaf-c64-20260930/)。

#### 100 MiB

![Hash 100 MiB、128 B：HGET 与 HSET QPS 随连接数变化](charts/hash-104857600-128-ab.png)

历史测量，等待最新 main 复测：`817473b7`，500 key，128 B 元素。[原始数据](raw/lavik-pr222817-hash-100m-k500-f128-20260930/)。

![Hash 100 MiB、1 KiB：HGET 与 HSET QPS 随连接数变化](charts/hash-104857600-1024-ab.png)

历史测量，等待最新 main 复测：`d1ce200e`，500 key，1024 B 元素。[原始数据](raw/lavik-maind1ce200e-hash-100m-k500-f1024-20260929/)。

### HGETALL

#### 1 MiB

![Hash 1 MiB、128 B：HGETALL QPS 随连接数变化](charts/hash-1048576-128-ab-full.png)

![Hash 1 MiB、1 KiB：HGETALL QPS 随连接数变化](charts/hash-1048576-1024-ab-full.png)

#### 100 MiB

![Hash 100 MiB、128 B：HGETALL QPS 随连接数变化](charts/hash-104857600-128-ab-full.png)

![Hash 100 MiB、1 KiB：HGETALL QPS 随连接数变化](charts/hash-104857600-1024-ab-full.png)

### 批量导入（HSET）

#### 1 MiB / 1024 B

![Hash batched HSET import](charts/hash-1048576-1024-k50000-fill.png)

四库统一用 HSET，每条 16 个元素、8 个连接、pipeline 64；main 灌入耗时 **500.3 秒**。持久化配置仍不同。

#### 1 MiB / 128 B

![Hash batched HSET import](charts/hash-1048576-128-k50000-fill.png)

四库统一用 HSET，每条 128 个元素、8 个连接、pipeline 64；main 灌入耗时 **1306.3 秒**。持久化配置仍不同。

### RESTORE

#### 100 MiB

本轮没有重新计时 Hash RESTORE；批量 HSET 的导入结果见上一节，二者分开记录。

## Set

下列点查/写入图每张包含两个命令；1 MiB 和 100 MiB 档分别使用 50,000 和 500 个 key。

### SISMEMBER / SADD/SREM

#### 1 MiB

![Set 1 MiB、128 B：SISMEMBER 与 SADD/SREM QPS 随连接数变化](charts/set-1048576-128-ab.png)

已合并实现的实测结果：`faef28d9`，50,000 key，128 B 元素。[原始数据](raw/lavik-pr222faef28d9-set-1m-k50000-f128-leaf-c64-20260930/)。

![Set 1 MiB、1 KiB：SISMEMBER 与 SADD/SREM QPS 随连接数变化](charts/set-1048576-1024-ab.png)

已合并实现的实测结果：`faef28d9`，50,000 key，1024 B 元素。[原始数据](raw/lavik-pr222faef28d9-set-1m-k50000-f1024-leaf-c64-20260930/)。

#### 100 MiB

![Set 100 MiB、128 B：SISMEMBER 与 SADD/SREM QPS 随连接数变化](charts/set-104857600-128-ab.png)

历史测量，等待最新 main 复测：`817473b7`，500 key，128 B 元素。[原始数据](raw/lavik-pr222817-set-100m-k500-f128-20260930/)。

![Set 100 MiB、1 KiB：SISMEMBER 与 SADD/SREM QPS 随连接数变化](charts/set-104857600-1024-ab.png)

历史测量，等待最新 main 复测：`d1ce200e`，500 key，1024 B 元素。[原始数据](raw/lavik-maind1ce200e-set-100m-k500-f1024-20260929/)。

### SMEMBERS

#### 1 MiB

![Set 1 MiB、128 B：SMEMBERS QPS 随连接数变化](charts/set-1048576-128-ab-full.png)

![Set 1 MiB、1 KiB：SMEMBERS QPS 随连接数变化](charts/set-1048576-1024-ab-full.png)

#### 100 MiB

![Set 100 MiB、128 B：SMEMBERS QPS 随连接数变化](charts/set-104857600-128-ab-full.png)

![Set 100 MiB、1 KiB：SMEMBERS QPS 随连接数变化](charts/set-104857600-1024-ab-full.png)

### 批量导入（SADD）

#### 1 MiB / 1024 B

![Set batched SADD import](charts/set-1048576-1024-k50000-fill.png)

四库统一用 SADD，每条 16 个元素、8 个连接、pipeline 64；main 灌入耗时 **517.9 秒**。持久化配置仍不同。

#### 1 MiB / 128 B

![Set batched SADD import](charts/set-1048576-128-k50000-fill.png)

四库统一用 SADD，每条 128 个元素、8 个连接、pipeline 64；main 灌入耗时 **1724.2 秒**。持久化配置仍不同。

另测 Lavik main `31a1e130` 与 已合并实现 `faef28d9`：64 连接、每条 1,024 个成员、pipeline 8，使用相同客户端重新灌入 50,000 个 1 MiB key，耗时分别为 **352.3 秒**和 **166.7 秒**，PR 吞吐为 main 的 **2.11 倍**；均逐 key 校验通过。这是另一组导入参数，不与上图的旧参数结果横向比较。 [main raw](raw/lavik-main31-set-1m-k50000-f128-b128k-c64-p8-encoded-20260930/), [PR raw](raw/lavik-pr222faef28d9-set-1m-k50000-f128-b128k-c64-p8-encoded-20260930/).

100 MiB 的同命令 SADD 导入尚无本轮完整结果。
此前 Lavik RESTORE 与其他数据库 SADD 混用的对比图已撤下。

### RESTORE

main `ebe28dd5` 用八个并发 RESTORE 客户端导入 500 个 100 MiB key，耗时 **544.4 秒**。
这个独立结果不与 SADD 导入耗时混画。[原始记录](raw/lavik-mainebe-set-100m-k500-f128-20260930/set-104857600-128.fill.json)。

## 工作负载

按位置读取和覆盖时，memtier 轮流访问每个 key 内均匀分布的八个位置。
原先的 64 KiB、1 MiB 条件使用 64 个 key；100 MiB 条件使用八个 key。
本轮 Hash/Set 使用 1 MiB/50,000 key、100 MiB/500 key。每个命令在当前条件的 key 中均匀随机选取一个。每个 field
value、member 或元素为 128 B 或 1 KiB。Stream 的字段名和各结构元数据
不计入逻辑 payload。测量前检查元素数量和抽样内容，写入后再次检查元素
数量。Set 的增删在随机命中相同 key 时可能产生空操作，因此该项目报告
两种命令合计的 QPS，而不是实际持久化修改的 QPS。

## 测试配置

- 服务端 172.16.0.4，AMD EPYC 9V74 的 16 个 vCPU（0–15），100 Gb/s 网卡。
  Redis 8.8.0 与 Valkey 9.1.0 使用
  12 个 I/O 线程，关闭 RDB/AOF；Lavik 使用 12 个 worker、内核 TCP
  和六块专用 SPDK NVMe。三者的持久化配置不同。
- List 和 Sorted Set 章节的 Lavik 是早期 [PR #203](https://github.com/eloqdata/lavik/pull/203) 的
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

![List 100 MiB、1 KiB：LINDEX / LSET QPS 随连接数变化](charts/list-104857600-1024.png)

### LRANGE 0 -1

#### 64 KiB

![List 64 KiB、128 B：LRANGE 0 -1 QPS 随连接数变化](charts/list-65536-128-full.png)

![List 64 KiB、1 KiB：LRANGE 0 -1 QPS 随连接数变化](charts/list-65536-1024-full.png)

#### 1 MiB

![List 1 MiB、128 B：LRANGE 0 -1 QPS 随连接数变化](charts/list-1048576-128-full.png)

![List 1 MiB、1 KiB：LRANGE 0 -1 QPS 随连接数变化](charts/list-1048576-1024-full.png)

#### 100 MiB

![List 100 MiB、128 B：LRANGE 0 -1 QPS 随连接数变化](charts/list-104857600-128-full.png)

![List 100 MiB、1 KiB：LRANGE 0 -1 QPS 随连接数变化](charts/list-104857600-1024-full.png)

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

![Sorted Set 100 MiB、1 KiB：ZSCORE / ZINCRBY QPS 随连接数变化](charts/zset-104857600-1024.png)

### ZRANGE WITHSCORES

#### 64 KiB

![Sorted Set 64 KiB、128 B：ZRANGE WITHSCORES QPS 随连接数变化](charts/zset-65536-128-full.png)

![Sorted Set 64 KiB、1 KiB：ZRANGE WITHSCORES QPS 随连接数变化](charts/zset-65536-1024-full.png)

#### 1 MiB

![Sorted Set 1 MiB、128 B：ZRANGE WITHSCORES QPS 随连接数变化](charts/zset-1048576-128-full.png)

![Sorted Set 1 MiB、1 KiB：ZRANGE WITHSCORES QPS 随连接数变化](charts/zset-1048576-1024-full.png)

#### 100 MiB

![Sorted Set 100 MiB、128 B：ZRANGE WITHSCORES QPS 随连接数变化](charts/zset-104857600-128-full.png)

![Sorted Set 100 MiB、1 KiB：ZRANGE WITHSCORES QPS 随连接数变化](charts/zset-104857600-1024-full.png)

## 测量边界

每点运行八秒、只测一次，QPS 没有重复测量置信区间。Redis/Valkey 关闭持久化，Kvrocks 关闭 WAL 并使用 80 GiB block cache，Lavik 向 SPDK 提交；写入曲线不可解释为同等持久性下的排名。100 MiB 的全量读取有些测点不足 100 次完成回复，小差异不宜过度解释。

[HGETALL 内存调查](diagnostics/hgetall-oom-20260929/README.md)和 [HSET 写入诊断](diagnostics/hset-20260929/README.md)保存了问题分析；Hash/Set 的旧版测点仍在 `raw/`，不作为当前 main 的曲线。

## Stream

Lavik 使用已合并 Stream 优化的最新 main `9acd7b6f`。64 KiB 和 1 MiB 档使用 64 个热 key、128 B 或 1 KiB 元素；100 MiB 档使用八个 key、1 KiB 元素。横轴为连接数，纵轴为 QPS；每图只画一条 Lavik main 曲线。

点查和写入覆盖 80–5120 连接；小档完整读取覆盖 16/80 连接，100 MiB 档覆盖 1/4/16 连接。Redis 和 Valkey 关闭持久化，Kvrocks 关闭 WAL 且启用 80 GiB block cache，Lavik 提交到 SPDK；写入结果反映这些具体配置。

[完整测点](stream-latest.csv)、[绘图脚本](plot_stream_latest.py)、Lavik [小档](raw/lavik-main9acd-stream-small-20260929/)与 [100 MiB 档](raw/lavik-main9acd-stream-100m-20260929/)的原始记录可复核各点。每点八秒、只测一次；旧优化阶段的结果保留在 `raw/`，不参与当前图表。

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
