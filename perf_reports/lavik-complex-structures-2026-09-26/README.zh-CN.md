# 复杂数据结构性能：Redis、Valkey、Lavik 与 Kvrocks

[English](README.md)

本报告在同一台服务端和一台独立的 memtier 客户端上比较五类
Redis 兼容数据结构。每张图固定数据结构、每个 key 的逻辑数据量和
每个元素的字节数。横轴为连接数，纵轴为每秒完成的命令数。

## 2026-09-29 分组 Hash 与 Set 复测

Lavik 只展示已合并 [PR #212](https://github.com/eloqdata/lavik/pull/212)
后的 `main` 实测。当前 1 MiB 档使用提交 `bde3120e`，SPDK
RelWithDebInfo 二进制 SHA256 为
`1acecaa40948d473caedce591d1a775d3d910b260a50b38a68f25bf946a4546e`。
10 MiB 和 100 MiB 档已测完三个对照数据库；Set 的 10 MiB 档已补测
`9acd7b6f` main，Hash 的大 key 与 Set 的 100 MiB 仍待补测。早期 main 和 PR #212
的原始运行记录仍保留在 `raw/`，但不再当作当前 main 的数据展示。

1 MiB 和 10 MiB 使用 64 个 key；100 MiB 使用八个 key。每个元素为
128 B 或 1 KiB。点命令测 80/320/1280/2560/5120 连接，完整读取
测 1 MiB 的 16/80、10 MiB 的 4/16、100 MiB 的 1/4/16 连接；
每点八秒。Redis、Valkey 不持久化，Kvrocks 使用无压缩 RAID0、关闭 WAL、
启用 80 GiB block cache 和 blob cache；Lavik 在六块 NVMe 上用 SPDK
提交。这些配置影响绝对写入 QPS。

目前 1 MiB/64-key 的 HGET、SISMEMBER 和 10 MiB/64-key 的
SISMEMBER 已采用合并后 main。没有给 Lavik 增加数据页缓存。

1 MiB/64-key 的 HSET 和 SADD/SREM 在合并后 main 中分别约为
9.4–9.6k 与 18.8–20.1k QPS；SADD/SREM 混合结果含空操作。
更多热 key 的同条件对照见下节。

### 256 个热 key 的写入复测

针对热 key 偏少的问题，四款产品统一填充 256 个 1 MiB key，元素分别为
128 B 和 1 KiB；命令、八秒测量、连接数和持久化配置与上面的 64-key 档相同。
这里的 Lavik 只画最新 main (`9acd7b6f`)，没有重复画早期 PR。
256 key 相比 64 key，把 128 B HSET 的 320 连接吞吐从约 9.4k 提到
19.2k QPS，Set 的 SADD/SREM 从 18.8k 提到 36.1k；仍远低于 Kvrocks。
80 连接时 Lavik 的 HSET 达 29.7k，而 320 连接回落至 19.2k，说明仅增加
连接不能消除写入等待。图的纵轴使用对数刻度，保留了 Lavik 与三个对照库的
数量级差距。

[完整测点 CSV](write-256.csv)、[绘图脚本](plot_write_256.py)及
[Redis](raw/redis-1m-k256-write-20260929/)、
[Valkey](raw/valkey-1m-k256-write-20260929/)、
[Kvrocks](raw/kvrocks-1m-k256-write-20260929/)、
[Lavik](raw/lavik-main9acd-1m-k256-20260929/)的运行记录可复核所有点。

合并前的写入诊断与 HGETALL 内存调查保留在 [HSET 诊断](diagnostics/hset-20260929/README.md)和 [HGETALL 内存调查](diagnostics/hgetall-oom-20260929/README.md)，不作为当前 main 的实测值。每点仅测一次，没有置信区间；可用 [当前数据 CSV](set-hash-ab.csv)、[原始运行记录](raw/)和 [绘图脚本](plot_set_hash_ab.py)复核。

## Hash

下列点查/写入图每张包含两个命令；1 MiB 的 Lavik 为合并后 main，10 MiB 和 100 MiB 仍待同条件补测。

### HGET / HSET

#### 1 MiB

![Hash 1 MiB、128 B：HGET 与 HSET QPS 随连接数变化](charts/hash-1048576-128-ab.png)

![Hash 1 MiB、1 KiB：HGET 与 HSET QPS 随连接数变化](charts/hash-1048576-1024-ab.png)

#### 10 MiB

![Hash 10 MiB、128 B：HGET 与 HSET QPS 随连接数变化](charts/hash-10485760-128-ab.png)

![Hash 10 MiB、1 KiB：HGET 与 HSET QPS 随连接数变化](charts/hash-10485760-1024-ab.png)

#### 100 MiB

![Hash 100 MiB、128 B：HGET 与 HSET QPS 随连接数变化](charts/hash-104857600-128-ab.png)

![Hash 100 MiB、1 KiB：HGET 与 HSET QPS 随连接数变化](charts/hash-104857600-1024-ab.png)

### HSET / 256 个热 key

每 key 1 MiB，128 B 和 1 KiB 元素；Lavik 是最新 main `9acd7b6f`。

![Hash HSET，256 key，四款数据库](charts/hash-hset-1048576-k256.png)

### HGETALL

#### 1 MiB

![Hash 1 MiB、128 B：HGETALL QPS 随连接数变化](charts/hash-1048576-128-ab-full.png)

![Hash 1 MiB、1 KiB：HGETALL QPS 随连接数变化](charts/hash-1048576-1024-ab-full.png)

#### 10 MiB

![Hash 10 MiB、128 B：HGETALL QPS 随连接数变化](charts/hash-10485760-128-ab-full.png)

![Hash 10 MiB、1 KiB：HGETALL QPS 随连接数变化](charts/hash-10485760-1024-ab-full.png)

#### 100 MiB

![Hash 100 MiB、128 B：HGETALL QPS 随连接数变化](charts/hash-104857600-128-ab-full.png)

![Hash 100 MiB、1 KiB：HGETALL QPS 随连接数变化](charts/hash-104857600-1024-ab-full.png)

## Set

下列点查/写入图每张包含两个命令；1 MiB 和 10 MiB 的 Lavik 为合并后 main，100 MiB 仍待同条件补测。

### SISMEMBER / SADD/SREM

#### 1 MiB

![Set 1 MiB、128 B：SISMEMBER 与 SADD/SREM QPS 随连接数变化](charts/set-1048576-128-ab.png)

![Set 1 MiB、1 KiB：SISMEMBER 与 SADD/SREM QPS 随连接数变化](charts/set-1048576-1024-ab.png)

#### 10 MiB

![Set 10 MiB、128 B：SISMEMBER 与 SADD/SREM QPS 随连接数变化](charts/set-10485760-128-ab.png)

![Set 10 MiB、1 KiB：SISMEMBER 与 SADD/SREM QPS 随连接数变化](charts/set-10485760-1024-ab.png)

#### 100 MiB

![Set 100 MiB、128 B：SISMEMBER 与 SADD/SREM QPS 随连接数变化](charts/set-104857600-128-ab.png)

![Set 100 MiB、1 KiB：SISMEMBER 与 SADD/SREM QPS 随连接数变化](charts/set-104857600-1024-ab.png)

### SADD/SREM / 256 个热 key

每 key 1 MiB，128 B 和 1 KiB 元素；Lavik 是最新 main `9acd7b6f`。

![Set SADD/SREM，256 key，四款数据库](charts/set-sadd_srem-1048576-k256.png)

### SMEMBERS

#### 1 MiB

![Set 1 MiB、128 B：SMEMBERS QPS 随连接数变化](charts/set-1048576-128-ab-full.png)

![Set 1 MiB、1 KiB：SMEMBERS QPS 随连接数变化](charts/set-1048576-1024-ab-full.png)

#### 10 MiB

![Set 10 MiB、128 B：SMEMBERS QPS 随连接数变化](charts/set-10485760-128-ab-full.png)

![Set 10 MiB、1 KiB：SMEMBERS QPS 随连接数变化](charts/set-10485760-1024-ab-full.png)

#### 100 MiB

![Set 100 MiB、128 B：SMEMBERS QPS 随连接数变化](charts/set-104857600-128-ab-full.png)

![Set 100 MiB、1 KiB：SMEMBERS QPS 随连接数变化](charts/set-104857600-1024-ab-full.png)

## 工作负载

按位置读取和覆盖时，memtier 轮流访问每个 key 内均匀分布的八个位置。
原先的 64 KiB、1 MiB 及新增的 10 MiB 条件使用 64 个 key；100 MiB 条件
使用八个 key。每个命令在当前条件的 key 中均匀随机选取一个。每个 field
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
- Kvrocks 在三个大小档位使用相同配置。64 KiB 与 1 MiB 于 2026-09-27
  后补测，工作负载参数与原始档位一致。保存的配置启用了 80 GiB RocksDB
  block cache 和 blob cache；它的热读 QPS 因而包含大容量内存缓存的收益，
  与 Lavik 的数据页读取路径不同。
- 客户端 172.16.0.5，AMD EPYC 9V45 的 16 个 vCPU，memtier_benchmark 2.5.1，
  pipeline 1、随机选 key，每个点测八秒。点查和写入用 16 个客户端线程、
  80/320/1280/2560/5120 个连接；64 KiB 和 1 MiB 完整读取用 16/80
  个连接，100 MiB 完整读取用 1/4/16 个连接，客户端线程数不超过连接数。
- 每种条件由八个并发 RESP 客户端重新填充。先读后写，写入过程使结构长度
  基本保持在初始水平；同一条件下不同连接数访问相同的 key。100 MiB 条件
  的每个预填充连接按 64 条命令做有界 pipeline。
- 这里的大小只计算 payload 字节，不等于 Redis 内存占用或 Lavik 磁盘用量。
  64 个热 key 会显露单对象竞争，不代表海量 key 的负载。
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

复现 9 月 29 日补测时，分别构建本报告开头列出的两版 Lavik，用各自二进制
执行 `run.py lavik`，共同参数为 `--types hash,set --fields 128,1024`、
`--mode both --levels 80,320,1280,2560,5120 --seconds 8`。1 MiB 使用
`--sizes 1048576 --keys 64 --full-levels 16,80`；100 MiB 使用
`--sizes 104857600 --keys 8`、`--seed-pipeline 64 --full-levels 1,4,16`
和 `--continue-on-error`。四个 tag 分别为 `main-20260929`、`opt-20260929`
及各自的 `-100m` 版本。用 `--source-commit` 指定准确源码提交；原始运行目录
中的 provenance JSON 同时记录源码提交和二进制 SHA256。恢复 SPDK 驱动后，
运行 `.venv/bin/python plot_set_hash_ab.py` 重绘新图和 CSV。
