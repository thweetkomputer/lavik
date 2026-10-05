# ZSCORE / ZMSCORE 成员页借用视图（验证中）

**2026-10-05 当前 PR：** #280 已 rebase 为 `a5c825e9`，基于 `main`，[新 CI](https://github.com/eloqdata/lavik/actions/runs/37297696440) 待完成。以下 native、CI 和性能数据仍归属各自标注的原提交；正在执行或排队的对照仍用固定提交，不代表新 head 已通过。[完整记录](../grouped-expiry-recovery-20261004/prs-rebased-after268.json)。

候选 [`9d1ffc85`](https://github.com/thweetkomputer/lavik/commit/9d1ffc8572f558cc139b1801488d014c2099dbfd) 从 main `4610d607` 开始。原 indexed score lookup 会完整解码所选 Hash 成员页，复制每个字段和值，并重建进程级 digest，最后只保留请求成员的 double 分数。候选同步遍历已加载页的借用视图，只保留所需分数；路由验证计算的持久化 seed digest 同时用于临时查重表。

这仍会分配查重表，不是零分配读取。完整字段路由、重复字段、内部计数、编码和尾部校验均保留；原有页 scratch admission、人口代次/逻辑根检查、页读取和 GC 身份验证保持。借用视图不跨越 read lease；失败时丢弃未发布的命令 scratch。写入路径继续使用 owning snapshot，磁盘格式与缓存策略不变。

现有 HGET/HMGET 视图扫描器只检查请求字段的重复，不能直接替代原 ZSCORE 全页校验；因此复用 HashValueReader 并增加完整校验 visitor。原 Hash 编辑中的临时字段 key/hash 类型移至同文件共享，避免复制该类型实现。测试扩展已有 codec corruption/binary/empty fixture，覆盖命中后的无关重复字段、错误路由和 visitor 错误；现有 ZSet fixture 增加反序 256 成员跨页 ZMSCORE 检查，没有新增磁盘 fixture。

[固定 head 的完整 fork CI](zset-score-views-9d1ffc85-full-ci.json) 已通过全部 17 项：两种架构编译、12 个软件分片、格式和汇总检查。[草稿 PR #280](https://github.com/eloqdata/lavik/pull/280) 的[独立上游 pull_request CI](pr280-upstream-full-ci.json)也已通过全部 17 项（[运行记录](https://github.com/eloqdata/lavik/actions/runs/37276852398)）；PR 创建时 main 已新增两个 Meta 优化提交，性能对照仍固定原父版本 `4610d607` 和候选 `9d1ffc85`，不重标为其他版本。[PR 身份](pr280-created.json) · [源码及脚本身份](prototype-status.json)。固定提交的原生回归已完成；96 点性能对照已开始，大对象读取 24 点已完成，大对象写入控制也已完成，整体收益仍待小对象控制。不能把已有 ZINCRBY 采样称为 ZSCORE 读热点证明。

## 已完成的大对象读取

[24 点 ZSCORE 三轮对照](zset-score-views-large-reads.md)：c80/320/2560/5120 的配对 QPS 中位数分别 **+16.27% / +19.82% / +17.08% / +14.45%**，每档三轮均提升。前三档 p99 三轮均改善；c5120 p99 两轮变差，中位 **+2.40%**。[大对象写入 24 点](zset-score-views-large-writes.md)也已完成：c80/320/2560/5120 的配对 QPS 中位 **−1.10%/+0.24%/−0.76%/−1.62%**，各档方向混合；c2560 p99 中位 **+6.67%**。小对象对照、独立 perf 尚未完成，PR 保持草稿。该部分不是整体性能或追平对手的结论。

已完成的 48 个大对象点也通过 INFO 命令计数核验：[读取 24 点](zset-score-views-large-reads-command-audit.json) · [写入 24 点](zset-score-views-large-writes-command-audit.json)。每点实际业务调用数等于 requests，失败/拒绝增量为零，除 INFO 外没有其他命令混入测量窗口。这不证明性能变化的因果。

## 原生验证结果与后续测量

[原生验证摘要](zset-score-views-native-summary.json) · [二进制、依赖及完整测试清单](zset-score-views-versions.json) · [验证驱动日志](zset-score-views-native-driver.log)

| 固定版本 | 单元测试通过 | 原生测试通过 | 原生测试跳过 | 失败 |
|---|---:|---:|---:|---:|
| parent `4610d607` | 87 | 29 | 7 | 0 |
| candidate `9d1ffc85` | 88 | 29 | 7 | 0 |

原生范围涵盖 Sorted Set 点读写、反序多成员分数回复、超过 512 MiB 的聚合恢复、demotion、跨 worker transfer 和三项 RDB 用例。七项跳过均要求生产构建关闭的故障注入；不能把跳过算作通过。故障注入的历史完整 CI 见上方独立记录。每个版本分别构建其测试驱动，候选新增 visitor 单元覆盖，端到端使用扩展后的既有 fixture。

生产二进制父/候选 SHA-256 分别为 `44695167697904ad6a210dd50e6fcdf3634f494fb633eb1267c5e9b568eed552` / `36de21675ae4c15ac391cb73579080b5d6fbee65cb2a6e5358d5daa4e8ce5675`。实际 CMake 依赖为 `62509c93`，嵌套 SPDK 工作区修改状态仍记录；不宣称递归依赖干净。所有结果属于上述冻结提交，不替代 rebase 后 `a5c825e9` 的 CI，也不是 QPS 收益证据。


[原生验证](validate-zset-score-views-native.py) 已在前置任务结束后取得主机锁并完成。两个固定提交分别构建测试驱动，运行相关 Hash/Sorted Set、demotion、transfer 和 RDB 用例，冻结 tests/faults OFF 的生产二进制并记录 SHA-256。构建使用 `/mnt/dev` TMPDIR 和实际 CMake 选定的 Bycorf 源目录。

[96 点配对测试](repeat-zset-score-views.py) 要求两个固定提交完整 CI 及原生验证通过。100 MiB/key、1024 B/member、8 keys 和 64 KiB/key、128 B/member、64 keys 各三轮 A/B、B/A、A/B；每点 30 秒、pipeline=1，连接数 80/320/2560/5120。每轮 ZSCORE 先由 parent 新建数据，再让两个版本依次重启读取同一逻辑数据，期间不写入。这减少独立 seed/布局差异，但后台物理变化仍可能发生，不能称为不可变设备镜像。ZINCRBY 控制则每个版本独立重新预置，全部 key 的基数、错误和退出码均检查。

[独立 perf](profile-zset-score-views.py) 在全部 96 点完成后采集 ZSCORE：大数据 c5120、小数据 c320，两个版本各一次，共四组；每个版本重启读取该组相同的 parent seed。显式记录 operation 和采样脚本 SHA，每个服务线程分别以 99 Hz task-clock / 16 KiB DWARF 采样 25 秒，服务指标窗口 30 秒。采样包括轮询/后台/内核工作，不将固定顺序的诊断耗时混入干净 QPS。原始 perf 和调用栈保留本地。

所有本机编译、测试、预置、压测和 perf 使用同一 host lock 串行执行。脚本保留当前主机的绝对路径及进程代次等待条件，是本次实验记录；在其他环境复现需先适配路径、设备白名单和前置验证。
