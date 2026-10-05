# 复杂结构组合验证

main 已前进到 `4610d607`（Meta 观察事实捕获，#257）。现有图表和配对结果继续保留各自的固定基线与二进制出处。组合分支 [`78e29277`](https://github.com/thweetkomputer/lavik/tree/bench/complex-combined-20261005) 从这个 main 开始，纳入以下优化及其已有修复：

| PR | 纳入提交 | 内容 | 单项证据 |
|---|---|---|---|
| #265 | `7586dc6f` | Stream 尾部目录复用 | [测量及限制](../stream-suffix-20261004/README.md) |
| #266 | `067c7589` | ZSet 成员叶页复用，包含冷恢复修复 | [测量及精确版本归属](../zset-member-probe-20261004/README.md) |
| #270 | `adec3a34` | Stream 回复批处理，包含冷恢复修复 | [配对控制与 perf](../stream-reply-20261004/README.md) |

三个合并均无冲突。已核对父提交可达性、源码树清洁状态、格式及 diff；已有架构修订一并合入并检查。[完整组合清单](combination.json) · [独立 CI](https://github.com/thweetkomputer/lavik/actions/runs/37260751356)。CI 尚在运行，本机原生验证及组合后的 QPS/p99/perf 尚未执行，不能把单项历史收益相乘或视为组合结果。

这是一阶段组合。List 范围读取仍需解决当前验证中的超时问题；ZSet 页复用、Hash/Set 单路由替换等增量候选等待各自配对测量。后续按实际正确性与性能证据更新组合，再用匹配负载与版本的完整命令测量检验 peer 差距。当前尚未达到全体复杂结构命令与另外三个系统相近的水平。
