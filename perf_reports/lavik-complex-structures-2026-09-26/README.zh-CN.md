# 复杂数据结构性能：Redis、Valkey 与 Lavik

[English](README.md)

本报告在同一台服务端和一台独立的 memtier 客户端上比较五类
Redis 兼容数据结构。每张图固定数据结构、每个 key 的逻辑数据量和
每个元素的字节数。横轴为连接数，纵轴为每秒完成的命令数。

## 工作负载

| 数据结构 | 点查 | 写入 | 完整读取 | 写入行为 |
|---|---|---|---|---|
| Hash | HGET | HSET | HGETALL | 覆盖已有 field 的 value |
| Set | SISMEMBER | SADD + SREM | SMEMBERS | 对同一个 member 等比例交替增删 |
| List | LINDEX | LSET | LRANGE 0 -1 | 覆盖已有元素 |
| Sorted Set | ZSCORE | ZINCRBY | ZRANGE WITHSCORES | 增加已有 member 的 score |
| Stream | 指定 ID 的 XRANGE | XADD MAXLEN ~ N | XRANGE - + | 追加并近似裁剪到预填充长度 |

按位置读取和覆盖时，memtier 轮流访问每个 key 内均匀分布的八个位置。
每个命令从 64 个 key 中均匀随机选取一个。每种条件均从 64 个 key
开始；每个 key 的逻辑 payload 为 64 KiB 或 1 MiB，每个 field
value、member 或元素为 128 B 或 1 KiB。Stream 的字段名和各结构元数据
不计入逻辑 payload。测量前检查元素数量和抽样内容，写入后再次检查元素
数量。Set 的增删在随机命中相同 key 时可能产生空操作，因此该项目报告
两种命令合计的 QPS，而不是实际持久化修改的 QPS。

## 测试配置

- 服务端 172.16.0.4，AMD EPYC 9V74 的 16 个 vCPU（0–15），100 Gb/s 网卡。
  Redis 8.8.0 与 Valkey 9.1.0 使用
  12 个 I/O 线程，关闭 RDB/AOF；Lavik 使用 12 个 worker、内核 TCP
  和六块专用 SPDK NVMe。三者的持久化配置不同。
