# 8 MiB/key RPUSH/LPOP：合并后 main 的邻页读取优化实验

已更新并复测合并后的 main。省略未变化邻页确实能减少加载与解码，但这次三种候选均未得到同时改善吞吐和尾延迟的结果：同时优化 push/pop 的吞吐配对提升中位数为 18.0%，p99 增加 65.3%；只优化 pop 的吞吐增加 12.9%，p99 增加 70.2%；只优化 push 的吞吐下降 12.1%。因此本次不提新 PR，也不把候选应用到 main。保留全部实验补丁与原始数据供复现。提交队列积压是待继续定位的现象，目前尚未证明根因。

## 版本与测试范围

- 基线：合并 #289 后的 main `cc31b3a6250d0fcf2fa0d985b1ece3a8602e09f9`。其 Git tree 与已验证的 #289 `c8f128dc` 完全相同，因此复用同一 SHA256 的冻结生产二进制；源树等价关系记录在每组 `versions.json`。所有 main 观测均为本次重新测量。
- 每个 key 初始 8 MiB：8192 个 1 KiB 元素，共 8 个 key。320 连接、16 个客户端线程、pipeline=1、30 秒。每次独立随机选 key，并以 50/50 概率选择 RPUSH 或 LPOP；不强制配对。QPS 按命令数计算。
- 每个观测都新启服务、清空并重新准备允许使用的六块 SPDK 设备、重新填充数据并等待事务清理。服务端 12 workers，16 vCPU 配额，无 payload cache。每一对使用相同的进程 digest seed 和客户端种子，三轮交替 main/候选、候选/main、main/候选。
- 三种候选各有三组新测对照，共 18 个常规性能观测；另有 3 次最初 main 复现、6 次独立 perf 采样。perf 不计入 QPS/p99 对照。未测 5120 连接。
- 每条响应、客户端/服务端命令数、push/pop 比例、最终逐 key 元素数（初值 + push − pop）、[0.5N, 2N] 边界以及正常退出均检查通过。生产 CMake cache、Bycorf 依赖和编译参数一致。

## 三种候选的结果

增幅取三个 **候选/main 配对比值的中位数**；它不必等于两列独立中位数之比。

|候选|main QPS 中位数|候选 QPS 中位数|配对 QPS 变化|main p99 中位数|候选 p99 中位数|配对 p99 变化|结论|
|---|---:|---:|---:|---:|---:|---:|---|
|同时省略 RPUSH / 未删空页 pop 的邻页|53,905|60,437|+18.0%|24.65 ms|45.84 ms|+65.3%|未采用：p99 回退|
|只省略 RPUSH 的前邻页|49,786|41,208|-12.1%|49.08 ms|66.26 ms|+12.3%|未采用：吞吐回退|
|只省略未删空页 pop 的邻页|57,799|63,271|+12.9%|20.87 ms|38.39 ms|+70.2%|未采用：p99 回退|

## 实现与正确性

原路径预先加载目标页的相邻页，以便分裂或退休页面时修改完整页面的链接。三个候选分别省略确定不会变化的邻页：尾部插入保留原尾页 ID；单页 pop 若留下非空页面，则两侧链接均不变。若删除整页或确实改动链接，规划器仍要求对应邻页快照。所有已提供页面仍检查版本、身份、链接和内容；Sorted Set 的跨页有序性校验保持完整。

目录规划器、公共 API 注释和对应架构陈述一起修改；既有穷举测试扩展为在相同 180 种 splice 组合中比较“完整加载”和“只加载必要页面”的完整写入后像，再验证事务提交与恢复结果。三个实验的独立补丁见 [combined.patch](combined.patch)、[push-only.patch](push-only.patch)、[pop-only.patch](pop-only.patch)。

- 第一版：244 项单元测试、75 项有序集合/恢复集成测试和 16 项 Hash 集成测试通过。故障注入关闭，分别跳过 36 / 20 项依赖注入的集成测试。
- 后两版仅调整运行时页面选择，规划器及单元测试源文件与第一版相同；各重新运行 12 项 List/有序写集成测试，4 项故障注入用例按配置跳过。
- 修改的 C++ 文件通过 clang-format 23.1.1 检查。

## 逐轮证据与 perf

三次最初 main 复现为 39,350 / 58,034 / 57,321 QPS，p99 为 73.62 / 21.19 / 20.95 ms。慢轮提交队列峰值为 3147；另两轮为 210 / 294。后续各组 main 也有明显波动。因此未把一次低基线当作收益，未把队列峰值与尾延迟的相关性当作根因证明。

perf 使用每 worker 99 Hz task-clock、25 秒、DWARF 调用栈；下表为保留完整函数名的物理调用栈中页面加载/解码的 inclusive CPU 占比。占比包含轮询、内核及后台工作，并非 CPU/命令或 I/O 等待时间；各版本处理的请求数不同，不能直接据此推导延迟改善。

### 同时省略 RPUSH / 未删空页 pop 的邻页

