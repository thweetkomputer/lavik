# 根记录复用：候选独立 perf 验证

[原始操作与进程计数](grouped-verified-root-candidate-profiles.json) · [核验摘要和逐符号 self 表](grouped-root-candidate-perf-summary.json) · [核验脚本](summarize-root-candidate-perf.py) · [原始日志与 self 表清单](grouped-root-candidate-perf-evidence-index.json)

固定旧候选 `28d7cca4` 的 CI 二进制，在同一只读恢复镜像的三份独立副本上执行原 16 条诊断命令。2 workers，原 60 秒 socket / 120 秒关闭限制，只对 9 MiB key 的 GET 采集全进程线程 49 Hz task-clock / DWARF 8192；每轮返回完整 6 MiB value 并逐字节校验。全部 48 个操作和 15 次完整 GET 校验成功，三次服务正常退出。记录器按协议收到 SIGINT，原 `-2` 返回码保留；完整写出日志、report 与 script 解码均通过，解码在主机锁内完成。

| 轮次 | GET 秒 | 进程 read_bytes 增量 | 进程 CPU 秒 | 样本数 | perf task-clock 秒 | Lost |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 1.701 | 18,989,056 | 0.60 | 23 | 0.469 | 0 |
| 2 | 1.718 | 18,989,056 | 0.61 | 22 | 0.449 | 0 |
| 3 | 1.678 | 18,989,056 | 0.61 | 23 | 0.469 | 0 |

每轮 `read_bytes` 为 18,989,056（约 18.1 MiB），与此前三个不采样候选回放一致；这次完整 GET 没有出现旧 main / #267 超时诊断中累积的数 GiB 读量。进程计数仍包含后台工作。旧基线采样失败且并非同期配对，不能据此计算精确加速比、放大系数或普通命令 QPS。进程 CPU 来自命令边界的 `/proc`；perf task-clock 来自采样期间的事件权重，两者窗口和取样方式不同，不能混为同一计数。

三次仅有 23 / 22 / 23 个样本（合计 68）。`memcmp` 的 self 占比分别为 47.83% / 50.00% / 39.13%；此前显眼的 CRC32 和 memmove 符号未在这些短采样的 self 表中出现，但缺少样本不能证明工作或分配次数为零。`Lost=0` 也不证明调用栈完整。公开 self 表仅去除行尾空白和末尾空行，清单同时记录原始与公开文件哈希；完整 self 表保留全部符号及原始计数，不用小样本推导新的优化方案或总体收益。

该结果仅验证既有候选的长 key 场景。普通短 key 的 native 回归及 72 点对照仍待完成；新 head `2c94e9da` 的 CI 独立等待，不转记旧 head 的结果。没有在覆盖写入后重启并读回两个巨型 key 的新值；也没有解释原 #267 的 SET 超时。#282 保持草稿，原始失败和协议不变。perf 二进制与完整 stacks 保留本机，哈希和解码命令已记录；公开操作计数、原始 self 表与日志。
