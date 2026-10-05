# #282：冻结父版本 CI 检查修正

原排队任务在组合对照结束后检查冻结父版本 `19496654` 的 [CI 37237724710](https://github.com/eloqdata/lavik/actions/runs/37237724710)，发现该轮实际失败，因而在 checkout、编译和测试之前退出；依赖它的性能任务随后也停止。原协议里“两边完整 CI 全绿”的前提不成立，之前没有产生普通 key 的 native 或 QPS 结果。

该 CI 有 14 项成功、一个软件分片和两个汇总项失败。arm64 第 4 分片共 290 个 CTest，仅 `lavik_redis_sync_reader_cluster-cluster` 失败：作为测试源的 Redis 7.2.14 无法绑定 cluster bus `127.0.0.1:54785`，日志明确为 `Address already in use`，Redis 在启动阶段退出。其余 289 个 CTest 通过，包括该分片的 extent recovery 与 grouped Hash 写入套件。

父版本 CI 仍记录为失败，不能视为全绿；这一导入场景仍缺少该父版本的成功结果。候选 `28d7cca4` 的完整 CI 已有 17/17 通过。修正后的前置检查只接受这一个固定 run、head、失败 job 集合和完整日志 SHA，不放行任意失败，也没有重跑 CI。运行清单同时记录失败结论和限制。

既定原生验证已重新取得主机锁并开始构建。两边原生回归仍须全部通过，72 点普通 key 对照才能开始；源码版本、测试范围、编译选项、故障注入设置、数据规模、三轮顺序和超时均保持原协议。旧驱动及其失败日志保留。当前尚无普通 key 的 native 或性能通过结论，#282 继续保持 draft。

[失败 CI](grouped-root-parent-failed-full-ci.json) · [原始分片日志](grouped-root-parent-arm64-shard4-failed.log) · [精确限制与文件哈希](grouped-root-reviewed-ci-preflight.json) · [审查后的 CI 记录](grouped-root-parent-reviewed-full-ci.json) · [前置检查实现](grouped_root_ci_evidence.py) · [修正后的原生驱动](validate-grouped-root-native-reviewed-ci.py) · [既定 72 点驱动](repeat-grouped-root-controls-reviewed-ci.py) · [调度身份](grouped-root-reviewed-ci-launch.json)。原始日志中的列对齐空白和尾部空行保持不变。