|轮次|版本|QPS|p99 ms|提交队列峰值（测量前 → 后）|原始数据|
|---:|---|---:|---:|---:|---|
|1|main|56,889|21.482|34 → 1831|[结果](../../raw/lavik-maincc31b3a6-queue8m-list-8388608-rpush_lpop-r4-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|1|queueopt|58,958|48.921|23 → 5478|[结果](../../raw/lavik-queueopt309e2af3-queue8m-list-8388608-rpush_lpop-r4-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|2|queueopt|64,384|40.742|17 → 4083|[结果](../../raw/lavik-queueopt309e2af3-queue8m-list-8388608-rpush_lpop-r5-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|2|main|53,905|24.647|19 → 2527|[结果](../../raw/lavik-maincc31b3a6-queue8m-list-8388608-rpush_lpop-r5-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|3|main|51,221|29.917|39 → 2531|[结果](../../raw/lavik-maincc31b3a6-queue8m-list-8388608-rpush_lpop-r6-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|3|queueopt|60,437|45.836|18 → 5877|[结果](../../raw/lavik-queueopt309e2af3-queue8m-list-8388608-rpush_lpop-r6-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|

|perf 版本|诊断 QPS|诊断 p99 ms|页面加载 CPU 占比|解码 CPU 占比|
|---|---:|---:|---:|---:|
|main|39,023|69.829|2.11%|0.67%|
|queueopt|62,949|43.067|1.78%|0.53%|

[审计](combined/audit.json) · [逐轮摘要](combined/summary.json) · [perf 摘要](combined/perf-summary.json) · [版本和构建](combined/versions.json) · [测量脚本](combined/pairs.py)

### 只省略 RPUSH 的前邻页

|轮次|版本|QPS|p99 ms|提交队列峰值（测量前 → 后）|原始数据|
|---:|---|---:|---:|---:|---|
|1|main|49,786|49.079|41 → 2787|[结果](../../raw/lavik-maincc31b3a6-push8m-list-8388608-rpush_lpop-r4-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|1|pushopt|48,653|55.109|31 → 2850|[结果](../../raw/lavik-pushopta519271b-push8m-list-8388608-rpush_lpop-r4-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|2|pushopt|34,454|79.291|41 → 3330|[结果](../../raw/lavik-pushopta519271b-push8m-list-8388608-rpush_lpop-r5-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|2|main|39,186|97.906|35 → 2524|[结果](../../raw/lavik-maincc31b3a6-push8m-list-8388608-rpush_lpop-r5-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|3|main|57,908|20.915|102 → 105|[结果](../../raw/lavik-maincc31b3a6-push8m-list-8388608-rpush_lpop-r6-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|3|pushopt|41,208|66.259|28 → 2690|[结果](../../raw/lavik-pushopta519271b-push8m-list-8388608-rpush_lpop-r6-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|

|perf 版本|诊断 QPS|诊断 p99 ms|页面加载 CPU 占比|解码 CPU 占比|
|---|---:|---:|---:|---:|
|main|55,995|21.823|2.36%|0.90%|
|pushopt|53,125|27.171|1.78%|0.49%|

[审计](push-only/audit.json) · [逐轮摘要](push-only/summary.json) · [perf 摘要](push-only/perf-summary.json) · [版本和构建](push-only/versions.json) · [测量脚本](push-only/pairs.py)

### 只省略未删空页 pop 的邻页

|轮次|版本|QPS|p99 ms|提交队列峰值（测量前 → 后）|原始数据|
|---:|---|---:|---:|---:|---|
|1|main|39,819|68.145|15 → 2674|[结果](../../raw/lavik-maincc31b3a6-pop8m-list-8388608-rpush_lpop-r4-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|1|popopt|63,271|38.394|24 → 4463|[结果](../../raw/lavik-popopt6d74a5fb-pop8m-list-8388608-rpush_lpop-r4-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|2|popopt|65,246|35.523|48 → 5356|[结果](../../raw/lavik-popopt6d74a5fb-pop8m-list-8388608-rpush_lpop-r5-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|2|main|57,799|20.872|34 → 365|[结果](../../raw/lavik-maincc31b3a6-pop8m-list-8388608-rpush_lpop-r5-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|3|main|58,336|20.236|21 → 737|[结果](../../raw/lavik-maincc31b3a6-pop8m-list-8388608-rpush_lpop-r6-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|
|3|popopt|61,131|44.078|25 → 5882|[结果](../../raw/lavik-popopt6d74a5fb-pop8m-list-8388608-rpush_lpop-r6-20261008/list-8388608-1024-rpush_lpop-c320.result.json)|

|perf 版本|诊断 QPS|诊断 p99 ms|页面加载 CPU 占比|解码 CPU 占比|
|---|---:|---:|---:|---:|
|main|44,411|62.531|2.36%|0.95%|
|popopt|54,527|52.944|2.08%|0.77%|

[审计](pop-only/audit.json) · [逐轮摘要](pop-only/summary.json) · [perf 摘要](pop-only/perf-summary.json) · [版本和构建](pop-only/versions.json) · [测量脚本](pop-only/pairs.py)

## 范围与复现

这是 c320、8 MiB/key 的 RPUSH/LPOP 专项实验，不代表其他并发或大小的收益；没有用这些结果替换四系统全量 main 曲线。最新合并状态已补充到原 #289 报告。命令、冻结二进制 SHA、相同种子验证、原始 INFO、客户端结果、编译及测试日志随报告保存；原始大体积 perf.data 留在测试主机，仓库保留采样命令和符号摘要。测试后六块 NVMe 均恢复内核驱动，hugepages 归零，未遗留服务进程。
