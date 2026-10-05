# #282：冻结版本原生回归完成

固定父版本 `19496654` 与候选 `28d7cca4` 使用相同的测试驱动，原生生产二进制均关闭测试和故障注入。九项记录的编译配置一致，实际 Bycorf 提交均为 `62509c93`；候选构建及相关单元测试完成后，顺序验证两边生产二进制。二进制和驱动 SHA、完整逐例结果及现有依赖来源限制保留在清单中。

| 版本 | Hash 通过 / 跳过 | 有序结构通过 / 跳过 | 阻塞/恢复通过 | 本轮单元测试 |
|---|---:|---:|---:|---:|
| parent `19496654` | 16 / 20 | 47 / 8 | 5 | 本轮未重跑 |
| candidate `28d7cca4` | 16 / 20 | 47 / 8 | 5 | 128 通过 |

每边集成测试共 68 通过、28 跳过，零失败和错误；两边执行和跳过的用例集合相同。28 个跳过项需要生产配置关闭的故障注入钩子，完整名称见校验记录，不计入通过数量。有序结构包括大 Stream/ZSet、RDB 往返、transfer、恢复及多 extent 父 key 场景。测试耗时不是吞吐结果，不拿两边用例耗时计算性能提升。

候选完整 CI 17/17 通过；父版本 CI 仍为失败，唯一实际失败是外部 Redis cluster bus 端口占用导致源 Redis 启动退出。[前置检查修正及原始失败](../grouped-expiry-recovery-20261004/grouped-root-reviewed-ci-preflight.md)保留。这一导入场景没有因原生回归通过而变成已验证，也不将历史 #267 的独立 SET 超时解释为已修复。

既定 72 点普通短 key 对照已在原生验证结束后取得同一主机锁，开始第一轮 Hash 数据准备。当前没有完整配对 QPS/p99 结论；#282 保持 draft。这里验证的是固定历史提交，当前 rebased head `2c94e9da` 的完整 CI 单独记录，不把冻结性能或原生结果转记为当前 head。

[完整版本、逐例结果与二进制/驱动身份](grouped-root-native-versions.json) · [通过/跳过清单、配置及输入哈希](grouped-root-native-complete-validation.json) · [执行日志](grouped-root-native-reviewed-ci-driver.log) · [父构建配置](grouped-root-parent-CMakeCache.txt) · [候选构建配置](grouped-root-candidate-CMakeCache.txt)。原始日志和配置文本的尾部空白保持不变。
