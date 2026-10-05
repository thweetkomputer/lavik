# 复杂结构组合验证

组合对照固定 main `4610d607`（Meta 观察事实捕获，#257），并不将后来更新的 main 重标为这个版本。现有图表和配对结果继续保留各自的固定基线与二进制出处。组合分支 [`78e29277`](https://github.com/thweetkomputer/lavik/tree/bench/complex-combined-20261005) 从这个 main 开始，纳入以下优化及其已有修复：

| PR | 纳入提交 | 内容 | 单项证据 |
|---|---|---|---|
| #265 | `7586dc6f` | Stream 尾部目录复用 | [测量及限制](../stream-suffix-20261004/README.md) |
| #266 | `067c7589` | ZSet 成员叶页复用，包含冷恢复修复 | [测量及精确版本归属](../zset-member-probe-20261004/README.md) |
| #270 | `adec3a34` | Stream 回复批处理，包含冷恢复修复 | [配对控制与 perf](../stream-reply-20261004/README.md) |

三个合并均无冲突。已核对父提交可达性、源码树清洁状态、格式及 diff；已有架构修订一并合入并检查。[完整组合清单](combination.json) · [独立 CI](https://github.com/thweetkomputer/lavik/actions/runs/37260751356)。[完整 CI 已通过](combined-78e29277-full-ci.json)：两种架构编译、12 个软件分片、两个汇总检查和格式检查均成功。本机原生验证现已通过；组合后的 QPS/p99 尚未测量，不能把单项历史收益相乘或视为组合结果。

这是一阶段组合。List 范围读取仍需解决当前验证中的超时问题；ZSet 页复用、Hash/Set 单路由替换等增量候选等待各自配对测量。后续按实际正确性与性能证据更新组合，再用匹配负载与版本的完整命令测量检验 peer 差距。当前尚未达到全体复杂结构命令与另外三个系统相近的水平。

## 原生验证已完成

[原生验证](validate-combined-native.py)在统一主机锁下分别构建并冻结 main `4610d607`、组合 `78e29277` 的 GCC/native/SPDK 生产二进制及测试驱动。两个生产构建均关闭测试和故障注入。

| 版本 | 单元测试通过 | 有序结构集成通过 / fault-only 跳过 | 阻塞命令通过 | Pub/Sub |
|---|---:|---:|---:|---|
| main `4610d607` | 80 | 42 / 8 | 5 | exit 0 |
| combined `78e29277` | 83 | 43 / 9 | 5 | exit 0 |

上述用例均无失败。有序结构包含 ZSet、Stream、demotion、transfer 及三个 RDB 导入/恢复用例；阻塞/恢复与 Pub/Sub 另外运行。跳过项仍明确保留，由对应[父版本完整 CI](combined-main-full-ci.json)和[组合完整 CI](combined-78e29277-full-ci.json)补充 fault-enabled 覆盖，两边各 17 个 job 成功。测试耗时不是吞吐结果。

[固定生产二进制/驱动 SHA 与逐例结果](combined-native-versions.json) · [验证汇总与所有跳过项](combined-native-validation.json) · [父版本构建配置](combined-main-CMakeCache.txt) · [组合构建配置](combined-combined-CMakeCache.txt)。

原构建进程在依赖来源解析器修复前已启动，因此内存中的旧脚本仍从空 `source_repo/bycorf` 目录向上找到 Lavik 仓库，错记依赖提交。[更正脚本](correct-combined-native-provenance.py)根据各自保存的生产 CMake 配置解析实际依赖，保留原字段，并记录后续 checkout、reflog 和嵌套 dirty 状态。[原始清单哈希、更正证据及限制](combined-native-dependency-correction.json)。发布的 CMake 文本仅移除文件末尾多余空行，原始与发布 SHA 分别记录，配置值未改变。它不是独立的构建时源码快照，也不宣称递归依赖干净；二进制、驱动、测试结果和编译选项没有改变。

构建将 `TMPDIR` 放在 `/mnt/dev`，避免先前 Hash 构建遇到的根分区临时空间不足；没有改变优化参数或测试范围。

## 组合后的 150 点对照已排队

[执行脚本](repeat-combined-controls.py)与[固定条件、来源和排队身份](combined-controls-protocol.json)已记录。任务等待现有原生验证、grouped lookup 对照和小 Hash perf 退出，再检查两边原生测试、完整 CI、更正后的依赖清单、匹配编译选项及二进制 SHA，取得主机锁后执行。排队时与取得锁时的驱动 SHA 必须一致。

| 数据 | 读命令及连接数 | 写命令及连接数 |
|---|---|---|
| Stream 100 MiB / 128 B / 8 keys | XRANGE c2560；XRANGE_FULL c1/4/16 | XADD_MAXLEN c320/5120 |
| Stream 64 KiB / 1024 B / 64 keys | XRANGE c5120；XRANGE_FULL c80 | XADD_MAXLEN c2560/5120 |
| Stream 100 MiB / 1024 B / 8 keys | 此条件仅补充写入测量 | XADD_MAXLEN c80/320/5120 |
| ZSet 100 MiB / 1024 B / 8 keys | ZSCORE c80/320/5120 | ZINCRBY c80/320/5120 |
| ZSet 64 KiB / 128 B / 64 keys | ZSCORE c80/320/5120 | ZINCRBY c80/320/5120 |

共 25 个命令/条件/连接数组合，三轮 A/B、B/A、A/B，每点 30 秒、pipeline=1，两版本共 150 个观测。每轮读取让两个版本重启访问同一份新建的父版本逻辑数据，中间不写入；后台物理变化仍可能发生，不称作不可变磁盘镜像。写入为每个版本分别新建数据。全部 key 的基数、原始错误、退出码和精确来源保留，首个失败停止并保留结果。

这是 #265/#266/#270 的一阶段组合验证，既不是全命令套件复测，也不代表已经达到 peer 水平。历史 peer 未重跑，不相乘单项收益；此处没有组合 QPS 或新 perf 结论。脚本保留本机绝对路径、统一锁和 scratch 设备白名单，移机需要适配目录与设备。
