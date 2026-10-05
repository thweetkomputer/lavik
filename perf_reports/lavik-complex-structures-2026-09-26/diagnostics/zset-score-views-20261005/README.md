# ZSCORE / ZMSCORE 成员页借用视图（验证中）

候选 [`9d1ffc85`](https://github.com/thweetkomputer/lavik/commit/9d1ffc8572f558cc139b1801488d014c2099dbfd) 从 main `4610d607` 开始。原 indexed score lookup 会完整解码所选 Hash 成员页，复制每个字段和值，并重建进程级 digest，最后只保留请求成员的 double 分数。候选同步遍历已加载页的借用视图，只保留所需分数；路由验证计算的持久化 seed digest 同时用于临时查重表。

这仍会分配查重表，不是零分配读取。完整字段路由、重复字段、内部计数、编码和尾部校验均保留；原有页 scratch admission、人口代次/逻辑根检查、页读取和 GC 身份验证保持。借用视图不跨越 read lease；失败时丢弃未发布的命令 scratch。写入路径继续使用 owning snapshot，磁盘格式与缓存策略不变。

现有 HGET/HMGET 视图扫描器只检查请求字段的重复，不能直接替代原 ZSCORE 全页校验；因此复用 HashValueReader 并增加完整校验 visitor。原 Hash 编辑中的临时字段 key/hash 类型移至同文件共享，避免复制该类型实现。测试扩展已有 codec corruption/binary/empty fixture，覆盖命中后的无关重复字段、错误路由和 visitor 错误；现有 ZSet fixture 增加反序 256 成员跨页 ZMSCORE 检查，没有新增磁盘 fixture。

[固定 head 的完整 fork CI](zset-score-views-9d1ffc85-full-ci.json) 已通过全部 17 项：两种架构编译、12 个软件分片、格式和汇总检查。[草稿 PR #280](https://github.com/eloqdata/lavik/pull/280) 已提交，upstream PR 合并树 CI 单独执行；PR 创建时 main 已新增两个 Meta 优化提交，性能对照仍固定原父版本 `4610d607` 和候选 `9d1ffc85`，不重标为其他版本。[PR 身份](pr280-created.json) · [源码及脚本身份](prototype-status.json)。原生回归和性能尚未完成，不能把已有 ZINCRBY 采样称为 ZSCORE 读热点证明。

## 已排队的验证与测量

[原生验证](validate-zset-score-views-native.py) 等待当前 Hash/Set、合并版本验证、长 key 重放及 Stream 对照/采样结束，再取得主机锁。两个固定提交分别构建测试驱动，运行相关 Hash/Sorted Set、demotion、transfer 和 RDB 用例，冻结 tests/faults OFF 的生产二进制并记录 SHA-256。构建使用 `/mnt/dev` TMPDIR 和实际 CMake 选定的 Bycorf 源目录。

[96 点配对测试](repeat-zset-score-views.py) 要求两个固定提交完整 CI 及原生验证通过。100 MiB/key、1024 B/member、8 keys 和 64 KiB/key、128 B/member、64 keys 各三轮 A/B、B/A、A/B；每点 30 秒、pipeline=1，连接数 80/320/2560/5120。每轮 ZSCORE 先由 parent 新建数据，再让两个版本依次重启读取同一逻辑数据，期间不写入。这减少独立 seed/布局差异，但后台物理变化仍可能发生，不能称为不可变设备镜像。ZINCRBY 控制则每个版本独立重新预置，全部 key 的基数、错误和退出码均检查。

[独立 perf](profile-zset-score-views.py) 在全部 96 点完成后采集 ZSCORE：大数据 c5120、小数据 c320，两个版本各一次，共四组；每个版本重启读取该组相同的 parent seed。显式记录 operation 和采样脚本 SHA，每个服务线程分别以 99 Hz task-clock / 16 KiB DWARF 采样 25 秒，服务指标窗口 30 秒。采样包括轮询/后台/内核工作，不将固定顺序的诊断耗时混入干净 QPS。原始 perf 和调用栈保留本地。

所有本机编译、测试、预置、压测和 perf 使用同一 host lock 串行执行。脚本保留当前主机的绝对路径及进程代次等待条件，是本次实验记录；在其他环境复现需先适配路径、设备白名单和前置验证。