- Lavik 二进制来自 [PR #203](https://github.com/eloqdata/lavik/pull/203) 的
  `646a7b4e` 提交，SHA256 为
  `d98624e48eeac1aa942435f53e3c0f56882022f1f2184ae0bc415dfe5e31870a`；
  测试开始时上游 `main` 为 `9e31d073`。
- 客户端 172.16.0.5，AMD EPYC 9V45 的 16 个 vCPU，memtier_benchmark 2.5.1，
  16 个客户端线程、
  pipeline 1、随机选 key；点查和写入用 80/320/1280/2560/5120 个连接，
  完整读取用 16/80 个连接，每个点测八秒。
- 每种条件由八个并发 RESP 客户端重新填充。先读后写，写入过程使结构长度
  基本保持在初始水平；不同连接数都访问相同的 64 个 key。
- 这里的大小只计算 payload 字节，不等于 Redis 内存占用或 Lavik 磁盘用量。
  64 个热 key 会显露单对象竞争，不代表海量 key 的负载。
- QPS 和延迟来自 memtier JSON；脚本拒绝连接错误、中断和服务端错误。

## 结果

计划中的 720 个组合均已完成。原始依据包括
[results.csv](results.csv)、[raw/](raw/) 下的每次运行 JSON 与命令记录，
以及绘图脚本 [collect_plot.py](collect_plot.py)。每个点只测一次、时长八秒；
下列 QPS 没有重复测量的置信区间。

对 1 MiB 对象，Lavik 的单元素读取通常在 320 个连接以内达到峰值，
Redis 则经常继续升至 1280–2560 个连接。128 B 元素时，Lavik 的
HGET、SISMEMBER、LINDEX、ZSCORE 和单条 XRANGE 峰值分别约为
50.2 万、40.8 万、13.9 万、37.8 万和 4.4 万 QPS；List 与 Stream
差距最大。5120 个连接显著增加排队延迟：以 1 MiB/128 B HGET 为例，
Lavik 从 320 连接时的 50.2 万 QPS、p99 1.9 ms，降为 5120 连接时的
31.6 万 QPS、p99 127 ms。Redis 的 Hash/Set/Sorted Set 峰值点已占用
客户端 16 个 CPU 核中的约 15 个，高连接数曲线也受客户端容量影响。

完整读取表现不同。80 连接、1 MiB/128 B 下，Lavik 的 HGETALL
（1524 QPS）、SMEMBERS（1544）及含 score 的 ZRANGE（1488）达到或
超过 Redis；LRANGE（949）与全范围 XRANGE（251）则更慢。
元素为 1 KiB 时，Lavik 和 Redis 的若干 1 MiB 完整读取达到约
2.8 GiB/s 客户端接收速率，接近本环境观察到的回复带宽平台。
较小元素会产生更多回复条目：1 MiB Stream 在 128 B 时有 8192 条消息，
在 1 KiB 时有 1024 条；Lavik 全范围 XRANGE 因而从 251 升至
1526 QPS。

写入必须结合持久化配置理解：Redis 与 Valkey 关闭 RDB/AOF，
Lavik 则提交到 SPDK。Lavik 的 HSET、LSET、ZINCRBY 和限长 XADD
在 80 连接下多数为 5000–7000 QPS。继续增加连接数对 QPS 帮助很小，
却把 p99 推到秒级。Set 的 SADD/SREM 行表示命令吞吐，其中可能有空操作。

### 单元素读取峰值 QPS（括号内为连接数）

| 数据结构 | 元素大小 | 命令 | Redis | Valkey | Lavik |
|---|---:|---|---:|---:|---:|
| Hash | 128 B | HGET | 1,001,626（2560） | 837,629（2560） | 502,460（320） |
| Hash | 1 KiB | HGET | 968,662（2560） | 931,407（2560） | 645,839（320） |
| Set | 128 B | SISMEMBER | 1,038,463（2560） | 908,383（1280） | 408,024（320） |
| Set | 1 KiB | SISMEMBER | 815,565（1280） | 837,087（2560） | 501,939（320） |
| List | 128 B | LINDEX | 753,041（2560） | 682,135（320） | 138,566（80） |
| List | 1 KiB | LINDEX | 795,571（1280） | 669,135（1280） | 677,413（320） |
| Sorted Set | 128 B | ZSCORE | 989,218（2560） | 857,403（2560） | 378,358（320） |
| Sorted Set | 1 KiB | ZSCORE | 800,531（1280） | 824,607（1280） | 453,124（320） |
| Stream | 128 B | XRANGE | 336,558（2560） | 403,711（320） | 43,545（320） |
| Stream | 1 KiB | XRANGE | 349,674（1280） | 436,291（320） | 58,595（320） |

### 80 连接时的写入命令 QPS

| 数据结构 | 元素大小 | 命令 | Redis | Valkey | Lavik |
|---|---:|---|---:|---:|---:|
| Hash | 128 B | HSET | 445,582 | 541,152 | 6,471 |
| Hash | 1 KiB | HSET | 438,749 | 532,240 | 6,436 |
| Set | 128 B | SADD + SREM | 449,673 | 560,382 | 13,287 |
| Set | 1 KiB | SADD + SREM | 436,456 | 537,995 | 13,137 |
| List | 128 B | LSET | 426,554 | 483,039 | 6,319 |
| List | 1 KiB | LSET | 430,357 | 466,391 | 6,575 |
| Sorted Set | 128 B | ZINCRBY | 402,062 | 531,647 | 6,102 |
| Sorted Set | 1 KiB | ZINCRBY | 407,553 | 490,732 | 6,445 |
| Stream | 128 B | XADD MAXLEN | 358,357 | 464,902 | 4,715 |
| Stream | 1 KiB | XADD MAXLEN | 323,761 | 393,696 | 5,576 |

### 80 连接时的完整读取 QPS

| 数据结构 | 元素大小 | 命令 | Redis | Valkey | Lavik |
|---|---:|---|---:|---:|---:|
| Hash | 128 B | HGETALL | 1,137 | 295 | 1,524 |
| Hash | 1 KiB | HGETALL | 2,771 | 1,235 | 2,807 |
| Set | 128 B | SMEMBERS | 999 | 464 | 1,544 |
| Set | 1 KiB | SMEMBERS | 2,847 | 1,252 | 2,846 |
| List | 128 B | LRANGE | 2,322 | 938 | 949 |
| List | 1 KiB | LRANGE | 2,849 | 1,073 | 1,380 |
| Sorted Set | 128 B | ZRANGE | 1,441 | 537 | 1,488 |
| Sorted Set | 1 KiB | ZRANGE | 2,823 | 1,035 | 2,824 |
| Stream | 128 B | XRANGE - + | 424 | 327 | 251 |
| Stream | 1 KiB | XRANGE - + | 1,346 | 885 | 1,526 |

### Tx 积压上限定点 A/B

在 1 MiB Hash、128 B field value 的 HSET 上，将每 worker Tx
积压上限从默认 8 MiB 调到 64 MiB。更大的上限消除了测得的反压等待，
却没有带来明确吞吐收益；默认值仍保持 8 MiB。

| 连接数 | 8 MiB QPS | 8 MiB 反压等待次数 | 64 MiB QPS | 64 MiB 反压等待次数 |
|---:|---:|---:|---:|---:|
| 80 | 6,471 | 304 | 6,281 | 0 |
| 320 | 6,446 | 582 | 6,425 | 0 |
| 2,560 | 7,018 | 3,899 | 7,128 | 0 |

大 List 的点读值得继续剖析。当前代码按 rank 二分定位有序页，
再[加载并解码选中的整页](../../src/storage/engine/grouped_list.cpp)，
并非每次 LINDEX 都扫描整个 List。1 MiB/128 B List 有 8192 个元素，
LINDEX 峰值仅约 13.9 万 QPS；1 MiB/1 KiB List 有 1024 个元素，
峰值约 67.7 万。页内解码与分配是合理候选原因，尚未通过剖析确认为根因。

### 图表

每个单元格分别链接到“点查/写入”图和“完整读取”图。
点查/写入图的连接数横轴为对数刻度；写入 QPS 纵轴也是对数刻度，
以便看清 Lavik 与关闭持久化的两款服务之间的数量级差异。
完整读取图使用线性刻度。

| 数据结构 | 64 KiB / 128 B | 64 KiB / 1 KiB | 1 MiB / 128 B | 1 MiB / 1 KiB |
|---|---|---|---|---|
| Hash | [点查与写入](charts/hash-65536-128.png) · [完整读取](charts/hash-65536-128-full.png) | [点查与写入](charts/hash-65536-1024.png) · [完整读取](charts/hash-65536-1024-full.png) | [点查与写入](charts/hash-1048576-128.png) · [完整读取](charts/hash-1048576-128-full.png) | [点查与写入](charts/hash-1048576-1024.png) · [完整读取](charts/hash-1048576-1024-full.png) |
| Set | [点查与写入](charts/set-65536-128.png) · [完整读取](charts/set-65536-128-full.png) | [点查与写入](charts/set-65536-1024.png) · [完整读取](charts/set-65536-1024-full.png) | [点查与写入](charts/set-1048576-128.png) · [完整读取](charts/set-1048576-128-full.png) | [点查与写入](charts/set-1048576-1024.png) · [完整读取](charts/set-1048576-1024-full.png) |
| List | [点查与写入](charts/list-65536-128.png) · [完整读取](charts/list-65536-128-full.png) | [点查与写入](charts/list-65536-1024.png) · [完整读取](charts/list-65536-1024-full.png) | [点查与写入](charts/list-1048576-128.png) · [完整读取](charts/list-1048576-128-full.png) | [点查与写入](charts/list-1048576-1024.png) · [完整读取](charts/list-1048576-1024-full.png) |
| Sorted Set | [点查与写入](charts/zset-65536-128.png) · [完整读取](charts/zset-65536-128-full.png) | [点查与写入](charts/zset-65536-1024.png) · [完整读取](charts/zset-65536-1024-full.png) | [点查与写入](charts/zset-1048576-128.png) · [完整读取](charts/zset-1048576-128-full.png) | [点查与写入](charts/zset-1048576-1024.png) · [完整读取](charts/zset-1048576-1024-full.png) |
| Stream | [点查与写入](charts/stream-65536-128.png) · [完整读取](charts/stream-65536-128-full.png) | [点查与写入](charts/stream-65536-1024.png) · [完整读取](charts/stream-65536-1024-full.png) | [点查与写入](charts/stream-1048576-128.png) · [完整读取](charts/stream-1048576-128-full.png) | [点查与写入](charts/stream-1048576-1024.png) · [完整读取](charts/stream-1048576-1024-full.png) |

### 解读边界

- 64 个 key 是刻意设置的热 key；每个点仅跑一次八秒，没有重复测量误差范围，
  也没有冷缓存测试。
- 逻辑大小只计算元素 payload；field 名、score、Stream 元数据、协议编码、
  分配器开销与 Lavik 页/索引字节都不计入。
- Set 的 SADD/SREM 等比例访问独立随机 key，可能返回空操作。
  Stream 的 XADD 使用近似 MAXLEN，实际物理写入及保留条数会略有波动。
- Redis/Valkey 关闭持久化，Lavik 没有。写入 QPS 是这些配置下的比较，
  不是同等持久性条件下的性能。
- 1 MiB/128 B Stream 的 64 个 key 共需 524,288 次 XADD 预填充；
  填充时间不计入 memtier 测量。各组耗时见 `*.fill.json`。
  数据组按固定顺序执行，没有随机化。

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
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python collect_plot.py
```

SPDK 准备脚本在丢弃临时数据前，会核对六块专用控制器的序列号和 PCI
地址。不要对需要保留数据的设备执行准备命令。服务端命令、二进制哈希、
memtier 命令、填充耗时、校验结果与各次运行的 JSON 已提交到 `raw/`。
控制台输出留在本机，分支中的 JSON 已包含测量数据，因此没有提交重复日志。
